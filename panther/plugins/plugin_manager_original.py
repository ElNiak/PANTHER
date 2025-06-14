"""
Plugin Manager for Panther Framework
"""

import importlib
import importlib.util
import os
from pathlib import Path
from typing import Any

from omegaconf import OmegaConf

from panther.config.config_experiment_schema import ServiceConfig, TestConfig
from panther.config.config_global_schema import GlobalConfig
from panther.core.observer.impl.plugin_observer import PluginObserver
from panther.core.observer.management.event_manager import EventManager
from panther.core.docker_builder import DockerBuilder
from panther.core.utils.logging_mixin import LoggerMixin
from panther.plugins.environments.environment_interface import IEnvironmentPlugin
from panther.plugins.environments.execution_environment.execution_environment_interface import (
    IExecutionEnvironment,
)
from panther.plugins.environments.network_environment.network_environment_interface import (
    INetworkEnvironment,
)
from panther.plugins.plugin_catalog import PluginCatalog
from panther.plugins.plugin_manifest import PluginRegistration, PluginType
from panther.plugins.protocols.config_schema import ProtocolConfig
from panther.plugins.services.iut.config_schema import ImplementationConfig
from panther.plugins.services.services_interface import IServiceManager


class PluginManager(LoggerMixin):
    """
    Unified plugin manager using catalog-based plugin functionality.

    This manager provides:
    - Configuration-based plugin loading
    - Catalog-based discovery and validation
    - Dependency resolution
    - Event-driven architecture support
    """

    @staticmethod
    def _get_class_name(plugin_name: str, suffix: str = "Config") -> str:
        """Convert plugin name to class name format."""
        class_name_parts = plugin_name.split("_")
        class_name_parts = [part.capitalize() for part in class_name_parts]
        class_name = "".join(class_name_parts) + suffix
        return class_name

    def _create_execution_environment_config(self, environment_type: str):
        """
        Create the appropriate configuration object for the execution environment type.

        This method dynamically discovers and instantiates the config class for the given
        environment type by following the standard naming convention and module structure.

        Args:
            environment_type: Type of execution environment (e.g., 'strace', 'gperf_cpu')

        Returns:
            Appropriate configuration object for the environment type
        """
        try:
            # Dynamically construct the module path and config class name
            module_path = f"panther.plugins.environments.execution_environment.{environment_type}.config_schema"
            config_class_name = self._get_class_name(environment_type, suffix="Config")

            # Try to import the specific config module and class
            try:
                import importlib

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
                    "Failed to load specific config for environment type '%s': %s. Using fallback.",
                    environment_type,
                    e,
                )
                # Fall through to generic config fallback

        except Exception as e:
            self.logger.warning(
                "Unexpected error creating config for environment type '%s': %s",
                environment_type,
                e,
            )

        # Fallback to generic config for any failure case
        from panther.plugins.environments.config_schema import EnvironmentConfig

        self.logger.debug(
            "Using generic EnvironmentConfig for environment type '%s'", environment_type
        )
        return EnvironmentConfig(type=environment_type)

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

        # Plugin catalog for discovery and validation
        self.plugin_directories = plugin_directories or []
        self.plugin_catalog = PluginCatalog(self.plugin_directories)

        # Event system
        self.event_manager = event_manager
        self.plugin_observer = None
        self.plugin_event_emitter = None
        if self.event_manager:
            self._setup_event_system()

        # Plugin registrations
        self.registrations: dict[str, PluginRegistration] = {}

        # Docker management
        self.global_config = global_config
        try:
            self.docker_builder = DockerBuilder(
                build_log_file=(
                    global_config.docker.log_docker_image_build if global_config else None
                )
            )
        except Exception as e:
            self.logger.warning("Failed to initialize DockerBuilder: %s", e)
            self.docker_builder = None

        # Built images and dockerfiles tracking
        self.built_images = {}
        self.dockerfiles = {}

        # Scan for available plugins
        self._discover_plugins()

    def _setup_event_system(self):
        """Setup event system components."""
        if self.event_manager:
            # Create plugin event emitter
            from panther.core.events import PluginEventEmitter

            self.plugin_event_emitter = PluginEventEmitter(self.event_manager)

            # Create and register plugin observer
            self.plugin_observer = PluginObserver()
            self.event_manager.register_observer(self.plugin_observer)

            self.logger.debug("Event system initialized")

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
        for plugin_id, manifest in plugins.items():
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
                    plugin_id = f"{PluginType.ENVIRONMENT.value}:{env_type}"
                    required_plugins.add(plugin_id)

            # Check services
            if hasattr(test, "services"):
                for service_name, service_config in test.services.items():
                    if hasattr(service_config, "implementation") and service_config.implementation:
                        impl = service_config.implementation
                        impl_name = impl.name if hasattr(impl, "name") else None
                        impl_type = impl.type.lower() if hasattr(impl, "type") else "iut"

                        if impl_name:
                            if impl_type == "testers":
                                plugin_id = f"{PluginType.TESTER.value}:{impl_name}"
                            else:
                                plugin_id = f"{PluginType.IUT.value}:{impl_name}"

                            required_plugins.add(plugin_id)

        # Validate each required plugin
        for plugin_id in required_plugins:
            if plugin_id not in self.plugin_catalog.catalog:
                errors.append(f"Required plugin not found: {plugin_id}")

        # Resolve dependencies
        if not errors:
            plugin_list = list(required_plugins)
            resolved_order, missing_deps = self.plugin_catalog.resolve_dependencies(plugin_list)
            if missing_deps:
                errors.extend(missing_deps)

        return len(errors) == 0, errors

    def create_service_manager(
        self,
        protocol: ProtocolConfig,
        implementation: ImplementationConfig,
        implementation_dir: Path,
        service_config_to_test: ServiceConfig,
        event_manager: EventManager | None = None,
        emitter_registry=None,
    ) -> IServiceManager:
        """
        Create a service manager instance using the catalog-based approach.
        """
        self.logger.debug(
            "Creating service manager for %s (%s)",
            implementation.name,
            implementation.type,
        )

        # Check if we have a catalog entry for this plugin
        impl_type_str = (
            implementation.type
            if isinstance(implementation.type, str)
            else implementation.type.name
        )
        plugin_type = PluginType.TESTER if impl_type_str.lower() == "testers" else PluginType.IUT
        plugin_id = f"{plugin_type.value}:{implementation.name}"
        manifest = self.plugin_catalog.catalog.get(plugin_id)

        try:
            # Determine module name and path
            impl_name = implementation.name

            if impl_type_str.lower() == "testers":
                service_module_name = f"panther.plugins.services.testers.{impl_name}.{impl_name}"
                service_file_path = implementation_dir / f"{impl_name}.py"
            else:
                protocol_name = protocol.name if hasattr(protocol, "name") else protocol
                service_module_name = (
                    f"panther.plugins.services.iut.{protocol_name}.{impl_name}.{impl_name}"
                )
                service_file_path = implementation_dir / f"{impl_name}.py"

            self.logger.debug("Loading service module from %s", service_file_path)

            # Use PluginManagerUtils to load the plugin class
            from panther.plugins.plugin_loader_utils import PluginManagerUtils

            service_manager_class = PluginManagerUtils.load_plugin_class(
                plugin_path=service_file_path,
                class_suffix="ServiceManager",
                name_transform=lambda name: self._get_class_name(name, suffix=""),
            )

            # Create the instance - pass both event_manager and emitter_registry
            # The service manager can use emitter_registry if available, otherwise fallback to event_manager
            service_manager = service_manager_class(  # type: ignore[misc]
                service_config_to_test=service_config_to_test,
                service_type=implementation.type,
                protocol=protocol,
                implementation_name=impl_name,
                event_manager=event_manager or self.event_manager,
                emitter_registry=emitter_registry,
            )

            # Register if we have a manifest
            if manifest:
                registration = PluginRegistration(
                    manifest=manifest,
                    instance=service_manager,
                    loaded=True,
                    active=True,
                )
                self.registrations[plugin_id] = registration

            # Emit plugin loaded event if we have event system
            if self.plugin_event_emitter:
                self.plugin_event_emitter.emit_plugin_loading_completed(
                    plugin_id=plugin_id,
                    plugin_name=impl_name,
                    plugin_type=plugin_type.value,
                    duration=0.0,  # TODO: Track actual load time
                    capabilities=[],
                    version=manifest.version if manifest else "unknown",
                )

            self.logger.debug("Service manager %s created successfully", impl_name)
            return service_manager

        except Exception as e:
            # Create a more helpful error message
            available_plugins = self.list_available_plugins()
            error_message = (
                f"Failed to create service manager for '{implementation.name}': {str(e)}"
            )

            if plugin_id not in self.plugin_catalog.catalog:
                error_message += f"\n\nPlugin '{implementation.name}' not found in catalog."
                error_message += "\n\nAvailable plugins:"
                for p_type, plugins in available_plugins.items():
                    if plugins:
                        error_message += (
                            f"\n  {p_type}: {', '.join(p.split(' v')[0] for p in plugins)}"
                        )

                error_message += "\n\nPlease ensure the plugin is installed and available."
                error_message += "\nYou can list all plugins with: python -m panther --list-plugins"

            self.logger.error(error_message)

            # Emit plugin loading failed event
            if self.plugin_event_emitter:
                self.plugin_event_emitter.emit_plugin_loading_failed(
                    plugin_id=plugin_id,
                    plugin_name=implementation.name,
                    plugin_type=plugin_type.value,
                    error_message=error_message,
                    error_details={"exception_type": type(e).__name__},
                )

            raise RuntimeError(error_message) from e

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
        """
        self.logger.debug("Creating environment manager for %s", environment)

        # Check catalog for this environment
        plugin_id = f"{PluginType.ENVIRONMENT.value}:{environment}"
        manifest = self.plugin_catalog.catalog.get(plugin_id)

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

            # Construct module name
            module_name = f"panther.plugins.environments.{env_type}.{env_sub_type}.{env_sub_type}"

            # Determine file path
            if manifest and manifest.file_path:
                env_file_path = Path(manifest.file_path) / f"{env_sub_type}.py"
            else:
                env_file_path = environment_dir / f"{env_sub_type}.py"

            self.logger.debug("Loading environment module from %s", env_file_path)

            # Use PluginManagerUtils to load the plugin class
            from panther.plugins.plugin_loader_utils import PluginManagerUtils

            env_manager_class = PluginManagerUtils.load_plugin_class(
                plugin_path=env_file_path,
                class_suffix="Environment",
                name_transform=lambda name: self._get_class_name(name, suffix=""),
            )

            # Extract environment configuration
            from panther.plugins.environments.config_schema import EnvironmentConfig

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

            self.logger.debug("Environment manager %s created successfully", environment)
            return env_manager

        except Exception as e:
            # Create a more helpful error message
            available_plugins = self.list_available_plugins()
            error_message = f"Failed to create environment manager for '{environment}': {str(e)}"

            if plugin_id not in self.plugin_catalog.catalog:
                error_message += f"\n\nEnvironment plugin '{environment}' not found in catalog."
                error_message += "\n\nAvailable environment plugins:"
                env_plugins = available_plugins.get(PluginType.ENVIRONMENT.value, [])
                if env_plugins:
                    error_message += f"\n  {', '.join(p.split(' v')[0] for p in env_plugins)}"
                else:
                    error_message += "\n  No environment plugins found"

                error_message += "\n\nPlease ensure the plugin is installed and available."
                error_message += "\nYou can list all plugins with: python -m panther --list-plugins"

            self.logger.error(error_message)
            raise RuntimeError(error_message) from e

    def get_plugin_info(self, plugin_id: str) -> dict[str, Any] | None:
        """Get detailed information about a plugin."""
        return self.plugin_catalog.get_plugin_info(plugin_id)

    def list_available_plugins(self) -> dict[str, list[str]]:
        """List all available plugins organized by type."""
        plugins_by_type = {}

        for plugin_id, manifest in self.plugin_catalog.catalog.items():
            plugin_type = manifest.type.value
            if plugin_type not in plugins_by_type:
                plugins_by_type[plugin_type] = []

            plugins_by_type[plugin_type].append(f"{manifest.name} v{manifest.version}")

        return plugins_by_type

    def get_plugin_status(self, plugin_id: str) -> dict[str, Any]:
        """Get the status of a plugin."""
        registration = self.registrations.get(plugin_id)

        if registration:
            return {
                "plugin_id": plugin_id,
                "loaded": registration.loaded,
                "active": registration.active,
                "version": registration.manifest.version,
                "error": registration.error_message,
            }

        manifest = self.plugin_catalog.catalog.get(plugin_id)
        if manifest:
            return {
                "plugin_id": plugin_id,
                "loaded": False,
                "active": False,
                "version": manifest.version,
                "error": "Not loaded",
            }

        return {
            "plugin_id": plugin_id,
            "loaded": False,
            "active": False,
            "error": "Plugin not found",
        }

    def refresh_catalog(self):
        """Refresh the plugin catalog by rescanning directories."""
        self.plugin_catalog.scan_plugins(use_cache=False)
        self.logger.info("Plugin catalog refreshed")

    def get_implementations_for_protocol(self, protocol: str) -> list[str]:
        """Get implementations for a specific protocol from catalog."""
        self.logger.debug("Getting implementations for protocol: %s", protocol)
        implementations = []

        # Check catalog
        for plugin_id, manifest in self.plugin_catalog.catalog.items():
            if manifest.type == PluginType.IUT and protocol in manifest.supported_protocols:
                implementations.append(manifest.name)

        return implementations

    def get_testers(self) -> list[str]:
        """Get testers from catalog."""
        testers = []

        # Check catalog
        for plugin_id, manifest in self.plugin_catalog.catalog.items():
            if manifest.type == PluginType.TESTER:
                testers.append(manifest.name)

        return testers

    def get_plugin_manifest(self, plugin_name: str, plugin_type: str | None = None):
        """
        Get the manifest for a specific plugin.

        Args:
            plugin_name: Name of the plugin
            plugin_type: Optional type hint to disambiguate

        Returns:
            PluginManifest if found, None otherwise
        """
        # Try with type hint first
        if plugin_type:
            plugin_id = f"{plugin_type}:{plugin_name}"
            if plugin_id in self.plugin_catalog.catalog:
                return self.plugin_catalog.catalog[plugin_id]

        # Search without type
        for plugin_id, manifest in self.plugin_catalog.catalog.items():
            if manifest.name == plugin_name:
                return manifest

        return None

    def validate_plugin_dependencies(self, plugin_name: str) -> tuple[bool, list[str]]:
        """
        Validate that all dependencies for a plugin are satisfied.

        Args:
            plugin_name: Name of the plugin to validate

        Returns:
            Tuple of (is_valid, list_of_missing_dependencies)
        """
        manifest = self.get_plugin_manifest(plugin_name)
        if not manifest:
            return False, [f"Plugin '{plugin_name}' not found"]

        # Find the plugin ID
        plugin_id = None
        for pid, m in self.plugin_catalog.catalog.items():
            if m.name == plugin_name:
                plugin_id = pid
                break

        if not plugin_id:
            return False, [f"Plugin ID not found for '{plugin_name}'"]

        # Use catalog's dependency resolution
        _, missing = self.plugin_catalog.resolve_dependencies([plugin_id])

        return len(missing) == 0, missing

    def get_plugin_version(self, plugin_name: str) -> str | None:
        """
        Get the version of a plugin.

        Args:
            plugin_name: Name of the plugin

        Returns:
            Version string if found, None otherwise
        """
        manifest = self.get_plugin_manifest(plugin_name)
        return manifest.version if manifest else None

    def build_docker_image(self, impl_name: str, versions: str):
        """Build Docker image for a plugin implementation."""
        if not self.docker_builder:
            self.logger.error("DockerBuilder not initialized, cannot build images")
            raise RuntimeError("DockerBuilder not initialized")

        self.logger.debug(
            "Looking for Dockerfile for '%s' in dockerfiles: %s",
            impl_name,
            list(self.dockerfiles.keys()),
        )

        # If not found, try to discover it from the protocol implementations
        if impl_name not in self.dockerfiles:
            # Try to find the protocol this implementation belongs to
            services_base = Path(os.path.dirname(__file__)) / "services"

            # Check both iut and testers directories
            for service_type in ["iut", "testers"]:
                service_type_dir = services_base / service_type
                if not service_type_dir.exists():
                    continue

                if service_type == "iut":
                    # For IUT services, look in protocol subdirectories
                    for protocol_dir in service_type_dir.iterdir():
                        if protocol_dir.is_dir():
                            impl_dir = protocol_dir / impl_name
                            if impl_dir.exists() and (impl_dir / "Dockerfile").exists():
                                self.dockerfiles[impl_name] = impl_dir / "Dockerfile"
                                self.logger.info(
                                    "Discovered Dockerfile for '%s' at '%s'",
                                    impl_name,
                                    impl_dir / "Dockerfile",
                                )
                                break
                else:
                    # For testers services, look directly in the service type directory
                    impl_dir = service_type_dir / impl_name
                    if impl_dir.exists() and (impl_dir / "Dockerfile").exists():
                        self.dockerfiles[impl_name] = impl_dir / "Dockerfile"
                        self.logger.info(
                            "Discovered Dockerfile for '%s' at '%s'",
                            impl_name,
                            impl_dir / "Dockerfile",
                        )
                        break

                # If found, break from outer loop
                if impl_name in self.dockerfiles:
                    break

        if impl_name in self.dockerfiles:
            dockerfile_path = self.dockerfiles[impl_name]
            self.logger.debug(
                "Found configuration for implementation '%s': %s", impl_name, versions
            )
            image_tag = self.docker_builder.build_image(
                impl_name=impl_name,
                version=("unknown" if not hasattr(versions, "version") else versions.version),
                dockerfile_path=dockerfile_path,
                context_path=dockerfile_path.parent,
                config=(
                    {}
                    if not hasattr(versions, "version")
                    else {
                        "commit": versions.commit,
                        "dependencies": OmegaConf.to_container(versions.dependencies),
                    }
                ),
                tag_version="latest",
                build_image_force=(
                    self.global_config.docker.build_docker_image if self.global_config else True
                ),
                remove_dangling=(
                    self.global_config.docker.remove_dangling_images if self.global_config else True
                ),
            )
            if image_tag:
                key = f"{impl_name}_{versions}"
                self.built_images[key] = image_tag
            else:
                self.logger.error(
                    "Image build failed for implementation '%s' version '%s'",
                    impl_name,
                    versions,
                )
        else:
            self.logger.error(
                "Dockerfile not found for implementation '%s' in %s. Skipping.",
                impl_name,
                self.dockerfiles,
            )
            raise FileNotFoundError(f"Dockerfile not found for implementation '{impl_name}'.")

    def build_docker_image_from_path(self, path: Path, name: str, version: str | None = None):
        """Build Docker image from a specific path."""
        if not self.docker_builder:
            self.logger.error("DockerBuilder not initialized, cannot build images")
            raise RuntimeError("DockerBuilder not initialized")

        self.logger.info("Building image from path '%s'", path)
        dockerfile_path = path.resolve()
        versions = {version: {}} if version else {"latest": {}}
        self.logger.debug("Found configuration for path '%s': %s", path.name, versions)
        for version, version_config in versions.items():
            self.logger.info("Building image for path '%s' version '%s'", path.name, version)
            image_tag = self.docker_builder.build_image(
                impl_name=name,
                version=version,
                dockerfile_path=dockerfile_path,
                context_path=dockerfile_path.parent.resolve(),
                config=version_config,
                tag_version="latest",
                build_image_force=(
                    self.global_config.docker.build_docker_image if self.global_config else True
                ),
                remove_dangling=(
                    self.global_config.docker.remove_dangling_images if self.global_config else True
                ),
            )
            if image_tag:
                key = f"{path.name}_{version}"
                self.built_images[key] = image_tag
            else:
                self.logger.error(
                    "Image build failed for implementation '%s' version '%s'",
                    path.name,
                    version,
                )
                raise RuntimeError(
                    f"Image build failed for implementation '{path.name}' version '{version}'."
                )
            return image_tag

    def get_network_environment_plugin(self, environment_type: str) -> INetworkEnvironment | None:
        """
        Get a network environment plugin instance by type.

        Args:
            environment_type: Type of network environment (e.g., 'docker_compose', 'localhost_single_container')

        Returns:
            Network environment plugin instance or None if not found
        """
        try:
            # Check catalog for this environment
            plugin_id = f"{PluginType.ENVIRONMENT.value}:{environment_type}"
            manifest = self.plugin_catalog.catalog.get(plugin_id)

            if not manifest:
                self.logger.warning(
                    "Network environment plugin '%s' not found in catalog",
                    environment_type,
                )
                return None

            # Get the path for this environment plugin
            base_path = Path(__file__).parent
            env_path = base_path / "environments" / "network_environment" / environment_type

            if not env_path.exists():
                self.logger.error("Network environment path does not exist: %s", env_path)
                return None

            # Load the plugin module
            module_name = f"panther.plugins.environments.network_environment.{environment_type}.{environment_type}"

            try:
                module = importlib.import_module(module_name)
            except ImportError as e:
                self.logger.error(
                    "Failed to import network environment module %s: %s", module_name, e
                )
                return None

            # Get the environment class
            class_name = self._get_class_name(environment_type, suffix="Environment")

            try:
                env_class = getattr(module, class_name)
            except AttributeError:
                self.logger.error(
                    "Network environment class '%s' not found in module %s",
                    class_name,
                    module_name,
                )
                return None

            # Create a minimal config for the plugin
            from panther.plugins.environments.config_schema import EnvironmentConfig

            env_config = EnvironmentConfig(type=environment_type)

            # Create and return instance
            env_instance = env_class(
                env_config_to_test=env_config,
                output_dir="",  # Will be set later
                env_type="network_environment",
                env_sub_type=environment_type,
                event_manager=self.event_manager,
            )

            return env_instance

        except Exception as e:
            self.logger.error(
                "Failed to get network environment plugin '%s': %s",
                environment_type,
                e,
                exc_info=True,
            )
            return None

    def get_execution_environment_plugin(
        self, environment_type: str
    ) -> IExecutionEnvironment | None:
        """
        Get an execution environment plugin instance by type.

        Args:
            environment_type: Type of execution environment (e.g., 'strace', 'gperf_cpu')

        Returns:
            Execution environment plugin instance or None if not found
        """
        try:
            # Check catalog for this environment
            plugin_id = f"{PluginType.ENVIRONMENT.value}:{environment_type}"
            manifest = self.plugin_catalog.catalog.get(plugin_id)

            if not manifest:
                self.logger.warning(
                    "Execution environment plugin '%s' not found in catalog",
                    environment_type,
                )
                return None

            # Get the path for this environment plugin
            base_path = Path(__file__).parent
            env_path = base_path / "environments" / "execution_environment" / environment_type

            if not env_path.exists():
                self.logger.error("Execution environment path does not exist: %s", env_path)
                return None

            # Load the plugin module
            module_name = f"panther.plugins.environments.execution_environment.{environment_type}.{environment_type}"

            try:
                module = importlib.import_module(module_name)
            except ImportError as e:
                self.logger.error(
                    "Failed to import execution environment module %s: %s",
                    module_name,
                    e,
                )
                return None

            # Get the environment class
            class_name = self._get_class_name(environment_type, suffix="Environment")

            try:
                env_class = getattr(module, class_name)
            except AttributeError:
                self.logger.error(
                    "Execution environment class '%s' not found in module %s",
                    class_name,
                    module_name,
                )
                return None

            # Create the appropriate config for the plugin
            env_config = self._create_execution_environment_config(environment_type)

            # Create and return instance
            env_instance = env_class(
                env_config_to_test=env_config,
                output_dir="",  # Will be set later
                env_type="execution_environment",
                env_sub_type=environment_type,
                event_manager=self.event_manager,
            )

            return env_instance

        except Exception as e:
            self.logger.error(
                "Failed to get execution environment plugin '%s': %s",
                environment_type,
                e,
                exc_info=True,
            )
            return None
