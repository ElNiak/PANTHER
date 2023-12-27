# :skull_and_crossbones: PFV (Protocols Formal Verification) :skull_and_crossbones:

This tool presents a novel approach to bolstering network
protocol verification by integrating the Shadow network simulator with
the Ivy formal verification tool to check time properties. Furthermore,
it extends Ivy’s capabilities with a dedicated time module, enabling the
verification of complex quantitative-time properties. The methodology
is applied to real-world protocols by enhancing the QUIC formal specifi-
cation in Ivy, verifying key specifications, and demonstrating its practi-
cality on the picoquic implementation. This revealed an error in the im-
plementation which underscores the effectiveness of the approach. This
integration opens new avenues for more detailed, efficient, and accurate
protocol testing and verification.

## :books: Installation

### Locally

Possible but no automatic way for now

### Locally with Docker (Recommanded)

First time:
```
make install
```

Then to update:
```
make build-docker-compose
```


## :books: Run tests

### Locally (attached to container)

```
python3 pfv.py --mode client --categories all --update_include_tls \
		--timeout 180 --implementations $(IMPLEM) --iter $(ITER) --compile  --initial_version 29 --alpn hq-29  
```

### Locally with Docker


```
# IMPLEM="<implem>" MODE="<mode>" CATE="<category>" ITER="<iteration>" OPT="<options>" make test-<version>
IMPLEM="picoquic" MODE="client" CATE="global_test" ITER="1" OPT="--vnet" make test-draft29
IMPLEM="picoquic" MODE="server" CATE="global_test" ITER="1" OPT="--vnet" make test-rfc9000
```

### Locally with Docker Compose - WebApp (Recommanded)

```
make compose;
```

Then go at http://ivy-standalone/ 
Also add "tls_cert" to your trust certificate in your browser

## :books: TODO

- reput the adversarial env for tested (!= port, adress, cid) -> long run (40 min same server)

- Why sometimes the deserializer do not take the full packet ?

- NS3

- Why removing the dcil and scil field ?

- VN: when the list no contain "Supported Version: Unknown (0x0a1a2a3a) (GREASE)"
    => never run read() from udp_impl.ivy TODO

- TODO 0rtt same keys + tps

- How to activate the generation of 2 packets at the same time ?
