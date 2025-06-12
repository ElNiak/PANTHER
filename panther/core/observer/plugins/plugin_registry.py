"""
Plugin Registry Module

This module provides functionality for discovering, loading, and managing
observer plugins in the PANTHER framework.
"""

import os
import sys
import importlib
import inspect
from typing import Any

from panther.core.observer.plugins.plugin_interface import IObserverPlugin


class PluginRegistry:
    """
    Registry for observer plugins.

    This class provides functionality for discovering, loading,
    and managing observer plugins from specified directories.
    """

    def __init__(self, plugin_paths: list[str] = None):
        """
        Initialize a new PluginRegistry.

        Args:
            plugin_paths: List of directories to search for plugins
        """
        self.plugin_paths = plugin_paths or []
        self.plugins: dict[str, type[IObserverPlugin]] = {}
        self.plugin_metadata: dict[str, dict[str, Any]] = {}

    def discover_plugins(self) -> dict[str, type[IObserverPlugin]]:
        """
        Discover available plugins in plugin directories.

        Returns:
            Dictionary of plugin names to plugin classes
        """
        for path in self.plugin_paths:
            if not os.path.isdir(path):
                continue

            # Add path to Python path temporarily
            sys.path.insert(0, path)

            # Scan for Python files
            for file in os.listdir(path):
                if file.endswith(".py") and not file.startswith("__"):
                    module_name = file[:-3]  # Remove .py extension

                    try:
                        # Import the module
                        module = importlib.import_module(module_name)

                        # Find plugin classes
                        for name, obj in inspect.getmembers(module):
                            if (
                                inspect.isclass(obj)
                                and issubclass(obj, IObserverPlugin)
                                and obj != IObserverPlugin
                            ):
                                self.plugins[name] = obj

                                # Extract metadata
                                metadata = {
                                    "version": getattr(obj, "VERSION", "unknown"),
                                    "author": getattr(obj, "AUTHOR", "unknown"),
                                    "events": getattr(obj, "EVENTS", []),
                                    "description": getattr(obj, "__doc__", ""),
                                }
                                self.plugin_metadata[name] = metadata
                    except Exception as e:
                        print(f"Error loading plugin module {module_name}: {e}")

            # Remove from path
            sys.path.remove(path)

        return self.plugins

    def get_plugin_class(self, name: str) -> type[IObserverPlugin] | None:
        """
        Get a plugin class by name.

        Args:
            name: Name of the plugin class

        Returns:
            Plugin class if found, None otherwise
        """
        return self.plugins.get(name)

    def get_plugin_metadata(self, name: str) -> dict[str, Any]:
        """
        Get metadata for a plugin.

        Args:
            name: Name of the plugin

        Returns:
            Dictionary of plugin metadata
        """
        return self.plugin_metadata.get(name, {})

    def instantiate_plugin(self, name: str, *args, **kwargs) -> IObserverPlugin | None:
        """
        Instantiate a plugin by name.

        Args:
            name: Name of the plugin class
            *args: Positional arguments for plugin constructor
            **kwargs: Keyword arguments for plugin constructor

        Returns:
            Instantiated plugin if successful, None otherwise
        """
        plugin_class = self.get_plugin_class(name)
        if plugin_class:
            try:
                return plugin_class(*args, **kwargs)
            except Exception as e:
                print(f"Error instantiating plugin {name}: {e}")
        return None
