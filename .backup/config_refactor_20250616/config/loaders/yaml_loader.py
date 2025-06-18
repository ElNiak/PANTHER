"""YAML configuration loader with OmegaConf integration."""

import re
from pathlib import Path
from typing import Any, Dict, List, Type, Union

import yaml
from omegaconf import DictConfig, OmegaConf

from panther.config.loaders.base_loader import (
    AbstractConfigLoader,
    ConfigurationLoadingError,
    FileBasedLoaderMixin,
)
from panther.config.models.base import ConfigModel
from panther.config.models.experiment import ExperimentConfigModel
from panther.config.models.global_config import CompleteConfigModel, GlobalConfigModel


class YAMLConfigLoader(AbstractConfigLoader, FileBasedLoaderMixin):
    """YAML configuration loader with OmegaConf support.
    
    Supports variable interpolation, includes, and other OmegaConf features.
    """
    
    def __init__(self, enable_cache: bool = True, enable_interpolation: bool = True):
        super().__init__(enable_cache=enable_cache)
        self.supported_extensions = [".yaml", ".yml"]
        self.enable_interpolation = enable_interpolation
        self._include_stack: List[Path] = []  # Track includes to prevent cycles
    
    def load(self, source: Union[str, Path, Dict[str, Any]]) -> Dict[str, Any]:
        """Load YAML configuration with OmegaConf processing.
        
        Args:
            source: Path to YAML file or dictionary
            
        Returns:
            Configuration dictionary with interpolation resolved
        """
        if isinstance(source, dict):
            return source
        
        file_path = self.validate_file_exists(source)
        
        # Check for circular includes
        if file_path in self._include_stack:
            raise ConfigurationLoadingError(
                f"Circular include detected: {' -> '.join(str(p) for p in self._include_stack + [file_path])}",
                source=str(file_path)
            )
        
        self._include_stack.append(file_path)
        
        try:
            # Load with OmegaConf for interpolation support
            omega_config = OmegaConf.load(file_path)
            
            # Process includes if present
            if "includes" in omega_config:
                omega_config = self._process_includes(omega_config, file_path.parent)
            
            # Convert to container with interpolation resolved
            config_dict = OmegaConf.to_container(omega_config, resolve=True)
            
            if not isinstance(config_dict, dict):
                raise ConfigurationLoadingError(
                    f"YAML file must contain a dictionary at root level, got {type(config_dict)}",
                    source=str(file_path)
                )
            
            return config_dict
            
        except yaml.YAMLError as e:
            raise ConfigurationLoadingError(
                f"YAML parsing error in {file_path}: {e}",
                source=str(file_path),
                line=getattr(e, 'problem_mark', {}).get('line')
            )
        except Exception as e:
            raise ConfigurationLoadingError(
                f"Failed to load YAML configuration from {file_path}: {e}",
                source=str(file_path)
            )
        finally:
            self._include_stack.pop()
    
    def _process_includes(self, config: DictConfig, base_dir: Path) -> DictConfig:
        """Process include directives in configuration.
        
        Args:
            config: Configuration with potential includes
            base_dir: Base directory for resolving relative paths
            
        Returns:
            Configuration with includes merged
        """
        includes = config.get("includes", [])
        if not includes:
            return config
        
        # Create a new config without the includes directive
        merged_config = OmegaConf.create({})
        
        # Process each include
        for include_path in includes:
            include_file = base_dir / include_path
            if not include_file.exists():
                self.logger.warning(f"Include file not found: {include_file}")
                continue
            
            try:
                include_config = self.load(include_file)
                include_omega = OmegaConf.create(include_config)
                merged_config = OmegaConf.merge(merged_config, include_omega)
            except Exception as e:
                self.logger.warning(f"Failed to load include {include_file}: {e}")
        
        # Remove includes from original config and merge
        config_without_includes = OmegaConf.create({k: v for k, v in config.items() if k != "includes"})
        final_config = OmegaConf.merge(merged_config, config_without_includes)
        
        return final_config
    
    def validate(self, config: Dict[str, Any]) -> bool:
        """Basic structural validation of YAML configuration."""
        if not isinstance(config, dict):
            raise ConfigurationLoadingError("Configuration must be a dictionary")
        
        # Check for common structural issues
        if not config:
            raise ConfigurationLoadingError("Configuration cannot be empty")
        
        return True
    
    def get_schema(self) -> Type[ConfigModel]:
        """Get the default schema for YAML configurations.
        
        Override this in subclasses for specific schemas.
        """
        return CompleteConfigModel
    
    def supports_source_type(self, source: Union[str, Path, Dict[str, Any]]) -> bool:
        """Check if this loader supports the source type."""
        if isinstance(source, dict):
            return True
        
        if isinstance(source, (str, Path)):
            return self.supports_file(source)
        
        return False


class ExperimentYAMLLoader(YAMLConfigLoader):
    """Specialized YAML loader for experiment configurations."""
    
    def get_schema(self) -> Type[ConfigModel]:
        """Get the schema for experiment configurations."""
        return ExperimentConfigModel
    
    def validate(self, config: Dict[str, Any]) -> bool:
        """Validate experiment-specific structure."""
        super().validate(config)
        
        # Check for required experiment fields
        if "tests" not in config:
            raise ConfigurationLoadingError("Experiment configuration must contain 'tests'")
        
        if not isinstance(config["tests"], list):
            raise ConfigurationLoadingError("'tests' must be a list")
        
        if not config["tests"]:
            raise ConfigurationLoadingError("'tests' list cannot be empty")
        
        return True


class GlobalYAMLLoader(YAMLConfigLoader):
    """Specialized YAML loader for global configurations."""
    
    def get_schema(self) -> Type[ConfigModel]:
        """Get the schema for global configurations."""
        return GlobalConfigModel
    
    def validate(self, config: Dict[str, Any]) -> bool:
        """Validate global configuration structure."""
        super().validate(config)
        
        # Global configs are more flexible, just check basic structure
        return True


class CompleteYAMLLoader(YAMLConfigLoader):
    """Loader for complete configurations (global + experiment)."""
    
    def get_schema(self) -> Type[ConfigModel]:
        """Get the schema for complete configurations."""
        return CompleteConfigModel
    
    def load(self, source: Union[str, Path, Dict[str, Any]]) -> Dict[str, Any]:
        """Load complete configuration, separating global and experiment sections."""
        config = super().load(source)
        
        # If the config has both global and experiment sections, keep as is
        if "global_config" in config and "experiment_config" in config:
            return config
        
        # Otherwise, try to separate based on known keys
        global_keys = {
            "logging", "paths", "docker", "observers", "fast_fail", 
            "progress", "features", "debug_override", "dry_run"
        }
        experiment_keys = {
            "tests", "name", "description", "tags"
        }
        
        global_config = {}
        experiment_config = {}
        
        for key, value in config.items():
            if key in global_keys:
                global_config[key] = value
            elif key in experiment_keys:
                experiment_config[key] = value
            else:
                # Default unknown keys to experiment config
                experiment_config[key] = value
        
        # Return structured format
        return {
            "global_config": global_config,
            "experiment_config": experiment_config
        }
    
    def validate(self, config: Dict[str, Any]) -> bool:
        """Validate complete configuration structure."""
        super().validate(config)
        
        # Check that we have at least experiment configuration
        if "experiment_config" not in config and "tests" not in config:
            raise ConfigurationLoadingError(
                "Configuration must contain either 'experiment_config' or 'tests'"
            )
        
        return True


class TemplateYAMLLoader(YAMLConfigLoader):
    """YAML loader with template processing support."""
    
    def __init__(self, template_variables: Dict[str, Any] = None, **kwargs):
        super().__init__(**kwargs)
        self.template_variables = template_variables or {}
    
    def load(self, source: Union[str, Path, Dict[str, Any]]) -> Dict[str, Any]:
        """Load YAML with template variable substitution."""
        if isinstance(source, dict):
            return self._substitute_variables(source)
        
        file_path = self.validate_file_exists(source)
        
        try:
            # Read file content
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Substitute template variables
            content = self._substitute_template_variables(content)
            
            # Parse with OmegaConf
            omega_config = OmegaConf.create(yaml.safe_load(content))
            
            # Process includes
            if "includes" in omega_config:
                omega_config = self._process_includes(omega_config, file_path.parent)
            
            # Convert to container
            config_dict = OmegaConf.to_container(omega_config, resolve=True)
            
            return config_dict
            
        except Exception as e:
            raise ConfigurationLoadingError(
                f"Failed to load template YAML from {file_path}: {e}",
                source=str(file_path)
            )
    
    def _substitute_template_variables(self, content: str) -> str:
        """Substitute template variables in YAML content.
        
        Supports {{variable}} syntax.
        """
        def replace_var(match):
            var_name = match.group(1).strip()
            if var_name in self.template_variables:
                return str(self.template_variables[var_name])
            else:
                self.logger.warning(f"Template variable not found: {var_name}")
                return match.group(0)  # Return original if not found
        
        # Replace {{variable}} patterns
        pattern = r'\{\{\s*([^}]+)\s*\}\}'
        return re.sub(pattern, replace_var, content)
    
    def _substitute_variables(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Substitute variables in a config dictionary."""
        if isinstance(config, dict):
            return {k: self._substitute_variables(v) for k, v in config.items()}
        elif isinstance(config, list):
            return [self._substitute_variables(item) for item in config]
        elif isinstance(config, str):
            # Simple string substitution
            for var_name, var_value in self.template_variables.items():
                config = config.replace(f"{{{{{var_name}}}}}", str(var_value))
            return config
        else:
            return config
    
    def add_template_variable(self, name: str, value: Any) -> None:
        """Add a template variable."""
        self.template_variables[name] = value
    
    def add_template_variables(self, variables: Dict[str, Any]) -> None:
        """Add multiple template variables."""
        self.template_variables.update(variables)