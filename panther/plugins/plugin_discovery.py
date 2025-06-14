"""
Plugin Discovery Module

This module handles plugin catalog management, registration, validation,
and discovery operations for the PANTHER framework.
"""

from pathlib import Path
from typing import Any

from panther.core.utils.logging_mixin import LoggerMixin
from panther.plugins.plugin_catalog import PluginCatalog
from panther.plugins.plugin_manifest import PluginRegistration


class PluginDiscovery(LoggerMixin):
    """
    Handles plugin discovery, catalog management, and registration.

    This class provides functionality for:
    - Plugin catalog management
    - Plugin registration and validation
    - Directory scanning and plugin discovery
    """

    def __init__(self, plugin_directories: list[str] | None = None):
        """
        Initialize the plugin discovery system.

        Args:
            plugin_directories: Directories to scan for plugins
        """
        super().__init__()

        # Plugin catalog for discovery and validation
        self.plugin_directories = plugin_directories or []
        self.plugin_catalog = PluginCatalog(self.plugin_directories)

        # Plugin registrations and dockerfiles tracking
        self.registrations: dict[str, PluginRegistration] = {}
        self.dockerfiles: dict[str, Path] = {}

        # Automatically discover plugins on initialization
        self._discover_plugins()

    def _discover_plugins(self):
        """Discover available plugins using the catalog."""
        # Add default plugin directories if not specified
        if not self.plugin_directories:
            base_path = Path(__file__).parent
            self.plugin_directories = [
                str(base_path / "services"),
                str(base_path / "environments"),
                str(base_path / "protocols"),
            ]
            # Update the catalog with the directories
            self.plugin_catalog = PluginCatalog(self.plugin_directories)

        # Scan for plugins
        plugins = self.plugin_catalog.scan_plugins(use_cache=False)

        # Register Dockerfiles from discovered plugins
        for plugin_id, manifest in plugins.items():  # pylint: disable=unused-variable
            plugin_path = Path(manifest.file_path) if manifest.file_path else None
            if plugin_path:
                dockerfile_path = plugin_path / "Dockerfile"
                if dockerfile_path.exists():
                    self.dockerfiles[manifest.name] = dockerfile_path
                    self.logger.debug(
                        "Registered Dockerfile for plugin '%s' at '%s'",
                        manifest.name,
                        dockerfile_path,
                    )

        self.logger.info("Discovered %d plugins", len(self.plugin_catalog.catalog))

    def validate_experiment_plugins(self, experiment_config: Any) -> tuple[bool, list[str]]:
        """
        Validate that all plugins required by an experiment are available.

        Args:
            experiment_config: Experiment configuration

        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []
        required_plugins = set()

        # Extract required plugins from experiment config
        for test in experiment_config.tests:
            # Check network environment
            if hasattr(test, "network_environment"):
                env_type = test.network_environment.get("type")
                if env_type:
                    required_plugins.add(f"environment:{env_type}")

            # Check execution environments
            if hasattr(test, "execution_environment") and test.execution_environment:
                for exec_env in test.execution_environment:
                    if hasattr(exec_env, "type"):
                        required_plugins.add(f"environment:{exec_env.type}")

            # Check services
            if hasattr(test, "services"):
                for (
                    service_name,
                    service_config,
                ) in test.services.items():  # pylint: disable=unused-variable
                    if hasattr(service_config, "implementation"):
                        impl = service_config.implementation
                        # Convert service type to plugin type format
                        if impl.type.lower() == "testers":
                            plugin_type = "tester"
                        elif impl.type.lower() == "iut":
                            plugin_type = "iut"
                        else:
                            plugin_type = impl.type.lower()
                        required_plugins.add(f"{plugin_type}:{impl.name}")

        # Validate each required plugin
        for plugin_id in required_plugins:
            if not self.is_plugin_available(plugin_id):
                errors.append(f"Required plugin not available: {plugin_id}")

        return len(errors) == 0, errors

    def get_plugin_info(self, plugin_id: str) -> dict[str, Any] | None:
        """
        Get information about a specific plugin.

        Args:
            plugin_id: The plugin identifier

        Returns:
            Plugin information dictionary or None if not found
        """
        return self.plugin_catalog.get_plugin_info(plugin_id)

    def list_available_plugins(self) -> dict[str, list[str]]:
        """
        Get a list of all available plugins organized by type.

        Returns:
            Dictionary mapping plugin types to lists of plugin names
        """
        try:
            all_plugins = self.plugin_catalog.catalog

            # Organize plugins by type
            plugins_by_type = {}
            for (
                plugin_id,
                manifest,
            ) in all_plugins.items():  # pylint: disable=unused-variable
                # Handle different attribute access patterns
                if hasattr(manifest, "plugin_type") and manifest.plugin_type:
                    plugin_type = (
                        manifest.plugin_type.value
                        if hasattr(manifest.plugin_type, "value")
                        else str(manifest.plugin_type)
                    )
                elif hasattr(manifest, "type"):
                    plugin_type = manifest.type
                else:
                    plugin_type = "unknown"

                if plugin_type not in plugins_by_type:
                    plugins_by_type[plugin_type] = []
                plugins_by_type[plugin_type].append(manifest.name)

            return plugins_by_type

        except Exception as e:  # pylint: disable=broad-exception-caught
            self.logger.error("Error listing available plugins: %s", e)
            return {}

    def get_plugin_status(self, plugin_id: str) -> dict[str, Any]:
        """
        Get the current status of a plugin.

        Args:
            plugin_id: The plugin identifier

        Returns:
            Plugin status information
        """
        try:
            plugin_info = self.get_plugin_info(plugin_id)

            if plugin_info is None:
                return {
                    "status": "not_found",
                    "available": False,
                    "message": f"Plugin {plugin_id} not found",
                }

            # Check if plugin is properly registered
            is_registered = plugin_id in self.registrations

            return {
                "status": "available" if is_registered else "discovered",
                "available": True,
                "registered": is_registered,
                "info": plugin_info,
            }

        except Exception as e:  # pylint: disable=broad-exception-caught
            self.logger.error("Error getting plugin status for %s: %s", plugin_id, e)
            return {
                "status": "error",
                "available": False,
                "message": f"Error getting status: {str(e)}",
            }

    def is_plugin_available(self, plugin_id: str) -> bool:
        """
        Check if a plugin is available.

        Args:
            plugin_id: The plugin identifier

        Returns:
            True if plugin is available, False otherwise
        """
        return plugin_id in self.plugin_catalog.catalog

    def refresh_catalog(self):
        """
        Refresh the plugin catalog by re-scanning directories.
        """
        try:
            self.logger.info("Refreshing plugin catalog")
            self.plugin_catalog.refresh()
            self._discover_plugins()
            self.logger.info("Plugin catalog refreshed successfully")

        except Exception as e:  # pylint: disable=broad-exception-caught
            self.logger.error("Error refreshing plugin catalog: %s", e)

    def get_implementations_for_protocol(self, protocol: str) -> list[str]:
        """
        Get all available implementations for a specific protocol.

        Args:
            protocol: The protocol name (e.g., 'quic')

        Returns:
            List of implementation names
        """
        try:
            implementations = []
            all_plugins = self.plugin_catalog.catalog

            for (
                plugin_id,
                manifest,
            ) in all_plugins.items():  # pylint: disable=unused-variable
                # Check if this is a service plugin that supports the protocol
                manifest_type = None
                if hasattr(manifest, "plugin_type") and manifest.plugin_type:
                    manifest_type = (
                        manifest.plugin_type.value
                        if hasattr(manifest.plugin_type, "value")
                        else str(manifest.plugin_type)
                    )
                elif hasattr(manifest, "type"):
                    manifest_type = manifest.type

                if manifest_type == "service" and protocol in getattr(
                    manifest, "supported_protocols", []
                ):
                    implementations.append(manifest.name)

            self.logger.debug(
                "Found %d implementations for protocol %s",
                len(implementations),
                protocol,
            )
            return implementations

        except Exception as e:  # pylint: disable=broad-exception-caught
            self.logger.error("Error getting implementations for protocol %s: %s", protocol, e)
            return []

    def get_testers(self) -> list[str]:
        """
        Get all available tester plugins.

        Returns:
            List of tester plugin names
        """
        try:
            testers = []
            all_plugins = self.plugin_catalog.catalog

            for (
                plugin_id,
                manifest,
            ) in all_plugins.items():  # pylint: disable=unused-variable
                # Check if this is a tester plugin
                if (
                    hasattr(manifest, "categories") and "tester" in manifest.categories
                ) or "tester" in plugin_id:
                    testers.append(manifest.name)

            self.logger.debug("Found %d tester plugins", len(testers))
            return testers

        except Exception as e:  # pylint: disable=broad-exception-caught
            self.logger.error("Error getting tester plugins: %s", e)
            return []

    def get_plugin_manifest(self, plugin_name: str, plugin_type: str | None = None):
        """
        Get the manifest information for a plugin.

        Args:
            plugin_name: Name of the plugin
            plugin_type: Optional plugin type for filtering

        Returns:
            Plugin manifest or None if not found
        """
        try:
            # Search through catalog
            for (
                plugin_id,
                manifest,
            ) in self.plugin_catalog.catalog.items():  # pylint: disable=unused-variable
                manifest_type = None
                if hasattr(manifest, "plugin_type") and manifest.plugin_type:
                    manifest_type = (
                        manifest.plugin_type.value
                        if hasattr(manifest.plugin_type, "value")
                        else str(manifest.plugin_type)
                    )
                elif hasattr(manifest, "type"):
                    manifest_type = manifest.type

                if manifest.name == plugin_name and (
                    plugin_type is None or manifest_type == plugin_type
                ):
                    return manifest

            return None

        except Exception as e:  # pylint: disable=broad-exception-caught
            self.logger.error("Error getting plugin manifest for %s: %s", plugin_name, e)
            return None

    def validate_plugin_dependencies(self, plugin_name: str) -> tuple[bool, list[str]]:
        """
        Validate that all dependencies for a plugin are available.

        Args:
            plugin_name: Name of the plugin to validate

        Returns:
            Tuple of (dependencies_satisfied, missing_dependencies)
        """
        try:
            manifest = self.get_plugin_manifest(plugin_name)

            if manifest is None:
                return False, [f"Plugin {plugin_name} not found"]

            dependencies = getattr(manifest, "dependencies", [])
            missing_dependencies = []

            for dependency in dependencies:
                if not self.is_plugin_available(dependency):
                    missing_dependencies.append(dependency)

            dependencies_satisfied = len(missing_dependencies) == 0

            self.logger.debug(
                "Plugin %s dependency validation: %s (missing: %s)",
                plugin_name,
                "passed" if dependencies_satisfied else "failed",
                missing_dependencies,
            )

            return dependencies_satisfied, missing_dependencies

        except Exception as e:  # pylint: disable=broad-exception-caught
            self.logger.error("Error validating dependencies for %s: %s", plugin_name, e)
            return False, [f"Validation error: {str(e)}"]

    def get_plugin_version(self, plugin_name: str) -> str | None:
        """
        Get the version of a specific plugin.

        Args:
            plugin_name: Name of the plugin

        Returns:
            Plugin version string or None if not found
        """
        try:
            manifest = self.get_plugin_manifest(plugin_name)
            return getattr(manifest, "version", None) if manifest else None

        except Exception as e:  # pylint: disable=broad-exception-caught
            self.logger.error("Error getting version for plugin %s: %s", plugin_name, e)
            return None

    def get_dockerfiles(self) -> dict[str, Path]:
        """
        Get all discovered Dockerfiles mapped by plugin name.

        Returns:
            Dictionary mapping plugin names to Dockerfile paths
        """
        return self.dockerfiles.copy()
