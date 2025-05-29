# Configuration Guide — Writing & Validating PANTHER YAML 📜

> **Purpose:** Comprehensive guide for designing experiment configurations and understanding PANTHER's validation system

> **Target:** Newcomers designing tests; plugin authors adding schemas; advanced users optimizing configurations

> **Schema System:** Dynamic plugin-based configuration with OmegaConf validation

A **PANTHER configuration** is a single YAML file that defines what to run, where to run it, and how to instrument it. This guide covers the complete configuration system, from basic setups to advanced plugin-specific options.

---

## Configuration Architecture

PANTHER uses a **hierarchical configuration system** with the following key principles:

1. **Plugin-Based Schemas**: Each plugin contributes its own configuration schema via `config_schema.py`
2. **Dynamic Validation**: Schemas are merged at runtime and validated with OmegaConf
3. **Type Safety**: Strong typing with dataclass-based configuration models
4. **Extensibility**: New plugins automatically extend the configuration space

### Configuration Structure

```yaml
# Global settings that apply to all tests
logging:
  level: INFO
  format: "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

paths:
  output_dir: "./outputs"
  temp_dir: "./temp"

docker:
  pull_images: true
  cleanup_on_exit: true

# Array of individual test configurations
tests:
  - name: "quic_basic_test"
    network_environment:
      type: "docker_compose"
      config:
        compose_file: "docker-compose.yml"

    execution_environment:
      type: "docker_container"
      config:
        image: "panther/test-env"

    services:
      - name: "quic_server"
        type: "iut"
        implementation: "quiche"
        role: "server"
        config:
          port: 4433
          cert_file: "/certs/server.crt"
          key_file: "/certs/server.key"

      - name: "quic_client"
        type: "iut"
        implementation: "quiche"
        role: "client"
        config:
          target: "quic_server"

      - name: "formal_verifier"
        type: "tester"
        implementation: "panther_ivy"
        config:
          protocol: "quic"
          test_suite: "basic_conformance"
```

---

## Configuration Sections

### 1. Global Settings

#### Logging Configuration

```yaml
logging:
  level: INFO                    # DEBUG, INFO, WARNING, ERROR, CRITICAL
  format: "%(asctime)s - %(levelname)s - %(message)s"
  file: "./logs/panther.log"     # Optional: log to file
  console: true                  # Enable console output
```

#### Path Configuration

```yaml
paths:
  output_dir: "./outputs"        # Where test results are stored
  temp_dir: "./temp"            # Temporary files directory
  config_dir: "./configs"       # Additional configuration files
  data_dir: "./data"            # Test data and resources
```

#### Docker Configuration

```yaml
docker:
  pull_images: true             # Pull latest images before tests
  cleanup_on_exit: true         # Clean up containers after tests
  registry: "docker.io"         # Custom registry (optional)
  build_timeout: 300            # Build timeout in seconds
  network_name: "panther_net"   # Custom network name
```

### 2. Network Environments

Network environments define where and how containers communicate.

#### Docker Compose Environment

```yaml
network_environment:
  type: "docker_compose"
  config:
    compose_file: "docker-compose.yml"
    project_name: "panther_test"
    services:
      - "quic_server"
      - "quic_client"
    networks:
      - name: "test_network"
        driver: "bridge"
        ipam:
          config:
            - subnet: "172.20.0.0/16"
```

#### Localhost Single Container

```yaml
network_environment:
  type: "localhost_single_container"
  config:
    container_name: "panther_test"
    network_mode: "host"
    exposed_ports:
      - "4433:4433"
      - "8080:8080"
```

#### Shadow Network Simulator

```yaml
network_environment:
  type: "shadow"
  config:
    hosts:
      - name: "server"
        processes:
          - path: "/app/server"
            args: ["--port", "4433"]
      - name: "client"
        processes:
          - path: "/app/client"
            args: ["server", "4433"]
    network:
      topology: "1_gbit_ethernet"
      latency: "10ms"
      bandwidth: "1000mbit"
```

### 3. Execution Environments

Execution environments define the runtime context for services.

#### Docker Container Environment

```yaml
execution_environment:
  type: "docker_container"
  config:
    image: "panther/test-env:latest"
    dockerfile: "./Dockerfile"
    build_context: "./build"
    environment:
      - "DEBUG=1"
      - "RUST_LOG=debug"
    volumes:
      - "./certs:/certs:ro"
      - "./logs:/app/logs:rw"
    capabilities:
      - "NET_ADMIN"
      - "SYS_PTRACE"
```

#### Host Environment

```yaml
execution_environment:
  type: "host"
  config:
    working_dir: "/tmp/panther"
    environment:
      PATH: "/usr/local/bin:$PATH"
      LD_LIBRARY_PATH: "/usr/local/lib"
```

### 4. Services Configuration

Services define the actual implementations being tested or doing the testing.

#### IUT (Implementation Under Test) Services

##### QUIC Implementations

**Quiche Configuration:**

```yaml
services:
  - name: "quiche_server"
    type: "iut"
    implementation: "quiche"
    role: "server"
    config:
      binary:
        path: "/app/quiche-server"
        args: ["--cert", "/certs/cert.pem", "--key", "/certs/key.pem"]
      network:
        port: 4433
        interface: "0.0.0.0"
      protocol:
        alpn: ["h3", "hq-29"]
        version: "draft-29"
        max_packet_size: 1350
      certificates:
        cert_file: "/certs/server.crt"
        key_file: "/certs/server.key"
      logging:
        log_path: "/app/logs/server.log"
        err_path: "/app/logs/server.err"
        level: "debug"
```

**Picoquic Configuration:**

```yaml
services:
  - name: "picoquic_client"
    type: "iut"
    implementation: "picoquic"
    role: "client"
    config:
      binary:
        path: "/app/picoquic_sample"
        args: ["-l", "/app/logs/client.log"]
      target: "quiche_server"
      network:
        port: 4433
      protocol:
        alpn: ["hq-29"]
        initial_version: "ff00001d"
      certificates:
        ca_file: "/certs/ca.pem"
        verify_certificate: false
```

**Aioquic Configuration:**

```yaml
services:
  - name: "aioquic_server"
    type: "iut"
    implementation: "aioquic"
    role: "server"
    config:
      binary:
        path: "/app/http3_server.py"
        interpreter: "python3"
      network:
        port: 4433
        host: "0.0.0.0"
      protocol:
        alpn: ["h3"]
        quic_logger: true
      certificates:
        cert_file: "/certs/cert.pem"
        key_file: "/certs/key.pem"
```

#### Tester Services

##### Panther Ivy Formal Verification

```yaml
services:
  - name: "ivy_verifier"
    type: "tester"
    implementation: "panther_ivy"
    config:
      protocol: "quic"
      ivy_files:
        - "/app/protocols/quic/quic_protocol.ivy"
        - "/app/protocols/quic/quic_tests.ivy"
      test_config:
        seed: 12345
        max_steps: 1000
        timeout: 300
      verification:
        check_safety: true
        check_liveness: true
        bounded_check: true
        bound: 10
      logging:
        log_path: "/app/logs/ivy.log"
        err_path: "/app/logs/ivy.err"
        trace_file: "/app/logs/trace.txt"
```

---

## Configuration Validation

PANTHER provides comprehensive configuration validation through its schema system:

### Schema Definition

Each plugin defines its configuration schema using Python dataclasses:

```python
# Example: panther/plugins/services/iut/quic/quiche/config_schema.py
from dataclasses import dataclass
from typing import Optional, List

@dataclass
class QuicheBinaryConfig:
    path: str
    args: Optional[List[str]] = None
    dir: str = "/app"

@dataclass
class QuicheNetworkConfig:
    port: int = 4433
    interface: str = "0.0.0.0"

@dataclass
class QuicheProtocolConfig:
    alpn: List[str]
    version: Optional[str] = None
    max_packet_size: int = 1350

@dataclass
class QuicheConfig:
    binary: QuicheBinaryConfig
    network: QuicheNetworkConfig
    protocol: QuicheProtocolConfig
    certificates: CertificateConfig
    logging: LoggingConfig
```

### Validation Process

1. **Schema Discovery**: PANTHER automatically discovers all plugin schemas
2. **Schema Merging**: Schemas are combined into a unified configuration model
3. **Type Validation**: OmegaConf validates types and required fields
4. **Custom Validation**: Plugins can provide custom validation logic
5. **Error Reporting**: Clear error messages with field-level details

### Validation Commands

```bash
# Validate configuration before running
panther --validate-config --experiment-config config.yaml

# Validate and show merged schema
panther --show-schema --experiment-config config.yaml

# Validate specific plugin configuration
panther --validate-plugin quiche --config plugin_config.yaml

# List available parameters for a specific plugin
panther --list-plugin-params quiche  # Plugin type and protocol will be auto-detected
```

### Inspecting Plugin Parameters

To view all available configuration parameters for a specific plugin, use:

```bash
panther --list-plugin-params PLUGIN_NAME [--plugin-type PLUGIN_TYPE] [--protocol PROTOCOL]
```

Where:

- `PLUGIN_NAME` is the name of the plugin (e.g., `quiche`, `docker_compose`)
- `PLUGIN_TYPE` (optional) is one of: `iut`, `tester`, `network_environment`, or `execution_environment`
  - If not provided, PANTHER will auto-detect the plugin type
- `PROTOCOL` (optional) for IUT/tester plugins, specifies the protocol (e.g., `quic`, `http`, `minip`)
  - If not provided, PANTHER will auto-detect the protocol for protocol-specific plugins

This command displays all parameters, their types, default values, whether they're required, and their descriptions:

```text
Parameter           Type                           Default              Required   Description
----------------------------------------------------------------------------------------------------
binary              QuicheBinaryConfig             None                 Yes        Binary configuration
network             QuicheNetworkConfig            None                 Yes        Network settings
protocol            QuicheProtocolConfig           None                 Yes        Protocol parameters
certificates        CertificateConfig              None                 Yes        Certificate settings
logging             LoggingConfig                  None                 Yes        Logging configuration
```

This feature helps you understand exactly what parameters are available and required for each plugin without having to examine the source code directly.

---
