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
    git clone https://github.com/ElNiak/picoquic.git && \
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
ENTRYPOINT [ "/bin/sh", "-l", "-c" ]