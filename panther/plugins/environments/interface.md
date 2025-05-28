# Environment Plugins Interface Reference

This document provides a technical reference for the environment plugin interfaces in PANTHER, covering both execution and network environments.

## Common Environment Interface

All environment plugins implement a common interface defined in `environment_interface.py`:

```python
from panther.plugins.plugin_interface import PluginInterface

class EnvironmentInterface(PluginInterface):
    """Base interface for all environment plugins."""

    def initialize(self, config):
        """Initialize the environment with configuration."""
        pass
        
    def setup(self):
        """Set up the environment for execution."""
        pass
        
    def teardown(self):
        """Tear down the environment after execution."""
        pass
        
    def execute(self):
        """Execute the environment's main functionality."""
        pass
        
    def cleanup(self):
        """Clean up resources."""
        pass
```

<!-- src: /panther/plugins/environments/environment_interface.py -->

## Execution Environment Interface

Execution environment plugins also implement additional methods specific to execution control:

```python
from panther.plugins.environments.environment_interface import EnvironmentInterface

class ExecutionEnvironmentInterface(EnvironmentInterface):
    """Interface for execution environment plugins."""
    
    def start_monitoring(self):
        """Start monitoring the execution."""
        pass
        
    def stop_monitoring(self):
        """Stop monitoring the execution."""
        pass
        
    def get_metrics(self):
        """Get metrics from the execution."""
        pass
```

<!-- src: /panther/plugins/environments/execution_environment/execution_environment_interface.py -->

## Network Environment Interface

Network environment plugins implement additional methods for network configuration:

```python
from panther.plugins.environments.environment_interface import EnvironmentInterface

class NetworkEnvironmentInterface(EnvironmentInterface):
    """Interface for network environment plugins."""
    
    def get_network_info(self):
        """Get information about the network environment."""
        pass
        
    def apply_network_conditions(self, conditions):
        """Apply specific network conditions."""
        pass
        
    def reset_network_conditions(self):
        """Reset network conditions to default."""
        pass
```

<!-- src: /panther/plugins/environments/network_environment/network_environment_interface.py -->

## Configuration Schema Reference

Environment plugins use configuration schemas to validate their parameters:

### Execution Environment Schema

```python
from panther.core.config.schema import Schema, Optional, And

execution_schema = Schema({
    "name": str,
    "type": lambda s: s == "execution_environment",
    "implementation": str,
    "config": {
        # Common execution environment parameters
        Optional("output_dir"): str,
        Optional("log_level"): And(str, lambda s: s in ["DEBUG", "INFO", "WARNING", "ERROR"]),
        # Implementation-specific parameters are validated
        # by the plugin's own schema
    }
})
```

### Network Environment Schema

```python
from panther.core.config.schema import Schema, Optional, And

network_schema = Schema({
    "name": str,
    "type": lambda s: s == "network_environment",
    "implementation": str,
    "config": {
        # Common network environment parameters
        Optional("network_name"): str,
        Optional("ip_version"): And(int, lambda n: n in [4, 6]),
        # Implementation-specific parameters are validated
        # by the plugin's own schema
    }
})
```

## Integration Points

Environment plugins integrate with the PANTHER framework through the plugin manager:

```python
from panther.plugins.plugin_manager import PluginManager

# Example usage
plugin_manager = PluginManager()
environment = plugin_manager.load_plugin("docker_compose", "network_environment")
environment.initialize(config)
environment.setup()
# Run experiment
environment.teardown()
environment.cleanup()
```

## Error Handling

Environment plugins use a standardized error handling approach:

```python
from panther.core.errors import EnvironmentError

# Example error handling in a plugin
def setup(self):
    try:
        # Setup logic
        pass
    except Exception as e:
        raise EnvironmentError(f"Failed to set up environment: {str(e)}")
```
