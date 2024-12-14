FROM panther_base_service_panther:latest

ENV DEBIAN_FRONTEND=noninteractive
# Define build arguments for version-specific configurations
ARG VERSION=master
ARG DEPENDENCIES="[]"  # JSON-formatted list of dependencies
ENV VERSION=${VERSION}
ENV DEPENDENCIES=${DEPENDENCIES}

RUN apt-get update && \
    apt-get install -y build-essential git cmake software-properties-common \
    openssl libssl-dev pkg-config clang binutils \
    libasan5 \
    wget \
    libhttp-parser2.9 \
    libubsan1 && \
    apt-get clean

RUN wget https://go.dev/dl/go1.21.10.linux-amd64.tar.gz
RUN rm -rf /usr/local/go && tar -C /usr/local -xzf go1.21.10.linux-amd64.tar.gz
RUN export PATH="$PATH:/usr/local/go/bin"

RUN cd /opt && \
    git clone https://github.com/lucas-clemente/quic-go; \
    cd quic-go; \
    git fetch; \ 
    git checkout v0.45.2;  \
    git submodule update --init --recursive; \
    mkdir client server

ADD file_to_change/rfc9000-2/go_client/main.go /opt/quic-go/client/main.go
ADD file_to_change/rfc9000-2/go_server/main.go /opt/quic-go/server/main.go
ADD file_to_change/cert.pem /certs/cert.pem
ADD file_to_change/priv.key /certs/priv.key

RUN cd /opt/quic-go/; /usr/local/go/bin/go clean -modcache
RUN cd /opt/quic-go/; /usr/local/go/bin/go build -o server/server server/main.go
RUN cd /opt/quic-go/; /usr/local/go/bin/go build -o client/client client/main.go

# Expose necessary ports
EXPOSE 4443
EXPOSE 8080

# Ensure the log directory exists
RUN mkdir -p /app/logs
RUN mkdir -p /opt/certs
RUN mkdir -p /opt/ticket

# Set entrypoint (can be overridden)
ENTRYPOINT [ "/bin/sh", "-l", "-c" ]