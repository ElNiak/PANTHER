"""Environment variable handling mixin for ConfigurationManager."""

import os
from typing import Any, Dict

from omegaconf import DictConfig, OmegaConf

from panther.core.utils.logging_mixin import LoggerMixin


class EnvironmentHandlingMixin(LoggerMixin):
    """Handles environment variables and interpolation."""
    
    # Environment variable mappings
    ENV_MAPPINGS = {
        'PANTHER_LOG_LEVEL': 'logging.level',
        'PANTHER_BUILD_IMAGES': 'docker.build_docker_image',
        'PANTHER_OUTPUT_DIR': 'paths.output_dir',
        'PANTHER_LOG_COLORS': 'logging.enable_colors',
        'PANTHER_PLUGIN_DIR': 'paths.plugin_dir',
        'PANTHER_METRICS_ENABLED': 'metrics.enabled',
        'PANTHER_FAST_FAIL': 'fast_fail.enabled',
    }
    
    def _apply_environment_variables(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Apply environment variable overrides to configuration.
        
        Args:
            config: Configuration dictionary
            
        Returns:
            Configuration with environment variables applied
        """
        # Convert to OmegaConf for easier manipulation
        omega_config = OmegaConf.create(config)
        
        # Apply environment variable mappings
        for env_var, config_path in self.ENV_MAPPINGS.items():
            env_value = os.environ.get(env_var)
            if env_value is not None:
                self.logger.debug(f"Applying {env_var}={env_value} to {config_path}")
                
                # Handle type conversions
                if config_path.endswith('.enabled') or config_path.endswith('.build_docker_image'):
                    # Boolean conversion
                    env_value = env_value.lower() in ('true', '1', 'yes', 'on')
                elif env_var == 'PANTHER_LOG_LEVEL':
                    # Keep as string for log level
                    env_value = env_value.upper()
                
                # Update config
                try:
                    OmegaConf.update(omega_config, config_path, env_value, merge=False)
                except Exception as e:
                    self.logger.warning(f"Failed to apply {env_var}: {e}")
        
        # Support OmegaConf environment variable interpolation
        # This allows ${oc.env:VAR_NAME,default} syntax in configs
        omega_config = self._enable_env_interpolation(omega_config)
        
        # Resolve and return
        return OmegaConf.to_container(omega_config, resolve=True)
    
    def _resolve_interpolations(self, config: Any) -> Any:
        """Resolve all interpolations in configuration.
        
        Args:
            config: Configuration object (dict, DictConfig, or model)
            
        Returns:
            Configuration with interpolations resolved
        """
        if isinstance(config, dict):
            omega_config = OmegaConf.create(config)
        elif isinstance(config, DictConfig):
            omega_config = config
        else:
            # Assume it's a model with to_omega method
            omega_config = config.to_omega()
        
        # Enable environment variable interpolation
        omega_config = self._enable_env_interpolation(omega_config)
        
        # Resolve all interpolations
        resolved = OmegaConf.to_container(omega_config, resolve=True)
        
        # Return in appropriate format
        if isinstance(config, dict):
            return resolved
        elif isinstance(config, DictConfig):
            return OmegaConf.create(resolved)
        else:
            # Recreate model instance
            return config.__class__(**resolved)
    
    def _enable_env_interpolation(self, omega_config: DictConfig) -> DictConfig:
        """Enable environment variable interpolation in OmegaConf.
        
        Args:
            omega_config: OmegaConf DictConfig
            
        Returns:
            DictConfig with env interpolation enabled
        """
        # Register environment resolver if not already registered
        if not OmegaConf.has_resolver("oc.env"):
            OmegaConf.register_new_resolver(
                "oc.env",
                lambda var_name, default=None: os.environ.get(var_name, default)
            )
        
        return omega_config
    
    def _get_environment_mappings(self) -> Dict[str, str]:
        """Get current environment variable mappings.
        
        Returns:
            Dictionary of environment variable to config path mappings
        """
        return self.ENV_MAPPINGS.copy()
    
    def add_environment_mapping(self, env_var: str, config_path: str) -> None:
        """Add a new environment variable mapping.
        
        Args:
            env_var: Environment variable name
            config_path: Configuration path (dot notation)
        """
        self.ENV_MAPPINGS[env_var] = config_path
        self.logger.debug(f"Added environment mapping: {env_var} -> {config_path}")
    
    def remove_environment_mapping(self, env_var: str) -> None:
        """Remove an environment variable mapping.
        
        Args:
            env_var: Environment variable name to remove
        """
        if env_var in self.ENV_MAPPINGS:
            del self.ENV_MAPPINGS[env_var]
            self.logger.debug(f"Removed environment mapping: {env_var}")
    
    def get_environment_value(self, env_var: str, default: Any = None) -> Any:
        """Get environment variable value with type conversion.
        
        Args:
            env_var: Environment variable name
            default: Default value if not set
            
        Returns:
            Environment variable value or default
        """
        value = os.environ.get(env_var, default)
        
        if value is not None and isinstance(value, str):
            # Try to convert to appropriate type
            if value.lower() in ('true', 'false', '1', '0', 'yes', 'no', 'on', 'off'):
                return value.lower() in ('true', '1', 'yes', 'on')
            
            try:
                # Try integer
                return int(value)
            except ValueError:
                try:
                    # Try float
                    return float(value)
                except ValueError:
                    # Keep as string
                    pass
        
        return value