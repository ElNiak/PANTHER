# syntax=docker/dockerfile:1
# =============================================================================
# PANTHER Build Base - Dev + full compilation toolchain (1.2GB)
# =============================================================================
FROM panther-dev-base AS panther-build-base

USER root

# Full compilation toolchain
RUN --mount=type=cache,target=/var/cache/apt,id=build-$TARGETPLATFORM,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,id=buildlib-$TARGETPLATFORM,sharing=locked \
    apt-get update && \
    apt-get install --fix-missing --auto-remove --show-upgraded --no-install-recommends -y \
    # Complete build environment
    build-essential clang \
    autoconf automake libtool \
    # Advanced development
    ninja-build \
    # Library development
    libssl-dev pkg-config \
    libc6-dev libdw1 libelf1 libunwind-dev \
    # Cross-compilation support
    gcc-aarch64-linux-gnu g++-aarch64-linux-gnu \
    gcc-arm-linux-gnueabihf g++-arm-linux-gnueabihf && \
    rm -rf /var/lib/apt/lists/*

# Cross-compilation environment
ENV CC_aarch64_unknown_linux_gnu=aarch64-linux-gnu-gcc \
    CXX_aarch64_unknown_linux_gnu=aarch64-linux-gnu-g++ \
    CC_arm_unknown_linux_gnueabihf=arm-linux-gnueabihf-gcc \
    CXX_arm_unknown_linux_gnueabihf=arm-linux-gnueabihf-g++

# Build metadata
LABEL panther.base="build" \
      panther.size="~1.2GB" \
      panther.packages="dev+build-essential,clang,autotools" \
      panther.capabilities="full-compilation,cross-compilation"

USER pantheruser
