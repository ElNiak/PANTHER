# PANTHER Plugin Development Guide

This guide provides detailed instructions for creating new plugins for the PANTHER framework across all plugin types.

!!! warning "Development Prerequisites"
    Before starting plugin development, ensure you understand PANTHER's architecture by reading the [WORKFLOW.md](../../WORKFLOW.md) and have a working PANTHER installation following the [INSTALL.md](../../INSTALL.md) guide.

## Development Guides

Comprehensive development documentation for each plugin category:

- **[Service Plugin Development](panther/plugins/services/development.md)**: Creating IUT and tester plugins
- **[Protocol Plugin Development](panther/plugins/protocols/development.md)**: Adding protocol support
- **[Environment Plugin Development](panther/plugins/environments/development.md)**: Environment management plugins
- **[General Plugin Development](panther/plugins/development.md)**: Common plugin development patterns

## Modern Inheritance-Based Architecture (2024)

!!! success "Base Class System"
    PANTHER now uses an inheritance-based architecture with specialized base classes that eliminate code duplication and provide consistent behavior. All new plugins should inherit from appropriate base classes rather than implementing functionality from scratch.

**Architectural Evolution**: The modern PANTHER plugin system has evolved from a traditional interface-based approach to a sophisticated inheritance hierarchy that provides:
- **47.2% Average Code Reduction**: Eliminate duplicate functionality across plugin implementations
- **Consistent Behavior**: Shared functionality and event integration across all plugin types
- **Automatic Updates**: New features and fixes in base classes automatically benefit all derived plugins
- **Comprehensive Integration**: Built-in support for event management, configuration resolution, and error handling

### Base Class Hierarchy

```text
BaseQUICServiceManager              # Core QUIC functionality
├── PythonQUICServiceManager       # Python-specific extensions (aioquic)
├── RustQUICServiceManager         # Rust-specific extensions (quiche, quinn)
└── Direct inheritance             # C/Go implementations (picoquic, lsquic, etc.)

DockerBuilderFactory               # Docker build patterns
├── QUICDockerBuilder              # QUIC-specific build configurations
├── RustDockerBuilder              # Rust compilation patterns
└── PythonDockerBuilder            # Python async patterns
```

### Template Method Pattern

The modern architecture uses the template method pattern where base classes define the workflow and subclasses implement specific details:

```python
# Modern plugin implementation
from panther.plugins.services.base.quic_service_base import BaseQUICServiceManager

class MyQuicImplementation(BaseQUICServiceManager):
    """Modern QUIC implementation using inheritance."""

    def _get_implementation_name(self) -> str:
        return "my_quic"

    def _get_binary_name(self) -> str:
        return "my_quic_server"

    def _get_server_specific_args(self, **kwargs) -> List[str]:
        port = kwargs.get("port", 4443)
        return ["-p", str(port)]

    def _get_client_specific_args(self, **kwargs) -> List[str]:
        host = kwargs.get("host", "localhost")
        port = kwargs.get("port", 4443)
        return [host, str(port)]

    # All common functionality inherited automatically!
```

### Benefits of Inheritance Architecture

- **47.2% Average Code Reduction**: Eliminate duplicate command generation logic
- **Consistent Behavior**: Common functionality shared across implementations
- **Automatic Updates**: New features in base classes automatically available
- **Event Integration**: Built-in event emission for monitoring
- **Command Processing**: Structured command generation through Command Processor
- **Error Handling**: Comprehensive error handling and recovery

### Migration Guide: From Legacy to Modern Architecture

If you have existing plugins using the old architecture, follow this migration guide:

#### Step 1: Identify the Appropriate Base Class

```python
# OLD: Manual implementation
class LegacyQuicPlugin:
    def generate_server_command(self, **kwargs):
        # Lots of duplicate command generation logic
        port = kwargs.get("port", 4443)
        cert = kwargs.get("cert_file", "")
        # ... extensive manual implementation
        return f"my_server -p {port} -c {cert} ..."

# NEW: Inherit from base class
from panther.plugins.services.base.quic_service_base import BaseQUICServiceManager

class ModernQuicPlugin(BaseQUICServiceManager):
    def _get_implementation_name(self) -> str:
        return "my_quic"

    def _get_server_specific_args(self, **kwargs) -> List[str]:
        port = kwargs.get("port", 4443)
        return ["-p", str(port)]

    # 90% of the logic is now inherited!
```

#### Step 2: Remove Duplicate Code

Delete these methods that are now provided by base classes:
- `generate_run_command()` → Provided by `BaseQUICServiceManager`
- `_extract_common_params()` → Provided by base class
- `_build_server_args()` → Provided by base class
- Event emission logic → Provided by base class
- Docker build patterns → Use `DockerBuilderFactory`

#### Step 3: Implement Required Abstract Methods

```python
class ModernQuicPlugin(BaseQUICServiceManager):
    # REQUIRED: Implement these abstract methods
    def _get_implementation_name(self) -> str:
        return "my_implementation"

    def _get_binary_name(self) -> str:
        return "my_binary"

    def _get_server_specific_args(self, **kwargs) -> List[str]:
        # Return implementation-specific server arguments
        pass

    def _get_client_specific_args(self, **kwargs) -> List[str]:
        # Return implementation-specific client arguments
        pass

    def generate_deployment_commands(self) -> str:
        # Return deployment commands
        pass

    def _do_prepare(self, plugin_manager=None):
        # Implementation-specific preparation
        pass
```

### Docker Build Base Classes

Modern plugins use shared Docker build patterns through the `DockerBuilderFactory`:

```python
from panther.plugins.services.base.docker_build_base import DockerBuilderFactory

# Use predefined builder for common implementations
class ModernQuicPlugin(BaseQUICServiceManager):
    def _get_docker_builder(self):
        return DockerBuilderFactory.create_builder(
            implementation_name=self._get_implementation_name(),
            language="rust",  # or "python", "c", "go"
            repo_url="https://github.com/example/my-quic.git",
            build_features=["async", "tls13"]
        )

    def generate_dockerfile_content(self) -> str:
        builder = self._get_docker_builder()
        return builder.generate_complete_dockerfile()
```

#### Available Docker Builders

```python
# Predefined builders from DockerBuilderFactory
QUIC_DOCKER_BUILDERS = {
    "picoquic": PicoquicDockerBuilder(),
    "aioquic": AioquicDockerBuilder(),
    "quiche": QuicheDockerBuilder(),
    "quinn": QuinnDockerBuilder(),
    "lsquic": LsquicDockerBuilder(),
    # ... more implementations
}

# Custom builder creation
builder = DockerBuilderFactory.create_builder(
    implementation_name="my_quic",
    language="rust",
    repo_url="https://github.com/my-org/my-quic.git",
    cargo_features=["async-std", "ring"],
    build_commands=[
        "cargo build --release --features async-std,ring",
        "cp target/release/my-quic /usr/local/bin/"
    ]
)
```

## Interactive Plugin Creation

> **New Feature**: Plugins now support Jinja2 templates for dynamic code generation and better subplugin integration.

PANTHER provides tools to easily create new plugins from templates:

### Tutorial Launcher (Recommended)

!!! tip "Recommended Method"
    The tutorial launcher is the easiest way to get started with plugin development:

```bash
# From the PANTHER root directory
python -m panther --interactive-tutorials
```

The tutorial launcher provides a menu-driven interface to access all available tutorials.

```bash
# Run tutorials
panther --tutorial service
panther --tutorial environment
panther --tutorial protocol
```

### Creating Plugins and Subplugins

1. **Top-level plugin creation**: Using `--create-plugin TYPE NAME`
2. **Subplugin creation**: Using `--create-subplugin PLUGIN_TYPE PLUGIN_NAME SUBPLUGIN_TYPE`
3. **Complete plugin setup**: Using `--create-plugin TYPE NAME --with-subplugins`

```bash
# First create the main plugin structure
python -m panther --create-plugin service my_protocol

# Then create the IUT subplugin
python -m panther --create-subplugin service my_protocol iut

# Then create the Tester subplugin
python -m panther --create-subplugin service my_protocol tester

# Create a complete service plugin with all subplugins
python -m panther --create-plugin service my_protocol --with-subplugins

# Create a network environment subplugin
python -m panther --create-subplugin environment my_env network_environment

# Create an execution environment subplugin
python -m panther --create-subplugin environment my_env execution_environment
```

### Development vs Production Mode

When creating plugins, PANTHER automatically detects whether you're in development mode (GitHub cloned repository) or production mode (installed package):

- **Development Mode**: Plugins are created in the repository structure
- **Production Mode**: Plugins are created in `~/.panther/plugins/`

You can explicitly specify the mode:

```bash
# Force development mode (put plugins in source tree)
panther --create-plugin protocol my_protocol --dev-mode

# Force production mode (put plugins in user directory)
panther --create-plugin service my_service --production-mode
```

### Interactive Tutorials

For guided plugin development:

```bash
# Launch a specific tutorial
panther --tutorial service
panther --tutorial environment
panther --tutorial protocol

# Launch the interactive tutorial menu
panther --interactive-tutorials
panther --tutorial environment
panther --tutorial protocol
```

## Manual Creating a New Plugin

### 1. Choose the Plugin Type

Determine which category your plugin belongs to:

- **Environment**: Execution or network environment
- **Protocol**: Client-server or peer-to-peer protocol
- **Service**: Implementation under test (IUT) or tester

### 2. Set Up the Plugin Directory

!!! note "Plugin Directory Structure"
    This directory structure is automatically created when using the `--create-plugin` command, but you can also create it manually.

Create a directory for your plugin in the appropriate location:

```text
plugins/<plugin_type>/<plugin_name>/
├── __init__.py
├── plugin.py           # Main plugin implementation
├── config_schema.py    # Configuration schema
├── README.md           # Plugin documentation
└── tests/              # Plugin tests
    └── test_plugin.py
```

### 3. Implement the Plugin Interface

Create a class that implements the appropriate plugin interface:

```python
# plugins/<plugin_type>/<plugin_name>/plugin.py
from panther.plugins.<plugin_type>.<type>_interface import <Type>Interface

class MyPlugin(<Type>Plugin):
    """My custom PANTHER plugin."""

    def initialize(self, config):
        """Initialize the plugin with configuration."""
        self.config = config
        # Perform setup tasks

    def execute(self):
        """Execute the plugin's main functionality."""
        # Implement main functionality
        pass

    def cleanup(self):
        """Clean up resources."""
        # Release resources, close connections, etc.
        pass
```

### 4. Define Configuration Schema

Create a schema for your plugin's configuration using dataclasses and protocol-aware features:

```python
# plugins/<plugin_type>/<plugin_name>/config_schema.py
from dataclasses import dataclass
from typing import Optional, List
from panther.plugins.protocols.config_schema import ProtocolConfig

@dataclass
class MyPluginConfig:
    """Configuration schema for MyPlugin."""

    # Required parameters
    required_param: str

    # Optional parameters with defaults
    optional_param: Optional[int] = None
    timeout: int = 30

    # For protocol plugins, inherit from ProtocolConfig for port management
    # This automatically provides port validation and default assignment
    # based on protocol type (QUIC, HTTP, etc.)

# For protocol-specific plugins (e.g., QUIC implementations)
@dataclass
class MyQuicProtocolConfig(ProtocolConfig):
    """QUIC-specific configuration with automatic port management."""

    @classmethod
    def get_default_server_port(cls) -> int:
        """Define the default server port for this protocol."""
        return 4443  # QUIC default

    def get_default_port_mapping(self) -> Optional[str]:
        """Get default port mapping for this protocol configuration."""
        if self.role == "server":
            port = self.get_default_server_port()
            return f"{port}:{port}"
        return None

    def requires_server_port(self) -> bool:
        """Check if this protocol configuration requires server ports."""
        return self.role == "server"

# For service plugins, use ServiceConfig base class
from panther.plugins.services.config_schema import ServiceConfig

@dataclass
class MyServiceConfig(ServiceConfig):
    """Service configuration with automatic port validation."""

    # Service-specific configuration
    binary_path: str = "/usr/local/bin/my_service"
    log_level: str = "info"

    def validate_configuration(self) -> List[str]:
        """Custom validation logic for this service."""
        errors = []

        # Ensure server services have ports (handled automatically)
        self.ensure_server_has_ports()

        # Add custom validation
        if self.binary_path and not self.binary_path.startswith('/'):
            errors.append("Binary path must be absolute")

        return errors
```

#### Configuration Management Features

Your plugin configuration automatically benefits from PANTHER's advanced configuration management:

**Port Management:**
- **Automatic port assignment** for server services based on protocol defaults
- **Port conflict detection** and resolution
- **Protocol-aware validation** (QUIC uses 4443, HTTP uses 80, etc.)

**Validation:**
- **Schema-based validation** with clear error messages
- **Business rule validation** for cross-service dependencies
- **Custom validation** through `validate_configuration()` methods

**Auto-fixing:**
- **Automatic port assignment** when missing
- **Configuration standardization** (port format, field completion)
- **Conflict resolution** for common configuration issues

#### Example: Protocol Plugin with Port Management

```python
from dataclasses import dataclass
from panther.plugins.protocols.client_server.config_schema import ClientServerProtocolConfig

@dataclass
class MyCustomProtocolConfig(ClientServerProtocolConfig):
    """Custom protocol with automatic port management."""

    # Protocol-specific settings
    encryption_enabled: bool = True
    compression_level: int = 6

    @classmethod
    def get_default_server_port(cls) -> int:
        """Custom protocol uses port 9443."""
        return 9443

    def get_supported_roles(self) -> List[str]:
        """Define supported roles for this protocol."""
        return ["server", "client", "proxy"]

    def validate_role_specific_config(self) -> List[str]:
        """Validate role-specific configuration."""
        errors = []

        if self.role == "proxy" and not self.encryption_enabled:
            errors.append("Proxy role requires encryption to be enabled")

        return errors
```

This configuration automatically provides:
- Port 9443 assignment for server services
- Validation that servers have required ports
- Auto-fixing for missing port configurations
- Integration with PANTHER's configuration validation system

### 5. Register Your Plugin

**Modern Registration System**: PANTHER uses a decorator-based registration system that automatically discovers and validates plugins during import. This eliminates the need for manual registration and provides comprehensive metadata management.

#### Using the @register_plugin Decorator

```python
# plugins/<plugin_type>/<plugin_name>/plugin.py
from panther.plugins.core.plugin_decorators import register_plugin
from panther.plugins.core.structures.plugin_type import PluginType

@register_plugin(
    plugin_type=PluginType.IUT,
    name="my_implementation",
    version="1.0.0",
    author="Your Name",
    description="Enhanced implementation with advanced features",
    license="MIT",
    homepage="https://github.com/your-org/my-implementation",
    min_panther_version="1.0.0",
    dependencies=["quic_protocol>=1.0.0"],
    config_schema={
        "type": "object",
        "properties": {
            "timeout": {"type": "number", "default": 60, "minimum": 1},
            "host": {"type": "string", "default": "localhost"},
            "port": {"type": "number", "minimum": 1, "maximum": 65535}
        },
        "required": ["host", "port"]
    },
    default_config={"timeout": 60, "generate_certificates": True},
    supported_protocols=["quic"],
    capabilities=["rfc9000", "0rtt", "migration", "async"],
    tags=["quic", "implementation", "c"],
    external_dependencies=["docker>=20.0", "openssl>=1.1.1"],
    runtime_mode="minimal"
)
class MyImplementationServiceManager(BaseQUICServiceManager):
    """Modern QUIC implementation using comprehensive registration."""

    def _get_implementation_name(self) -> str:
        return "my_implementation"

    def _get_binary_name(self) -> str:
        return "my_implementation_server"

    # Implementation-specific methods...
```

#### Registration Benefits

The decorator-based registration provides:

- **Automatic Discovery**: Plugins are automatically discovered during system startup
- **Metadata Validation**: Comprehensive validation of plugin metadata during registration
- **Dependency Management**: Automatic dependency resolution with semantic versioning
- **Version Configuration**: Support for protocol version-specific configurations
- **Schema Integration**: JSON Schema validation for plugin configurations
- **Performance Optimization**: Registration metadata cached for fast access

#### Legacy Registration Support

For backward compatibility, you can still update `__init__.py` for manual imports:

```python
# plugins/<plugin_type>/<plugin_name>/__init__.py
from .plugin import MyPlugin

__all__ = ["MyPlugin"]
```

#### Plugin Discovery Process

The registration system follows this discovery workflow:

1. **Import Phase**: Decorators execute during module import, storing metadata in global registry
2. **Discovery Phase**: PluginManager scans registered plugins during system initialization
3. **Validation Phase**: Plugin metadata validated for consistency and dependencies
4. **Instantiation Phase**: PluginFactory uses metadata for type-safe plugin creation
5. **Runtime Phase**: EventManager coordinates plugin lifecycle with automatic event emission

### 6. Create Tests

Write tests to verify your plugin functions correctly:

```python
# plugins/<plugin_type>/<plugin_name>/tests/test_plugin.py
import pytest
from panther.plugins.<plugin_type>.<plugin_name>.plugin import MyPlugin

def test_plugin_initialization():
    plugin = MyPlugin()
    config = {"required_param": "test"}
    plugin.initialize(config)
    # Assert expected behavior

def test_plugin_execution():
    plugin = MyPlugin()
    plugin.initialize({"required_param": "test"})
    result = plugin.execute()
    # Assert expected behavior
```

### 7. Document Your Plugin

Create a `README.md` file using the [plugin template](panther/plugins/plugin_template.md) that includes:

- Purpose and overview
- Requirements and dependencies
- Configuration options
- Usage examples
- Extension points
- Testing and verification

## Advanced Usage: Custom Plugin Directories

> **Work in Progress**

PANTHER supports specifying custom directories for different plugin types through CLI arguments:

```bash
# Specify custom directories for plugin discovery
python -m panther --exec-env-dir /path/to/custom/execution/env \
                 --net-env-dir /path/to/custom/network/env \
                 --iut-dir /path/to/custom/iut \
                 --tester-dir /path/to/custom/tester
```

These arguments are useful when:

1. Developing plugins outside the main PANTHER directory structure
2. Using plugins from multiple sources
3. Testing plugins without installing them in the standard locations
4. Using organization-specific plugin collections
