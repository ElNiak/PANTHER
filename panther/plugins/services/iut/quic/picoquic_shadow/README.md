# Picoquic Shadow Plugin

> **Plugin Type**: Service (IUT - Implementation Under Test)
> **Protocol**: QUIC
> **Verified Source Location**: `plugins/services/iut/quic/picoquic_shadow/`

## Purpose and Overview

The Picoquic Shadow plugin provides a specialized integration of the Picoquic QUIC implementation designed specifically for use with the Shadow network simulator. This variant enables large-scale network simulation experiments with thousands of nodes while maintaining the performance characteristics and protocol compliance of the standard Picoquic implementation.

<!-- src: /panther/plugins/services/iut/quic/picoquic_shadow/picoquic_shadow.py -->

This implementation is valuable for:
- **Large-scale network simulation**: Simulating thousands of QUIC connections in Shadow
- **Network topology research**: Testing QUIC behavior across complex network topologies
- **Performance analysis at scale**: Evaluating QUIC performance under various network conditions
- **Protocol research**: Studying QUIC behavior in controlled, reproducible network environments
- **Shadow-specific optimizations**: Leveraging Shadow's simulation capabilities for QUIC research

The Shadow integration allows for deterministic, repeatable experiments with precise control over network conditions, making it ideal for academic research and large-scale protocol evaluation.

## Key Features

### Shadow Network Simulator Integration
- **Deterministic simulation**: Reproducible experiments with controlled network conditions
- **Scalable architecture**: Support for thousands of simulated nodes and connections
- **Network topology simulation**: Complex network topologies with realistic latency and bandwidth
- **Event-driven simulation**: Precise timing control for protocol analysis

### Picoquic Core Features (Shadow-Compatible)
- **QUIC version support**: QUIC v1 (RFC 9000) and draft versions
- **HTTP/3 support**: Full HTTP/3 implementation over QUIC
- **Connection migration**: Seamless connection migration across network paths
- **Loss recovery**: Advanced loss detection and recovery mechanisms
- **Congestion control**: Multiple congestion control algorithms (NewReno, BBR, Cubic)

### Research and Development Features
- **Protocol experimentation**: Support for custom QUIC extensions and modifications
- **Performance metrics**: Detailed simulation metrics and performance analysis
- **Debugging support**: Enhanced logging and state inspection for simulation environments
- **Batch experimentation**: Support for large-scale parameter sweeps and experiments

## Requirements and Dependencies

### System Requirements
- **Shadow Network Simulator**: Compatible version with QUIC support
- **Build tools**: CMake, GCC/Clang, Make
- **Libraries**: OpenSSL, libev, picotls
- **Container runtime**: Docker (for containerized Shadow experiments)

### Python Dependencies
```bash
# Core dependencies from requirements
omegaconf>=2.0
dataclasses-json
```

### Build Dependencies
The plugin automatically manages the following build dependencies:
- **Picotls**: TLS 1.3 implementation (configured via dependencies)
- **OpenSSL**: Cryptographic library
- **CMake build system**: For compilation management

## Configuration Options

The Picoquic Shadow plugin accepts the following configuration parameters:

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `name` | String | `"picoquic_shadow"` | Implementation identifier |
| `type` | ImplementationType | `iut` | Plugin type designation |
| `shadow_compatible` | Boolean | `true` | Shadow simulator compatibility flag |
| `version.version` | String | `""` | Picoquic version to use |
| `version.commit` | String | `""` | Git commit hash for specific version |
| `version.dependencies` | List | `[]` | Build dependencies configuration |
| `version.client` | Dict | `{}` | Client-specific configuration |
| `version.server` | Dict | `{}` | Server-specific configuration |

### Version Configuration Schema
```yaml
version:
  version: "master"           # Git branch or tag
  commit: "abc123def456"      # Specific commit hash
  dependencies:               # Build dependencies
    - name: "picotls"
      url: "https://github.com/h2o/picotls.git"
      commit: "def789abc012"
  client:                     # Client-specific settings
    default_port: 4433
    max_connections: 1000
  server:                     # Server-specific settings
    bind_address: "0.0.0.0"
    port: 4433
```

## Usage Examples

### Basic Shadow Simulation Configuration

```yaml
# experiment_config_shadow_quic.yaml
services:
  - name: "picoquic_shadow_server"
    type: "iut"
    implementation: "picoquic_shadow"
    role: "server"
    config:
      shadow_compatible: true
      version:
        version: "master"
        dependencies:
          - name: "picotls"
            url: "https://github.com/h2o/picotls.git"
            commit: "latest"

  - name: "picoquic_shadow_client"
    type: "iut"
    implementation: "picoquic_shadow"
    role: "client"
    config:
      shadow_compatible: true
```

### Large-Scale Simulation Configuration

```yaml
# Shadow topology with multiple clients
services:
  - name: "picoquic_shadow_server_central"
    type: "iut"
    implementation: "picoquic_shadow"
    role: "server"
    instances: 1
    config:
      shadow_compatible: true
      version:
        server:
          max_connections: 10000
          threads: 8

  - name: "picoquic_shadow_clients"
    type: "iut"
    implementation: "picoquic_shadow"
    role: "client"
    instances: 1000
    config:
      shadow_compatible: true
      version:
        client:
          connection_timeout: 30
          request_rate: 1.0
```

### Research Configuration with Custom Extensions

```yaml
# Research experiment with protocol modifications
services:
  - name: "picoquic_research_server"
    type: "iut"
    implementation: "picoquic_shadow"
    role: "server"
    config:
      shadow_compatible: true
      version:
        version: "research-branch"
        commit: "experimental-features"
        dependencies:
          - name: "picotls"
            url: "https://github.com/h2o/picotls.git"
            commit: "experimental"
        server:
          enable_custom_extensions: true
          log_level: "debug"
          metrics_collection: true
```

## Integration Examples

### Shadow Network Environment Integration

```python
# Python integration with Shadow environment
from panther.plugins.plugin_loader import PluginLoader

# Load Shadow environment and Picoquic Shadow implementation
loader = PluginLoader()
shadow_env = loader.load_plugin('environments', 'network_environment', 'shadow_ns')
picoquic_shadow = loader.load_plugin('services', 'iut', 'quic', 'picoquic_shadow')

# Configure for large-scale simulation
shadow_config = {
    'topology': 'large_scale',
    'nodes': 1000,
    'simulation_time': 3600
}

picoquic_config = {
    'shadow_compatible': True,
    'version': {
        'version': 'master',
        'server': {'max_connections': 5000},
        'client': {'connection_rate': 10.0}
    }
}

# Initialize for simulation
shadow_env.initialize(shadow_config)
picoquic_shadow.initialize(picoquic_config)
```

### Performance Analysis Setup

```python
# Integration with performance monitoring
experiment_config = {
    'services': [
        {
            'name': 'picoquic_shadow_perf',
            'type': 'iut',
            'implementation': 'picoquic_shadow',
            'config': {
                'shadow_compatible': True,
                'version': {
                    'server': {
                        'enable_metrics': True,
                        'metrics_interval': 1.0,
                        'detailed_logging': True
                    }
                }
            }
        }
    ],
    'environments': [
        {
            'name': 'shadow_large_scale',
            'type': 'network_environment',
            'implementation': 'shadow_ns',
            'config': {
                'topology_file': 'large_scale_topology.xml',
                'simulation_time': 7200
            }
        }
    ]
}
```

## Troubleshooting

### Common Issues and Solutions

#### Shadow Compatibility Issues
```bash
# Verify Shadow simulator installation
shadow --version

# Check Picoquic Shadow build compatibility
docker logs <picoquic_shadow_container> | grep "Shadow"

# Validate Shadow-specific configurations
grep -r "shadow_compatible" /path/to/config/
```

#### Build and Dependency Issues
```bash
# Check dependency resolution
cat /opt/picoquic_shadow/dependencies.json

# Verify CMake configuration
cmake --version
cmake -LA /opt/picoquic_shadow/build/ | grep -i shadow

# Debug build process
docker build --no-cache -f Dockerfile --target debug .
```

#### Performance and Scaling Issues
```bash
# Monitor Shadow simulation performance
shadow --log-level debug --template-directory /etc/shadow

# Check resource utilization
docker stats <picoquic_shadow_container>

# Validate simulation parameters
shadow-validator --config shadow_config.xml
```

### Debug Configuration

```yaml
# Enhanced debugging for Shadow experiments
services:
  - name: "picoquic_shadow_debug"
    type: "iut"
    implementation: "picoquic_shadow"
    config:
      shadow_compatible: true
      version:
        server:
          log_level: "debug"
          enable_packet_logging: true
          enable_state_logging: true
          metrics_output: "/tmp/picoquic_metrics.log"
      debug:
        enable_gdb: false  # GDB not compatible with Shadow
        enable_strace: false  # Use Shadow's built-in tracing
        shadow_log_level: "debug"
```

## Development and Extension

### Building Custom Versions

```bash
# Build Picoquic Shadow with custom features
git clone https://github.com/private-octopus/picoquic.git picoquic_shadow
cd picoquic_shadow
git checkout <research-branch>

# Apply Shadow-specific patches
patch -p1 < shadow_integration.patch

# Build with Shadow support
mkdir build && cd build
cmake -DSHADOW_SUPPORT=ON -DCMAKE_BUILD_TYPE=Debug ..
make -j$(nproc)
```

### Adding Custom Extensions

```c
// Example custom extension for Shadow experiments
// filepath: picoquic_shadow_extensions.c

#ifdef SHADOW_SUPPORT
#include "shadow_interface.h"

// Custom metrics collection for Shadow
void picoquic_shadow_collect_metrics(picoquic_cnx_t* cnx) {
    if (shadow_is_simulation()) {
        shadow_log_metric("quic.rtt", cnx->path[0]->rtt_min);
        shadow_log_metric("quic.cwnd", cnx->path[0]->cwin);
        shadow_log_metric("quic.bytes_sent", cnx->nb_bytes_sent);
    }
}
#endif
```

### Research Integration

```python
# Integration with research frameworks
# filepath: picoquic_shadow_research.py

class PicoquicShadowResearch:
    def __init__(self, config):
        self.config = config
        self.shadow_interface = ShadowInterface()

    def run_parameter_sweep(self, parameters):
        """Run experiments with parameter variations"""
        results = []
        for param_set in parameters:
            shadow_config = self.generate_shadow_config(param_set)
            picoquic_config = self.generate_picoquic_config(param_set)

            result = self.run_experiment(shadow_config, picoquic_config)
            results.append(result)

        return self.analyze_results(results)

    def analyze_protocol_behavior(self, traces):
        """Analyze QUIC protocol behavior from Shadow traces"""
        metrics = {
            'connection_establishment_time': [],
            'handshake_duration': [],
            'migration_events': [],
            'congestion_window_evolution': []
        }

        for trace in traces:
            metrics.update(self.extract_metrics(trace))

        return self.generate_analysis_report(metrics)
```

## Performance Considerations

### Shadow Simulation Optimization
- **Memory usage**: Shadow simulations can be memory-intensive with many nodes
- **CPU utilization**: Multi-threaded Shadow simulations benefit from high core counts
- **Simulation time**: Large-scale experiments may require extended simulation periods
- **Result storage**: Simulation outputs can generate substantial data volumes

### Network Topology Considerations
- **Node scaling**: Test with progressively larger node counts to identify scaling limits
- **Bandwidth simulation**: Ensure realistic bandwidth constraints for accurate results
- **Latency modeling**: Use appropriate latency distributions for target scenarios
- **Loss patterns**: Configure realistic packet loss patterns for protocol evaluation

## Integration with Testing Framework

This plugin integrates with PANTHER's testing infrastructure through:
- **Shadow environment plugins**: Seamless integration with Shadow network simulator
- **Protocol testing**: Compatible with QUIC protocol test suites
- **Performance monitoring**: Integration with execution environment plugins
- **Result analysis**: Automated collection and analysis of simulation results

## Related Documentation

- [Shadow Network Environment Plugin](panther/plugins/services/iut/environments/network_environment/shadow_ns/README.md)
- [Picoquic Standard Plugin](panther/plugins/services/iut/quic/picoquic/README.md)
- [QUIC Protocol Documentation](panther/plugins/protocols/client_server/quic/README.md)
- [Shadow Simulator Documentation](https://shadow.github.io/)
- [Picoquic Project Repository](https://github.com/private-octopus/picoquic)

---

*For additional support or questions about the Picoquic Shadow plugin, please refer to the main PANTHER documentation or contact the development team.*
