# Protocol Plugins API Reference

## Overview

This reference documents the public API for the PANTHER protocol plugins system. All protocol implementations follow the interface defined by `IProtocolManager` and use the `@register_protocol` decorator for metadata registration.

## Core Classes

### IProtocolManager

Base class for all protocol implementations.

**Module**: `panther.plugins.protocols.protocol_interface`

```python
class IProtocolManager(IPlugin):
    """Manage protocol configurations for network testing services."""
```

#### Constructor

```python
def __init__(self, service_type: str)
```

Initialize protocol manager with service type configuration.

**Parameters:**
- `service_type` (str): Type of service protocol to manage (e.g., 'quic', 'http')

**Raises:**
- `FileNotFoundError`: If the protocol configuration file doesn't exist
- `yaml.YAMLError`: If the configuration file contains invalid YAML

#### Methods

##### validate_config()

```python
def validate_config(self) -> None
```

Validate the loaded protocol configuration.

This method should be overridden by concrete implementations to provide protocol-specific validation logic. The default implementation performs no validation.

**Raises:**
- `ValueError`: If configuration contains invalid or missing required fields

##### load_config()

```python
def load_config(self) -> dict
```

Load protocol configuration from YAML file.

Reads and parses the YAML configuration file for this protocol type. The configuration file path is determined by the service_type provided during initialization.

**Returns:**
- `dict`: Parsed configuration data from the YAML file

**Raises:**
- `FileNotFoundError`: If the configuration file doesn't exist
- `yaml.YAMLError`: If the YAML file is malformed
- `PermissionError`: If the file cannot be read due to permissions

**Example:**
```python
config = self.load_config()
print(config['protocol_version'])  # 'quic-1.0'
```

## Protocol Implementations

### QUICProtocol

QUIC transport protocol implementation.

**Module**: `panther.plugins.protocols.client_server.quic.quic`

```python
@register_protocol(
    name="quic",
    type="client_server",
    versions=["rfc9000", "draft29", "draft27", "draft27-vuln1", "draft27-vuln2"],
    default_version="rfc9000",
    capabilities=["0-rtt", "connection-migration", "stream-multiplexing", ...],
    config_schema={...}
)
class QUICProtocol(IProtocolManager):
    """QUIC Protocol Manager."""
```

#### Constructor

```python
def __init__(self)
```

Initialize QUIC protocol manager.

Sets up logging and skips parent YAML loading since configuration is handled through the decorator metadata system.

#### Methods

##### validate_config()

```python
def validate_config(self) -> None
```

Validate QUIC protocol configuration.

Configuration validation is handled automatically through the schema defined in the register_protocol decorator. This method serves as a placeholder for any additional runtime validation.

##### load_config()

```python
def load_config(self) -> dict
```

Load QUIC protocol configuration from decorator metadata.

**Returns:**
- `dict`: Default QUIC configuration parameters including stream limits, data limits, timeout values, and ALPN protocols

**Example:**
```python
config = self.load_config()
print(config['initial_max_data'])  # 10485760
```

##### get_version_parameters()

```python
def get_version_parameters(self, version: str) -> dict
```

Get version-specific QUIC protocol parameters.

Retrieves configuration parameters that are specific to a particular QUIC version, including version negotiation settings and vulnerability testing parameters.

**Parameters:**
- `version` (str): QUIC version identifier (e.g., 'rfc9000', 'draft-27')

**Returns:**
- `dict`: Version-specific parameters including initial version hex, version negotiation flag, compatible versions list, and optional vulnerability test settings

**Example:**
```python
params = self.get_version_parameters('rfc9000')
print(params['initial_version'])  # '00000001'
```

##### get_default_server_port()

```python
@classmethod
def get_default_server_port(cls) -> int
```

Get the default server port for QUIC connections.

**Returns:**
- `int`: Default QUIC server port (4443)

**Note:**
Port 4443 is commonly used for QUIC as it's the HTTPS port (443) plus 4000, making it easy to remember and unlikely to conflict.

##### get_default_client_port()

```python
@classmethod
def get_default_client_port(cls) -> int
```

Get the default client port for QUIC connections.

**Returns:**
- `int`: Ephemeral port (0), allowing the OS to assign an available port

**Note:**
QUIC clients typically use ephemeral ports assigned by the operating system to avoid port conflicts and enable multiple concurrent connections.

### MiniPProtocol

Minimal protocol for basic testing functionality.

**Module**: `panther.plugins.protocols.client_server.minip.minip`

```python
@register_protocol(
    name="minip",
    description="MiniP Protocol Manager",
    versions=["flaky", "fail", "functional", "random", "vulnerable"],
    tags=["transport", "secure", "multiplexed"]
)
class MiniPProtocol(IProtocolManager):
    """MiniP Protocol Manager."""
```

#### Constructor

```python
def __init__(self)
```

Initialize MiniP protocol manager.

Skip parent init since we don't need the old YAML loading.

#### Methods

##### validate_config()

```python
def validate_config(self) -> None
```

Validate protocol configuration.

Configuration is validated through the schema.

##### load_config()

```python
def load_config(self) -> dict
```

Load protocol configuration.

**Returns:**
- `dict`: The default config from decorator

##### get_version_parameters()

```python
def get_version_parameters(self, version: str) -> dict
```

Get version-specific parameters.

**Parameters:**
- `version` (str): Protocol version identifier

**Returns:**
- `dict`: Version-specific parameters

##### get_default_server_port()

```python
@classmethod
def get_default_server_port(cls) -> int
```

Get the default server port for QUIC.

**Returns:**
- `int`: Default server port (4443)

##### get_default_client_port()

```python
@classmethod
def get_default_client_port(cls) -> int
```

Get the default client port for QUIC (usually ephemeral).

**Returns:**
- `int`: Ephemeral port (0)

## Decorators

### @register_protocol

Decorator for registering protocol plugins with metadata.

**Module**: `panther.plugins.core.plugin_decorators`

```python
@register_protocol(
    name: str,
    type: str = "client_server",
    versions: List[str] = None,
    default_version: str = None,
    description: str = "",
    author: str = "",
    license: str = "",
    homepage: str = "",
    capabilities: List[str] = None,
    tags: List[str] = None,
    config_schema: Dict = None,
    default_config: Dict = None
)
```

**Parameters:**
- `name` (str): Protocol identifier (e.g., "quic", "http")
- `type` (str): Protocol category ("client_server" or "peer_to_peer")
- `versions` (List[str]): Supported protocol versions
- `default_version` (str): Default version to use
- `description` (str): Human-readable protocol description
- `author` (str): Protocol implementation author
- `license` (str): Protocol license information
- `homepage` (str): Protocol specification or documentation URL
- `capabilities` (List[str]): Protocol capabilities and features
- `tags` (List[str]): Categorization tags
- `config_schema` (Dict): JSON schema for configuration validation
- `default_config` (Dict): Default configuration values

**Example:**
```python
@register_protocol(
    name="custom_protocol",
    type="client_server",
    versions=["v1.0", "v1.1"],
    default_version="v1.0",
    capabilities=["encryption", "compression"],
    config_schema={
        "port": {"type": "integer", "default": 8080},
        "timeout": {"type": "integer", "default": 30}
    },
    default_config={
        "port": 8080,
        "timeout": 30
    }
)
class CustomProtocol(IProtocolManager):
    ...
```

## Configuration Schema

### QUIC Configuration Schema

```json
{
    "initial_max_data": {
        "type": "integer",
        "default": 10485760,
        "description": "Initial maximum data limit for the connection"
    },
    "initial_max_stream_data_bidi_local": {
        "type": "integer",
        "default": 1048576,
        "description": "Initial maximum data for locally-initiated bidirectional streams"
    },
    "initial_max_stream_data_bidi_remote": {
        "type": "integer",
        "default": 1048576,
        "description": "Initial maximum data for remotely-initiated bidirectional streams"
    },
    "initial_max_stream_data_uni": {
        "type": "integer",
        "default": 1048576,
        "description": "Initial maximum data for unidirectional streams"
    },
    "initial_max_streams_bidi": {
        "type": "integer",
        "default": 100,
        "description": "Initial maximum number of bidirectional streams"
    },
    "initial_max_streams_uni": {
        "type": "integer",
        "default": 100,
        "description": "Initial maximum number of unidirectional streams"
    },
    "max_idle_timeout": {
        "type": "integer",
        "default": 30000,
        "description": "Maximum idle timeout in milliseconds"
    },
    "alpn_protocols": {
        "type": "array",
        "items": {"type": "string"},
        "default": ["h3", "hq-interop"],
        "description": "ALPN protocols to negotiate"
    }
}
```

### Version Parameters

#### QUIC Version Parameters

```python
{
    "rfc9000": {
        "initial_version": "00000001",
        "version_negotiation": True,
        "compatible_versions": ["rfc9000"]
    },
    "draft-29": {
        "initial_version": "ff00001d",  # 0xFF00001D
        "version_negotiation": True,
        "compatible_versions": ["draft-29"]
    },
    "draft-27": {
        "initial_version": "ff00001b",  # 0xFF00001B
        "version_negotiation": True,
        "compatible_versions": ["draft-27"]
    },
    "draft-27-vuln1": {
        "initial_version": "ff00001b",
        "version_negotiation": True,
        "compatible_versions": ["draft-27"],
        "enable_vuln_test": "vuln1"
    },
    "draft-27-vuln2": {
        "initial_version": "ff00001b",
        "version_negotiation": True,
        "compatible_versions": ["draft-27"],
        "enable_vuln_test": "vuln2"
    }
}
```

## Usage Examples

### Basic Protocol Usage

```python
from panther.plugins.protocols.client_server.quic import QUICProtocol

# Initialize protocol
protocol = QUICProtocol()

# Load configuration
config = protocol.load_config()
print(f"Max data: {config['initial_max_data']}")

# Get version parameters
rfc9000_params = protocol.get_version_parameters('rfc9000')
print(f"Version: {rfc9000_params['initial_version']}")

# Get default ports
server_port = protocol.get_default_server_port()  # 4443
client_port = protocol.get_default_client_port()  # 0
```

### Protocol Discovery

```python
from panther.plugins.core.plugin_catalog import PluginCatalog

# Get all protocols
catalog = PluginCatalog()
protocols = catalog.get_protocols()

# Filter by type
quic_protocols = catalog.get_protocols_by_name("quic")
client_server_protocols = catalog.get_protocols_by_type("client_server")

# Get protocol metadata
for protocol in protocols:
    print(f"Name: {protocol.name}")
    print(f"Versions: {protocol.versions}")
    print(f"Capabilities: {protocol.capabilities}")
```

### Custom Protocol Implementation

```python
from panther.plugins.protocols.protocol_interface import IProtocolManager
from panther.plugins.core.plugin_decorators import register_protocol

@register_protocol(
    name="my_protocol",
    type="client_server",
    versions=["v1.0"],
    config_schema={
        "custom_param": {
            "type": "string",
            "default": "default_value"
        }
    }
)
class MyProtocol(IProtocolManager):
    """Custom protocol implementation."""

    def __init__(self):
        self.logger = logging.getLogger("MyProtocol")

    def validate_config(self):
        """Validate configuration."""
        pass

    def load_config(self) -> dict:
        """Load configuration."""
        return self.get_protocol_metadata().get("default_config", {})

    def get_version_parameters(self, version: str) -> dict:
        """Get version parameters."""
        return {"version": version}

    @classmethod
    def get_default_server_port(cls) -> int:
        return 9999

    @classmethod
    def get_default_client_port(cls) -> int:
        return 0
```

## Error Handling

### Common Exceptions

- `FileNotFoundError`: Configuration file not found
- `yaml.YAMLError`: Invalid YAML configuration
- `ValueError`: Invalid configuration values
- `KeyError`: Missing required configuration fields
- `TypeError`: Incorrect parameter types

### Error Handling Patterns

```python
try:
    protocol = QUICProtocol()
    config = protocol.load_config()
except FileNotFoundError as e:
    logger.error(f"Configuration file not found: {e}")
except yaml.YAMLError as e:
    logger.error(f"Invalid YAML configuration: {e}")
except ValueError as e:
    logger.error(f"Configuration validation failed: {e}")
```

## Type Hints

All public APIs include complete type hints for better IDE support and static analysis:

```python
from typing import Dict, List, Optional, Union

def get_version_parameters(self, version: str) -> Dict[str, Union[str, bool, List[str]]]:
    """Get version-specific parameters with full type hints."""
    pass
```

## Thread Safety

Protocol instances are designed to be thread-safe for concurrent testing scenarios:

- Configuration loading is performed once during initialization
- Version parameters are computed dynamically without state modification
- Class methods for default ports are stateless
- Logger instances are thread-safe

## Performance Considerations

- **Lazy Loading**: Configuration loaded only when needed
- **Caching**: Version parameters computed on-demand but can be cached
- **Memory Efficiency**: Minimal memory footprint per protocol instance
- **No Network I/O**: All operations are local configuration access
