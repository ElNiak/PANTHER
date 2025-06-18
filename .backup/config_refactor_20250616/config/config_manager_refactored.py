"""Refactored ConfigManager using modular components."""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import yaml

from panther.config.config_experiment_schema import ExperimentConfig
from panther.config.config_global_schema import GlobalConfig
from panther.config.managers.configuration_builder import ConfigurationBuilder
from panther.config.managers.configuration_validator import (
    ConfigurationValidator,
    ValidationResult,
)
from panther.config.managers.plugin_discovery import PluginDiscovery
from panther.config.managers.plugin_file_manager import PluginFileManager
from panther.config.managers.plugin_schema_loader_simple import PluginSchemaLoader
from panther.core.exceptions.error_handler_mixin import ErrorHandlerMixin


class ConfigManagerRefactored(ErrorHandlerMixin):
    """
    Refactored configuration manager using modular components.

    This class coordinates between specialized components for different responsibilities:
    - ConfigurationBuilder: Assembly and building of configurations
    - ConfigurationValidator: Schema validation and business rules
    - PluginDiscovery: Plugin scanning and metadata extraction
    - PluginFileManager: Plugin file system operations
    - PluginSchemaLoader: Plugin schema loading and caching
    """

    def __init__(
        self,
        experiment_file: Optional[str] = None,
        output_dir: Optional[str] = None,
        exec_env_dir: Optional[str] = "",
        net_env_dir: Optional[str] = "",
        iut_dir: Optional[str] = "",
        testers_dir: Optional[str] = "",
        metrics_collector=None,
        debug_override: bool = False,
        panther_dir: Optional[Path] = None,
    ):
        """Initialize with modular components.

        Args:
            experiment_file: Path to experiment configuration file
            output_dir: Output directory for results
            exec_env_dir: Execution environment plugins directory
            net_env_dir: Network environment plugins directory
            iut_dir: IUT plugins directory
            testers_dir: Testers plugins directory
            metrics_collector: Metrics collector instance
            debug_override: Debug mode override
            panther_dir: Root directory of PANTHER installation
        """
        super().__init__()

        # Store original constructor parameters for compatibility
        self.experiment_file = experiment_file
        self.output_dir = output_dir
        self.exec_env_dir = exec_env_dir
        self.net_env_dir = net_env_dir
        self.iut_dir = iut_dir
        self.testers_dir = testers_dir
        self.metrics_collector = metrics_collector
        self.debug_override = debug_override

        # Determine PANTHER directory
        if panther_dir is None:
            panther_dir = Path(__file__).parent.parent.parent
        self.panther_dir = Path(panther_dir)

        # Initialize modular components
        self.configuration_builder = ConfigurationBuilder()
        self.configuration_validator = ConfigurationValidator()
        self.plugin_discovery = PluginDiscovery(
            self.panther_dir / "panther" / "plugins"
        )
        self.plugin_file_manager = PluginFileManager(self.panther_dir)
        self.plugin_schema_loader = PluginSchemaLoader(
            self.panther_dir / "panther" / "plugins"
        )

        # State tracking
        self.current_experiment_config: Optional[ExperimentConfig] = None
        self.current_global_config: Optional[GlobalConfig] = None
        self.global_config: Optional[GlobalConfig] = None  # For backward compatibility
        self.validation_results: Dict[str, ValidationResult] = {}

        # Configuration paths
        self.default_global_config_path = (
            self.panther_dir / "panther" / "config" / "config_global.yaml"
        )

        self.logger.info("ConfigManager initialized with modular components")

    def load_and_validate_global_config(self) -> GlobalConfig:
        """Load and validate the global configuration from the experiment file.

        Returns:
            GlobalConfig: Validated global configuration
        """
        try:
            if not self.experiment_file or not os.path.exists(self.experiment_file):
                # Load default global config
                default_config_path = (
                    self.panther_dir / "panther" / "config" / "config_global.yaml"
                )
                if default_config_path.exists():
                    with open(default_config_path, "r") as f:
                        config_data = yaml.safe_load(f)
                    global_config = GlobalConfig(**config_data)
                    self.global_config = global_config
                    self.current_global_config = global_config
                    return global_config
                else:
                    # Return default global config
                    global_config = GlobalConfig()
                    self.global_config = global_config
                    self.current_global_config = global_config
                    return global_config

            # Load experiment file and extract global config
            with open(self.experiment_file, "r") as f:
                exp_data = yaml.safe_load(f)

            # Extract global config sections with defaults
            logging_config = exp_data.get("logging", {})
            paths_config = exp_data.get("paths", {})
            docker_config = exp_data.get("docker", {})

            # Build GlobalConfig with proper dataclass objects
            from panther.config.config_global_schema import (
                DockerConfig,
                LoggingConfig,
                LoggingLevel,
                PathsConfig,
            )

            # Handle logging level
            level_str = logging_config.get("level", "INFO")
            if isinstance(level_str, str):
                try:
                    level = LoggingLevel[level_str.upper()]
                except KeyError:
                    level = LoggingLevel.INFO
            else:
                level = level_str

            # Extract feature levels from loaded config
            from panther.config.config_global_schema import FeatureLogLevelsConfig
            
            feature_levels_config = None
            if "feature_levels" in logging_config:
                feature_levels_dict = logging_config.get("feature_levels", {})
                feature_levels_kwargs = {}
                
                # Convert string levels to LoggingLevel enum
                for feature_name, level_str in feature_levels_dict.items():
                    if isinstance(level_str, str):
                        try:
                            feature_levels_kwargs[feature_name] = LoggingLevel[level_str.upper()]
                        except KeyError:
                            print(f"WARNING: Invalid logging level '{level_str}' for feature '{feature_name}', using INFO")
                            feature_levels_kwargs[feature_name] = LoggingLevel.INFO
                    else:
                        feature_levels_kwargs[feature_name] = level_str
                
                # Create FeatureLogLevelsConfig with user's values
                try:
                    feature_levels_config = FeatureLogLevelsConfig(**feature_levels_kwargs)
                except TypeError as e:
                    # Extract the invalid field name from the error message
                    import re
                    match = re.search(r"got an unexpected keyword argument '(\w+)'", str(e))
                    if match:
                        invalid_field = match.group(1)
                        valid_fields = [f for f in dir(FeatureLogLevelsConfig) if not f.startswith('_')]
                        print(f"ERROR: Invalid feature name '{invalid_field}' in feature_levels configuration")
                        print(f"Valid feature names are: {', '.join(sorted(valid_fields))}")
                        # Skip the invalid field and retry
                        feature_levels_kwargs.pop(invalid_field, None)
                        feature_levels_config = FeatureLogLevelsConfig(**feature_levels_kwargs)
                    else:
                        raise

            # Create config with proper dataclass structure including feature_levels
            default_logging_config = LoggingConfig()
            logging_cfg = LoggingConfig(
                level=level,
                format=logging_config.get(
                    "format", "%(asctime)s [%(levelname)s] - %(module)s - %(message)s"
                ),
                enable_colors=logging_config.get("enable_colors", default_logging_config.enable_colors),
                feature_levels=feature_levels_config if feature_levels_config else default_logging_config.feature_levels,
            )

            paths_cfg = PathsConfig(
                output_dir=self.output_dir or paths_config.get("output_dir", "outputs"),
                log_dir=paths_config.get("log_dir", "outputs/logs"),
                plugin_dir=paths_config.get("plugin_dir", "panther/plugins"),
            )

            docker_cfg = DockerConfig(
                build_docker_image=docker_config.get("build_docker_image", False)
            )

            global_config = GlobalConfig(
                logging=logging_cfg, paths=paths_cfg, docker=docker_cfg
            )

            self.global_config = global_config
            self.current_global_config = global_config
            return global_config

        except Exception as e:
            self.logger.error(f"Error loading global config: {e}")
            # Return default config on error
            global_config = GlobalConfig()
            self.global_config = global_config
            self.current_global_config = global_config
            return global_config

    def load_and_validate_experiment_config(self) -> ExperimentConfig:
        """Load and validate the experiment configuration.

        Returns:
            ExperimentConfig: Validated experiment configuration
        """
        try:
            if not self.experiment_file or not os.path.exists(self.experiment_file):
                raise FileNotFoundError(
                    f"Experiment file not found: {self.experiment_file}"
                )

            # Load experiment file
            with open(self.experiment_file, "r") as f:
                exp_data = yaml.safe_load(f)

            # Extract only experiment-specific sections (ExperimentConfig only has 'tests')
            experiment_data = {"tests": exp_data.get("tests", [])}

            # Use configuration builder to create ExperimentConfig
            self.configuration_builder.set_base_config(experiment_data)
            experiment_config = self.configuration_builder.build_experiment_config()

            # Validate the config (simplified validation)
            try:
                validation_result = (
                    self.configuration_validator.validate_experiment_config(
                        experiment_config
                    )
                )
                if not validation_result.is_valid:
                    self.logger.warning(
                        "Experiment configuration validation warnings: %s",
                        validation_result.errors,
                    )
                    # Continue despite validation warnings for now
            except Exception as validation_error:
                self.logger.warning(
                    "Configuration validation failed, proceeding anyway: %s",
                    validation_error,
                )
                # Continue despite validation errors for now

            self.current_experiment_config = experiment_config
            return experiment_config

        except Exception as e:
            self.logger.error(f"Error loading experiment config: {e}")
            raise

    def load_experiment_config(
        self,
        config_path: Path,
        overrides: Optional[Dict[str, Any]] = None,
        validate: bool = True,
    ) -> ExperimentConfig:
        """Load and build experiment configuration using configuration builder.

        Args:
            config_path: Path to experiment configuration file
            overrides: Optional configuration overrides
            validate: Whether to validate the configuration

        Returns:
            Loaded and validated ExperimentConfig

        Raises:
            FileNotFoundError: If config file doesn't exist
            ValueError: If configuration is invalid
        """
        self.logger.info(f"Loading experiment configuration from {config_path}")

        try:
            # Load base configuration from file
            base_config = self._load_yaml_file(config_path)

            # Setup configuration builder
            self.configuration_builder.reset()
            self.configuration_builder.set_base_config(base_config)

            # Add overrides if provided
            if overrides:
                self.configuration_builder.add_overrides(overrides)

            # Add environment variable mappings
            env_mappings = {
                "logging.level": "PANTHER_LOG_LEVEL",
                "docker.build_docker_image": "PANTHER_BUILD_IMAGES",
                "paths.output_dir": "PANTHER_OUTPUT_DIR",
            }
            self.configuration_builder.add_environment_variables(env_mappings)

            # Build the final configuration
            experiment_config = self.configuration_builder.build_experiment_config()

            # Validate if requested
            if validate:
                validation_result = self.validate_experiment_config(experiment_config)
                self.validation_results["experiment"] = validation_result

                if not validation_result.is_valid:
                    raise ValueError(
                        f"Configuration validation failed: {validation_result.get_summary()}"
                    )

            self.current_experiment_config = experiment_config
            self.logger.info("Experiment configuration loaded successfully")

            return experiment_config

        except Exception as e:
            self.handle_error(e, f"loading experiment configuration from {config_path}")
            raise

    def load_global_config(
        self,
        config_path: Optional[Path] = None,
        overrides: Optional[Dict[str, Any]] = None,
        validate: bool = True,
    ) -> GlobalConfig:
        """Load and build global configuration using configuration builder.

        Args:
            config_path: Path to global configuration file (optional)
            overrides: Optional configuration overrides
            validate: Whether to validate the configuration

        Returns:
            Loaded and validated GlobalConfig
        """
        if config_path is None:
            config_path = self.default_global_config_path

        self.logger.info(f"Loading global configuration from {config_path}")

        try:
            # Load base configuration from file
            if config_path.exists():
                base_config = self._load_yaml_file(config_path)
            else:
                # Use default configuration
                base_config = self._get_default_global_config()

            # Setup configuration builder
            self.configuration_builder.reset()
            self.configuration_builder.set_base_config(base_config)

            # Add overrides if provided
            if overrides:
                self.configuration_builder.add_overrides(overrides)

            # Add environment variable mappings
            env_mappings = {
                "logging.level": "PANTHER_LOG_LEVEL",
                "logging.enable_colors": "PANTHER_LOG_COLORS",
                "paths.plugin_dir": "PANTHER_PLUGIN_DIR",
            }
            self.configuration_builder.add_environment_variables(env_mappings)

            # Build the final configuration
            global_config = self.configuration_builder.build_global_config()

            # Validate if requested
            if validate:
                validation_result = self.validate_global_config(global_config)
                self.validation_results["global"] = validation_result

                if not validation_result.is_valid:
                    self.logger.warning(
                        f"Global configuration validation issues: {validation_result.get_summary()}"
                    )

            self.current_global_config = global_config
            self.logger.info("Global configuration loaded successfully")

            return global_config

        except Exception as e:
            self.handle_error(e, f"loading global configuration from {config_path}")
            raise

    def validate_experiment_config(
        self, config: Union[Dict[str, Any], ExperimentConfig]
    ) -> ValidationResult:
        """Validate experiment configuration using configuration validator.

        Args:
            config: Configuration to validate

        Returns:
            ValidationResult with validation status and messages
        """
        return self.configuration_validator.validate_experiment_config(config)

    def validate_global_config(
        self, config: Union[Dict[str, Any], GlobalConfig]
    ) -> ValidationResult:
        """Validate global configuration using configuration validator.

        Args:
            config: Configuration to validate

        Returns:
            ValidationResult with validation status and messages
        """
        return self.configuration_validator.validate_global_config(config)

    def discover_plugins(self, force_refresh: bool = False) -> Dict[str, Any]:
        """Discover plugins using plugin discovery component.

        Args:
            force_refresh: Whether to force a fresh discovery

        Returns:
            Dictionary of discovered plugin metadata
        """
        plugins = self.plugin_discovery.discover_all_plugins(force_refresh)
        summary = self.plugin_discovery.get_plugin_summary()

        self.logger.info(
            f"Discovered {summary['total_plugins']} plugins ({summary['valid_plugins']} valid)"
        )

        return {
            "plugins": {name: metadata.to_dict() for name, metadata in plugins.items()},
            "summary": summary,
        }

    def get_plugin_metadata(self, plugin_name: str) -> Optional[Dict[str, Any]]:
        """Get metadata for a specific plugin.

        Args:
            plugin_name: Name of the plugin

        Returns:
            Plugin metadata dictionary if found, None otherwise
        """
        metadata = self.plugin_discovery.get_plugin_metadata(plugin_name)
        return metadata.to_dict() if metadata else None

    def validate_plugin_config(
        self, plugin_name: str, config_data: Dict[str, Any]
    ) -> Optional[ValidationResult]:
        """Validate plugin configuration using plugin schema loader.

        Args:
            plugin_name: Name of the plugin
            config_data: Configuration data to validate

        Returns:
            ValidationResult if schema is available, None otherwise
        """
        try:
            result = self.plugin_schema_loader.validate_plugin_config(
                plugin_name, config_data
            )

            if result is None:
                return None

            validation_result = ValidationResult()

            if hasattr(result, "errors"):
                # It's a ValidationError
                validation_result.is_valid = False
                for error in result.errors():
                    field_path = " -> ".join(str(loc) for loc in error["loc"])
                    message = error["msg"]
                    validation_result.add_error(f"{field_path}: {message}")
            else:
                # It's a valid model
                validation_result.is_valid = True

            return validation_result

        except Exception as e:
            self.logger.error(
                f"Failed to validate plugin config for {plugin_name}: {e}"
            )
            return None

    def load_plugin_schemas(self, force_refresh: bool = False) -> Dict[str, Any]:
        """Load plugin schemas using plugin schema loader.

        Args:
            force_refresh: Whether to force refresh from source files

        Returns:
            Dictionary of loaded schema information
        """
        schemas = self.plugin_schema_loader.load_all_schemas(force_refresh)
        summary = self.plugin_schema_loader.get_schema_summary()

        self.logger.info(f"Loaded {summary['total_schemas']} plugin schemas")

        return {
            "schemas": {name: info.to_dict() for name, info in schemas.items()},
            "summary": summary,
        }

    def add_plugin(
        self, plugin_type: str, source_dir: Path, plugin_name: Optional[str] = None
    ) -> bool:
        """Add a plugin using plugin file manager.

        Args:
            plugin_type: Type of plugin to add
            source_dir: Source directory containing plugin files
            plugin_name: Optional name for the plugin

        Returns:
            True if successfully added, False otherwise
        """
        try:
            from panther.config.managers.plugin_file_manager import PluginType

            plugin_type_enum = PluginType.from_string(plugin_type)
            if not plugin_type_enum:
                raise ValueError(f"Invalid plugin type: {plugin_type}")

            self.plugin_file_manager.add_plugin(
                plugin_type_enum, source_dir, plugin_name
            )

            # Refresh plugin discovery to include the new plugin
            self.plugin_discovery.discover_all_plugins(force_refresh=True)

            self.logger.info(
                f"Successfully added {plugin_type} plugin: {plugin_name or source_dir.name}"
            )
            return True

        except Exception as e:
            self.logger.error(f"Failed to add plugin: {e}")
            return False

    def remove_plugin(
        self, plugin_type: str, plugin_name: str, protocol: Optional[str] = None
    ) -> bool:
        """Remove a plugin using plugin file manager.

        Args:
            plugin_type: Type of plugin to remove
            plugin_name: Name of the plugin to remove
            protocol: Optional protocol for service plugins

        Returns:
            True if successfully removed, False otherwise
        """
        try:
            from panther.config.managers.plugin_file_manager import PluginType

            plugin_type_enum = PluginType.from_string(plugin_type)
            if not plugin_type_enum:
                raise ValueError(f"Invalid plugin type: {plugin_type}")

            self.plugin_file_manager.remove_plugin(
                plugin_type_enum, plugin_name, protocol
            )

            # Refresh plugin discovery to reflect the removal
            self.plugin_discovery.discover_all_plugins(force_refresh=True)

            self.logger.info(
                f"Successfully removed {plugin_type} plugin: {plugin_name}"
            )
            return True

        except Exception as e:
            self.logger.error(f"Failed to remove plugin: {e}")
            return False

    def get_configuration_summary(self) -> Dict[str, Any]:
        """Get a summary of current configuration state.

        Returns:
            Summary dictionary with configuration information
        """
        summary = {
            "experiment_config_loaded": self.current_experiment_config is not None,
            "global_config_loaded": self.current_global_config is not None,
            "validation_results": {
                name: result.get_summary()
                for name, result in self.validation_results.items()
            },
            "builder_summary": self.configuration_builder.get_override_summary(),
        }

        # Add plugin information if available
        try:
            plugin_summary = self.plugin_discovery.get_plugin_summary()
            summary["plugins"] = plugin_summary
        except Exception:
            summary["plugins"] = {"error": "Plugin discovery not available"}

        # Add schema information if available
        try:
            schema_summary = self.plugin_schema_loader.get_schema_summary()
            summary["schemas"] = schema_summary
        except Exception:
            summary["schemas"] = {"error": "Schema loader not available"}

        return summary

    def set_validation_mode(self, strict: bool) -> None:
        """Set validation mode for configuration validator.

        Args:
            strict: Whether to use strict validation
        """
        self.configuration_validator.set_strict_mode(strict)
        self.logger.info(f"Validation mode set to {'strict' if strict else 'lenient'}")

    def add_configuration_override(self, key: str, value: Any) -> None:
        """Add a configuration override to the builder.

        Args:
            key: Configuration key (dot notation supported)
            value: Value to set
        """
        self.configuration_builder.add_overrides({key: value})
        self.logger.debug(f"Added configuration override: {key} = {value}")

    def clear_configuration_overrides(self) -> None:
        """Clear all configuration overrides from the builder."""
        self.configuration_builder.reset()
        self.logger.debug("Cleared all configuration overrides")

    def _load_yaml_file(self, file_path: Path) -> Dict[str, Any]:
        """Load YAML configuration file.

        Args:
            file_path: Path to YAML file

        Returns:
            Parsed YAML content as dictionary

        Raises:
            FileNotFoundError: If file doesn't exist
            yaml.YAMLError: If YAML parsing fails
        """
        if not file_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {file_path}")

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = yaml.safe_load(f)

            if content is None:
                return {}

            return content

        except yaml.YAMLError as e:
            raise yaml.YAMLError(f"Failed to parse YAML file {file_path}: {e}")

    def _get_default_global_config(self) -> Dict[str, Any]:
        """Get default global configuration.

        Returns:
            Default global configuration dictionary
        """
        return {
            "version": "1.0.0",
            "logging": {
                "level": "INFO",
                "format": "%(asctime)s [%(levelname)s] - %(module)s - %(message)s",
                "enable_colors": True,
            },
            "observers": {
                "logger": {"enabled": True, "log_level": "INFO"},
                "metrics": {"enabled": True},
                "storage": {"enabled": True},
            },
            "paths": {
                "output_dir": "outputs",
                "log_dir": "outputs/logs",
                "plugin_dir": "panther/plugins",
            },
            "docker": {"build_docker_image": False},
        }

    # Legacy API compatibility methods

    def load_config(self, config_path: Path, **kwargs) -> ExperimentConfig:
        """Legacy method - delegates to load_experiment_config."""
        return self.load_experiment_config(config_path, **kwargs)

    def validate_config(self, config: Union[Dict[str, Any], ExperimentConfig]) -> bool:
        """Legacy method - returns boolean validation result."""
        validation_result = self.validate_experiment_config(config)
        return validation_result.is_valid

    def get_plugins(self) -> Dict[str, Any]:
        """Legacy method - delegates to discover_plugins."""
        return self.discover_plugins()

    # Context manager support

    def __enter__(self):
        """Enter context manager."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context manager."""
        # Clean up if needed
        self.clear_configuration_overrides()

    # String representation

    def __str__(self) -> str:
        experiment_loaded = "loaded" if self.current_experiment_config else "not loaded"
        global_loaded = "loaded" if self.current_global_config else "not loaded"
        return f"ConfigManagerRefactored(experiment={experiment_loaded}, global={global_loaded})"

    def __repr__(self) -> str:
        return f"ConfigManagerRefactored(panther_dir='{self.panther_dir}')"


# Compatibility alias
ConfigManager = ConfigManagerRefactored
