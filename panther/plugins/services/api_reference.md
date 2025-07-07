# Service Plugins API Reference

## Core Interfaces

### IServiceManager

```python
class IServiceManager(IPlugin, CommandEventMixin)
```

Abstract base class for all service managers in the PANTHER framework.

**Inherits from:**
- `IPlugin`: Core plugin interface
- `CommandEventMixin`: Event handling for command lifecycle

#### Constructor

```python
def __init__(
    self,
    service_config_to_test: Any,
    service_type: str,
    protocol: ProtocolConfig,
    implementation_name: str,
    event_manager: Optional[EventManager] = None,
    test_case: Optional[Any] = None
)
```

Initialize service manager with configuration and context.

**Parameters:**
- `service_config_to_test`: Service configuration object
- `service_type`: Service type ("TESTERS" or "IUT")
- `protocol`: Protocol configuration (QUIC, HTTP, etc.)
- `implementation_name`: Name of the specific implementation
- `event_manager`: Optional event manager for notifications
- `test_case`: Reference to parent test case

**Raises:**
- `AssertionError`: If service_type is not valid

#### Properties

```python
@property
def role(self) -> str
```
Get the service role (client/server).

```python
@role.setter
def role(self, value) -> None
```
Set the service role.

```python
@property
def protocol_version(self) -> str
```
Get the protocol version.

#### Core Methods

##### Command Generation

```python
def render_commands(
    self,
    params: dict,
    template_name: str,
    command_args: Optional[List[str]] = None,
    env_vars: Optional[Dict[str, str]] = None,
    extra_fields: Optional[str] = None
) -> str
```

Render command using Jinja2 template with proper shell/YAML quoting.

**Parameters:**
- `params`: Template parameters dictionary
- `template_name`: Name of Jinja2 template file
- `command_args`: Structured command arguments
- `env_vars`: Environment variables dictionary
- `extra_fields`: Additional YAML fragments

**Returns:**
- Rendered command string with proper escaping

**Example:**
```python
command = service.render_commands(
    params={"service_name": "test_service"},
    template_name="docker-compose.yml.j2",
    command_args=["--verbose", "--port", "4433"],
    env_vars={"DEBUG": "1"}
)
```

##### Command Lifecycle

```python
def generate_pre_compile_commands(self) -> List[Union[str, ShellCommand]]
```
Generate commands to execute before compilation.

```python
def generate_compile_commands(self) -> List[Union[str, ShellCommand]]
```
Generate compilation commands.

```python
def generate_post_compile_commands(self) -> List[Union[str, ShellCommand]]
```
Generate commands to execute after compilation.

```python
def generate_pre_run_commands(self) -> List[Union[str, ShellCommand]]
```
Generate commands to execute before running.

```python
def generate_run_command(self) -> Dict[str, Any]
```
Generate the main execution command.

**Returns:**
Dictionary with structure:
```python
{
    "working_dir": str,      # Execution directory
    "command_binary": str,   # Executable name/path
    "command_args": Union[str, List[str]], # Arguments
    "timeout": Union[int, float],          # Timeout seconds
    "environment": Dict[str, str]          # Environment variables
}
```

```python
def generate_post_run_commands(self) -> List[Union[str, ShellCommand]]
```
Generate commands to execute after running.

##### Abstract Methods

```python
@abstractmethod
def generate_deployment_commands(self) -> str
```
Generate deployment configuration (Docker Compose, etc.).

**Must be implemented by subclasses.**

##### Output Management

```python
def get_output_patterns(self) -> List[Tuple[str, str]]
```
Get output patterns for this service.

**Returns:**
List of (output_type, filename_pattern) tuples:
- `output_type`: Category like 'stdout', 'qlog', 'pcap'
- `filename_pattern`: File pattern with optional {service_name} placeholder

```python
def add_output_pattern(self, output_type: str, filename_pattern: str) -> None
```
Add custom output pattern.

```python
def get_output_file_paths(self, log_base_path: str = "/app/logs") -> Dict[str, str]
```
Get concrete output file paths for entrypoint scripts.

```python
def get_standard_redirections(self) -> Dict[str, str]
```
Get standard I/O redirections (stdout/stderr paths).

##### Service Management

```python
def set_test_context(self, test_name: str) -> None
```
Set test context for this service.

```python
def get_test_context(self) -> Optional[str]
```
Get current test context.

```python
def stop(self) -> Any
```
Stop the service with proper event notifications.

```python
def _do_stop(self) -> Any
```
Perform actual service stop work (override in subclasses).

##### Utility Methods

```python
def get_service_name(self) -> str
```
Get the service name.

```python
def get_implementation_name(self) -> str
```
Get the implementation name.

```python
def is_tester(self) -> bool
```
Check if this is a tester service.

```python
def is_client(self) -> bool
```
Check if service role is client.

```python
def is_server(self) -> bool
```
Check if service role is server.

## Base Service Classes

### BaseQUICServiceManager

```python
class BaseQUICServiceManager(IServiceManager)
```

Base class for QUIC protocol implementations with common QUIC patterns.

#### Additional Methods

```python
def get_port(self) -> int
```
Get the QUIC port number.

```python
def get_server_host(self) -> str
```
Get the server hostname for client connections.

```python
def get_alpn_protocols(self) -> List[str]
```
Get Application Layer Protocol Negotiation protocols.

```python
def get_certificate_paths(self) -> Dict[str, str]
```
Get SSL certificate file paths.

#### QUIC-Specific Output Patterns

Default output patterns include:
- `("qlog", "*.qlog")` - QUIC event logs
- `("sslkeylog", "sslkeylogfile.txt")` - SSL key log for Wireshark
- `("keys", "*keys.log")` - Key material logs
- `("pcap", "{service_name}.pcap")` - Packet captures

### BaseHTTPServiceManager

```python
class BaseHTTPServiceManager(IServiceManager)
```

Base class for HTTP protocol implementations.

#### HTTP-Specific Output Patterns

Default output patterns include:
- `("access_log", "access.log")` - HTTP access logs
- `("error_log", "error.log")` - HTTP error logs
- `("har", "*.har")` - HTTP Archive files

### BaseMinipServiceManager

```python
class BaseMinipServiceManager(IServiceManager)
```

Base class for MinIP (minimal protocol) implementations.

## Mixins and Utilities

### ServiceManagerMixin

```python
class ServiceManagerMixin(LoggerMixin)
```

Provides common patterns and integrates with PANTHER architecture.

#### Constructor

```python
def __init__(self, *args, global_config=None, **kwargs)
```

#### Command Validation

```python
@validate_cmd
def generate_validated_command(self) -> Dict[str, Any]
```

Decorator that validates command structure against `RUN_CMD_SCHEMA`.

#### Schema Definition

```python
RUN_CMD_SCHEMA = {
    "pre_compile_cmds": list,
    "compile_cmds": list,
    "post_compile_cmds": list,
    "pre_run_cmds": list,
    "run_cmd": {
        "working_dir": str,
        "command_binary": str,
        "command_args": (list, str),
        "timeout": (int, float),
        "environment": dict,
    },
    "post_run_cmds": list,
}
```

### ServiceManagerUtilities

```python
class ServiceManagerUtilities
```

Collection of utility functions for service management.

#### Methods

```python
@staticmethod
def validate_service_config(config: dict) -> Tuple[bool, List[str]]
```
Validate service configuration against schema.

```python
@staticmethod
def merge_environment_variables(*env_dicts: Dict[str, str]) -> Dict[str, str]
```
Merge multiple environment variable dictionaries.

```python
@staticmethod
def resolve_template_path(service_type: str, protocol: str,
                         implementation: str, template_name: str) -> str
```
Resolve full path to template file.

## Event System

### ServiceEventEmitter

```python
class ServiceEventEmitter
```

Handles service-specific events within the PANTHER event system.

#### Events

**Service Lifecycle Events:**
- `service_preparation_started`
- `service_started`
- `service_stopped`
- `service_error`

**Command Generation Events:**
- `command_generation_started`
- `command_generated`

#### Usage

```python
# Emit service started event
self.notify_service_started(details={
    "service_name": self.service_name,
    "implementation": self.implementation_name,
    "protocol": self.service_protocol.name
})

# Emit command generation event
self.emit_command_generation_started("compile")
self.emit_command_generated("compile", "Generated 3 compile commands")

# Emit error event
self.notify_service_error(
    error_type="configuration_error",
    error_message="Invalid port configuration",
    details={"service_name": self.service_name}
)
```

## Configuration Schemas

### Service Configuration

```python
SERVICE_CONFIG_SCHEMA = {
    "name": str,                    # Service instance name
    "timeout": int,                 # Execution timeout seconds
    "protocol": {
        "role": str,                # "client" or "server"
        "version": str,             # Protocol version
        "port": int,                # Port number
        "target": Optional[str]     # Target for clients
    },
    "implementation": {
        "name": str,                # Implementation name
        "version": str,             # Implementation version
        "version_config": dict,     # Version-specific config
        "use_system_models": bool   # Use system or protocol models
    }
}
```

### Template Variables

Available in all Jinja2 templates:

**Service Context:**
- `service_name`: Service instance name
- `implementation_name`: Implementation name
- `service_type`: "IUT" or "TESTERS"
- `role`: "client" or "server"
- `protocol_name`: Protocol name
- `protocol_version`: Protocol version

**Environment:**
- `environments`: Environment variables dict
- `volumes`: Volume mount specifications
- `working_dir`: Service working directory

**Network:**
- `port`: Service port number
- `server_host`: Server hostname (for clients)
- `bind_address`: Address to bind to

**Paths:**
- `log_base_path`: Base path for log files
- `cert_path`: SSL certificate path
- `key_path`: SSL private key path

### Template Filters

**Shell Quoting:**
```jinja2
{{ user_input | quote_shell }}
```
Safely quote strings for shell commands.

**YAML Quoting:**
```jinja2
{{ config_value | quote_yaml }}
```
Safely quote strings for YAML files.

**Path Resolution:**
```jinja2
{{ relative_path | realpath }}
```
Convert relative paths to absolute paths.

**Type Checking:**
```jinja2
{% if config_value | is_dict %}
```
Check if value is a dictionary.

## Error Handling

### Exception Hierarchy

```python
class ServiceError(Exception):
    """Base exception for service-related errors."""

class ConfigurationError(ServiceError):
    """Configuration validation or loading error."""

class TemplateError(ServiceError):
    """Template rendering error."""

class CommandGenerationError(ServiceError):
    """Error generating service commands."""

class DeploymentError(ServiceError):
    """Error during service deployment."""
```

### Error Context

All service errors include context:

```python
try:
    command = self.generate_run_command()
except Exception as e:
    raise CommandGenerationError(
        f"Failed to generate run command for {self.service_name}: {e}"
    ) from e
```

## Best Practices

### 1. Command Generation

```python
# Prefer structured arguments over string concatenation
def generate_run_command(self) -> Dict[str, Any]:
    args = ["--server", "--port", str(self.get_port())]
    if self.role == "client":
        args.extend(["--host", self.get_server_host()])

    return {
        "command_binary": "my_app",
        "command_args": args,  # List, not string
        "environment": self.environments
    }
```

### 2. Template Usage

```python
# Use structured parameters for proper quoting
deployment = self.render_commands(
    params={"service_name": self.service_name},
    template_name="docker-compose.yml.j2",
    command_args=["--verbose", "--config", "/app/config.yaml"],
    env_vars={"LOG_LEVEL": "DEBUG"}
)
```

### 3. Output Patterns

```python
def get_output_patterns(self) -> List[Tuple[str, str]]:
    """Define comprehensive output patterns."""
    patterns = super().get_output_patterns()  # Get base patterns

    # Add implementation-specific patterns
    patterns.extend([
        ("app_log", "{service_name}_app.log"),
        ("metrics", "metrics_{service_name}.json"),
        ("debug", "debug_*.log")  # Glob pattern for discovery
    ])

    return patterns
```

### 4. Event Notifications

```python
def _do_prepare(self, plugin_manager=None):
    """Preparation with proper event notifications."""
    try:
        self.notify_service_event("preparation_started",
                                  service_id=self.implementation_name)

        # Perform preparation work
        result = self._perform_preparation(plugin_manager)

        self.notify_service_started(details={
            "implementation": self.implementation_name
        })

        return result

    except Exception as e:
        self.notify_service_error(
            error_type="preparation_failed",
            error_message=str(e),
            details={"service_name": self.service_name}
        )
        raise
```

---

*This API reference provides comprehensive documentation for all public interfaces, methods, and patterns in the PANTHER service plugin system.*
