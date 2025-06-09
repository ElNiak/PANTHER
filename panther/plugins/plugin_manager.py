"""
Enhanced Plugin Ecosystem for PANTHER Framework

This module provides a comprehensive plugin system with discovery, management,
hot-reloading, and lifecycle management capabilities while maintaining
backward compatibility with existing service and environment plugin loading.
"""

import importlib
import importlib.util
import logging
import os
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Optional

from panther.core.observer.event_manager import EventManager
from panther.core.observer.plugin.plugin_observer import PluginObserver
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
from panther.plugins.plugin_interface_enhanced import IPantherPlugin


class PluginStatus(Enum):
    """Plugin status enumeration."""

    NOT_LOADED = "not_loaded"
    LOADING = "loading"
    LOADED = "loaded"
    ACTIVE = "active"
    ERROR = "error"
    DISABLED = "disabled"


@dataclass
class PluginMetadata:
    """Plugin metadata information."""

    name: str
    version: str = "1.0.0"
    description: str = ""
    author: str = ""
    dependencies: list[str] = field(default_factory=list)
    minimum_panther_version: str = "1.0.0"
    supported_events: list[str] = field(default_factory=list)
    configuration_schema: dict[str, Any] = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)


@dataclass
class PluginInfo:
    """Complete plugin information."""

    metadata: PluginMetadata
    plugin_class: type["IPantherPlugin"]
    file_path: str
    status: PluginStatus = PluginStatus.NOT_LOADED
    instance: Optional["IPantherPlugin"] = None
    error_message: str = ""
    load_time: float | None = None
    last_modified: float | None = None


class PluginManager:
    """
    Enhanced plugin manager for PANTHER framework.

    Manages the loading and instantiation of various plugins for the system,
    including traditional service/environment plugins and modern extensible plugins
    with discovery, lifecycle management, and hot-reloading capabilities.

    Attributes:
        plugins_loader (PluginLoader): The loader responsible for loading traditional plugins.
        logger (logging.Logger): Logger instance for logging messages.
        protocol_plugins (Dict[str, IServiceManager]): Dictionary to store protocol plugins.
        network_environment_plugins (Dict[str, INetworkEnvironment]): Dictionary to store network environment plugins.
        execution_environment_plugins (Dict[str, IExecutionEnvironment]): Dictionary to store execution environment plugins.
    Methods:
        # Traditional plugin methods (backward compatibility)
        create_service_manager(protocol: ProtocolConfig, implementation: ImplementationConfig, implementation_dir: Path, service_config_to_test: ServiceConfig) -> IServiceManager:
            Creates and returns an instance of a service manager for the given protocol and implementation.

        create_environment_manager(environment: str, test_config: TestConfig, environment_dir: Path, output_dir: Path, event_manager: EventManager) -> IEnvironmentPlugin:
            Creates and returns an instance of an environment manager for the given environment.
    """

    def __init__(self, plugins_loader: PluginLoader = None, plugin_directories: list[str] = None):
        """
        Initialize plugin manager with both traditional and enhanced capabilities.

        Args:
            plugins_loader: Traditional plugin loader (for backward compatibility)
            plugin_directories: Directories to scan for modern plugins
        """
        # Traditional plugin system (backward compatibility)
        self.plugins_loader = plugins_loader
        self.logger = logging.getLogger("PluginManager")
        self.protocol_plugins: dict[str, IServiceManager] = {}
        self.network_environment_plugins: dict[str, INetworkEnvironment] = {}
        self.execution_environment_plugins: dict[str, IExecutionEnvironment] = {}

        # Create a combined dictionary to make it easier to access environment plugins
        self.environment_plugins = {
            "network_environment": self.network_environment_plugins,
            "execution_environment": self.execution_environment_plugins,
        }

        # Event system support
        self.event_emitter = None
        self.event_manager = None
        self.plugin_observer = None

        # Enhanced plugin system
        self.plugin_directories = plugin_directories or []
        self.plugins: dict[str, PluginInfo] = {}
        self.active_plugins: dict[str, IPantherPlugin] = {}
        self.plugin_dependencies: dict[str, set[str]] = {}

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
        if (
            self.plugins_loader
            and hasattr(self.plugins_loader, "environment_plugins")
            and "network_environment" in self.plugins_loader.environment_plugins
            and environment_type in self.plugins_loader.environment_plugins["network_environment"]
        ):

            # Store in our cache for future use
            plugin = self.plugins_loader.environment_plugins["network_environment"][
                environment_type
            ]
            self.network_environment_plugins[environment_type] = plugin
            return plugin

        # Not found anywhere
        self.logger.error("Network environment plugin not found: %s", environment_type)
        available_plugins = list(self.network_environment_plugins.keys())
        if self.plugins_loader and hasattr(self.plugins_loader, "environment_plugins"):
            if "network_environment" in self.plugins_loader.environment_plugins:
                available_plugins.extend(
                    self.plugins_loader.environment_plugins["network_environment"].keys()
                )
        self.logger.error("Available network environment plugins: %s", available_plugins)
        return None

    def create_service_manager(
        self,
        protocol: ProtocolConfig,
        implementation: ImplementationConfig,
        implementation_dir: Path,
        service_config_to_test: ServiceConfig,
    ) -> IServiceManager:
        """
        Creates and returns a service manager for the given protocol and implementation.

        This method creates a service manager instance based on the provided protocol
        and implementation configurations. It loads the appropriate module, instantiates
        the service manager class, and sets up event emission if applicable.

        Args:
            protocol: The protocol configuration
            implementation: The implementation configuration
            implementation_dir: Directory containing the implementation
            service_config_to_test: Service configuration to use for testing

        Returns:
            IServiceManager: A new instance of a service manager

        Raises:
            ImportError: If the module cannot be imported
            AttributeError: If the service manager class is not found in the module
            Exception: For other errors during service manager creation
        """
        self.logger.debug(
            f"Creating service manager for {implementation.name} ({implementation.type})"
        )

        try:
            # Determine the module name and class name based on implementation
            impl_name = implementation.name

            # Construct the module path (depends on implementation type)
            if implementation.type.name.lower() == "testers":
                service_module_name = f"panther.plugins.services.testers.{impl_name}.{impl_name}"
                service_file_path = implementation_dir / f"{impl_name}.py"
            else:  # iut or other types
                protocol_name = protocol.name if hasattr(protocol, "name") else protocol
                service_module_name = (
                    f"panther.plugins.services.iut.{protocol_name}.{impl_name}.{impl_name}"
                )
                service_file_path = implementation_dir / f"{impl_name}.py"

            self.logger.debug(f"Loading service module from {service_file_path}")

            # Import the module using importlib
            spec = importlib.util.spec_from_file_location(service_module_name, service_file_path)
            if spec is None or spec.loader is None:
                raise ImportError(f"Could not find module at {service_file_path}")

            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # Get the class name using the plugin loader's naming convention
            class_name = self.plugins_loader.get_class_name(impl_name, suffix="ServiceManager")
            service_manager_class = getattr(module, class_name, None)

            if service_manager_class is None:
                raise AttributeError(
                    f"Could not find class {class_name} in module {service_module_name}"
                )

            # Create the service manager instance
            service_manager = service_manager_class(
                service_config_to_test=service_config_to_test,
                service_type=implementation.type,
                protocol=protocol,
                implementation_name=impl_name,
            )

            # Set up event emitter if available
            if self.event_emitter and hasattr(service_manager, "event_emitter"):
                service_manager.event_emitter = self.event_emitter
                self.logger.debug(f"Set event emitter on service manager {impl_name}")

            return service_manager

            return service_manager

        except Exception as e:
            self.logger.error(f"Failed to create service manager: {e}", exc_info=True)
            raise

    def create_environment_manager(
        self,
        environment: str,
        test_config: TestConfig,
        environment_dir: Path,
        output_dir: Path,
        event_manager: EventManager,
    ) -> IEnvironmentPlugin:
        """
        Creates and returns an environment manager for the given environment.

        This method creates an environment manager instance based on the provided
        environment type and test configuration. It loads the appropriate module,
        instantiates the environment manager class, and sets up event emission if applicable.

        Args:
            environment: The environment type (e.g., "docker_compose", "shadow_ns")
            test_config: Test configuration
            environment_dir: Directory containing the environment implementation
            output_dir: Directory for output files
            event_manager: Event manager instance

        Returns:
            IEnvironmentPlugin: A new instance of an environment manager

        Raises:
            ImportError: If the module cannot be imported
            AttributeError: If the environment manager class is not found in the module
            Exception: For other errors during environment manager creation
        """
        self.logger.debug("Creating environment manager for %s", environment)

        try:
            # Initialize variables
            env_type = None
            env_sub_type = None

            # First check if the plugins_loader has environment plugins loaded
            if self.plugins_loader and hasattr(self.plugins_loader, "environment_plugins"):
                # Check if environment exists in network_environment plugins from the loader
                if (
                    "network_environment" in self.plugins_loader.environment_plugins
                    and environment
                    in self.plugins_loader.environment_plugins["network_environment"]
                ):
                    env_type = "network_environment"
                    env_sub_type = environment
                # Check if environment exists in execution_environment plugins from the loader
                elif (
                    "execution_environment" in self.plugins_loader.environment_plugins
                    and environment
                    in self.plugins_loader.environment_plugins["execution_environment"]
                ):
                    env_type = "execution_environment"
                    env_sub_type = environment

            # If not found in loader, check our own environment_plugins
            if env_type is None:
                # Check in network_environment plugins
                if environment in self.environment_plugins.get("network_environment", {}):
                    env_type = "network_environment"
                    env_sub_type = environment
                # Check in execution_environment plugins
                elif environment in self.environment_plugins.get("execution_environment", {}):
                    env_type = "execution_environment"
                    env_sub_type = environment

            # If still not found, raise an error
            if env_type is None:
                self.logger.error(f"Unknown environment type: {environment}")
                if self.plugins_loader and hasattr(self.plugins_loader, "environment_plugins"):
                    self.logger.debug(
                        f"Available environment types in loader: {self.plugins_loader.environment_plugins.keys()}"
                    )
                    if "network_environment" in self.plugins_loader.environment_plugins:
                        self.logger.debug(
                            f"Available network environments: {list(self.plugins_loader.environment_plugins['network_environment'].keys())}"
                        )
                    if "execution_environment" in self.plugins_loader.environment_plugins:
                        self.logger.debug(
                            f"Available execution environments: {list(self.plugins_loader.environment_plugins['execution_environment'].keys())}"
                        )
                raise ValueError(f"Unknown environment type: {environment}")

            # Construct module name
            module_name = f"panther.plugins.environments.{env_type}.{env_sub_type}.{env_sub_type}"

            # Determine the file path (either from directory structure or plugin loader info)
            if self.plugins_loader and hasattr(self.plugins_loader, "environment_plugins"):
                plugin_info = self.plugins_loader.environment_plugins.get(env_type, {}).get(
                    env_sub_type
                )
                if plugin_info and isinstance(plugin_info, Path):
                    # If we have a directory path from plugin_loader, use the module file inside that directory
                    env_file_path = plugin_info / f"{env_sub_type}.py"
                else:
                    # Otherwise use the standard path
                    env_file_path = environment_dir / f"{env_sub_type}.py"
            else:
                # Fallback to standard path
                env_file_path = environment_dir / f"{env_sub_type}.py"

            self.logger.debug("Loading environment module from %s", env_file_path)

            # Import the module using importlib
            spec = importlib.util.spec_from_file_location(module_name, env_file_path)
            if spec is None or spec.loader is None:
                raise ImportError(f"Could not find module at {env_file_path}")

            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # Get the class name
            class_name = self.plugins_loader.get_class_name(env_sub_type, suffix="Environment")
            env_manager_class = getattr(module, class_name, None)

            if env_manager_class is None:
                raise AttributeError(f"Could not find class {class_name} in module {module_name}")

            # Create the environment manager instance
            from panther.plugins.environments.config_schema import EnvironmentConfig

            # Extract environment configuration from test_config
            env_config = getattr(test_config, env_type, {})
            if isinstance(env_config, dict):
                env_config_to_test = EnvironmentConfig(**env_config)
            else:
                env_config_to_test = env_config

            env_manager = env_manager_class(
                env_config_to_test=env_config_to_test,
                output_dir=str(output_dir),
                env_type=env_type,
                env_sub_type=env_sub_type,
                event_manager=event_manager,
            )

            # Set up event emitter if available
            if self.event_emitter and hasattr(env_manager, "event_emitter"):
                env_manager.event_emitter = self.event_emitter
                self.logger.debug("Set event emitter on environment manager %s", environment)

            return env_manager

        except Exception as e:
            self.logger.error("Failed to create environment manager: %s", e, exc_info=True)
            raise

    def set_event_emitter(self, event_emitter):
        """
        Set the event emitter for this plugin manager.

        This method configures the event system for the plugin manager and
        all managed plugins. It handles:
        1. Setting the event_emitter attribute
        2. Obtaining the event_manager from the emitter
        3. Creating and registering a PluginObserver
        4. Propagating the event_emitter to existing plugin instances

        Args:
            event_emitter: The event emitter to use
        """
        self.event_emitter = event_emitter

        # Get the event manager from the emitter
        if hasattr(event_emitter, "event_manager"):
            self.event_manager = event_emitter.event_manager

            # Create and register the plugin observer
            self.plugin_observer = PluginObserver()
            self.event_manager.register_observer(self.plugin_observer)

            # Propagate to existing plugins
            for plugin_info in self.plugins.values():
                if plugin_info.instance and isinstance(plugin_info.instance, IPantherPlugin):
                    plugin_info.instance.set_event_emitter(event_emitter)

        self.logger.debug("Event emitter set on PluginManager")

    def _set_event_emitter_on_service(self, service_instance):
        """
        Set the event emitter on a service instance.

        This method is used internally and for testing to ensure service
        instances have access to the event emitter for proper event-driven
        architecture integration.

        Args:
            service_instance: The service instance to set the event emitter on
        """
        if hasattr(service_instance, "event_emitter"):
            service_instance.event_emitter = self.event_emitter
        else:
            # For services that don't have event_emitter attribute, add it
            service_instance.event_emitter = self.event_emitter

    def scan_plugin_directories(self):
        """
        Scan configured directories for available plugins.

        This method searches all plugin directories for Python modules
        that implement the IPantherPlugin interface.
        """
        if not self.plugin_directories:
            self.logger.warning("No plugin directories configured")
            return

        for plugin_dir in self.plugin_directories:
            if not os.path.isdir(plugin_dir):
                self.logger.warning("Plugin directory not found: %s", plugin_dir)
                continue

            self.logger.info("Scanning plugin directory: %s", plugin_dir)
            self._scan_directory_for_plugins(plugin_dir)

    def _scan_directory_for_plugins(self, directory: str):
        """
        Scan a single directory for plugins.

        Args:
            directory: Directory path to scan
        """
        for root, _, files in os.walk(directory):
            for filename in files:
                if filename.endswith(".py") and not filename.startswith("__"):
                    file_path = os.path.join(root, filename)
                    self._try_load_plugin_module(file_path)

    def _try_load_plugin_module(self, file_path: str):
        """
        Try to load a Python file as a plugin module.

        Args:
            file_path: Path to the Python file
        """
        try:
            module_name = os.path.basename(file_path)[:-3]  # Remove .py extension
            self.logger.debug("Examining module: %s from %s", module_name, file_path)

            # Import the module
            spec = importlib.util.spec_from_file_location(module_name, file_path)
            if not spec or not spec.loader:
                return

            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # Find plugin classes in the module
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (
                    isinstance(attr, type)
                    and attr != IPantherPlugin
                    and issubclass(attr, IPantherPlugin)
                ):

                    self._register_plugin_class(attr, file_path)

        except (ImportError, AttributeError) as e:
            self.logger.debug("Failed to load potential plugin %s: %s", file_path, str(e))

    def _register_plugin_class(self, plugin_class: type[IPantherPlugin], file_path: str):
        """
        Register a plugin class.

        Args:
            plugin_class: The plugin class to register
            file_path: Path to the plugin file
        """
        # Extract plugin metadata
        metadata = self._extract_plugin_metadata(plugin_class, file_path)

        # Create plugin info
        plugin_info = PluginInfo(
            metadata=metadata,
            plugin_class=plugin_class,
            file_path=file_path,
            last_modified=os.path.getmtime(file_path),
        )

        self.plugins[metadata.name] = plugin_info
        self.logger.info("Found plugin: %s (version %s)", metadata.name, metadata.version)

    def _extract_plugin_metadata(
        self, plugin_class: type[IPantherPlugin], file_path: str
    ) -> PluginMetadata:
        """
        Extract metadata from a plugin class.

        Args:
            plugin_class: The plugin class
            file_path: Path to the plugin file

        Returns:
            Extracted PluginMetadata
        """
        # Start with default metadata using the class name
        metadata = PluginMetadata(name=plugin_class.__name__)

        # Extract metadata from class attributes if available
        if hasattr(plugin_class, "METADATA"):
            class_metadata = getattr(plugin_class, "METADATA", {})
            if isinstance(class_metadata, dict):
                metadata.name = class_metadata.get("name", metadata.name)
                metadata.version = class_metadata.get("version", metadata.version)
                metadata.description = class_metadata.get("description", metadata.description)
                metadata.author = class_metadata.get("author", metadata.author)
                metadata.dependencies = class_metadata.get("dependencies", metadata.dependencies)
                metadata.minimum_panther_version = class_metadata.get(
                    "minimum_panther_version", metadata.minimum_panther_version
                )
                metadata.supported_events = class_metadata.get(
                    "supported_events", metadata.supported_events
                )
                metadata.configuration_schema = class_metadata.get(
                    "configuration_schema", metadata.configuration_schema
                )
                metadata.tags = class_metadata.get("tags", metadata.tags)

        return metadata

    def load_plugin(self, plugin_name: str, config: dict = None) -> bool:
        """
        Load a plugin by name.

        This method instantiates the plugin, initializes it, and registers it with
        the plugin observer for event delivery.

        Args:
            plugin_name: Name of the plugin to load
            config: Configuration for the plugin

        Returns:
            bool: True if plugin was successfully loaded
        """
        if plugin_name not in self.plugins:
            self.logger.warning("Plugin not found: %s", plugin_name)
            return False

        plugin_info = self.plugins[plugin_name]
        if plugin_info.status == PluginStatus.ACTIVE:
            self.logger.debug("Plugin already active: %s", plugin_name)
            return True

        # Update status
        plugin_info.status = PluginStatus.LOADING

        try:
            # Instantiate the plugin
            plugin_instance = plugin_info.plugin_class(
                plugin_id=plugin_name, name=plugin_info.metadata.name
            )

            # Set the event emitter if available
            if self.event_emitter:
                plugin_instance.set_event_emitter(self.event_emitter)

            # Initialize the plugin
            success = plugin_instance.initialize(config or {})
            if not success:
                self.logger.error("Failed to initialize plugin: %s", plugin_name)
                plugin_info.status = PluginStatus.ERROR
                plugin_info.error_message = "Initialization failed"
                return False

            # Update plugin info
            plugin_info.instance = plugin_instance
            plugin_info.status = PluginStatus.ACTIVE
            plugin_info.load_time = time.time()

            # Register with plugin observer if available
            if self.plugin_observer:
                self.plugin_observer.register_plugin(plugin_instance)

            self.logger.info("Successfully loaded plugin: %s", plugin_name)
            return True

        except Exception as e:
            self.logger.error("Error loading plugin %s: %s", plugin_name, str(e), exc_info=True)
            plugin_info.status = PluginStatus.ERROR
            plugin_info.error_message = str(e)
            return False

    def unload_plugin(self, plugin_name: str) -> bool:
        """
        Unload a plugin by name.

        This method shuts down the plugin and unregisters it from the plugin observer.

        Args:
            plugin_name: Name of the plugin to unload

        Returns:
            bool: True if plugin was successfully unloaded
        """
        if plugin_name not in self.plugins:
            self.logger.warning("Plugin not found: %s", plugin_name)
            return False

        plugin_info = self.plugins[plugin_name]
        if plugin_info.status != PluginStatus.ACTIVE or not plugin_info.instance:
            self.logger.debug("Plugin not active: %s", plugin_name)
            return True

        try:
            # Shutdown the plugin
            plugin_instance = plugin_info.instance
            success = plugin_instance.shutdown()

            # Unregister from plugin observer
            if self.plugin_observer and plugin_instance:
                self.plugin_observer.unregister_plugin(plugin_instance.plugin_id)

            # Update plugin info
            plugin_info.instance = None
            plugin_info.status = PluginStatus.LOADED

            self.logger.info("Successfully unloaded plugin: %s", plugin_name)
            return success

        except Exception as e:
            self.logger.error("Error unloading plugin %s: %s", plugin_name, str(e), exc_info=True)
            plugin_info.status = PluginStatus.ERROR
            plugin_info.error_message = str(e)
            return False

    def get_active_plugins(self) -> list[str]:
        """
        Get names of currently active plugins.

        Returns:
            List of plugin names
        """
        return [name for name, info in self.plugins.items() if info.status == PluginStatus.ACTIVE]

    def get_available_plugins(self) -> dict[str, PluginMetadata]:
        """
        Get metadata for all available plugins.

        Returns:
            Dict mapping plugin names to their metadata
        """
        return {name: info.metadata for name, info in self.plugins.items()}

    def reload_plugins(self) -> dict[str, bool]:
        """
        Check for changes and reload modified plugins.

        Returns:
            Dict mapping plugin names to reload success status
        """
        results = {}

        for name, info in self.plugins.items():
            if not os.path.exists(info.file_path):
                self.logger.warning("Plugin file no longer exists: %s", info.file_path)
                continue

            last_modified = os.path.getmtime(info.file_path)
            if info.last_modified and last_modified > info.last_modified:
                self.logger.info("Plugin file changed, reloading: %s", name)

                # Remember the current status
                was_active = info.status == PluginStatus.ACTIVE

                # Unload if active
                if was_active:
                    self.unload_plugin(name)

                # Reload the module and recreate plugin info
                self._try_load_plugin_module(info.file_path)

                # Reload if it was active before
                if was_active and name in self.plugins:
                    success = self.load_plugin(name)
                    results[name] = success

        return results
