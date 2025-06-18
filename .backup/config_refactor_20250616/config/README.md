# Configuration Guide — Writing & Validating PANTHER YAML 📜

A **PANTHER configuration** is a single YAML file that defines what to run, where to run it, and how to instrument it. This guide covers the complete configuration system, from basic setups to advanced plugin-specific options.

!!! info "Configuration Purpose"
    **Target Audience:** Newcomers designing tests; plugin authors adding schemas; advanced users optimizing configurations
    **Schema System:** Dynamic plugin-based configuration with OmegaConf validation

---

## Configuration Architecture

!!! warning "Schema Complexity"
    PANTHER's configuration system is highly flexible but can be complex. Start with example configurations in the `experiment-config/` directory before creating custom setups.

PANTHER uses a **hierarchical configuration system** with the following key principles:

1. **Plugin-Based Schemas**: Each plugin contributes its own configuration schema via `config_schema.py`
2. **Dynamic Validation**: Schemas are merged at runtime and validated with OmegaConf
3. **Type Safety**: Strong typing with dataclass-based configuration models
4. **Extensibility**: New plugins automatically extend the configuration space

### Configuration Structure

PANTHER configurations follow a hierarchical structure that combines global settings with test-specific configurations. Below is an annotated example with explanations:

```yaml
# Global settings that apply to all tests
logging:
  level: INFO                    # Set logging verbosity (DEBUG, INFO, WARNING, ERROR, CRITICAL)
  format: "%(asctime)s [%(levelname)s] - %(module)s - %(message)s"  # Custom log format

paths:
  output_dir: "outputs"          # Where results and artifacts will be stored
  log_dir: "outputs/logs"        # Directory for log files
  config_dir: "panther/configs"  # Location of additional configuration files
  plugin_dir: "panther/plugins"  # Directory containing PANTHER plugins

docker:
  build_docker_image: false      # Skip Docker image building (use existing images)

# List of tests to run - each test is a complete testing scenario
tests:
  - name: "QUIC Client-Server Communication Test"    # Human-readable test identifier
    description: "Verify that the Picoquic server can communicate with the Picoquic client over Shadow network."
    network_environment:
      type: "docker_compose"     # Use docker-compose for container orchestration
    iterations: 1                # Run this test just once
    execution_environment: []    # No special execution environment settings
    debug_environment: [ ]       # No debugging tools to attach
    
    # Define the services (containers) involved in this test
    services:
      picoquic_client:           # First service - a QUIC client
        timeout: 100             # Maximum runtime in seconds
        name: "picoquic_client"  # Container name
        implementation:
          name: "picoquic"       # Using the Picoquic implementation
          type: "iut"            # Implementation Under Test (not a tester)
        protocol:
          name: "quic"           # Using the QUIC protocol
          version: "rfc9000"     # QUIC protocol version
          role: "client"         # This service acts as a client
          target: "ivy_server"   # Connect to the ivy_server service
        ports:                   # Port mappings (host:container)
          - "5000:5000"          # Example port mapping
          - "8081:8081"          # Another port mapping
        generate_new_certificates: True  # Generate fresh TLS certificates

      ivy_server:                # Second service - a QUIC server using Ivy for verification
        name: "ivy_server"       # Container name
        timeout: 100             # Maximum runtime in seconds
        implementation:
          type: "testers"        # This is a testing tool, not an IUT
          name: "panther_ivy"    # Using the Ivy formal verification tool
          test: quic_client_test_max  # Specific test to run within Ivy
        protocol:
          name: "quic"           # Using the QUIC protocol
          version: "rfc9000"     # QUIC protocol version
          role: "server"         # This service acts as a server
        ports:                   # Port mappings (host:container)
          - "4443:4443"          # QUIC server port
          - "4987:4987"          # Additional port mapping
          - "8080:8080"          # Health check endpoint
        generate_new_certificates: True  # Generate fresh TLS certificates
        
    steps:
      wait: 100                  # Wait 100 seconds during test execution before proceeding
```

This configuration defines a test scenario where a Picoquic client communicates with an Ivy-based server over a QUIC connection. The test runs in Docker containers orchestrated by Docker Compose, with specific port mappings and protocol settings.

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

## Configuration Management and Port Handling

PANTHER provides an advanced configuration management system with intelligent validation, auto-fixing, and protocol-aware port management.

### Port Management System

PANTHER automatically manages port configurations with protocol-aware defaults and validation:

#### Automatic Port Assignment

When a server service doesn't specify ports, PANTHER automatically assigns protocol defaults:

```yaml
services:
  server:
    implementation: {name: picoquic, type: iut}
    protocol: {name: quic, version: rfc9000, role: server}
    # No ports specified - PANTHER will auto-assign 4443:4443 for QUIC
    timeout: 60
```

#### Protocol-Based Port Defaults

Different protocols have different default ports defined in their configuration schemas:

- **QUIC**: 4443 (defined in `QuicConfig.get_default_server_port()`)
- **HTTP**: 80
- **HTTPS**: 443
- **Custom protocols**: Can define their own defaults

#### Port Validation Rules

1. **Server services** must have at least one port mapping
2. **Client services** typically don't need port mappings
3. **Port mappings** must be valid (format: "host_port:container_port")
4. **Port conflicts** are automatically detected and resolved

#### Configuration Auto-Fixing

PANTHER can automatically fix common configuration issues:

```bash
# Enable auto-fixing during validation
panther config validate --config experiment.yaml --auto-fix

# Auto-fix saves the corrected configuration
panther config validate --config experiment.yaml --auto-fix --output fixed_config.yaml
```

**Auto-fixes include:**
- Adding default ports to server services
- Resolving port conflicts with alternative ports
- Standardizing port mapping formats
- Adding missing required fields

#### Manual Port Configuration

You can explicitly specify ports to override defaults:

```yaml
services:
  custom_server:
    implementation: {name: picoquic, type: iut}
    protocol: {name: quic, version: rfc9000, role: server}
    ports:
      - "8443:4443"  # Custom host port mapping
      - "8080:8080"  # Additional port for health checks
    timeout: 60
```

#### Port Conflict Resolution

When auto-assigning ports, PANTHER:
1. Checks if the default port is available on the host
2. If unavailable, tries the next available port in range
3. Updates the configuration with the assigned port
4. Logs the port assignment for reference

### Configuration Validation

PANTHER provides comprehensive configuration validation through its schema system:

#### Validation Features

- **Schema-based validation**: Type checking and required field validation
- **Business rule validation**: Protocol-specific and cross-service validation
- **Port validation**: Automatic port conflict detection and resolution
- **Custom validators**: Plugin-specific validation logic
- **Detailed error reporting**: Clear messages with field-level details

#### Validation Commands

```bash
# Basic validation
panther config validate --config experiment.yaml

# Validation with detailed explanations
panther config validate --config experiment.yaml --explain

# Auto-fix validation issues
panther config validate --config experiment.yaml --auto-fix

# Strict validation mode
panther config validate --config experiment.yaml --strict
```

#### Validation Results

Validation provides structured results:

```python
from panther.config.managers.configuration_validator import ConfigurationValidator

validator = ConfigurationValidator()
result = validator.validate_experiment_config(config)

print(result.get_summary())         # "Validation passed with 2 warnings"
print(result.get_detailed_report()) # Full validation report

# Check specific aspects
if result.is_valid:
    print("Configuration is valid")
for error in result.errors:
    print(f"Error: {error}")
for warning in result.warnings:
    print(f"Warning: {warning}")
```

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
