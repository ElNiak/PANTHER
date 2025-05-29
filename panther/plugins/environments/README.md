<!-- filepath: /Users/elniak/Documents/Project/PANTHER/panther/plugins/environments/README.md -->
# PANTHER Environment Plugins

**Execution and network environment management for testing**

Environment plugins manage where and how tests execute within PANTHER. They provide abstractions for different deployment scenarios, from localhost testing to containerized environments and network simulation platforms.

<!-- src: /panther/plugins/environments/environment_interface.py -->

## Environment Categories

### Execution Environments

Execution environment plugins provide monitoring, profiling, and analysis capabilities during test execution.

| Tool | Purpose | Documentation |
|------|---------|---------------|
| **gperf_cpu** | CPU profiling and performance analysis | [Documentation](panther/plugins/environments/execution_environment/gperf_cpu) |
| **gperf_heap** | Memory allocation profiling | [Documentation](panther/plugins/environments/execution_environment/gperf_heap) |
| **strace** | System call tracing | [Documentation](panther/plugins/environments/execution_environment/strace) |
| **memcheck** | Memory error detection | [Documentation](panther/plugins/environments/execution_environment/memcheck) |
| **helgrind** | Thread error detection | [Documentation](panther/plugins/environments/execution_environment/helgrind) |

### Network Environments

Network environment plugins manage network topology, containerization, and simulation infrastructure.

| Environment | Purpose | Documentation |
|-------------|---------|---------------|
| **docker_compose** | Multi-container testing environments | [Documentation](panther/plugins/environments/network_environment/docker_compose) |
| **shadow_ns** | Network simulation and emulation | [Documentation](panther/plugins/environments/network_environment/shadow_ns) |

## Quick Start

### Using an Execution Environment

```python
# filepath: example_execution_env.py
from panther.plugins.plugin_loader import PluginLoader

# Load CPU profiling environment
loader = PluginLoader()
gperf_cpu = loader.load_plugin('environments', 'execution_environment', 'gperf_cpu')

# Configure profiling
config = {
    "profile_frequency": 100,
    "output_file": "/tmp/cpu_profile.prof",
    "target_process": "picoquic_server"
}

gperf_cpu.initialize(config)
```

### Using a Network Environment

```python
# filepath: example_network_env.py
from panther.plugins.plugin_loader import PluginLoader

# Load Docker Compose environment
loader = PluginLoader()
docker_env = loader.load_plugin('environments', 'network_environment', 'docker_compose')

# Configure network topology
config = {
    "compose_file": "docker-compose.yml",
    "network_name": "panther_test_net",
    "services": ["quic_server", "quic_client"]
}

docker_env.setup_environment(config)
```

## Directory Structure

```text
environments/
├── README.md                    # This file
├── environment_interface.py    # Base environment interface
├── config_schema.py           # Configuration validation
├── execution_environment/     # Execution monitoring tools
│   ├── README.md
│   ├── config_schema.py
│   ├── execution_environment_interface.py
│   ├── gperf_cpu/            # CPU profiling
│   ├── gperf_heap/           # Memory profiling
│   ├── strace/               # System call tracing
│   ├── memcheck/             # Memory error detection
│   └── helgrind/             # Thread error detection
└── network_environment/       # Network deployment
    ├── README.md
    ├── docker_compose/       # Container orchestration
    └── shadow_ns/            # Network simulation
```

## Environment Interfaces

### Base Environment Interface

```python
# filepath: /panther/plugins/environments/environment_interface.py
from panther.plugins.plugin_interface import IPlugin

class EnvironmentInterface(IPlugin):
    """Base interface for environment plugins."""

    def setup_environment(self, config):
        """Setup the testing environment."""
        pass

    def teardown_environment(self):
        """Clean up the testing environment."""
        pass

    def get_environment_status(self):
        """Get current environment status."""
        pass
```

### Execution Environment Interface

```python
# filepath: /panther/plugins/environments/execution_environment/execution_environment_interface.py
from panther.plugins.environments.environment_interface import EnvironmentInterface

class ExecutionEnvironmentInterface(EnvironmentInterface):
    """Interface for execution monitoring environments."""

    def start_monitoring(self, target_process):
        """Start monitoring target process."""
        pass

    def stop_monitoring(self):
        """Stop monitoring and collect results."""
        pass

    def get_monitoring_data(self):
        """Retrieve collected monitoring data."""
        pass
```

## Configuration

### Common Configuration Options

All environment plugins support these base options:

- **environment_name**: Unique identifier for the environment
- **cleanup_on_exit**: Automatically clean up resources when done
- **timeout**: Maximum setup/execution time
- **logging_level**: Environment-specific logging

### Execution Environment Configuration

- **target_process**: Process or service to monitor
- **monitoring_duration**: How long to collect data
- **output_directory**: Where to store monitoring results
- **sampling_rate**: Data collection frequency

### Network Environment Configuration

- **network_topology**: Network layout and connections
- **deployment_target**: Where to deploy (local, cloud, simulation)
- **resource_limits**: CPU, memory, network constraints
- **service_dependencies**: Service startup order and dependencies

## Environment Integration

Environment plugins integrate with the PANTHER experiment lifecycle:

1. **Setup Phase**: Environment plugins prepare the testing infrastructure
2. **Execution Phase**: Monitor and manage running tests
3. **Collection Phase**: Gather results and monitoring data
4. **Teardown Phase**: Clean up resources and temporary files

### Execution Flow

```python
# filepath: example_environment_flow.py
# 1. Setup environment
environment.setup_environment(config)

# 2. Start monitoring (execution environments)
if isinstance(environment, ExecutionEnvironmentInterface):
    environment.start_monitoring(target_process)

# 3. Run tests (handled by core framework)
# ...

# 4. Stop monitoring and collect results
if isinstance(environment, ExecutionEnvironmentInterface):
    monitoring_data = environment.get_monitoring_data()

# 5. Teardown environment
environment.teardown_environment()
```

## Development

For information on creating new environment plugins:

- **[Environment Plugin Development Guide](panther/plugins/environments/development.md)**: Comprehensive development documentation
- **[Execution Environment Development](panther/plugins/environments/execution_environment/development.md)**: Creating monitoring tools
- **[Network Environment Development](panther/plugins/environments/network_environment/development.md)**: Creating deployment environments

## API Reference

Detailed API documentation for environment plugins:

- **[Environment Interfaces](./index.md)**: Auto-generated API reference
- **[Configuration Schema](panther/plugins/environments/config_schema.py)**: Configuration validation
- **[Execution Environment API](panther/plugins/environments/execution_environment)**: Monitoring and profiling interfaces
