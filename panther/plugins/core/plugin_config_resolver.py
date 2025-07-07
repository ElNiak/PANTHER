"""
Dynamic plugin configuration resolver for PANTHER.

This module provides dynamic discovery and resolution of plugin configuration classes,
enabling true separation of concerns where plugins can be added without modifying core code.
"""

import importlib
import logging
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Type

from pydantic import BaseModel

from panther.config.core.models.environment import (
    EnvironmentConfig,
    ExecutionEnvironmentConfig,
    NetworkEnvironmentConfig,
)
from panther.config.core.models.plugin import (
    BasePluginConfig,
    ExecutionEnvironmentPluginConfig,
    NetworkEnvironmentPluginConfig,
    ProtocolPluginConfig,
    ServicePluginConfig,
)

logger = logging.getLogger(__name__)


class PluginConfigResolver:
    """
    Dynamically resolves plugin configuration classes based on plugin type and name.

    This class eliminates the need for hardcoded plugin configurations in core code
    by discovering and loading config classes from plugin directories at runtime.
    """

    def __init__(self, plugin_base_dir: Optional[Path] = None):
        """
        Initialize the plugin config resolver.

        Args:
            plugin_base_dir: Base directory for plugins. Defaults to panther/plugins
        """
        if plugin_base_dir is None:
            plugin_base_dir = Path(__file__).parent
        self.plugin_base_dir = plugin_base_dir
        self._config_cache: Dict[str, Type[BaseModel]] = {}

    @lru_cache(maxsize=128)
    def _find_config_class_in_module(
        self, module_path: str, base_class: Type
    ) -> Optional[Type[BaseModel]]:
        """
        Find a configuration class in a module that inherits from the specified base class.

        Args:
            module_path: Python module path
            base_class: Base class to look for

        Returns:
            Config class if found, None otherwise
        """
        try:
            module = importlib.import_module(module_path)

            # Look for classes that inherit from the base class
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (
                    isinstance(attr, type)
                    and issubclass(attr, base_class)
                    and attr is not base_class
                    and attr.__name__.endswith("Config")
                ):
                    return attr

        except ImportError as e:
            logger.debug(f"Could not import module {module_path}: {e}")
        except Exception as e:
            logger.warning(f"Error inspecting module {module_path}: {e}")

        return None

    def resolve_environment_config_class(
        self, env_type: str, env_category: str
    ) -> Optional[Type[BaseModel]]:
        """
        Resolve environment configuration class based on type and category.

        Args:
            env_type: Environment type (e.g., 'docker_compose', 'strace')
            env_category: Category ('network_environment' or 'execution_environment')

        Returns:
            Configuration class or None if not found
        """
        cache_key = f"{env_category}:{env_type}"

        # Check cache first
        if cache_key in self._config_cache:
            return self._config_cache[cache_key]

        # Determine base class based on category
        if env_category == "network_environment":
            plugin_base_class = NetworkEnvironmentPluginConfig
            runtime_base_class = NetworkEnvironmentConfig
        elif env_category == "execution_environment":
            plugin_base_class = ExecutionEnvironmentPluginConfig
            runtime_base_class = ExecutionEnvironmentConfig
        else:
            logger.warning(f"Unknown environment category: {env_category}")
            return None

        # Try to find config in plugin directory
        config_paths = [
            # Standard location: plugins/environments/{category}/{env_type}/config_schema.py
            f"panther.plugins.environments.{env_category}.{env_type}.config_schema",
            # Alternative location: plugins/environments/{category}/config_schema.py
            f"panther.plugins.environments.{env_category}.config_schema",
        ]

        for module_path in config_paths:
            # First try plugin config base class
            config_class = self._find_config_class_in_module(
                module_path, plugin_base_class
            )
            if config_class:
                self._config_cache[cache_key] = config_class
                logger.debug(
                    f"Found plugin config {config_class.__name__} for {env_type}"
                )
                return config_class

            # Then try runtime config base class (for backward compatibility)
            config_class = self._find_config_class_in_module(
                module_path, runtime_base_class
            )
            if config_class:
                self._config_cache[cache_key] = config_class
                logger.debug(
                    f"Found runtime config {config_class.__name__} for {env_type}"
                )
                return config_class

        logger.debug(f"No config class found for {env_type} in {env_category}")
        return None

    def resolve_service_config_class(
        self, service_type: str, protocol: str, name: str
    ) -> Optional[Type[BaseModel]]:
        """
        Resolve service configuration class.

        Args:
            service_type: Service type ('iut' or 'testers')
            protocol: Protocol name (e.g., 'quic', 'http')
            name: Service implementation name

        Returns:
            Configuration class or None if not found
        """
        cache_key = f"service:{service_type}:{protocol}:{name}"

        if cache_key in self._config_cache:
            return self._config_cache[cache_key]

        # Build module path
        if service_type == "testers":
            module_path = (
                f"panther.plugins.services.{service_type}.{name}.config_schema"
            )
        else:
            module_path = f"panther.plugins.services.{service_type}.{protocol}.{name}.config_schema"

        config_class = self._find_config_class_in_module(
            module_path, ServicePluginConfig
        )
        if config_class:
            self._config_cache[cache_key] = config_class
            logger.debug(f"Found service config {config_class.__name__} for {name}")

        return config_class

    def resolve_protocol_config_class(
        self, protocol_name: str
    ) -> Optional[Type[BaseModel]]:
        """
        Resolve protocol configuration class.

        Args:
            protocol_name: Protocol name

        Returns:
            Configuration class or None if not found
        """
        cache_key = f"protocol:{protocol_name}"

        if cache_key in self._config_cache:
            return self._config_cache[cache_key]

        module_paths = [
            f"panther.plugins.protocols.client_server.{protocol_name}.config_schema",
            f"panther.plugins.protocols.peer_to_peer.{protocol_name}.config_schema",
        ]

        for module_path in module_paths:
            config_class = self._find_config_class_in_module(
                module_path, ProtocolPluginConfig
            )
            if config_class:
                self._config_cache[cache_key] = config_class
                logger.debug(
                    f"Found protocol config {config_class.__name__} for {protocol_name}"
                )
                return config_class

        return None

    def create_environment_config_dynamic(
        self, config_data: Dict[str, Any], env_category: str
    ) -> BaseModel:
        """
        Dynamically create an environment configuration instance.

        Args:
            config_data: Configuration data dictionary
            env_category: Environment category

        Returns:
            Configuration instance

        Raises:
            ValueError: If config class cannot be resolved
        """
        env_type = config_data.get("type")
        if not env_type:
            raise ValueError("Configuration must include 'type' field")

        config_class = self.resolve_environment_config_class(env_type, env_category)

        if not config_class:
            # Fall back to base class
            if env_category == "network_environment":
                config_class = NetworkEnvironmentConfig
            elif env_category == "execution_environment":
                config_class = ExecutionEnvironmentConfig
            else:
                config_class = EnvironmentConfig

            logger.warning(
                f"No specific config class found for {env_type}, using base class {config_class.__name__}"
            )

        return config_class(**config_data)

    def list_available_plugins(self) -> Dict[str, List[str]]:
        """
        List all available plugins by category.

        Returns:
            Dictionary mapping categories to list of plugin names
        """
        available = {
            "network_environments": [],
            "execution_environment": [],
            "services": [],
            "protocols": [],
        }

        # Scan plugin directories
        env_base = self.plugin_base_dir / "environments"

        # Network environments
        net_env_dir = env_base / "network_environment"
        if net_env_dir.exists():
            for path in net_env_dir.iterdir():
                if path.is_dir() and (path / "config_schema.py").exists():
                    available["network_environments"].append(path.name)

        # Execution environments
        exec_env_dir = env_base / "execution_environment"
        if exec_env_dir.exists():
            for path in exec_env_dir.iterdir():
                if path.is_dir() and (path / "config_schema.py").exists():
                    available["execution_environment"].append(path.name)

        return available

    def clear_cache(self):
        """Clear the configuration cache."""
        self._config_cache.clear()
        self._find_config_class_in_module.cache_clear()


# Global instance for convenience
_resolver = None


def get_plugin_config_resolver() -> PluginConfigResolver:
    """Get the global plugin config resolver instance."""
    global _resolver
    if _resolver is None:
        _resolver = PluginConfigResolver()
    return _resolver
