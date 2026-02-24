# Docker Compose Environment

> **Plugin Type**: Network Environment
> **Source Location**: `plugins/environments/network_environment/docker_compose/`

## Overview

The Docker Compose Environment plugin provides containerized network environments for testing protocol implementations in isolated, reproducible settings. It leverages Docker Compose to create multi-container applications, enabling complex network topologies and controlled testing environments. The environment builds individual service images, generates docker-compose.yml with proper service definitions, sets up isolated networks, and manages shared volumes.

> [!WARNING]
> This plugin requires Docker Engine (27.03.0+) and Docker Compose (v1.27.0+) to be installed and accessible. Ensure your user has proper Docker permissions.

## Configuration Options

<!-- src: config_schema.py -->

```yaml
network_environment:
  type: "docker_compose"
  version: "3.8"              # Docker Compose file version
  network_name: "test_net"    # Name of the Docker network
  service_prefix: "panther_"  # Optional prefix for service names
  volumes:                    # Optional volume mappings
    - "/path/on/host:/path/in/container"
  environment:                # Optional environment variables
    ENV_VAR: "value"
```

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `type` | string | Yes | - | Must be "docker_compose" |
| `version` | string | No | "3.8" | Docker Compose file version |
| `network_name` | string | No | "default_network" | Name of the Docker network |
| `service_prefix` | string | No | None | Prefix added to all service names |
| `volumes` | list | No | [] | List of volume mappings |
| `environment` | dict | No | {} | Environment variables for all containers |

## Usage Example

```yaml
tests:
  - name: "Basic Network Test"
    network_environment:
      type: "docker_compose"
      network_name: "test_network"
    services:
      server:
        name: "http_server"
        implementation:
          name: "nginx"
          type: "iut"
      client:
        name: "http_client"
        implementation:
          name: "curl"
          type: "tester"
```

## Integration

- Integrates with the PANTHER event management system for lifecycle coordination
- Works with all service plugins (IUT and tester) for deploying containerized services
- Supports volume sharing for logs, certificates, and synchronization between containers
- Requires Docker Engine and Docker Compose accessible from the host

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Docker network conflicts | Ensure unique network names or use `service_prefix` |
| Permission issues | Run with appropriate Docker permissions or use sudo |
| Container communication failures | Check Docker network settings and service configurations |
| Timeouts during container startup | Increase service timeout values in configuration |

For more detailed debugging, set `logging.level: DEBUG` in your experiment configuration and use `docker compose logs` to view container logs.
