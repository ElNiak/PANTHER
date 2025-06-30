# Implementation Under Test (IUT) Development Guide

**Creating protocol implementations for the PANTHER testing framework**

This guide covers developing Implementation Under Test (IUT) plugins for any protocol using PANTHER's inheritance-based architecture.

## IUT Architecture Overview

IUT plugins represent protocol implementations being tested within PANTHER. The architecture provides:

1. **Inheritance-Based Development**: Use base classes for common functionality across protocols
2. **Template Method Pattern**: Implement only what's unique to your implementation
3. **Event-Driven Integration**: Automatic event emission and monitoring
4. **Command Processor Integration**: Structured command generation and validation
5. **Protocol Agnostic**: Support for any network protocol

### Base Class Hierarchy

```text
BaseServiceManager                  # Core service management functionality
├── BaseQUICServiceManager         # QUIC protocol specifics
│   ├── PythonQUICServiceManager   # Python QUIC implementations
│   └── RustQUICServiceManager     # Rust QUIC implementations
├── BaseHTTPServiceManager         # HTTP protocol specifics
├── BaseMinipServiceManager        # MINIP protocol specifics
└── BaseTCPServiceManager          # Generic TCP implementations
```

## IUT Development Steps

### 1. Choose Your Base Class

Select the appropriate base class based on your protocol and implementation language:

#### Protocol-Specific Base Classes

```python
# For QUIC implementations
from panther.plugins.services.base.quic_service_base import BaseQUICServiceManager

# For HTTP implementations  
from panther.plugins.services.base.http_service_base import BaseHTTPServiceManager

# For MINIP implementations
from panther.plugins.services.base.minip_service_base import BaseMinipServiceManager

# For custom protocols
from panther.plugins.services.base.service_manager_base import BaseServiceManager
```

#### Language-Specific Extensions

Some protocols have language-specific extensions:

```python
# For Python QUIC implementations
from panther.plugins.services.base.python_quic_base import PythonQUICServiceManager

# For Rust QUIC implementations
from panther.plugins.services.base.rust_quic_base import RustQUICServiceManager

# For Python HTTP implementations (when available)
from panther.plugins.services.base.python_http_base import PythonHTTPServiceManager
```

### 2. Create the Plugin Directory Structure

Create the following directory structure for your IUT:

```text
panther/plugins/services/iut/protocol_name/your_implementation/
├── __init__.py                    # Plugin registration
├── your_implementation.py         # Main service manager (inherits from base class)
├── config_schema.py              # Configuration schema
├── Dockerfile                    # Container build definition (optional)
├── templates/                    # Jinja2 command templates (optional)
│   ├── client_command.jinja
│   └── server_command.jinja
├── tests/                        # Implementation-specific tests
│   └── test_your_implementation.py
└── README.md                     # Documentation
```

**Directory Components:**
- **Small implementation files**: Base classes handle common protocol functionality
- **Template-based commands**: Optional Jinja2 templates for complex command generation
- **Docker integration**: Use DockerBuilderFactory or custom Dockerfiles
- **Event integration**: Automatic event emission through base classes

### 3. Define the Configuration Schema

Create a configuration schema for your implementation:

```python
# config_schema.py
from dataclasses import dataclass, field
from typing import Dict, List, Optional
from panther.config.core.models import ImplementationConfig

@dataclass
class YourImplementationConfig(ImplementationConfig):
    """Configuration schema for your protocol implementation."""
    
    # Implementation identification (required by base class)
    implementation_name: str = "your_implementation"
    binary_name: str = "your_binary"
    
    # Protocol-specific configuration
    protocol_version: str = "1.0"
    supported_features: List[str] = field(default_factory=list)
    
    # Network configuration (handled by base class)
    default_port: int = 8080  # Protocol default port
    bind_address: str = "0.0.0.0"
    
    # Implementation-specific parameters
    performance_mode: str = "balanced"  # balanced, throughput, latency
    debug_level: int = 0
    custom_options: Dict[str, str] = field(default_factory=dict)
    
    # Advanced configuration
    certificate_config: Dict[str, str] = field(default_factory=dict)
    runtime_parameters: Dict[str, str] = field(default_factory=dict)
    
    # Docker integration (optional)
    dockerfile_template: Optional[str] = None
    base_image_override: Optional[str] = None
```

#### Protocol-Specific Examples

```python
# For QUIC implementations
@dataclass
class QuicImplementationConfig(IUTConfig):
    implementation_name: str = "your_quic"
    binary_name: str = "your_quic_binary"
    protocol_version: str = "rfc9000"
    default_port: int = 4443
    quic_extensions: List[str] = field(default_factory=list)

# For HTTP implementations  
@dataclass
class HttpImplementationConfig(IUTConfig):
    implementation_name: str = "your_http"
    binary_name: str = "your_http_server"
    protocol_version: str = "2.0"
    default_port: int = 80
    http_features: List[str] = field(default_factory=lambda: ["h2", "h3"])

# For custom protocols
@dataclass
class CustomProtocolConfig(IUTConfig):
    implementation_name: str = "your_protocol"
    binary_name: str = "your_protocol_impl"
    protocol_version: str = "1.0"
    default_port: int = 9999
    custom_settings: Dict[str, str] = field(default_factory=dict)
```

### 4. Implement the IUT Service Manager

Create your main service manager by inheriting from the appropriate base class:

#### Example 1: Generic Protocol Implementation

```python
# your_implementation.py
from typing import List, Dict
from panther.plugins.services.base.service_manager_base import BaseServiceManager
from panther.plugins.plugin_decorators import register_plugin

@register_plugin(
    plugin_type="iut",
    name="your_implementation",
    version="1.0.0",
    description="Your protocol implementation",
    supported_protocols=["your_protocol"],
    capabilities=["basic_features"]
)
class YourServiceManager(BaseServiceManager):
    """Service manager for your protocol implementation."""
    
    def _get_implementation_name(self) -> str:
        return "your_implementation"
    
    def _get_binary_name(self) -> str:
        return "your_binary"
    
    def _get_server_specific_args(self, **kwargs) -> List[str]:
        """Implementation-specific server arguments."""
        port = kwargs.get("port", 8080)
        config_file = kwargs.get("config_file", "")
        
        args = ["--listen", f"0.0.0.0:{port}"]
        if config_file:
            args.extend(["--config", config_file])
        
        # Add implementation-specific options
        if kwargs.get("performance_mode") == "high":
            args.append("--high-performance")
            
        return args
    
    def _get_client_specific_args(self, **kwargs) -> List[str]:
        """Implementation-specific client arguments."""
        host = kwargs.get("host", "localhost")
        port = kwargs.get("port", 8080)
        
        args = ["--connect", f"{host}:{port}"]
        
        # Add client-specific options
        if kwargs.get("persistent", False):
            args.append("--keep-alive")
            
        return args
    
    def generate_deployment_commands(self) -> str:
        """Generate deployment commands for this implementation."""
        return f"{self._get_binary_name()} --listen 0.0.0.0:8080"
    
    def _do_prepare(self, plugin_manager=None):
        """Implementation-specific preparation."""
        # Custom initialization logic
        self._setup_implementation()
        self._validate_requirements()
    
    def _setup_implementation(self):
        """Setup implementation-specific configuration."""
        # Implementation setup logic
        pass
    
    def _validate_requirements(self):
        """Validate that implementation requirements are met."""
        # Check dependencies, binary availability, etc.
        pass
    
    def get_supported_features(self) -> Dict[str, bool]:
        """Return implementation-specific feature support."""
        return {
            "basic_protocol": True,
            "advanced_features": False
        }
```

#### Example 2: QUIC Protocol Implementation

```python
# quic_implementation.py
from typing import List, Dict
from panther.plugins.services.base.quic_service_base import BaseQUICServiceManager
from panther.plugins.plugin_decorators import register_plugin

@register_plugin(
    plugin_type="iut",
    name="your_quic",
    version="1.0.0",
    description="QUIC protocol implementation",
    supported_protocols=["quic"],
    capabilities=["rfc9000"]
)
class YourQuicServiceManager(BaseQUICServiceManager):
    """QUIC-specific service manager."""
    
    def _get_implementation_name(self) -> str:
        return "your_quic"
    
    def _get_binary_name(self) -> str:
        return "your_quic_binary"
    
    def _get_server_specific_args(self, **kwargs) -> List[str]:
        """QUIC server arguments."""
        port = kwargs.get("port", 4443)
        cert_file = kwargs.get("cert_file", "")
        
        args = ["-p", str(port)]
        if cert_file:
            args.extend(["-c", cert_file])
            
        return args
    
    def _get_client_specific_args(self, **kwargs) -> List[str]:
        """QUIC client arguments."""
        host = kwargs.get("host", "localhost")
        port = kwargs.get("port", 4443)
        return [host, str(port)]
```

#### Example 3: HTTP Protocol Implementation

```python
# http_implementation.py  
from typing import List, Dict
from panther.plugins.services.base.http_service_base import BaseHTTPServiceManager
from panther.plugins.plugin_decorators import register_plugin

@register_plugin(
    plugin_type="iut", 
    name="your_http",
    version="1.0.0",
    description="HTTP protocol implementation",
    supported_protocols=["http"],
    capabilities=["http/1.1", "http/2"]
)
class YourHttpServiceManager(BaseHTTPServiceManager):
    """HTTP-specific service manager."""
    
    def _get_implementation_name(self) -> str:
        return "your_http"
    
    def _get_binary_name(self) -> str:
        return "your_http_server"
    
    def _get_server_specific_args(self, **kwargs) -> List[str]:
        """HTTP server arguments."""
        port = kwargs.get("port", 80)
        document_root = kwargs.get("document_root", "/var/www")
        
        args = ["--port", str(port), "--root", document_root]
        
        if kwargs.get("enable_h2", False):
            args.append("--enable-http2")
            
        return args
    
    def _get_client_specific_args(self, **kwargs) -> List[str]:
        """HTTP client arguments."""
        url = kwargs.get("url", f"http://localhost:{kwargs.get('port', 80)}/")
        return ["--url", url]
```

#### Language-Specific Extensions

When using language-specific base classes, implement additional methods:

```python
# Python implementation with async support
from panther.plugins.services.base.python_quic_base import PythonQUICServiceManager

class PythonQuicServiceManager(PythonQUICServiceManager):
    def _get_python_module(self) -> str:
        return "your_package.server"
    
    def _get_async_patterns(self) -> Dict[str, str]:
        return {
            "event_loop": "asyncio",
            "concurrency_model": "async/await"
        }

# Rust implementation with Cargo support
from panther.plugins.services.base.rust_quic_base import RustQUICServiceManager

class RustQuicServiceManager(RustQUICServiceManager):
    def _get_cargo_features(self) -> List[str]:
        return ["tokio-runtime", "ring-crypto"]
    
    def _get_rust_runtime_config(self) -> Dict[str, str]:
        return {
            "RUST_LOG": "debug",
            "TOKIO_WORKER_THREADS": "4"
        }
```

### 5. Create Docker Integration (Optional)

PANTHER provides Docker build patterns through `DockerBuilderFactory`. You can either use predefined builders or create custom Dockerfiles:

#### Option A: Use Predefined Docker Builders

```python
# Using predefined Docker builders (recommended)
from panther.plugins.services.base.docker_build_base import DockerBuilderFactory

class YourServiceManager(BaseServiceManager):
    def generate_dockerfile_content(self) -> str:
        """Use predefined Docker builder."""
        builder = DockerBuilderFactory.create_builder(
            implementation_name=self._get_implementation_name(),
            language="rust",  # or "python", "c", "go"
            repo_url="https://github.com/yourorg/your-impl.git",
            build_features=["feature1", "feature2"]  # Implementation-specific
        )
        return builder.generate_complete_dockerfile()
```

#### Option B: Custom Dockerfile

```dockerfile
# Multi-stage build for efficient containers
FROM rust:1.75 as builder

# Install build dependencies
RUN apt-get update && apt-get install -y \
    cmake \
    pkg-config \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

# Set working directory for build
WORKDIR /build

# Copy source code
COPY . .

# Build with specific features
RUN cargo build --release --features=your-features

# Runtime stage
FROM debian:bookworm-slim as runtime

# Install runtime dependencies only
RUN apt-get update && apt-get install -y \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy binary from builder stage
COPY --from=builder /build/target/release/your_binary /usr/local/bin/

# Create app user
RUN useradd -r -s /bin/false panther

# Set working directory
WORKDIR /app

# Switch to app user  
USER panther

# Set entrypoint
ENTRYPOINT ["/usr/local/bin/your_binary"]
```

#### Command Template Integration

Create Jinja2 templates for command generation:

```bash
# templates/server_command.jinja
{{ binary_name }} \
    --server \
    --listen {{ bind_address }}:{{ port }} \
    --cert {{ cert_file }} \
    --key {{ key_file }} \
    {% if debug_level > 0 %}--debug={{ debug_level }}{% endif %} \
    {% for arg in extra_args %}{{ arg }} {% endfor %}

# templates/client_command.jinja  
{{ binary_name }} \
    --client \
    --connect {{ host }}:{{ port }} \
    {% if zero_rtt %}--enable-0rtt{% endif %} \
    {% if custom_crypto %}--crypto-provider=custom{% endif %} \
    {% for arg in extra_args %}{{ arg }} {% endfor %}
```

### 6. Create Modern Plugin Documentation

Create a comprehensive README.md that highlights the inheritance architecture:

```markdown
# Your QUIC Implementation

> **Plugin Type**: Service (IUT)  
> **Base Class**: BaseQUICServiceManager
> **Verified Source Location**: `plugins/services/iut/quic/your_implementation/`

## Modern Architecture Overview (2024)

This implementation leverages PANTHER's inheritance-based architecture, providing **X% code reduction** compared to legacy implementations through specialized base classes.

### Inheritance Pattern

```text
BaseQUICServiceManager                    # Core QUIC functionality
└── YourQuicServiceManager               # Implementation-specific logic only
    ├── _get_server_specific_args()      # Custom server arguments
    ├── _get_client_specific_args()      # Custom client arguments  
    └── _do_prepare()                    # Implementation preparation
```

### Key Benefits

- **Reduced Code Duplication**: Common QUIC logic handled by base class
- **Automatic Event Integration**: Real-time monitoring through inherited events
- **Consistent Command Generation**: Template method pattern ensures reliability
- **Docker Integration**: Standardized container builds through base classes

## Purpose and Capabilities

[Describe your implementation's specific purpose and unique features]

### Supported Features

```python
{
    "rfc9000": True,
    "key_updates": True,
    "0rtt": [True/False],
    "connection_migration": [True/False],
    "multipath": [True/False]
}
```

## Configuration Schema

### Implementation-Specific Parameters

```yaml
services:
  server:
    implementation:
      name: "your_implementation"
      type: "iut"
      # Implementation-specific configuration
      performance_mode: "balanced"  # balanced, throughput, latency
      custom_crypto: false
      debug_level: 0
      runtime_parameters:
        optimization_level: "high"
        buffer_size: "64KB"
```

### Inherited Configuration

Common QUIC parameters are handled automatically by the base class:
- `port`, `host`, `cert_file`, `key_file`
- Network timeouts and retry logic
- Certificate generation and management
- Event emission and monitoring

## Usage Examples

### Basic Server/Client Test

```yaml
tests:
  - name: "Your Implementation Test"
    network_environment:
      type: "docker_compose"
    services:
      server:
        implementation:
          name: "your_implementation"
          type: "iut"
        protocol:
          name: "quic"
          version: "rfc9000"
          role: "server"
        ports: ["4443:4443"]
      client:
        implementation:
          name: "your_implementation"
          type: "iut"
        protocol:
          name: "quic"
          version: "rfc9000"
          role: "client"
          target: "server"
```

### Performance Testing

```yaml
execution_environment:
  - type: "gperf_cpu"
    config:
      duration: 60
services:
  server:
    implementation:
      name: "your_implementation"
      performance_mode: "throughput"
      runtime_parameters:
        optimization_level: "high"
```

## Development and Extension

### Extending the Implementation

To add new features to your implementation:

```python
class YourQuicServiceManager(BaseQUICServiceManager):
    def _get_server_specific_args(self, **kwargs) -> List[str]:
        args = super()._get_server_specific_args(**kwargs)
        
        # Add your custom arguments
        if kwargs.get("enable_custom_feature"):
            args.append("--custom-feature")
            
        return args
    
    def get_supported_features(self) -> Dict[str, bool]:
        features = super().get_supported_features()
        features["custom_feature"] = True
        return features
```

### Integration with Testers

Your implementation automatically integrates with formal testers:

```yaml
services:
  ivy_tester:
    implementation:
      name: "panther_ivy"
      type: "testers"
      test: "quic_client_test_max"
    protocol:
      name: "quic"
      role: "server"
  your_client:
    implementation:
      name: "your_implementation"
      type: "iut"
    protocol:
      name: "quic"
      role: "client"
      target: "ivy_tester"
```

## Testing and Verification

### Unit Testing

Test your implementation-specific logic:

```python
def test_implementation_specific_args():
    manager = YourQuicServiceManager()
    args = manager._get_server_specific_args(
        port=8443, 
        performance_mode="throughput"
    )
    assert "--optimize-throughput" in args
```

### Integration Testing

Base class functionality is automatically tested through inheritance.

## Event Integration

Your implementation automatically emits events through the base class:

- `ServiceInitializationEvent`: When implementation starts
- `CommandGenerationEvent`: When commands are created
- `ServiceReadyEvent`: When implementation is ready
- `ServiceErrorEvent`: When errors occur

## Troubleshooting

### Common Issues

**Build Failures**: Check that base class dependencies are met
**Command Generation Issues**: Verify template method implementations
**Event System Problems**: Ensure base class event integration

### Debug Mode

Enable detailed logging:

```yaml
implementation:
  name: "your_implementation"
  debug_level: 2
  runtime_parameters:
    verbose_logging: true
```

<!-- src: /panther/plugins/services/iut/quic/your_implementation/ -->
```

### 7. Register the Modern Plugin

Register your plugin using the modern plugin system:

```python
# __init__.py
from .your_implementation import YourQuicServiceManager

__all__ = ["YourQuicServiceManager"]
```

The `@register_plugin` decorator in your service manager automatically handles discovery:

```python
@register_plugin(
    plugin_type="iut",
    name="your_implementation",
    version="1.0.0",
    description="Your implementation description",
    supported_protocols=["quic"],
    capabilities=["rfc9000", "key_updates"]
)
class YourQuicServiceManager(BaseQUICServiceManager):
    # Implementation details
```

## Testing Patterns

### 1. Unit Testing

Test implementation-specific functionality:

```python
# tests/test_your_implementation.py
import pytest
from unittest.mock import MagicMock, patch
from your_implementation import YourServiceManager

class TestYourServiceManager:
    
    def test_inheritance_functionality(self):
        """Test that base class methods are inherited."""
        manager = YourServiceManager()
        
        # Test inherited command generation
        command = manager.generate_run_command(role="server", port=8080)
        assert manager._get_binary_name() in command
        assert "8080" in command
    
    def test_implementation_specific_args(self):
        """Test implementation-specific argument generation."""
        manager = YourServiceManager()
        
        server_args = manager._get_server_specific_args(
            port=9090,
            performance_mode="high"
        )
        
        assert "--listen" in server_args
        assert "9090" in str(server_args)
        assert "--high-performance" in server_args
    
    def test_event_emission(self):
        """Test that events are emitted correctly."""
        manager = YourServiceManager()
        
        with patch.object(manager, 'emit_event') as mock_emit:
            manager._do_prepare()
            # Verify preparation events were emitted
            mock_emit.assert_called()
```

### 2. Integration Testing

Test full functionality with base class integration:

```python
# tests/test_integration.py
@pytest.mark.integration
def test_full_command_generation():
    """Test complete command generation workflow."""
    manager = YourServiceManager()
    
    # Test server command
    server_cmd = manager.generate_run_command(
        role="server",
        port=8080,
        config_file="/app/config.yaml",
        performance_mode="high"
    )
    
    expected_components = [
        manager._get_binary_name(),
        "--listen", "0.0.0.0:8080",
        "--config", "/app/config.yaml",
        "--high-performance"
    ]
    
    for component in expected_components:
        assert str(component) in server_cmd
```

### 3. Configuration Testing

Create a comprehensive test configuration:

```yaml
# test_config.yaml
logging:
  level: DEBUG
  
observers:
  logger:
    enabled: true
  metrics:
    enabled: true
    
tests:
  - name: "Implementation Test"
    description: "Test your protocol implementation"
    network_environment:
      type: "docker_compose"
    execution_environment:
      - type: "gperf_cpu"
        config:
          duration: 30
    services:
      server:
        implementation:
          name: "your_implementation"
          type: "iut"
          performance_mode: "high"
          debug_level: 1
        protocol:
          name: "your_protocol"
          version: "1.0"
          role: "server"
        timeout: 60
        ports: ["8080:8080"]
      client:
        implementation:
          name: "your_implementation" 
          type: "iut"
          performance_mode: "balanced"
        protocol:
          name: "your_protocol"
          version: "1.0"
          role: "client"
          target: "server"
        timeout: 50
    steps:
      wait: 45
```

### 4. Run Tests

Execute tests with your implementation:

```bash
# Run with debug logging
python -m panther --experiment-config test_config.yaml --debug

# Validate configuration before running
python -m panther --experiment-config test_config.yaml --validate-config

# Run with metrics collection
python -m panther --experiment-config test_config.yaml --enable-metrics
```

## Development Best Practices

### 1. Leverage Inheritance Architecture

**DO**: Use base classes for common functionality
```python
class YourServiceManager(BaseServiceManager):
    # Only implement what's unique to your implementation
    def _get_server_specific_args(self, **kwargs) -> List[str]:
        return ["--listen", f"0.0.0.0:{kwargs.get('port', 8080)}"]
```

**DON'T**: Duplicate common protocol logic
```python
# Avoid duplicating base class functionality
def generate_run_command(self, **kwargs):
    # Don't reimplement this - it's handled by base class
```

### 2. Event-Driven Integration

**DO**: Emit meaningful events in your implementation
```python
def _do_prepare(self, plugin_manager=None):
    self.emit_event(ServicePreparationEvent(
        service_name=self._get_implementation_name(),
        preparation_type="custom_setup"
    ))
    # Custom preparation logic
```

**DON'T**: Skip event emission for debugging
```python
# Events are crucial for monitoring and debugging
```

### 3. Template Method Pattern

**DO**: Implement only the abstract methods you need
```python
class YourServiceManager(BaseServiceManager):
    def _get_implementation_name(self) -> str:
        return "your_impl"  # Required
    
    def _get_binary_name(self) -> str:
        return "your_binary"  # Required
    
    # Optional: Only implement if you have specific args
    def _get_server_specific_args(self, **kwargs) -> List[str]:
        return []
```

**DON'T**: Override main workflow methods unnecessarily
```python
# Don't override generate_run_command() unless absolutely necessary
```

### 4. Configuration Schema Design

**DO**: Provide implementation-specific configuration
```python
@dataclass
class YourImplConfig(IUTConfig):
    # Required identification
    implementation_name: str = "your_impl"
    binary_name: str = "your_binary"
    
    # Implementation-specific parameters
    custom_feature: bool = False
    optimization_level: str = "balanced"
```

**DON'T**: Duplicate base class configuration
```python
# Don't redefine common parameters - these are handled by base class
```

### 5. Testing Strategy

**DO**: Test implementation-specific logic
```python
def test_custom_arguments():
    manager = YourServiceManager()
    args = manager._get_server_specific_args(custom_feature=True)
    assert "--custom-feature" in args
```

**DON'T**: Test inherited functionality
```python
# Base class functionality is tested separately
# Focus on your implementation-specific logic
```

### 6. Docker Integration

**DO**: Use DockerBuilderFactory when possible
```python
def generate_dockerfile_content(self) -> str:
    builder = DockerBuilderFactory.create_builder(
        implementation_name=self._get_implementation_name(),
        language="rust"
    )
    return builder.generate_complete_dockerfile()
```

**DON'T**: Create custom Dockerfiles unnecessarily
```python
# Use predefined builders unless you have specific requirements
```

### 7. Documentation Standards

**DO**: Document inheritance patterns and implementation-specific features
```markdown
## Inheritance Pattern
BaseProtocolServiceManager → YourServiceManager

## Implementation-Specific Features
- Custom authentication provider
- Performance optimization modes
```

**DON'T**: Document base class functionality
```markdown
<!-- Don't document common protocol features - focus on your additions -->
```

## Reference Implementations

Examine existing implementations for best practices:

### Protocol Implementations by Type

**QUIC Protocol**:
- **PicoQUIC**: `plugins/services/iut/quic/picoquic/` - C implementation with direct inheritance
- **AioQUIC**: `plugins/services/iut/quic/aioquic/` - Python implementation with async patterns
- **Quiche**: `plugins/services/iut/quic/quiche/` - Rust implementation with Cargo integration

**HTTP Protocol**:
- **Custom HTTP**: `plugins/services/iut/http/` - Example HTTP implementation
- **HTTP/2 Support**: Advanced HTTP features and version handling

**MINIP Protocol**:
- **Ping Pong**: `plugins/services/iut/minip/ping_pong/` - Simple protocol example

### Implementation Patterns by Language

```text
├── C/C++ Implementations (Direct base class inheritance)
│   ├── picoquic/         # QUIC protocol
│   ├── lsquic/           # QUIC protocol
│   └── custom_tcp/       # Generic TCP protocol
├── Python Implementations (Language-specific extensions)
│   ├── aioquic/          # QUIC with asyncio
│   └── http_async/       # HTTP with async support
├── Rust Implementations (Cargo integration)
│   ├── quiche/           # QUIC with Tokio
│   └── quinn/            # QUIC with async runtime
└── Go Implementations (Direct inheritance)
    └── quic_go/          # QUIC protocol
```

### Key Architecture Benefits

1. **Reduced Code Duplication**: Base classes handle common protocol functionality
2. **Consistent Behavior**: Template method pattern ensures reliability
3. **Event-Driven Monitoring**: Real-time insights into implementation behavior
4. **Docker Integration**: Standardized container builds
5. **Testing Efficiency**: Focus on implementation-specific logic only

## Creating IUTs for New Protocols

When implementing a new protocol:

1. **Analyze Protocol Requirements**: Understand client/server patterns, configuration needs
2. **Choose Base Class**: Use BaseServiceManager for new protocols or existing protocol base classes
3. **Define Configuration Schema**: Create protocol-specific configuration parameters
4. **Implement Template Methods**: Focus only on implementation-specific logic
5. **Add Event Integration**: Leverage built-in event emission for monitoring
6. **Write Focused Tests**: Test only implementation-specific functionality
7. **Document Protocol Specifics**: Focus on your implementation's unique features

For comprehensive development guidance, see [Service Plugin Development Guide](../development.md).

<!-- src: /panther/plugins/services/iut/ -->
