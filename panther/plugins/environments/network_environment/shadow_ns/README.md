# Shadow NS Environment

> **Plugin Type**: Network Environment
> **Source Location**: `plugins/environments/network_environment/shadow_ns/`

## Overview

The Shadow NS Environment plugin provides a high-fidelity network simulation environment for testing protocol implementations in reproducible network conditions. It leverages the Shadow discrete-event network simulator, running real unmodified application binaries natively as standard OS processes while intercepting and emulating system calls through an internal simulated network.

> [!WARNING]
> Not all implementations under test are compatible with Shadow due to potential missing system call implementations. Test compatibility before deploying production experiments.

## Configuration Options

<!-- src: config_schema.py -->

```yaml
network_environment:
  type: "shadow_ns"
  general:
    stop_time: "300s"                    # Simulation duration
    model_unblocked_syscall_latency: false
  experimental:
    strace_logging_mode: "standard"      # 'none', 'standard', 'detailed'
  network:
    latency: 10                          # Network latency in milliseconds
    jitter: 10                           # Network jitter in milliseconds
    packet_loss: 0.0                     # Packet loss rate (0.0 to 1.0)
  host_option_defaults:
    pcap_enabled: true                   # Enable packet capture
```

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

## Usage Example

```yaml
tests:
  - name: "Shadow Network Test"
    network_environment:
      type: "shadow_ns"
      general:
        stop_time: 100
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

## Integration

- Integrates with the PANTHER event management system for lifecycle coordination
- Uses `EnvironmentManagerDockerMixin` for consistent Docker operations across all network environments
- Requires service plugins compatible with Shadow's system call emulation
- Produces pcap files and Shadow logs in the output directory for post-experiment analysis

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Unsupported system call crashes | Check Shadow documentation for supported calls; use an alternative implementation |
| Slow simulation execution | Reduce simulation complexity, decrease simulation time, or restrict packet capture |
| "Resource temporarily unavailable" errors | Increase Docker container resource limits (memory, CPU) |
| Empty FROM in Dockerfile | Ensure you are using the latest version with `EnvironmentManagerDockerMixin` integration |

For debugging, enable detailed strace logging in the configuration, check Shadow logs in the output directory, and inspect the generated Dockerfile and `shadow.yml` configuration files.
