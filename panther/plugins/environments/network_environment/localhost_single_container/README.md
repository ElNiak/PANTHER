# Localhost Single Container Environment

!!! info "Lightweight Testing Environment"
    This plugin provides a simple, single-container environment for rapid protocol testing and development. All services run on localhost within one Docker container for minimal complexity.

> **Plugin Type**: Network Environment

> **Verified Source Location**: `plugins/environments/network_environment/localhost_single_container/`

## Purpose and Overview

The Localhost Single Container Environment plugin provides a lightweight containerized testing environment where all services run in a single Docker container on localhost. This environment is ideal for simple protocol testing with minimal network complexity, offering quick setup and execution for development and initial verification of protocol implementations.

<!-- src: /panther/plugins/environments/network_environment/localhost_single_container/localhost_single_container.py -->

This network environment plugin is particularly useful for:

!!! tip "Ideal Use Cases"
    Perfect for rapid development iterations, debugging protocol implementations, and initial validation before moving to more complex multi-container or simulated network environments.

- Rapid development iterations and testing of protocol implementations
- Testing client-server interactions in a controlled, local environment
- Simplified debugging with direct access to all services in one container
- Reducing resource consumption compared to multi-container environments

The Localhost Single Container environment allows services to communicate directly via localhost networking within a single container, while still maintaining isolation from the host system.

## Requirements and Dependencies

The plugin requires:

- **Docker Engine**: Version 19.03.0 or later
- **Python Dependencies**:
  - subprocess (standard library)
  - pathlib (standard library)

The plugin also integrates with:

- PANTHER event management system
- Service plugins that can operate in a containerized environment

## Configuration Options

The Localhost Single Container environment accepts the following configuration parameters:

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

<!-- src: /panther/plugins/environments/network_environment/localhost_single_container/config_schema.py -->

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `type` | string | Yes | - | Must be "localhost_single_container" |
| `version` | string | No | "3.8" | Docker version specification |
| `network_name` | string | No | "default_network" | Name for the container's network |
| `service_prefix` | string | No | None | Prefix for service names |
| `environment` | dict | No | {} | Environment variables for all services |

## Usage Examples

### Basic Configuration

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

### Advanced Configuration with Environment Variables

```yaml
tests:
  - name: "Advanced Localhost Test"
    network_environment:
      type: "localhost_single_container"
      service_prefix: "debug_"
      environment:
        DEBUG: "true"
        LOG_LEVEL: "debug"
        TRACE_PACKETS: "1"
    services:
      server:
        name: "quic_server"
        implementation:
          name: "picoquic"
          type: "iut"
        ports:
          - "4443:4443"
      client:
        name: "quic_client"
        implementation:
          name: "picoquic"
          type: "iut"
        protocol:
          target: "quic_server"
```

## Extension Points

The Localhost Single Container environment plugin can be extended in several ways:

### Custom Container Setup

You can extend the plugin to customize the container environment:

```python
from panther.plugins.environments.network_environment.localhost_single_container.localhost_single_container import LocalhostSingleContainerEnvironment

class EnhancedLocalhostEnvironment(LocalhostSingleContainerEnvironment):
    """Enhanced localhost environment with additional features."""

    def prepare_environment(self):
        """Custom setup with additional container configuration."""
        super().prepare_environment()
        # Add custom setup code

    def generate_environment_services(self, paths, timestamp):
        """Generate enhanced service configuration."""
        base_config = super().generate_environment_services(paths, timestamp)
        # Modify the configuration with custom settings
        return modified_config
```

### Network Instrumentation

Add network monitoring capabilities:

```python
def add_network_monitoring(self):
    """Add network monitoring tools to the container."""
    # Implementation using tcpdump, iftop, or other monitoring tools
    self.additional_packages.extend(["tcpdump", "iftop", "net-tools"])
```

## Testing and Verification

To test the Localhost Single Container environment plugin:

1. **Unit Tests**: Located in `/tests/unit/plugins/environments/network_environment/localhost_single_container/`
2. **Integration Tests**: Run the example configuration to verify proper operation:

   ```bash
   python -m panther -c experiment-config/experiment_config_localhost.yaml
   ```

3. **Verification Metrics**:
   - Verify all services start correctly in the container
   - Check inter-service communication via localhost networking
   - Test port exposure and access from the host system

## Troubleshooting

### Common Issues

#### Port Conflicts

**Problem**: Services fail to start due to port binding issues
**Solution**: Check for port conflicts with other running containers or processes and adjust port mappings in the configuration.

```yaml
services:
  my_service:
    ports:
      - "8081:8080"  # Map container port 8080 to host port 8081 instead
```

#### Inter-Service Communication Issues

**Problem**: Services can't communicate with each other
**Solution**: Ensure proper service name resolution by using the correct target service name:

```yaml
services:
  client:
    protocol:
      target: "server_name"  # Use the correct service name here
```

#### Resource Constraints

**Problem**: Container crashes or becomes unresponsive due to resource limits
**Solution**: Adjust Docker resource limits for the container:

```bash
docker run --memory=4g --cpus=2 [container_name]
```

### Debugging Tips

1. Use environment variables to enable debug logs in your services
2. Inspect container logs using `docker logs [container_name]`
3. Use `docker exec -it [container_name] /bin/bash` to access a shell in the running container for manual debugging
4. Check the generated Dockerfile and run script in the output directory for potential issues
