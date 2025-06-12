"""
Plugin Registration Decorators

This module provides decorators for easy plugin registration and metadata declaration.
"""

import functools
import logging
from typing import Any

from panther.plugins.plugin_manifest import PluginManifest, PluginType, PluginDependency


# Global registry for decorated plugins
_DECORATED_PLUGINS: dict[str, tuple[type, PluginManifest]] = {}


def register_plugin(
    plugin_type: str | PluginType,
    name: str | None = None,
    version: str = "1.0.0",
    author: str = "",
    description: str = "",
    min_panther_version: str = "1.0.0",
    dependencies: list[str | dict] | None = None,
    **kwargs,
):
    """
    Decorator to register a plugin with metadata.

    Usage:
        @register_plugin(
            plugin_type="service",
            name="picoquic",
            version="1.2.0",
            description="PicoQUIC QUIC implementation",
            dependencies=["quic_protocol>=1.0.0"]
        )
        class PicoquicServiceManager(IServiceManager):
            pass

    Args:
        plugin_type: Type of plugin (service, environment, tester, etc.)
        name: Plugin name (defaults to class name)
        version: Plugin version
        author: Plugin author
        description: Plugin description
        min_panther_version: Minimum PANTHER version required
        dependencies: List of dependencies (strings or dicts)
        **kwargs: Additional metadata fields
    """
    # Convert string to PluginType enum
    if isinstance(plugin_type, str):
        try:
            plugin_type = PluginType(plugin_type.lower())
        except ValueError:
            # Try mapping common aliases
            type_map = {
                "iut": PluginType.IUT,
                "implementation": PluginType.IUT,
                "test": PluginType.TESTER,
                "net": PluginType.ENVIRONMENT,
                "network": PluginType.ENVIRONMENT,
                "exec": PluginType.ENVIRONMENT,
                "execution": PluginType.ENVIRONMENT,
            }
            plugin_type = type_map.get(plugin_type.lower(), PluginType.SERVICE)

    def decorator(cls: type) -> type:
        # Use provided name or class name
        plugin_name = name or cls.__name__.lower().replace("servicemanager", "").replace(
            "manager", ""
        )

        # Parse dependencies
        parsed_deps = []
        if dependencies:
            for dep in dependencies:
                if isinstance(dep, str):
                    # Simple string format: "name>=version"
                    if ">=" in dep or "==" in dep or "<=" in dep or ">" in dep or "<" in dep:
                        parts = (
                            dep.replace(">=", " >=")
                            .replace("==", " ==")
                            .replace("<=", " <=")
                            .replace(">", " >")
                            .replace("<", " <")
                            .split()
                        )
                        if len(parts) >= 2:
                            parsed_deps.append(
                                PluginDependency(name=parts[0], version_spec=" ".join(parts[1:]))
                            )
                        else:
                            parsed_deps.append(PluginDependency(name=dep))
                    else:
                        parsed_deps.append(PluginDependency(name=dep))
                elif isinstance(dep, dict):
                    # Dictionary format
                    parsed_deps.append(PluginDependency(**dep))

        # Create manifest
        manifest = PluginManifest(
            name=plugin_name,
            version=version,
            type=plugin_type,
            author=author,
            description=description or cls.__doc__ or "",
            min_panther_version=min_panther_version,
            dependencies=parsed_deps,
            entry_point=f"{cls.__module__}.{cls.__name__}",
            **kwargs,
        )

        # Store in global registry
        plugin_id = f"{plugin_type.value}:{plugin_name}"
        _DECORATED_PLUGINS[plugin_id] = (cls, manifest)

        # Add manifest as class attribute
        cls._PLUGIN_MANIFEST = manifest

        # Add helper methods
        @classmethod
        def get_plugin_manifest(cls) -> PluginManifest:
            return cls._PLUGIN_MANIFEST

        @classmethod
        def get_plugin_id(cls) -> str:
            return f"{cls._PLUGIN_MANIFEST.type.value}:{cls._PLUGIN_MANIFEST.name}"

        cls.get_plugin_manifest = get_plugin_manifest
        cls.get_plugin_id = get_plugin_id

        # Log registration
        logger = logging.getLogger("PluginDecorator")
        logger.debug(
            "Registered plugin: %s v%s (type: %s)", plugin_name, version, plugin_type.value
        )

        return cls

    return decorator


def plugin_version(version: str):
    """
    Simple decorator to set plugin version.

    Usage:
        @plugin_version("2.0.0")
        class MyPlugin:
            pass
    """

    def decorator(cls: type) -> type:
        cls.PLUGIN_VERSION = version
        return cls

    return decorator


def plugin_dependency(*dependencies: str):
    """
    Decorator to declare plugin dependencies.

    Usage:
        @plugin_dependency("quic_protocol>=1.0.0", "network_environment")
        class MyPlugin:
            pass
    """

    def decorator(cls: type) -> type:
        if not hasattr(cls, "PLUGIN_DEPENDENCIES"):
            cls.PLUGIN_DEPENDENCIES = []
        cls.PLUGIN_DEPENDENCIES.extend(dependencies)
        return cls

    return decorator


def plugin_capability(*capabilities: str):
    """
    Decorator to declare plugin capabilities.

    Usage:
        @plugin_capability("tls", "http3", "0rtt")
        class QuicPlugin:
            pass
    """

    def decorator(cls: type) -> type:
        if not hasattr(cls, "PLUGIN_CAPABILITIES"):
            cls.PLUGIN_CAPABILITIES = []
        cls.PLUGIN_CAPABILITIES.extend(capabilities)
        return cls

    return decorator


def supported_protocol(*protocols: str):
    """
    Decorator to declare supported protocols.

    Usage:
        @supported_protocol("quic", "http3")
        class MyImplementation:
            pass
    """

    def decorator(cls: type) -> type:
        if not hasattr(cls, "SUPPORTED_PROTOCOLS"):
            cls.SUPPORTED_PROTOCOLS = []
        cls.SUPPORTED_PROTOCOLS.extend(protocols)
        return cls

    return decorator


def plugin_config_schema(schema: dict[str, Any]):
    """
    Decorator to declare plugin configuration schema.

    Usage:
        @plugin_config_schema({
            "port": "number",
            "host": "string",
            "tls_enabled": "boolean"
        })
        class MyPlugin:
            pass
    """

    def decorator(cls: type) -> type:
        cls.PLUGIN_CONFIG_SCHEMA = schema
        return cls

    return decorator


def requires_plugin(plugin_id: str, version_spec: str = "*"):
    """
    Method decorator to declare that a method requires another plugin.

    Usage:
        class MyPlugin:
            @requires_plugin("environment:docker_compose", ">=1.0.0")
            def deploy(self):
                pass
    """

    def decorator(func):
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            # This is mainly for documentation/validation purposes
            # Actual dependency checking happens at plugin load time
            return func(self, *args, **kwargs)

        # Add metadata to function
        if not hasattr(func, "_required_plugins"):
            func._required_plugins = []
        func._required_plugins.append((plugin_id, version_spec))

        return wrapper

    return decorator


def get_decorated_plugins() -> dict[str, tuple[type, PluginManifest]]:
    """
    Get all plugins registered via decorators.

    Returns:
        Dictionary mapping plugin IDs to (class, manifest) tuples
    """
    return _DECORATED_PLUGINS.copy()


def clear_decorated_plugins():
    """Clear the decorated plugins registry (mainly for testing)."""
    _DECORATED_PLUGINS.clear()
