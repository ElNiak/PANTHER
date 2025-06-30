"""PANTHER docker_compose network environment plugin.

This package contains the Docker Compose network environment plugin.
"""

# NOTE: Imports removed to avoid circular import during plugin discovery
# The plugin is loaded dynamically via @register_plugin decorator

__all__ = ["DockerComposeEnvironment"]
