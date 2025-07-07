# Protocol Plugin Development Guide

## Environment Setup

### Prerequisites

Ensure you have the following tools installed before developing protocol plugins:

```bash
# Python development environment
python >= 3.8
pip install -e .[dev]  # Install PANTHER in development mode

# Testing tools
pytest
pytest-cov
hypothesis  # For property-based testing

# Code quality tools
black       # Code formatting
ruff        # Linting and import sorting
mypy        # Type checking
```

### Development Environment

```bash
# Clone the PANTHER repository
git clone <repository-url>
cd panther

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install development dependencies
pip install -e .[dev,test,docs]

# Verify installation
python -m panther --version
pytest tests/plugins/protocols/ -v
```

### IDE Configuration

Configure your IDE with the following settings:

**VSCode** (`\.vscode/settings.json`):
```json
{
    "python.defaultInterpreterPath": "./venv/bin/python",
    "python.linting.enabled": true,
    "python.linting.ruffEnabled": true,
    "python.formatting.provider": "black",
    "python.testing.pytestEnabled": true,
    "python.testing.pytestArgs": ["tests/"]
}
```

**PyCharm**:
- Set Python interpreter to `./venv/bin/python`
- Enable code inspections for PEP 8
- Configure pytest as default test runner
- Set up Black as external formatter

## Development Workflow

### 1. Planning Phase

Before implementing a new protocol plugin:

```bash
# Create feature branch
git checkout -b feature/protocol-<protocol-name>

# Document the protocol specification
# Create docs/protocols/<protocol-name>-spec.md
```

Requirements to document:
- Protocol RFC or specification reference
- Supported versions and variations
- Key capabilities and features
- Configuration parameters needed
- Port assignments and conventions
- Testing scenarios required

### 2. Implementation Phase

#### Create Protocol Directory Structure

```bash
# For client-server protocols
mkdir -p panther/plugins/protocols/client_server/<protocol-name>
touch panther/plugins/protocols/client_server/<protocol-name>/__init__.py
touch panther/plugins/protocols/client_server/<protocol-name>/README.md
touch panther/plugins/protocols/client_server/<protocol-name>/<protocol-name>.py

# For peer-to-peer protocols
mkdir -p panther/plugins/protocols/peer_to_peer/<protocol-name>
touch panther/plugins/protocols/peer_to_peer/<protocol-name>/__init__.py
touch panther/plugins/protocols/peer_to_peer/<protocol-name>/README.md
touch panther/plugins/protocols/peer_to_peer/<protocol-name>/<protocol-name>.py
```

#### Protocol Implementation Template

```python
# panther/plugins/protocols/client_server/<protocol-name>/<protocol-name>.py
"""
<Protocol Name> Protocol Plugin

This plugin defines the <Protocol Name> protocol metadata including supported versions,
capabilities, and configuration schema.
"""

import logging
from panther.plugins.core.plugin_decorators import register_protocol
from panther.plugins.protocols.protocol_interface import IProtocolManager


@register_protocol(
    name="<protocol-name>",
    type="client_server",  # or "peer_to_peer"
    versions=["v1.0", "v1.1"],  # Supported versions
    default_version="v1.0",
    description="Brief protocol description",
    author="Your Name / Organization",
    license="Protocol License",
    homepage="https://protocol-spec-url.com",
    capabilities=[
        "feature1",  # Protocol capabilities
        "feature2",
        "feature3"
    ],
    tags=["transport", "secure", "category"],
    config_schema={
        "parameter1": {
            "type": "integer",
            "default": 1024,
            "description": "Parameter description"
        },
        "parameter2": {
            "type": "string",
            "default": "default_value",
            "description": "Another parameter"
        }
    },
    default_config={
        "parameter1": 1024,
        "parameter2": "default_value"
    }
)
class <ProtocolName>Protocol(IProtocolManager):
    """<Protocol Name> Protocol Manager.

    This class manages <Protocol Name> protocol configurations and provides
    version-specific parameters for <Protocol Name> implementations.
    """

    def __init__(self):
        """Initialize <Protocol Name> protocol manager.

        Sets up logging and skips parent YAML loading since configuration
        is handled through the decorator metadata system.
        """
        self.logger = logging.getLogger("<ProtocolName>Protocol")

    def validate_config(self):
        """Validate <Protocol Name> protocol configuration.

        Configuration validation is handled automatically through the schema
        defined in the register_protocol decorator.
        """
        pass

    def load_config(self) -> dict:
        """Load <Protocol Name> protocol configuration from decorator metadata.

        Returns:
            dict: Default configuration parameters for <Protocol Name>.
        """
        return self.get_protocol_metadata().get("default_config", {})

    def get_version_parameters(self, version: str) -> dict:
        """Get version-specific <Protocol Name> protocol parameters.

        Args:
            version: Protocol version identifier.

        Returns:
            dict: Version-specific parameters.
        """
        version_params = {
            "v1.0": {
                "protocol_version": "1.0",
                "features": ["basic"]
            },
            "v1.1": {
                "protocol_version": "1.1",
                "features": ["basic", "extended"]
            }
        }
        return version_params.get(version, {})

    @classmethod
    def get_default_server_port(cls) -> int:
        """Get the default server port for <Protocol Name>.

        Returns:
            int: Default server port.
        """
        return 8080  # Replace with protocol-specific port

    @classmethod
    def get_default_client_port(cls) -> int:
        """Get the default client port for <Protocol Name>.

        Returns:
            int: Default client port (usually ephemeral).
        """
        return 0  # Ephemeral port
```

### 3. Testing Phase

#### Unit Tests

Create comprehensive unit tests:

```python
# tests/plugins/protocols/test_<protocol-name>.py
import pytest
from panther.plugins.protocols.client_server.<protocol-name> import <ProtocolName>Protocol


class Test<ProtocolName>Protocol:
    """Test suite for <ProtocolName>Protocol."""

    def setup_method(self):
        """Set up test fixtures."""
        self.protocol = <ProtocolName>Protocol()

    def test_initialization(self):
        """Test protocol initialization."""
        assert self.protocol is not None
        assert hasattr(self.protocol, 'logger')

    def test_load_config(self):
        """Test configuration loading."""
        config = self.protocol.load_config()
        assert isinstance(config, dict)
        assert 'parameter1' in config
        assert config['parameter1'] == 1024

    def test_version_parameters(self):
        """Test version-specific parameters."""
        v10_params = self.protocol.get_version_parameters('v1.0')
        assert v10_params['protocol_version'] == '1.0'

        v11_params = self.protocol.get_version_parameters('v1.1')
        assert v11_params['protocol_version'] == '1.1'

    def test_default_ports(self):
        """Test default port assignments."""
        server_port = self.protocol.get_default_server_port()
        client_port = self.protocol.get_default_client_port()

        assert isinstance(server_port, int)
        assert isinstance(client_port, int)
        assert server_port > 0
        assert client_port >= 0

    def test_invalid_version(self):
        """Test handling of invalid version."""
        params = self.protocol.get_version_parameters('invalid')
        assert params == {}

    @pytest.mark.parametrize("version", ["v1.0", "v1.1"])
    def test_supported_versions(self, version):
        """Test all supported versions."""
        params = self.protocol.get_version_parameters(version)
        assert 'protocol_version' in params
```

#### Integration Tests

```python
# tests/integration/test_<protocol-name>_integration.py
import pytest
from panther.plugins.protocols.client_server.<protocol-name> import <ProtocolName>Protocol


class Test<ProtocolName>Integration:
    """Integration tests for <ProtocolName>Protocol."""

    def test_protocol_registry_integration(self):
        """Test protocol registration with plugin system."""
        # Test that protocol is discoverable
        from panther.plugins.core.plugin_catalog import PluginCatalog

        catalog = PluginCatalog()
        protocols = catalog.get_protocols_by_type("client_server")

        protocol_names = [p.name for p in protocols]
        assert "<protocol-name>" in protocol_names

    def test_metadata_validation(self):
        """Test protocol metadata validation."""
        protocol = <ProtocolName>Protocol()
        metadata = protocol.get_protocol_metadata()

        # Validate required metadata fields
        assert metadata['name'] == "<protocol-name>"
        assert metadata['type'] == "client_server"
        assert 'versions' in metadata
        assert 'config_schema' in metadata
```

### 4. Documentation Phase

#### Protocol-Specific README

```markdown
# <Protocol Name> Protocol Plugin

## Overview

Brief description of the protocol and its purpose within PANTHER.

## Protocol Specification

- **RFC/Specification**: [Link to specification]
- **Versions Supported**: v1.0, v1.1
- **Default Version**: v1.0
- **Default Ports**: Server 8080, Client ephemeral

## Configuration

### Schema

\`\`\`json
{
    "parameter1": {
        "type": "integer",
        "default": 1024,
        "description": "Parameter description"
    }
}
\`\`\`

### Example Configuration

\`\`\`python
config = {
    "parameter1": 2048,
    "parameter2": "custom_value"
}
\`\`\`

## Version Differences

### v1.0
- Basic functionality
- Standard features

### v1.1
- Extended features
- Performance improvements

## Usage Examples

\`\`\`python
from panther.plugins.protocols.client_server.<protocol-name> import <ProtocolName>Protocol

protocol = <ProtocolName>Protocol()
config = protocol.load_config()
params = protocol.get_version_parameters('v1.1')
\`\`\`

## Testing

Run protocol-specific tests:

\`\`\`bash
pytest tests/plugins/protocols/test_<protocol-name>.py -v
\`\`\`
```

### 5. Quality Assurance

#### Pre-commit Validation

```bash
# Format code
black panther/plugins/protocols/client_server/<protocol-name>/

# Lint code
ruff panther/plugins/protocols/client_server/<protocol-name>/

# Type checking
mypy panther/plugins/protocols/client_server/<protocol-name>/

# Run tests
pytest tests/plugins/protocols/test_<protocol-name>.py -v

# Test coverage
pytest tests/plugins/protocols/test_<protocol-name>.py --cov=panther.plugins.protocols.client_server.<protocol-name>
```

#### Documentation Testing

```bash
# Test that documentation examples work
python -m doctest panther/plugins/protocols/client_server/<protocol-name>/<protocol-name>.py

# Validate README links and formatting
markdownlint panther/plugins/protocols/client_server/<protocol-name>/README.md
```

## Pull Request Workflow

### 1. Pre-PR Checklist

- [ ] All tests pass locally
- [ ] Code coverage >= 90%
- [ ] Documentation updated
- [ ] Examples tested
- [ ] CHANGELOG.md updated
- [ ] No linting errors

### 2. Create Pull Request

```bash
# Push feature branch
git push origin feature/protocol-<protocol-name>

# Create PR with template
gh pr create --template .github/pull_request_template.md
```

### 3. PR Review Process

The PR should include:

1. **Clear Description**: What protocol is added and why
2. **Testing Evidence**: Test output and coverage reports
3. **Documentation**: Complete README and examples
4. **Breaking Changes**: Any compatibility concerns
5. **Performance Impact**: Resource usage considerations

### 4. Post-Merge Tasks

```bash
# Update documentation site
mkdocs build

# Run full test suite
pytest tests/ -v

# Update protocol registry
python scripts/update_protocol_registry.py
```

## Debugging and Troubleshooting

### Common Issues

#### Import Errors
```python
# Ensure proper package structure
# __init__.py files must exist in all directories
# Import paths must be correct
```

#### Configuration Validation Errors
```python
# Check config_schema format
# Ensure all required fields have defaults
# Validate JSON schema syntax
```

#### Port Conflicts
```python
# Use ephemeral ports for clients (return 0)
# Choose unique server ports not used by other protocols
# Document port usage in README
```

### Debug Tools

```bash
# Enable debug logging
export PANTHER_LOG_LEVEL=DEBUG

# Verbose test output
pytest -vv -s tests/plugins/protocols/test_<protocol-name>.py

# Profile test performance
pytest --profile tests/plugins/protocols/test_<protocol-name>.py
```

### Getting Help

- **Internal Documentation**: Check existing protocol implementations
- **Protocol Specifications**: Refer to official RFCs and specifications
- **Community**: Ask questions in project discussions
- **Code Review**: Request feedback during development

## Performance Guidelines

### Resource Efficiency

- **Lazy Loading**: Load configuration only when needed
- **Memory Management**: Avoid storing large objects in class attributes
- **Caching**: Cache expensive operations appropriately
- **Connection Pooling**: Reuse connections when possible

### Scalability Considerations

- **Concurrent Testing**: Ensure thread-safety for parallel tests
- **Resource Limits**: Respect system resource constraints
- **Cleanup**: Properly clean up resources after tests
- **Monitoring**: Include performance metrics in tests

## Security Guidelines

### Input Validation

- **Schema Validation**: All inputs validated against schema
- **Boundary Checking**: Validate ranges and limits
- **Type Safety**: Use type hints and runtime validation
- **Sanitization**: Clean untrusted input data

### Vulnerability Testing

- **Security Versions**: Create versions for vulnerability testing
- **Isolation**: Isolate security tests from production code
- **Documentation**: Document security test scenarios
- **Responsible Disclosure**: Follow security reporting procedures
