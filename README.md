# :skull_and_crossbones: PFV (Protocols Formal Verification) :skull_and_crossbones:

## :rocket: Overview

PFV harnesses cutting-edge techniques in network protocol verification, merging the capabilities of the Shadow network simulator with the Ivy formal verification tool. This powerful combination facilitates the examination of time properties in network protocols. A specialized time module enhances Ivy, enabling it to handle complex quantitative-time properties with greater precision. PFV's effectiveness is highlighted through its application to the QUIC protocol. By refining QUIC's formal specification in Ivy, the tool not only verifies essential aspects of the protocol but also exposes real-world implementation errors, demonstrating its practical utility. This innovative integration paves the way for more thorough, efficient, and precise protocol testing and verification.

### :heavy_plus_sign: Multi-Protocol Support

PFV supports multiple protocols. Add new protocol specifications in the `protocols` directory, following the existing structure.
For now the following protocols are supported:
- [X] QUIC
- [X] MiniP
- [~] BGP
- [~] CoAP

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

- `protocols/`: Specifications for supported protocols.
- `tools/`: Utility scripts.
- `docker/`: Docker configurations.
- `tests/`: Testing scripts.
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
| ![Docker Compose Architecture](file-AloKpJ1kRqVFe2sOVxjAfFIO) | ![Docker Container Internal Architecture](file-YoPEG0mGDXMFvzR5kg3HVYnC) |

</details>

## :book: Tutorial (Expand for details)

<details>
<summary>Click to expand</summary>

### Getting Started with PFV

1. Clone the repository and navigate to the project directory.
2. Follow the installation steps for Docker.
3. Start with running basic tests...

</details>
