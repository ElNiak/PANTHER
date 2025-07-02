"""
Feature Registry for dynamic feature logging registration.

This module provides a centralized registry where plugins and modules
can register themselves for feature-specific logging.
"""

import logging
from threading import Lock
from typing import Dict, List, Optional, Set, Union


class FeatureRegistry:
    """
    Centralized registry for feature-to-module mappings.

    Allows plugins and modules to dynamically register themselves
    for specific feature categories, enabling automatic feature
    detection and logging configuration.
    """

    _instance = None
    _lock = Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if not self._initialized:
            self._feature_mappings: Dict[str, Set[str]] = {}
            self._module_features: Dict[str, str] = {}
            self._pattern_mappings: Dict[str, Set[str]] = {}
            self._logger = logging.getLogger(__name__)
            self._initialized = True

    def register_feature(
        self,
        feature: str,
        module_patterns: Union[str, List[str]],
        module_name: Optional[str] = None,
    ) -> None:
        """
        Register module patterns for a specific feature.

        Args:
            feature: Feature name (e.g., 'docker_operations', 'command_generation')
            module_patterns: String pattern or list of patterns to match module names
            module_name: Optional specific module name for direct mapping
        """
        with self._lock:
            # Ensure feature exists in mappings
            if feature not in self._feature_mappings:
                self._feature_mappings[feature] = set()
            if feature not in self._pattern_mappings:
                self._pattern_mappings[feature] = set()

            # Handle module patterns
            if isinstance(module_patterns, str):
                module_patterns = [module_patterns]

            for pattern in module_patterns:
                self._pattern_mappings[feature].add(pattern.lower())
                self._feature_mappings[feature].add(pattern.lower())

            # Handle direct module name mapping
            if module_name:
                self._module_features[module_name.lower()] = feature
                self._feature_mappings[feature].add(module_name.lower())

            self._logger.debug(
                f"Registered feature '{feature}' with patterns: {module_patterns}"
            )

    def register_module(self, module_name: str, feature: str) -> None:
        """
        Register a specific module for a feature.

        Args:
            module_name: Full module name (e.g., 'panther.plugins.services.picoquic')
            feature: Feature name
        """
        with self._lock:
            self._module_features[module_name.lower()] = feature

            if feature not in self._feature_mappings:
                self._feature_mappings[feature] = set()
            self._feature_mappings[feature].add(module_name.lower())

            self._logger.debug(
                f"Registered module '{module_name}' for feature '{feature}'"
            )

    def detect_feature(self, module_name: str) -> Optional[str]:
        """
        Detect the feature for a given module name.

        Args:
            module_name: Module name to analyze

        Returns:
            Detected feature name or None
        """
        module_lower = module_name.lower()

        # Check direct module mapping first
        if module_lower in self._module_features:
            return self._module_features[module_lower]

        # Check pattern matching
        for feature, patterns in self._pattern_mappings.items():
            for pattern in patterns:
                if pattern in module_lower:
                    return feature

        return None

    def get_modules_for_feature(self, feature: str) -> Set[str]:
        """
        Get all registered modules for a feature.

        Args:
            feature: Feature name

        Returns:
            Set of module names/patterns for the feature
        """
        return self._feature_mappings.get(feature, set()).copy()

    def get_all_features(self) -> List[str]:
        """
        Get all registered features.

        Returns:
            List of all feature names
        """
        return list(self._feature_mappings.keys())

    def get_feature_info(self) -> Dict[str, Dict[str, any]]:
        """
        Get complete feature registry information.

        Returns:
            Dictionary with feature information
        """
        return {
            "features": list(self._feature_mappings.keys()),
            "total_modules": len(self._module_features),
            "feature_mappings": {k: list(v) for k, v in self._feature_mappings.items()},
            "direct_mappings": dict(self._module_features),
        }

    def clear_feature(self, feature: str) -> None:
        """
        Clear all registrations for a feature.

        Args:
            feature: Feature name to clear
        """
        with self._lock:
            if feature in self._feature_mappings:
                del self._feature_mappings[feature]
            if feature in self._pattern_mappings:
                del self._pattern_mappings[feature]

            # Remove from module mappings
            to_remove = [k for k, v in self._module_features.items() if v == feature]
            for key in to_remove:
                del self._module_features[key]

    def reset(self) -> None:
        """Reset the entire registry."""
        with self._lock:
            self._feature_mappings.clear()
            self._module_features.clear()
            self._pattern_mappings.clear()


# Global registry instance
feature_registry = FeatureRegistry()


def register_feature(
    feature: str,
    module_patterns: Union[str, List[str]],
    module_name: Optional[str] = None,
) -> None:
    """
    Convenience function to register a feature.

    Args:
        feature: Feature name
        module_patterns: Pattern(s) to match module names
        module_name: Optional specific module name
    """
    feature_registry.register_feature(feature, module_patterns, module_name)


def register_module_feature(module_name: str, feature: str) -> None:
    """
    Convenience function to register a module for a feature.

    Args:
        module_name: Module name
        feature: Feature name
    """
    feature_registry.register_module(module_name, feature)


def detect_module_feature(module_name: str) -> Optional[str]:
    """
    Convenience function to detect feature for a module.

    Args:
        module_name: Module name

    Returns:
        Detected feature or None
    """
    return feature_registry.detect_feature(module_name)


# Decorator for automatic registration
def feature_logger(feature: str, patterns: Optional[Union[str, List[str]]] = None):
    """
    Decorator to automatically register a class/module for a feature.

    Args:
        feature: Feature name to register for
        patterns: Optional additional patterns to register

    Usage:
        @feature_logger('docker_operations', ['docker', 'container'])
        class DockerBuilder:
            pass
    """

    def decorator(cls):
        # Register the class module
        module_name = cls.__module__
        register_module_feature(module_name, feature)

        # Register additional patterns if provided
        if patterns:
            register_feature(feature, patterns, module_name)

        # Also register class name pattern
        class_patterns = [cls.__name__.lower()]
        register_feature(feature, class_patterns, module_name)

        return cls

    return decorator


# Initialize with some core patterns
def _initialize_core_patterns():
    """Initialize the registry with core PANTHER patterns."""

    # Core Components
    register_feature("command_generation", ["command", "cmd", "builder", "processor"])
    register_feature("template_rendering", ["template", "render", "jinja"])
    register_feature("docker_operations", ["docker", "container", "build"])
    register_feature("config_processing", ["config", "configuration", "schema"])
    register_feature("event_system", ["event", "emitter", "state", "observer"])
    register_feature("file_operations", ["file", "output", "storage", "utils"])

    # Service Management
    register_feature("service_managers", ["service", "manager", "factory"])
    register_feature("ivy_operations", ["ivy", "panther_ivy"])
    register_feature(
        "quic_services",
        ["quic", "picoquic", "aioquic", "lsquic", "mvfst", "quiche", "quinn"],
    )
    register_feature("plugin_loading", ["plugin", "loader", "discovery", "catalog"])

    # Environment Management
    register_feature("network_environments", ["network_environment", "net_env"])
    register_feature(
        "execution_environment",
        [
            "execution_environment",
            "exec_env",
            "strace",
            "gperf",
            "memcheck",
            "helgrind",
        ],
    )
    register_feature("docker_compose", ["docker_compose", "compose"])
    register_feature("shadow_ns", ["shadow"])
    register_feature("localhost_container", ["localhost"])

    # Protocol Operations
    register_feature("certificate_management", ["cert", "certificate", "tls", "ssl"])
    register_feature("network_setup", ["network", "networking"])
    register_feature("port_management", ["port", "ports"])
    register_feature("protocol_communication", ["protocol", "communication"])

    # Data and Metrics
    register_feature(
        "metrics_collection", ["metrics", "monitor", "collector", "reporter"]
    )
    register_feature("data_storage", ["storage", "store", "database"])
    register_feature("result_processing", ["result", "processor"])
    register_feature("output_aggregation", ["aggregator", "collector"])

    # Development and Debugging
    register_feature("test_execution", ["test", "experiment"])
    register_feature("validation_checks", ["validation", "validator"])
    register_feature("error_handling", ["error", "exception", "fail"])


# Initialize core patterns on module import
_initialize_core_patterns()
