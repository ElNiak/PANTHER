# Adding an Execution Environment Plugin to PANTHER

This guide walks through the process of creating a new execution environment plugin for the PANTHER framework.

## Overview

Execution environment plugins provide control over the runtime context where services execute. These plugins enable resource monitoring, performance profiling, and execution control for PANTHER experiments.

## Implementation Steps

### 1. Create the Plugin Directory Structure

Create the following directory structure for your plugin:

```
panther/plugins/environments/execution_environment/your_plugin_name/
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

from panther.plugins.environments.execution_environment.config_schema import ExecutionEnvironmentConfig


@dataclass
class YourPluginConfig(ExecutionEnvironmentConfig):
    """Configuration for YourPlugin execution environment."""
    parameter1: str = "default_value"  # Add your parameters here
    parameter2: int = 100
    optional_params: Dict[str, str] = field(default_factory=dict)
```

### 3. Implement the Execution Environment Class

Create your main plugin implementation in `your_plugin_name.py`:

```python
from abc import ABC

from panther.core.observer.event_manager import EventManager
from panther.config.config_experiment_schema import TestConfig
from panther.config.config_global_schema import GlobalConfig
from panther.plugins.environments.execution_environment.your_plugin_name.config_schema import YourPluginConfig
from panther.plugins.environments.execution_environment.execution_environment_interface import IExecutionEnvironment
from panther.plugins.plugin_loader import PluginLoader
from panther.plugins.services.services_interface import IServiceManager


class YourPluginEnvironment(IExecutionEnvironment, ABC):
    """
    YourPluginEnvironment provides execution control and monitoring capabilities.
    It extends the IExecutionEnvironment interface to implement specific execution features.
    """

    def __init__(
        self,
        env_config_to_test: YourPluginConfig,
        output_dir: str,
        env_type: str,
        env_sub_type: str,
        event_manager: EventManager,
    ):
        super().__init__(
            env_config_to_test, output_dir, env_type, env_sub_type, event_manager
        )
        self.env_config_to_test = env_config_to_test

    def setup_environment(
        self,
        services_managers: list[IServiceManager],
        test_config: TestConfig,
        global_config: GlobalConfig,
        timestamp: str,
        plugin_loader: PluginLoader,
    ):
        """Set up the execution environment."""
        self.services_managers = services_managers
        self.test_config = test_config
        self.plugin_loader = plugin_loader
        self.global_config = global_config
        self.logger.debug("Setting up execution environment...")
        
        # Modify service commands or environment variables as needed
        for service in self.services_managers:
            if self.is_service_compatible(service):
                # Add environment variables, wrappers, or modify commands
                service.environments["YOUR_ENV_VAR"] = "value"
                
                # Modify run commands if needed
                service.run_cmd["pre_run_cmds"].append(
                    self.generate_command(service.service_name)
                )
                
                # Add post-processing commands if needed
                service.run_cmd["post_run_cmds"].append(
                    f"process_output {service.service_name}"
                )

    def is_service_compatible(self, service: IServiceManager) -> bool:
        """Check if a service is compatible with this execution environment."""
        # Check if the service has the required compatibility flag
        return service.service_config_to_test.implementation.get("your_plugin_compatible", False)

    def generate_command(self, service_name: str) -> str:
        """Generate a command for the given service."""
        # Create environment-specific commands
        return f"your_tool --service {service_name} --param {self.env_config_to_test.parameter1}"
```

### 4. Create the Plugin Documentation

Create a comprehensive README.md file following the PANTHER documentation template:

```markdown
# Your Plugin Name

> **Plugin Type**: Environment (execution_environment)  
> **Verified Source Location**: `plugins/environments/execution_environment/your_plugin_name/`  

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
from panther.plugins.environments.execution_environment.your_plugin_name.your_plugin_name import YourPluginEnvironment

__all__ = ["YourPluginEnvironment"]
```

## Testing Your Plugin

1. Create a test configuration file:

```yaml
tests:
  - name: "Test with Your Execution Plugin"
    execution_environment:
      - name: "your_plugin_instance"
        type: "execution_environment"
        implementation: "your_plugin_name"
        config:
          parameter1: "value1"
          parameter2: 200
    services:
      server:
        name: "test_server" 
        implementation: 
          name: "test_implementation"
          type: "iut"
          your_plugin_compatible: true
```

2. Run PANTHER with your test configuration:

```bash
python -m panther -c path/to/your/test/config.yaml
```

3. Debug any issues and refine your implementation.

## Best Practices

1. **Service Compatibility**: Clearly define how services indicate compatibility with your environment
2. **Minimal Interference**: Design your plugin to have minimal impact on service behavior unless explicitly desired
3. **Resource Management**: Properly manage any resources your plugin allocates
4. **Output Collection**: Provide clear mechanisms for collecting and analyzing plugin-generated data
5. **Documentation**: Keep your README.md updated with accurate information

## Example Implementation

For reference, you can examine existing execution environment plugins:

- GPerf CPU: `plugins/environments/execution_environment/gperf_cpu/`
- GPerf Heap: `plugins/environments/execution_environment/gperf_heap/`
- Strace: `plugins/environments/execution_environment/strace/`
