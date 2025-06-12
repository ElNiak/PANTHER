"""
Enhanced Plugin Catalog with Hierarchical Discovery

This module provides a catalog system for plugin discovery and management
that properly handles category-level manifests while continuing to scan
for actual implementation plugins.
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Any

import yaml

from panther.plugins.plugin_manifest import PluginManifest, PluginType, PluginDependency


class PluginCatalog:
    """
    Enhanced catalog for plugin discovery, registration, and dependency management.

    This version properly handles hierarchical plugin structures where category
    manifests exist alongside actual implementation manifests.
    """

    MANIFEST_FILENAMES = ["plugin.yaml", "plugin.yml", "manifest.yaml", "manifest.yml"]
    CACHE_FILE = ".plugin_catalog_cache.json"
    CACHE_EXPIRY_HOURS = 24

    def __init__(self, discovery_paths: list[str]):
        """
        Initialize the plugin catalog.

        Args:
            discovery_paths: List of directories to scan for plugins
        """
        self.discovery_paths = discovery_paths
        self.catalog: dict[str, PluginManifest] = {}
        self.category_manifests: dict[str, PluginManifest] = {}  # Track category manifests
        self.logger = logging.getLogger("PluginCatalog")

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
        self.category_manifests.clear()

        for path in self.discovery_paths:
            if not os.path.exists(path):
                self.logger.warning("Discovery path does not exist: %s", path)
                continue

            self._scan_directory(path)

        # Save cache for next time
        self._save_cache()

        self.logger.info(
            "Found %d plugins (%d categories)", len(self.catalog), len(self.category_manifests)
        )
        return self.catalog

    def _scan_directory(self, directory: str, depth: int = 0) -> None:
        """
        Recursively scan a directory for plugins.

        Args:
            directory: Directory to scan
            depth: Current recursion depth
        """
        path = Path(directory)

        # Look for manifest files in this directory
        manifest_found = False
        for manifest_file in self.MANIFEST_FILENAMES:
            manifest_path = path / manifest_file
            if manifest_path.exists():
                manifest = self._load_manifest_file(manifest_path)
                if manifest:
                    # Check if this is a concrete implementation or just a category
                    if self._is_category_manifest(manifest, path):
                        # Store as category but continue scanning
                        category_id = f"category:{manifest.name}"
                        self.category_manifests[category_id] = manifest
                        self.logger.debug("Found category manifest: %s", manifest.name)
                        manifest_found = True
                    else:
                        # This is an actual plugin, register it
                        plugin_id = f"{manifest.type.value}:{manifest.name}"
                        self.catalog[plugin_id] = manifest
                        self.logger.debug("Found plugin: %s", plugin_id)
                        # Still scan subdirectories for multi-level plugins
                        manifest_found = True
                break

        # Continue scanning subdirectories regardless of manifest presence
        # This allows for hierarchical plugin structures
        try:
            for item in path.iterdir():
                if item.is_dir() and not item.name.startswith("."):
                    # Skip certain directories that are definitely not plugins
                    if item.name in [
                        "__pycache__",
                        "templates",
                        "tests",
                        "docs",
                        "examples",
                        "submodules",
                        ".git",
                    ]:
                        continue
                    self._scan_directory(str(item), depth + 1)
        except PermissionError:
            self.logger.warning("Permission denied accessing: %s", directory)

    def _is_category_manifest(self, manifest: PluginManifest, path: Path) -> bool:
        """
        Enhanced category detection logic.

        Determines if a manifest represents a category rather than an actual plugin.
        """
        # Check if manifest explicitly declares itself as a category
        if manifest.is_category:
            return True

        # Check for auto-generated description AND empty config
        if (
            "Auto-generated manifest for" in manifest.description
            and not manifest.config_schema
            and not manifest.capabilities
        ):
            return True

        # Check for specific category-level names only
        category_names = ["iut", "testers", "protocols", "environments"]
        if manifest.name in category_names and not manifest.config_schema:
            return True

        # Check if manifest has no entry point and no implementation class
        if not manifest.entry_point and not self._has_implementation_class(path):
            return True

        # Check if subdirectories contain implementations
        if self._has_implementation_subdirs(path):
            return True

        # Everything else is a real plugin
        return False

    def _has_implementation_class(self, path: Path) -> bool:
        """Check if directory contains an implementation class."""
        # Look for Python files that might contain implementation classes
        for py_file in path.glob("*.py"):
            if py_file.name.startswith("__"):
                continue

            try:
                with open(py_file) as f:
                    content = f.read()
                    # Check for common implementation patterns
                    if any(
                        pattern in content
                        for pattern in [
                            "ServiceManager",
                            "IImplementationManager",
                            "INetworkEnvironment",
                            "IExecutionEnvironment",
                            "ITesterPlugin",
                            "class ",
                        ]
                    ):
                        return True
            except Exception:
                continue

        return False

    def _has_implementation_subdirs(self, path: Path) -> bool:
        """Check if directory contains subdirectories with implementations."""
        try:
            for subdir in path.iterdir():
                if subdir.is_dir() and not subdir.name.startswith("."):
                    # Check if subdirectory has manifest files
                    for manifest_file in self.MANIFEST_FILENAMES:
                        if (subdir / manifest_file).exists():
                            return True
        except Exception:
            pass

        return False

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

            return manifest

        except Exception as e:
            self.logger.error("Failed to load manifest from %s: %s", manifest_path, e)
            return None

    def _infer_plugin_type(self, manifest_path: Path) -> str:
        """Infer plugin type from directory structure."""
        path_str = str(manifest_path).lower()

        if "services" in path_str:
            if "iut" in path_str:
                return "iut"
            elif "testers" in path_str:
                return "tester"
            else:
                return "service"
        elif "environments" in path_str:
            return "environment"
        elif "protocols" in path_str:
            return "protocol"
        elif "observers" in path_str:
            return "observer"
        else:
            return "unknown"

    def get_plugin(self, plugin_id: str) -> PluginManifest | None:
        """Get a plugin by ID."""
        return self.catalog.get(plugin_id)

    def find_plugin_by_name(
        self, name: str, plugin_type: str | None = None
    ) -> PluginManifest | None:
        """
        Find a plugin by name, optionally filtering by type.

        Args:
            name: Plugin name to search for
            plugin_type: Optional type to filter by

        Returns:
            First matching plugin manifest, or None
        """
        for plugin_id, manifest in self.catalog.items():
            if manifest.name == name:
                if plugin_type is None or manifest.type.value == plugin_type:
                    return manifest
        return None

    def list_plugins_by_type(self, plugin_type: PluginType) -> list[PluginManifest]:
        """List all plugins of a specific type."""
        return [manifest for manifest in self.catalog.values() if manifest.type == plugin_type]

    def validate_config(self, plugin_id: str, config: dict[str, Any]) -> tuple[bool, list[str]]:
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
            Tuple of (ordered_plugin_ids, missing_dependencies)
        """
        # Build dependency graph
        graph = {}
        all_deps = set(plugin_ids)
        missing = []
        external_deps = set()  # Track external dependencies

        # Process queue of plugins to check
        to_process = plugin_ids.copy()
        processed = set()

        while to_process:
            plugin_id = to_process.pop(0)
            if plugin_id in processed:
                continue
            processed.add(plugin_id)

            # Skip external dependencies
            if plugin_id.startswith("external:"):
                external_deps.add(plugin_id)
                continue

            manifest = self.catalog.get(plugin_id)
            if not manifest:
                # Try to find by name if not found by ID
                for pid, m in self.catalog.items():
                    if m.name == plugin_id.split(":")[-1]:
                        manifest = m
                        plugin_id = pid
                        break

                if not manifest:
                    missing.append(plugin_id)
                    continue

            graph[plugin_id] = []

            # Process plugin dependencies
            for dep in manifest.dependencies:
                dep_id = self._find_dependency(dep)
                if dep_id:
                    if not dep_id.startswith("external:"):
                        graph[plugin_id].append(dep_id)
                        all_deps.add(dep_id)
                        if dep_id not in processed:
                            to_process.append(dep_id)
                    else:
                        external_deps.add(dep_id)
                else:
                    missing.append(f"{dep.plugin_type}:{dep.name}" if dep.plugin_type else dep.name)

        # Topological sort
        ordered = []
        visited = set()
        temp_visited = set()

        def visit(node):
            if node in temp_visited:
                raise ValueError(f"Circular dependency detected involving {node}")
            if node in visited:
                return

            temp_visited.add(node)
            for neighbor in graph.get(node, []):
                visit(neighbor)
            temp_visited.remove(node)
            visited.add(node)
            ordered.append(node)

        for node in graph:
            if node not in visited:
                visit(node)

        return ordered, missing

    def _find_dependency(self, dependency: PluginDependency) -> str | None:
        """
        Find a plugin that satisfies the dependency.

        Returns plugin ID or 'external:name' for external dependencies.
        """
        # List of known external dependencies
        KNOWN_EXTERNAL_DEPS = {
            "docker",
            "docker-compose",
            "cmake",
            "z3",
            "strace",
            "gperf",
            "valgrind",
            "python",
            "rust",
            "cargo",
        }

        # Check if it's an external dependency
        dep_name = dependency.name.split(">=")[0].split("==")[0].split("<")[0].strip()
        if dep_name in KNOWN_EXTERNAL_DEPS:
            return f"external:{dependency.name}"

        # Original plugin resolution logic
        for plugin_id, manifest in self.catalog.items():
            if manifest.name == dependency.name:
                if dependency.plugin_type is None or manifest.type == dependency.plugin_type:
                    # Check version compatibility
                    if dependency.is_satisfied_by(manifest.version):
                        return plugin_id

        return None

    def get_external_dependencies(self, plugin_ids: list[str]) -> list[str]:
        """
        Get all external dependencies for a set of plugins.

        Args:
            plugin_ids: List of plugin IDs to check

        Returns:
            List of external dependency specifications
        """
        external_deps = set()

        for plugin_id in plugin_ids:
            manifest = self.catalog.get(plugin_id)
            if manifest:
                # Add external dependencies from manifest
                external_deps.update(manifest.external_dependencies)

                # Check plugin dependencies that are external
                for dep in manifest.dependencies:
                    dep_id = self._find_dependency(dep)
                    if dep_id and dep_id.startswith("external:"):
                        external_deps.add(dep_id.replace("external:", ""))

        return sorted(list(external_deps))

    def _save_cache(self) -> None:
        """Save catalog to cache file."""
        cache_data = {
            "timestamp": datetime.now().isoformat(),
            "catalog": {
                plugin_id: manifest.to_dict() for plugin_id, manifest in self.catalog.items()
            },
            "categories": {
                cat_id: manifest.to_dict() for cat_id, manifest in self.category_manifests.items()
            },
        }

        try:
            cache_path = Path(self.discovery_paths[0]) / self.CACHE_FILE
            with open(cache_path, "w") as f:
                json.dump(cache_data, f, indent=2)
        except Exception as e:
            self.logger.warning("Failed to save cache: %s", e)

    def _load_cache(self) -> bool:
        """Load catalog from cache if valid."""
        try:
            cache_path = Path(self.discovery_paths[0]) / self.CACHE_FILE
            if not cache_path.exists():
                return False

            with open(cache_path) as f:
                cache_data = json.load(f)

            # Check cache age
            timestamp = datetime.fromisoformat(cache_data["timestamp"])
            age_hours = (datetime.now() - timestamp).total_seconds() / 3600
            if age_hours > self.CACHE_EXPIRY_HOURS:
                return False

            # Load catalog
            self.catalog.clear()
            for plugin_id, data in cache_data["catalog"].items():
                self.catalog[plugin_id] = PluginManifest.from_dict(data)

            # Load categories
            self.category_manifests.clear()
            if "categories" in cache_data:
                for cat_id, data in cache_data["categories"].items():
                    self.category_manifests[cat_id] = PluginManifest.from_dict(data)

            return True

        except Exception as e:
            self.logger.warning("Failed to load cache: %s", e)
            return False
