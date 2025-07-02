"""
Plugin Discovery Module

This module provides plugin discovery functionality for the PANTHER framework,
using the decorator registry to identify available plugins.
"""

import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from panther.core.utils.logging_mixin import LoggerMixin
from panther.plugins.core.structures.plugin_manifest import PluginManifest
from panther.plugins.core.structures.plugin_metadata import PluginMetadata


class PluginDiscovery(LoggerMixin):
    """
    Discovers plugins in the PANTHER framework using the decorator registry.

    This class provides a clean interface for plugin discovery, following
    the Single Responsibility Principle by focusing only on discovery logic.
    """

    def __init__(
        self,
        plugin_directories: Optional[List[str]] = None,
        enable_cache: bool = True,
        cache_ttl: int = 3600,
    ):
        """Initialize the plugin discovery system.

        Args:
            plugin_directories: Optional list of directories to scan for plugins
            enable_cache: Enable version and schema caching
            cache_ttl: Cache time-to-live in seconds
        """
        super().__init__()
        self.discovered_plugins: Dict[str, PluginMetadata] = {}
        self.plugin_directories = plugin_directories or self._get_default_directories()

        # Cache configuration
        self.enable_cache = enable_cache
        self.cache_ttl = cache_ttl
        self._cache_timestamp = 0
        self._version_cache: Dict[str, List[str]] = {}
        self._schema_cache: Dict[str, Dict[str, Any]] = {}

    def discover_plugins(
        self,
        force_refresh: bool = False,
        external_plugin_paths: Optional[List[str]] = None,
    ) -> Dict[str, PluginMetadata]:
        """
        Discover all plugins from the decorator registry.

        Args:
            force_refresh: If True, refresh the plugin list
            external_plugin_paths: Additional paths to scan for external plugins

        Returns:
            Dictionary mapping plugin IDs to metadata
        """
        from panther.plugins.core.plugin_decorators import get_decorated_plugins

        if force_refresh or not self.discovered_plugins:
            self.discovered_plugins.clear()

            # First, scan and import core plugin modules
            self.logger.debug("Starting core plugin discovery")
            self.scan_and_import_plugins()

            # Then scan external plugin directories if provided
            if external_plugin_paths:
                self.logger.debug(
                    f"Scanning external plugin paths: {external_plugin_paths}"
                )
                self.scan_external_plugins(external_plugin_paths)

            # Get all plugins from decorator registry
            decorated_plugins = get_decorated_plugins()
            self.logger.debug(
                f"Found {len(decorated_plugins)} plugins in decorator registry"
            )

            for plugin_id, (plugin_class, manifest) in decorated_plugins.items():
                self.logger.debug(f"Processing plugin {plugin_id}")
                metadata = self._convert_manifest_to_metadata(manifest)
                if metadata:
                    self.discovered_plugins[metadata.name] = metadata
                    self.logger.debug(
                        f"Discovered plugin: {metadata.name} " f"({metadata.type})"
                    )

                    # Discover and register version configurations for this plugin
                    self._discover_plugin_versions(metadata)
                else:
                    self.logger.warning(f"Failed to convert manifest for {plugin_id}")

            self.logger.info(
                f"Discovered {len(self.discovered_plugins)} plugins "
                f"from decorator registry"
            )

        return self.discovered_plugins.copy()

    def _convert_manifest_to_metadata(
        self, manifest: PluginManifest
    ) -> Optional[PluginMetadata]:
        """Convert PluginManifest from decorator to PluginMetadata."""
        try:
            # Convert dependencies to list of strings
            deps = []
            if manifest.dependencies:
                for dep in manifest.dependencies:
                    if hasattr(dep, "name"):
                        deps.append(dep.name)
                    else:
                        deps.append(str(dep))

            return PluginMetadata(
                name=manifest.name,
                version=manifest.version,
                type=(
                    manifest.type.value
                    if hasattr(manifest.type, "value")
                    else str(manifest.type)
                ),
                supported_protocols=manifest.supported_protocols or [],
                path=Path(manifest.file_path) if manifest.file_path else None,
                dependencies=deps,
                description=manifest.description or "",
                author=manifest.author or "",
                capabilities=manifest.capabilities or [],
                runtime_mode=manifest.runtime_mode,  # Include runtime_mode from decorator
                external_dependencies=manifest.external_dependencies or [],
                tags=manifest.tags or [],
            )
        except Exception as e:
            self.logger.error(f"Failed to convert manifest to metadata: {e}")
            return None

    def get_plugins_by_type(self, plugin_type: str) -> List[PluginMetadata]:
        """Get all discovered plugins of a specific type."""
        return [
            metadata
            for metadata in self.discovered_plugins.values()
            if metadata.type == plugin_type
        ]

    def get_plugin(self, plugin_name: str) -> Optional[PluginMetadata]:
        """Get metadata for a specific plugin by name."""
        return self.discovered_plugins.get(plugin_name)

    def clear_cache(self) -> None:
        """Clear the discovery cache."""
        self.discovered_plugins.clear()
        self.logger.debug("Cleared plugin discovery cache")

    def _get_default_directories(self) -> List[str]:
        """Get default plugin directories."""
        base_path = Path(__file__).parent.parent
        return [
            str(
                base_path / "protocols"
            ),  # Add protocols directory for protocol plugin discovery
            str(base_path / "services" / "iut"),
            str(base_path / "services" / "testers"),
            str(base_path / "environments" / "network_environment"),
            str(base_path / "environments" / "execution_environment"),
        ]

    def scan_and_import_plugins(self) -> None:
        """
        Optimized plugin scanning using naming conventions.

        Instead of walking all files, directly check for expected plugin patterns:
        plugin_directory/plugin_name/plugin_name.py

        This method is much faster as it only checks expected locations rather
        than scanning hundreds of files.
        """
        self.logger.debug(f"Scanning of plugin directories: {self.plugin_directories}")
        for directory in self.plugin_directories:
            directory_path = Path(directory)
            if not directory_path.exists():
                self.logger.debug(f"Directory does not exist: {directory_path}")
                continue
            self.logger.debug(f"Scanning directory: {directory_path}")

            # Check if this is already a specific plugin type directory
            dir_name = directory_path.name

            # Handle different directory structures with optimized scanning
            if dir_name in ["testers", "network_environment", "execution_environment"]:
                # These are already plugin type directories, scan them directly
                self.logger.debug(f"Scanning plugin type directory: {directory_path}")
                self._scan_plugin_type_directory(directory_path)
            elif dir_name == "iut":
                # IUT directory contains protocol subdirectories
                self.logger.debug(f"Scanning IUT directory: {directory_path}")
                self._scan_nested_plugin_directory(directory_path)
            elif dir_name == "protocols":
                # This is the protocols directory itself
                self._scan_nested_plugin_directory(directory_path)
            elif dir_name == "services":
                # This is the services directory itself
                self.logger.debug(f"Processing services directory: {directory_path}")
                # Import IUT plugins
                iut_dir = directory_path / "iut"
                if iut_dir.exists():
                    self.logger.debug(f"Scanning IUT plugins from: {iut_dir}")
                    self._scan_nested_plugin_directory(iut_dir)

                # Import tester plugins
                testers_dir = directory_path / "testers"
                if testers_dir.exists():
                    self.logger.debug(f"Scanning tester plugins from: {testers_dir}")
                    self._scan_plugin_type_directory(testers_dir)
                else:
                    self.logger.warning(f"Testers directory not found: {testers_dir}")
            elif dir_name == "environments":
                # This is the environments directory itself
                self._scan_nested_plugin_directory(directory_path)
            else:
                # This is a base plugins directory, scan for subdirectories
                # Import protocol plugins
                protocols_dir = directory_path / "protocols"
                if protocols_dir.exists():
                    self._scan_plugin_type_directory(protocols_dir)

                # Import service plugins
                services_dir = directory_path / "services"
                if services_dir.exists():
                    # Import IUT plugins
                    iut_dir = services_dir / "iut"
                    if iut_dir.exists():
                        self._scan_nested_plugin_directory(iut_dir)

                    # Import tester plugins
                    testers_dir = services_dir / "testers"
                    if testers_dir.exists():
                        self._scan_plugin_type_directory(testers_dir)

                # Import environment plugins
                environments_dir = directory_path / "environments"
                if environments_dir.exists():
                    self._scan_nested_plugin_directory(environments_dir)

    def scan_external_plugins(self, external_plugin_paths: List[str]) -> None:
        """
        Scan external plugin directories.

        External plugins should follow the same naming convention as core plugins:
        plugin_directory/plugin_name/plugin_name.py

        Args:
            external_plugin_paths: List of external plugin directory paths
        """
        self.logger.debug(f"Scanning external plugin paths: {external_plugin_paths}")
        for external_path in external_plugin_paths:
            external_path_obj = Path(external_path)
            if not external_path_obj.exists():
                self.logger.warning(
                    f"External plugin path does not exist: {external_path}"
                )
                continue

            self.logger.debug(f"Scanning external plugin directory: {external_path}")
            if external_path_obj.is_file() and external_path_obj.suffix == ".py":
                # Direct Python file
                self._import_module_file(external_path_obj)
            elif external_path_obj.is_dir():
                # Check if it's a plugin directory (contains plugin_name.py)
                plugin_file = external_path_obj / f"{external_path_obj.name}.py"
                if plugin_file.exists():
                    # This is a plugin directory
                    self._import_module_file(plugin_file)
                else:
                    # This is a directory containing plugins
                    self._scan_plugin_type_directory(external_path_obj)

    def _scan_plugin_type_directory(self, directory: Path):
        """
        Optimized scan for plugins in a plugin type directory.

        Directly checks for plugin_name/plugin_name.py pattern instead of
        walking all files.

        Args:
            directory: Plugin type directory to scan
        """
        self.logger.debug(f"Optimized scan of plugin type directory: {directory}")
        try:
            for plugin_dir in directory.iterdir():
                if not plugin_dir.is_dir() or plugin_dir.name.startswith(("_", ".")):
                    continue

                # Skip known non-plugin directories
                if plugin_dir.name in [
                    "mixins",
                    "utils",
                    "__pycache__",
                    "tests",
                    "base",
                ]:
                    continue

                # Check for plugin_name.py file
                plugin_file = plugin_dir / f"{plugin_dir.name}.py"
                if plugin_file.exists():
                    self.logger.debug(f"Found plugin: {plugin_file}")
                    self._import_module_file(plugin_file)
                else:
                    self.logger.debug(f"No plugin file found at: {plugin_file}")

        except Exception as e:
            self.logger.debug(f"Error scanning plugin type directory {directory}: {e}")

    def _scan_nested_plugin_directory(self, directory: Path):
        """
        Scan nested plugin directories (e.g., services/iut/quic/*).

        Args:
            directory: Directory containing nested plugin structures
        """
        self.logger.debug(f"Scanning nested plugin directory: {directory}")
        try:
            for protocol_or_type_dir in directory.iterdir():
                if (
                    not protocol_or_type_dir.is_dir()
                    or protocol_or_type_dir.name.startswith(("_", "."))
                ):
                    continue

                # Skip known non-plugin directories
                if protocol_or_type_dir.name in [
                    "mixins",
                    "utils",
                    "__pycache__",
                    "tests",
                    "base",
                ]:
                    continue

                # This could be a protocol directory (like 'quic') or direct plugin directory
                self._scan_plugin_type_directory(protocol_or_type_dir)

        except Exception as e:
            self.logger.debug(f"Error scanning nested directory {directory}: {e}")

    def _import_module_file(self, file_path: Path):
        """
        Import a single Python module file.

        Args:
            file_path: Path to the Python file
        """
        try:
            # Generate a unique module name based on the file path
            # Convert to relative path from panther module
            try:
                relative_path = file_path.relative_to(
                    Path(__file__).parent.parent.parent
                )
                module_name = "panther." + str(relative_path).replace("/", ".").replace(
                    "\\", "."
                ).replace(".py", "")
            except ValueError:
                # If not under panther, use absolute path but remove leading slash
                module_name = (
                    str(file_path)
                    .replace("/", ".")
                    .replace("\\", ".")
                    .replace(".py", "")
                    .lstrip(".")
                )

            # Use the plugin loader utils to import the module
            from panther.plugins.core.plugin_loader_utils import PluginManagerUtils

            PluginManagerUtils.load_module_from_file(file_path, module_name)
            self.logger.info(f"Imported plugin module: {file_path}")

        except Exception as e:
            # Don't fail on import errors - some files may not be plugins
            self.logger.warning(f"Could not import {file_path}: {e}")
            import traceback

            self.logger.debug(f"Traceback: {traceback.format_exc()}")

    def _discover_plugin_versions(self, metadata: PluginMetadata):
        """Discover and register version configurations for a plugin."""
        if not metadata.path or not metadata.supported_protocols:
            return

        from pathlib import Path

        from panther.plugins.core.plugin_decorators import register_version_config
        from panther.plugins.core.version_loader import VersionLoader

        plugin_path = Path(metadata.path)
        if plugin_path.is_file():
            plugin_path = plugin_path.parent

        version_loader = VersionLoader()

        for protocol in metadata.supported_protocols:
            try:
                versions = version_loader.discover_and_load_versions(
                    metadata.name, plugin_path, protocol
                )
                for version_name, config in versions.items():
                    register_version_config(metadata.name, version_name, config)
                    self.logger.debug(
                        f"Registered version config: {metadata.name}:{version_name}"
                    )
            except Exception as e:
                self.logger.warning(
                    f"Failed to load versions for {metadata.name}:{protocol}: {e}"
                )

    def _is_cache_valid(self) -> bool:
        """Check if cache is still valid."""
        if not self.enable_cache:
            return False
        return time.time() - self._cache_timestamp < self.cache_ttl

    def discover_protocol_versions(
        self, protocol: Optional[str] = None
    ) -> Dict[str, List[str]]:
        """
        Discover available protocol versions.

        Args:
            protocol: Optional protocol to filter by

        Returns:
            Dictionary mapping protocols to version lists
        """
        cache_key = protocol or "all"

        if cache_key in self._version_cache and self._is_cache_valid():
            return (
                {protocol: self._version_cache[cache_key]}
                if protocol
                else self._version_cache.copy()
            )

        self.logger.info(f"Discovering versions for protocol: {protocol or 'all'}")

        versions = {}

        # Scan protocol directories and service implementations
        for directory in self.plugin_directories:
            directory_path = Path(directory)

            # Check protocols directory
            protocols_dir = directory_path / "protocols"
            if protocols_dir.exists():
                for category in ["client_server", "peer_to_peer"]:
                    category_dir = protocols_dir / category
                    if category_dir.exists():
                        for proto_dir in category_dir.iterdir():
                            if not proto_dir.is_dir():
                                continue

                            proto_name = proto_dir.name
                            if protocol and proto_name != protocol:
                                continue

                            proto_versions = self._discover_versions_in_directory(
                                proto_dir
                            )
                            if proto_versions:
                                versions[proto_name] = proto_versions

            # Check service implementations
            services_dir = directory_path / "services"
            if services_dir.exists():
                for impl_type in ["iut", "testers"]:
                    type_dir = services_dir / impl_type
                    if type_dir.exists():
                        for proto_dir in type_dir.iterdir():
                            if not proto_dir.is_dir():
                                continue

                            proto_name = proto_dir.name
                            if protocol and proto_name != protocol:
                                continue

                            # Check each implementation
                            for impl_dir in proto_dir.iterdir():
                                if impl_dir.is_dir():
                                    impl_versions = (
                                        self._discover_versions_in_directory(impl_dir)
                                    )
                                    if impl_versions:
                                        if proto_name not in versions:
                                            versions[proto_name] = []
                                        versions[proto_name].extend(impl_versions)

        # Deduplicate and sort
        for proto in versions:
            versions[proto] = sorted(list(set(versions[proto])))
            self._version_cache[proto] = versions[proto]

        if not protocol:
            self._version_cache["all"] = versions

        return versions

    def _discover_versions_in_directory(self, directory: Path) -> List[str]:
        """Discover version files in a directory."""
        versions = []

        # Look for versions directory
        versions_dir = directory / "versions"
        if versions_dir.exists():
            for item in versions_dir.iterdir():
                if item.is_file() and item.suffix in [".yaml", ".yml", ".json"]:
                    versions.append(item.stem)
                elif item.is_dir():
                    versions.append(item.name)

        # Look for version files in config directory
        config_dir = directory / "config"
        if config_dir.exists():
            for item in config_dir.glob("version_*.y*ml"):
                version = item.stem.replace("version_", "")
                versions.append(version)

        # Check for hardcoded versions in config_schema.py
        config_schema = directory / "config_schema.py"
        if config_schema.exists() and "quic" in str(directory):
            # Add common QUIC versions if not found
            default_versions = ["rfc9000", "draft-29"]
            for v in default_versions:
                if v not in versions:
                    versions.append(v)

        return versions

    def discover_plugin_schemas(self) -> Dict[str, Dict[str, Any]]:
        """
        Discover all plugin configuration schemas.

        Returns:
            Dictionary mapping plugin names to schema information
        """
        if self._schema_cache and self._is_cache_valid():
            return self._schema_cache.copy()

        self.logger.info("Discovering plugin schemas")

        schemas = {}
        plugins = self.discover_plugins()

        for plugin_name, plugin in plugins.items():
            if (
                hasattr(plugin, "config_schema_path")
                and plugin.config_schema_path
                and plugin.config_schema_path.exists()
            ):
                try:
                    schema_info = self._load_schema(plugin.config_schema_path)
                    if schema_info:
                        schemas[plugin_name] = {
                            "schema": schema_info,
                            "path": str(plugin.config_schema_path),
                            "type": plugin.type,
                            "protocol": getattr(plugin, "protocol", None),
                        }
                except Exception as e:
                    self.logger.warning(f"Failed to load schema for {plugin_name}: {e}")

        self._schema_cache = schemas
        return schemas.copy()

    def _load_schema(self, schema_path: Path) -> Optional[Dict[str, Any]]:
        """Load schema from file."""
        try:
            with open(schema_path) as f:
                if schema_path.suffix.lower() in [".yaml", ".yml"]:
                    import yaml

                    return yaml.safe_load(f)
                elif schema_path.suffix.lower() == ".json":
                    import json

                    return json.load(f)
                elif schema_path.suffix.lower() == ".py":
                    # For Python schema files - simplified extraction
                    return {"type": "python_schema", "path": str(schema_path)}
        except Exception:
            pass
        return None
