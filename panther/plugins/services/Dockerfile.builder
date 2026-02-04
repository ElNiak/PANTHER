# syntax=docker/dockerfile:1

# =============================================================================
# PANTHER Builder Stage - Multi-Platform Build Environment
# Cross-platform build with automatic platform detection and gperftools
# =============================================================================

# BuildKit automatic platform arguments
ARG BUILDPLATFORM=linux/amd64
ARG TARGETPLATFORM=linux/amd64
ARG TARGETOS=linux
ARG TARGETARCH=amd64
ARG BUILDVARIANT

# Use Ubuntu 20.04 targeting amd64
FROM --platform=linux/amd64 ubuntu:20.04 AS builder

ENV DEBIAN_FRONTEND=noninteractive

# Platform-aware package installation with enhanced security
RUN --mount=type=cache,target=/var/cache/apt,id=apt-${TARGETPLATFORM},sharing=locked \
    --mount=type=cache,target=/var/lib/apt,id=aptlib-${TARGETPLATFORM},sharing=locked \
    --mount=type=tmpfs,target=/tmp \
    ln -fs /usr/share/zoneinfo/UTC /etc/localtime && \
    apt-get update && \
    apt-get install --fix-missing --auto-remove --show-upgraded --no-install-recommends -y \
    build-essential git cmake software-properties-common \
    openssl libssl-dev pkg-config python3 \
    clang automake autoconf libtool \
    wget curl sudo \
    libc6-dev libdw1 libelf1 libunwind-dev \
    net-tools tcpdump iperf iperf3 traceroute \
    wireshark tshark libcap2-bin \
    iputils-ping iproute2 netcat-openbsd \
    curl dnsutils automake autoconf libtool pkg-config libssl-dev \
    cmake build-essential

# Install cross-compilation tools based on target architecture
RUN --mount=type=cache,target=/var/cache/apt,id=crossbuild-${TARGETPLATFORM},sharing=locked \
    case "$TARGETARCH" in \
        arm64) \
            apt-get update && \
            apt-get install -y gcc-aarch64-linux-gnu g++-aarch64-linux-gnu && \
            rm -rf /var/lib/apt/lists/* ;; \
        arm) \
            apt-get update && \
            apt-get install -y gcc-arm-linux-gnueabihf g++-arm-linux-gnueabihf && \
            rm -rf /var/lib/apt/lists/* ;; \
        amd64) \
            echo "Native compilation for amd64" ;; \
        *) \
            echo "Unsupported target architecture: $TARGETARCH" && exit 1 ;; \
    esac

# Set cross-compilation environment variables
ENV CC_aarch64_unknown_linux_gnu=aarch64-linux-gnu-gcc \
    CXX_aarch64_unknown_linux_gnu=aarch64-linux-gnu-g++ \
    CC_arm_unknown_linux_gnueabihf=arm-linux-gnueabihf-gcc \
    CXX_arm_unknown_linux_gnueabihf=arm-linux-gnueabihf-g++

# Add platform-specific CMake environment (for downstream usage)
RUN case "${TARGETARCH:-amd64}" in \
        "amd64") \
            echo 'export CMAKE_ARGS="-DCMAKE_SYSTEM_PROCESSOR=x86_64 -DCMAKE_C_COMPILER=gcc -DCMAKE_CXX_COMPILER=g++"' >> /etc/environment \
            ;; \
        "arm64") \
            echo 'export CMAKE_ARGS="-DCMAKE_SYSTEM_PROCESSOR=aarch64 -DCMAKE_C_COMPILER=aarch64-linux-gnu-gcc -DCMAKE_CXX_COMPILER=aarch64-linux-gnu-g++"' >> /etc/environment \
            ;; \
        "arm") \
            echo 'export CMAKE_ARGS="-DCMAKE_SYSTEM_PROCESSOR=arm -DCMAKE_C_COMPILER=arm-linux-gnueabihf-gcc -DCMAKE_CXX_COMPILER=arm-linux-gnueabihf-g++"' >> /etc/environment \
            ;; \
        *) \
            echo 'export CMAKE_ARGS="-DCMAKE_SYSTEM_PROCESSOR=x86_64"' >> /etc/environment \
            ;; \
    esac

# Git clone with platform-specific build cache isolation
RUN --mount=type=cache,target=/tmp/git-cache,id=git-${TARGETPLATFORM},sharing=locked \
    --mount=type=cache,target=/tmp/build-cache,id=build-${TARGETPLATFORM},sharing=private \
    git clone https://github.com/gperftools/gperftools /tmp/git-cache/gperftools || \
    (cd /tmp/git-cache/gperftools && git pull) && \
    cp -r /tmp/git-cache/gperftools /gperftools

WORKDIR /gperftools

# Build with platform-specific cache for compiled objects
RUN --mount=type=cache,target=/gperftools/.libs,id=gperflibs-${TARGETPLATFORM},sharing=locked \
    --mount=type=cache,target=/gperftools/src/.libs,id=gperfsrc-${TARGETPLATFORM},sharing=locked \
    ./autogen.sh && \
    ./configure && \
    make && \
    make install

RUN whereis libprofiler && whereis libtcmalloc

WORKDIR /
RUN mkdir -p /app /opt

# Metadata for builder stage
LABEL panther.stage="builder" \
      panther.size="~1.5GB" \
      panther.purpose="cross-platform-build-with-gperftools" \
      panther.packages="build-essential,cmake,gperftools,cross-compilers"
