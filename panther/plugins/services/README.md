# PANTHER Service Plugins

## Overview

The PANTHER Service Plugins framework provides a comprehensive architecture for managing network protocol implementations and testing services within containerized environments. This system enables automated testing of protocol implementations across multiple environments (Docker Compose, localhost, Shadow NS) with sophisticated command generation, event handling, and output collection capabilities.

## Architecture

The service plugin system follows a hierarchical architecture with clear separation between implementations under test (IUT) and testing services, both built on a common foundation of base classes and interfaces.

### Service Type Hierarchy

```text
Services
├── IUT (Implementation Under Test)
│   ├── QUIC Implementations
│   │   ├── aioquic (Python)
│   │   ├── lsquic (C)
│   │   ├── mvfst (C++)
│   │   ├── picoquic (C)
│   │   ├── quant (C)
│   │   ├── quic-go (Go)
│   │   ├── quiche (Rust)
│   │   └── quinn (Rust)
│   ├── HTTP Implementations
│   └── MinIP Implementations
│       └── ping_pong
└── Testers
    └── panther_ivy (Formal Verification)
```

## Service Categories

!!! note "Service Types"
    IUT services represent implementations being tested, while Tester services provide validation and analysis capabilities. Both work together to create comprehensive testing scenarios.

### Implementation Under Test (IUT)

IUT plugins represent protocol implementations that are being evaluated for conformance, performance, or security characteristics. All implementations inherit from protocol-specific base classes using the template method pattern.

#### QUIC Implementations

All QUIC implementations inherit from `BaseQUICServiceManager` or specialized subclasses:

| Implementation | Language | Base Class | Description | Documentation |
|---------------|----------|------------|-------------|---------------|
| **[PicoQUIC](iut/quic/picoquic/README.md)** | C | BaseQUICServiceManager | Mature, RFC-compliant | [Documentation](iut/quic/picoquic/README.md) |
| **[AioQUIC](iut/quic/aioquic/README.md)** | Python | PythonQUICServiceManager | Async/await, HTTP/3 | [Documentation](iut/quic/aioquic/README.md) |
| **[Quiche](iut/quic/quiche/README.md)** | Rust | RustQUICServiceManager | Memory safety, performance | [Documentation](iut/quic/quiche/README.md) |
| **[Quinn](iut/quic/quinn/README.md)** | Rust | RustQUICServiceManager | Modern async | [Documentation](iut/quic/quinn/README.md) |
| **[LsQUIC](iut/quic/lsquic/README.md)** | C | BaseQUICServiceManager | LiteSpeed optimized | [Documentation](iut/quic/lsquic/README.md) |
| **[QUIC-Go](iut/quic/quic_go/README.md)** | Go | BaseQUICServiceManager | Goroutine-based | [Documentation](iut/quic/quic_go/README.md) |
| **[mvfst](iut/quic/mvfst/README.md)** | C++ | BaseQUICServiceManager | Facebook's impl | [Documentation](iut/quic/mvfst/README.md) |
| **[Quant](iut/quic/quant/README.md)** | C | BaseQUICServiceManager | Research-focused | [Documentation](iut/quic/quant/README.md) |
| **[PicoQUIC Shadow](iut/quic/picoquic_shadow/README.md)** | C | BaseQUICServiceManager | Shadow NS integration | [Documentation](iut/quic/picoquic_shadow/README.md) |

See the [QUIC implementations overview](iut/quic/README.md) for detailed comparison and usage examples.

#### Other Protocol Implementations

| Protocol | Implementation | Base Class | Description | Documentation |
|----------|----------------|------------|-------------|---------------|
| **MINIP** | ping_pong | BaseMinipServiceManager | Simple ping-pong service | [Documentation](iut/minip/ping_pong/README.md) |
| **HTTP** | *Available for development* | BaseHTTPServiceManager | HTTP implementation base | [Base class documentation](base/README.md) |

### Testers

Tester plugins provide mechanisms for evaluating implementations, generating test traffic, and validating protocol behavior.

| Tester | Purpose | Documentation |
|--------|---------|---------------|
| panther_ivy | Formal verification and conformance testing | [Documentation](testers/panther_ivy/README.md) |

## Quick Start

### Using an IUT Service

```python
# filepath: example_iut_usage.py
from panther.plugins.plugin_loader import PluginLoader

# Load the picoquic IUT plugin
loader = PluginLoader()
picoquic = loader.load_plugin('services', 'iut', 'quic', 'picoquic')

# Configure the service
config = {
    "role": "server",
    "port": 4433,
    "cert_file": "/path/to/cert.pem",
    "key_file": "/path/to/key.pem"
}

# Initialize and start
picoquic.initialize(config)
picoquic.start()
```

### Configuration Structure

Service plugins follow a standardized configuration schema:

```python
# filepath: /panther/plugins/services/config_schema.py
SERVICE_CONFIG_SCHEMA = {
    "service_name": str,
    "service_type": str,  # "iut" or "tester"
    "role": str,          # "client", "server", or "both"
    "configuration": {
        # Service-specific parameters
    }
}
```

## Directory Structure

```text
services/
├── README.md                    # This file
├── development.md              # Development guide
├── services_interface.py       # Base service interface
├── config_schema.py           # Configuration validation
├── iut/                       # Implementation Under Test plugins
│   ├── README.md
│   ├── config_schema.py
│   ├── implementation_interface.py
│   ├── http/                  # HTTP implementations
│   ├── quic/                  # QUIC implementations
│   │   └── picoquic/         # Specific implementation
│   └── minip/                # Custom protocols
└── testers/                  # Testing tools
    ├── README.md
    └── panther_ivy/         # Formal verification tester
```

## Service Interface

All service plugins implement the base service interface:

```python
# filepath: /panther/plugins/services/services_interface.py
from panther.plugins.plugin_interface import IPlugin

class ServiceInterface(IPlugin):
    """Base interface for all service plugins."""

    def initialize(self, config):
        """Initialize the service with configuration."""
        pass

    def start(self):
        """Start the service."""
        pass

    def stop(self):
        """Stop the service."""
        pass

    def get_status(self):
        """Get current service status."""
        pass
```

## Configuration

### Common Configuration Options

All service plugins support these base configuration options:

- **service_name**: Unique identifier for the service instance
- **role**: Service role (client, server, or both)
- **timeout**: Maximum execution time
- **logging_level**: Service-specific logging configuration

### IUT-Specific Configuration

IUT services additionally support:

- **protocol_version**: Specific protocol version to test
- **implementation_args**: Implementation-specific command line arguments
- **environment_variables**: Custom environment variables

### Tester-Specific Configuration

Tester services additionally support:

- **test_scenarios**: List of test scenarios to execute
- **validation_rules**: Rules for determining test success/failure
- **output_format**: Format for test results

## Development

For information on creating new service plugins, see:

- **[Service Plugin Development Guide](development.md)**: Comprehensive development documentation
- **[IUT Development Guide](iut/development.md)**: Creating new IUT plugins
- **[Plugin Interface Documentation](../development.md)**: Base interface requirements
