ARG BASE_IMAGE=panther_base_service:latest
FROM ${BASE_IMAGE}

ARG VERSION=master
ARG DEPENDENCIES="[]"

ENV DEBIAN_FRONTEND=noninteractive

# Install FRR from the official LibCoAP APT repository (glibc, matches Ubuntu base)
RUN apt-get update && \
    apt-get install --no-install-recommends -y curl git make asciidoc xmlto docbook-xml docbook-xsl libcunit1-dev && \
    apt-get update && \
    rm -rf /var/lib/apt/lists/*


# These examples require libcoap-3 with a minimum version of 4.3.2 to compile and execute.

# client.cc is a minimal libcoap client that sends a confirmable UDP GET /hello request to a pre-defined CoAP server (coap.me in this example) and outputs a received response. It supports an optional argument which can be a different CoAP URI to send the request to. If the host is a multicast address, then this is handled by a NON-confirmable request.

# server.cc is a minimal CoAP server that binds on ::5683, as well as the multicast IPs 224.0.1.187 and ff02::fd. It has two defined resources /hello and hello/my along with the inbuilt resource .well-known/core.

# Copyright (C) 2018-2026 Olaf Bergmann bergmann@tzi.org
WORKDIR /opt/
RUN git clone https://github.com/obgm/libcoap.git && \
    cd libcoap && ./autogen.sh --clean && ./autogen.sh && \
    ./configure LIBS="-lpthread" --disable-doxygen --enable-manpages --enable-dtls --enable-tests  --enable-examples && make && sudo make install
COPY ./version_configs/rfc7252.yaml /opt/libcoap/version_config.yaml


RUN git clone https://github.com/obgm/libcoap-minimal.git &&\
    cd libcoap-minimal && \
    make



ENTRYPOINT [ "/bin/bash", "-l", "-c" ]
