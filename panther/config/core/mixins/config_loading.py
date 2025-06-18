"""Configuration loading mixin for ConfigurationManager."""

from pathlib import Path
from typing import Any, Dict, Optional, Union

import yaml
from omegaconf import DictConfig, OmegaConf

from panther.core.utils.logging_mixin import LoggerMixin


class ConfigLoadingMixin(LoggerMixin):
    """Handles configuration loading from various sources."""
    
    def load_and_validate_experiment_config(self) -> 'ExperimentConfig':
        """Load and validate experiment configuration.
        
        Returns:
            Validated ExperimentConfig instance
            
        Raises:
            ValueError: If no experiment file specified
            ValidationError: If validation fails
        """
        if not hasattr(self, 'experiment_file') or not self.experiment_file:
            raise ValueError("No experiment configuration file specified")
        
        return self.load_experiment_config(
            self.experiment_file,
            validate=True,
            auto_fix=getattr(self, 'auto_fix_configs', True)
        )
    
    def load_and_validate_global_config(self) -> 'GlobalConfig':
        """Load and validate global configuration.
        
        Returns:
            Validated GlobalConfig instance
        """
        # Look for global config in standard locations
        panther_dir = getattr(self, 'panther_dir', Path.cwd())
        global_config_path = panther_dir / "config" / "global.yaml"
        
        if not global_config_path.exists():
            # Return default global config if file doesn't exist
            self.logger.debug("No global config file found, using defaults")
            from ..models.global_config import GlobalConfig
            return GlobalConfig()
        
        return self.load_global_config(global_config_path, validate=True)
    
    def load_experiment_config(
        self,
        source: Union[str, Path, Dict[str, Any]],
        defaults: Optional[Dict[str, Any]] = None,
        validate: bool = True,
        auto_fix: bool = True
    ) -> 'ExperimentConfig':
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
            with open(Path(source), 'r') as f:
                config_dict = yaml.safe_load(f)
        else:
            config_dict = source
        
        # Apply defaults
        if defaults:
            for key, value in defaults.items():
                if key not in config_dict:
                    config_dict[key] = value
        
        # Apply environment variables (simplified)
        # config_dict = self._apply_environment_variables(config_dict)
        
        # Create ExperimentConfig instance
        from ..models.experiment import ExperimentConfig
        experiment_config = ExperimentConfig(**config_dict)
        
        # Validate if requested (simplified - Pydantic handles validation)
        if validate:
            # Pydantic automatically validates during instantiation
            self.logger.debug("Configuration validation completed successfully")
        
        # Cache the configuration
        if hasattr(self, '_loaded_experiments'):
            cache_key = str(source) + str(hash(str(defaults or {})))
            self._loaded_experiments[cache_key] = experiment_config
        
        # Store as current experiment config
        self.current_experiment_config = experiment_config
        
        return experiment_config
    
    def load_global_config(
        self,
        path: Optional[Union[str, Path]] = None,
        overrides: Optional[Dict[str, Any]] = None,
        validate: bool = True
    ) -> 'GlobalConfig':
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
                with open(config_path, 'r') as f:
                    config_dict = yaml.safe_load(f) or {}
                self.logger.info(f"Loaded global config from {config_path}")
        
        # Apply overrides (simplified)
        if overrides:
            config_dict.update(overrides)
        
        # Create GlobalConfig instance
        from ..models.global_config import GlobalConfig
        global_config = GlobalConfig(**config_dict)
        
        # Validate if requested (simplified - Pydantic handles validation)
        if validate:
            self.logger.debug("Global configuration validation completed successfully")
        
        # Store as current global config
        self.current_global_config = global_config
        
        return global_config
    
    def reload_configuration(self) -> 'ExperimentConfig':
        """Reload configuration with hot-reload support.
        
        Returns:
            Reloaded ExperimentConfig instance
        """
        self.logger.info("Reloading configuration")
        
        # Clear caches
        if hasattr(self, 'clear_cache'):
            self.clear_cache()
        
        # Reload experiment config
        return self.load_and_validate_experiment_config()