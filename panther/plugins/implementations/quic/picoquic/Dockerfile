FROM ubuntu:20.04

ENV DEBIAN_FRONTEND=noninteractive

RUN ln -fs /usr/share/zoneinfo/UTC /etc/localtime && \
    apt-get update && \
    apt-get install -y build-essential git cmake software-properties-common \
    openssl libssl-dev pkg-config clang python3 net-tools tcpdump \
    apt-utils  wireshark tshark  libcap2-bin traceroute \
    iputils-ping iproute2 iperf3 netcat-openbsd curl dnsutils iperf 

# "yes" answer by 'dpkg-reconfigure wireshark-common' so you can run tshark as normal use
RUN yes yes | DEBIAN_FRONTEND=teletype dpkg-reconfigure wireshark-common

# Define build arguments for version-specific configurations
ARG VERSION=master
ARG DEPENDENCIES="[]"  # JSON-formatted list of dependencies
ENV VERSION=${VERSION}
ENV DEPENDENCIES=${DEPENDENCIES}

ARG USER_UID=1000
ARG USER_GID=1000
ARG USER_N=elniak

RUN addgroup --gid ${USER_GID} ${USER_N} && \
    adduser --disabled-password --gecos '' --uid ${USER_UID} --gid ${USER_GID} ${USER_N} && \
    usermod -aG wireshark ${USER_N}

# RUN chown ${USER_N}:wireshark /usr/bin/dumpcap

# RUN setcap 'CAP_NET_RAW+eip CAP_NET_ADMIN+eip' /usr/bin/dumpcap && \
#     chgrp wireshark /usr/bin/dumpcap 
    # chmod 750 /usr/bin/dumpcap

# RUN setcap 'CAP_NET_RAW+eip CAP_NET_ADMIN+eip' /usr/bin/dumpcap
# RUN chmod +x /usr/bin/dumpcap 


# Give the user ownership of the /app directory (or any directories you need)
RUN mkdir -p /app
RUN chown -R ${USER_N}:${USER_N} /app
RUN chown -R ${USER_N}:${USER_N} /opt

# Switch to the new user

# Perl stuff is for the picotls test code
RUN echo install Test::TCP | perl -MCPAN -
RUN echo install Scope::Guard | perl -MCPAN -

# Install jq for JSON parsing
RUN apt-get install -y jq

USER ${USER_N}

# Function to parse and build dependencies
# TODO make more modular
RUN cd /opt && \ 
    echo "Starting dependency installation..." && \
    echo $DEPENDENCIES | jq -c '.[]' | while read -r dep; do \
        DEP_NAME=$(echo $dep | jq -r '.name'); \
        DEP_URL=$(echo $dep | jq -r '.url'); \
        DEP_COMMIT=$(echo $dep | jq -r '.commit'); \
        if [ -n "$DEP_NAME" ] && [ -n "$DEP_URL" ] && [ -n "$DEP_COMMIT" ]; then \
            echo "Cloning dependency '$DEP_NAME' from '$DEP_URL' at commit '$DEP_COMMIT'" && \
            git clone "$DEP_URL" "$DEP_NAME" && \
            cd "$DEP_NAME" && \
            git checkout "$DEP_COMMIT" && \
            git submodule update --init --recursive && \
            OPENSSL_INCLUDE_DIR="/usr/include/openssl" cmake . && \
            make && \
            make check && \
            echo "Successfully built dependency '$DEP_NAME'"; \
        else \
            echo "Invalid dependency configuration: $dep"; \
            exit 1; \
        fi; \
    done


RUN cd /opt && \
    git clone https://github.com/private-octopus/picoquic.git && \
    cd /opt/picoquic && \
    git checkout ${VERSION} && \
    cmake . && \
    make && \
    ./picoquic_ct || true

# Expose necessary ports
EXPOSE 4443
EXPOSE 8080

# Ensure the log directory exists
RUN mkdir -p /app/logs
RUN mkdir -p /opt/certs
RUN mkdir -p /opt/ticket

# Set entrypoint (can be overridden)
ENTRYPOINT [ "/bin/bash", "-l", "-c" ]