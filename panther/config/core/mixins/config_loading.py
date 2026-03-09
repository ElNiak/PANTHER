"""Configuration loading mixin for ConfigurationManager."""

from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, Optional, Tuple, Union

import yaml
from omegaconf import DictConfig, OmegaConf

from panther.core.utils.logging_mixin import LoggerMixin

if TYPE_CHECKING:
    from ..models import ExperimentConfig, GlobalConfig


class ConfigLoadingMixin(LoggerMixin):
    """Handles configuration loading from various sources."""

    def load_and_validate_experiment_config(self) -> "ExperimentConfig":
        """Load and validate experiment configuration.

        Returns:
            Validated ExperimentConfig instance

        Raises:
            ValueError: If no experiment file specified
            ValidationError: If validation fails
        """
        if not hasattr(self, "experiment_file") or not self.experiment_file:
            raise ValueError("No experiment configuration file specified")

        return self.load_experiment_config(
            self.experiment_file,
            validate=True,
            auto_fix=getattr(self, "auto_fix_configs", True),
        )

    def load_and_validate_global_config(
        self,
        extract_global_only: bool = True,
        use_model_defaults: bool = True,
        validate: bool = True,
    ) -> "GlobalConfig":
        """Load and validate global configuration from mixed input files.

        Parses input configuration files that contain both global and experiment
        sections, extracts the global configuration parts, and applies Pydantic
        model defaults for missing values.

        Args:
            input_config_path: Path to input config file. If None, looks for standard locations
            extract_global_only: Whether to extract only global sections from mixed files
            use_model_defaults: Whether to use Pydantic model defaults for missing keys
            validate: Whether to validate the configuration

        Returns:
            Validated GlobalConfig instance with proper defaults

        Raises:
            FileNotFoundError: If input config file doesn't exist
            ValueError: If validation fails
        """
        from ..models.global_config import GlobalConfig

        # Determine input config path
        if self.experiment_file is None:
            # Return default global config using only Pydantic model defaults
            self.logger.debug(
                "No input config path specified, using Pydantic model defaults"
            )
            return GlobalConfig()

        input_path = Path(self.experiment_file)
        if not input_path.exists():
            raise FileNotFoundError(f"Input configuration file not found: {input_path}")

        if not input_path.is_file():
            error_msg = (
                f"Path exists but is not a file: {input_path}\n"
                f"Please specify a valid experiment configuration file, not a directory."
            )
            raise FileNotFoundError(error_msg)

        self.logger.info(f"Loading global configuration from {input_path}")

        # Load input configuration file
        try:
            with open(input_path, "r") as f:
                mixed_config = yaml.safe_load(f) or {}
        except yaml.YAMLError as e:
            error_msg = (
                f"Invalid YAML syntax in configuration file: {input_path}\n"
                f"YAML error: {e}\n"
                f"Please check the file syntax and format."
            )
            raise ValueError(error_msg) from e
        except Exception as e:
            error_msg = (
                f"Unexpected error reading configuration file: {input_path}\n"
                f"Error: {e}"
            )
            raise RuntimeError(error_msg) from e

        # Extract global configuration sections from mixed file using model field names
        from ..models.global_config import GlobalConfig

        global_sections = {}

        if extract_global_only:
            # Get field names from GlobalConfig model instead of hardcoding
            global_field_names = set(GlobalConfig.model_fields.keys())
            self.logger.debug(f"GlobalConfig model fields: {global_field_names}")

            # Extract only global sections that exist in the model
            for field_name in global_field_names:
                if field_name in mixed_config:
                    global_sections[field_name] = mixed_config[field_name]

            self.logger.debug(
                f"Extracted global sections: {list(global_sections.keys())}"
            )
        else:
            # Use entire config as global (for pure global config files)
            global_sections = mixed_config

        # Create GlobalConfig instance using builder to properly handle complex configurations
        from ..components.builders import GlobalConfigBuilder

        # Prepare config data for builder
        if use_model_defaults:
            # Start with empty dict, let builder apply Pydantic defaults
            config_data = {}
            self.logger.debug(
                "Using empty config data, builder will apply Pydantic model defaults"
            )
        else:
            # Use minimal config data
            config_data = {}

        # Merge extracted global sections into config data
        if global_sections:
            config_data.update(global_sections)
            self.logger.debug(f"Merged extracted global sections into config data")

        # Use builder to properly process global configuration
        builder = GlobalConfigBuilder()
        try:
            resolved_config = builder.build(config_data, resolve_env=True)
            self.logger.debug(
                "GlobalConfigBuilder processed configuration successfully"
            )
        except Exception as e:
            self.logger.error(f"GlobalConfigBuilder failed: {e}")
            if validate:
                raise ValueError(f"Global configuration building failed: {e}")
            # Fallback to basic GlobalConfig
            from ..models.global_config import GlobalConfig

            resolved_config = GlobalConfig()

        # Validate if requested
        if validate:
            # Pydantic validation happens automatically during builder.build()
            self.logger.debug(
                "Pydantic validation completed successfully during builder processing"
            )

        # Store as current global config
        self.current_global_config = resolved_config

        return resolved_config

    def load_experiment_config(
        self,
        source: Union[str, Path, Dict[str, Any]],
        defaults: Optional[Dict[str, Any]] = None,
        validate: bool = True,
        auto_fix: bool = True,
    ) -> "ExperimentConfig":
        """Load experiment configuration from various sources.

        Args:
            source: Configuration source (file path or dict)
            defaults: Default values to apply
            validate: Whether to validate the configuration
            auto_fix: Whether to auto-fix configuration issues

        Returns:
            Loaded ExperimentConfig instance

        Raises:
            FileNotFoundError: If source file doesn't exist
            ValidationError: If validation fails and auto_fix is False
        """
        self.logger.info(f"Loading experiment configuration from {source}")

        # Load raw configuration
        if isinstance(source, (str, Path)):
            source_path = Path(source)
            try:
                if not source_path.exists():
                    error_msg = (
                        f"Experiment configuration file not found: {source_path}\n"
                        f"Current working directory: {Path.cwd()}\n"
                        f"Resolved path: {source_path.resolve()}"
                    )
                    raise FileNotFoundError(error_msg)

                if not source_path.is_file():
                    error_msg = (
                        f"Path exists but is not a file: {source_path}\n"
                        f"Please specify a valid experiment configuration file."
                    )
                    raise FileNotFoundError(error_msg)

                with open(source_path, "r") as f:
                    config_dict = yaml.safe_load(f)

                if config_dict is None:
                    error_msg = (
                        f"Configuration file is empty or contains only comments: {source_path}\n"
                        f"Please ensure the file contains valid YAML configuration."
                    )
                    raise ValueError(error_msg)

            except PermissionError as e:
                error_msg = (
                    f"Permission denied accessing configuration file: {source_path}\n"
                    f"Please check file permissions."
                )
                raise PermissionError(error_msg) from e
            except yaml.YAMLError as e:
                error_msg = (
                    f"Invalid YAML syntax in configuration file: {source_path}\n"
                    f"YAML error: {e}\n"
                    f"Please check the file syntax and format."
                )
                raise ValueError(error_msg) from e
            except Exception as e:
                error_msg = (
                    f"Unexpected error reading configuration file: {source_path}\n"
                    f"Error: {e}"
                )
                raise RuntimeError(error_msg) from e
        else:
            config_dict = source

        # Apply defaults
        if defaults:
            for key, value in defaults.items():
                if key not in config_dict:
                    config_dict[key] = value

        # Apply environment variables (simplified)
        # config_dict = self._apply_environment_variables(config_dict)

        # Early port conflict validation before instantiation
        early_validation_result = self._validate_ports_early(config_dict)
        if not early_validation_result.is_valid and validate:
            # Log early validation errors
            for error in early_validation_result.errors:
                self.logger.error(f"Early port validation error: {error}")

            # Raise exception for early validation failures
            if early_validation_result.errors:
                error_msg = f"Port validation failed before config instantiation with {len(early_validation_result.errors)} error(s)"
                raise ValueError(error_msg)

        # Create ExperimentConfig instance using builder to extract plugin configs
        from ..components.builders import ExperimentBuilder
        from ..models.experiment import ExperimentConfig

        # Use builder to properly extract plugin configurations
        builder = ExperimentBuilder(plugin_dir=getattr(self, "panther_dir", None))
        experiment_config = builder.build(config_dict, auto_fix=auto_fix)

        # Validate if requested
        if validate:
            # Pydantic automatically validates during instantiation
            self.logger.debug("Pydantic validation completed successfully")

            # Run business rules validation if available
            if hasattr(self, "validate_experiment_config"):
                validation_result = self.validate_experiment_config(experiment_config)
                if not validation_result.is_valid:
                    # Log errors and warnings
                    for error in validation_result.errors:
                        self.logger.error(f"Validation error: {error}")
                    for warning in validation_result.warnings:
                        self.logger.warning(f"Validation warning: {warning}")

                    # Raise exception if there are errors (not just warnings)
                    if validation_result.errors:
                        error_msg = f"Configuration validation failed with {len(validation_result.errors)} error(s)"
                        raise ValueError(error_msg)
                else:
                    self.logger.debug(
                        "Business rules validation completed successfully"
                    )

        # Cache the configuration
        if hasattr(self, "_loaded_experiments"):
            cache_key = str(source) + str(hash(str(defaults or {})))
            self._loaded_experiments[cache_key] = experiment_config

        # Store as current experiment config
        self.current_experiment_config = experiment_config

        return experiment_config

    def load_global_config(
        self,
        path: Optional[Union[str, Path]] = None,
        overrides: Optional[Dict[str, Any]] = None,
        validate: bool = True,
    ) -> "GlobalConfig":
        """Load global configuration.

        Args:
            path: Path to global config file
            overrides: Configuration overrides to apply
            validate: Whether to validate the configuration

        Returns:
            Loaded GlobalConfig instance
        """
        config_dict = {}

        # Load from file if path provided
        if path:
            config_path = Path(path)
            if config_path.exists():
                with open(config_path, "r") as f:
                    config_dict = yaml.safe_load(f) or {}
                self.logger.info(f"Loaded global config from {config_path}")

        # Apply overrides
        if overrides:
            config_dict.update(overrides)

        # Create GlobalConfig instance using builder to properly handle complex configurations
        from ..components.builders import GlobalConfigBuilder
        from ..models.global_config import GlobalConfig

        # Use builder to properly process global configuration
        builder = GlobalConfigBuilder()
        global_config = builder.build(config_dict, resolve_env=True)

        # Validate if requested
        if validate:
            self.logger.debug("Global configuration validation completed successfully")

        # Store as current global config
        self.current_global_config = global_config

        return global_config

    def load_full_config(
        self,
        yaml_path: str,
        cli_overrides: Optional[Dict[str, Any]] = None,
    ) -> Tuple["GlobalConfig", "ExperimentConfig"]:
        """Single entry point: YAML -> split global/experiment -> validate -> return.

        Pipeline:
        1. Load YAML via OmegaConf
        2. Split into global sections (GlobalConfig fields) vs test sections
        3. Apply cli_overrides with CLI > YAML > defaults precedence
        4. Build GlobalConfig via GlobalConfigBuilder
        5. Build ExperimentConfig via ExperimentBuilder
        6. Return (GlobalConfig, ExperimentConfig)

        Args:
            yaml_path: Path to the experiment YAML file.
            cli_overrides: Optional dot-notation overrides (CLI > YAML > defaults).

        Returns:
            Tuple of (GlobalConfig, ExperimentConfig).

        Raises:
            FileNotFoundError: If yaml_path does not exist.
            ValueError: If validation fails.
        """
        from ..components.builders import ExperimentBuilder, GlobalConfigBuilder
        from ..models.global_config import GlobalConfig

        source_path = Path(yaml_path)
        if not source_path.exists():
            raise FileNotFoundError(f"Configuration file not found: {source_path}")

        # 1. Load raw YAML
        with open(source_path, "r") as f:
            raw_config = yaml.safe_load(f) or {}

        # 2. Split global vs experiment sections
        global_field_names = set(GlobalConfig.model_fields.keys())
        global_sections = {}
        experiment_sections = {}

        for key, value in raw_config.items():
            if key in global_field_names:
                global_sections[key] = value
            else:
                experiment_sections[key] = value

        # 3. Apply CLI overrides (dot-notation keys)
        if cli_overrides:
            omega_global = OmegaConf.create(global_sections)
            omega_experiment = OmegaConf.create(experiment_sections)

            for dot_key, value in cli_overrides.items():
                # Determine which section owns this key
                top_key = dot_key.split(".")[0]
                if top_key in global_field_names:
                    OmegaConf.update(omega_global, dot_key, value, merge=False)
                else:
                    OmegaConf.update(omega_experiment, dot_key, value, merge=False)

            global_sections = OmegaConf.to_container(omega_global, resolve=True)
            experiment_sections = OmegaConf.to_container(omega_experiment, resolve=True)

        # 4. Build GlobalConfig
        global_builder = GlobalConfigBuilder()
        global_config = global_builder.build(global_sections, resolve_env=True)

        # 5. Build ExperimentConfig
        experiment_builder = ExperimentBuilder(
            plugin_dir=getattr(self, "panther_dir", None)
        )
        experiment_config = experiment_builder.build(experiment_sections, auto_fix=True)

        # Store references
        self.current_global_config = global_config
        self.current_experiment_config = experiment_config

        return global_config, experiment_config

    def reload_configuration(self) -> "ExperimentConfig":
        """Reload configuration with hot-reload support.

        Returns:
            Reloaded ExperimentConfig instance
        """
        self.logger.info("Reloading configuration")

        # Clear caches
        if hasattr(self, "clear_cache"):
            self.clear_cache()

        # Reload experiment config
        return self.load_and_validate_experiment_config()

    def _validate_ports_early(self, config_dict: Dict[str, Any]) -> "ValidationResult":
        """Perform early port validation on raw config dict before instantiation.

        Args:
            config_dict: Raw configuration dictionary

        Returns:
            Validation result with port conflict errors
        """
        # Import here to avoid circular imports
        from ..components.validators import ValidationResult

        result = ValidationResult()

        # Extract port information from raw config
        # NOTE: Only validate within-test conflicts, not cross-test conflicts
        # Different tests run in isolation and can use the same ports

        tests = config_dict.get("tests", [])
        for test in tests:
            test_name = test.get("name", "unnamed_test")
            services = test.get("services", {})

            # Check within-test port conflicts only
            test_ports = {}
            test_used_ports = set()

            for service_name, service in services.items():
                ports = service.get("ports", [])
                for port_mapping in ports:
                    if isinstance(port_mapping, str) and ":" in port_mapping:
                        host_port = port_mapping.split(":")[0]
                        test_used_ports.add(int(host_port))

                        if host_port in test_ports:
                            suggested_port = self._suggest_alternative_port_early(
                                int(host_port), test_used_ports
                            )
                            result.add_error(
                                f"tests.{test_name}.services.{service_name}.ports",
                                f"Port {host_port} already used by service {test_ports[host_port]} in the same test. "
                                f"Suggested alternative: {suggested_port}",
                            )
                        else:
                            test_ports[host_port] = service_name

        return result

    def _suggest_alternative_port_early(
        self, conflicting_port: int, used_ports: set
    ) -> int:
        """Early validation version of port suggestion."""
        for offset in range(1, 100):
            candidate = conflicting_port + offset
            if candidate not in used_ports and candidate <= 65535:
                return candidate
        return conflicting_port + 1000

    def _suggest_port_for_service_type_early(
        self, service_type: str, used_ports: set
    ) -> int:
        """Early validation version of service-type-aware port suggestion."""
        service_port_ranges = {
            "ivy_server": (4000, 4999),
            "ivy_client": (7000, 7999),
            "picoquic_server": (6000, 6999),
            "picoquic_client": (5000, 5999),
            "quic": (4400, 4500),
            "http": (8000, 8999),
            "https": (8400, 8500),
        }

        port_range = (50000, 59999)  # Default
        for service_pattern, range_tuple in service_port_ranges.items():
            if service_pattern.lower() in service_type.lower():
                port_range = range_tuple
                break

        start_port, end_port = port_range
        for candidate in range(start_port, end_port + 1):
            if candidate not in used_ports:
                return candidate

        return start_port
