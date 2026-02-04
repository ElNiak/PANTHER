# syntax=docker/dockerfile:1
# =============================================================================
# PANTHER Runtime Base - Minimal production runtime (200MB)
# =============================================================================
FROM --platform=$TARGETPLATFORM ubuntu:20.04 AS panther-runtime-base

ARG BUILDPLATFORM
ARG TARGETPLATFORM
ARG TARGETOS=linux
ARG TARGETARCH

ENV DEBIAN_FRONTEND=noninteractive

# Platform info for debugging
RUN echo "Building on: $BUILDPLATFORM for: $TARGETPLATFORM ($TARGETOS/$TARGETARCH)"

# Essential runtime packages only
RUN --mount=type=cache,target=/var/cache/apt,id=runtime-$TARGETPLATFORM,sharing=locked \
    --mount=type=cache,target=/var/lib/apt,id=runtimelib-$TARGETPLATFORM,sharing=locked \
    --mount=type=tmpfs,target=/tmp \
    ln -fs /usr/share/zoneinfo/UTC /etc/localtime && \
    apt-get update && \
    apt-get install --fix-missing --auto-remove --show-upgraded --no-install-recommends -y \
    # Core runtime
    python3 python3-pip openssl ca-certificates \
    # Network basics
    net-tools tcpdump iperf iperf3 traceroute \
    iputils-ping iproute2 netcat-openbsd curl \
    # Wireshark runtime (fix for original error)
    wireshark-common tshark libcap2-bin \
    dnsutils \
    && rm -rf /var/lib/apt/lists/*

# Fix wireshark permissions (addresses original build error)
RUN groupadd -r pantheruser && useradd -r -g pantheruser pantheruser && \
    echo "wireshark-common wireshark-common/install-setuid boolean false" | debconf-set-selections && \
    dpkg-reconfigure -f noninteractive wireshark-common && \
    (groupadd wireshark || true) && \
    usermod -aG wireshark pantheruser

# Application directories
RUN mkdir -p /app /opt && \
    chown -R pantheruser:pantheruser /app /opt

# Runtime metadata
LABEL panther.base="runtime" \
      panther.size="~200MB" \
      panther.packages="python3,wireshark,tcpdump,iperf3,curl" \
      panther.security="wireshark-fixed,non-root-user"

USER pantheruser
WORKDIR /app
