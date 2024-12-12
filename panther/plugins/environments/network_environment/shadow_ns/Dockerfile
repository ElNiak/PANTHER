FROM ubuntu:20.04 as panther_shadow_ns

SHELL ["/bin/bash", "-c"]
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y git \
                                    cmake \
                                    findutils \
                                    libclang-dev \
                                    libc-dbg \
                                    libglib2.0-0 \
                                    libglib2.0-dev \
                                    make \
                                    netbase \
                                    python3 \
                                    python3-networkx \
                                    xz-utils \
                                    util-linux \
                                    gcc \
                                    g++ \  
                                    wget \
                                    curl 

# rustup: https://rustup.rs
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
ENV PATH="/root/.local/bin:/root/.cargo/bin:${PATH}"

ENV CONTAINER ubuntu:20.04
ENV BUILDTYPE release
ENV RUSTPROFILE minimal

RUN git clone https://github.com/ElNiak/shadow.git && \
    cd /shadow && \
    git checkout rebasing_test
RUN cd shadow; \
    ./setup build --clean --test  && \
    # ./setup test && # This command is not working
    ./setup install 
#
RUN apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*


