# Protocol Plugin Development Guide

**Creating and extending protocol testing capabilities in PANTHER**

This guide provides comprehensive instructions for developing protocol plugins that define testing logic and configurations for specific network protocols within the PANTHER framework.

## Overview

Protocol plugins enable PANTHER to test different network protocols by defining:

- **Test Scenarios**: Standard conformance and performance tests
- **Configuration Parameters**: Protocol-specific settings and options
- **Validation Rules**: Criteria for determining test success/failure
- **Protocol Behavior**: Expected interactions and message flows

<!-- src: /panther/plugins/protocols/protocol_interface.py -->

## Development Setup

### Prerequisites

Before creating a protocol plugin, ensure you have:

1. **PANTHER Development Environment**: Complete PANTHER framework installation
2. **Protocol Specification**: Access to protocol RFCs, drafts, or specifications
3. **Reference Implementation**: At least one working implementation for testing
4. **Test Vector Knowledge**: Understanding of expected protocol behaviors

### Development Tools

```bash
# Install development dependencies
pip install -e .[dev]

# Run tests during development
pytest tests/unit/plugins/protocols/

# Validate plugin structure
python -m panther.plugins.plugin_loader --validate protocols
```

## Plugin Architecture

### Directory Structure

Create your protocol plugin following this structure:

```text
plugins/protocols/
├── client_server/           # or peer_to_peer/
│   └── your_protocol/      # Protocol name (e.g., "quic", "http")
│       ├── __init__.py
│       ├── README.md       # Protocol-specific documentation
│       ├── config_schema.py # Configuration validation
│       ├── protocol_plugin.py # Main implementation
│       ├── test_scenarios/ # Test scenario definitions
│       │   ├── __init__.py
│       │   ├── conformance.py
│       │   ├── performance.py
│       │   └── interop.py
│       └── versions/       # Protocol version support
│           ├── __init__.py
│           ├── v1_0/
│           └── v2_0/
```

### Base Protocol Interface

All protocol plugins must implement the `ProtocolInterface`:

```python
# filepath: /panther/plugins/protocols/protocol_interface.py
from abc import ABC, abstractmethod
from panther.plugins.plugin_interface import IPlugin

class ProtocolInterface(IPlugin):
    """Base interface for all protocol plugins."""

    @abstractmethod
    def get_supported_versions(self) -> list:
        """Return list of supported protocol versions."""
        pass

    @abstractmethod
    def get_test_scenarios(self) -> dict:
        """Return available test scenarios by category."""
        pass

    @abstractmethod
    def validate_configuration(self, config: dict) -> bool:
        """Validate protocol-specific configuration."""
        pass

    @abstractmethod
    def setup_test_environment(self, config: dict):
        """Setup testing environment for this protocol."""
        pass

    @abstractmethod
    def execute_test_scenario(self, scenario: str, config: dict):
        """Execute a specific test scenario."""
        pass
```

## Implementation Steps

### Step 1: Configuration Schema

Define your protocol's configuration schema in `config_schema.py`:

```python
# filepath: your_protocol/config_schema.py
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from panther.plugins.protocols.config_schema import ProtocolConfig

@dataclass
class YourProtocolConfig(ProtocolConfig):
    """Configuration schema for YourProtocol."""

    # Protocol version
    version: str = "1.0"

    # Protocol-specific parameters
    connection_timeout: int = 30
    max_packet_size: int = 1500
    enable_feature_x: bool = True

    # Test configuration
    test_scenarios: List[str] = field(default_factory=lambda: ["handshake", "data_transfer"])
    validation_rules: List[str] = field(default_factory=lambda: ["conformance"])

    # Advanced options
    custom_parameters: Dict[str, str] = field(default_factory=dict)
```

### Step 2: Main Plugin Implementation

Create your protocol plugin class in `protocol_plugin.py`:

```python
# filepath: your_protocol/protocol_plugin.py
from typing import Dict, List
from panther.plugins.protocols.protocol_interface import ProtocolInterface
from .config_schema import YourProtocolConfig

class YourProtocolPlugin(ProtocolInterface):
    """Protocol plugin for YourProtocol testing."""

    def __init__(self):
        super().__init__()
        self.config = None
        self.supported_versions = ["1.0", "1.1", "2.0"]

    def get_supported_versions(self) -> List[str]:
        """Return supported protocol versions."""
        return self.supported_versions

    def get_test_scenarios(self) -> Dict[str, List[str]]:
        """Return available test scenarios by category."""
        return {
            "conformance": [
                "handshake",
                "data_transfer",
                "error_handling",
                "connection_close"
            ],
            "performance": [
                "throughput",
                "latency",
                "connection_setup_time"
            ],
            "interoperability": [
                "version_negotiation",
                "extension_support"
            ]
        }

    def validate_configuration(self, config: dict) -> bool:
        """Validate protocol configuration."""
        try:
            self.config = YourProtocolConfig(**config)
            # Add custom validation logic
            if self.config.version not in self.supported_versions:
                raise ValueError(f"Unsupported version: {self.config.version}")
            return True
        except Exception as e:
            self.logger.error(f"Configuration validation failed: {e}")
            return False

    def setup_test_environment(self, config: dict):
        """Setup testing environment."""
        if not self.validate_configuration(config):
            raise ValueError("Invalid configuration")

        # Setup protocol-specific environment
        self._setup_protocol_handlers()
        self._configure_test_parameters()

    def execute_test_scenario(self, scenario: str, config: dict):
        """Execute a test scenario."""
        if scenario == "handshake":
            return self._test_handshake()
        elif scenario == "data_transfer":
            return self._test_data_transfer()
        # ... other scenarios

    def _test_handshake(self):
        """Test protocol handshake."""
        # Implement handshake testing logic
        pass

    def _test_data_transfer(self):
        """Test data transfer functionality."""
        # Implement data transfer testing logic
        pass
```

### Step 3: Test Scenarios

Organize test scenarios in separate modules for maintainability:

```python
# filepath: your_protocol/test_scenarios/conformance.py
from typing import Dict, Any

class ConformanceTests:
    """Conformance test scenarios for YourProtocol."""

    @staticmethod
    def handshake_test(config: Dict[str, Any]) -> Dict[str, Any]:
        """Test protocol handshake conformance."""
        return {
            "test_name": "handshake_conformance",
            "description": "Verify protocol handshake follows specification",
            "steps": [
                "initiate_connection",
                "exchange_parameters",
                "verify_handshake_completion"
            ],
            "success_criteria": [
                "connection_established",
                "parameters_negotiated",
                "no_protocol_errors"
            ]
        }
```

### Step 4: Plugin Registration

Register your plugin in `__init__.py`:

```python
# filepath: your_protocol/__init__.py
from .protocol_plugin import YourProtocolPlugin

__all__ = ["YourProtocolPlugin"]

# Plugin metadata
PLUGIN_NAME = "your_protocol"
PLUGIN_VERSION = "1.0.0"
PLUGIN_DESCRIPTION = "YourProtocol testing plugin"
PLUGIN_CLASS = YourProtocolPlugin
```

## Testing Your Plugin

### Unit Tests

Create comprehensive unit tests for your plugin:

```python
# filepath: tests/unit/plugins/protocols/test_your_protocol.py
import pytest
from panther.plugins.protocols.your_protocol import YourProtocolPlugin

class TestYourProtocolPlugin:

    def setup_method(self):
        self.plugin = YourProtocolPlugin()

    def test_supported_versions(self):
        versions = self.plugin.get_supported_versions()
        assert "1.0" in versions
        assert len(versions) > 0

    def test_configuration_validation(self):
        valid_config = {
            "version": "1.0",
            "connection_timeout": 30
        }
        assert self.plugin.validate_configuration(valid_config)

        invalid_config = {
            "version": "invalid_version"
        }
        assert not self.plugin.validate_configuration(invalid_config)

    def test_test_scenarios(self):
        scenarios = self.plugin.get_test_scenarios()
        assert "conformance" in scenarios
        assert "handshake" in scenarios["conformance"]
```

### Integration Tests

Test your plugin with the PANTHER framework:

```bash
# Test plugin loading
python -c "
from panther.plugins.plugin_loader import PluginLoader
loader = PluginLoader()
plugin = loader.load_plugin('protocols', 'client_server', 'your_protocol')
print('Plugin loaded successfully')
"

# Run integration test
python -m panther --config test_configs/your_protocol_test.yaml --dry-run
```

## Configuration Integration

### Adding to Experiment Configuration

Update experiment configuration to include your protocol:

```yaml
# filepath: experiment-config/your_protocol_example.yaml
experiment:
  name: "YourProtocol Testing"
  description: "Conformance and performance testing for YourProtocol"

protocol:
  name: "your_protocol"
  version: "1.0"
  configuration:
    connection_timeout: 30
    max_packet_size: 1500
    test_scenarios: ["handshake", "data_transfer"]
    validation_rules: ["conformance", "performance"]

services:
  iut: "your_protocol_implementation"
  tester: "generic_tester"

environment:
  execution: "default"
  network: "docker_compose"
```

## Best Practices

### Code Quality

1. **Follow PEP 8**: Use consistent Python coding style
2. **Type Hints**: Add type annotations for better code clarity
3. **Docstrings**: Document all public methods and classes
4. **Error Handling**: Provide meaningful error messages and logging

### Protocol Implementation

1. **Specification Compliance**: Ensure tests match protocol specifications
2. **Version Support**: Handle multiple protocol versions gracefully
3. **Extensibility**: Design for future protocol extensions
4. **Performance**: Optimize for test execution speed

### Testing

1. **Comprehensive Coverage**: Test normal and edge cases
2. **Mock External Dependencies**: Use mocks for network interactions
3. **Reproducible Tests**: Ensure tests run consistently
4. **Documentation**: Include test scenario documentation

## Common Pitfalls

### Configuration Issues

- **Missing Validation**: Always validate configuration parameters
- **Default Values**: Provide sensible defaults for optional parameters
- **Type Checking**: Ensure parameter types match expectations

### Test Implementation

- **Timeout Handling**: Always set appropriate timeouts for network operations
- **State Management**: Clean up test state between scenarios
- **Error Propagation**: Properly handle and report test failures

### Integration Problems

- **Plugin Discovery**: Ensure proper plugin registration and naming
- **Dependency Management**: Handle dependencies on other plugins gracefully
- **Resource Cleanup**: Always clean up resources after tests

## Debugging Tips

### Plugin Loading Issues

```bash
# Check plugin discovery
python -m panther.plugins.plugin_loader --list protocols

# Validate plugin structure
python -m panther.plugins.plugin_loader --validate protocols your_protocol
```

### Configuration Problems

```python
# Test configuration validation in isolation
from your_protocol.config_schema import YourProtocolConfig

try:
    config = YourProtocolConfig(**your_config_dict)
    print("Configuration valid")
except Exception as e:
    print(f"Configuration error: {e}")
```

### Test Execution Issues

- **Enable Debug Logging**: Set logging level to DEBUG
- **Use Dry Run Mode**: Test configuration without actual execution
- **Check Service Logs**: Examine IUT and tester service logs
- **Network Capture**: Use packet capture tools for network-level debugging

## Contributing Your Plugin

### Code Review Checklist

Before submitting your plugin:

- [ ] All unit tests pass
- [ ] Integration tests work with framework
- [ ] Documentation is complete and accurate
- [ ] Code follows project style guidelines
- [ ] Configuration schema is well-defined
- [ ] Error handling is comprehensive

### Documentation Requirements

- [ ] Plugin README with usage examples
- [ ] Configuration parameter documentation
- [ ] Test scenario descriptions
- [ ] Integration guide for experiments
- [ ] Known limitations and troubleshooting

### Submission Process

1. **Fork Repository**: Create a fork of the PANTHER repository
2. **Create Branch**: Use descriptive branch name (e.g., `feature/add-your-protocol`)
3. **Implement Plugin**: Follow this development guide
4. **Add Tests**: Include comprehensive test coverage
5. **Update Documentation**: Add plugin to inventory and guides
6. **Submit PR**: Create pull request with detailed description

## API Reference

For detailed API documentation:

- **[Protocol Interface](panther/plugins/protocol_interface.py)**: Base interface requirements
- **[Configuration Schema](panther/plugins/config_schema.py)**: Base configuration structure
- **[Plugin Loader](panther/plugins/plugin_loader.py)**: Plugin discovery and loading
- **[Test Examples](test_scenarios/)**: Example test implementations

## Creating a New Protocol Plugin

### 1. Choose Protocol Type

Determine whether your protocol follows a client-server or peer-to-peer architecture.

### 2. Set Up the Plugin Directory

Create a directory for your protocol in the appropriate location:

```
plugins/protocols/<type>/<protocol_name>/
├── __init__.py
├── plugin.py           # Main protocol implementation
├── config_schema.py    # Configuration schema
├── README.md           # Protocol documentation
└── tests/              # Protocol tests
    └── test_plugin.py
```

### 3. Implement the Protocol Interface

Create a class that implements the ProtocolInterface:

```python
# plugins/protocols/<type>/<protocol_name>/plugin.py
from panther.plugins.protocols.protocol_interface import ProtocolInterface

class MyProtocol(ProtocolInterface):
    """My custom protocol implementation."""

    def initialize(self, config):
        """Initialize the protocol with configuration."""
        self.config = config
        # Protocol initialization

    def execute(self):
        """Execute the protocol's main functionality."""
        # Protocol execution logic
        pass

    def get_protocol_version(self):
        """Get the version of the protocol."""
        return self.config.get("version", "1.0")

    def get_protocol_parameters(self):
        """Get the protocol parameters."""
        return self.config.get("parameters", {})

    def cleanup(self):
        """Clean up resources."""
        # Release resources, close connections, etc.
        pass
```

### 4. Define Configuration Schema

Create a schema for your protocol's configuration:

```python
# plugins/protocols/<type>/<protocol_name>/config_schema.py
from panther.core.config.schema import Schema, Optional, And, Or

# Define the configuration schema
schema = Schema({
    Optional("version"): str,
    Optional("parameters"): {
        str: object  # Parameter name: parameter value
    },
    # Protocol-specific parameters
})
```

### 5. Register Your Protocol Plugin

Make your protocol discoverable by updating your `__init__.py`:

```python
# plugins/protocols/<type>/<protocol_name>/__init__.py
from .plugin import MyProtocol

__all__ = ["MyProtocol"]
```

### 6. Create Tests

Write tests to verify your protocol functions correctly:

```python
# plugins/protocols/<type>/<protocol_name>/tests/test_plugin.py
import pytest
from panther.plugins.protocols.<type>.<protocol_name>.plugin import MyProtocol

def test_protocol_initialization():
    protocol = MyProtocol()
    config = {"version": "1.0"}
    protocol.initialize(config)
    assert protocol.get_protocol_version() == "1.0"

def test_protocol_execution():
    protocol = MyProtocol()
    protocol.initialize({"version": "1.0"})
    result = protocol.execute()
    # Assert expected behavior
```

### 7. Document Your Protocol

Create a README.md file using the [plugin template](panther/plugins/plugin_template.md) that includes:

- Protocol purpose and specifications
- Supported versions and features
- Configuration options
- Usage examples
- Integration with services
- Testing and verification

## Best Practices for Protocol Plugins

1. **Version Support**: Clearly document which protocol versions are supported
2. **Error Handling**: Provide clear error messages for protocol failures
3. **Protocol Parameters**: Document all configurable protocol parameters
4. **Interoperability**: Test with multiple implementations when possible
5. **Metrics**: Include performance and conformance metrics

## Testing Your Protocol

Protocol testing should include:

1. **Unit Tests**: Test individual protocol components
2. **Integration Tests**: Test with compatible services
3. **Conformance Tests**: Validate against protocol specifications
4. **Performance Tests**: Measure protocol efficiency

## Documentation Verification

Ensure all protocol documentation includes source references:

```markdown
The QUIC protocol supports connection migration.
<!-- src: /panther/plugins/protocols/client_server/quic/__init__.py -->
```
