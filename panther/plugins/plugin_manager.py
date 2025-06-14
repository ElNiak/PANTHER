"""
Refactored Plugin Manager for Panther Framework

This is the refactored version that uses specialized classes for different
responsibilities while maintaining backward compatibility with the existing API.
"""

from pathlib import Path
from typing import Any

from panther.config.config_experiment_schema import ServiceConfig, TestConfig
from panther.config.config_global_schema import GlobalConfig
from panther.core.observer.impl.plugin_observer import PluginObserver
from panther.core.observer.management.event_manager import EventManager
from panther.core.docker_builder import DockerBuilder
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
from panther.plugins.service_factory import ServiceFactory
from panther.plugins.environment_factory import EnvironmentFactory
from panther.plugins.plugin_manifest import PluginRegistration
from panther.plugins.protocols.config_schema import ProtocolConfig
from panther.plugins.services.iut.config_schema import ImplementationConfig
from panther.plugins.services.services_interface import IServiceManager


class PluginManager(LoggerMixin):
    """
    Refactored unified plugin manager using specialized components.

    This manager coordinates specialized classes:
    - PluginConfigResolver: Configuration resolution
    - PluginDiscovery: Plugin discovery and catalog management
    - ServiceFactory: Service manager creation
    - EnvironmentFactory: Environment manager creation

    Maintains backward compatibility with the original API.
    """

    def __init__(
        self,
        plugin_directories: list[str] | None = None,
        event_manager: EventManager | None = None,
        global_config: GlobalConfig | None = None,
    ):
        """
        Initialize the unified plugin manager.

        Args:
            plugin_directories: Directories to scan for plugins
            event_manager: Event manager for plugin events
            global_config: Global configuration for Docker and other settings
        """
        super().__init__()

        # Store configuration
        self.plugin_directories = plugin_directories or []
        self.event_manager = event_manager
        self.global_config = global_config

        # Initialize specialized components
        self.config_resolver = PluginConfigResolver()
        self.plugin_discovery = PluginDiscovery(plugin_directories)

        # Event system setup
        self.plugin_observer = None
        self.plugin_event_emitter = None
        if self.event_manager:
            self._setup_event_system()

        # Initialize factories with dependencies
        self.service_factory = ServiceFactory(
            config_resolver=self.config_resolver,
            plugin_discovery=self.plugin_discovery,
            event_manager=self.event_manager,
            plugin_event_emitter=self.plugin_event_emitter,
        )

        self.environment_factory = EnvironmentFactory(
            config_resolver=self.config_resolver,
            plugin_discovery=self.plugin_discovery,
            event_manager=self.event_manager,
            plugin_event_emitter=self.plugin_event_emitter,
        )

        # Docker management
        try:
            self.docker_builder = DockerBuilder(
                build_log_file=(
                    global_config.docker.log_docker_image_build if global_config else None
                )
            )
        except Exception as e:  # pylint: disable=broad-exception-caught
            self.logger.warning("Failed to initialize DockerBuilder: %s", e)
            self.docker_builder = None

        # Built images tracking
        self.built_images = {}

    def _setup_event_system(self):
        """Set up the event system for plugin management."""
        try:
            # Import event emitter
            from panther.core.events import (
                PluginEventEmitter,
            )  # pylint: disable=import-outside-toplevel

            # Create plugin observer
            self.plugin_observer = PluginObserver(event_manager=self.event_manager)

            # Create plugin event emitter
            self.plugin_event_emitter = PluginEventEmitter(self.event_manager)

            self.logger.debug("Plugin event system initialized successfully")
        except Exception as e:  # pylint: disable=broad-exception-caught
            self.logger.warning("Failed to initialize plugin event system: %s", e)

    # Backward compatibility methods - delegate to specialized classes

    @staticmethod
    def _get_class_name(plugin_name: str, suffix: str = "Config") -> str:
        """Convert plugin name to class name format. (Backward compatibility)"""
        return PluginConfigResolver.get_class_name(plugin_name, suffix)

    def _create_execution_environment_config(self, environment_type: str):
        """Create execution environment config. (Backward compatibility)"""
        return self.config_resolver.create_execution_environment_config(environment_type)

    def validate_experiment_plugins(self, experiment_config: Any) -> tuple[bool, list[str]]:
        """Validate that all plugins required by an experiment are available."""
        return self.plugin_discovery.validate_experiment_plugins(experiment_config)

    def create_service_manager(
        self,
        protocol: ProtocolConfig,
        implementation: ImplementationConfig,
        implementation_dir: Path,
        service_config_to_test: ServiceConfig,
        event_manager: EventManager | None = None,
        emitter_registry=None,
    ) -> IServiceManager:
        """Create a service manager instance."""
        return self.service_factory.create_service_manager(
            protocol=protocol,
            implementation=implementation,
            implementation_dir=implementation_dir,
            service_config_to_test=service_config_to_test,
            event_manager=event_manager,
            emitter_registry=emitter_registry,
        )

    def create_environment_manager(
        self,
        environment: str,
        test_config: TestConfig,
        environment_dir: Path,
        output_dir: Path,
        event_manager: EventManager,
    ) -> IEnvironmentPlugin:
        """Create an environment manager instance."""
        return self.environment_factory.create_environment_manager(
            environment=environment,
            test_config=test_config,
            environment_dir=environment_dir,
            output_dir=output_dir,
            event_manager=event_manager,
        )

    def get_plugin_info(self, plugin_id: str) -> dict[str, Any] | None:
        """Get information about a specific plugin."""
        return self.plugin_discovery.get_plugin_info(plugin_id)

    def list_available_plugins(self) -> dict[str, list[str]]:
        """Get a list of all available plugins organized by type."""
        return self.plugin_discovery.list_available_plugins()

    def get_plugin_status(self, plugin_id: str) -> dict[str, Any]:
        """Get the current status of a plugin."""
        return self.plugin_discovery.get_plugin_status(plugin_id)

    def refresh_catalog(self):
        """Refresh the plugin catalog by re-scanning directories."""
        self.plugin_discovery.refresh_catalog()

    def get_implementations_for_protocol(self, protocol: str) -> list[str]:
        """Get all available implementations for a specific protocol."""
        return self.plugin_discovery.get_implementations_for_protocol(protocol)

    def get_testers(self) -> list[str]:
        """Get all available tester plugins."""
        return self.plugin_discovery.get_testers()

    def get_plugin_manifest(self, plugin_name: str, plugin_type: str | None = None):
        """Get the manifest information for a plugin."""
        return self.plugin_discovery.get_plugin_manifest(plugin_name, plugin_type)

    def validate_plugin_dependencies(self, plugin_name: str) -> tuple[bool, list[str]]:
        """Validate that all dependencies for a plugin are available."""
        return self.plugin_discovery.validate_plugin_dependencies(plugin_name)

    def get_plugin_version(self, plugin_name: str) -> str | None:
        """Get the version of a specific plugin."""
        return self.plugin_discovery.get_plugin_version(plugin_name)

    def is_plugin_available(self, plugin_id: str) -> bool:
        """Check if a plugin is available."""
        return self.plugin_discovery.is_plugin_available(plugin_id)

    def get_network_environment_plugin(self, environment_type: str) -> INetworkEnvironment | None:
        """Get a network environment plugin instance."""
        return self.environment_factory.get_network_environment_plugin(environment_type)

    def get_execution_environment_plugin(
        self, environment_type: str, output_dir: str, event_manager: EventManager
    ) -> IExecutionEnvironment | None:
        """Get an execution environment plugin instance."""
        return self.environment_factory.get_execution_environment_plugin(
            environment_type, output_dir, event_manager
        )

    # Docker management methods (keep in main class)

    def build_docker_image(self, impl_name: str, versions):
        """
        Build Docker image for a plugin implementation.

        Args:
            impl_name: Implementation name
            versions: Version configuration (can be string or dict)
        """
        if not self.docker_builder:
            self.logger.warning("Docker builder not available")
            return

        try:
            # Get dockerfile path from plugin discovery
            dockerfiles = self.plugin_discovery.get_dockerfiles()
            dockerfile_path = dockerfiles.get(impl_name)

            if not dockerfile_path:
                self.logger.warning("No Dockerfile found for implementation: %s", impl_name)
                return

            # Extract version string from config object if necessary
            if isinstance(versions, dict):
                # If it's a config object, extract the version field or use a default
                version_str = versions.get("version", "latest")
            elif isinstance(versions, str):
                version_str = versions
            else:
                # For complex objects, try to extract version attributes safely
                if hasattr(versions, "version"):
                    version_str = str(versions.version)
                elif hasattr(versions, "name"):
                    version_str = str(versions.name)
                elif hasattr(versions, "value"):
                    version_str = str(versions.value)
                else:
                    # Safe fallback - use class name instead of full object string
                    version_str = (
                        versions.__class__.__name__.lower()
                        if hasattr(versions, "__class__")
                        else "latest"
                    )

            # Ensure version string is safe for Docker tag (no special characters)
            safe_version = "".join(c if c.isalnum() or c in ".-_" else "_" for c in version_str)

            # Build the image
            image_tag = f"{impl_name}:{safe_version}"

            self.logger.info("Building Docker image %s from %s", image_tag, dockerfile_path)

            build_result = self.docker_builder.build_image(
                impl_name=impl_name,
                version=safe_version,
                dockerfile_path=dockerfile_path,
                context_path=dockerfile_path.parent,
                config=versions if isinstance(versions, dict) else {},
            )

            if build_result:
                # Handle different return types from docker_builder.build_image()
                self.logger.debug(
                    "Docker build result type: %s, value: %s",
                    type(build_result).__name__,
                    str(build_result)[:100],  # Limit length for logging
                )
                if isinstance(build_result, dict):
                    build_info = {
                        "tag": image_tag,
                        "dockerfile": str(dockerfile_path),
                        "build_time": build_result.get("build_time"),
                        "image_id": build_result.get("image_id"),
                    }
                else:
                    # If build_result is not a dict (e.g., string or other type), use basic info
                    build_info = {
                        "tag": image_tag,
                        "dockerfile": str(dockerfile_path),
                        "build_time": None,
                        "image_id": str(build_result) if build_result else None,
                    }

                self.built_images[impl_name] = build_info
                self.logger.info("Successfully built Docker image: %s", image_tag)
            else:
                self.logger.error("Failed to build Docker image: %s", image_tag)

        except Exception as e:  # pylint: disable=broad-exception-caught
            self.logger.error("Error building Docker image for %s: %s", impl_name, e)
            # Add more specific debugging for get() attribute errors
            if "'str' object has no attribute 'get'" in str(e):
                self.logger.error(
                    "build_result type was: %s",
                    type(build_result).__name__ if "build_result" in locals() else "undefined",
                )
            import traceback

            self.logger.debug("Full traceback: %s", traceback.format_exc())

    def build_docker_image_from_path(self, path: Path, name: str, version: str | None = None):
        """
        Build Docker image from a specific path.

        Args:
            path: Path to Dockerfile or build context
            name: Image name
            version: Image version (optional)
        """
        if not self.docker_builder:
            self.logger.warning("Docker builder not available")
            return

        try:
            # Determine dockerfile path
            if path.is_file() and path.name == "Dockerfile":
                dockerfile_path = path
                build_context = path.parent
            elif path.is_dir():
                dockerfile_path = path / "Dockerfile"
                build_context = path
                if not dockerfile_path.exists():
                    self.logger.error("No Dockerfile found in directory: %s", path)
                    return
            else:
                self.logger.error("Invalid path for Docker build: %s", path)
                return

            # Build image tag
            image_tag = f"{name}:{version}" if version else name

            self.logger.info("Building Docker image %s from %s", image_tag, dockerfile_path)

            build_result = self.docker_builder.build_image(
                impl_name=name,
                version=version or "latest",
                dockerfile_path=dockerfile_path,
                context_path=build_context,
                config={},
            )

            if build_result:
                # Handle different return types from docker_builder.build_image()
                self.logger.debug(
                    "Docker build result type: %s, value: %s",
                    type(build_result).__name__,
                    str(build_result)[:100],  # Limit length for logging
                )
                if isinstance(build_result, dict):
                    build_info = {
                        "tag": image_tag,
                        "dockerfile": str(dockerfile_path),
                        "build_time": build_result.get("build_time"),
                        "image_id": build_result.get("image_id"),
                    }
                else:
                    # If build_result is not a dict (e.g., string or other type), use basic info
                    build_info = {
                        "tag": image_tag,
                        "dockerfile": str(dockerfile_path),
                        "build_time": None,
                        "image_id": str(build_result) if build_result else None,
                    }

                self.built_images[name] = build_info
                self.logger.info("Successfully built Docker image: %s", image_tag)
            else:
                self.logger.error("Failed to build Docker image: %s", image_tag)

        except Exception as e:  # pylint: disable=broad-exception-caught
            self.logger.error("Error building Docker image from path %s: %s", path, e)
            # Add more specific debugging for get() attribute errors
            if "'str' object has no attribute 'get'" in str(e):
                self.logger.error(
                    "build_result type was: %s",
                    type(build_result).__name__ if "build_result" in locals() else "undefined",
                )
            import traceback

            self.logger.debug("Full traceback: %s", traceback.format_exc())

    # Properties for backward compatibility

    @property
    def plugin_catalog(self):
        """Access to plugin catalog for backward compatibility."""
        return self.plugin_discovery.plugin_catalog

    @property
    def registrations(self) -> dict[str, PluginRegistration]:
        """Access to plugin registrations for backward compatibility."""
        # Combine registrations from all components
        all_registrations = {}
        all_registrations.update(self.plugin_discovery.registrations)
        all_registrations.update(self.service_factory.registrations)
        all_registrations.update(self.environment_factory.registrations)
        return all_registrations

    @property
    def dockerfiles(self) -> dict[str, Path]:
        """Access to dockerfiles for backward compatibility."""
        return self.plugin_discovery.get_dockerfiles()

    # Additional convenience methods

    def get_built_images(self) -> dict[str, dict[str, Any]]:
        """
        Get information about built Docker images.

        Returns:
            Dictionary mapping image names to build information
        """
        return self.built_images.copy()

    def is_image_built(self, image_name: str) -> bool:
        """
        Check if a Docker image has been built.

        Args:
            image_name: Name of the image to check

        Returns:
            True if image has been built, False otherwise
        """
        return image_name in self.built_images

    def get_summary(self) -> dict[str, Any]:
        """
        Get a summary of the plugin manager state.

        Returns:
            Dictionary containing summary information
        """
        return {
            "plugin_directories": self.plugin_directories,
            "total_plugins": len(self.plugin_catalog.catalog),
            "total_registrations": len(self.registrations),
            "built_images": len(self.built_images),
            "dockerfiles_found": len(self.dockerfiles),
            "available_plugins": self.list_available_plugins(),
            "event_system_enabled": self.plugin_event_emitter is not None,
            "docker_builder_available": self.docker_builder is not None,
        }
