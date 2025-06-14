"""Mixin for common configuration parsing and validation."""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from omegaconf import DictConfig, OmegaConf


class ConfigurationProcessorMixin:
    """
    Mixin providing common configuration processing and validation functionality.

    This mixin eliminates duplicated configuration handling patterns across network environments.
    """

    def process_service_config(
        self,
        service_config: Dict[str, Any],
        required_fields: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Process and validate service configuration.

        Args:
            service_config: Raw service configuration
            required_fields: List of required configuration fields

        Returns:
            Processed configuration dictionary

        Raises:
            ValueError: If required fields are missing
        """
        processed = {}

        # Default required fields if not specified
        if required_fields is None:
            required_fields = ["implementation", "protocol"]

        # Validate required fields
        for field in required_fields:
            if field not in service_config:
                raise ValueError(
                    f"Missing required field '{field}' in service configuration"
                )

        # Process common fields
        processed["implementation"] = self._process_implementation_config(
            service_config.get("implementation", {})
        )
        processed["protocol"] = self._process_protocol_config(
            service_config.get("protocol", {})
        )

        # Process optional fields
        optional_fields = [
            "timeout",
            "ports",
            "generate_new_certificates",
            "network_config",
            "environment",
            "volumes",
            "command",
            "depends_on",
        ]

        for field in optional_fields:
            if field in service_config:
                processed[field] = service_config[field]

        # Process environment variables
        if "environment" in processed:
            processed["environment"] = self._process_environment_variables(
                processed["environment"]
            )

        return processed

    def _process_implementation_config(
        self, impl_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process implementation configuration."""
        required = ["name", "type"]
        for field in required:
            if field not in impl_config:
                raise ValueError(f"Missing required implementation field: {field}")

        return impl_config

    def _process_protocol_config(self, proto_config: Dict[str, Any]) -> Dict[str, Any]:
        """Process protocol configuration."""
        required = ["name", "role"]
        for field in required:
            if field not in proto_config:
                raise ValueError(f"Missing required protocol field: {field}")

        # Validate role
        valid_roles = ["client", "server", "peer"]
        if proto_config["role"] not in valid_roles:
            raise ValueError(
                f"Invalid protocol role '{proto_config['role']}'. "
                f"Must be one of: {valid_roles}"
            )

        return proto_config

    def _process_environment_variables(
        self, env_vars: Union[Dict[str, str], DictConfig]
    ) -> Dict[str, str]:
        """
        Process environment variables with variable substitution.

        Args:
            env_vars: Environment variables dictionary

        Returns:
            Processed environment variables
        """
        if isinstance(env_vars, DictConfig):
            env_vars = OmegaConf.to_container(env_vars)

        processed = {}

        # First pass: add all variables without substitution
        for key, value in env_vars.items():
            processed[key] = str(value)

        # Second pass: perform substitutions
        for key, value in processed.items():
            # Replace references to other variables
            for var_name, var_value in processed.items():
                if var_name != key:  # Don't self-reference
                    value = value.replace(f"${{{var_name}}}", var_value)
                    value = value.replace(f"${var_name}", var_value)

            processed[key] = value

        return processed

    def validate_network_config(
        self,
        config: Dict[str, Any],
        required_fields: Optional[List[str]] = None,
    ) -> bool:
        """
        Validate network environment configuration.

        Args:
            config: Network configuration to validate
            required_fields: List of required fields

        Returns:
            True if configuration is valid

        Raises:
            ValueError: If configuration is invalid
        """
        if required_fields is None:
            required_fields = ["type"]

        # Check required fields
        for field in required_fields:
            if field not in config:
                raise ValueError(f"Missing required network config field: {field}")

        # Validate network type
        valid_types = ["docker_compose", "localhost_single_container", "shadow_ns"]
        if config["type"] not in valid_types:
            raise ValueError(
                f"Invalid network type '{config['type']}'. "
                f"Must be one of: {valid_types}"
            )

        return True

    def merge_configurations(
        self,
        *configs: Dict[str, Any],
        deep: bool = True,
    ) -> Dict[str, Any]:
        """
        Merge multiple configuration dictionaries.

        Args:
            *configs: Configuration dictionaries to merge
            deep: Whether to perform deep merge

        Returns:
            Merged configuration
        """
        if not configs:
            return {}

        # Convert to OmegaConf for merging
        omega_configs = [OmegaConf.create(cfg) for cfg in configs]

        # Merge configurations
        merged = OmegaConf.merge(*omega_configs)

        # Convert back to dict
        return OmegaConf.to_container(merged)

    def expand_paths(
        self,
        config: Dict[str, Any],
        base_path: Optional[Path] = None,
    ) -> Dict[str, Any]:
        """
        Expand relative paths in configuration to absolute paths.

        Args:
            config: Configuration containing paths
            base_path: Base path for relative paths

        Returns:
            Configuration with expanded paths
        """
        if base_path is None:
            base_path = Path.cwd()

        expanded = config.copy()

        # Fields that typically contain paths
        path_fields = [
            "output_dir",
            "log_dir",
            "template_dir",
            "plugin_dir",
            "dockerfile_path",
            "config_path",
            "cert_dir",
        ]

        for field in path_fields:
            if field in expanded and isinstance(expanded[field], str):
                path = Path(expanded[field])
                if not path.is_absolute():
                    expanded[field] = str(base_path / path)

        return expanded

    def validate_paths(
        self,
        paths: Dict[str, str],
        required: Optional[List[str]] = None,
        create_missing: bool = False,
    ) -> bool:
        """
        Validate that required paths exist.

        Args:
            paths: Dictionary of path names to paths
            required: List of required path names
            create_missing: Whether to create missing directories

        Returns:
            True if all paths are valid

        Raises:
            ValueError: If required paths don't exist and create_missing is False
        """
        if required is None:
            required = list(paths.keys())

        for name in required:
            if name not in paths:
                raise ValueError(f"Missing required path: {name}")

            path = Path(paths[name])

            if not path.exists():
                if create_missing and name.endswith("_dir"):
                    # Create directories
                    path.mkdir(parents=True, exist_ok=True)
                    self.logger.debug(f"Created directory: {path}")
                else:
                    raise ValueError(f"Path does not exist: {name}={path}")

        return True

    def generate_service_environment(
        self,
        service_name: str,
        service_config: Dict[str, Any],
        global_env: Optional[Dict[str, str]] = None,
    ) -> Dict[str, str]:
        """
        Generate environment variables for a service.

        Args:
            service_name: Name of the service
            service_config: Service configuration
            global_env: Global environment variables

        Returns:
            Complete environment variables for the service
        """
        env = {}

        # Add global environment variables
        if global_env:
            env.update(global_env)

        # Add service-specific environment
        if "environment" in service_config:
            env.update(service_config["environment"])

        # Add standard variables
        env["SERVICE_NAME"] = service_name
        env["SERVICE_TYPE"] = service_config.get("implementation", {}).get(
            "type", "unknown"
        )

        # Process variable substitutions
        return self._process_environment_variables(env)
