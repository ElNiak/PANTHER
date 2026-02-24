"""Environment configuration models."""

from typing import Any, Dict, List, Optional, Type, TypeVar

from pydantic import Field, validator

from .base_model import BaseUnifiedModel

T = TypeVar("T", bound="BaseUnifiedModel")


class EnvironmentConfig(BaseUnifiedModel):
    """Base environment configuration."""

    type: str = Field(..., description="Environment type")

    # Background monitoring configuration for non-blocking service health checks
    enable_background_monitoring: bool = Field(
        True, description="Enable background monitoring"
    )
    monitoring_interval_seconds: int = Field(
        5, description="Monitoring interval in seconds"
    )
    failure_threshold_count: int = Field(1, description="Failure threshold count")
    allow_partial_deployment: bool = Field(
        False, description="Allow partial deployment"
    )
    critical_services: List[str] = Field(
        default_factory=list, description="Critical services list"
    )

    # Plugin-specific configuration - exactly like ServiceConfig
    plugin_config: Optional[Dict[str, Any]] = Field(
        default_factory=dict, description="Plugin-specific configuration"
    )

    def get_plugin_config(self, config_class: Type[T], validate: bool = True) -> T:
        """Get typed plugin configuration with defaults.

        This method creates an instance of the plugin config class, using values
        from plugin_config where available and defaults from the class where not.

        For nested Pydantic models, it handles type conversion intelligently.

        Args:
            config_class: The plugin configuration class
            validate: Whether to validate using PluginConfigResolver (if available)

        Returns:
            Typed plugin configuration instance
        """
        # For plugin configs that have complex nested defaults, we need to be careful
        # First, create an instance with all defaults
        default_instance = config_class()

        # Get default values (handle both Pydantic v1 and v2)
        try:
            default_dict = default_instance.model_dump()
        except AttributeError:
            default_dict = default_instance.dict()

        # Deep merge plugin_config values over defaults with type awareness
        merged_config = self._deep_merge_with_type_conversion(
            default_dict, self.plugin_config, config_class
        )

        # Create final instance with merged values
        instance = config_class(**merged_config)

        # Optional validation with PluginConfigResolver
        if validate and hasattr(self, "type"):
            try:
                from panther.plugins.core.plugin_config_resolver import (
                    get_plugin_config_resolver,
                )

                resolver = get_plugin_config_resolver()

                # Try to find the expected config class
                expected_class = resolver.resolve_environment_config_class(
                    environment_type=self.type,
                    category=(
                        "network"
                        if isinstance(self, NetworkEnvironmentConfig)
                        else "execution"
                    ),
                )

                if expected_class and expected_class != config_class:
                    # Log warning but don't fail
                    import logging

                    logger = logging.getLogger(__name__)
                    logger.warning(
                        f"Plugin config class mismatch: expected {expected_class.__name__}, "
                        f"got {config_class.__name__}"
                    )
            except Exception as e:
                # Validation is optional, so we just log and continue
                import logging

                logger = logging.getLogger(__name__)
                logger.debug(f"Could not validate plugin config with resolver: {e}")

        return instance

    def _deep_merge_configs(
        self, defaults: Dict[str, Any], overrides: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Deep merge configuration dictionaries, preserving structure.

        Args:
            defaults: Default configuration with full structure
            overrides: Override values that may have simplified structure

        Returns:
            Merged configuration
        """
        result = defaults.copy()

        for key, value in overrides.items():
            if key in result:
                if isinstance(result[key], dict) and isinstance(value, dict):
                    # Recursive merge for nested dicts
                    result[key] = self._deep_merge_configs(result[key], value)
                else:
                    # Direct override for non-dict values
                    result[key] = value
            else:
                # New key not in defaults
                result[key] = value

        return result

    def _deep_merge_with_type_conversion(
        self,
        defaults: Dict[str, Any],
        overrides: Optional[Dict[str, Any]],
        config_class: Type[T],
    ) -> Dict[str, Any]:
        """Deep merge with type awareness for plugin configs.

        This handles the case where plugin_config may have simplified values
        that need to be converted to match the config class structure.

        Args:
            defaults: Default values from config class
            overrides: Override values from plugin_config
            config_class: The target configuration class

        Returns:
            Merged configuration ready for instantiation
        """
        if not overrides:
            return defaults

        # Use the standard deep merge
        return self._deep_merge_configs(defaults, overrides)


class NetworkEnvironmentConfig(EnvironmentConfig):
    """Base network environment configuration."""

    type: str = Field(..., description="Environment type")

    # Allow extra fields for environment-specific parameters


# Network environment configurations have been moved to plugin directories:
# - DockerComposeConfig -> panther/plugins/environments/network_environment/docker_compose/config_schema.py
# - LocalhostSingleContainerConfig -> panther/plugins/environments/network_environment/localhost_single_container/config_schema.py
# - ShadowNsConfig -> panther/plugins/environments/network_environment/shadow_ns/config_schema.py


class ExecutionEnvironmentConfig(EnvironmentConfig):
    """Base execution environment configuration."""

    type: str = Field(..., description="Environment type")
    enabled: bool = Field(True, description="Whether this environment is enabled")

    # Allow extra fields for environment-specific parameters


# Note: Plugin-specific configurations have been moved to their respective plugin directories
# to support dynamic plugin discovery. Only base classes remain here.
#
# For example:
# - StraceConfig -> panther/plugins/environments/execution_environment/strace/config_schema.py
# - GperfCpuConfig -> panther/plugins/environments/execution_environment/gperf_cpu/config_schema.py
# - etc.
#
# This allows new plugins to be added without modifying core code.
