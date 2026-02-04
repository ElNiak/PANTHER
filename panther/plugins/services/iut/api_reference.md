# IUT Services API Reference

## Core Interfaces

### IImplementationManager

```python
class IImplementationManager(IServiceManager, ABC)
```

Abstract base class that defines the core contract for all IUT implementations.

#### Attributes

- **service_config_to_test** (`ServiceConfig`): The configuration of the service to be tested
- **service_type** (`str`): The type of the service
- **protocol** (`ProtocolConfig`): The protocol configuration
- **implementation_name** (`str`): The name of the implementation
- **event_manager** (`Optional[EventManager]`): Manager for handling events
- **test_case**: Reference to parent test case for execution environment access

#### Methods

##### `__init__(service_config_to_test, service_type, protocol, implementation_name, event_manager, test_case)`

Initialize the IImplementationManager with the given parameters.

**Args:**
- `service_config_to_test` (`ServiceConfig`): Service configuration to test
- `service_type` (`str`): Type of service being managed
- `protocol` (`ProtocolConfig`): Protocol configuration object
- `implementation_name` (`str`): Name identifying the implementation
- `event_manager` (`Optional[EventManager]`): Event management system
- `test_case`: Parent test case reference for environment access

**Returns:**
- `None`

**Raises:**
- `ValueError`: If required parameters are missing or invalid

##### `is_tester()`

Check if this implementation is a tester.

**Returns:**
- `bool`: Always returns `False` for IUT implementations

**Example:**
```python
manager = SomeIUTManager(config, "iut", protocol, "implementation")
assert not manager.is_tester()  # IUT implementations are not testers
```

## Service Management Mixins

### IUTServiceManagerMixin

```python
class IUTServiceManagerMixin(ServiceManagerMixin, IImplementationManager)
```

Specialized mixin for IUT service managers providing IUT-specific patterns and utilities.

#### Properties

##### `role`

```python
@property
def role(self) -> str
```

Get the service role (client/server).

**Returns:**
- `str`: Service role, defaults to "client" if not configured

##### `protocol_version`

```python
@property
def protocol_version(self) -> str
```

Get the protocol version.

**Returns:**
- `str`: Protocol version, defaults to "default" if not configured

#### Core Methods

##### `setup_iut_specific_attributes(protocol, service_config_to_test)`

Set up IUT-specific attributes from configuration.

**Args:**
- `protocol` (`Any`): Protocol configuration object
- `service_config_to_test` (`Any`): Service configuration object

**Returns:**
- `None`

**Side Effects:**
- Sets `_role` attribute from protocol or service configuration
- Sets `_protocol_version` attribute from protocol or service configuration
- Applies default values if configuration missing

##### `is_client()`

Check if this service is configured as a client.

**Returns:**
- `bool`: True if role is "client" (case-insensitive)

**Example:**
```python
manager.role = "client"
assert manager.is_client()
assert not manager.is_server()
```

##### `is_server()`

Check if this service is configured as a server.

**Returns:**
- `bool`: True if role is "server" (case-insensitive)

##### `get_target_service()`

Get the target service name for client connections.

**Returns:**
- `Optional[str]`: Target service name if configured, None otherwise

#### Template Method Pattern

##### `standard_iut_initialization(service_config_to_test, service_type, protocol, implementation_name, event_manager, plugin_dir)`

Template method implementing the standard IUT service initialization pattern.

This method encapsulates the common 6-line initialization used by all IUT services:
1. Call standardized_initialization from ServiceManagerMixin
2. Set up IUT-specific attributes
3. Initialize template renderer
4. Set up Docker attributes

**Args:**
- `service_config_to_test` (`Any`, optional): Service configuration, defaults to instance attribute
- `service_type` (`str`, optional): Service type, defaults to instance attribute
- `protocol` (`Any`, optional): Protocol config, defaults to instance attribute
- `implementation_name` (`str`, optional): Implementation name, defaults to instance attribute
- `event_manager` (`Any`, optional): Event manager, defaults to instance attribute
- `plugin_dir` (`Any`): Plugin directory path (required for template setup)

**Returns:**
- `None`

**Side Effects:**
- Calls `standardized_initialization()` from parent mixin
- Sets up IUT-specific role and version attributes
- Initializes template renderer for command generation
- Configures Docker image and file attributes

**Example:**
```python
def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)

    # Single-line initialization replacing 6+ lines of boilerplate
    self.standard_iut_initialization(plugin_dir=Path(__file__).parent)
```

#### Hook Methods (Customization Points)

##### `_get_plugin_dir()`

Hook method for customizing plugin directory detection.

**Returns:**
- `Path`: Plugin directory path

**Override Example:**
```python
def _get_plugin_dir(self):
    return Path("/custom/plugin/path")
```

##### `_get_docker_image_name(implementation_name)`

Hook method for customizing Docker image naming.

**Args:**
- `implementation_name` (`str`, optional): Implementation name

**Returns:**
- `str`: Docker image name

**Default Behavior:**
Returns `{implementation_name}:latest`

##### `_setup_template_renderer()`

Hook method for customizing template renderer setup.

**Returns:**
- `None`

**Side Effects:**
- Creates `ServiceTemplateRenderer` with plugin directory
- Sets `self.template_renderer` attribute

##### `_setup_docker_attributes()`

Hook method for customizing Docker configuration.

**Returns:**
- `None`

**Side Effects:**
- Sets `self.docker_image_name` via `_get_docker_image_name()`
- Sets `self.docker_file_path` to plugin directory + "Dockerfile"

## Event Management

### IUTManagerEventMixin

```python
class IUTManagerEventMixin
```

Provides event handling capabilities for IUT service test execution monitoring.

#### Methods

*Note: Detailed method signatures to be extracted from source code inspection*

## Configuration Schemas

### Base Configuration Patterns

IUT implementations typically use Pydantic models for configuration validation:

```python
from pydantic import BaseModel, Field
from typing import Optional

class BaseIUTConfig(BaseModel):
    """Base configuration schema for IUT implementations."""

    binary_path: str = Field(description="Path to implementation binary")
    server_port: int = Field(default=4443, description="Server listening port")
    log_level: str = Field(default="info", description="Logging verbosity")

    class Config:
        schema_extra = {
            "example": {
                "binary_path": "/usr/local/bin/implementation",
                "server_port": 4443,
                "log_level": "debug"
            }
        }
```

## Usage Patterns

### Standard Implementation Pattern

```python
from panther.plugins.services.iut.iut_service_manager_mixin import IUTServiceManagerMixin
from panther.plugins.core.plugin_decorators import register_plugin

@register_plugin(
    plugin_type=PluginType.IUT,
    name="my_implementation",
    supported_protocols=["my_protocol"],
    capabilities=["feature1", "feature2"]
)
class MyImplementationServiceManager(IUTServiceManagerMixin, BaseServiceManager):
    def __init__(self, service_config_to_test, service_type, protocol,
                 implementation_name, event_manager=None, **kwargs):
        super().__init__(
            service_config_to_test=service_config_to_test,
            service_type=service_type,
            protocol=protocol,
            implementation_name=implementation_name,
            event_manager=event_manager,
            **kwargs
        )

        # Replace 6+ lines of boilerplate with standardized initialization
        self.standard_iut_initialization(plugin_dir=Path(__file__).parent)
```

### Configuration Access Pattern

```python
# Access service configuration
role = manager.role  # "client" or "server"
version = manager.protocol_version  # Protocol version string
is_client = manager.is_client()  # Boolean check
target = manager.get_target_service()  # Target service for clients
```

### Template Rendering Pattern

```python
# Generate implementation-specific commands
client_command = manager.template_renderer.render_template(
    "client_command.jinja",
    context={
        "server_host": "127.0.0.1",
        "server_port": 4443,
        "protocol_version": manager.protocol_version
    }
)
```

## Error Handling

### Common Exceptions

- **`ValueError`**: Invalid configuration parameters
- **`FileNotFoundError`**: Missing template files or plugin directories
- **`TemplateNotFound`**: Jinja2 template rendering failures
- **`ContainerExecutionError`**: Docker container execution failures

### Error Context

Most errors include contextual information about:
- Plugin name and version
- Configuration state at time of error
- Template rendering context (if applicable)
- Container execution logs (if applicable)
