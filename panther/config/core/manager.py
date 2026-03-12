"""Primary configuration manager combining all functionality via mixins.

Implements a configuration management system using the Mixin pattern
to compose capabilities from specialized components.

**Mixin Composition** (order matters for MRO):
1. ConfigLoadingMixin: Core configuration file loading and parsing
2. EnvironmentHandlingMixin: Environment variable resolution and path handling
3. ValidationOperationsMixin: Multi-stage validation with error enrichment
4. CachingMixin: Performance optimization through intelligent caching
5. ErrorHandlerMixin: Centralized error handling and recovery

**Integration Points**:
- Plugin system integration for dynamic configuration discovery
- MetricsCollector integration for performance monitoring
- Context manager support for automatic cleanup and error handling
"""

from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union

from panther.core.exceptions.error_handler_mixin import ErrorHandlerMixin
from panther.core.metrics.metrics_collector import MetricsCollector

if TYPE_CHECKING:
    from .components.validators import ValidationResult
    from .models import ExperimentConfig, GlobalConfig, ServiceConfig

from .mixins import (
    CachingMixin,
    ConfigLoadingMixin,
    EnvironmentHandlingMixin,
    ValidationOperationsMixin,
)


class ConfigurationManager(
    ConfigLoadingMixin,
    EnvironmentHandlingMixin,
    ValidationOperationsMixin,
    CachingMixin,
    ErrorHandlerMixin,
):
    """Primary configuration manager combining all functionality via mixins.

    Composed from 4 mixins + ErrorHandlerMixin:
    - ConfigLoadingMixin: YAML/JSON parsing with environment variable substitution
    - EnvironmentHandlingMixin: ``${VAR}`` interpolation and PANTHER_* env mappings
    - ValidationOperationsMixin: Schema validation + business rules + auto-fix
    - CachingMixin: In-memory caching for experiments, validations, plugins

    Usage::

        manager = ConfigurationManager()
        config = manager.load_experiment_config("experiment.yaml")

        plugins = manager.discover_plugins()
        versions = manager.discover_available_versions("quic")
    """

    def __init__(
        self,
        experiment_file: Optional[str] = None,
        output_dir: Optional[str] = None,
        exec_env_dir: Optional[str] = "",
        net_env_dir: Optional[str] = "",
        iut_dir: Optional[str] = "",
        testers_dir: Optional[str] = "",
        metrics_collector: Optional[MetricsCollector] = None,
        debug_override: bool = False,
        panther_dir: Optional[Path] = None,
        enable_cache: bool = True,
        auto_fix_configs: bool = True,
    ):
        """Initialize with all legacy parameters preserved.

        Args:
            experiment_file: Path to experiment configuration file
            output_dir: Output directory for experiment results
            exec_env_dir: Execution environment plugins directory
            net_env_dir: Network environment plugins directory
            iut_dir: IUT plugins directory
            testers_dir: Testers plugins directory
            metrics_collector: Metrics collector instance
            debug_override: Override debug settings
            panther_dir: PANTHER installation directory
            enable_cache: Enable configuration caching
            auto_fix_configs: Enable automatic configuration fixing
        """
        # Initialize all mixins
        super().__init__()

        # Store parameters
        self.experiment_file = experiment_file
        self.output_dir = output_dir
        self.exec_env_dir = exec_env_dir
        self.net_env_dir = net_env_dir
        self.iut_dir = iut_dir
        self.testers_dir = testers_dir
        self.metrics_collector = metrics_collector
        self.debug_override = debug_override
        self.panther_dir = panther_dir or self._get_default_panther_dir()
        self.enable_cache = enable_cache
        self.auto_fix_configs = auto_fix_configs

        # Initialize components
        self._initialize_components()

        # State tracking
        self.current_experiment_config: Optional["ExperimentConfig"] = None
        self.current_global_config: Optional["GlobalConfig"] = None
        self.validation_results: Dict[str, "ValidationResult"] = {}

        # Statistics tracking
        self._total_validations = 0
        self._validation_failures = 0
        self._auto_fixes_applied = 0

        self.logger.info("ConfigurationManager initialized")

    def _initialize_components(self):
        """Initialize all components used by mixins."""
        # Initialize caches
        self._loaded_experiments: Dict[str, "ExperimentConfig"] = {}
        self._validation_cache: Dict[str, bool] = {}
        self._plugin_cache: Optional[Dict[str, Any]] = None
        self._schema_cache: Optional[Dict[str, Any]] = None
        self._version_cache: Dict[str, Dict[str, List[str]]] = {}

        # Timing statistics
        self._timing_stats = {
            "config_loads": [],
            "validations": [],
            "plugin_discoveries": [],
        }

        # Initialize validators
        try:
            from .components.validators import BusinessRulesValidator, ConfigValidator

            self.validators = [
                BusinessRulesValidator(),
                # Add other validators as needed
            ]
            self.config_validator = ConfigValidator()

            self.logger.debug(f"Initialized {len(self.validators)} validators")

        except Exception as e:
            self.logger.error(
                "Failed to initialize validators: %s — configuration validation "
                "is disabled, all configs will be accepted without validation",
                e,
            )
            self.validators = []
            self.config_validator = None

        # Initialize plugin components using unified plugin manager
        try:
            from panther.plugins.plugin_manager import PluginManager

            # Set up plugin discovery
            plugin_dirs = []
            if self.exec_env_dir:
                plugin_dirs.append(self.exec_env_dir)
            if self.net_env_dir:
                plugin_dirs.append(self.net_env_dir)
            if not plugin_dirs:
                # Use default plugin directories
                plugin_base = self.panther_dir / "panther" / "plugins"
                plugin_dirs = [
                    str(plugin_base / "protocols"),  # Add protocols directory
                    str(plugin_base / "environments"),
                    str(plugin_base / "services"),
                ]

            self.plugin_discovery = PluginManager(
                plugin_directories=plugin_dirs,
                enable_cache=self.enable_cache,
                cache_ttl=3600,
            )

        except Exception as e:
            self.logger.error(
                "Failed to initialize plugin components: %s — plugin discovery "
                "is disabled, plugin lists will be empty",
                e,
            )
            self.plugin_discovery = None

    def _get_default_panther_dir(self) -> Path:
        """Get default PANTHER directory.

        Returns:
            Path to PANTHER installation
        """
        # Try to find PANTHER directory
        current = Path(__file__).resolve()

        # Go up until we find the panther directory
        while current.parent != current:
            if (current / "panther").exists():
                return current
            current = current.parent

        # Fallback to current working directory
        return Path.cwd()

    # Context manager support
    def __enter__(self):
        """Enter context manager."""
        self.logger.debug("Entering ConfigurationManager context")
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context manager."""
        self.logger.debug("Exiting ConfigurationManager context")

        # Log any exceptions
        if exc_type is not None:
            self.logger.error(f"Exception in context: {exc_type.__name__}: {exc_val}")

        # Return None to propagate exceptions normally
        return None

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"ConfigurationManager("
            f"experiments={len(self._loaded_experiments)}, "
            f"cache={'enabled' if self.enable_cache else 'disabled'}, "
            f"auto_fix={'enabled' if self.auto_fix_configs else 'disabled'}"
            f")"
        )

    # Additional utility methods
    def list_plugin_parameters(
        self,
        name: str,
        plugin_type: Optional[str] = None,
        protocol: Optional[str] = None,
    ) -> Dict[str, Any]:
        """List parameters for a plugin (ConfigLoader compatibility).

        Args:
            name: Plugin name
            plugin_type: Optional plugin type
            protocol: Optional protocol

        Returns:
            Plugin parameters with descriptions
        """
        if self.plugin_discovery:
            # Auto-detect plugin type if not provided
            if not plugin_type:
                plugin_type = self._auto_detect_plugin_type(name, protocol)

            if not plugin_type:
                return {"error": f"Could not determine plugin type for '{name}'"}

            # Get plugin metadata
            metadata = self.plugin_discovery.get_plugin(name)
            if metadata:
                return {
                    "plugin": name,
                    "type": plugin_type,
                    "protocol": protocol,
                    "parameters": [param.to_dict() for param in metadata.parameters],
                }

            # Try schema registry for config model
            try:
                from panther.plugins.core.plugin_decorators import get_config_model

                config_model = get_config_model(name)
                if config_model is not None:
                    return {
                        "plugin": name,
                        "type": plugin_type,
                        "protocol": protocol,
                        "parameters": {
                            k: str(v.annotation)
                            for k, v in config_model.model_fields.items()
                        },
                    }
            except ImportError:
                pass

        return {"error": f"Plugin '{name}' not found or plugin discovery not available"}

    def _auto_detect_plugin_type(
        self, name: str, protocol: Optional[str] = None
    ) -> Optional[str]:
        """Auto-detect plugin type (ConfigLoader compatibility).

        Args:
            name: Plugin name
            protocol: Optional protocol hint

        Returns:
            Detected plugin type or None
        """
        if self.plugin_discovery:
            # Check enhanced plugin metadata
            metadata = self.plugin_discovery.get_plugin(name)
            if metadata:
                return metadata.type.value

        # Pattern matching fallback
        if name.startswith("panther_"):
            return "testers"

        if protocol:
            # Protocol-specific implementations are usually IUTs
            return "iut"

        return None

    # Plugin Discovery Delegation Methods
    def discover_plugins(self, force_refresh: bool = False) -> Dict[str, Any]:
        """Discover all available plugins.

        Args:
            force_refresh: Force re-discovery even if cached

        Returns:
            Dictionary of plugin name to metadata
        """
        if self.plugin_discovery:
            plugins_dict = self.plugin_discovery.discover_plugins(force_refresh)
            return {name: plugin.to_dict() for name, plugin in plugins_dict.items()}
        return {}

    def get_plugin_metadata(self, plugin_name: str) -> Optional[Dict[str, Any]]:
        """Get metadata for a specific plugin.

        Args:
            plugin_name: Name of the plugin

        Returns:
            Plugin metadata or None if not found
        """
        if self.plugin_discovery:
            metadata = self.plugin_discovery.get_plugin(plugin_name)
            return metadata.to_dict() if metadata else None
        return None

    def discover_available_versions(
        self, protocol: Optional[str] = None
    ) -> Dict[str, List[str]]:
        """Discover available versions for protocols.

        Args:
            protocol: Optional protocol to filter by

        Returns:
            Dictionary mapping protocol names to version lists
        """
        if self.plugin_discovery:
            return self.plugin_discovery.discover_protocol_versions(protocol)
        return {}

    def get_plugin_schemas(self) -> Dict[str, type]:
        """Get all plugin config model classes from the schema registry.

        Returns:
            Dictionary mapping plugin names to config model classes
        """
        try:
            from panther.plugins.core.plugin_decorators import get_all_config_models

            return get_all_config_models()
        except ImportError:
            return {}


# Global instance management
_global_config_manager: Optional[ConfigurationManager] = None


def get_config_manager() -> ConfigurationManager:
    """Get the global configuration manager instance (lazy initialization).

    Returns:
        Global ConfigurationManager instance
    """
    global _global_config_manager
    if _global_config_manager is None:
        _global_config_manager = ConfigurationManager()
    return _global_config_manager


# Convenience functions
def load_experiment(
    config_path: Union[str, Path], validate: bool = True, auto_fix: bool = True
) -> "ExperimentConfig":
    """Convenience function to load experiment configuration.

    Args:
        config_path: Path to configuration file
        validate: Whether to validate configuration
        auto_fix: Whether to auto-fix issues

    Returns:
        Loaded ExperimentConfig instance
    """
    return get_config_manager().load_experiment_config(
        config_path, validate=validate, auto_fix=auto_fix
    )


def validate_service(service_dict: Dict[str, Any]) -> "ServiceConfig":
    """Convenience function to validate service configuration.

    Args:
        service_dict: Service configuration dictionary

    Returns:
        Validated ServiceConfig instance
    """
    return get_config_manager().validate_service_configuration(service_dict)


def discover_versions(protocol: Optional[str] = None) -> Dict[str, List[str]]:
    """Convenience function to discover available protocol versions.

    Args:
        protocol: Optional protocol to filter by

    Returns:
        Dictionary of protocol to version lists
    """
    return get_config_manager().discover_available_versions(protocol)
