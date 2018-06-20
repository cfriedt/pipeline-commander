#!/usr/bin/env python3

import argparse
import errno
import json
import os
import pprint
import requests
import signal
import sys
import time
import yaml

# global constants
PROGNAME = 'pipeline-commander'
HOME = os.path.expanduser( '~' )
DEFAULT_CONFIG = os.path.join( HOME, '.config', PROGNAME + '.yml' )

USAGE_STR="""
{0}

Notes:

The '-p' option should be used with care, as GitLab private tokens can be used in
place of stronger authentication mechanisms. Always use HTTPS to prevent this
token from being transmitted in plaintext.

Supported Commands:

{1}
"""

# globals
_sigint_received = False
def sigint_handler( signal, frame ):
    global _sigint_received
    if not _sigint_received:
        print( "caught signal {0} in frame {1}".format( signal, frame ) )
        _sigint_received = True

# https://stackoverflow.com/questions/15008758/parsing-boolean-values-with-argparse
def str2bool(v):
    if v.lower() in ('yes', 'true', 't', 'y', '1'):
        return True
    elif v.lower() in ('no', 'false', 'f', 'n', '0'):
        return False
    else:
        raise argparse.ArgumentTypeError('Boolean value expected.')

# the APIv4 class
class api_v4( object ):

    def __init__( self, url, private_token ):

        self._headers = { 'private-token': private_token }
        self._url = url + "/api/v4"
        self._verbose = False
        self._skip_ssl_verification = False

    def V( self, *args, **kwargs ):
        if self._verbose:
            print( *args, **kwargs )

    def set_verbosity( self, verbose ):
        self._verbose = verbose

    def skip_ssl_verification( self ):
        self._skip_ssl_verification = True

    def _get( self, url ):
        self.V( "GET APIv4 url '{0}'".format( url ) )
        if self._skip_ssl_verification:
            response = requests.get( url, headers = self._headers, verify = False )
        else:
            response = requests.get( url, headers = self._headers )
        if response.status_code not in ( 200, 201 ):
            raise ValueError( response )
        jsn = json.loads( response.text )
        self.V( "Received JSN response:" )
        self.V( pprint.pformat( jsn, indent = 4 ) )
        return jsn

    def _post( self, url, data ):
        self.V( "POST APIv4 url '{0}'".format( url ) )
        if self._skip_ssl_verification:
            response = requests.post( url, headers = self._headers, data = data, verify = False )
        else:
            response = requests.post( url, headers = self._headers, data = data )
        if response.status_code not in ( 200, 201 ):
            raise ValueError( response )
        jsn = json.loads( response.text )
        self.V( "Received JSN response:" )
        self.V( pprint.pformat( jsn, indent = 4 ) )
        return jsn

    #
    # API commands
    #

    # List All Projects
    # https://docs.gitlab.com/ee/api/projects.html#list-all-projects_list
    # Get Single Project
    # https://docs.gitlab.com/ee/api/projects.html#get-single-project
    def projects_list( self, project_id = None ):

        url = self._url + "/projects"
        if project_id:
            url += "/" + project_id

        return self._get( url )

    # List Project Pipelines
    # https://docs.gitlab.com/ee/api/pipelines_list.html#list-project-pipelines_list
    # Get a Single Pipeline
    # https://docs.gitlab.com/ee/api/pipelines_list.html#get-a-single-pipeline
    def pipelines_list( self, project_id, pipeline_id = None ):

        url = self._url + "/projects/{}".format( project_id ) + "/pipelines"

        if pipeline_id:
            url += "/{}".format( pipeline_id )

        return self._get( url )

    # Create a New Pipeline
    # https://docs.gitlab.com/ee/api/pipelines.html#create-a-new-pipeline
    def pipelines_create( self, project_id, ref, variables = {} ):

        url = self._url + "/projects/{}".format( project_id ) + "/pipeline"

        data = {}
        data.update( { 'ref': ( None, ref ) } )
        for k,v in variables.items():
            data.update( { k: ( None, v ) } )

        return self._post( url, data )

    # Cancel a Pipeline's Jobs
    # https://docs.gitlab.com/ee/api/pipelines.html#cancel-a-pipelines-jobs
    def pipelines_cancel( self, project_id, pipeline_id ):

        url = self._url + "/projects/{}".format( project_id ) + "/pipelines/{}".format( pipeline_id ) + "/cancel"

        return self._post( url, dict() )

# the main class
class pipeline_commander( object ):
    """
    Pipeline Commander

    A hackish tool to query and manipulate GitLab pipelines_list.

    See https://docs.gitlab.com/ee/api/pipelines_list.html
    """

    def __init__( self ):
        if pipeline_commander._instance:
            raise ValueError( 'This is a singleton class. Please use pipeline_commander.inst()' )

        setattr( self, 'version', '0.1' )
        setattr( self, 'verbose', False )

        parser_main = argparse.ArgumentParser( description = "{0}: A hackish tool to query and manipulate GitLab pipelines_list".format( PROGNAME ) )

        parser_main.add_argument( '-c', '--config', help = 'Path to configuration file' )
        parser_main.add_argument( '-p', '--private-token', help = 'GitLab private token' )
        parser_main.add_argument( '-u', '--server-url', help = 'Base server URL. E.g. https://172.17.0.1' )
        parser_main.add_argument( '-v', '--verbose', action = 'store_true', default = False, help = 'Increase verbosity of messages' )
        parser_main.add_argument( '-V', '--version', action = 'store_true', default = False, help = "Show the version of {0} and exit".format( PROGNAME ) )
        parser_main.add_argument( '-k', '--skip-ssl-verification', help = 'Skip SSL verification', default = False, action = 'store_const', const = True )

        subparsers = parser_main.add_subparsers( help = 'sub-command help' )

        # projects command
        parser_projects = subparsers.add_parser( 'projects' )
        parser_projects.add_argument( '-i', '--id', help = 'the id of the individual project to list' )
        parser_projects.set_defaults( func = projects )

        # pipelines command
        parser_pipelines = subparsers.add_parser( 'pipelines' )
        parser_pipelines.add_argument( 'pipelines_cmd', choices = ( 'list', 'create', 'cancel' )  )
        parser_pipelines.add_argument( '-i', '--project-id', help = 'the project id', required = True )
        parser_pipelines.add_argument( '-l', '--pipeline-id', help = 'the pipeline id' )
        parser_pipelines.add_argument( '-r', '--git-ref', help = 'the git reference' )
        parser_pipelines.add_argument( '-v','--variable', nargs='*', help = 'one or more variables in key=value format' )
        parser_pipelines.add_argument( '-w','--wait', help = 'wait for completion and adjust return value accordingly', default = False, action = 'store_const', const = True )
        parser_pipelines.set_defaults( func = pipelines )

        self.parser = parser_main

    # sort-of singleton
    _instance = None
    def inst():
        if not pipeline_commander._instance:
            pipeline_commander._instance = pipeline_commander()
        return pipeline_commander._instance
    inst = staticmethod( inst )

    def V( self, *args, **kwargs ):
        if self.verbose:
            print( *args, file=sys.stderr, **kwargs )

    def E( self, *args, **kwargs ):
        print( *args, file=sys.stderr, **kwargs )

    def usage( self ):
        commands = ""
        for k,v in self.valid_commands.items():
            commands += "{0}\t\t{1}\n".format( k, v )

        usage_str = USAGE_STR.format(
            self.ap.format_help(),
            commands
        )

        print( usage_str )

    def process_config( self, cfg_path = DEFAULT_CONFIG, must_exist = False ):

        if not os.path.exists( cfg_path ):
            self.V( "ignoring nonexistent path '{0}'".format( cfg_path ) )
            return

        try:
            with open( cfg_path, 'r' ) as yamlcfg:
                cfg = yaml.load( yamlcfg )
                if cfg is not None:
                    for k,v in cfg.items():
                        self.V( "processing config option '{0}'='{1}'".format( k, v ) )
                        setattr( self, k, v )
        except IOError:
            if must_exist:
                raise
            else:
                pass

    def process_arguments( self ):

        if len( sys.argv ) is 0:
            self.usage()
            sys.exit( os.EX_OK )

        args = self.parser.parse_args()

        cfg = getattr( args, 'config' )
        if cfg:
            setattr( self, 'config', cfg )
            self.process_config( cfg_path = cfg, must_exist = True )
        else:
            setattr( self, 'config', DEFAULT_CONFIG )

        if getattr( args, 'version' ):
            print( self.version )
            sys.exit( os.EX_OK )

        for key in vars( args ):
            if 'config' is key:
                continue
            val = getattr( args, key )
            if val is not None:
                setattr( self, key, val )

        if not hasattr( self, 'private_token' ):
            self.E( "please add your private token to {0}".format( getattr( self, 'config' ) ) )
            sys.exit( errno.EINVAL )

        if not hasattr( self, 'server_url' ):
            self.E( "No server-url argument specified" )
            sys.exit( errno.EINVAL )

        self._api = api_v4( getattr( self, 'server_url' ), getattr( self, 'private_token' ) )
        self._api.set_verbosity( getattr( self, 'verbose' ) )
        if getattr( self, 'skip_ssl_verification' ):
         self._api.skip_ssl_verification()

        sys.exit( args.func( args ) )

# commands
def projects( *args ):
    pc = pipeline_commander.inst()
    jsn = pc._api.projects_list( getattr( pc, 'id', None ) )
    for prj in jsn:
        print(
            "{0}\t{1}\t{2}".format(
                prj[ 'id' ],
                prj[ 'name' ],
                prj[ 'web_url' ]
            )
        )

def pipelines( *args ):
    pc = pipeline_commander.inst()

    if False:
        pass
    elif 'list' == getattr( pc, 'pipelines_cmd' ):
        jsn = pc._api.pipelines_list( getattr( pc, 'project_id' ), getattr( pc, 'pipeline_id', None ) )

        # when reading back a single id, it's a dict, not a list, so just convert it to a list to reuse code
        if type( jsn ) is dict:
            jsn = [ jsn ]

        for ppl in jsn:
            print(
                "{0}\t{1}\t{2}\t{3}".format(
                    ppl[ 'id' ],
                    ppl[ 'ref' ],
                    ppl[ 'sha' ],
                    ppl[ 'status' ]
                )
            )

    elif 'create' == getattr( pc, 'pipelines_cmd' ):

        variables = {}
        for kv in getattr( pc, 'variable', list() ):
            pc.V( "Processing variable '{}'".format( kv ) )
            if '=' not in kv:
                raise ValueError( "variables are of the form KEY=VAL" )
            kvlst = kv.split( '=' )
            if 2 != len( kvlst ):
                raise ValueError( "variables are of the form KEY=VAL" )
            k = kvlst[ 0 ]
            v = kvlst[ 1 ]
            variables.update( { k: v } )

        project_id = getattr( pc, 'project_id' )

        jsn = pc._api.pipelines_create( project_id, getattr( pc, 'git_ref' ), variables )

        pipeline_id = jsn[ 'id' ]

        print( pipeline_id )

        if getattr( pc, 'wait' ):
            pc.V( "Waiting for pipeline {} to complete..".format( pipeline_id ) )

            prev_status = ''
            while True:

                if _sigint_received:
                    print( "received SIGINT - cancelling pipeline {}".format( pipeline_id ) )
                    jsn = pc._api.pipelines_cancel( project_id, pipeline_id )
                    return os.EX_OK

                time.sleep( 1 )

                # get status
                jsn = pc._api.pipelines_list( project_id, pipeline_id )
                status = jsn[ 'status' ]

                if status != prev_status:
                    print( "status: {}".format( status ) )
                    prev_status = status
                else:
                    print( '.', end = '', flush = True )

                if 'failed' == status:
                    return os.EX_SOFTWARE

                if 'success' == status:
                    return os.EX_OK

                if 'canceled' == status:
                    print( "pipeline {} was cancelled externally".format( pipeline_id ) )
                    return os.EX_OK

    elif 'cancel' == getattr( pc, 'pipelines_cmd' ):
        jsn = pc._api.pipelines_cancel( getattr( pc, 'project_id' ), getattr( pc, 'pipeline_id' ) )

if __name__ == '__main__':

    signal.signal( signal.SIGINT, sigint_handler )

    pc = pipeline_commander.inst()
    # load configuration options stored in ~/.config/pipeline-commander.yml
    pc.process_config()
    # process command-line arguments, potentially specifying a different config file
    pc.process_arguments()
