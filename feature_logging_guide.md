# Feature Logging Registration Guide

PANTHER now supports dynamic feature registration for granular logging control. This guide shows how new plugins and modules can register themselves for feature-specific logging.

## Overview

The feature registration system allows plugins to:
1. **Auto-register** for specific logging features
2. **Define custom patterns** for automatic detection
3. **Set feature-specific log levels** independently
4. **Integrate seamlessly** with existing PANTHER logging

## Registration Methods

### Method 1: Decorator Registration (Recommended)

The simplest way to register a new plugin:

```python
from panther.core.utils import feature_logger, LoggerMixin

@feature_logger('my_protocol', ['myproto', 'custom'])
class MyProtocolManager(LoggerMixin):
    """Custom protocol implementation with automatic feature logging."""
    
    def __init__(self):
        super().__init__()
        # Logging automatically uses 'my_protocol' feature levels
        self.info("MyProtocol manager initialized")
    
    def process_request(self):
        self.debug("Processing custom protocol request")
        self.trace("Detailed trace for my protocol")
```

### Method 2: Manual Registration

For existing classes or more control:

```python
from panther.core.utils import register_feature, register_module_feature

# Register patterns for a feature
register_feature('distributed_testing', [
    'distributed', 'cluster', 'multi_node', 'k8s'
])

# Register specific modules
register_module_feature('panther.plugins.environments.kubernetes', 'distributed_testing')
register_module_feature('panther.plugins.environments.nomad', 'distributed_testing')

class ExistingService:
    def __init__(self):
        # Register this specific class
        register_module_feature(f"{__name__}.ExistingService", 'distributed_testing')
```

### Method 3: Module-Level Registration

Register in your plugin's `__init__.py`:

```python
# panther/plugins/protocols/http3/__init__.py
from panther.core.utils import register_feature

# Register HTTP/3 related patterns
register_feature('http3_operations', [
    'http3', 'h3', 'quic_http', 'http_over_quic'
])

# Register specific modules in this package
register_module_feature('panther.plugins.protocols.http3.client', 'http3_operations')
register_module_feature('panther.plugins.protocols.http3.server', 'http3_operations')
```

### Method 4: Plugin Manifest Registration

For comprehensive plugin registration:

```python
# Plugin registration function
def register_plugin_features():
    """Register all features for this plugin."""
    
    # Main feature
    register_feature('msquic_operations', [
        'msquic', 'microsoft', 'winquic'
    ])
    
    # Implementation-specific features
    register_feature('windows_networking', [
        'windows', 'win32', 'winsock'
    ])
    
    # Register modules
    modules = [
        'panther.plugins.services.iut.quic.msquic.client',
        'panther.plugins.services.iut.quic.msquic.server',
        'panther.plugins.services.iut.quic.msquic.manager'
    ]
    
    for module in modules:
        register_module_feature(module, 'msquic_operations')

# Call during plugin initialization
register_plugin_features()
```

## Configuration Usage

Once registered, features can be controlled in configuration files:

```yaml
logging:
  level: INFO
  feature_levels:
    # Your custom features
    my_protocol: DEBUG
    distributed_testing: TRACE
    http3_operations: INFO
    msquic_operations: DEBUG
    windows_networking: WARNING
    
    # Existing PANTHER features
    docker_operations: DEBUG
    command_generation: INFO
    quic_services: DEBUG
```

## Real-World Examples

### New QUIC Implementation

```python
# panther/plugins/services/iut/quic/msquic/msquic.py
from panther.core.utils import feature_logger
from panther.plugins.services.base.quic_service_base import BaseQUICServiceManager

@feature_logger('msquic_operations', ['msquic', 'microsoft'])
class MSQuicServiceManager(BaseQUICServiceManager):
    """Microsoft QUIC implementation with feature logging."""
    
    def __init__(self):
        super().__init__()
        # Uses 'msquic_operations' logging level
        self.info("MSQuic service manager initialized")
    
    def _get_implementation_name(self) -> str:
        return "msquic"
    
    def _get_binary_name(self) -> str:
        return "msquic_sample"
    
    def generate_deployment_commands(self) -> str:
        self.debug("Generating MSQuic deployment commands")
        return "msquic_sample -server -port:4443"
```

### New Network Environment

```python
# panther/plugins/environments/network_environment/kubernetes/kubernetes.py
from panther.core.utils import feature_logger
from panther.plugins.environments.network_environment.network_environment_interface import INetworkEnvironment

@feature_logger('kubernetes_environment', ['k8s', 'kubernetes', 'container_orchestration'])
class KubernetesNetworkEnvironment(INetworkEnvironment):
    """Kubernetes network environment with dedicated logging."""
    
    def __init__(self):
        super().__init__()
        self.info("Kubernetes network environment initialized")
    
    def prepare(self):
        self.debug("Preparing Kubernetes deployment")
        self.trace("Applying K8s manifests...")
    
    def deploy(self):
        self.info("Deploying services to Kubernetes")
        self.debug("Creating pods and services")
```

### New Protocol Plugin

```python
# panther/plugins/protocols/mqtt/mqtt_manager.py
from panther.core.utils import feature_logger, register_feature

# Register MQTT-specific patterns
register_feature('mqtt_operations', [
    'mqtt', 'message_queue', 'publish', 'subscribe', 'broker'
])

@feature_logger('mqtt_operations')
class MQTTProtocolManager:
    """MQTT protocol manager with feature logging."""
    
    def __init__(self):
        self.info("MQTT protocol manager initialized")
    
    def publish_message(self, topic, message):
        self.debug(f"Publishing to topic: {topic}")
        self.trace(f"Message content: {message}")
```

## Feature Categories

Common feature categories to use or extend:

### Core Components
- `command_generation` - Command building and processing
- `template_rendering` - Template processing and rendering
- `docker_operations` - Docker build and container management
- `config_processing` - Configuration loading and validation

### Service Management
- `service_managers` - Service manager operations
- `quic_services` - QUIC implementations (picoquic, aioquic, etc.)
- `http_services` - HTTP implementations
- `custom_protocol_services` - Your custom protocol implementations

### Environment Management
- `network_environments` - Network environment setup
- `execution_environments` - Execution environment configuration
- `cloud_environments` - Cloud platform integrations
- `container_orchestration` - K8s, Docker Swarm, etc.

### Protocol Operations
- `protocol_communication` - Protocol-level communication
- `certificate_management` - TLS/SSL certificate handling
- `network_setup` - Network configuration
- `security_operations` - Security and authentication

### Specialized Features
- `distributed_testing` - Multi-node testing
- `performance_monitoring` - Performance metrics and profiling
- `formal_verification` - Ivy and formal methods
- `compliance_testing` - Standards compliance

## Best Practices

### 1. Feature Naming
- Use descriptive, lowercase names with underscores
- Follow pattern: `{domain}_{operation}` (e.g., `mqtt_operations`, `kubernetes_environment`)
- Group related functionality under common features

### 2. Pattern Selection
- Include protocol names, implementation names, and domain terms
- Use both full names and common abbreviations
- Consider variations (e.g., `k8s`, `kubernetes`)

### 3. Registration Timing
- Register in `__init__.py` files for package-wide features
- Use decorators for class-specific features
- Call registration functions during plugin initialization

### 4. Logging Levels
- Use DEBUG for detailed operational information
- Use TRACE for very detailed debugging (protocol internals)
- Use INFO for normal operation status
- Use WARNING/ERROR for issues

### 5. Integration
```python
# Good: Inherit from LoggerMixin for automatic integration
class MyPlugin(LoggerMixin):
    def __init__(self):
        super().__init__()
        self.__init_logger__('my_feature')  # Explicit feature

# Better: Use decorator for automatic registration
@feature_logger('my_feature', ['my', 'plugin'])
class MyPlugin(LoggerMixin):
    pass
```

## Testing Registration

Test your feature registration:

```python
from panther.core.utils import feature_registry

# Check if your feature is registered
features = feature_registry.get_all_features()
print(f"Registered features: {features}")

# Test feature detection
detected = feature_registry.detect_feature('your.module.name')
print(f"Detected feature: {detected}")

# Get feature info
info = feature_registry.get_feature_info()
print(f"Feature registry info: {info}")
```

## Migration from Static Mappings

If you have existing code using static feature detection:

1. **Add registration** to existing plugins:
```python
# Old: Relied on static FEATURE_MAPPINGS
class DockerBuilder(LoggerMixin):
    pass

# New: Explicit registration
@feature_logger('docker_operations')
class DockerBuilder(LoggerMixin):
    pass
```

2. **Register custom patterns**:
```python
# Register additional patterns for existing features
register_feature('docker_operations', ['podman', 'containerd'])
```

3. **Test detection** works as expected with your module names.

The system maintains backward compatibility with existing static mappings while enabling dynamic registration for new plugins.

## Advanced Usage

### Dynamic Feature Updates
```python
# Update feature levels at runtime
from panther.core.utils import LoggerFactory

LoggerFactory.update_feature_level('my_feature', 'TRACE')
```

### Multiple Features per Module
```python
# Register a module for multiple features
register_module_feature('my.module', 'primary_feature')
register_feature('secondary_feature', ['pattern'], 'my.module')
```

### Feature Hierarchies
```python
# Create related features with shared patterns
register_feature('quic_client_operations', ['quic', 'client'])
register_feature('quic_server_operations', ['quic', 'server'])
register_feature('quic_performance', ['quic', 'perf', 'benchmark'])
```

This registration system enables fine-grained logging control for any new plugin while maintaining the clean, efficient logging established in the framework.