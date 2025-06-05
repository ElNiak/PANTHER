"""
Enhanced Plugin Manager Module

This module provides a central manager for the enhanced plugin architecture.
"""

import importlib
import inspect
import logging
import os
import sys
from pathlib import Path
from typing import Any

from panther.core.observer.event_manager import EventManager
from panther.core.observer.events import Event
from panther.plugins.enhanced_plugin_interface import IPantherPlugin
from panther.plugins.enhanced_plugin_registry import EnhancedPluginRegistry
from panther.plugins.services.base_service_plugin import BaseServicePlugin
from panther.plugins.environments.base_environment_plugin import BaseEnvironmentPlugin
from panther.plugins.testers.base_tester_plugin import BaseTesterPlugin


class EnhancedPluginManager:
    """
    Manager for the enhanced plugin architecture.

    This class is responsible for discovering, initializing, and managing plugins
    in the enhanced plugin architecture.
    """

    PLUGIN_TYPE_SERVICE = "service"
    PLUGIN_TYPE_ENVIRONMENT = "environment"
    PLUGIN_TYPE_TESTER = "tester"

    def __init__(self, event_manager: EventManager, discovery_paths: list[str] = None):
        """
        Initialize the plugin manager.

        Args:
            event_manager: Event manager for event propagation
            discovery_paths: Paths to search for plugins
        """
        self.event_manager = event_manager
        self.discovery_paths = discovery_paths or []
        self.plugin_registry = EnhancedPluginRegistry(event_manager)
        self.logger = logging.getLogger("EnhancedPluginManager")

        # Store plugin classes by type
        self.plugin_classes: dict[str, dict[str, type[IPantherPlugin]]] = {
            self.PLUGIN_TYPE_SERVICE: {},
            self.PLUGIN_TYPE_ENVIRONMENT: {},
            self.PLUGIN_TYPE_TESTER: {},
        }

        # Plugin metadata
        self.plugin_metadata: dict[str, dict[str, Any]] = {}

    def discover_plugins(self) -> dict[str, dict[str, type[IPantherPlugin]]]:
        """
        Discover available plugins in the discovery paths.

        Returns:
            Dict[str, Dict[str, Type[IPantherPlugin]]]: Dictionary of plugin types to plugin classes
        """
        for path in self.discovery_paths:
            if not os.path.isdir(path):
                self.logger.warning(f"Plugin discovery path does not exist: {path}")
                continue

            self.logger.info(f"Discovering plugins in: {path}")

            # Add path to Python path temporarily
            sys.path.insert(0, str(path))

            try:
                self._discover_in_path(path)
            except Exception as e:
                self.logger.exception(f"Error discovering plugins in {path}: {e}")
            finally:
                # Remove from path
                if str(path) in sys.path:
                    sys.path.remove(str(path))

        return self.plugin_classes

    def _discover_in_path(self, path: str) -> None:
        """
        Discover plugins in a specific path.

        Args:
            path: Path to search for plugins
        """
        path_obj = Path(path)

        # Look for Python files in the path
        for item in path_obj.glob("**/*.py"):
            # Skip __init__ and other special files
            if item.name.startswith("__"):
                continue

            relative_path = item.relative_to(path_obj)
            module_path = str(relative_path).replace(os.sep, ".")[:-3]  # Remove .py extension

            try:
                # Import the module
                module = importlib.import_module(module_path)

                # Find plugin classes
                for name, obj in inspect.getmembers(module):
                    if (
                        not inspect.isclass(obj)
                        or not issubclass(obj, IPantherPlugin)
                        or obj is IPantherPlugin
                    ):
                        continue

                    # Determine plugin type
                    plugin_type = self._determine_plugin_type(obj)
                    if not plugin_type:
                        continue

                    # Store the plugin class
                    plugin_id = f"{module_path}.{name}"
                    self.plugin_classes[plugin_type][plugin_id] = obj

                    # Extract metadata
                    self.plugin_metadata[plugin_id] = {
                        "name": name,
                        "module": module_path,
                        "file_path": str(item),
                        "type": plugin_type,
                        "version": getattr(obj, "VERSION", "1.0.0"),
                        "author": getattr(obj, "AUTHOR", "unknown"),
                        "description": getattr(obj, "__doc__", ""),
                    }

                    self.logger.debug(f"Discovered plugin: {plugin_id} (type: {plugin_type})")
            except Exception as e:
                self.logger.warning(f"Error loading module {module_path}: {e}")

    def _determine_plugin_type(self, plugin_class: type[IPantherPlugin]) -> str | None:
        """
        Determine the type of a plugin class.

        Args:
            plugin_class: The plugin class to check

        Returns:
            Optional[str]: Plugin type or None if unknown
        """
        if issubclass(plugin_class, BaseServicePlugin):
            return self.PLUGIN_TYPE_SERVICE
        elif issubclass(plugin_class, BaseEnvironmentPlugin):
            return self.PLUGIN_TYPE_ENVIRONMENT
        elif issubclass(plugin_class, BaseTesterPlugin):
            return self.PLUGIN_TYPE_TESTER
        else:
            return None

    def get_plugin_types(self) -> list[str]:
        """
        Get the available plugin types.

        Returns:
            List[str]: List of plugin types
        """
        return list(self.plugin_classes.keys())

    def get_plugins_by_type(self, plugin_type: str) -> dict[str, type[IPantherPlugin]]:
        """
        Get all plugins of a specific type.

        Args:
            plugin_type: Type of plugins to get

        Returns:
            Dict[str, Type[IPantherPlugin]]: Dictionary of plugin IDs to plugin classes
        """
        return self.plugin_classes.get(plugin_type, {})

    def get_plugin_class(self, plugin_id: str) -> type[IPantherPlugin] | None:
        """
        Get a plugin class by ID.

        Args:
            plugin_id: ID of the plugin class

        Returns:
            Optional[Type[IPantherPlugin]]: Plugin class if found, None otherwise
        """
        for plugin_type in self.plugin_classes:
            if plugin_id in self.plugin_classes[plugin_type]:
                return self.plugin_classes[plugin_type][plugin_id]
        return None

    def get_plugin_metadata(self, plugin_id: str) -> dict[str, Any]:
        """
        Get metadata for a plugin.

        Args:
            plugin_id: ID of the plugin

        Returns:
            Dict[str, Any]: Plugin metadata
        """
        return self.plugin_metadata.get(plugin_id, {})

    def create_plugin_instance(
        self, plugin_id: str, instance_id: str = None, config: dict[str, Any] = None
    ) -> IPantherPlugin | None:
        """
        Create an instance of a plugin.

        Args:
            plugin_id: ID of the plugin class
            instance_id: Unique ID for the instance (defaults to plugin_id)
            config: Configuration for the plugin

        Returns:
            Optional[IPantherPlugin]: Plugin instance if creation was successful, None otherwise
        """
        plugin_class = self.get_plugin_class(plugin_id)
        if not plugin_class:
            self.logger.error(f"Plugin class not found: {plugin_id}")
            return None

        try:
            # Use instance_id if provided, otherwise use plugin_id
            instance_id = instance_id or plugin_id

            # Create the plugin instance
            plugin_instance = plugin_class(
                plugin_id=instance_id, plugin_registry=self.plugin_registry, config=config or {}
            )

            # Register the plugin with the registry
            self.plugin_registry.register_plugin(instance_id, plugin_instance)

            return plugin_instance
        except Exception as e:
            self.logger.exception(f"Error creating plugin instance {plugin_id}: {e}")
            return None

    def initialize_plugin(self, plugin_instance_id: str) -> bool:
        """
        Initialize a plugin instance.

        Args:
            plugin_instance_id: ID of the plugin instance

        Returns:
            bool: True if initialization was successful, False otherwise
        """
        plugin = self.plugin_registry.get_plugin(plugin_instance_id)
        if not plugin:
            self.logger.error(f"Plugin instance not found: {plugin_instance_id}")
            return False

        try:
            return plugin.initialize()
        except Exception as e:
            self.logger.exception(f"Error initializing plugin {plugin_instance_id}: {e}")
            return False

    def start_plugin(self, plugin_instance_id: str) -> bool:
        """
        Start a plugin instance.

        Args:
            plugin_instance_id: ID of the plugin instance

        Returns:
            bool: True if startup was successful, False otherwise
        """
        plugin = self.plugin_registry.get_plugin(plugin_instance_id)
        if not plugin:
            self.logger.error(f"Plugin instance not found: {plugin_instance_id}")
            return False

        try:
            return plugin.start()
        except Exception as e:
            self.logger.exception(f"Error starting plugin {plugin_instance_id}: {e}")
            return False

    def stop_plugin(self, plugin_instance_id: str) -> bool:
        """
        Stop a plugin instance.

        Args:
            plugin_instance_id: ID of the plugin instance

        Returns:
            bool: True if shutdown was successful, False otherwise
        """
        plugin = self.plugin_registry.get_plugin(plugin_instance_id)
        if not plugin:
            self.logger.error(f"Plugin instance not found: {plugin_instance_id}")
            return False

        try:
            return plugin.stop()
        except Exception as e:
            self.logger.exception(f"Error stopping plugin {plugin_instance_id}: {e}")
            return False

    def get_plugin_status(self, plugin_instance_id: str) -> dict[str, Any]:
        """
        Get the status of a plugin instance.

        Args:
            plugin_instance_id: ID of the plugin instance

        Returns:
            Dict[str, Any]: Plugin status information
        """
        return self.plugin_registry.get_plugin_status(plugin_instance_id)

    def dispatch_event(self, event: Event) -> None:
        """
        Dispatch an event to the plugin registry.

        Args:
            event: Event to dispatch
        """
        self.plugin_registry.dispatch_event(event)

    def unregister_plugin(self, plugin_instance_id: str) -> bool:
        """
        Unregister a plugin instance.

        Args:
            plugin_instance_id: ID of the plugin instance

        Returns:
            bool: True if unregistration was successful, False otherwise
        """
        # First stop the plugin if it exists
        plugin = self.plugin_registry.get_plugin(plugin_instance_id)
        if plugin:
            try:
                plugin.stop()
            except Exception as e:
                self.logger.warning(
                    f"Error stopping plugin {plugin_instance_id} during unregistration: {e}"
                )

        # Then unregister it
        return self.plugin_registry.unregister_plugin(plugin_instance_id)
