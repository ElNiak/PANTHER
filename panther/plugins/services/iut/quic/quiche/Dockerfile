ARG BASE_IMAGE=panther_base_service:latest
FROM ${BASE_IMAGE}

ENV DEBIAN_FRONTEND=noninteractive
# Define build arguments for version-specific configurations
ARG VERSION=master
ARG DEPENDENCIES="[]"  # JSON-formatted list of dependencies
ARG USER_N=root  # Define USER_N with default value
ENV VERSION=${VERSION}
ENV DEPENDENCIES=${DEPENDENCIES}



# Install jq for JSON parsing
RUN apt-get install --fix-missing --no-install-recommends -y jq

USER ${USER_N}

# Function to parse and build dependencies
RUN wget https://github.com/Kitware/CMake/releases/download/v3.12.4/cmake-3.12.4-Linux-x86_64.sh
RUN chmod +x cmake-3.12.4-Linux-x86_64.sh
RUN mkdir /opt/cmake
RUN bash cmake-3.12.4-Linux-x86_64.sh --skip-license --prefix=/opt/cmake
RUN ln -s /opt/cmake/bin/cmake /usr/local/bin/cmake
RUN cmake --version

RUN curl https://sh.rustup.rs -sSf | sh -s -- -y
ENV PATH="/root/.cargo/bin:${PATH}"



WORKDIR /opt
RUN git clone https://github.com/cloudflare/quiche

WORKDIR /opt/quiche
RUN git checkout 4bda0917dd5aa535f39214063ee85c2cad00ceb2 && \
    git submodule update --init

COPY file_to_change/packet_0.9.0.rs /opt/quiche/src/packet.rs

RUN cargo build --examples && \
    cargo test || true

# Expose necessary ports
EXPOSE 4443
EXPOSE 8080

# Ensure the log directory exists
RUN mkdir -p /app/logs
RUN mkdir -p /opt/certs
RUN mkdir -p /opt/ticket

# Set entrypoint (can be overridden)
ENTRYPOINT [ "/bin/bash", "-l", "-c" ]
