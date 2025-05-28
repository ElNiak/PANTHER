<!-- filepath: /Users/elniak/Documents/Project/PANTHER/panther/plugins/protocols/README.md -->
# PANTHER Protocol Plugins

**Protocol-specific testing logic and configurations**

Protocol plugins provide testing frameworks and configurations for specific network protocols. These plugins define how protocols should be tested, what parameters to validate, and how to interpret test results for different protocol specifications.

<!-- src: /panther/plugins/protocols/protocol_interface.py -->

## Protocol Categories

### Client-Server Protocols

Traditional client-server protocol testing where one endpoint initiates connections and the other responds.

| Protocol | Description | Documentation |
|----------|-------------|---------------|
| **QUIC** | HTTP/3 transport protocol | [Documentation](panther/plugins/protocols/client_server/quic) |
| **HTTP** | Hypertext Transfer Protocol | [Documentation](panther/plugins/protocols/client_server/http) |

### Peer-to-Peer Protocols

Distributed protocols where endpoints can act as both clients and servers.

| Protocol | Description | Documentation |
|----------|-------------|---------------|
| **BitTorrent** | P2P file sharing protocol | [Documentation](panther/plugins/protocols/peer_to_peer/bittorrent) |

## Quick Start

### Using a Protocol Plugin

```python
# filepath: example_protocol_usage.py
from panther.plugins.plugin_loader import PluginLoader

# Load QUIC protocol plugin
loader = PluginLoader()
quic_plugin = loader.load_plugin('protocols', 'client_server', 'quic')

# Configure protocol testing
config = {
    "version": "rfc9000",
    "test_scenarios": ["handshake", "data_transfer", "connection_close"],
    "validation_rules": ["conformance", "performance"]
}

quic_plugin.initialize(config)
```

### Configuration Structure

Protocol plugins use standardized configuration schemas:

```python
# filepath: /panther/plugins/protocols/config_schema.py
PROTOCOL_CONFIG_SCHEMA = {
    "protocol_name": str,
    "version": str,
    "test_scenarios": list,
    "validation_rules": list,
    "parameters": {
        # Protocol-specific parameters
    }
}
```

## Directory Structure

```text
protocols/
├── README.md                    # This file
├── development.md              # Development guide  
├── protocol_interface.py       # Base protocol interface
├── config_schema.py           # Configuration validation
├── client_server/             # Client-server protocols
│   ├── README.md
│   ├── quic/                  # QUIC protocol testing
│   │   ├── README.md
│   │   ├── rfc9000/          # QUIC v1 (RFC 9000)
│   │   └── draft29/          # QUIC Draft 29
│   └── http/                 # HTTP protocol testing
└── peer_to_peer/             # P2P protocols
    ├── README.md
    └── bittorrent/           # BitTorrent protocol
```

## Protocol Interface

All protocol plugins implement the base protocol interface:

```python
# filepath: /panther/plugins/protocols/protocol_interface.py
from panther.plugins.plugin_interface import IPlugin

class ProtocolInterface(IPlugin):
    """Base interface for protocol testing plugins."""
    
    def get_test_scenarios(self):
        """Return available test scenarios for this protocol."""
        pass
        
    def validate_configuration(self, config):
        """Validate protocol-specific configuration."""
        pass
    
    def setup_test_environment(self, config):
        """Setup testing environment for this protocol."""
        pass
    
    def execute_test(self, scenario, config):
        """Execute a specific test scenario."""
        pass
```

## Configuration

### Common Configuration Options

All protocol plugins support these base options:

- **protocol_name**: Protocol identifier (e.g., "quic", "http")
- **version**: Protocol version to test
- **test_scenarios**: List of test scenarios to execute
- **timeout**: Test execution timeout
- **validation_rules**: Rules for test result validation

### Protocol-Specific Options

Each protocol plugin defines additional configuration options:

#### QUIC Protocol

- **connection_timeout**: QUIC connection establishment timeout
- **initial_max_data**: Initial flow control limit
- **max_packet_size**: Maximum packet size for testing

#### HTTP Protocol

- **http_version**: HTTP version (1.1, 2, 3)
- **request_methods**: HTTP methods to test
- **response_codes**: Expected response codes

## Test Scenarios

Protocol plugins define standard test scenarios:

### Conformance Testing

- **Basic Handshake**: Protocol connection establishment
- **Data Transfer**: Reliable data transmission
- **Error Handling**: Protocol error response behavior
- **Connection Termination**: Clean connection closure

### Performance Testing

- **Throughput**: Maximum data transfer rate
- **Latency**: Round-trip time characteristics
- **Connection Setup Time**: Time to establish connections
- **Resource Usage**: Memory and CPU consumption

### Interoperability Testing

- **Version Negotiation**: Protocol version compatibility
- **Extension Support**: Optional feature negotiation
- **Error Recovery**: Handling of network issues

## Development

For information on creating new protocol plugins:

- **[Protocol Plugin Development Guide](panther/plugins/protocols/development.md)**: Comprehensive development documentation
- **[Protocol Interface Documentation](panther/plugins/protocols/protocol_interface.py)**: Base interface requirements
- **[Configuration Schema Guide](panther/plugins/protocols/config_schema.py)**: Configuration validation

## API Reference

Detailed API documentation for protocol plugins:

- **[Protocol Interfaces](./index.md)**: Auto-generated API reference
- **[Configuration Schema](panther/plugins/protocols/config_schema.py)**: Configuration validation
- **[Test Scenario Definitions](panther/plugins/protocols/client_server)**: Available test scenarios
