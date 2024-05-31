FROM ubuntu:20.04
ENV DEBIAN_FRONTEND=noninteractive
# if this line is not present, it cannot find GCC, even when using apt-get update below this command
RUN apt update
RUN apt-get update 

# install dependencies
RUN apt-get install -y wget tar git gcc g++
RUN apt-get install -y --fix-missing         \
        cmake                    \
        libboost-all-dev         \
        libevent-dev             \
        libdouble-conversion-dev \
        libgoogle-glog-dev       \
        libgflags-dev            \
        libiberty-dev            \
        liblz4-dev               \
        liblzma-dev
RUN apt-get install -y --fix-missing        \
        libsnappy-dev            \
        zlib1g-dev               \
        binutils-dev             \
        libjemalloc-dev          \
        libssl-dev               \
        pkg-config               \
        libsodium-dev

# clone mvfst
RUN git clone https://github.com/facebookincubator/mvfst

WORKDIR mvfst

# modify mvfst to export TLS keys
COPY tls-keys-patch.diff /mvfst/
RUN git checkout 36111c1 && git apply tls-keys-patch.diff

# build and install mvfst
RUN apt-get -y install sudo
RUN bash build_helper.sh

COPY generic /mvfst/quic/samples/generic
COPY samples-build-patch.diff ./
RUN git apply samples-build-patch.diff

WORKDIR /mvfst/quic/samples
RUN cmake .
RUN make

WORKDIR /mvfst/_build/build/quic/samples
RUN make -j 8

RUN mkdir /mvfst-generic
RUN cp generic /mvfst-generic/

COPY run_endpoint.sh /
RUN chmod +x /run_endpoint.sh

WORKDIR /logs

ENTRYPOINT [ "/run_endpoint.sh" ]
