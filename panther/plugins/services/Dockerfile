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

# "yes" answer by 'dpkg-reconfigure wireshark-common' so you can run tshark as normal user
RUN yes yes | DEBIAN_FRONTEND=teletype dpkg-reconfigure wireshark-common

# Add root to wireshark group for packet capture capabilities
RUN usermod -aG wireshark root

# Create application directories
RUN mkdir -p /app /opt
