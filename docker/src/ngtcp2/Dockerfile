FROM ubuntu:20.04 as build
ENV DEBIAN_FRONTEND=noninteractive
WORKDIR /

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        git g++ make binutils autoconf automake autotools-dev libtool \
        pkg-config libev-dev libjemalloc-dev \
        ca-certificates mime-support && \
    git clone --depth 1 -b OpenSSL_1_1_1g-quic-draft-29 https://github.com/tatsuhiro-t/openssl && \
    cd openssl && ./config enable-tls1_3 --openssldir=/etc/ssl && make -j$(nproc) && make install_sw && cd .. && \
    git clone --branch draft-29 --depth 1 https://github.com/ngtcp2/nghttp3 && \
    cd nghttp3 && autoreconf -i && \
    ./configure --enable-lib-only && \
    make -j$(nproc) && make install-strip && cd ..

RUN git clone  --branch draft-29 --depth 1 https://github.com/ngtcp2/ngtcp2

RUN cd ngtcp2 && autoreconf -i && \
    ./configure \
        LIBTOOL_LDFLAGS="-static-libtool-libs" \
        LIBS="-ldl -pthread" \
        OPENSSL_LIBS="-l:libssl.a -l:libcrypto.a" \
        LIBEV_LIBS="-l:libev.a" \
        JEMALLOC_LIBS="-l:libjemalloc.a" && \
    make -j$(nproc) && \
    strip examples/client examples/server && \
    cp examples/client examples/server /usr/local/bin && \
    cd .. && \
    rm -rf /var/log/*

COPY generic-client-server /generic-client-server

WORKDIR /generic-client-server

RUN make

RUN mkdir /certs /logs /ngtcp2-generic

RUN cp generic-client /ngtcp2-generic/generic-http3-client
RUN cp generic-server /ngtcp2-generic/generic-http3-server

COPY run_endpoint.sh /
RUN chmod +x /run_endpoint.sh

WORKDIR /logs

ENTRYPOINT ["/run_endpoint.sh"]
