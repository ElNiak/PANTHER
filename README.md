# :skull_and_crossbones: QUIC Formal Verification :skull_and_crossbones:

## :books: Installation

### Locally

```
TODO not updated
``` 

### Locally with Docker

Currently, only work under Ubuntu 18

```
make install

# First build for each implementation (done like that for isolation)
# IMPLEM="<implem>" make build-docker
IMPLEM="picoquic" make build-docker
IMPLEM="quant" make build-docker

# For shorter build
# IMPLEM="<implem>" make build-docker-ivy
IMPLEM="picoquic" make build-docker-ivy
IMPLEM="quant" make build-docker-ivy
```

### Locally with Docker Compose

```
make build-docker-compose; 
```

## :books: Run tests

### Locally

```
python3 run_experiments.py --mode client --categories all --update_include_tls \
		--timeout 180 --implementations $(IMPLEM) --iter $(ITER) --compile  --initial_version 29 --alpn hq-29  
```

### Locally with Docker


```
# IMPLEM="<implem>" MODE="<mode>" CATE="<category>" ITER="<iteration>" OPT="<options>" make test-<version>
IMPLEM="picoquic" MODE="client" CATE="global_test" ITER="1" OPT="--vnet" make test-draft29
IMPLEM="picoquic" MODE="server" CATE="global_test" ITER="1" OPT="--vnet" make test-rfc9000
```

### Locally with Docker Compose (WebAPP)

```
make compose;
```

Then go at http://ivy-standalone/

## :books: TODO

- reput the adversarial env for tested (!= port, adress, cid) -> long run (40 min same server)

- Why sometimes the deserializer do not take the full packet ?

- NS3

- Why removing the dcil and scil field ?

- VN: when the list no contain "Supported Version: Unknown (0x0a1a2a3a) (GREASE)"
    => never run read() from udp_impl.ivy TODO

- TODO 0rtt same keys + tps

- How to activate the generation of 2 packets at the same time ?
