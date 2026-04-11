# =============================================================================
# PANTHER Service - Standard Dockerfile (No BuildKit Required)
# Multi-stage build compatible with standard Docker (no --mount syntax)
# For BuildKit with caching, use Dockerfile.buildkit instead
# =============================================================================

ARG RUNTIME_MODE=minimal

# =============================================================================
# STAGE 1: BUILDER - Build tools and dependencies
# =============================================================================
FROM ubuntu:20.04 AS builder

ENV DEBIAN_FRONTEND=noninteractive

RUN ln -fs /usr/share/zoneinfo/UTC /etc/localtime

# Essential build tools and libraries (including pyenv dependencies)
RUN apt-get update && \
    apt-get install --fix-missing --auto-remove --show-upgraded --no-install-recommends -y \
    build-essential git cmake software-properties-common \
    openssl libssl-dev pkg-config \
    clang automake autoconf libtool \
    wget curl sudo \
    libc6-dev libdw1 libelf1 libunwind-dev \
    net-tools tcpdump iperf iperf3 traceroute \
    wireshark-common wireshark tshark libcap2-bin \
    iputils-ping iproute2 netcat-openbsd \
    curl dnsutils jq ca-certificates \
    libffi-dev libbz2-dev libreadline-dev libsqlite3-dev \
    llvm libncurses5-dev libncursesw5-dev xz-utils tk-dev liblzma-dev && \
    rm -rf /var/lib/apt/lists/*

# Install pyenv and Python 3.10.12
# Use bash explicitly — pyenv init outputs bash-specific syntax that dash cannot parse
SHELL ["/bin/bash", "-c"]
RUN curl https://pyenv.run | bash && \
    echo 'export PYENV_ROOT="$HOME/.pyenv"' >> ~/.bashrc && \
    echo 'export PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.bashrc && \
    echo 'eval "$(pyenv init -)"' >> ~/.bashrc && \
    echo 'eval "$(pyenv virtualenv-init -)"' >> ~/.bashrc && \
    export PYENV_ROOT="$HOME/.pyenv" && \
    export PATH="$PYENV_ROOT/bin:$PATH" && \
    eval "$(pyenv init -)" && \
    eval "$(pyenv virtualenv-init -)" && \
    pyenv install 3.10.12 && \
    pyenv global 3.10.12
SHELL ["/bin/sh", "-c"]

# Create symlinks for python commands
RUN ln -sf "$HOME/.pyenv/shims/python3.10" /usr/local/bin/python3.10 && \
    ln -sf "$HOME/.pyenv/shims/python3" /usr/local/bin/python3 && \
    ln -sf "$HOME/.pyenv/shims/python" /usr/local/bin/python && \
    python3 -V && which python3

# Set PATH for pyenv in environment
ENV PYENV_ROOT=/root/.pyenv
ENV PATH=$PYENV_ROOT/shims:$PYENV_ROOT/bin:$PATH

# Build gperftools from source (needed for profiling)
RUN git clone https://github.com/gperftools/gperftools /tmp/gperftools

WORKDIR /tmp/gperftools

RUN ./autogen.sh && \
    ./configure && \
    make && \
    make install

RUN whereis libprofiler && whereis libtcmalloc

WORKDIR /
RUN mkdir -p /app /opt

# =============================================================================
# STAGE 2: DEBUG - BUILDER + debugging tools
# =============================================================================
FROM builder AS debug

ENV DEBIAN_FRONTEND=noninteractive

# Install debugging tools
RUN apt-get update && \
    apt-get install --no-install-recommends -y \
    gdb valgrind strace util-linux && \
    rm -rf /var/lib/apt/lists/*

# Copy built gperftools for debugging
COPY --from=builder /usr/local/lib/libprofiler.* /usr/local/lib/
COPY --from=builder /usr/local/lib/libtcmalloc.* /usr/local/lib/

# =============================================================================
# STAGE 3: PROFILE - DEBUG + performance profiling tools
# =============================================================================
FROM debug AS profile

ENV DEBIAN_FRONTEND=noninteractive

# Install performance profiling tools
RUN apt-get update && \
    apt-get install --no-install-recommends -y \
    linux-tools-generic linux-tools-common linux-cloud-tools-common \
    radare2 google-perftools graphviz gv && \
    rm -rf /var/lib/apt/lists/*

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
# Includes pyenv dependencies for Python installation
RUN apt-get update && \
    apt-get install --fix-missing --auto-remove --show-upgraded --no-install-recommends -y \
    openssl ca-certificates \
    git jq sudo \
    net-tools tcpdump iperf iperf3 traceroute \
    wireshark-common wireshark tshark libcap2-bin \
    iputils-ping iproute2 netcat-openbsd \
    curl dnsutils software-properties-common \
    automake autoconf libtool pkg-config libssl-dev \
    cmake build-essential \
    libffi-dev libbz2-dev libreadline-dev libsqlite3-dev \
    llvm libncurses5-dev libncursesw5-dev xz-utils tk-dev liblzma-dev && \
    rm -rf /var/lib/apt/lists/*

# Install pyenv and Python 3.10.12
# Use bash explicitly — pyenv init outputs bash-specific syntax that dash cannot parse
SHELL ["/bin/bash", "-c"]
RUN curl https://pyenv.run | bash && \
    echo 'export PYENV_ROOT="$HOME/.pyenv"' >> ~/.bashrc && \
    echo 'export PATH="$PYENV_ROOT/bin:$PATH"' >> ~/.bashrc && \
    echo 'eval "$(pyenv init -)"' >> ~/.bashrc && \
    echo 'eval "$(pyenv virtualenv-init -)"' >> ~/.bashrc && \
    export PYENV_ROOT="$HOME/.pyenv" && \
    export PATH="$PYENV_ROOT/bin:$PATH" && \
    eval "$(pyenv init -)" && \
    eval "$(pyenv virtualenv-init -)" && \
    pyenv install 3.10.12 && \
    pyenv global 3.10.12
SHELL ["/bin/sh", "-c"]

# Create symlinks for python commands
RUN ln -sf "$HOME/.pyenv/shims/python3.10" /usr/local/bin/python3.10 && \
    ln -sf "$HOME/.pyenv/shims/python3" /usr/local/bin/python3 && \
    ln -sf "$HOME/.pyenv/shims/python" /usr/local/bin/python && \
    python3 -V && which python3

# Set PATH for pyenv in environment
ENV PYENV_ROOT=/root/.pyenv
ENV PATH=$PYENV_ROOT/shims:$PYENV_ROOT/bin:$PATH

# Configure wireshark for non-root usage (PANTHER protocol testing requirement)
RUN yes yes | DEBIAN_FRONTEND=teletype dpkg-reconfigure wireshark-common && \
    usermod -aG wireshark root

# Create application directories
RUN mkdir -p /app /opt /app/logs /app/certs /app/data

# =============================================================================
# FINAL STAGE: Runtime mode selection
# =============================================================================
FROM ${RUNTIME_MODE} AS final

ENV DEBIAN_FRONTEND=noninteractive

# Labels for runtime identification
ARG RUNTIME_MODE=minimal
LABEL runtime.mode="${RUNTIME_MODE}"
LABEL runtime.description="PANTHER service execution environment"
LABEL runtime.capabilities.network="wireshark,tshark,tcpdump,iperf3"
LABEL runtime.capabilities.debug="gdb,valgrind,strace"
LABEL runtime.capabilities.profile="perf,gperftools,radare2"
LABEL dockerfile.type="legacy"
LABEL dockerfile.buildkit_required="false"

WORKDIR /app

# Health check for runtime validation
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python3 -c "import sys; sys.exit(0)" || exit 1
