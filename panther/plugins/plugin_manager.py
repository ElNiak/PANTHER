"""
Plugin Manager for Panther Framework
"""

import importlib
import importlib.util
import logging
import os
from pathlib import Path
from typing import Any

from panther.core.observer.management.event_manager import EventManager
from panther.core.observer.impl.plugin_observer import PluginObserver
from panther.config.config_experiment_schema import ServiceConfig, TestConfig
from panther.plugins.protocols.config_schema import ProtocolConfig
from panther.plugins.services.iut.config_schema import ImplementationConfig
from panther.plugins.services.services_interface import IServiceManager
from panther.plugins.environments.network_environment.network_environment_interface import (
    INetworkEnvironment,
)
from panther.plugins.environments.execution_environment.execution_environment_interface import (
    IExecutionEnvironment,
)
from panther.plugins.environments.environment_interface import IEnvironmentPlugin
from panther.plugins.plugin_loader import PluginLoader
from panther.plugins.plugin_catalog import PluginCatalog
from panther.plugins.plugin_manifest import PluginType, PluginRegistration


class PluginManager:
    """
    Unified plugin manager that combines traditional and enhanced plugin functionality.

    This manager provides:
    - Configuration-based plugin loading
    - Catalog-based discovery and validation
    - Dependency resolution
    - Event-driven architecture support
    - Backward compatibility with existing plugins
    """

    def __init__(
        self,
        plugin_loader: PluginLoader | None = None,
        plugin_directories: list[str] | None = None,
        event_manager: EventManager | None = None,
    ):
        """
        Initialize the unified plugin manager.

        Args:
            plugin_loader: Traditional plugin loader for backward compatibility
            plugin_directories: Directories to scan for plugins
            event_manager: Event manager for plugin events
        """
        self.logger = logging.getLogger("PluginManager")

        # Traditional plugin system support
        self.plugin_loader = plugin_loader

        # Plugin catalog for discovery and validation
        self.plugin_directories = plugin_directories or []
        self.plugin_catalog = PluginCatalog(self.plugin_directories)

        # Event system
        self.event_manager = event_manager
        self.plugin_observer = None
        if self.event_manager:
            self._setup_event_system()

        # Plugin registrations
        self.registrations: dict[str, PluginRegistration] = {}

        # Legacy plugin caches (for backward compatibility)
        self.protocol_plugins: dict[str, IServiceManager] = {}
        self.network_environment_plugins: dict[str, INetworkEnvironment] = {}
        self.execution_environment_plugins: dict[str, IExecutionEnvironment] = {}

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
        self.plugin_catalog.scan_plugins()
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
    ) -> IServiceManager:
        """
        Create a service manager instance (backward compatible method).

        This maintains compatibility with the existing plugin system while
        internally using the new catalog-based approach when possible.
        """
        self.logger.debug(
            "Creating service manager for %s (%s)", implementation.name, implementation.type
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

            # Import the module
            spec = importlib.util.spec_from_file_location(service_module_name, service_file_path)
            if spec is None or spec.loader is None:
                raise ImportError(f"Could not find module at {service_file_path}")

            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # Get the class name
            class_name = PluginLoader.get_class_name(impl_name, suffix="ServiceManager")
            service_manager_class = getattr(module, class_name, None)

            if service_manager_class is None:
                raise AttributeError(
                    f"Could not find class {class_name} in module {service_module_name}"
                )

            # Create the instance
            service_manager = service_manager_class(  # type: ignore[misc]
                service_config_to_test=service_config_to_test,
                service_type=implementation.type,
                protocol=protocol,
                implementation_name=impl_name,
                event_manager=event_manager or self.event_manager,
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
        Create an environment manager instance (backward compatible method).
        """
        self.logger.debug("Creating environment manager for %s", environment)

        # Check catalog for this environment
        plugin_id = f"{PluginType.ENVIRONMENT.value}:{environment}"
        manifest = self.plugin_catalog.catalog.get(plugin_id)

        try:
            # Determine environment type and subtype
            env_type = None
            env_sub_type = environment

            # Check in plugin loader's discovered plugins
            if self.plugin_loader and hasattr(self.plugin_loader, "environment_plugins"):
                if "network_environment" in self.plugin_loader.environment_plugins:
                    if environment in self.plugin_loader.environment_plugins["network_environment"]:
                        env_type = "network_environment"
                elif "execution_environment" in self.plugin_loader.environment_plugins:
                    if (
                        environment
                        in self.plugin_loader.environment_plugins["execution_environment"]
                    ):
                        env_type = "execution_environment"

            if env_type is None:
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

            # Import the module
            spec = importlib.util.spec_from_file_location(module_name, env_file_path)
            if spec is None or spec.loader is None:
                raise ImportError(f"Could not find module at {env_file_path}")

            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # Get the class
            class_name = PluginLoader.get_class_name(env_sub_type, suffix="Environment")
            env_manager_class = getattr(module, class_name, None)

            if env_manager_class is None:
                raise AttributeError(f"Could not find class {class_name} in module {module_name}")

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

    def get_network_environment_plugin(self, environment_type: str) -> INetworkEnvironment:
        """
        Get a network environment plugin by type.

        Args:
            environment_type: The type of the network environment plugin to retrieve

        Returns:
            INetworkEnvironment: The requested network environment plugin if found

        Raises:
            ValueError: If the environment type is not found
        """
        self.logger.debug("Getting network environment plugin for type: %s", environment_type)

        # First try to get from our own cache
        if environment_type in self.network_environment_plugins:
            return self.network_environment_plugins[environment_type]

        # If not found and we have a plugins loader, check there
        if self.plugin_loader and hasattr(self.plugin_loader, "environment_plugins"):
            plugin_path = None

            # Check for flat structure (catalog-based discovery)
            network_key = f"network_{environment_type}"
            if network_key in self.plugin_loader.environment_plugins:
                plugin_path = self.plugin_loader.environment_plugins[network_key]

            # Check for nested structure (legacy file-based discovery)
            elif (
                "network_environment" in self.plugin_loader.environment_plugins
                and environment_type
                in self.plugin_loader.environment_plugins["network_environment"]
            ):
                plugin_path = self.plugin_loader.environment_plugins["network_environment"][
                    environment_type
                ]

            if plugin_path:
                # We need to create an actual plugin instance, not just return the path
                try:
                    # Create the environment manager instance
                    from panther.plugins.environments.config_schema import EnvironmentConfig

                    env_config_to_test = EnvironmentConfig(type=environment_type)

                    # Now create the actual plugin instance
                    env_type = "network_environment"
                    env_sub_type = environment_type

                    # Create an output directory if needed
                    output_dir = "/tmp/panther_output"  # This will be overridden by the test case
                    os.makedirs(output_dir, exist_ok=True)

                    # Create an event manager if needed
                    event_manager = self.event_manager or EventManager()

                    # Create the environment manager using the create_environment_manager method
                    plugin_instance = self.create_environment_manager(
                        environment=environment_type,
                        test_config=None,  # This will be set later by the test case
                        environment_dir=plugin_path.parent,  # Parent directory contains all environments
                        output_dir=output_dir,
                        event_manager=event_manager,
                    )

                    # Cache and return the instance
                    self.network_environment_plugins[environment_type] = plugin_instance
                    return plugin_instance
                except Exception as e:
                    self.logger.error(
                        "Failed to instantiate network environment plugin %s: %s",
                        environment_type,
                        str(e),
                        exc_info=True,
                    )
                    return None

        # Not found anywhere
        self.logger.error("Network environment plugin not found: %s", environment_type)
        available_plugins = list(self.network_environment_plugins.keys())
        if self.plugin_loader and hasattr(self.plugin_loader, "environment_plugins"):
            # Check for flat structure
            for key in self.plugin_loader.environment_plugins.keys():
                if key.startswith("network_"):
                    plugin_name = key.replace("network_", "")
                    if plugin_name not in available_plugins:
                        available_plugins.append(plugin_name)

            # Check for nested structure
            if "network_environment" in self.plugin_loader.environment_plugins:
                for plugin_name in self.plugin_loader.environment_plugins[
                    "network_environment"
                ].keys():
                    if plugin_name not in available_plugins:
                        available_plugins.append(plugin_name)

        self.logger.error("Available network environment plugins: %s", available_plugins)
        return None

    def get_execution_environment_plugin(self, environment_type: str) -> IExecutionEnvironment:
        """
        Get an execution environment plugin by type.

        Args:
            environment_type: The type of the execution environment plugin to retrieve

        Returns:
            IExecutionEnvironment: The requested execution environment plugin if found

        Raises:
            ValueError: If the environment type is not found
        """
        self.logger.debug("Getting execution environment plugin for type: %s", environment_type)

        # First try to get from our own cache
        if environment_type in self.execution_environment_plugins:
            return self.execution_environment_plugins[environment_type]

        # If not found and we have a plugins loader, check there
        if self.plugin_loader and hasattr(self.plugin_loader, "environment_plugins"):
            plugin_path = None

            # Check for flat structure (catalog-based discovery)
            execution_key = f"execution_{environment_type}"
            if execution_key in self.plugin_loader.environment_plugins:
                plugin_path = self.plugin_loader.environment_plugins[execution_key]

            # Check for nested structure (legacy file-based discovery)
            elif (
                "execution_environment" in self.plugin_loader.environment_plugins
                and environment_type
                in self.plugin_loader.environment_plugins["execution_environment"]
            ):
                plugin_path = self.plugin_loader.environment_plugins["execution_environment"][
                    environment_type
                ]

            if plugin_path:
                # We need to create an actual plugin instance, not just return the path
                try:
                    # Create the environment manager instance
                    from panther.plugins.environments.config_schema import EnvironmentConfig

                    env_config_to_test = EnvironmentConfig(type=environment_type)

                    # Now create the actual plugin instance
                    env_type = "execution_environment"
                    env_sub_type = environment_type

                    # Create an output directory if needed
                    output_dir = "/tmp/panther_output"  # This will be overridden by the test case
                    os.makedirs(output_dir, exist_ok=True)

                    # Create an event manager if needed
                    event_manager = self.event_manager or EventManager()

                    # Create the environment manager using the create_environment_manager method
                    plugin_instance = self.create_environment_manager(
                        environment=environment_type,
                        test_config=None,  # This will be set later by the test case
                        environment_dir=plugin_path.parent,  # Parent directory contains all environments
                        output_dir=output_dir,
                        event_manager=event_manager,
                    )

                    # Cache and return the instance
                    self.execution_environment_plugins[environment_type] = plugin_instance
                    return plugin_instance
                except Exception as e:
                    self.logger.error(
                        "Failed to instantiate execution environment plugin %s: %s",
                        environment_type,
                        str(e),
                        exc_info=True,
                    )
                    return None
        # Not found anywhere
        self.logger.error("Execution environment plugin not found: %s", environment_type)
        return None
