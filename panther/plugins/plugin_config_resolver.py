"""
Plugin Configuration Resolution Module

This module handles dynamic configuration class loading and resolution
for different plugin types in the PANTHER framework.
"""

import importlib
from typing import Any

from panther.core.utils.logging_mixin import LoggerMixin


class PluginConfigResolver(LoggerMixin):
    """
    Handles dynamic configuration class loading and type resolution.

    This class provides utilities for dynamically discovering and instantiating
    configuration classes based on plugin names and types.
    """

    @staticmethod
    def get_class_name(plugin_name: str, suffix: str = "Config") -> str:
        """
        Convert plugin name to class name format.

        Args:
            plugin_name: The plugin name (e.g., 'gperf_cpu')
            suffix: Class name suffix (default: 'Config')

        Returns:
            Formatted class name (e.g., 'GperfCpuConfig')
        """
        class_name_parts = plugin_name.split("_")
        class_name_parts = [part.capitalize() for part in class_name_parts]
        class_name = "".join(class_name_parts) + suffix
        return class_name

    def create_execution_environment_config(self, environment_type: str) -> Any:
        """
        Create the appropriate configuration object for execution environment type.

        This method dynamically discovers and instantiates the config class for the
        given environment type by following the standard naming convention and
        module structure.

        Args:
            environment_type: Type of execution environment (e.g., 'strace',
                'gperf_cpu')

        Returns:
            Appropriate configuration object for the environment type
        """
        try:
            # Dynamically construct the module path and config class name
            module_path = (
                f"panther.plugins.environments.execution_environment."
                f"{environment_type}.config_schema"
            )
            config_class_name = self.get_class_name(environment_type, suffix="Config")

            # Try to import the specific config module and class
            try:
                config_module = importlib.import_module(module_path)
                config_class = getattr(config_module, config_class_name)

                self.logger.debug(
                    "Successfully loaded config class '%s' for environment type '%s'",
                    config_class_name,
                    environment_type,
                )

                # Instantiate the config with the environment type
                return config_class(type=environment_type)

            except (ImportError, AttributeError) as e:
                self.logger.debug(
                    "Failed to load specific config for environment type '%s': %s. "
                    "Using fallback.",
                    environment_type,
                    e,
                )
                # Fall through to generic config fallback

        except Exception as e:  # pylint: disable=broad-exception-caught
            self.logger.warning(
                "Unexpected error creating config for environment type '%s': %s",
                environment_type,
                e,
            )

        # Fallback to generic config for any failure case
        from panther.plugins.environments.config_schema import (
            EnvironmentConfig,
        )  # pylint: disable=import-outside-toplevel

        self.logger.debug(
            "Using generic EnvironmentConfig for environment type '%s'",
            environment_type,
        )
        return EnvironmentConfig(type=environment_type)

    def resolve_config_class(self, module_path: str, class_name: str) -> type | None:
        """
        Resolve and return a configuration class from module path and class name.

        Args:
            module_path: Full module path (e.g.,
                'panther.plugins.services.iut.quic.config_schema')
            class_name: Class name to load

        Returns:
            The resolved class or None if not found
        """
        try:
            config_module = importlib.import_module(module_path)
            config_class = getattr(config_module, class_name)

            self.logger.debug(
                "Successfully resolved config class '%s' from module '%s'",
                class_name,
                module_path,
            )
            return config_class

        except (ImportError, AttributeError) as e:
            self.logger.debug(
                "Failed to resolve config class '%s' from module '%s': %s",
                class_name,
                module_path,
                e,
            )
            return None

    def create_service_config(self, service_type: str, service_name: str) -> Any:
        """
        Create configuration object for a service.

        Args:
            service_type: Type of service ('iut', 'tester', etc.)
            service_name: Name of the specific service

        Returns:
            Service configuration object or None if not found
        """
        try:
            # Construct module path based on service type and name
            module_path = f"panther.plugins.services.{service_type}.{service_name}.config_schema"
            config_class_name = self.get_class_name(service_name, suffix="Config")

            config_class = self.resolve_config_class(module_path, config_class_name)

            if config_class:
                return config_class()
            else:
                self.logger.warning(
                    "Could not create config for service type '%s', service '%s'",
                    service_type,
                    service_name,
                )
                return None

        except Exception as e:  # pylint: disable=broad-exception-caught
            self.logger.error(
                "Error creating service config for '%s/%s': %s",
                service_type,
                service_name,
                e,
            )
            return None

    def validate_config_class(self, config_class: type, expected_attributes: list[str]) -> bool:
        """
        Validate that a configuration class has expected attributes.

        Args:
            config_class: The configuration class to validate
            expected_attributes: List of expected attribute names

        Returns:
            True if all expected attributes exist, False otherwise
        """
        try:
            for attr in expected_attributes:
                if not hasattr(config_class, attr):
                    self.logger.warning(
                        "Configuration class '%s' missing expected attribute '%s'",
                        config_class.__name__,
                        attr,
                    )
                    return False
            return True

        except Exception as e:  # pylint: disable=broad-exception-caught
            self.logger.error("Error validating config class: %s", e)
            return False
