from typing import Any, Dict, List, Optional, Set, Tuple

from panther.plugins.core.structures.plugin_dependency import PluginDependency
from panther.plugins.core.structures.plugin_registration import PluginRegistration

"""
Plugin Catalog System

This module provides plugin discovery, cataloging, and dependency resolution
for the PANTHER plugin ecosystem.
"""

import json
import logging
from collections import defaultdict
from pathlib import Path

from panther.plugins.core.structures.plugin_manifest import PluginManifest


class PluginCatalog:
    """

    Central catalog for plugin discovery, validation, and dependency management.

    This class maintains a registry of all available plugins, handles discovery
    from various sources, and provides dependency resolution capabilities.
    """

    CACHE_FILENAME = ".plugin_catalog_cache.json"

    def __init__(self, discovery_paths: Optional[List[str]] = None):
        """
        Initialize the plugin catalog.

        Args:
            discovery_paths: List of paths to search for plugins
        """
        self.logger = logging.getLogger("PluginCatalog")
        self.discovery_paths = discovery_paths or []
        self.catalog: Dict[str, PluginManifest] = {}
        self.registrations: Dict[str, PluginRegistration] = {}
        self._dependency_graph: Dict[str, Set[str]] = defaultdict(set)

    def add_discovery_path(self, path: str) -> None:
        """Add a new path for plugin discovery."""
        if path not in self.discovery_paths:
            self.discovery_paths.append(path)
            self.logger.debug("Added discovery path: %s", path)

    def scan_plugins(self, use_cache: bool = True) -> Dict[str, PluginManifest]:
        """
        Scan all discovery paths for plugins.

        Args:
            use_cache: Whether to use cached catalog if available

        Returns:
            Dictionary mapping plugin IDs to manifests
        """
        # Try to load from cache first
        from panther.plugins.core.plugin_decorators import get_decorated_plugins

        # Clear existing catalog
        self.catalog.clear()

        # Load all plugins from decorator registry
        decorated_plugins = get_decorated_plugins()
        for plugin_id, (plugin_class, manifest) in decorated_plugins.items():
            self.catalog[plugin_id] = manifest

        self.logger.info("Loaded %d plugins from decorator registry", len(self.catalog))
        return self.catalog

    def _scan_directory(self, directory: str) -> None:
        """Scan directory for plugins using decorator registry only."""
        from panther.plugins.core.plugin_decorators import get_decorated_plugins

        # Get all decorated plugins
        decorated_plugins = get_decorated_plugins()

        # Filter plugins by directory if needed
        for plugin_id, (plugin_class, manifest) in decorated_plugins.items():
            # Add to catalog if not already present
            if plugin_id not in self.catalog:
                self.catalog[plugin_id] = manifest
                self.logger.debug(f"Added plugin from decorator registry: {plugin_id}")

    def validate_plugin_config(
        self, plugin_id: str, config: Dict[str, Any]
    ) -> Tuple[bool, List[str]]:
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
                        errors.append(
                            f"Invalid type for {key}: expected {expected_type}"
                        )

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

    def resolve_dependencies(
        self, plugin_ids: List[str]
    ) -> Tuple[List[str], List[str]]:
        """
        Resolve dependencies for a set of plugins.

        Args:
            plugin_ids: List of plugin IDs to resolve

        Returns:
            Tuple of (resolved_order, missing_dependencies)
        """
        # TODO: Implement dependency resolution in future work
        # For now, just return the plugin IDs as-is without dependency checking
        return plugin_ids, []

    def _build_dependency_graph(self, plugin_ids: List[str]) -> None:
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
            # If plugin_id depends on dep_id, then dep_id must be loaded
            # before plugin_id. So we add an edge from dep_id to plugin_id
            for dep in manifest.dependencies:
                dep_id = self._find_dependency(dep)
                if dep_id:
                    self._dependency_graph[dep_id].add(plugin_id)
                    # Add dependency to processing queue
                    if dep_id not in processed:
                        to_process.add(dep_id)

    def _find_dependency(self, dependency: PluginDependency) -> Optional[str]:
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

    def _find_missing_dependencies(self, plugin_ids: List[str]) -> List[str]:
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

    def _topological_sort(self, plugin_ids: List[str]) -> List[str]:
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

    def get_plugin_info(self, plugin_id: str) -> Optional[Dict[str, Any]]:
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
                plugin_id: manifest.to_dict()
                for plugin_id, manifest in self.catalog.items()
            }

            with open(self.CACHE_FILENAME, "w") as f:
                json.dump(cache_data, f, indent=2)

        except Exception as e:
            self.logger.warning("Failed to save cache: %s", e)

    def validate_experiment_plugins(self, experiment_config) -> Tuple[bool, List[str]]:
        """
        Validate that all plugins required by an experiment are available.

        Args:
            experiment_config: Experiment configuration

        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []
        required_plugins = set()

        # Load plugins if not already in catalog
        if not self.catalog:
            self.scan_plugins()

        # Extract required plugins from experiment config
        for test in experiment_config.tests:
            # Check network environment
            if hasattr(test, "network_environment") and test.network_environment:
                env_type = test.network_environment.type
                if env_type:
                    required_plugins.add((env_type, "network environment"))

            # Check execution environments
            if hasattr(test, "execution_environment") and test.execution_environment:
                for exec_env in test.execution_environment:
                    if hasattr(exec_env, "type") and exec_env.type:
                        required_plugins.add((exec_env.type, "execution environment"))

            # Check services
            if hasattr(test, "services") and test.services:
                for _, service_config in test.services.items():
                    if hasattr(service_config, "implementation"):
                        impl = service_config.implementation
                        impl_name = impl.name
                        impl_type = impl.type if hasattr(impl, "type") else "iut"

                        # Handle string or enum type
                        impl_type_str = (
                            impl_type if isinstance(impl_type, str) else impl_type.value
                        )
                        if impl_type_str.lower() == "testers":
                            required_plugins.add((impl_name, "tester"))
                        else:
                            required_plugins.add((impl_name, "IUT implementation"))

        # Validate each required plugin
        for plugin_name, plugin_desc in required_plugins:
            # Check if plugin exists in catalog
            plugin_found = False
            for plugin_id, manifest in self.catalog.items():
                if manifest.name == plugin_name:
                    plugin_found = True
                    break

            if not plugin_found:
                errors.append(
                    f"Required {plugin_desc} plugin '{plugin_name}' not found"
                )

        return len(errors) == 0, errors

    def validate_plugin_dependencies(self, plugin_name: str) -> Tuple[bool, List[str]]:
        """
        Validate plugin dependencies.

        Args:
            plugin_name: Name of plugin to validate

        Returns:
            Tuple of (all_satisfied, missing_dependencies)
        """
        # Find the plugin manifest
        target_manifest = None
        for plugin_id, manifest in self.catalog.items():
            if manifest.name == plugin_name:
                target_manifest = manifest
                break

        if not target_manifest:
            return False, [f"Plugin '{plugin_name}' not found"]

        # Check dependencies
        missing = []
        for dep in target_manifest.dependencies:
            # Find if dependency is satisfied
            dependency_satisfied = False
            for plugin_id, manifest in self.catalog.items():
                if manifest.name == dep.name:
                    # Check version compatibility if needed
                    if dep.is_satisfied_by(manifest.version):
                        dependency_satisfied = True
                        break

            if not dependency_satisfied:
                missing.append(f"Missing dependency: {dep.name} {dep.version_spec}")

        return len(missing) == 0, missing

    def refresh(self) -> None:
        """Refresh the plugin catalog."""
        self.logger.info("Refreshing plugin catalog")
        self.catalog.clear()
        self.scan_plugins(use_cache=False)
