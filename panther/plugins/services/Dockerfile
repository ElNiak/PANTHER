FROM ubuntu:20.04

# TODOS - Question should we set '--not-install-recommends' -> might introduce issues 

ENV DEBIAN_FRONTEND=noninteractive
RUN ln -fs /usr/share/zoneinfo/UTC /etc/localtime && \
    apt-get update && \
    apt-get install --auto-remove --show-upgraded  -y \
    build-essential git cmake software-properties-common \
    openssl libssl-dev pkg-config python3 net-tools tcpdump iperf traceroute \
    wireshark tshark clang libcap2-bin iputils-ping iproute2 iperf3 netcat-openbsd curl dnsutils \
    wget sudo radare2 strace automake autoconf libtool 

# https://github.com/gperftools/gperftools
RUN git clone https://github.com/gperftools/gperftools
WORKDIR /gperftools
RUN ./autogen.sh
RUN ./configure
RUN make
RUN sudo make install
RUN apt-get install -y libunwind-dev google-perftools graphviz gv
RUN whereis libprofiler
RUN whereis libtcmalloc

WORKDIR /

# "yes" answer by 'dpkg-reconfigure wireshark-common' so you can run tshark as normal use
RUN yes yes | DEBIAN_FRONTEND=teletype dpkg-reconfigure wireshark-common

ARG USER_UID=1000
ARG USER_GID=1000
ARG USER_N=crochetch

RUN addgroup --gid ${USER_GID} ${USER_N} && \
    adduser --disabled-password --gecos '' --uid ${USER_UID} --gid ${USER_GID} ${USER_N} && \
    usermod -aG wireshark ${USER_N}

RUN usermod -aG wireshark root

# Give the user ownership of the /app directory (or any directories you need)
RUN mkdir -p /app
RUN chown -R ${USER_N}:${USER_N} /app
RUN chown -R ${USER_N}:${USER_N} /opt
