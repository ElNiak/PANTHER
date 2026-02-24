FROM --platform=linux/amd64 ubuntu:20.04 as panther_shadow_ns

SHELL ["/bin/bash", "-c"]
ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    cmake \
    findutils \
    golang-go \
    iproute2 \
    libc-dbg \
    libclang-dev \
    libglib2.0-0 \
    libglib2.0-dev \
    make \
    netbase \
    pkg-config \
    python3 \
    python3-networkx \
    python3-yaml \
    xz-utils \
    util-linux \
    git \
    gcc \
    g++ \
    wget \
    curl \
    rsync

# rustup: https://rustup.rs
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y --no-modify-path --default-toolchain none --profile minimal
ENV PATH="/root/.local/bin:/root/.cargo/bin:${PATH}"


ENV CONTAINER ubuntu:20.04
ENV BUILDTYPE release
ENV RUSTPROFILE minimal

RUN git clone https://github.com/ElNiak/shadow.git && \
    cd /shadow && \
    git checkout rebasing_test

RUN ln -s shadow/ci/rust-toolchain-stable.toml rust-toolchain.toml; rustup toolchain install

RUN go install -buildmode=shared -linkshared std

# Build Shadow without tests (tests can be flaky and cause build failures)
# Only build the core Shadow functionality, not the tests
RUN cd shadow && ./setup build --clean

RUN cd shadow; ./setup install
#
    # ./setup test && # This command is not working # --test


RUN apt-get clean && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*
