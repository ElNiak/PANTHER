ARG BASE_IMAGE=panther_base_service:latest
FROM frrouting/frr:v8.4.1 AS frr

FROM ${BASE_IMAGE}

ARG VERSION=master
ARG DEPENDENCIES="[]"

# Copy FRRouting binaries, libs, and config from the official image
COPY --from=frr /usr/lib/frr/ /usr/lib/frr/
COPY --from=frr /usr/bin/vtysh /usr/bin/vtysh
COPY --from=frr /etc/frr/ /etc/frr/
COPY --from=frr /usr/lib/libfrr* /usr/lib/
COPY --from=frr /usr/lib/libyang.so* /usr/lib/
COPY --from=frr /usr/lib/libcrypto.so* /usr/lib/

# Enable bgpd and zebra daemons
RUN sed -i 's/bgpd=no/bgpd=yes/' /etc/frr/daemons && \
    sed -i 's/zebra=no/zebra=yes/' /etc/frr/daemons && \
    ldconfig

WORKDIR /etc/frr

ENTRYPOINT [ "/bin/bash", "-l", "-c" ]
