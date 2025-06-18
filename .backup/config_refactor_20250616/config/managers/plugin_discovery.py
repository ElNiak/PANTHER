"""Plugin discovery and metadata extraction functionality."""

import importlib
import inspect
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from panther.core.exceptions.error_handler_mixin import ErrorHandlerMixin
from panther.plugins.plugin_interface import IPlugin


class PluginMetadata:
    """Container for plugin metadata."""

    def __init__(self, name: str, plugin_type: str, path: Path):
        """Initialize plugin metadata.

        Args:
            name: Plugin name
            plugin_type: Type of plugin
            path: Path to plugin directory
        """
        self.name = name
        self.plugin_type = plugin_type
        self.path = path
        self.module_name = None
        self.class_name = None
        self.version = "unknown"
        self.description = ""
        self.author = ""
        self.dependencies = []
        self.supported_protocols = []
        self.capabilities = []
        self.external_dependencies = []
        self.config_schema = None
        self.is_valid = False
        self.errors = []
        self.warnings = []

    def to_dict(self) -> Dict[str, Any]:
        """Convert metadata to dictionary.

        Returns:
            Dictionary representation of metadata
        """
        return {
            "name": self.name,
            "plugin_type": self.plugin_type,
            "path": str(self.path),
            "module_name": self.module_name,
            "class_name": self.class_name,
            "version": self.version,
            "description": self.description,
            "author": self.author,
            "dependencies": self.dependencies,
            "supported_protocols": self.supported_protocols,
            "capabilities": self.capabilities,
            "external_dependencies": self.external_dependencies,
            "config_schema": self.config_schema,
            "is_valid": self.is_valid,
            "errors": self.errors,
            "warnings": self.warnings,
        }

    def add_error(self, message: str) -> None:
        """Add an error message.

        Args:
            message: Error message
        """
        self.errors.append(message)
        self.is_valid = False

    def add_warning(self, message: str) -> None:
        """Add a warning message.

        Args:
            message: Warning message
        """
        self.warnings.append(message)


class PluginDiscovery(ErrorHandlerMixin):
    """Handles discovery and metadata extraction for plugins."""

    def __init__(self, plugins_base_dir: Path):
        """Initialize plugin discovery.

        Args:
            plugins_base_dir: Base directory containing all plugins
        """
        super().__init__()
        self.plugins_base_dir = plugins_base_dir
        self.discovered_plugins: Dict[str, PluginMetadata] = {}
        self.plugin_cache_file = plugins_base_dir / ".plugin_cache.json"

    def discover_all_plugins(
        self, force_refresh: bool = False
    ) -> Dict[str, PluginMetadata]:
        """Discover all plugins in the plugins directory.

        Args:
            force_refresh: Whether to force a fresh discovery

        Returns:
            Dictionary mapping plugin names to metadata
        """
        if not force_refresh and self._load_from_cache():
            self.logger.info(
                f"Loaded {len(self.discovered_plugins)} plugins from cache"
            )
            return self.discovered_plugins

        self.logger.info("Discovering plugins...")

        # Discover different types of plugins
        self._discover_service_plugins()
        self._discover_environment_plugins()
        self._discover_protocol_plugins()

        # Save to cache
        self._save_to_cache()

        self.logger.info(f"Discovered {len(self.discovered_plugins)} plugins")
        return self.discovered_plugins

    def discover_plugins_by_type(self, plugin_type: str) -> Dict[str, PluginMetadata]:
        """Discover plugins of a specific type.

        Args:
            plugin_type: Type of plugins to discover

        Returns:
            Dictionary mapping plugin names to metadata
        """
        plugins = {}

        if plugin_type == "service":
            plugins.update(self._discover_service_plugins())
        elif plugin_type == "environment":
            plugins.update(self._discover_environment_plugins())
        elif plugin_type == "protocol":
            plugins.update(self._discover_protocol_plugins())
        else:
            self.logger.warning(f"Unknown plugin type: {plugin_type}")

        return plugins

    def get_plugin_metadata(self, plugin_name: str) -> Optional[PluginMetadata]:
        """Get metadata for a specific plugin.

        Args:
            plugin_name: Name of the plugin

        Returns:
            Plugin metadata if found, None otherwise
        """
        return self.discovered_plugins.get(plugin_name)

    def validate_plugin(self, plugin_path: Path) -> PluginMetadata:
        """Validate a single plugin and extract metadata.

        Args:
            plugin_path: Path to plugin directory

        Returns:
            Plugin metadata with validation results
        """
        plugin_name = plugin_path.name
        plugin_type = self._determine_plugin_type(plugin_path)

        metadata = PluginMetadata(plugin_name, plugin_type, plugin_path)

        try:
            # Check if plugin directory contains required files
            if not self._has_required_files(plugin_path, metadata):
                return metadata

            # Extract metadata from plugin module
            self._extract_module_metadata(plugin_path, metadata)

            # Validate plugin class
            self._validate_plugin_class(plugin_path, metadata)

            # Extract configuration schema if available
            self._extract_config_schema(plugin_path, metadata)

            # Mark as valid if no errors
            if not metadata.errors:
                metadata.is_valid = True

        except Exception as e:
            metadata.add_error(f"Validation failed: {str(e)}")

        return metadata

    def _discover_service_plugins(self) -> Dict[str, PluginMetadata]:
        """Discover service plugins (IUT and testers)."""
        plugins = {}
        services_dir = self.plugins_base_dir / "services"

        if not services_dir.exists():
            return plugins

        # Discover IUT plugins
        iut_dir = services_dir / "iut"
        if iut_dir.exists():
            plugins.update(self._discover_nested_plugins(iut_dir, "iut"))

        # Discover tester plugins
        testers_dir = services_dir / "testers"
        if testers_dir.exists():
            plugins.update(self._discover_nested_plugins(testers_dir, "tester"))

        return plugins

    def _discover_environment_plugins(self) -> Dict[str, PluginMetadata]:
        """Discover environment plugins."""
        plugins = {}
        environments_dir = self.plugins_base_dir / "environments"

        if not environments_dir.exists():
            return plugins

        # Discover network environment plugins
        network_dir = environments_dir / "network_environment"
        if network_dir.exists():
            plugins.update(
                self._discover_flat_plugins(network_dir, "network_environment")
            )

        # Discover execution environment plugins
        execution_dir = environments_dir / "execution_environment"
        if execution_dir.exists():
            plugins.update(
                self._discover_flat_plugins(execution_dir, "execution_environment")
            )

        return plugins

    def _discover_protocol_plugins(self) -> Dict[str, PluginMetadata]:
        """Discover protocol plugins."""
        plugins = {}
        protocols_dir = self.plugins_base_dir / "protocols"

        if protocols_dir.exists():
            plugins.update(self._discover_flat_plugins(protocols_dir, "protocol"))

        return plugins

    def _discover_nested_plugins(
        self, base_dir: Path, plugin_type: str
    ) -> Dict[str, PluginMetadata]:
        """Discover plugins in nested directory structure (protocol/implementation)."""
        plugins = {}

        for protocol_dir in base_dir.iterdir():
            if not protocol_dir.is_dir() or protocol_dir.name.startswith("_"):
                continue

            for plugin_dir in protocol_dir.iterdir():
                if not plugin_dir.is_dir() or plugin_dir.name.startswith("_"):
                    continue

                plugin_name = f"{protocol_dir.name}/{plugin_dir.name}"
                metadata = self.validate_plugin(plugin_dir)
                metadata.plugin_type = plugin_type

                plugins[plugin_name] = metadata
                self.discovered_plugins[plugin_name] = metadata

        return plugins

    def _discover_flat_plugins(
        self, base_dir: Path, plugin_type: str
    ) -> Dict[str, PluginMetadata]:
        """Discover plugins in flat directory structure."""
        plugins = {}

        for plugin_dir in base_dir.iterdir():
            if not plugin_dir.is_dir() or plugin_dir.name.startswith("_"):
                continue

            plugin_name = plugin_dir.name
            metadata = self.validate_plugin(plugin_dir)
            metadata.plugin_type = plugin_type

            plugins[plugin_name] = metadata
            self.discovered_plugins[plugin_name] = metadata

        return plugins

    def _determine_plugin_type(self, plugin_path: Path) -> str:
        """Determine plugin type from path."""
        path_parts = plugin_path.parts

        if "services" in path_parts:
            if "iut" in path_parts:
                return "iut"
            elif "testers" in path_parts:
                return "tester"
            else:
                return "service"
        elif "environments" in path_parts:
            if "network_environment" in path_parts:
                return "network_environment"
            elif "execution_environment" in path_parts:
                return "execution_environment"
            else:
                return "environment"
        elif "protocols" in path_parts:
            return "protocol"
        else:
            return "unknown"

    def _has_required_files(self, plugin_path: Path, metadata: PluginMetadata) -> bool:
        """Check if plugin has required files."""
        required_files = ["__init__.py"]

        for filename in required_files:
            file_path = plugin_path / filename
            if not file_path.exists():
                metadata.add_error(f"Missing required file: {filename}")
                return False

        return True

    def _extract_module_metadata(
        self, plugin_path: Path, metadata: PluginMetadata
    ) -> None:
        """Extract metadata from plugin module."""
        try:
            # Look for Python files that might contain the plugin class
            python_files = list(plugin_path.glob("*.py"))
            main_file = None

            # Try to find the main plugin file
            for py_file in python_files:
                if py_file.name == f"{plugin_path.name}.py":
                    main_file = py_file
                    break
                elif py_file.name == "__init__.py":
                    main_file = py_file

            if not main_file:
                main_file = python_files[0] if python_files else None

            if main_file:
                self._extract_metadata_from_file(main_file, metadata)
            else:
                metadata.add_error("No Python files found in plugin directory")

        except Exception as e:
            metadata.add_error(f"Failed to extract module metadata: {str(e)}")

    def _extract_metadata_from_file(
        self, file_path: Path, metadata: PluginMetadata
    ) -> None:
        """Extract metadata from a Python file."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Look for register_plugin decorator
            import re

            decorator_pattern = r"@register_plugin\((.*?)\)"
            matches = re.findall(decorator_pattern, content, re.DOTALL)

            if matches:
                self._parse_register_plugin_decorator(matches[0], metadata)

            # Look for class definitions
            class_pattern = r"class\s+(\w+)\s*\([^)]*\):"
            class_matches = re.findall(class_pattern, content)

            if class_matches:
                # Find the most likely plugin class
                for class_name in class_matches:
                    if any(
                        suffix in class_name
                        for suffix in ["Manager", "Plugin", "Environment"]
                    ):
                        metadata.class_name = class_name
                        break

                if not metadata.class_name and class_matches:
                    metadata.class_name = class_matches[0]

        except Exception as e:
            metadata.add_error(f"Failed to parse file {file_path}: {str(e)}")

    def _parse_register_plugin_decorator(
        self, decorator_content: str, metadata: PluginMetadata
    ) -> None:
        """Parse register_plugin decorator content."""
        try:
            # Remove comments and clean up
            lines = [line.strip() for line in decorator_content.split("\n")]
            content = " ".join(lines)

            # Extract key-value pairs
            import re

            # Extract string values
            for key in ["name", "version", "description", "author"]:
                pattern = rf'{key}\s*=\s*["\']([^"\']*)["\']'
                match = re.search(pattern, content)
                if match:
                    setattr(metadata, key, match.group(1))

            # Extract list values
            for key in [
                "dependencies",
                "supported_protocols",
                "capabilities",
                "external_dependencies",
            ]:
                pattern = rf"{key}\s*=\s*\[(.*?)\]"
                match = re.search(pattern, content, re.DOTALL)
                if match:
                    list_content = match.group(1)
                    # Extract quoted strings from the list
                    string_pattern = r'["\']([^"\']*)["\']'
                    values = re.findall(string_pattern, list_content)
                    setattr(metadata, key, values)

        except Exception as e:
            metadata.add_warning(f"Failed to parse decorator: {str(e)}")

    def _validate_plugin_class(
        self, plugin_path: Path, metadata: PluginMetadata
    ) -> None:
        """Validate that the plugin class follows expected interface."""
        if not metadata.class_name:
            metadata.add_warning("No plugin class found")
            return

        try:
            # Try to import and inspect the class
            # This is a simplified validation - full validation would require
            # loading the module, which might have dependencies

            # Check if it looks like a proper plugin class name
            if not metadata.class_name.endswith(("Manager", "Plugin", "Environment")):
                metadata.add_warning(
                    f"Plugin class name '{metadata.class_name}' doesn't follow naming convention"
                )

        except Exception as e:
            metadata.add_warning(f"Could not validate plugin class: {str(e)}")

    def _extract_config_schema(
        self, plugin_path: Path, metadata: PluginMetadata
    ) -> None:
        """Extract configuration schema if available."""
        schema_file = plugin_path / "config_schema.py"
        if schema_file.exists():
            try:
                # Try to extract schema information
                with open(schema_file, "r", encoding="utf-8") as f:
                    content = f.read()

                # Look for Pydantic model classes
                import re

                model_pattern = r"class\s+(\w+)\s*\([^)]*BaseModel[^)]*\):"
                models = re.findall(model_pattern, content)

                if models:
                    metadata.config_schema = {
                        "models": models,
                        "file": "config_schema.py",
                    }

            except Exception as e:
                metadata.add_warning(f"Could not extract config schema: {str(e)}")

    def _load_from_cache(self) -> bool:
        """Load plugin metadata from cache file."""
        if not self.plugin_cache_file.exists():
            return False

        try:
            with open(self.plugin_cache_file, "r", encoding="utf-8") as f:
                cache_data = json.load(f)

            # Check if cache is still valid (simple timestamp check)
            cache_timestamp = cache_data.get("timestamp", 0)
            current_timestamp = self.plugins_base_dir.stat().st_mtime

            if cache_timestamp < current_timestamp:
                return False

            # Load plugins from cache
            for plugin_name, plugin_data in cache_data.get("plugins", {}).items():
                metadata = PluginMetadata(
                    plugin_data["name"],
                    plugin_data["plugin_type"],
                    Path(plugin_data["path"]),
                )

                # Restore metadata attributes
                for key, value in plugin_data.items():
                    if hasattr(metadata, key):
                        setattr(metadata, key, value)

                self.discovered_plugins[plugin_name] = metadata

            return True

        except Exception as e:
            self.logger.warning(f"Failed to load plugin cache: {str(e)}")
            return False

    def _save_to_cache(self) -> None:
        """Save plugin metadata to cache file."""
        try:
            cache_data = {
                "timestamp": self.plugins_base_dir.stat().st_mtime,
                "plugins": {
                    name: metadata.to_dict()
                    for name, metadata in self.discovered_plugins.items()
                },
            }

            with open(self.plugin_cache_file, "w", encoding="utf-8") as f:
                json.dump(cache_data, f, indent=2)

            self.logger.debug(f"Saved plugin cache to {self.plugin_cache_file}")

        except Exception as e:
            self.logger.warning(f"Failed to save plugin cache: {str(e)}")

    def get_plugins_by_type(self, plugin_type: str) -> Dict[str, PluginMetadata]:
        """Get all plugins of a specific type.

        Args:
            plugin_type: Type of plugins to retrieve

        Returns:
            Dictionary of plugins of the specified type
        """
        return {
            name: metadata
            for name, metadata in self.discovered_plugins.items()
            if metadata.plugin_type == plugin_type
        }

    def get_plugins_by_protocol(self, protocol: str) -> Dict[str, PluginMetadata]:
        """Get all plugins that support a specific protocol.

        Args:
            protocol: Protocol name

        Returns:
            Dictionary of plugins supporting the protocol
        """
        return {
            name: metadata
            for name, metadata in self.discovered_plugins.items()
            if protocol in metadata.supported_protocols
        }

    def get_plugin_summary(self) -> Dict[str, Any]:
        """Get a summary of discovered plugins.

        Returns:
            Summary dictionary with counts and statistics
        """
        total_plugins = len(self.discovered_plugins)
        valid_plugins = sum(1 for m in self.discovered_plugins.values() if m.is_valid)

        by_type = {}
        for metadata in self.discovered_plugins.values():
            plugin_type = metadata.plugin_type
            if plugin_type not in by_type:
                by_type[plugin_type] = 0
            by_type[plugin_type] += 1

        return {
            "total_plugins": total_plugins,
            "valid_plugins": valid_plugins,
            "invalid_plugins": total_plugins - valid_plugins,
            "by_type": by_type,
            "supported_protocols": list(
                set(
                    protocol
                    for metadata in self.discovered_plugins.values()
                    for protocol in metadata.supported_protocols
                )
            ),
        }
