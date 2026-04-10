ARG BASE_IMAGE=frrouting/frr:10.2.1
FROM ${BASE_IMAGE}

# FRR ships with all daemons; we only need bgpd + zebra
RUN sed -i 's/bgpd=no/bgpd=yes/' /etc/frr/daemons && \
    sed -i 's/zebra=no/zebra=yes/' /etc/frr/daemons

WORKDIR /etc/frr

ENTRYPOINT [ "/bin/bash", "-l", "-c" ]
