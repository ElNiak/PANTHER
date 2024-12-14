FROM panther_base_service_panther:latest

ENV DEBIAN_FRONTEND=noninteractive
# Define build arguments for version-specific configurations
ARG VERSION=master
ARG DEPENDENCIES="[]"  # JSON-formatted list of dependencies
ENV VERSION=${VERSION}
ENV DEPENDENCIES=${DEPENDENCIES}



# Install jq for JSON parsing
RUN apt-get install --fix-missing -y jq 

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



RUN cd /opt && \
    git clone https://github.com/quinn-rs/quinn.git\
    cd /opt/quinn && \
    git checkout bb02a12a8435a7732a1d762783eeacbb7e50418e #0.7.0 # master # 0.9.0 for quic client ! TODO\
    git submodule update --init --recursive;

# ADD file_to_change/packet_0.9.0.rs /opt/quiche/src/packet.rs

RUN cd /opt/quinn && \
    cargo build --examples \
    cargo test || true

# Expose necessary ports
EXPOSE 4443
EXPOSE 8080

# Ensure the log directory exists
RUN mkdir -p /app/logs
RUN mkdir -p /opt/certs
RUN mkdir -p /opt/ticket

# Set entrypoint (can be overridden)
ENTRYPOINT [ "/bin/sh", "-l", "-c" ]