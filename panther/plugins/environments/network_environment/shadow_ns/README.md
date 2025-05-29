# Shadow NS Environment

> **Plugin Type**: Network Environment
> **Verified Source Location**: `plugins/environments/network_environment/shadow_ns/`

## Purpose and Overview

The Shadow NS Environment plugin provides a high-fidelity network simulation environment for testing protocol implementations in reproducible network conditions. This plugin leverages the Shadow discrete-event network simulator, running real applications in a simulated network with controlled parameters.

<!-- src: /panther/plugins/environments/network_environment/shadow_ns/shadow_ns.py -->

The Shadow NS environment is designed for:

- Executing real, unmodified application binaries natively as standard OS processes
- Creating reproducible network experiments with precise control over network conditions
- Simulating various network topologies and characteristics (latency, jitter, packet loss)
- Efficiently testing both small client/server networks and large distributed systems

Shadow intercepts and emulates system calls made by the co-opted processes, connecting them through an internal network using simulated implementations of common network protocols (e.g., TCP and UDP). This provides high reproducibility for networking experiments.

> **Note**: Not all implementations under test are compatible with Shadow due to potential missing system call implementations.

## Requirements and Dependencies

The plugin requires:

- **Docker**: Version 20.10.0 or later
- **Python Dependencies**:
  - PyYAML (for configuration parsing)
  - Jinja2 (for template rendering)

The plugin also integrates with:
- PANTHER event management system
- Service plugins that are compatible with Shadow's system call emulation

<!-- src: /panther/plugins/environments/network_environment/shadow_ns/shadow_ns.py -->

## Configuration Options

The Shadow NS environment accepts the following configuration parameters:

```yaml
network_environment:
  type: "shadow_ns"
  general:
    stop_time: "300s"                    # Simulation duration
    model_unblocked_syscall_latency: false   # Add latency for unblocked syscalls
  experimental:
    strace_logging_mode: "standard"      # Logging level for syscalls ('none', 'standard', 'detailed')
  network:
    latency: 10                          # Network latency in milliseconds
    jitter: 10                           # Network jitter in milliseconds
    packet_loss: 0.0                     # Packet loss rate (0.0 to 1.0)
  host_option_defaults:
    pcap_enabled: true                   # Enable packet capture
```

<!-- src: /panther/plugins/environments/network_environment/shadow_ns/config_schema.py -->

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `type` | string | Yes | - | Must be "shadow_ns" |
| `general.stop_time` | string | No | "300s" | Total simulation time |
| `general.model_unblocked_syscall_latency` | boolean | No | false | Add latency for unblocked syscalls |
| `experimental.strace_logging_mode` | string | No | "standard" | System call logging level |
| `network.latency` | integer | No | 10 | Network latency in milliseconds |
| `network.jitter` | integer | No | 10 | Network jitter in milliseconds |
| `network.packet_loss` | float | No | 0.0 | Packet loss probability (0.0-1.0) |
| `host_option_defaults.pcap_enabled` | boolean | No | true | Enable packet capture |

## Usage Examples

### Basic Configuration with Default Network Settings

```yaml
tests:
  - name: "Basic Shadow Network Test"
    network_environment:
      type: "shadow_ns"
      general:
        stop_time: 100
    services:
      server:
        name: "quic_server"
        implementation:
          name: "picoquic_shadow"
          type: "iut"
      client:
        name: "quic_client"
        implementation:
          name: "picoquic_shadow"
          type: "iut"
```

### Advanced Configuration with Network Impairments

```yaml
tests:
  - name: "Shadow Network Test with Impairments"
    network_environment:
      type: "shadow_ns"
      general:
        stop_time: 200
        model_unblocked_syscall_latency: true
      experimental:
        strace_logging_mode: "detailed"
      network:
        latency: 50
        jitter: 25
        packet_loss: 0.02
      host_option_defaults:
        pcap_enabled: true
    services:
      server:
        name: "quic_server"
        implementation:
          name: "picoquic_shadow"
          type: "iut"
      client:
        name: "quic_client"
        implementation:
          name: "picoquic_shadow"
          type: "iut"
```

## Extension Points

The Shadow NS environment plugin can be extended in several ways:

### Custom Network Topologies

You can extend the Shadow NS environment to support more complex network topologies:

```python
from panther.plugins.environments.network_environment.shadow_ns.shadow_ns import ShadowNsEnvironment

class CustomTopologyEnvironment(ShadowNsEnvironment):
    """Custom network environment with advanced topology features."""

    def generate_environment_services(self, paths, timestamp):
        """Generate a custom network topology."""
        # Create a custom topology configuration
        base_config = super().generate_environment_services(paths, timestamp)
        # Add custom network nodes and connections
        return modified_config
```

### Enhanced Traffic Capture

The plugin can be extended to provide more detailed network traffic analysis:

```python
def analyze_traffic(self, pcap_file):
    """Analyze network traffic from captured PCAP files."""
    # Implementation using tools like pyshark or scapy
    pass
```

## Testing and Verification

To test the Shadow NS environment plugin:

1. **Unit Tests**: Located in `/panther/plugins/environments/network_environment/shadow_ns/tests/`
2. **Integration Tests**: Run the example configuration to verify proper operation:
   ```bash
   python -m panther -c experiment-config/experiment_config_shadow_ns.yaml
   ```

3. **Verification Metrics**:
   - Verify that network parameters (latency, jitter, packet loss) are correctly applied
   - Check system call emulation works correctly for the target applications
   - Ensure reproducibility of experiments across multiple runs

## Troubleshooting

### Common Issues

#### System Call Issues

**Problem**: Service crashes with "Unsupported system call" messages.
**Solution**: Not all system calls are supported by Shadow. Check the Shadow documentation for supported calls or use an alternative implementation that relies on supported system calls.

#### Performance Problems

**Problem**: Slow simulation execution
**Solution**: Reduce simulation complexity, decrease simulation time, or restrict packet capture to specific hosts.

#### Container Limits

**Problem**: "Resource temporarily unavailable" errors
**Solution**: Shadow may need higher resource limits. Adjust Docker container resources:

```yaml
network_environment:
  type: "shadow_ns"
  container_resources:
    memory: "4G"
    cpu_limit: 2.0
```

### Debugging Tips

- Enable detailed strace logging in the configuration to see system calls
- Check Shadow logs in the output directory
- Use pcap files generated by Shadow for network traffic analysis
