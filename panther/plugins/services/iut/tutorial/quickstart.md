# IUT Plugin Development Quickstart

This tutorial walks you through implementing a simple IUT plugin for testing a fictional "Echo" protocol implementation.

## Learning Objectives

By completing this tutorial, you will:
- Create a functional IUT plugin from scratch
- Understand the IUT plugin architecture
- Configure Docker containerization for your implementation
- Write command templates for client/server execution
- Test your plugin with PANTHER's testing framework

## Prerequisites

- PANTHER development environment set up
- Docker installed and running
- Basic Python knowledge
- Familiarity with Jinja2 templates

## Step 1: Create Plugin Structure

Create the directory structure for your Echo protocol implementation:

```bash
mkdir -p panther/plugins/services/iut/echo/simple_echo
cd panther/plugins/services/iut/echo/simple_echo
```

Create the basic file structure:

```bash
touch __init__.py
touch simple_echo.py
touch config_schema.py
touch Dockerfile
mkdir templates
mkdir version_configs
```

## Step 2: Define Configuration Schema

Edit `config_schema.py` to define configuration validation:

```python
from pydantic import BaseModel, Field
from typing import Optional, List

class SimpleEchoConfig(BaseModel):
    """Configuration schema for Simple Echo implementation."""

    binary_path: str = Field(
        default="/usr/local/bin/echo_server",
        description="Path to echo implementation binary"
    )

    server_port: int = Field(
        default=8080,
        ge=1024,
        le=65535,
        description="Server listening port"
    )

    message_size: int = Field(
        default=1024,
        ge=1,
        le=65536,
        description="Maximum message size in bytes"
    )

    log_level: str = Field(
        default="info",
        regex="^(debug|info|warn|error)$",
        description="Logging verbosity level"
    )

    timeout_seconds: int = Field(
        default=30,
        ge=1,
        description="Connection timeout in seconds"
    )

    class Config:
        schema_extra = {
            "example": {
                "binary_path": "/usr/local/bin/echo_server",
                "server_port": 8080,
                "message_size": 1024,
                "log_level": "debug",
                "timeout_seconds": 30
            }
        }
```

## Step 3: Implement Service Manager

Create `simple_echo.py` with the main service manager class:

```python
"""Simple Echo protocol implementation for IUT testing."""

from pathlib import Path
from typing import Any, Dict, Optional

from panther.config.core.models import ProtocolConfig
from panther.config.core.models.service import ServiceConfig
from panther.plugins.core.plugin_decorators import register_plugin
from panther.plugins.core.structures.plugin_type import PluginType
from panther.plugins.services.base.base_service_manager import BaseServiceManager
from panther.plugins.services.iut.iut_service_manager_mixin import IUTServiceManagerMixin
from panther.plugins.services.iut.echo.simple_echo.config_schema import SimpleEchoConfig


@register_plugin(
    plugin_type=PluginType.IUT,
    name="simple_echo",
    version="1.0.0",
    author="Tutorial Example",
    description="Simple Echo protocol implementation for testing",
    license="MIT",
    min_panther_version="1.0.0",
    supported_protocols=["echo"],
    capabilities=[
        "bidirectional_messaging",
        "configurable_timeout",
        "variable_message_size"
    ],
    tags=["echo", "simple", "tutorial", "example"],
    external_dependencies=["docker"]
)
class SimpleEchoServiceManager(IUTServiceManagerMixin, BaseServiceManager):
    """
    Simple Echo service manager for IUT testing.

    Provides echo functionality for testing basic client-server communication
    patterns with configurable message sizes and timeouts.
    """

    def __init__(
        self,
        service_config_to_test: ServiceConfig,
        service_type: str,
        protocol: ProtocolConfig,
        implementation_name: str,
        event_manager=None,
        global_config=None,
        test_case=None,
        **kwargs
    ):
        """Initialize the Simple Echo service manager."""

        # Store configuration for validation
        self._echo_config = None
        if hasattr(service_config_to_test, 'implementation_config'):
            self._echo_config = SimpleEchoConfig(**service_config_to_test.implementation_config)

        # Initialize parent classes
        super().__init__(
            service_config_to_test=service_config_to_test,
            service_type=service_type,
            protocol=protocol,
            implementation_name=implementation_name,
            event_manager=event_manager,
            global_config=global_config,
            test_case=test_case,
            **kwargs
        )

        # Use standardized IUT initialization pattern
        self.standard_iut_initialization(plugin_dir=Path(__file__).parent)

    @property
    def echo_config(self) -> SimpleEchoConfig:
        """Get validated echo configuration."""
        if self._echo_config is None:
            # Create default configuration if none provided
            self._echo_config = SimpleEchoConfig()
        return self._echo_config

    def get_server_port(self) -> int:
        """Get the server port for this echo implementation."""
        return self.echo_config.server_port

    def get_timeout_seconds(self) -> int:
        """Get the configured timeout for connections."""
        return self.echo_config.timeout_seconds

    def get_max_message_size(self) -> int:
        """Get the maximum message size for echo operations."""
        return self.echo_config.message_size
```

## Step 4: Create Command Templates

Create client command template at `templates/client_command.jinja`:

```jinja2
{% set config = context.echo_config %}
{{ config.binary_path }} \
  --mode client \
  --host {{ context.server_host | default('127.0.0.1') }} \
  --port {{ context.server_port | default(config.server_port) }} \
  --message-size {{ config.message_size }} \
  --timeout {{ config.timeout_seconds }} \
  --log-level {{ config.log_level }} \
  {% if context.test_message -%}
  --message "{{ context.test_message }}" \
  {% endif -%}
  {% if context.repeat_count -%}
  --repeat {{ context.repeat_count }} \
  {% endif -%}
  {% if context.output_file -%}
  --output {{ context.output_file }} \
  {% endif %}
```

Create server command template at `templates/server_command.jinja`:

```jinja2
{% set config = context.echo_config %}
{{ config.binary_path }} \
  --mode server \
  --bind {{ context.bind_address | default('0.0.0.0') }} \
  --port {{ context.server_port | default(config.server_port) }} \
  --message-size {{ config.message_size }} \
  --timeout {{ config.timeout_seconds }} \
  --log-level {{ config.log_level }} \
  {% if context.max_connections -%}
  --max-connections {{ context.max_connections }} \
  {% endif -%}
  {% if context.daemon_mode -%}
  --daemon \
  {% endif %}
```

## Step 5: Create Version Configuration

Create `version_configs/v1.0.yaml`:

```yaml
# Simple Echo Protocol v1.0 Configuration
version: "1.0"
protocol_name: "echo"
description: "Basic echo protocol for testing client-server communication"

# Protocol-specific parameters
parameters:
  default_port: 8080
  max_message_size: 65536
  min_message_size: 1
  supported_modes: ["client", "server"]
  default_timeout: 30

# Implementation-specific settings
implementation:
  binary_name: "echo_server"
  config_file_format: "yaml"
  supports_tls: false
  supports_compression: false

# Test scenarios this version supports
test_scenarios:
  - "basic_echo"
  - "large_message_echo"
  - "timeout_testing"
  - "concurrent_connections"

# Version compatibility
compatibility:
  backward_compatible: []
  forward_compatible: []
```

## Step 6: Create Dockerfile

Create the `Dockerfile` for containerizing your implementation:

```dockerfile
# Multi-stage build for Simple Echo implementation
FROM ubuntu:20.04 AS builder

# Install build dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    make \
    git \
    && rm -rf /var/lib/apt/lists/*

# Create and switch to build directory
WORKDIR /build

# Copy source code (in real implementation, this would be from a repository)
COPY src/ ./

# Build the echo implementation
RUN make clean && make all

# Production stage
FROM ubuntu:20.04

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Create application user
RUN useradd -r -u 1000 echo_user

# Copy binary from builder stage
COPY --from=builder /build/echo_server /usr/local/bin/
RUN chmod +x /usr/local/bin/echo_server

# Set up working directory
WORKDIR /app
RUN chown echo_user:echo_user /app

# Switch to non-root user
USER echo_user

# Expose default port
EXPOSE 8080

# Default command (will be overridden by PANTHER)
CMD ["/usr/local/bin/echo_server", "--help"]
```

## Step 7: Initialize Plugin Module

Edit `__init__.py` to make the plugin discoverable:

```python
"""Simple Echo IUT Plugin for PANTHER."""

from .simple_echo import SimpleEchoServiceManager
from .config_schema import SimpleEchoConfig

__all__ = ["SimpleEchoServiceManager", "SimpleEchoConfig"]

# Plugin metadata
__version__ = "1.0.0"
__author__ = "Tutorial Example"
__description__ = "Simple Echo protocol implementation for IUT testing"
```

## Step 8: Test Your Plugin

Create a test configuration file `test_config.yaml`:

```yaml
test_name: "simple_echo_basic_test"
description: "Basic echo functionality test"

protocol:
  name: "echo"
  version: "v1.0"

services:
  - name: "echo_server"
    type: "iut"
    implementation: "echo/simple_echo"
    role: "server"
    config:
      server_port: 8080
      message_size: 1024
      log_level: "debug"

  - name: "echo_client"
    type: "iut"
    implementation: "echo/simple_echo"
    role: "client"
    config:
      server_port: 8080
      message_size: 1024
      log_level: "debug"

test_cases:
  - name: "basic_echo_test"
    description: "Send message and verify echo response"
    steps:
      - start_service: "echo_server"
      - wait: 2
      - start_service: "echo_client"
      - wait: 5
      - stop_service: "echo_client"
      - stop_service: "echo_server"
```

Test plugin discovery:

```bash
# Verify plugin is discoverable
python -c "from panther.plugins.plugin_manager import PluginManager; \
           pm = PluginManager(); \
           print([p for p in pm.get_available_plugins() if 'simple_echo' in p.name])"

# Test configuration validation
python -c "from panther.plugins.services.iut.echo.simple_echo.config_schema import SimpleEchoConfig; \
           config = SimpleEchoConfig(); \
           print(f'Default config: {config.dict()}')"
```

## Step 9: Run Integration Test

Build and test the Docker container:

```bash
# Build container
cd panther/plugins/services/iut/echo/simple_echo
docker build -t simple_echo:latest .

# Test container runs
docker run --rm simple_echo:latest /usr/local/bin/echo_server --version

# Run PANTHER test
panther test --config test_config.yaml --verbose
```

## Step 10: Verify Command Generation

Test template rendering:

```bash
# Generate client command
python -c "
from panther.core.template.template_renderer import ServiceTemplateRenderer
from pathlib import Path

renderer = ServiceTemplateRenderer(Path('panther/plugins/services/iut/echo/simple_echo'))
cmd = renderer.render_template('client_command.jinja', {
    'echo_config': {'binary_path': '/usr/local/bin/echo_server', 'server_port': 8080, 'message_size': 1024, 'timeout_seconds': 30, 'log_level': 'debug'},
    'server_host': '127.0.0.1',
    'test_message': 'Hello, Echo!'
})
print('Generated command:', cmd)
"
```

## Next Steps

Now that you have a working IUT plugin:

1. **Add more sophisticated features**: Error handling, performance metrics, TLS support
2. **Create additional test scenarios**: Stress testing, failure injection, edge cases
3. **Optimize the container**: Multi-stage builds, smaller base images, security hardening
4. **Add monitoring**: Health checks, metric collection, structured logging
5. **Write comprehensive tests**: Unit tests, integration tests, performance benchmarks

## Common Issues and Solutions

**Plugin not discovered**: Check `__init__.py` imports and `@register_plugin` decorator
**Template rendering fails**: Verify Jinja2 syntax and context variable availability
**Container build errors**: Check Dockerfile syntax and dependency availability
**Command execution fails**: Verify binary paths and argument formatting in templates

This tutorial provides a foundation for implementing more complex IUT plugins following PANTHER's patterns and conventions.
