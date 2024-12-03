FROM ubuntu:20.04 as panther_shadow_ns
WORKDIR /
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
                                    wget

# rustup: https://rustup.rs
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh


RUN git clone https://github.com/ElNiak/shadow.git && cd /shadow && git checkout rebasing_test

WORKDIR /shadow

ENV CC gcc
ENV CONTAINER ubuntu:20.04
ENV BUILDTYPE release
ENV RUSTPROFILE minimal
ENV PATH="/root/.local/bin:${PATH}"

RUN wget https://github.com/Kitware/CMake/releases/download/v3.26.4/cmake-3.26.4-linux-x86_64.tar.gz
RUN tar xzf cmake-3.26.4-linux-x86_64.tar.gz

WORKDIR /shadow
RUN ci/container_scripts/install_deps.sh && ci/container_scripts/install_extra_deps.sh

ENV PATH="/shadow/cmake-3.26.4-linux-x86_64/bin:/root/.cargo/bin:${PATH}"
RUN ci/container_scripts/build_and_install.sh

# Clean up
RUN apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*
RUN rm cmake-3.26.4-linux-x86_64.tar.gz

WORKDIR /
