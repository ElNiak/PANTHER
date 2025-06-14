FROM ubuntu:20.04

# Using --no-install-recommends to reduce image size and security surface

ENV DEBIAN_FRONTEND=noninteractive
RUN ln -fs /usr/share/zoneinfo/UTC /etc/localtime && \
    apt-get update && \
    apt-get install --auto-remove --show-upgraded --no-install-recommends -y \
    build-essential git cmake software-properties-common \
    openssl libssl-dev pkg-config python3 net-tools tcpdump iperf traceroute \
    wireshark tshark clang libcap2-bin iputils-ping iproute2 iperf3 netcat-openbsd curl dnsutils \
    wget sudo radare2 strace automake autoconf libtool valgrind

# https://github.com/gperftools/gperftools
RUN git clone https://github.com/gperftools/gperftools
WORKDIR /gperftools
RUN ./autogen.sh
RUN ./configure
RUN make
RUN make install
RUN apt-get install --no-install-recommends -y libunwind-dev google-perftools graphviz gv
RUN whereis libprofiler
RUN whereis libtcmalloc

WORKDIR /

# "yes" answer by 'dpkg-reconfigure wireshark-common' so you can run tshark as normal use
RUN yes yes | DEBIAN_FRONTEND=teletype dpkg-reconfigure wireshark-common

ARG USER_UID=1000
ARG USER_GID=1000
ARG USER_N=crochetch

# Create group and user more robustly
RUN if ! getent group ${USER_N} > /dev/null 2>&1; then \
        addgroup --gid ${USER_GID} ${USER_N} || echo "Failed to add group ${USER_N}"; \
    fi && \
    if ! id -u ${USER_N} > /dev/null 2>&1; then \
        adduser --disabled-password --gecos '' --uid ${USER_UID} --gid ${USER_GID} ${USER_N} || echo "Failed to add user ${USER_N}"; \
    fi && \
    if id -u ${USER_N} > /dev/null 2>&1; then \
        usermod -aG wireshark ${USER_N} || echo "Failed to add ${USER_N} to wireshark group"; \
    fi

RUN usermod -aG wireshark root

# Give the user ownership of the /app directory (or any directories you need)
# Create directories first before changing ownership
RUN mkdir -p /app /opt

# Use a more robust approach - check if user exists before chown
# This prevents failures if the user creation failed for some reason
RUN if id -u ${USER_N} > /dev/null 2>&1; then \
        chown -R ${USER_N}:${USER_N} /app || true && \
        chown -R ${USER_N}:${USER_N} /opt || true; \
    else \
        echo "Warning: User ${USER_N} does not exist, skipping chown"; \
    fi || true
