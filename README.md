# pipeline-commander
A hackish tool to trigger a [GitLab](https://gitlab.com) pipeline and wait for its completion.

It's kind of like the poor man's version of the [Multi-Project Pipelines](https://docs.gitlab.com/ee/ci/multi_project_pipeline_graphs.html) feature just [released in GitLab 9.3](https://about.gitlab.com/2017/06/22/gitlab-9-3-released/).

# Usage
```
usage: pipeline-commander.py [-h] [-c CONFIG] [-p PRIVATE_TOKEN]
                             [-u SERVER_URL] [-v] [-V] [-k]
                             {projects,pipelines} ...

pipeline-commander: A hackish tool to query and manipulate GitLab
pipelines_list

positional arguments:
  {projects,pipelines}  sub-command help

optional arguments:
  -h, --help            show this help message and exit
  -c CONFIG, --config CONFIG
                        Path to configuration file
  -p PRIVATE_TOKEN, --private-token PRIVATE_TOKEN
                        GitLab private token
  -u SERVER_URL, --server-url SERVER_URL
                        Base server URL. E.g. https://172.17.0.1
  -v, --verbose         Increase verbosity of messages
  -V, --version         Show the version of pipeline-commander and exit
  -k, --skip-ssl-verification
                        Skip SSL verification
```

# List Projects

```
usage: pipeline-commander projects [-h] [-i ID]

optional arguments:
  -h, --help      show this help message and exit
  -i ID, --id ID  the id of the individual project to list
```

# List, Create, and Cancel Pipelines

```
usage: pipeline-commander pipelines [-h] -i PROJECT_ID [-l PIPELINE_ID]
                                    [-r GIT_REF]
                                    [-v [VARIABLE [VARIABLE ...]]] [-w]
                                    {list,create,cancel}

positional arguments:
  {list,create,cancel}

optional arguments:
  -h, --help            show this help message and exit
  -i PROJECT_ID, --project-id PROJECT_ID
                        the project id
  -l PIPELINE_ID, --pipeline-id PIPELINE_ID
                        the pipeline id
  -r GIT_REF, --git-ref GIT_REF
                        the git reference
  -v [VARIABLE [VARIABLE ...]], --variable [VARIABLE [VARIABLE ...]]
                        one or more variables in key=value format
  -w, --wait            wait for completion and adjust return value
                        accordingly
```

# Example

The typical use-case is below

```bash
curl -L -s -o pipeline-commander.py https://goo.gl/146MEQ
python3 pipeline-commander.py \
  pipeline create \
  --server-url https://example.co \
  --project-id 11 \
  --git-ref master \
  --private-token AbcDefGhijkLmNopQrsT \
  -w
echo "exit status was $?"
```
Output:
```
status: pending
..status: running
...........status: success
exit status was 0
```

Most users would likely keep their private token in a secure configuration file.

```bash
mkdir -p ~/.config
set +o history
echo "private_token: 'AbcDefGhijkLmNopQrsT'" > ~/.config/pipeline-commander.yml
chmod go-rwx ~/.config/pipeline-commander.yml
set -o history
curl -L -s -o pipeline-commander.py https://goo.gl/146MEQ
python3 pipeline-commander.py \
  pipeline create \
  --server-url https://example.co \
  --project-id 11 \
  --git-ref master \
  -w
echo "exit status was $?"
```
Output:
```
status: pending
..status: running
...........status: success
exit status was 0
```
