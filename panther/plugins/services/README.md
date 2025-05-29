<!-- filepath: /Users/elniak/Documents/Project/PANTHER/panther/plugins/services/README.md -->
# PANTHER Service Plugins

**Implementation Under Test (IUT) and Testing Service Management**

Service plugins in PANTHER represent concrete implementations of network protocols and testing tools. They provide the actual services that participate in protocol testing, including implementations being evaluated (IUT) and tools that perform testing and validation.

<!-- src: /panther/plugins/services/services_interface.py -->

## Service Categories

### Implementation Under Test (IUT)

IUT plugins represent protocol implementations that are being evaluated for conformance, performance, or security characteristics.

| Protocol | Implementation | Description | Documentation |
|----------|----------------|-------------|---------------|
| **QUIC** | picoquic | C implementation by Christian Huitema | [Documentation](panther/plugins/services/iut/quic/picoquic) |
| **HTTP** | Various | HTTP server implementations | [Documentation](panther/plugins/services/iut/http) |
| **Custom** | ping_pong | Simple test service for basic validation | [Documentation](panther/plugins/services/iut/minip) |

### Testers

Tester plugins provide mechanisms for evaluating implementations, generating test traffic, and validating protocol behavior.

| Tester | Purpose | Documentation |
|--------|---------|---------------|
| ivy_tester | Formal verification and conformance testing | [Documentation](testers/ivy_tester/) |

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
    └── ivy_tester/          # Formal verification tester
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

- **[Service Plugin Development Guide](panther/plugins/services/development.md)**: Comprehensive development documentation
- **[IUT Development Guide](iut/development_iut.md)**: Creating new IUT plugins
- **[Plugin Interface Documentation](panther/plugins/services/services_interface.py)**: Base interface requirements

## API Reference

Detailed API documentation for service plugins:

- **[Service Interfaces](./index.md)**: Auto-generated API reference
- **[Configuration Schema](panther/plugins/services/config_schema.py)**: Configuration validation
- **[IUT Interface](panther/plugins/services/iut/implementation_interface.py)**: IUT-specific interface
