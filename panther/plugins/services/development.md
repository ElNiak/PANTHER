# Service Plugin Development Guide

This document provides comprehensive guidance for developing service plugins for the PANTHER framework, covering both Implementation Under Test (IUT) services and Tester services.

## Service Plugin Architecture

PANTHER service plugins are organized into two primary categories:

```
plugins/services/
├── iut/                 # Implementation Under Test plugins
│   ├── http/
│   ├── quic/
│   └── ...
├── testers/             # Tester plugins
│   ├── ivy_tester/
│   └── ...
├── __init__.py
├── config_schema.py
└── services_interface.py
```

<!-- src: /panther/plugins/services/services_interface.py -->

## Service Plugin Interfaces

All service plugins must implement the appropriate interface based on their category:

### Common Service Interface

```python
from panther.plugins.plugin_interface import PluginInterface

class ServiceInterface(PluginInterface):
    """Base interface for all service plugins."""
    
    def initialize(self, config):
        """Initialize the service with configuration."""
        pass
        
    def start(self):
        """Start the service."""
        pass
    
    def stop(self):
        """Stop the service."""
        pass
    
    def restart(self):
        """Restart the service."""
        pass
        
    def get_status(self):
        """Get the status of the service."""
        pass
        
    def execute(self):
        """Execute the service's main functionality."""
        pass
        
    def cleanup(self):
        """Clean up resources."""
        pass
```

### Implementation Manager Interface

For IUT services:

```python
from panther.plugins.services.services_interface import IServiceManager

class IImplementationManager(IServiceManager):
    """Interface for implementation under test managers."""
    
    def is_tester(self):
        """Returns False indicating this is not a tester."""
        return False
    
    def get_implementation_version(self):
        """Get the version of the implementation."""
        pass
    
    def get_implementation_capabilities(self):
        """Get the capabilities of the implementation."""
        pass
```

### Tester Manager Interface

For tester services:

```python
from panther.plugins.services.services_interface import IServiceManager

class ITesterManager(IServiceManager):
    """Interface for tester service managers."""
    
    def is_tester(self):
        """Returns True indicating this is a tester."""
        return True
    
    def run_test(self, test_case):
        """Run a specific test case."""
        pass
    
    def get_test_results(self):
        """Get the results of the tests."""
        pass
```

## Creating a New Service Plugin

### 1. Choose Service Type

Determine whether your service is an Implementation Under Test (IUT) or a Tester.

### 2. Set Up the Plugin Directory

Create a directory for your service in the appropriate location:

```
# For IUT:
plugins/services/iut/<protocol_name>/<implementation_name>/
├── __init__.py
├── plugin.py           # Main service implementation
├── config_schema.py    # Configuration schema
├── README.md           # Service documentation
└── tests/              # Service tests
    └── test_plugin.py

# For Tester:
plugins/services/testers/<tester_name>/
├── __init__.py
├── plugin.py
├── config_schema.py
├── README.md
└── tests/
```

### 3. Implement the Service Interface

#### For IUT Service:

```python
# plugins/services/iut/<protocol>/<implementation>/plugin.py
from panther.plugins.services.iut.implementation_interface import IImplementationManager

class MyImplementation(IImplementationManager):
    """My custom implementation under test."""
    
    def initialize(self, config):
        """Initialize the implementation with configuration."""
        self.config = config
        # Implementation initialization
        
    def start(self):
        """Start the implementation."""
        # Service startup logic
        pass
    
    def stop(self):
        """Stop the implementation."""
        # Service shutdown logic
        pass
        
    def execute(self):
        """Execute the implementation's main functionality."""
        # Implementation execution logic
        pass
        
    def cleanup(self):
        """Clean up resources."""
        # Release resources
        pass
```

#### For Tester Service:

```python
# plugins/services/testers/<tester_name>/plugin.py
from panther.plugins.services.testers.tester_interface import ITesterManager

class MyTester(ITesterManager):
    """My custom tester service."""
    
    def initialize(self, config):
        """Initialize the tester with configuration."""
        self.config = config
        self.test_results = {}
        # Tester initialization
        
    def run_test(self, test_case):
        """Run a specific test case."""
        # Test execution logic
        pass
    
    def get_test_results(self):
        """Get the test results."""
        return self.test_results
        
    def execute(self):
        """Execute the tester's main functionality."""
        # Tester execution logic
        pass
        
    def cleanup(self):
        """Clean up resources."""
        # Release resources
        pass
```

### 4. Define Configuration Schema

#### For IUT Service:

```python
# plugins/services/iut/<protocol>/<implementation>/config_schema.py
from dataclasses import dataclass, field
from panther.plugins.services.iut.config_schema import ImplementationConfig, ImplementationType

@dataclass
class MyImplementationConfig(ImplementationConfig):
    """Configuration for my implementation."""
    name: str = "my_implementation"  # Implementation name
    type: ImplementationType = ImplementationType.iut
    # Implementation-specific parameters
    port: int = 8080
    log_level: str = "info"
    extra_args: list[str] = field(default_factory=list)
```

#### For Tester Service:

```python
# plugins/services/testers/<tester_name>/config_schema.py
from dataclasses import dataclass, field
from panther.plugins.services.testers.config_schema import TesterConfig, TesterType

@dataclass
class MyTesterConfig(TesterConfig):
    """Configuration for my tester."""
    name: str = "my_tester"  # Tester name
    type: TesterType = TesterType.tester
    # Tester-specific parameters
    test_suite: str = "default"
    timeout_seconds: int = 60
    verbose: bool = False
```

### 5. Register Your Service Plugin

Make your service discoverable by updating your `__init__.py`:

```python
# plugins/services/iut/<protocol>/<implementation>/__init__.py
# or
# plugins/services/testers/<tester_name>/__init__.py
from .plugin import MyImplementation  # or MyTester

__all__ = ["MyImplementation"]  # or ["MyTester"]
```

### 6. Create Tests

Write tests to verify your service functions correctly:

```python
# plugins/services/iut/<protocol>/<implementation>/tests/test_plugin.py
# or
# plugins/services/testers/<tester_name>/tests/test_plugin.py
import pytest
from panther.plugins.services.iut.<protocol>.<implementation>.plugin import MyImplementation

def test_service_initialization():
    service = MyImplementation()
    config = {"port": 8080}
    service.initialize(config)
    # Assert expected initialization behavior
    
def test_service_execution():
    service = MyImplementation()
    service.initialize({"port": 8080})
    service.start()
    # Assert service started correctly
    service.stop()
    service.cleanup()
```

### 7. Document Your Service

Create a README.md file using the [plugin template](../../../plugin_template.md) that includes:

- Service purpose and capabilities
- Configuration options and examples
- Integration with protocols and environments
- Testing and troubleshooting guidance

## Best Practices for Service Plugins

1. **Separation of Concerns**: Keep service logic separate from protocol and environment specifics
2. **Resource Management**: Properly release all resources in the cleanup method
3. **Error Handling**: Provide clear error messages and graceful failure handling
4. **Configuration Validation**: Thoroughly validate all input parameters
5. **Logging**: Include adequate logging for debugging and monitoring
6. **Documentation**: Document all configuration options and usage examples

## Service Integration

Services need to integrate with other PANTHER components:

1. **Protocol Integration**: Connect services to appropriate protocols
2. **Environment Integration**: Ensure services work in different execution and network environments
3. **Test Framework Integration**: Provide proper metrics and results collection

## Documentation Verification

Ensure all service documentation includes source references:

```markdown
This service implements the QUIC protocol according to RFC9000.
<!-- src: /panther/plugins/services/iut/quic/picoquic/plugin.py -->
```
