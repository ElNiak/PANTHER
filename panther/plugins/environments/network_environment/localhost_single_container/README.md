# Localhost Single Container Environment

> **Plugin Type**: Network Environment
> **Source Location**: `plugins/environments/network_environment/localhost_single_container/`

## Overview

The Localhost Single Container Environment plugin provides a lightweight containerized testing environment where all services run in a single Docker container on localhost. This environment is ideal for simple protocol testing with minimal network complexity, offering quick setup and execution for development and initial verification of protocol implementations.

## Configuration Options

<!-- src: config_schema.py -->

```yaml
network_environment:
  type: "localhost_single_container"
  version: "3.8"              # Docker Compose file version
  network_name: "default_network"  # Name of the virtual network
  service_prefix: "test_"     # Optional prefix for service names
  environment:                # Optional environment variables
    DEBUG: "true"
    LOG_LEVEL: "info"
```

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `type` | string | Yes | - | Must be "localhost_single_container" |
| `version` | string | No | "3.8" | Docker version specification |
| `network_name` | string | No | "default_network" | Name for the container's network |
| `service_prefix` | string | No | None | Prefix for service names |
| `environment` | dict | No | {} | Environment variables for all services |

## Usage Example

```yaml
tests:
  - name: "Basic Localhost Test"
    network_environment:
      type: "localhost_single_container"
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
- Uses `EnvironmentManagerDockerMixin` for consistent Docker operations across all network environments
- Services communicate directly via localhost networking within a single container
- Suitable for rapid development iterations before moving to multi-container environments

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Port conflicts | Check for port conflicts with other running containers or processes and adjust port mappings |
| Inter-service communication | Ensure proper service name resolution by using the correct target service name |
| Resource constraints | Adjust Docker resource limits (`--memory`, `--cpus`) for the container |
| Empty FROM in Dockerfile | Ensure you are using the latest version with `EnvironmentManagerDockerMixin` integration |

For more detailed debugging, use environment variables to enable debug logs, inspect container logs with `docker logs`, or use `docker exec -it <container> /bin/bash` for manual inspection.
