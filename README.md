# :skull_and_crossbones: PFV (Protocols Formal Verification) :skull_and_crossbones:

## :rocket: Overview

PFV harnesses cutting-edge techniques in network protocol verification, merging the capabilities of the Shadow network simulator with the Ivy formal verification tool. This powerful combination facilitates the examination of time properties in network protocols. A specialized time module enhances Ivy, enabling it to handle complex quantitative-time properties with greater precision. PFV's effectiveness is highlighted through its application to the QUIC protocol. By refining QUIC's formal specification in Ivy, the tool not only verifies essential aspects of the protocol but also exposes real-world implementation errors, demonstrating its practical utility. This innovative integration paves the way for more thorough, efficient, and precise protocol testing and verification.

## :wrench: Installation

### :computer: Local Installation

Manual installation is possible, though currently, there's no automated process available.
You can use the command in dockerfile to install the dependencies.

### :whale: Docker Installation (Recommended)

**Initial Setup:**
```bash
make install
```

**For Updates:**
```bash
make build-docker-compose
```

Based on the argument parser provided, I'll update the "Usage" section of the README for the PFV project to include comprehensive details on how to use the tool with various command-line options.

---

# :skull_and_crossbones: PFV (Protocols Formal Verification) :skull_and_crossbones:

PFV is an advanced tool for formal verification of network protocols, integrating the Shadow network simulator with the Ivy formal verification tool for comprehensive protocol analysis.

## :computer: Usage

PFV offers a wide range of command-line options to tailor its functionality to your needs. Below are the available options and their descriptions:

### Global Parameters

- `--dir`: Specify the output directory (default: `temp/`).
- `--build_dir`: Specify the build directory (default: `build/`).
- `--tests_dir`: Specify the tests directory (default: `build/`).
- `--iter`: Set the number of iterations per test (default: `1`).
- `--internal_iteration`: Set the number of Ivy iterations per test (default: `100`).
- `--getstats`: Print all stats (default: enabled).
- `--compile`: Compile Ivy tests (default: enabled).
- `--run`: Launch the tested implementation (default: enabled).
- `--timeout`: Set the timeout in seconds (default: `100`).
- `--keep_alive`: Keep the Ivy implementation alive (default: disabled).
- `--update_ivy`: Update `<include>` folder for picoTLS files of Ivy (default: enabled).
- `--docker`: Use Docker for running tests (default: enabled).

### Debugging Ivy

- `--gperf`: Enable gperf profiling (default: disabled).
- `--gdb`: Use gdb for debugging (default: disabled).
- `--memprof`: Perform memory profiling (default: disabled).

### Network Type

- `--localhost`: Use localhost network (default: enabled).
- `--vnet`: Use a virtual network (default: disabled).
- `--shadow`: Use Shadow simulator (default: disabled).

### Usage Type

- `--webapp`: Run as a WebApp UI (default: disabled).
- `--worker`: Run in worker server mode (default: disabled).

### Shadow Parameters

- `--loss`: Set packet loss rate in Shadow (default: `0`).
- `--jitter`: Set jitter in milliseconds in Shadow (default: `10`).
- `--latency`: Set latency in milliseconds in Shadow (default: `10`).

### QUIC Verification with Ivy

- `--nb_request`: Number of requests sent by implementations (default: `10`).
- `--initial_version`: Set the initial QUIC version (choices: `1`, `29`, `28`; default: `1`).
- `--nclient`: Number of clients per test for server implementation (default: `1`).
- `--alpn`: Set the Application-Layer Protocol Negotiation (choices: `hq-interop`, `hq-29`, `hq-28`).

### BGP Verification with Ivy

[Options related to BGP verification]

### MiniP Verification with Ivy

[Options related to MiniP verification]

## :running: Running Tests

### :desktop_computer: Local Testing (Direct Container Access)

Execute the following command to run tests in a local environment attached to the container:
```bash
python3 pfv.py --mode client --categories all --update_include_tls \
               --timeout 180 --implementations $(IMPLEM) --iter $(ITER) --compile  --initial_version 29 --alpn hq-29
```

### :whale: Testing with Docker

Use these commands for testing with Docker:
```bash
# IMPLEM="<implem>" MODE="<mode>" CATE="<category>" ITER="<iteration>" OPT="<options>" make test-<version>
IMPLEM="picoquic" MODE="client" CATE="global_test" ITER="1" OPT="--vnet" make test-draft29
IMPLEM="picoquic" MODE="server" CATE="global_test" ITER="1" OPT="--vnet" make test-rfc9000
```

### :whale: Docker Compose - WebApp (Recommended)

For a user-friendly interface:
```bash
make compose;
```
Access the application at http://ivy-standalone/. Remember to add "tls_cert" to your trusted certificates in the browser.

## :framed_picture: Architecture Diagrams
Docker Compose and Container Internal Layer Architecture
<details>
<summary>Click to expand</summary>
Docker Compose Architecture	Docker Container Internal Architecture
	
</details>

## :framed_picture: Docker Container Internal Layer Architecture

[Include an image that shows the internal layer architecture of the Docker container here.]
## :arrow_down_small: Tutorial
<details>
<summary>Click to expand the tutorial section</summary>
Getting Started with PFV

    [Here, provide the initial steps or introduction for the tutorial.]

...
</details>