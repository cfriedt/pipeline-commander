#!/usr/bin/env python3

import argparse
import json
import os
import requests
import sys
import time

class pipeline_commander:
	"""
	Pipeline Commander
	
	A hackish tool to trigger a GitLab pipeline and wait for its completion.
	
	See https://docs.gitlab.com/ee/api/pipelines.html
	"""

	def __init__( self, server_url = 'http://localhost:80', git_ref = 'master', project_id = 0, verbose = False, private_token = None, trigger_token = None ):

		# state variables
		self.triggered = False

		# values that can be set in the environment
		try:
			self.private_token = os.environ[ 'PRIVATE_TOKEN' ]
		except KeyError as e:
			self.private_token = None
			pass

		try:
			self.trigger_token = os.environ[ 'TRIGGER_TOKEN' ]
		except KeyError as e:
			self.trigger_token = None
			pass

		# fields
		self.server_url = server_url
		self.git_ref = git_ref
		self.project_id = project_id
		self.verbose = verbose
		
		if private_token is not None:
			self.private_token = private_token
			
		if trigger_token is not None:
			self.trigger_token = trigger_token

		if self.private_token is None:
			ValueError( "Private Token was not specified" )

		if self.trigger_token is None:
			ValueError( "Trigger Token was not specified" )


	def trigger( self ):

		if self.triggered:
			ValueError( 'Already triggered' )

		payload = { 'token': ( None, self.trigger_token ), 'ref': ( None, self.git_ref ) }
		url = "{0}/api/v4/projects/{1}/trigger/pipeline".format( self.server_url, self.project_id )

		self.v( "Triggering build for project {0}, ref {1}, via {2}".format( self.project_id, self.git_ref, self.server_url ) )
		response = requests.post( url, files = payload )

		if not ( response.status_code == 200 or response.status_code == 201 ):
			raise ValueError( response )

		self.triggered = True
		self.trigger_jsn = json.loads( response.text )

		self.v( "Trigger Response:\n{0}".format( response.text ) )
		self.v( "Build status URL is {0}".format( self.get_pipeline_url() ) )


	def get_pipeline_url( self ):

		if not self.triggered:
			ValueError( 'Not triggered' )

		url = "{0}/api/v4/projects/{1}/pipeline/{2}".format( self.server_url, self.project_id, self.trigger_jsn[ 'id' ] )

		return url


	def get_jobs_url( self ):
		"""
		For some reason, the API call for getting the status for just one particular pipeline does not seem to be working right now,
		so we just get all of the jobs and filter-out
		"""

		if not self.triggered:
			ValueError( 'Not triggered' )

		url = "{0}/api/v4/projects/{1}/pipelines".format( self.server_url, self.project_id )

		return url


	def get_status( self ):

		if not self.triggered:
			ValueError( 'Not triggered' )

		headers = { 'PRIVATE-TOKEN': self.private_token }

		url = self.get_jobs_url()
		
		self.v( "Getting Build ID {0} for Project ID {1} via URL {2}".format( self.trigger_jsn[ 'id' ], self.project_id, url ) )
		
		response = requests.get( url, headers = headers )

		jsn = json.loads( response.text )

		for e in jsn:
			if e[ 'id' ] == self.trigger_jsn[ 'id' ]:
				return e[ 'status' ]

		raise ValueError( "Build id {0} for project id {1} not found!".format( self.trigger_jsn[ 'id' ], self.project_id ) )
	

	def wait_for( self ):
		
		prev_status = ''
		
		while True:
			
			status = self.get_status()
			
			if status != prev_status:
				print( "status: {0}".format( status ) )
				prev_status = status
				
			if "success" == status:
				return 0
			
			elif "failed" == status:
				print( "\nError:\n{0}".format( status_jsn ) )
				return 1
			
			else:
				sys.stdout.write( '.' )
				sys.stdout.flush()
				time.sleep( 1 )

	def v( self, arg ):
		if self.verbose:
			print( arg )

if __name__ == '__main__':

	ap = argparse.ArgumentParser( description = 'Trigger a GitLab Pipeline and wait for its completion' )
	
	ap.add_argument( '-r', '--git-ref', help = 'Git reference, e.g. master' )
	ap.add_argument( '-o', '--timeout', type = int, help = 'Timeout in seconds' )
	ap.add_argument( '-i', '--project-id', type = int, help = 'Numerical Project ID (under Settings->General Project Settings in GitLab' )
	ap.add_argument( '-p', '--private-token', help = 'An private or personal token authorised to query pipeline status. See https://docs.gitlab.com/ee/api/README.html#private-tokens. By default, this value is initialized with PRIVATE_TOKEN environment variable.' )
	ap.add_argument( '-u', '--server-url', help = 'Server URL to use, e.g. http://localhost:80' )
	ap.add_argument( '-t', '--trigger-token', help = 'The trigger token for a pipeline. See https://docs.gitlab.com/ee/ci/triggers. By default, this value is initialized with TRIGGER_TOKEN environment variable.' )
	ap.add_argument( '-v', '--verbose', help = 'Print more verbose information' )

	args = ap.parse_args()

	pc = pipeline_commander()
	
	for key in vars( args ):
		val = getattr( args, key )
		if val is not None:
			setattr( pc, key, val )

	pc.trigger()
	exit( pc.wait_for() )
