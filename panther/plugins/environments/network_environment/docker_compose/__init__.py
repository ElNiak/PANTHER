"""Docker Compose network environment plugin.

Orchestrates multi-container test environments using Docker Compose.
Generates `docker-compose.yml` from experiment configuration,
manages container lifecycle, and provides inter-service networking.

Key features:
    - Automatic `docker-compose.yml` generation from YAML config
    - Custom Docker network creation with configurable subnets
    - Volume mounts for certificate sharing and output collection
    - Health-check integration for service readiness
    - Automatic cleanup on experiment completion or failure
"""

# NOTE: Imports removed to avoid circular import during plugin discovery
# The plugin is loaded dynamically via @register_plugin decorator

__all__ = ["DockerComposeEnvironment"]
