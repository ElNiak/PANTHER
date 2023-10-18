FROM alpine:latest
RUN apk add --no-cache \
        bsd-compat-headers \
        cmake \
        g++ \
        gcc \
        git \
        http-parser-dev \
        linux-headers \
        musl-dev \
        ninja \
        openssl \
        openssl-dev
RUN git config --global user.email "docker@example.com"
ADD . /src
WORKDIR /src/Debug
RUN cmake -GNinja -DDOCKER=True -DCMAKE_INSTALL_PREFIX=/dst ..
RUN ninja install

FROM alpine:latest
COPY --from=0 /dst /
COPY --from=0 /src/Debug/test/dummy.* /tls/
COPY --from=0 /src/test/interop.sh /bin
RUN apk add --no-cache openssl http-parser ethtool
EXPOSE 443/UDP
EXPOSE 4433/UDP
EXPOSE 4434/UDP
CMD ["/bin/server", "-i", "eth0", "-d", "/tmp", \
        "-c", "/tls/dummy.crt", "-k", "/tls/dummy.key"]
