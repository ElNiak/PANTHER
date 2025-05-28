# Service Plugins Interface Reference

This document provides a technical reference for the service plugin interfaces in PANTHER, covering both Implementation Under Test (IUT) and Tester services.

## Service Interface

All service plugins implement a common interface defined in `services_interface.py`:

```python
from panther.plugins.plugin_interface import PluginInterface

class ServiceInterface(PluginInterface):
    """Base interface for all service plugins."""

    def initialize(self, config):
        """Initialize the service with the given configuration."""
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
        """Clean up any resources used by the service."""
        pass
```

<!-- src: /panther/plugins/services/services_interface.py -->

## Service Manager Interface

Service plugins use the service manager interface to interact with the PANTHER framework:

```python
from abc import ABC
from panther.plugins.services.services_interface import ServiceInterface

class IServiceManager(ServiceInterface, ABC):
    """Interface for service managers."""
    
    def is_tester(self):
        """Returns True if this service is a tester, False otherwise."""
        pass
    
    def get_container_name(self):
        """Get the name of the container running this service."""
        pass
    
    def get_service_endpoints(self):
        """Get the network endpoints for this service."""
        pass
    
    def get_service_logs(self):
        """Get logs from the service."""
        pass
```

## Service Types

PANTHER supports two main types of service plugins:

### Implementation Under Test (IUT) Interface

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

### Tester Interface

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

## Service Configuration Schema

Service plugins use configuration schemas to validate their parameters:

```python
from dataclasses import dataclass
from enum import Enum
from panther.plugins.services.config_schema import ServiceConfig

class ServiceType(Enum):
    """Enum for service types."""
    iut = "iut"
    tester = "tester"

@dataclass
class ServiceConfig:
    """Base configuration class for services."""
    name: str
    type: ServiceType
    implementation: str
    timeout: int = 60  # Default timeout in seconds
```

## Integration Points

Service plugins integrate with the PANTHER framework through the plugin loader:

```python
from panther.plugins.plugin_loader import PluginLoader

# Example usage
plugin_loader = PluginLoader()
service = plugin_loader.load_service("picoquic", "iut")
service.initialize(config)
service.start()
# Perform tests
service.stop()
service.cleanup()
```

## Error Handling

Service plugins use a standardized error handling approach:

```python
from panther.core.errors import ServiceError

# Example error handling in a plugin
def start(self):
    try:
        # Service startup logic
        pass
    except Exception as e:
        raise ServiceError(f"Failed to start service: {str(e)}")
```
