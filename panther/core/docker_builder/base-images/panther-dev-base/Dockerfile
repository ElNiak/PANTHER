# syntax=docker/dockerfile:1
# =============================================================================
# PANTHER Development Base - Runtime + common dev tools (600MB)
# =============================================================================
FROM panther-runtime-base AS panther-dev-base

USER root

# Development and debugging tools
RUN --mount=type=cache,target=/var/cache/apt,id=dev-$TARGETPLATFORM,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,id=devlib-$TARGETPLATFORM,sharing=locked \
    apt-get update && \
    apt-get install --fix-missing --auto-remove --show-upgraded --no-install-recommends -y \
    # Version control and download
    git wget curl \
    # Basic build tools
    cmake pkg-config \
    # Essential debugging
    gdb valgrind strace \
    # Python development
    python3-dev python3-setuptools \
    # Network analysis enhancement
    wireshark && \
    rm -rf /var/lib/apt/lists/*

# Development environment setup
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# Development metadata
LABEL panther.base="dev" \
      panther.size="~600MB" \
      panther.packages="runtime+git,cmake,gdb,valgrind,strace" \
      panther.capabilities="development,debugging,basic-analysis"

USER pantheruser
