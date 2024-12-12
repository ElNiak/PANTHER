FROM panther_base_service_panther:latest

ENV DEBIAN_FRONTEND=noninteractive


WORKDIR /opt/

ARG VERSION=random
ENV VERSION=${VERSION}

ADD src//${VERSION}/miniP.h /opt/ping-pong/miniP.h
ADD src/${VERSION}/delay.h /opt/ping-pong/delay.h
ADD src/${VERSION}/miniP_client.c /opt/ping-pong/miniP_client.c
ADD src/${VERSION}/miniP_server.c /opt/ping-pong/miniP_server.c

RUN cd ping-pong/; \
    gcc miniP_client.c -o miniP_client && gcc miniP_server.c -o miniP_server

ENTRYPOINT [ "/bin/sh", "-l", "-c" ]