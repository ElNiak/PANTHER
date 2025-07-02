# =============================================================================
# PANTHER Service - 3-Stage Multi-Target Dockerfile
# BUILDER -> DEBUG -> MINIMAL runtime environments with execution tools
# =============================================================================

ARG RUNTIME_MODE=minimal

# =============================================================================
# STAGE 1: BUILDER - Build tools and dependencies
# =============================================================================
FROM ubuntu:20.04 AS builder

ENV DEBIAN_FRONTEND=noninteractive
RUN ln -fs /usr/share/zoneinfo/UTC /etc/localtime

# Essential build tools and libraries
RUN apt-get update && \
    apt-get install --fix-missing --auto-remove --show-upgraded --no-install-recommends -y \
    build-essential git cmake software-properties-common \
    openssl libssl-dev pkg-config python3 \
    clang automake autoconf libtool \
    wget curl sudo \
    libc6-dev libdw1 libelf1 libunwind-dev

# Build gperftools from source (needed for profiling)
RUN git clone https://github.com/gperftools/gperftools /tmp/gperftools
WORKDIR /tmp/gperftools
RUN ./autogen.sh && \
    ./configure && \
    make && \
    make install

WORKDIR /
RUN mkdir -p /app /opt

# =============================================================================
# STAGE 2: DEBUG - MINIMAL + debugging tools
# =============================================================================
FROM builder AS debug

# Install debugging tools
RUN apt-get install --no-install-recommends -y \
    gdb valgrind strace util-linux

# Copy built gperftools for debugging
COPY --from=builder /usr/local/lib/libprofiler.* /usr/local/lib/
COPY --from=builder /usr/local/lib/libtcmalloc.* /usr/local/lib/

# =============================================================================
# STAGE 3: PROFILE - DEBUG + performance profiling tools
# =============================================================================
FROM debug AS profile

# Install performance profiling tools
RUN apt-get install --no-install-recommends -y \
    linux-tools-generic linux-tools-common linux-cloud-tools-common \
    radare2 google-perftools graphviz gv

# Update library cache for gperftools
RUN ldconfig

# Verify profiling tools installation
RUN whereis libprofiler && whereis libtcmalloc

# =============================================================================
# STAGE 4: MINIMAL - Core runtime + network analysis (PANTHER requirement)
# =============================================================================
FROM ubuntu:20.04 AS minimal

ENV DEBIAN_FRONTEND=noninteractive
RUN ln -fs /usr/share/zoneinfo/UTC /etc/localtime

# Core runtime and network analysis tools (required for PANTHER protocol testing)
RUN apt-get update && \
    apt-get install --fix-missing --auto-remove --show-upgraded --no-install-recommends -y \
    python3 openssl \
    net-tools tcpdump iperf iperf3 traceroute \
    wireshark tshark libcap2-bin \
    iputils-ping iproute2 netcat-openbsd \
    curl dnsutils software-properties-common git sudo \
    jq automake autoconf libtool pkg-config libssl-dev \
    cmake build-essential

# Configure wireshark for non-root usage (PANTHER protocol testing requirement)
RUN yes yes | DEBIAN_FRONTEND=teletype dpkg-reconfigure wireshark-common && \
    usermod -aG wireshark root

# Create application directories
RUN mkdir -p /app /opt

# =============================================================================
# FINAL STAGE: Runtime mode selection
# =============================================================================
FROM ${RUNTIME_MODE} AS final


# Labels for runtime identification
ARG RUNTIME_MODE=minimal
LABEL runtime.mode="${RUNTIME_MODE}"
LABEL runtime.description="PANTHER service execution environment"
LABEL runtime.capabilities.network="wireshark,tshark,tcpdump,iperf3"
LABEL runtime.capabilities.debug="gdb,valgrind,strace"
LABEL runtime.capabilities.profile="perf,gperftools,radare2"

WORKDIR /app
