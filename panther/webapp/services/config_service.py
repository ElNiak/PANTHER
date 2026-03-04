"""Service layer for configuration validation and YAML generation."""

import logging
from typing import Optional

import yaml

logger = logging.getLogger(__name__)

DEFAULT_CONFIG_YAML = """\
# PANTHER Experiment Configuration
# See: panther config validate --config <file> to validate

logging:
  level: INFO

docker:
  force_build_docker_image: true

tests:
  - name: "Example Test"
    network_environment:
      type: docker_compose
    services:
      server:
        implementation:
          name: picoquic
          type: iut
        protocol:
          name: quic
          version: rfc9000
          role: server
      client:
        implementation:
          name: picoquic
          type: iut
        protocol:
          name: quic
          version: rfc9000
          role: client
"""


class ConfigService:
    """Service for config validation, YAML generation, and form model adaptation."""

    def get_default_yaml(self) -> str:
        """Return a default experiment config YAML template."""
        return DEFAULT_CONFIG_YAML

    def validate_yaml(self, yaml_content: str) -> Optional[str]:
        """Validate a YAML string as a PANTHER config.

        Returns None if valid, or an error message string.
        """
        # Step 1: YAML syntax check
        try:
            data = yaml.safe_load(yaml_content)
        except yaml.YAMLError as e:
            return f"YAML syntax error: {e}"

        if not isinstance(data, dict):
            return "Config must be a YAML mapping (dict)"

        # Step 2: Basic structural validation
        # Full Pydantic validation can be added here via config models
        try:
            from panther.config.core.models import GlobalConfig

            global_section = data.get("logging") or data.get("global", {})
            if isinstance(global_section, dict) and "level" in global_section:
                # Quick check that log level is valid
                GlobalConfig(logging=global_section)
        except Exception as e:
            return f"Config validation error: {e}"

        if "tests" not in data:
            return "Config must contain a 'tests' section"

        if not isinstance(data["tests"], list) or len(data["tests"]) == 0:
            return "'tests' must be a non-empty list"

        return None

    def yaml_to_dict(self, yaml_content: str) -> Optional[dict]:
        """Parse YAML content to a dict. Returns None on error."""
        try:
            return yaml.safe_load(yaml_content)
        except yaml.YAMLError:
            return None

    def dict_to_yaml(self, data: dict) -> str:
        """Convert a dict to YAML string."""
        return yaml.dump(data, default_flow_style=False, sort_keys=False)
