FROM frrouting/frr:10.2.1

# FRR ships with all daemons; enable bgpd + zebra
RUN sed -i 's/bgpd=no/bgpd=yes/' /etc/frr/daemons && \
    sed -i 's/zebra=no/zebra=yes/' /etc/frr/daemons

WORKDIR /etc/frr

ENTRYPOINT [ "/bin/bash", "-l", "-c" ]
