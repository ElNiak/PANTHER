"""
Environment Factory Module

This module handles environment manager creation for both network
and execution environments in the PANTHER framework.
"""

from pathlib import Path
from typing import Any

from panther.config.config_experiment_schema import TestConfig
from panther.core.observer.management.event_manager import EventManager
from panther.core.utils.logging_mixin import LoggerMixin
from panther.plugins.environments.environment_interface import IEnvironmentPlugin
from panther.plugins.environments.execution_environment.execution_environment_interface import (  # noqa: E501
    IExecutionEnvironment,
)
from panther.plugins.environments.network_environment.network_environment_interface import (  # noqa: E501
    INetworkEnvironment,
)
from panther.plugins.plugin_config_resolver import PluginConfigResolver
from panther.plugins.plugin_discovery import PluginDiscovery
from panther.plugins.plugin_manifest import PluginRegistration, PluginType


class EnvironmentFactory(LoggerMixin):
    """
    Handles environment manager creation for both network and execution environments.

    This class provides functionality for:
    - Environment manager instantiation
    - Environment configuration and setup
    - Environment-specific logic and validation
    - Environment manager class loading
    """

    def __init__(
        self,
        config_resolver: PluginConfigResolver,
        plugin_discovery: PluginDiscovery,
        event_manager: EventManager | None = None,
        plugin_event_emitter=None,
    ):
        """
        Initialize the environment factory.

        Args:
            config_resolver: Configuration resolver instance
            plugin_discovery: Plugin discovery instance
            event_manager: Event manager for plugin events
            plugin_event_emitter: Plugin event emitter instance
        """
        super().__init__()

        self.config_resolver = config_resolver
        self.plugin_discovery = plugin_discovery
        self.event_manager = event_manager
        self.plugin_event_emitter = plugin_event_emitter

        # Plugin registrations
        self.registrations: dict[str, PluginRegistration] = {}

    def create_environment_manager(
        self,
        environment: str,
        test_config: TestConfig,
        environment_dir: Path,
        output_dir: Path,
        event_manager: EventManager,
    ) -> IEnvironmentPlugin:
        """
        Create an environment manager instance using the catalog-based approach.

        Args:
            environment: Environment name
            test_config: Test configuration
            environment_dir: Directory containing environment files
            output_dir: Output directory for environment data
            event_manager: Event manager instance

        Returns:
            Environment manager instance
        """
        self.logger.debug("Creating environment manager for %s", environment)

        # Check catalog for this environment
        plugin_id = f"{PluginType.ENVIRONMENT.value}:{environment}"
        manifest = self.plugin_discovery.plugin_catalog.catalog.get(plugin_id)

        try:
            # Determine environment type and subtype
            env_type = None
            env_sub_type = environment

            # Try to infer from manifest or directory structure
            if manifest:
                # Use manifest information
                if "network" in manifest.tags or "network" in manifest.capabilities:
                    env_type = "network_environment"
                elif "execution" in manifest.tags or "execution" in manifest.capabilities:
                    env_type = "execution_environment"
            else:
                # Default to network environment
                env_type = "network_environment"

            # Determine file path
            if manifest and manifest.file_path:
                env_file_path = Path(manifest.file_path) / f"{env_sub_type}.py"
            else:
                env_file_path = environment_dir / f"{env_sub_type}.py"

            self.logger.debug("Loading environment module from %s", env_file_path)

            # Use PluginManagerUtils to load the plugin class
            from panther.plugins.plugin_loader_utils import (
                PluginManagerUtils,
            )  # pylint: disable=import-outside-toplevel

            env_manager_class = PluginManagerUtils.load_plugin_class(
                plugin_path=env_file_path,
                class_suffix="Environment",
                name_transform=lambda name: self.config_resolver.get_class_name(name, suffix=""),
            )

            # Extract environment configuration
            from panther.plugins.environments.config_schema import (
                EnvironmentConfig,
            )  # pylint: disable=import-outside-toplevel

            env_config = getattr(test_config, env_type, {})
            if isinstance(env_config, dict):
                env_config_to_test = EnvironmentConfig(**env_config)
            else:
                env_config_to_test = env_config

            # Create instance
            env_manager = env_manager_class(  # type: ignore[misc]
                env_config_to_test=env_config_to_test,
                output_dir=str(output_dir),
                env_type=env_type,
                env_sub_type=env_sub_type,
                event_manager=event_manager,
            )

            # Register if we have a manifest
            if manifest:
                registration = PluginRegistration(
                    manifest=manifest,
                    instance=env_manager,
                    loaded=True,
                    active=True,
                )
                self.registrations[plugin_id] = registration

            # Emit plugin loaded event if we have event system
            if self.plugin_event_emitter:
                self.plugin_event_emitter.emit_plugin_loading_completed(
                    plugin_id=plugin_id,
                    plugin_name=environment,
                    plugin_type=PluginType.ENVIRONMENT.value,
                    # Note: details parameter not supported, omitting for now
                )

            self.logger.info("Successfully created environment manager for %s", environment)
            return env_manager

        except Exception as e:
            # Emit plugin loading failed event
            if self.plugin_event_emitter:
                self.plugin_event_emitter.emit_plugin_loading_failed(
                    plugin_id=plugin_id,
                    plugin_name=environment,
                    plugin_type=PluginType.ENVIRONMENT.value,
                    error_message=str(e),
                    error_details={
                        "environment_dir": str(environment_dir),
                        "exception_type": type(e).__name__,
                    },
                )

            self.logger.error("Failed to create environment manager for %s: %s", environment, e)
            raise

    def get_network_environment_plugin(self, environment_type: str) -> INetworkEnvironment | None:
        """
        Get a network environment plugin instance.

        Args:
            environment_type: Type of network environment

        Returns:
            Network environment plugin instance or None
        """
        try:
            # Check if plugin is available
            plugin_id = f"environment:{environment_type}"

            if not self.plugin_discovery.is_plugin_available(plugin_id):
                self.logger.warning(
                    "Network environment plugin not available: %s", environment_type
                )
                return None

            # Get manifest
            manifest = self.plugin_discovery.get_plugin_manifest(environment_type)

            if not manifest:
                self.logger.warning(
                    "No manifest found for network environment: %s", environment_type
                )
                return None

            # Load and instantiate the plugin
            from panther.plugins.plugin_loader_utils import (
                PluginManagerUtils,
            )  # pylint: disable=import-outside-toplevel

            plugin_file_path = Path(manifest.file_path) / f"{environment_type}.py"

            env_class = PluginManagerUtils.load_plugin_class(
                plugin_path=plugin_file_path,
                class_suffix="Environment",
                name_transform=lambda name: self.config_resolver.get_class_name(name, suffix=""),
            )

            # Create configuration
            env_config = self.config_resolver.create_execution_environment_config(environment_type)

            # Create instance
            env_instance = env_class(
                env_config_to_test=env_config,
                output_dir="",  # Will be set when used
                env_type="network_environment",
                env_sub_type=environment_type,
                event_manager=self.event_manager,
            )

            return env_instance

        except Exception as e:  # pylint: disable=broad-exception-caught
            self.logger.error(
                "Error getting network environment plugin %s: %s", environment_type, e
            )
            return None

    def get_execution_environment_plugin(
        self, environment_type: str, output_dir: str, event_manager: EventManager
    ) -> IExecutionEnvironment | None:
        """
        Get an execution environment plugin instance.

        Args:
            environment_type: Type of execution environment
            output_dir: Output directory for environment data
            event_manager: Event manager instance

        Returns:
            Execution environment plugin instance or None
        """
        try:
            # Check if plugin is available
            plugin_id = f"environment:{environment_type}"

            if not self.plugin_discovery.is_plugin_available(plugin_id):
                self.logger.warning(
                    "Execution environment plugin not available: %s", environment_type
                )
                return None

            # Get manifest
            manifest = self.plugin_discovery.get_plugin_manifest(environment_type)

            if not manifest:
                self.logger.warning(
                    "No manifest found for execution environment: %s", environment_type
                )
                return None

            # Load and instantiate the plugin
            from panther.plugins.plugin_loader_utils import (
                PluginManagerUtils,
            )  # pylint: disable=import-outside-toplevel

            plugin_file_path = Path(manifest.file_path) / f"{environment_type}.py"

            env_class = PluginManagerUtils.load_plugin_class(
                plugin_path=plugin_file_path,
                class_suffix="",
                name_transform=lambda name: self.config_resolver.get_class_name(name, suffix=""),
            )

            # Create configuration
            env_config = self.config_resolver.create_execution_environment_config(environment_type)

            # Create instance
            env_instance = env_class(
                env_config_to_test=env_config,
                output_dir=output_dir,
                env_type="execution_environment",
                env_sub_type=environment_type,
                event_manager=event_manager,
            )

            return env_instance

        except Exception as e:  # pylint: disable=broad-exception-caught
            self.logger.error(
                "Error getting execution environment plugin %s: %s", environment_type, e
            )
            return None

    def validate_environment_requirements(self, env_config: Any) -> bool:
        """
        Validate that environment requirements are met.

        Args:
            env_config: Environment configuration to validate

        Returns:
            True if requirements are satisfied, False otherwise
        """
        try:
            # Check if environment type is available
            if hasattr(env_config, "type") and env_config.type:
                plugin_id = f"environment:{env_config.type}"

                if not self.plugin_discovery.is_plugin_available(plugin_id):
                    self.logger.warning("Environment type not available: %s", env_config.type)
                    return False

                # Validate dependencies
                dependencies_ok, missing_deps = self.plugin_discovery.validate_plugin_dependencies(
                    env_config.type
                )
                if not dependencies_ok:
                    self.logger.warning(
                        "Missing dependencies for environment %s: %s",
                        env_config.type,
                        missing_deps,
                    )
                    return False

            return True

        except Exception as e:  # pylint: disable=broad-exception-caught
            self.logger.error("Error validating environment requirements: %s", e)
            return False

    def get_available_network_environments(self) -> list[str]:
        """
        Get all available network environment types.

        Returns:
            List of available network environment names
        """
        try:
            environments = []
            all_plugins = self.plugin_discovery.list_available_plugins()

            # Look for network environment plugins
            for plugin_type, plugin_names in all_plugins.items():
                if "network" in plugin_type.lower() and "environment" in plugin_type.lower():
                    environments.extend(plugin_names)

            self.logger.debug("Found %d network environments", len(environments))
            return environments

        except Exception as e:  # pylint: disable=broad-exception-caught
            self.logger.error("Error getting available network environments: %s", e)
            return []

    def get_available_execution_environments(self) -> list[str]:
        """
        Get all available execution environment types.

        Returns:
            List of available execution environment names
        """
        try:
            environments = []
            all_plugins = self.plugin_discovery.list_available_plugins()

            # Look for execution environment plugins
            for plugin_type, plugin_names in all_plugins.items():
                if "execution" in plugin_type.lower() and "environment" in plugin_type.lower():
                    environments.extend(plugin_names)

            self.logger.debug("Found %d execution environments", len(environments))
            return environments

        except Exception as e:  # pylint: disable=broad-exception-caught
            self.logger.error("Error getting available execution environments: %s", e)
            return []

    def create_environment_config(self, env_type: str, env_name: str) -> Any:
        """
        Create configuration object for an environment.

        Args:
            env_type: Type of environment ('network', 'execution')
            env_name: Name of the specific environment

        Returns:
            Environment configuration object or None if not found
        """
        try:
            if env_type == "execution":
                return self.config_resolver.create_execution_environment_config(env_name)
            else:
                # For network environments, create generic config
                from panther.plugins.environments.config_schema import (
                    EnvironmentConfig,
                )  # pylint: disable=import-outside-toplevel

                return EnvironmentConfig(type=env_name)

        except Exception as e:  # pylint: disable=broad-exception-caught
            self.logger.error(
                "Error creating environment config for %s/%s: %s", env_type, env_name, e
            )
            return None

    def get_environment_info(self, environment_name: str) -> dict[str, Any] | None:
        """
        Get information about a specific environment.

        Args:
            environment_name: Name of the environment

        Returns:
            Environment information dictionary or None if not found
        """
        try:
            manifest = self.plugin_discovery.get_plugin_manifest(environment_name)

            if manifest is None:
                return None

            # Build environment info from manifest
            env_info = {
                "name": manifest.name,
                "type": (manifest.plugin_type.value if manifest.plugin_type else "unknown"),
                "version": getattr(manifest, "version", "unknown"),
                "description": getattr(manifest, "description", ""),
                "capabilities": getattr(manifest, "capabilities", []),
                "dependencies": getattr(manifest, "dependencies", []),
                "tags": getattr(manifest, "tags", []),
            }

            return env_info

        except Exception as e:  # pylint: disable=broad-exception-caught
            self.logger.error("Error getting environment info for %s: %s", environment_name, e)
            return None
