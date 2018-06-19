FROM alpine:latest

RUN apk update
RUN apk add curl python3
RUN pip3 install requests
RUN true \
	&& curl -L -s -o /usr/bin/pipeline-commander https://goo.gl/146MEQ \
	&& chmod +x /usr/bin/pipeline-commander \
	&& /usr/bin/pipeline-commander --help
