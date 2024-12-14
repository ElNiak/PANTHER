FROM panther_base_service_panther:latest

ENV DEBIAN_FRONTEND=noninteractive
# Define build arguments for version-specific configurations
ARG VERSION=master
ARG DEPENDENCIES="[]"  # JSON-formatted list of dependencies
ENV VERSION=${VERSION}
ENV DEPENDENCIES=${DEPENDENCIES}

# Perl stuff is for the picotls test code
RUN echo install Test::TCP | perl -MCPAN -
RUN echo install Scope::Guard | perl -MCPAN -

# Install jq for JSON parsing
RUN apt-get install --fix-missing -y jq 

USER ${USER_N}

# Function to parse and build dependencies
RUN git clone https://boringssl.googlesource.com/boringssl;  \
    cd boringssl; \
    git checkout 9fc1c33e9c21439ce5f87855a6591a9324e569fd; \
    git submodule init; \
    git submodule update; \
    cmake . &&  make 

ENV BORINGSSL=/src/boringssl/

RUN git clone https://github.com/litespeedtech/lsquic.git;  \
    cd lsquic;    \
    git checkout v4.0.9; \
    git submodule update --init; 

RUN cd /opt/lsquic && \
    cmake -DBORINGSSL_DIR=/src/boringssl/ .; \
    make; \
    make test || true

# Expose necessary ports
EXPOSE 4443
EXPOSE 8080

# Ensure the log directory exists
RUN mkdir -p /app/logs
RUN mkdir -p /opt/certs
RUN mkdir -p /opt/ticket

# Set entrypoint (can be overridden)
ENTRYPOINT [ "/bin/sh", "-l", "-c" ]