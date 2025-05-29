# Adding a Network Environment Plugin to PANTHER

This guide walks through the process of creating a new network environment plugin for the PANTHER framework.

## Overview

Network environment plugins define the network topology, conditions, and characteristics for PANTHER experiments. They allow for creating realistic or controlled network scenarios for protocol testing.

## Implementation Steps

### 1. Create the Plugin Directory Structure

Create the following directory structure for your plugin:

```
panther/plugins/environments/network_environment/your_plugin_name/
├── __init__.py
├── your_plugin_name.py
├── config_schema.py
└── README.md
```

### 2. Define the Configuration Schema

Create a configuration schema in `config_schema.py` that defines the parameters your plugin accepts:

```python
from dataclasses import dataclass, field
from typing import Dict, List, Optional

from panther.config.config_experiment_schema import NetworkEnvironmentConfig


@dataclass
class YourPluginConfig(NetworkEnvironmentConfig):
    """Configuration for YourPlugin network environment."""
    type: str = "your_plugin_name"
    version: str = "1.0"
    parameter1: str = "default_value"  # Add your parameters here
    parameter2: int = 100
    optional_params: Dict[str, str] = field(default_factory=dict)
```

### 3. Implement the Network Environment Class

Create your main plugin implementation in `your_plugin_name.py`:

```python
from panther.core.observer.event_manager import EventManager
from panther.config.config_experiment_schema import TestConfig
from panther.config.config_global_schema import GlobalConfig
from panther.plugins.environments.config_schema import EnvironmentConfig
from panther.plugins.services.services_interface import IServiceManager
from panther.plugins.environments.execution_environment.execution_environment_interface import IExecutionEnvironment
from panther.plugins.plugin_loader import PluginLoader
from panther.plugins.environments.network_environment.network_environment_interface import INetworkEnvironment


class YourPluginEnvironment(INetworkEnvironment):
    """
    YourPluginEnvironment provides a network environment for testing purposes.
    It extends the INetworkEnvironment interface and provides methods to prepare,
    set up, deploy, monitor, and tear down the environment.
    """

    def __init__(
        self,
        env_config_to_test: EnvironmentConfig,
        output_dir: str,
        env_type: str,
        env_sub_type: str,
        event_manager: EventManager,
    ):
        super().__init__(
            env_config_to_test, output_dir, env_type, env_sub_type, event_manager
        )
        # Initialize your plugin-specific attributes here

    def prepare_environment(self):
        """Prepare the environment for deployment."""
        self.logger.info("Preparing environment...")
        # Implement environment preparation logic

    def setup_environment(
        self,
        services_managers: list[IServiceManager],
        test_config: TestConfig,
        global_config: GlobalConfig,
        timestamp: str,
        plugin_loader: PluginLoader,
        execution_environment: list[IExecutionEnvironment] = None,
    ):
        """Set up the environment with services and configurations."""
        self.logger.info("Setting up environment...")
        self.services_managers = services_managers
        self.test_config = test_config
        self.global_config = global_config
        # Implement environment setup logic

    def deploy_services(self):
        """Deploy services in the environment."""
        self.logger.info("Deploying services...")
        # Implement service deployment logic
        return True

    def generate_environment_services(self, paths, timestamp):
        """Generate environment-specific service configurations."""
        self.logger.info("Generating environment services...")
        # Implement service generation logic

    def launch_environment_services(self):
        """Launch services in the environment."""
        self.logger.info("Launching services...")
        # Implement service launch logic
        return True

    def monitor_environment(self):
        """Monitor the environment during execution."""
        self.logger.info("Monitoring environment...")
        # Implement monitoring logic
        return True

    def teardown_environment(self):
        """Clean up and tear down the environment."""
        self.logger.info("Tearing down environment...")
        # Implement cleanup logic
        return True
```

### 4. Create the Plugin Documentation

Create a comprehensive README.md file following the PANTHER documentation template:

```markdown
# Your Plugin Name

> **Plugin Type**: Network Environment

> **Verified Source Location**: `plugins/environments/network_environment/your_plugin_name/`

## Purpose and Overview

Describe your plugin's purpose and how it works.

## Requirements and Dependencies

List all dependencies required by this plugin.

## Configuration Options

Document all configuration parameters.

## Usage Examples

Provide examples of how to use your plugin.

## Extension Points

Document how your plugin can be extended.

## Testing and Verification

Explain how to test your plugin.

## Troubleshooting

Document common issues and solutions.
```

### 5. Register the Plugin

Make sure your plugin can be discovered by PANTHER by updating the `__init__.py` file:

```python
from panther.plugins.environments.network_environment.your_plugin_name.your_plugin_name import YourPluginEnvironment

__all__ = ["YourPluginEnvironment"]
```

## Testing Your Plugin

1. Create a test configuration file:

```yaml
tests:
  - name: "Test with Your Plugin"
    network_environment:
      type: "your_plugin_name"
      parameter1: "value1"
      parameter2: 200
    services:
      server:
        name: "test_server"
        implementation:
          name: "test_implementation"
          type: "iut"
```

2. Run PANTHER with your test configuration:

```bash
python -m panther -c path/to/your/test/config.yaml
```

3. Debug any issues and refine your implementation.

## Best Practices

1. **Proper Cleanup**: Always implement thorough cleanup in `teardown_environment()`
2. **Error Handling**: Use try/except blocks and handle errors gracefully
3. **Logging**: Use the logger provided by the base class for consistent logging
4. **Configuration Validation**: Validate configuration parameters early
5. **Documentation**: Keep your README.md updated with accurate information

## Example Implementation

For reference, you can examine existing network environment plugins:

- Docker Compose: `plugins/environments/network_environment/docker_compose/`
- Shadow NS: `plugins/environments/network_environment/shadow_ns/`
- Localhost Single Container: `plugins/environments/network_environment/localhost_single_container/`
