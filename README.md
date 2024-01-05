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

<details>
<summary>Click to expand</summary>

```bash
# For first installation 
make install
# For major update in ivy:
make build-docker-compose-full
# For a minor update in some implementation:
make build-docker-compose
```
</details>

### :warning: Clean Up

<details>
<summary>Click to expand</summary>

```bash
# To clean Docker images and system:
make clean-docker-full
```
</details>

## :open_file_folder: Project Structure

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


## :computer: Usage

### :computer: Tests parameters

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


### :computer: Attach to Docker Container (command line)

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

### :computer: From webapp

<details>
<summary>Click to expand</summary>

Update the `docker-compose.yml` file with the protocol implementation and run the following command:

```bash
# Compose the full Docker environment for all implementations
make compose
# Example: Sets up and runs Docker Compose environment
```
</details>

## :computer: Adding new protocol

### :computer: Add new protocol implementation

## :framed_picture: Architecture Diagrams

### Docker Compose and Container Internal Layer Architecture

<details>
<summary>Click to expand</summary>

| Docker Compose Architecture | Docker Container Internal Architecture |
|:---------------------------:|:--------------------------------------:|
| ![Docker Compose Architecture](res/DALL·E%202024-01-05%2006.59.32%20-%20A%20diagram%20illustrating%20the%20architecture%20of%20a%20Docker%20Compose%20setup%20for%20the%20PFV%20(Protocols%20Formal%20Verification)%20project.%20It%20shows%20various%20Docker%20contain.png) | ![Docker Container Internal Architecture](res/DALL·E%202024-01-05%2007.00.02%20-%20An%20internal%20architecture%20diagram%20of%20a%20Docker%20container%20for%20the%20PFV%20(Protocols%20Formal%20Verification)%20project.%20The%20diagram%20should%20show%20the%20layering%20of%20co.png) |

</details>

## :book: Tutorial (Expand for details)

<details>
<summary>Click to expand</summary>

### Getting Started with PFV

1. Clone the repository and navigate to the project directory.
2. Follow the installation steps for Docker.
3. Start with running basic tests...

</details>
