# Network Environment Plugins

!!! info "Network Topology Management"
    Network environment plugins define the network topology, conditions, and characteristics for experiments. They enable realistic network scenarios including containerized environments and network simulation.

> **Plugin Type**: Network Environment

> **Verified Source Location**: `plugins/environments/network_environment/`

## Overview

Network environment plugins define the network topology, conditions, and characteristics for PANTHER experiments. They allow for creating realistic or controlled network scenarios for protocol testing.

<!-- src: /panther/plugins/environments/network_environment/ -->

## Available Plugins

| Plugin | Description | Documentation |
|--------|-------------|---------------|
| docker_compose | Multi-container Docker environments | [Documentation](panther/plugins/environments/network_environment/docker_compose/README.md) |
| shadow_ns | Network namespace-based simulation | [Documentation](panther/plugins/environments/network_environment/shadow_ns/README.md) |
| localhost_single_container | Single container environment | [Documentation](panther/plugins/environments/network_environment/localhost_single_container/README.md) |

## Common Configuration

Network environment plugins typically share these configuration patterns:

```yaml
environments:
  network:
    - name: "test_network"
      type: "network_environment"
      implementation: "docker_compose"
      config:
        compose_file: "network_setup.yml"
        network_name: "test_net"
```

## Integration Points

Network environment plugins integrate primarily with:

1. **Service plugins**: They provide the network context for services to operate in
2. **Protocol plugins**: They enable testing protocol behavior under different network conditions

## Development

To create a new network environment plugin, see the [Adding Network Environment](panther/plugins/ADDING_NET_ENV.md) guide.
