FROM alpine:latest

RUN apk update
RUN apk add curl python3 py3-yaml
RUN pip3 install requests
