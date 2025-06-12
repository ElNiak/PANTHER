"""
Plugin Catalog System

This module provides plugin discovery, cataloging, and dependency resolution
for the PANTHER plugin ecosystem.
"""

import json
import logging
import os
from pathlib import Path
from typing import Any
import yaml
from collections import defaultdict

from panther.plugins.plugin_manifest import (
    PluginManifest,
    PluginType,
    PluginDependency,
    PluginRegistration,
)


class PluginCatalog:
    """
    Central catalog for plugin discovery, validation, and dependency management.

    This class maintains a registry of all available plugins, handles discovery
    from various sources, and provides dependency resolution capabilities.
    """

    MANIFEST_FILENAMES = ["plugin.yaml", "plugin.yml", "manifest.yaml", "manifest.yml"]
    CACHE_FILENAME = ".plugin_catalog_cache.json"

    def __init__(self, discovery_paths: list[str] | None = None):
        """
        Initialize the plugin catalog.

        Args:
            discovery_paths: List of paths to search for plugins
        """
        self.logger = logging.getLogger("PluginCatalog")
        self.discovery_paths = discovery_paths or []
        self.catalog: dict[str, PluginManifest] = {}
        self.registrations: dict[str, PluginRegistration] = {}
        self._dependency_graph: dict[str, set[str]] = defaultdict(set)

    def add_discovery_path(self, path: str) -> None:
        """Add a new path for plugin discovery."""
        if path not in self.discovery_paths:
            self.discovery_paths.append(path)
            self.logger.debug("Added discovery path: %s", path)

    def scan_plugins(self, use_cache: bool = True) -> dict[str, PluginManifest]:
        """
        Scan all discovery paths for plugins.

        Args:
            use_cache: Whether to use cached catalog if available

        Returns:
            Dictionary mapping plugin IDs to manifests
        """
        # Try to load from cache first
        if use_cache and self._load_cache():
            self.logger.info("Loaded plugin catalog from cache")
            return self.catalog

        self.logger.info("Scanning for plugins in %d paths", len(self.discovery_paths))
        self.catalog.clear()

        for path in self.discovery_paths:
            if not os.path.exists(path):
                self.logger.warning("Discovery path does not exist: %s", path)
                continue

            self._scan_directory(path)

        # Save cache for next time
        self._save_cache()

        self.logger.info("Found %d plugins", len(self.catalog))
        return self.catalog

    def _scan_directory(self, directory: str) -> None:
        """Recursively scan a directory for plugins."""
        path = Path(directory)

        # Look for manifest files in this directory
        for manifest_file in self.MANIFEST_FILENAMES:
            manifest_path = path / manifest_file
            if manifest_path.exists():
                self._load_manifest_file(manifest_path)
                # Continue scanning subdirectories to find nested plugins

        # Always scan subdirectories
        try:
            for item in path.iterdir():
                if item.is_dir() and not item.name.startswith("."):
                    # Skip common non-plugin directories
                    skip_dirs = [
                        "__pycache__",
                        "tests",
                        "test",
                        "docs",
                        "examples",
                        "submodules",
                        "scripts",
                        "bin",
                        "doc",
                        "build",
                        "dist",
                        "extra_vecs",
                        "arm",
                        "src",
                        "utils",
                        "cmake",
                        "contrib",
                        ".git",
                        ".github",
                        "z3",
                        "ivy",
                        "ivy2",
                        "protocol-testing",
                        "micro-ecc",
                        "python",
                    ]
                    if item.name.lower() in skip_dirs:
                        continue
                    self._scan_directory(str(item))
        except PermissionError:
            self.logger.warning("Permission denied accessing: %s", directory)

    def _load_manifest_file(self, manifest_path: Path) -> PluginManifest | None:
        """Load a plugin manifest from a YAML file."""
        try:
            with open(manifest_path) as f:
                data = yaml.safe_load(f)

            # Auto-detect plugin type from directory structure if not specified
            if "type" not in data:
                data["type"] = self._infer_plugin_type(manifest_path)

            # Set file path
            data["file_path"] = str(manifest_path.parent)

            # Create manifest
            manifest = PluginManifest.from_dict(data)

            # Register in catalog
            plugin_id = f"{manifest.type.value}:{manifest.name}"
            self.catalog[plugin_id] = manifest

            self.logger.debug("Loaded plugin manifest: %s v%s", manifest.name, manifest.version)
            return manifest

        except Exception as e:
            self.logger.error("Failed to load manifest from %s: %s", manifest_path, e)
            return None

    def _infer_plugin_type(self, manifest_path: Path) -> str:
        """Infer plugin type from directory structure."""
        path_str = str(manifest_path.parent).lower()

        if "services" in path_str:
            if "iut" in path_str:
                return PluginType.IUT.value
            elif "testers" in path_str:
                return PluginType.TESTER.value
            else:
                return PluginType.SERVICE.value
        elif "environments" in path_str:
            return PluginType.ENVIRONMENT.value
        elif "protocols" in path_str:
            return PluginType.PROTOCOL.value
        elif "observers" in path_str:
            return PluginType.OBSERVER.value
        else:
            return PluginType.SERVICE.value  # Default

    def validate_plugin_config(
        self, plugin_id: str, config: dict[str, Any]
    ) -> tuple[bool, list[str]]:
        """
        Validate plugin configuration against its schema.

        Args:
            plugin_id: Plugin identifier
            config: Configuration to validate

        Returns:
            Tuple of (is_valid, error_messages)
        """
        manifest = self.catalog.get(plugin_id)
        if not manifest:
            return False, [f"Plugin not found: {plugin_id}"]

        errors = []

        # Basic schema validation (can be enhanced with jsonschema)
        if manifest.config_schema:
            for key, expected_type in manifest.config_schema.items():
                if key not in config and key not in manifest.default_config:
                    errors.append(f"Missing required config key: {key}")
                elif key in config:
                    # Simple type checking
                    value = config[key]
                    if not self._check_type(value, expected_type):
                        errors.append(f"Invalid type for {key}: expected {expected_type}")

        return len(errors) == 0, errors

    def _check_type(self, value: Any, expected_type: Any) -> bool:
        """Simple type checking helper."""
        if expected_type == "string":
            return isinstance(value, str)
        elif expected_type == "number":
            return isinstance(value, (int, float))
        elif expected_type == "boolean":
            return isinstance(value, bool)
        elif expected_type == "array":
            return isinstance(value, list)
        elif expected_type == "object":
            return isinstance(value, dict)
        else:
            return True  # Unknown type, allow it

    def resolve_dependencies(self, plugin_ids: list[str]) -> tuple[list[str], list[str]]:
        """
        Resolve dependencies for a set of plugins.

        Args:
            plugin_ids: List of plugin IDs to resolve

        Returns:
            Tuple of (resolved_order, missing_dependencies)
        """
        # Build dependency graph
        self._build_dependency_graph(plugin_ids)

        # Check for missing dependencies
        # missing = self._find_missing_dependencies(plugin_ids)
        # if missing:
        #     return [], missing

        # Topological sort for load order
        try:
            resolved_order = self._topological_sort(plugin_ids)
            return resolved_order, []
        except ValueError as e:
            return [], [str(e)]

    def _build_dependency_graph(self, plugin_ids: list[str]) -> None:
        """Build dependency graph for given plugins."""
        self._dependency_graph.clear()

        # Process each plugin and its dependencies
        to_process = set(plugin_ids)
        processed = set()

        while to_process:
            plugin_id = to_process.pop()
            if plugin_id in processed:
                continue

            processed.add(plugin_id)
            manifest = self.catalog.get(plugin_id)

            if not manifest:
                continue

            # Add dependencies to graph
            # If plugin_id depends on dep_id, then dep_id must be loaded before plugin_id
            # So we add an edge from dep_id to plugin_id
            for dep in manifest.dependencies:
                dep_id = self._find_dependency(dep)
                if dep_id:
                    self._dependency_graph[dep_id].add(plugin_id)
                    # Add dependency to processing queue
                    if dep_id not in processed:
                        to_process.add(dep_id)

    def _find_dependency(self, dependency: PluginDependency) -> str | None:
        """Find a plugin that satisfies the dependency."""
        for plugin_id, manifest in self.catalog.items():
            # Check name match
            if manifest.name == dependency.name:
                # Check type match if specified
                if dependency.plugin_type and manifest.type != dependency.plugin_type:
                    continue
                # Check version match
                if dependency.is_satisfied_by(manifest.version):
                    return plugin_id
        return None

    def _find_missing_dependencies(self, plugin_ids: list[str]) -> list[str]:
        """Find any missing dependencies."""
        missing = []
        checked = set()

        for plugin_id in plugin_ids:
            manifest = self.catalog.get(plugin_id)
            if not manifest:
                missing.append(f"Plugin not found: {plugin_id}")
                continue

            for dep in manifest.dependencies:
                dep_key = f"{dep.name}:{dep.version_spec}"
                if dep_key in checked:
                    continue
                checked.add(dep_key)

                if not self._find_dependency(dep):
                    missing.append(f"Missing dependency: {dep.name} {dep.version_spec}")

        return missing

    def _topological_sort(self, plugin_ids: list[str]) -> list[str]:
        """Perform topological sort on dependency graph."""
        # Kahn's algorithm
        in_degree = defaultdict(int)

        # Calculate in-degrees
        all_nodes = set(plugin_ids)
        for node in self._dependency_graph:
            all_nodes.add(node)
            for dep in self._dependency_graph[node]:
                all_nodes.add(dep)
                in_degree[dep] += 1

        # Find nodes with no dependencies
        queue = [node for node in all_nodes if in_degree[node] == 0]
        result = []

        while queue:
            node = queue.pop(0)
            result.append(node)

            # Remove edges from this node
            for neighbor in self._dependency_graph.get(node, []):
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)

        # Check for cycles
        if len(result) != len(all_nodes):
            raise ValueError("Circular dependency detected in plugin graph")

        # Filter to only requested plugins and their dependencies
        return [p for p in result if p in all_nodes]

    def get_plugin_info(self, plugin_id: str) -> dict[str, Any] | None:
        """Get detailed information about a plugin."""
        manifest = self.catalog.get(plugin_id)
        if not manifest:
            return None

        info = manifest.to_dict()

        # Add dependency information
        info["resolved_dependencies"] = []
        for dep in manifest.dependencies:
            dep_id = self._find_dependency(dep)
            if dep_id:
                dep_manifest = self.catalog[dep_id]
                info["resolved_dependencies"].append(
                    {
                        "name": dep.name,
                        "version_spec": dep.version_spec,
                        "resolved_to": f"{dep_manifest.name} v{dep_manifest.version}",
                    }
                )

        return info

    def _load_cache(self) -> bool:
        """Load catalog from cache file."""
        cache_path = Path(self.CACHE_FILENAME)
        if not cache_path.exists():
            return False

        try:
            with open(cache_path) as f:
                cache_data = json.load(f)

            # Check if cache is still valid (simple timestamp check could be added)
            self.catalog.clear()
            for plugin_id, manifest_data in cache_data.items():
                self.catalog[plugin_id] = PluginManifest.from_dict(manifest_data)

            return True
        except Exception as e:
            self.logger.warning("Failed to load cache: %s", e)
            return False

    def _save_cache(self) -> None:
        """Save catalog to cache file."""
        try:
            cache_data = {
                plugin_id: manifest.to_dict() for plugin_id, manifest in self.catalog.items()
            }

            with open(self.CACHE_FILENAME, "w") as f:
                json.dump(cache_data, f, indent=2)

        except Exception as e:
            self.logger.warning("Failed to save cache: %s", e)
