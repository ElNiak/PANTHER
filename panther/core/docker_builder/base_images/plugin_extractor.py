"""
Plugin Requirements Extractor - Integration with Existing Plugin System

Implements PluginRequirementsExtractor using existing PANTHER plugin decorators and structures.
Follows DRY and SOLID principles by reusing existing plugin infrastructure.
"""

import logging
from typing import Any, Dict, List, Optional

from panther.plugins.core.plugin_decorators import (
    get_decorated_plugins,
    get_plugin_by_name,
    get_plugins_by_type,
)
from panther.plugins.core.structures.plugin_type import PluginType

from .interfaces import PluginRequirementsExtractor


class PantherPluginRequirementsExtractor(PluginRequirementsExtractor):
    """
    Extract Docker requirements from PANTHER plugin decorators.

    Integrates with existing plugin decorator system to extract base image requirements
    from plugin metadata declared via @register_plugin decorators.

    Follows SRP: Only handles requirements extraction from plugin system.
    Follows DRY: Reuses existing plugin metadata infrastructure.
    """

    def __init__(self, logger: Optional[logging.Logger] = None):
        self._logger = logger or logging.getLogger(__name__)
        self._cache: Dict[str, Dict[str, Any]] = {}

    def extract_docker_requirements(
        self, plugin_config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Extract Docker requirements from plugin configuration using existing plugin system.

        Uses plugin decorators to get capabilities, dependencies, and runtime requirements.
        """
        plugin_name = plugin_config.get("name", "")
        plugin_type = plugin_config.get("type", "")

        # Check cache first
        cache_key = f"{plugin_type}:{plugin_name}"
        if cache_key in self._cache:
            cached = self._cache[cache_key].copy()
            # Apply config overrides
            self._apply_config_overrides(cached, plugin_config)
            return cached

        # Initialize default requirements
        requirements = {
            "capabilities": [],
            "packages": [],
            "external_dependencies": [],
            "runtime_mode": "minimal",
            "build_mode": "",
            "max_size_mb": float("inf"),
            "platforms": ["linux/amd64", "linux/arm64"],
        }

        # Extract from plugin decorator if available
        plugin_entry = get_plugin_by_name(plugin_name, plugin_type)
        if plugin_entry:
            cls, manifest = plugin_entry
            requirements = self._extract_from_manifest(manifest)
        else:
            self._logger.debug(f"Plugin {plugin_name} not found in decorator registry")
            # Fallback to plugin name-based inference
            requirements = self._infer_from_plugin_name(plugin_name)

        # Apply configuration overrides
        self._apply_config_overrides(requirements, plugin_config)

        # Cache the result
        self._cache[cache_key] = requirements.copy()

        return requirements

    def _extract_from_manifest(self, manifest) -> Dict[str, Any]:
        """Extract requirements from plugin manifest."""
        requirements = {
            "capabilities": list(manifest.capabilities)
            if manifest.capabilities
            else [],
            "packages": [],
            "external_dependencies": list(manifest.external_dependencies)
            if manifest.external_dependencies
            else [],
            "runtime_mode": manifest.runtime_mode or "minimal",
            "build_mode": "",
            "max_size_mb": self._get_size_constraint_for_plugin_type(manifest.type),
            "platforms": ["linux/amd64", "linux/arm64"],
        }

        # Map external dependencies to packages
        if manifest.external_dependencies:
            requirements["packages"] = self._map_external_deps_to_packages(
                manifest.external_dependencies
            )

        # Add plugin type-specific capabilities
        type_capabilities = self._get_capabilities_for_plugin_type(manifest.type)
        requirements["capabilities"].extend(type_capabilities)

        # Add plugin name-specific capabilities
        name_capabilities = self._get_capabilities_for_plugin_name(manifest.name)
        requirements["capabilities"].extend(name_capabilities)

        # Remove duplicates
        requirements["capabilities"] = list(set(requirements["capabilities"]))
        requirements["packages"] = list(set(requirements["packages"]))

        return requirements

    def _infer_from_plugin_name(self, plugin_name: str) -> Dict[str, Any]:
        """Infer requirements from plugin name when decorator metadata is not available."""
        requirements = {
            "capabilities": ["runtime"],
            "packages": [],
            "external_dependencies": [],
            "runtime_mode": "minimal",
            "build_mode": "",
            "max_size_mb": 800,
            "platforms": ["linux/amd64", "linux/arm64"],
        }

        # Plugin name-based inference
        name_capabilities = self._get_capabilities_for_plugin_name(plugin_name)
        requirements["capabilities"].extend(name_capabilities)
        requirements["capabilities"] = list(set(requirements["capabilities"]))

        return requirements

    def _get_capabilities_for_plugin_type(self, plugin_type: PluginType) -> List[str]:
        """Get base capabilities for plugin type - DRY principle."""
        type_capabilities = {
            PluginType.IUT: ["networking", "runtime"],
            PluginType.TESTER: ["development", "debugging"],
            PluginType.NETWORK_ENVIRONMENT: ["networking", "orchestration"],
            PluginType.EXECUTION_ENVIRONMENT: ["profiling", "debugging"],
            PluginType.PROTOCOL: ["networking"],
            PluginType.OBSERVER: ["monitoring", "runtime"],
        }
        return type_capabilities.get(plugin_type, [])

    def _get_capabilities_for_plugin_name(self, plugin_name: str) -> List[str]:
        """Get capabilities based on plugin name - DRY principle."""
        name_mapping = {
            # QUIC implementations
            "picoquic": ["compilation", "cmake", "networking"],
            "quiche": ["compilation", "rust", "networking"],
            "mvfst": ["compilation", "cmake", "cpp", "networking"],
            "lsquic": ["compilation", "cmake", "networking"],
            "quinn": ["compilation", "rust", "networking"],
            "quic-go": ["compilation", "go", "networking"],
            "aioquic": ["python", "development", "networking"],
            # Testing tools
            "ivy": ["python", "debugging", "formal_verification"],
            "gdb": ["debugging", "profiling"],
            "valgrind": ["debugging", "profiling", "memory_analysis"],
            "strace": ["debugging", "profiling", "syscall_tracing"],
            "tcpdump": ["networking", "monitoring", "packet_capture"],
            "wireshark": ["networking", "monitoring", "packet_analysis"],
            # Environment plugins
            "docker_compose": ["orchestration", "networking", "containers"],
            "localhost": ["networking"],
            "shadow": ["networking", "simulation"],
            # HTTP implementations
            "nginx": ["networking", "http", "compilation"],
            "apache": ["networking", "http"],
            "curl": ["networking", "http", "client"],
        }

        return name_mapping.get(plugin_name.lower(), [])

    def _get_size_constraint_for_plugin_type(self, plugin_type: PluginType) -> float:
        """Get size constraints by plugin type."""
        constraints = {
            PluginType.IUT: 1000,
            PluginType.TESTER: 1200,
            PluginType.NETWORK_ENVIRONMENT: 800,
            PluginType.EXECUTION_ENVIRONMENT: 1200,
            PluginType.PROTOCOL: 300,
            PluginType.OBSERVER: 500,
        }
        return constraints.get(plugin_type, 800)

    def _map_external_deps_to_packages(self, external_deps: List[str]) -> List[str]:
        """Map external dependencies to system packages."""
        package_mapping = {
            "docker": ["docker.io"],
            "cmake": ["cmake", "build-essential"],
            "git": ["git"],
            "python3": ["python3", "python3-pip"],
            "openssl": ["openssl", "libssl-dev"],
            "curl": ["curl", "libcurl4-openssl-dev"],
            "gcc": ["gcc", "build-essential"],
            "gdb": ["gdb"],
            "valgrind": ["valgrind"],
            "strace": ["strace"],
            "tcpdump": ["tcpdump"],
            "nodejs": ["nodejs", "npm"],
            "go": ["golang-go"],
            "rust": ["rustc", "cargo"],
            "java": ["openjdk-11-jdk"],
            "pkg-config": ["pkg-config"],
        }

        packages = []
        for dep in external_deps:
            # Handle version specifications
            dep_name = dep.split(">=")[0].split("==")[0].split("<=")[0].strip()
            if dep_name in package_mapping:
                packages.extend(package_mapping[dep_name])
            else:
                packages.append(dep_name)

        return list(set(packages))

    def _apply_config_overrides(
        self, requirements: Dict[str, Any], config: Dict[str, Any]
    ) -> None:
        """Apply configuration overrides to requirements."""
        # Allow config to override specific fields
        override_fields = ["runtime_mode", "build_mode", "max_size_mb", "platforms"]

        for field in override_fields:
            if field in config and config[field]:
                if field == "max_size_mb":
                    # Take minimum constraint
                    requirements[field] = min(
                        requirements.get(field, float("inf")), config[field]
                    )
                else:
                    requirements[field] = config[field]

        # Merge list fields
        list_fields = ["capabilities", "packages", "external_dependencies"]
        for field in list_fields:
            if field in config and config[field]:
                existing = requirements.get(field, [])
                requirements[field] = list(set(existing + config[field]))

    def get_plugin_capabilities(self, plugin_name: str) -> List[str]:
        """Get capabilities required by specific plugin."""
        # Try to find in decorator registry
        plugin_entry = get_plugin_by_name(plugin_name)
        if plugin_entry:
            cls, manifest = plugin_entry
            capabilities = list(manifest.capabilities) if manifest.capabilities else []

            # Add type and name-specific capabilities
            capabilities.extend(self._get_capabilities_for_plugin_type(manifest.type))
            capabilities.extend(self._get_capabilities_for_plugin_name(plugin_name))

            return list(set(capabilities))

        # Fallback to name-based inference
        return self._get_capabilities_for_plugin_name(plugin_name)

    def analyze_dependencies(self, plugins: List[str]) -> Dict[str, Any]:
        """Analyze combined requirements from multiple plugins."""
        combined = {
            "capabilities": [],
            "packages": [],
            "external_dependencies": [],
            "runtime_mode": "minimal",
            "build_mode": "",
            "max_size_mb": float("inf"),
            "platforms": ["linux/amd64", "linux/arm64"],
            "plugins": plugins,
        }

        runtime_modes = []
        build_modes = []

        for plugin_name in plugins:
            # Try to determine plugin type
            plugin_type = ""
            for ptype in PluginType:
                if get_plugin_by_name(plugin_name, ptype.value):
                    plugin_type = ptype.value
                    break

            plugin_config = {"name": plugin_name, "type": plugin_type}
            requirements = self.extract_docker_requirements(plugin_config)

            # Merge requirements
            combined["capabilities"].extend(requirements.get("capabilities", []))
            combined["packages"].extend(requirements.get("packages", []))
            combined["external_dependencies"].extend(
                requirements.get("external_dependencies", [])
            )

            # Collect modes for resolution
            if requirements.get("runtime_mode"):
                runtime_modes.append(requirements["runtime_mode"])
            if requirements.get("build_mode"):
                build_modes.append(requirements["build_mode"])

            # Update size constraint (take minimum)
            plugin_max_size = requirements.get("max_size_mb", float("inf"))
            combined["max_size_mb"] = min(combined["max_size_mb"], plugin_max_size)

        # Remove duplicates
        combined["capabilities"] = list(set(combined["capabilities"]))
        combined["packages"] = list(set(combined["packages"]))
        combined["external_dependencies"] = list(set(combined["external_dependencies"]))

        # Resolve mode conflicts
        combined["runtime_mode"] = self._resolve_runtime_mode(runtime_modes)
        combined["build_mode"] = self._resolve_build_mode(build_modes)

        return combined

    def _resolve_runtime_mode(self, modes: List[str]) -> str:
        """Resolve runtime mode conflicts - prefer more capable modes."""
        if not modes:
            return "minimal"

        # Priority: profile > debug > minimal
        priority = {"profile": 3, "debug": 2, "minimal": 1}
        return max(modes, key=lambda m: priority.get(m, 0))

    def _resolve_build_mode(self, modes: List[str]) -> str:
        """Resolve build mode conflicts - prefer debug for development."""
        if not modes:
            return ""

        # Prefer debug modes
        debug_modes = [m for m in modes if "debug" in m.lower()]
        if debug_modes:
            return debug_modes[0]

        # Return first non-empty mode
        non_empty = [m for m in modes if m]
        return non_empty[0] if non_empty else ""

    def clear_cache(self) -> None:
        """Clear the requirements cache."""
        self._cache.clear()

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return {
            "cached_entries": len(self._cache),
            "cache_keys": list(self._cache.keys()),
        }
