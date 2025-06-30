# Docker Compose Environment

The Docker Compose Environment plugin provides containerized network environments for testing protocol implementations in isolated, reproducible settings. This plugin leverages Docker Compose to create multi-container Docker applications, enabling complex network topologies and controlled testing environments.

!!! info "Plugin Information"
    **Plugin Type**: Network Environment
    **Source Location**: `plugins/environments/network_environment/docker_compose/`

!!! warning "System Requirements"
    This plugin requires Docker Engine (27.03.0+) and Docker Compose (v1.27.0+) to be installed and accessible. Ensure your user has proper Docker permissions.

<!-- src: /panther/plugins/environments/network_environment/docker_compose/docker_compose.py -->

This network environment plugin is essential for:

- Isolating test environments from the host system
- Creating reproducible network configurations
- Enabling automated testing across multiple containers
- Supporting complex service configurations with defined networking

### Docker Build Workflow

The Docker Compose environment implements a streamlined Docker build process:

1. **Service Image Building**: Builds individual service images from their respective Dockerfiles
2. **Docker Compose Orchestration**: Generates docker-compose.yml with proper service definitions
3. **Network Configuration**: Sets up isolated networks for service communication
4. **Volume Management**: Handles shared volumes for logs, certificates, and synchronization

The environment leverages the service-specific Docker operations through service managers while maintaining its own orchestration logic.

## Requirements and Dependencies

The plugin requires:

- **Docker Engine**: Version 19.03.0 or later
- **Docker Compose**: Version 1.27.0 or later (V1 or V2 compatible)
- **Python Dependencies**:
  - subprocess
  - jinja2 (for template rendering)

The plugin also integrates with:

- PANTHER event management system
- Service plugins (for deploying containerized services)

## Configuration Options

The Docker Compose environment accepts the following configuration parameters:

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

<!-- src: /panther/plugins/environments/network_environment/docker_compose/config_schema.py -->

## Usage Examples

### Basic Configuration

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

### Advanced Configuration with Custom Volumes and Environment

```yaml
tests:
  - name: "Advanced Network Test"
    network_environment:
      type: "docker_compose"
      network_name: "secure_network"
      service_prefix: "secure_"
      volumes:
        - "./certs:/etc/certs:ro"
        - "./data:/app/data"
      environment:
        DEBUG: "true"
        TLS_ENABLED: "true"
    services:
      server:
        name: "quic_server"
        implementation:
          name: "picoquic"
          type: "iut"
      client:
        name: "quic_client"
        implementation:
          name: "picoquic"
          type: "tester"
```

## Extension Points

The Docker Compose environment plugin can be extended in several ways:

### Custom Network Configurations

You can extend the Docker Compose environment to support more complex network configurations:

```python
from panther.plugins.environments.network_environment.docker_compose.docker_compose import DockerComposeEnvironment

class CustomNetworkEnvironment(DockerComposeEnvironment):
    """Custom network environment with advanced features."""

    def setup(self):
        """Custom setup with additional network configuration."""
        super().setup()
        # Add custom network configuration

    def get_network_info(self):
        """Return enhanced network information."""
        base_info = super().get_network_info()
        # Add custom network metrics
        return base_info
```

### Integration with Custom Monitoring

The plugin can be extended to integrate with network monitoring tools:

```python
def apply_network_conditions(self, conditions):
    """Apply custom network conditions like latency or packet loss."""
    # Implementation using tc or other network simulation tools
    pass
```

## Testing and Verification

To test the Docker Compose environment plugin:

1. **Unit Tests**: Located in `/panther/plugins/environments/network_environment/docker_compose/tests/`
2. **Integration Tests**: Run the following test to verify Docker Compose setup:

```bash
python -m pytest tests/integration/test_docker_compose_environment.py
```

3. **Manual Verification**:
   - Run an experiment with the Docker Compose environment
   - Verify Docker networks and containers are created correctly
   - Check that services can communicate properly

## Troubleshooting

### Common Issues and Solutions

| Issue | Solution |
|-------|----------|
| Docker network conflicts | Ensure unique network names or use service_prefix |
| Permission issues | Run with appropriate Docker permissions or use sudo |
| Container communication failures | Check Docker network settings and service configurations |
| Timeouts during container startup | Increase service timeout values in configuration |

### Debugging

For more detailed debugging information:

```yaml
logging:
  level: DEBUG
  format: "%(asctime)s [%(levelname)s] - %(module)s - %(message)s"
```

Use `docker compose logs` to view container logs for additional troubleshooting.
