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

### :computer: Local Installation

<details>
<summary>Click to expand</summary>

Clone the repository and initialize submodules:

```bash
git submodule update --init --recursive
git submodule update --recursive
```

Switch to the development branch for CoAP protocol:

```bash
cd src/Protocols-Ivy/
git fetch
git checkout development-CoAP
```

Then, proceed with the installation:

```bash
make install
```
</details>

### :whale: Installation with Docker (Recommended)

<details>
<summary>Click to expand</summary>

For a full installation including all dependencies and configurations:

```bash
make build-docker-compose-full
```

For a standard installation:

```bash
make build-docker-compose
```
</details>

### :warning: Clean Up

<details>
<summary>Click to expand</summary>

To clean Docker images and system:

```bash
make clean-docker-full
```
</details>

## :open_file_folder: Project Structure

<details>
<summary>Click to expand</summary>

The PFV project is organized into several key directories, with `src/` and `src/Protocols-Ivy/` being crucial for the core functionalities:

### `src/` Directory

This directory contains the primary source code and components of the PFV project:

- **`Protocols-Ivy/`**: The heart of protocol specifications. It houses the Ivy formal verification tool configurations and specifications for various protocols.
- **`implementations/`**: Contains different QUIC implementation modules, such as `picoquic`, `aioquic`, and `lsquic`. This area is crucial for testing and comparing various implementations against the formal specifications.
- **`containers/`**: Holds Dockerfile definitions for creating different environment setups and implementation-specific containers, enabling a modular and isolated testing environment.

### `src/Protocols-Ivy/` Directory

This directory is pivotal for the protocol verification process:

- **`doc/`**: Documentation and examples relevant to the protocols, including practical use cases and setup guides.
   - **`examples/`**: Contains example protocols and their implementation, such as QUIC and MiniP. It's a great starting point for understanding how protocols are structured within PFV.
- **`protocol-testing/`**: This subdirectory is essential for the testing framework. It includes configurations and scripts for formal verification tests of different protocols like QUIC, MiniP, and potentially others.
   - **`quic/`, `minip/`, `coap/`**: Each subdirectory corresponds to a specific protocol, containing build and test scripts tailored for that protocol.
- **`ivy/`**: Contains the Ivy tool's core files, libraries, and scripts necessary for protocol verification.


</details>

## :hammer_and_wrench: Updating Docker Compose File

<details>
<summary>Click to expand</summary>

To update `docker-compose.yml`, edit the file in the `docker/` directory and run:

```bash
make build-docker-compose
```
</details>

## :computer: Usage

<details>
<summary>Click to expand</summary>

PFV offers a wide range of command-line options to tailor its functionality to your needs:

[Include detailed usage instructions here, as provided in the previous response]

</details>

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
