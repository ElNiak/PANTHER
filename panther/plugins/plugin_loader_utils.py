"""
Plugin Loader Utilities

This module provides utilities for loading plugins dynamically, reducing duplication
across plugin loading operations in PANTHER.
"""

from __future__ import annotations

import importlib.util
from collections.abc import Callable
from pathlib import Path
from typing import Any, List, Optional, TypeVar

from panther.core.utils.logging_mixin import LoggerMixin

T = TypeVar("T")


class PluginManagerUtils(LoggerMixin):
    """

    Utility class for common plugin loading operations.

    Reduces duplication in dynamic module loading and class instantiation.
    """

    @classmethod
    def load_module_from_file(
        cls, file_path: Path, module_name: Optional[str] = None
    ) -> Any:
        """
        Load a Python module from a file path.

        Args:
            file_path: Path to the Python file
            module_name: Optional module name (defaults to file stem)

        Returns:
            The loaded module

        Raises:
            ImportError: If module cannot be loaded
        """
        if not file_path.exists():
            raise ImportError(f"Module file not found: {file_path}")

        if module_name is None:
            module_name = file_path.stem

        spec = importlib.util.spec_from_file_location(module_name, file_path)
        if spec is None or spec.loader is None:
            raise ImportError(f"Could not find module at {file_path}")

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        return module

    @classmethod
    def get_class_from_module(
        cls, module: Any, class_name: str, base_class: Optional[type[T]] = None
    ) -> type[T]:
        """
        Get a class from a module with optional type checking.

        Args:
            module: The module to search in
            class_name: Name of the class to find
            base_class: Optional base class for type checking

        Returns:
            The class object

        Raises:
            AttributeError: If class not found
            TypeError: If class doesn't inherit from base_class
        """
        manager_class = getattr(module, class_name, None)
        if manager_class is None:
            raise AttributeError(
                f"Could not find class {class_name} in module {module.__name__}"
            )

        if base_class and not issubclass(manager_class, base_class):
            raise TypeError(
                f"Class {class_name} must inherit from {base_class.__name__}"
            )

        return manager_class

    @classmethod
    def load_plugin_class(
        cls,
        plugin_path: Path,
        class_suffix: str,
        base_class: Optional[type[T]] = None,
        name_transform: Optional[Callable] = None,
    ) -> type[T]:
        """
        Load a plugin class using standard naming conventions.

        Args:
            plugin_path: Path to plugin directory or file
            class_suffix: Suffix for the class name (e.g., "ServiceManager")
            base_class: Optional base class for validation
            name_transform: Optional function to transform plugin name to class name

        Returns:
            The loaded plugin class
        """
        # Determine the plugin name and file path
        if plugin_path.is_dir():
            plugin_name = plugin_path.name
            file_path = plugin_path / f"{plugin_name}.py"
        else:
            plugin_name = plugin_path.stem
            file_path = plugin_path

        # Load the module
        module = cls.load_module_from_file(file_path, plugin_name)

        # Determine class name
        if name_transform:
            class_name = name_transform(plugin_name) + class_suffix
        else:
            # Default transformation: snake_case to PascalCase
            class_name = "".join(word.capitalize() for word in plugin_name.split("_"))
            class_name += class_suffix

        # Get the class
        return cls.get_class_from_module(module, class_name, base_class)

    @classmethod
    def instantiate_plugin(cls, plugin_class: type[T], *args, **kwargs) -> T:
        """
        Instantiate a plugin class with error handling.

        Args:
            plugin_class: The plugin class to instantiate
            *args: Positional arguments for constructor
            **kwargs: Keyword arguments for constructor

        Returns:
            Instance of the plugin

        Raises:
            Exception: If instantiation fails
        """
        try:
            return plugin_class(*args, **kwargs)
        except Exception as e:
            raise Exception(
                f"Failed to instantiate {plugin_class.__name__}: {str(e)}"
            ) from e

    @classmethod
    def discover_plugins(
        cls, base_path: Path, pattern: str = "*.py", exclude: Optional[List[str]] = None
    ) -> List[Path]:
        """
        Discover plugin files in a directory.

        Args:
            base_path: Base directory to search
            pattern: File pattern to match
            exclude: List of filenames to exclude

        Returns:
            List of plugin file paths
        """
        exclude = exclude or ["__init__.py", "__pycache__"]

        plugin_files = []
        for file_path in base_path.glob(pattern):
            if file_path.name not in exclude and file_path.is_file():
                plugin_files.append(file_path)

        return sorted(plugin_files)
