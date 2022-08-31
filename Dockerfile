FROM ubuntu:18.04  

# Install dependencies

RUN apt-get update && apt-get -y install alien
RUN DEBIAN_FRONTEND="noninteractive" apt-get install -y apt-utils git
RUN DEBIAN_FRONTEND="noninteractive" apt-get install -y iptables
RUN DEBIAN_FRONTEND="noninteractive" apt-get install -y sudo

ADD QUIC-Ivy /QUIC-Ivy 
ADD scripts /scripts

RUN DEBIAN_FRONTEND="noninteractive" apt-get install --fix-missing  -y git python3 python3-dev python3-pip build-essential 
RUN DEBIAN_FRONTEND="noninteractive" apt-get --fix-missing  -y install tzdata curl wget tar 
RUN DEBIAN_FRONTEND="noninteractive" apt-get install  --fix-missing  -y python2.7 python-pip g++ cmake python-ply python-pygraphviz git python-tk tix gperf pkg-config libssl-dev lsof
RUN DEBIAN_FRONTEND="noninteractive" apt-get install  --fix-missing  -y doxygen pkg-config faketime libscope-guard-perl libtest-tcp-perl libbrotli-dev
RUN DEBIAN_FRONTEND="noninteractive" apt-get install  --fix-missing  -y libev-dev libhttp-parser-dev libbsd-dev snapd
RUN DEBIAN_FRONTEND="noninteractive" apt-get install  --fix-missing  -y cmake wireshark tshark rand
RUN DEBIAN_FRONTEND="noninteractive" apt-get install  --fix-missing  -y binutils autoconf automake autotools-dev libtool pkg-config libev-dev libjemalloc-dev ca-certificates mime-support
RUN DEBIAN_FRONTEND="noninteractive" apt-get install  --fix-missing  -y libboost-all-dev libevent-dev libdouble-conversion-dev libgoogle-glog-dev libgflags-dev libiberty-dev liblz4-dev liblzma-dev
RUN DEBIAN_FRONTEND="noninteractive" apt-get install  --fix-missing  -y libsnappy-dev zlib1g-dev binutils-dev libjemalloc-dev libsodium-dev
RUN DEBIAN_FRONTEND="noninteractive" apt-get install  --fix-missing  -y git python3 python3-dev python3-pip build-essential libffi-dev python-dev cargo
RUN DEBIAN_FRONTEND="noninteractive" apt-get install  --fix-missing  -y build-essential software-properties-common zlib1g-dev libevent-dev
RUN DEBIAN_FRONTEND="noninteractive" apt-get install  --fix-missing  -y python python-pip g++ cmake python-ply python-pygraphviz git python-tk tix pkg-config libssl-dev # TODO
RUN DEBIAN_FRONTEND="noninteractive" apt-get install  --fix-missing  -y libunwind-dev
RUN DEBIAN_FRONTEND="noninteractive" apt-get install  --fix-missing  -y libssl-dev # openssl

RUN DEBIAN_FRONTEND="noninteractive" apt install --fix-missing  -y bridge-utils

RUN DEBIAN_FRONTEND="noninteractive" snap install cmake --classic
RUN DEBIAN_FRONTEND="noninteractive" apt-get install cmake
RUN DEBIAN_FRONTEND="noninteractive" cmake --version
RUN DEBIAN_FRONTEND="noninteractive" /usr/bin/cmake --version

RUN pip3 install progressbar2

RUN DEBIAN_FRONTEND="noninteractive" curl -fsSL https://bootstrap.pypa.io/pip/3.5/get-pip.py | python3.5

WORKDIR /QUIC-Ivy

RUN git submodule update --init --recursive
RUN git submodule update --recursive

RUN DEBIAN_FRONTEND="noninteractive" git checkout quic-rfc9000 # rfc9000 # quic_29 
RUN DEBIAN_FRONTEND="noninteractive" git submodule update --init --recursive
RUN DEBIAN_FRONTEND="noninteractive" git submodule update --recursive
RUN DEBIAN_FRONTEND="noninteractive" git config --global --add safe.directory $PROOTPATH/QUIC-Ivy/submodules/picotls

RUN DEBIAN_FRONTEND="noninteractive" mkdir doc/examples/quic/build
RUN DEBIAN_FRONTEND="noninteractive" mkdir doc/examples/quic/test/temp

RUN DEBIAN_FRONTEND="noninteractive" rm -r /usr/local/lib/python2.7/dist-packages && sudo mkdir /usr/local/lib/python2.7/dist-packages
RUN DEBIAN_FRONTEND="noninteractive" pip2 install pexpect chardet
RUN DEBIAN_FRONTEND="noninteractive" pip2 install gperf pandas scandir
RUN DEBIAN_FRONTEND="noninteractive" pip2 install ply
RUN DEBIAN_FRONTEND="noninteractive" python3 -m pip install pexpect chardet
RUN DEBIAN_FRONTEND="noninteractive" python3 -m pip install gperf pandas scandir
RUN DEBIAN_FRONTEND="noninteractive" python3 -m pip install ply
RUN DEBIAN_FRONTEND="noninteractive" pip install pexpect chardet
RUN DEBIAN_FRONTEND="noninteractive" pip install gperf pandas scandir
RUN DEBIAN_FRONTEND="noninteractive" pip install ply
RUN DEBIAN_FRONTEND="noninteractive" pip3 install pexpect chardet
RUN DEBIAN_FRONTEND="noninteractive" pip3 install gperf pandas scandir

WORKDIR /QUIC-Ivy/submodules/picotls
RUN DEBIAN_FRONTEND="noninteractive" git checkout 047c5fe20bb9ea91c1caded8977134f19681ec76

WORKDIR /QUIC-Ivy

RUN DEBIAN_FRONTEND="noninteractive" pip3 install ply

RUN DEBIAN_FRONTEND="noninteractive" python2.7 build_submodules.py
RUN DEBIAN_FRONTEND="noninteractive" pip2 install ms-ivy==1.8.23 #global install


ENV PATH="/root/.cargo/bin:${PATH}"
