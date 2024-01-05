# :skull_and_crossbones: PFV (Protocols Formal Verification) :skull_and_crossbones:

## :rocket: Overview

PFV harnesses cutting-edge techniques in network protocol verification, merging the capabilities of the Shadow network simulator with the Ivy formal verification tool. This powerful combination facilitates the examination of time properties in network protocols. A specialized time module enhances Ivy, enabling it to handle complex quantitative-time properties with greater precision. PFV's effectiveness is highlighted through its application to the QUIC protocol. By refining QUIC's formal specification in Ivy, the tool not only verifies essential aspects of the protocol but also exposes real-world implementation errors, demonstrating its practical utility. This innovative integration paves the way for more thorough, efficient, and precise protocol testing and verification.

### :heavy_plus_sign: Multi-Protocol Support

PFV supports multiple protocols. Add new protocol specifications in the `protocols` directory, following the existing structure.
For now the following protocols are supported:
- [X] QUIC
- [X] MiniP
- [ ] BGP
- [ ] CoAP

## :wrench: Installation 

<details>
<summary>Click to expand</summary>

### :computer: Local Installation (Not Recommended)

<details>
<summary>Click to expand</summary>

See Dockerfile for dependencies and commands

</details>

### :whale: Single implementation 

<details>
<summary>Click to expand</summary>

```bash
# For a full installation including all dependencies and configurations:
IMPLEM="picoquic" make build-docker
```
</details>

### :whale: WebApp (Recommended) 

```bash
# For first installation 
make install

# For modification: 
##  For major update in ivy:
make build-docker-compose-full
## For a minor update in some implementation:
make build-docker-compose
```

### :warning: Clean Up

<details>
<summary>Click to expand</summary>

```bash
# To clean Docker images and system:
make clean-docker-full
```
</details>

</details>

## :computer: Usage

<details>
<summary>Click to expand</summary>

### :book: Tests parameters

<details>
<summary>Click to expand</summary>

*Global parameters:*

| Argument               | Description                                                                                               | Default Value           |
|------------------------|-----------------------------------------------------------------------------------------------------------|-------------------------|
| `--dir`                | Output directory to create                                                                                | `temp/`                 |
| `--build_dir`          | Build directory to create                                                                                 | `build/`                |
| `--tests_dir`          | Tests directory to create                                                                                 | `build/`                |
| `--iter`               | Number of iterations per test                                                                             | `1`                     |
| `--internal_iteration` | Number of Ivy iterations per test                                                                         | `100`                   |
| `--getstats`           | Print all stats                                                                                           | `True`                  |
| `--compile`            | Compile Ivy tests                                                                                         | `True`                  |
| `--run`                | Launch or not the tested implementation                                                                   | `True`                  |
| `--timeout`            | Timeout                                                                                                   | `100 sec`               |
| `--keep_alive`         | Keep alive Ivy implementation                                                                             | `False`                 |
| `--update_ivy`         | Update `<include>` folder for picoTLS files of Ivy (defined by g++)                                       | `True`                  |
| `--docker`             | Use docker                                                                                                | `True`                  |
| `--gperf`              | gperf                                                                                                     | `False`                 |
| `--gdb`                | Use gdb to debug                                                                                          | `False`                 |
| `--memprof`            | Perform memory profiling                                                                                  | `False`                 |
| `--localhost`          | Use localhost network                                                                                     | `True`                  |
| `--vnet`               | Use virtual network                                                                                       | `False`                 |
| `--shadow`             | Use Shadow simulator                                                                                      | `False`                 |
| `--webapp`             | WebApp UI                                                                                                 | `False`                 |
| `--worker`             | Worker server mode                                                                                        | `False`                 |

*Simulator parameters:*
| Argument               | Description                                                                                               | Default Value           |
|------------------------|-----------------------------------------------------------------------------------------------------------|-------------------------|
| `--loss`               | Shadow: loss percentage                                                                                   | `0`                     |
| `--jitter`             | Shadow: jitter in milliseconds                                                                            | `10`                    |
| `--latency`            | Shadow: latency in milliseconds                                                                           | `10`                    |

*QUIC parameters:*
| Argument               | Description                                                                                               | Default Value           |
|------------------------|-----------------------------------------------------------------------------------------------------------|-------------------------|
| `--nb_request`         | Number of request send by implementations (not always possible)                                           | `10`                    |
| `--initial_version`    | Initial version for protocol testing                                                                      | `1`                     |
| `--nclient`            | Number of clients per test for server implementation                                                      | `1`                     |
| `--alpn`               | Application-Layer Protocol Negotiation options                                                            | `hq-interop`, `hq-29`, `hq-28` |

*BGP parameters:*

*CoAP parameters:*

</details>


### :computer: Single implementation (Command Line)

<details>
<summary>Click to expand</summary>

```bash
# Start a Docker container for interactive Bash access
IMPLEM="picoquic" make start-bash
python3 pfv.py --mode client --categories all --update_include_tls \
		--timeout 180 --implementations $(IMPLEM) --iter $(ITER) --compile  --initial_version 29 --alpn hq-29  
# Example: Runs a Docker container with 'picoquic' for interactive Bash access
```
</details>

### :whale: WebApp (Recommended) 

Update the `docker-compose.yml` file with the protocol implementation and run the following command:

```bash
# Compose the full Docker environment for all implementations
make compose
```

</details>

## :book: Tutorial

<details>
<summary>Click to expand</summary>

### :computer: WebApp

<details>
<summary>Click to expand</summary>


</details>

### :computer: Adding new protocol

<details>
<summary>Click to expand</summary>

1. Create the corresponding Dockerfile in `src/containers/`, it should run over Ubuntu 20.04


</details>

### :computer: Adding new protocol implementation

<details>
<summary>Click to expand</summary>

1. Create the corresponding Dockerfile in `src/containers/`, it should run over Ubuntu 20.04
2. Add the corresponding configuration file in `src/pfv/configs/`
3. Build the docker image with `IMPLEM=<new_implem> make build-docker`
4. Add the new implementation in `docker-compose.yml` file such as:
```yaml
  <implem>-ivy:
    hostname: <implem>-ivy
    container_name: <implem>-ivy
    image: "<implem>-ivy:latest"
    command: python3 pfv.py --update_ivy --getstats --worker --compile  --docker
    ports:
      - "<new_pôrt>:80"
    volumes:
      - ${PWD}/src/webapp/pfv_client.py:/PFV/webapp/pfv_client.py
      - ${PWD}/src/pfv/pfv.py:/PFV/pfv.py
      - ${PWD}/src/pfv/res/shadow/shadow_client_test.yml:/PFV/topo.gml
      - ${PWD}/src/pfv/res/shadow/shadow_client_test.yml:/PFV/shadow_client_test.yml
      - ${PWD}/src/pfv/res/shadow/shadow_server_test.yml:/PFV/shadow_server_test.yml
      - ${PWD}/src/pfv/res/shadow/shadow_client_test_template.yml:/PFV/shadow_client_test_template.yml
      - ${PWD}/src/pfv/res/shadow/shadow_server_test_template.yml:/PFV/shadow_server_test_template.yml
      - ${PWD}/data/tls-keys:/PFV/tls-keys
      - ${PWD}/data/tickets:/PFV/tickets
      - ${PWD}/data/qlogs:/PFV/qlogs
      - ${PWD}/src/pfv/pfv_utils/:/PFV/pfv_utils/
      - ${PWD}/src/pfv/pfv_stats/:/PFV/pfv_stats/
      - ${PWD}/src/pfv/pfv_runner/:/PFV/pfv_runner/
      - ${PWD}/src/pfv/pfv_tester/:/PFV/pfv_tester/
      - ${PWD}/src/pfv/ivy_utils/:/PFV/ivy_utils/
      - ${PWD}/src/pfv/logger/:/PFV/logger/
      - ${PWD}/src/pfv/argument_parser/:/PFV/argument_parser/
      - ${PWD}/src/pfv/configs/:/PFV/configs/
      - ${PWD}/src/Protocols-Ivy/protocol-testing/:/PFV/Protocols-Ivy/protocol-testing/
      - ${PWD}/src/Protocols-Ivy/doc/examples/quic:/PFV/Protocols-Ivy/doc/examples/quic
      - ${PWD}/src/Protocols-Ivy/ivy/:/PFV/Protocols-Ivy/ivy/
      - ${PWD}/src/Protocols-Ivy/ivy/include/1.7:/PFV/Protocols-Ivy/ivy/include/1.7
      - /tmp/.X11-unix:/tmp/.X11-unix
    networks:
      net:
        ipv4_address: 172.27.0.<TODO>
    privileged: true
    security_opt:
      - seccomp:unconfined
    cap_add:
      - NET_ADMIN
    tmpfs:
      - /dev/shm:rw,nosuid,nodev,exec,size=1024g
    environment:
      - DISPLAY=${DISPLAY}
      - XAUTHORITY=~/.Xauthority
      - ROOT_PATH=${PWD} 
      - MPLBACKEND='Agg'
    restart: always
    devices:
      - /dev/dri:/dev/dri
    depends_on:
      - ivy-standalone
```
</details>

</details>

## :open_file_folder: Project Structure

<details>
<summary>Click to expand</summary>

### :open_file_folder: Directory Structure

<details>
<summary>Click to expand</summary>

The PFV project is organized into the following key directories:

```
PFV/
└── data/
└── src/
    ├── Protocols-Ivy/
    │   ├── protocol-testing/
    │   │   ├── quic/
    │   │   ├── minip/
    │   │   ├── coap/
    │   │   └── [other protocols]
    │   └── ivy/[ivy-core]
    ├── implementations/
    │   ├── quic-implementations/
    │   │       ├── picoquic/
    │   │       ├── aioquic/
    │   │       ├── lsquic/
    │   │       └── [protocol implementations]
    │   └── [other protocols]
    ├── containers/
    │   └── [Dockerfile definitions]
    └── pfv/
        ├── pfv.py
        ├── pfv_runner/ [test preparation]
        ├── ...
        ├── pfv_tester/ [test execution]
        └── configs/
            └── [configuration files]
```
- `data/`: Data directory for storing results and logs.
- `pfv/`: Main PFV module.
- `Protocols-Ivy/`: Core of protocol specifications and testing.
- `implementations/`: Various QUIC implementation modules.
- `containers/`: Dockerfile definitions for different environments.


</details>

### :framed_picture: Architecture Diagrams

<details>
<summary>Click to expand</summary>

| Docker Compose Architecture | Docker Container Internal Architecture |
|:---------------------------:|:--------------------------------------:|
| ![Docker Compose Architecture](res/DALL·E%202024-01-05%2006.59.32%20-%20A%20diagram%20illustrating%20the%20architecture%20of%20a%20Docker%20Compose%20setup%20for%20the%20PFV%20(Protocols%20Formal%20Verification)%20project.%20It%20shows%20various%20Docker%20contain.png) | ![Docker Container Internal Architecture](res/DALL·E%202024-01-05%2007.00.02%20-%20An%20internal%20architecture%20diagram%20of%20a%20Docker%20container%20for%20the%20PFV%20(Protocols%20Formal%20Verification)%20project.%20The%20diagram%20should%20show%20the%20layering%20of%20co.png) |

</details>


</details>