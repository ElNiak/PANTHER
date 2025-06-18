"""Main configuration manager for the new PANTHER configuration system.

This module provides the primary interface for loading, validating, and processing
experiment configurations using the new modular architecture.
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from omegaconf import DictConfig, OmegaConf

from panther.config.builders import ExperimentConfigBuilder, ServiceConfigBuilder
from panther.config.loaders import YAMLConfigLoader, VersionConfigLoader, CompositeLoader
from panther.config.mergers import ConfigMerger, MergeStrategy, MergeConflictResolution
from panther.config.models import (
    ExperimentConfigModel, TestConfigModel, ServiceConfigModel,
    GlobalConfigModel, ImplementationType
)
from panther.config.validators import PydanticValidator, BusinessRulesValidator
from panther.core.exceptions.error_handler_mixin import ErrorHandlerMixin


class ConfigurationManagerV2(ErrorHandlerMixin):
    """Advanced configuration manager with modular architecture.
    
    This manager coordinates all configuration system components:
    - Dynamic loading from multiple sources
    - Comprehensive validation
    - Intelligent merging and auto-configuration
    - Version discovery and management
    """
    
    def __init__(
        self, 
        plugin_dir: Optional[Union[str, Path]] = None,
        enable_cache: bool = True,
        auto_fix_configs: bool = True
    ):
        super().__init__()
        self._config_logger = logging.getLogger(f"{__name__}.ConfigManagerV2")
        
        # Configuration options
        self.plugin_dir = Path(plugin_dir) if plugin_dir else self._get_default_plugin_dir()
        self.enable_cache = enable_cache
        self.auto_fix_configs = auto_fix_configs
        
        # Initialize components
        self._initialize_loaders()
        self._initialize_validators()
        self._initialize_builders()
        self._initialize_merger()
        
        # State tracking
        self._loaded_experiments: Dict[str, ExperimentConfigModel] = {}
        self._validation_cache: Dict[str, bool] = {}
        
        self._config_logger.info("Configuration Manager V2 initialized")
    
    def _get_default_plugin_dir(self) -> Path:
        """Get default plugin directory."""
        return Path(__file__).parent.parent / "plugins"
    
    def _initialize_loaders(self) -> None:
        """Initialize configuration loaders."""
        self.yaml_loader = YAMLConfigLoader(enable_cache=self.enable_cache)
        self.version_loader = VersionConfigLoader(
            plugin_dir=self.plugin_dir, 
            enable_cache=self.enable_cache
        )
        
        # Composite loader for multiple source types
        self.loader = CompositeLoader([
            self.yaml_loader,
            self.version_loader
        ], enable_cache=self.enable_cache)
        
        # Preload version configurations for performance
        if self.enable_cache:
            try:
                self.version_loader.preload_all_versions()
                self._config_logger.debug("Preloaded version configurations")
            except Exception as e:
                self._config_logger.warning(f"Failed to preload versions: {e}")
    
    def _initialize_validators(self) -> None:
        """Initialize configuration validators."""
        self.pydantic_validator = PydanticValidator(ExperimentConfigModel)
        self.business_validator = BusinessRulesValidator()
        
        # Validator chain for comprehensive validation
        self.validators = [
            self.pydantic_validator,
            self.business_validator
        ]
    
    def _initialize_builders(self) -> None:
        """Initialize configuration builders."""
        self.experiment_builder = ExperimentConfigBuilder(
            plugin_dir=self.plugin_dir
        )
        
        self.service_builder = ServiceConfigBuilder(
            plugin_dir=self.plugin_dir
        )
        
        # Set auto-configuration mode
        if hasattr(self.experiment_builder, 'enable_auto_configuration'):
            self.experiment_builder.enable_auto_configuration = self.auto_fix_configs
        if hasattr(self.service_builder, 'enable_auto_configuration'):
            self.service_builder.enable_auto_configuration = self.auto_fix_configs
    
    def _initialize_merger(self) -> None:
        """Initialize configuration merger."""
        self.merger = ConfigMerger()
    
    def load_experiment_config(
        self, 
        config_source: Union[str, Path, Dict[str, Any]],
        defaults: Optional[Union[str, Path, Dict[str, Any]]] = None,
        validate: bool = True,
        auto_fix: Optional[bool] = None
    ) -> ExperimentConfigModel:
        """Load and process experiment configuration.
        
        Args:
            config_source: Configuration source (file path or dict)
            defaults: Optional default configuration to merge with
            validate: Whether to perform validation
            auto_fix: Whether to auto-fix configurations (overrides instance setting)
            
        Returns:
            Fully processed experiment configuration
            
        Raises:
            ConfigurationLoadingError: If loading fails
            ConfigurationValidationError: If validation fails
        """
        if auto_fix is None:
            auto_fix = self.auto_fix_configs
        
        # Generate cache key
        cache_key = self._generate_cache_key(config_source, defaults)
        
        # Check cache first
        if self.enable_cache and cache_key in self._loaded_experiments:
            self._config_logger.debug(f"Using cached experiment config: {cache_key}")
            return self._loaded_experiments[cache_key]
        
        try:
            self._config_logger.info(f"Loading experiment configuration from {config_source}")
            
            # Load base configuration
            config_dict = self.loader.load(config_source)
            
            # Merge with defaults if provided
            if defaults:
                self._config_logger.debug("Merging with default configuration")
                defaults_dict = self.loader.load(defaults)
                config_dict = self.merger.merge_with_defaults(config_dict, defaults_dict)
            
            # Build experiment configuration with auto-fixes
            experiment_config = self._build_experiment_config(config_dict, auto_fix)
            
            # Validate if requested
            if validate:
                self._validate_experiment_config(experiment_config)
            
            # Cache the result
            if self.enable_cache:
                self._loaded_experiments[cache_key] = experiment_config
            
            self._config_logger.info(
                f"Successfully loaded experiment with {len(experiment_config.tests)} tests"
            )
            
            return experiment_config
            
        except Exception as e:
            self.handle_error(
                f"Failed to load experiment configuration from {config_source}",
                type(e),
                original_exception=e
            )
    
    def _build_experiment_config(
        self, 
        config_dict: Dict[str, Any], 
        auto_fix: bool
    ) -> ExperimentConfigModel:
        """Build experiment configuration using builders."""
        
        # Set auto-configuration mode
        self.experiment_builder.enable_auto_configuration = auto_fix
        self.service_builder.enable_auto_configuration = auto_fix
        
        # Build the experiment configuration
        experiment_config = self.experiment_builder.from_dict(config_dict).build()
        
        # Log auto-fixes if any were applied
        if auto_fix:
            builder_warnings = self.experiment_builder._context.warnings
            if builder_warnings:
                self._config_logger.info(f"Applied {len(builder_warnings)} auto-fixes:")
                for warning in builder_warnings:
                    self._config_logger.info(f"  - {warning}")
        
        return experiment_config
    
    def _validate_experiment_config(self, config: ExperimentConfigModel) -> None:
        """Validate experiment configuration using all validators."""
        
        self._config_logger.debug("Starting comprehensive validation")
        
        all_errors = []
        
        for validator in self.validators:
            try:
                result = validator.validate(config)
                if not result.is_valid:
                    all_errors.extend([f"{validator.__class__.__name__}: {error.message}" 
                                     for error in result.errors])
            except Exception as e:
                self._config_logger.warning(f"Validator {validator.__class__.__name__} failed: {e}")
                all_errors.append(f"Validation error: {e}")
        
        if all_errors:
            error_summary = "\n".join(f"  - {error}" for error in all_errors)
            raise ValueError(f"Configuration validation failed:\n{error_summary}")
        
        self._config_logger.debug("Configuration validation passed")
    
    def validate_service_configuration(
        self, 
        service_dict: Dict[str, Any]
    ) -> ServiceConfigModel:
        """Validate and build a single service configuration.
        
        Args:
            service_dict: Service configuration dictionary
            
        Returns:
            Validated service configuration
        """
        try:
            # Build service configuration
            service_config = self.service_builder.from_dict(service_dict).build()
            
            # Validate with business rules
            business_result = self.business_validator.validate(service_config)
            if not business_result.is_valid:
                errors = [error.message for error in business_result.errors]
                raise ValueError(f"Service validation failed: {'; '.join(errors)}")
            
            return service_config
            
        except Exception as e:
            self.handle_error(
                f"Failed to validate service configuration",
                type(e),
                original_exception=e
            )
    
    def discover_available_versions(self, protocol: Optional[str] = None) -> Dict[str, List[str]]:
        """Discover available protocol versions.
        
        Args:
            protocol: Optional protocol filter
            
        Returns:
            Dictionary mapping protocols to available versions
        """
        return self.version_loader.discover_versions(protocol_name=protocol)
    
    def get_version_configuration(
        self,
        implementation_name: str,
        implementation_type: ImplementationType,
        protocol_name: str,
        protocol_version: str
    ) -> Optional[Dict[str, Any]]:
        """Get version-specific configuration for an implementation.
        
        Args:
            implementation_name: Implementation name
            implementation_type: Implementation type
            protocol_name: Protocol name
            protocol_version: Protocol version
            
        Returns:
            Version configuration dictionary or None if not found
        """
        version_config = self.version_loader.load_version_config(
            implementation_name, implementation_type, protocol_name, protocol_version
        )
        
        return version_config.dict() if version_config else None
    
    def merge_configurations(
        self,
        *configs: Union[Dict[str, Any], ExperimentConfigModel],
        strategy: MergeStrategy = MergeStrategy.DEEP_MERGE,
        conflict_resolution: MergeConflictResolution = MergeConflictResolution.OVERRIDE
    ) -> DictConfig:
        """Merge multiple configurations with specified strategy.
        
        Args:
            *configs: Configurations to merge
            strategy: Merge strategy to use
            conflict_resolution: How to resolve conflicts
            
        Returns:
            Merged configuration as OmegaConf DictConfig
        """
        if not configs:
            return OmegaConf.create({})
        
        context = self.merger.create_merge_context(
            strategy=strategy,
            conflict_resolution=conflict_resolution
        )
        
        result = self.merger.merge(*configs, context=context)
        
        # Log merge report
        merge_report = self.merger.get_merge_report(context)
        if merge_report["total_conflicts"] > 0:
            self._config_logger.warning(f"Merge completed with {merge_report['total_conflicts']} conflicts")
        
        return result
    
    def create_experiment_from_template(
        self,
        template_name: str,
        parameters: Dict[str, Any],
        output_path: Optional[Union[str, Path]] = None
    ) -> ExperimentConfigModel:
        """Create experiment configuration from template.
        
        Args:
            template_name: Name of the template to use
            parameters: Parameters to substitute in template
            output_path: Optional path to save generated config
            
        Returns:
            Generated experiment configuration
        """
        # This would be implemented with template loading logic
        # For now, we'll create a basic template-based config
        
        template_config = {
            "tests": [
                {
                    "name": parameters.get("test_name", "generated_test"),
                    "description": parameters.get("test_description", "Generated from template"),
                    "network_environment": {"type": parameters.get("network_env", "docker_compose")},
                    "services": parameters.get("services", {})
                }
            ]
        }
        
        # Apply parameters to template
        processed_config = self._apply_template_parameters(template_config, parameters)
        
        # Build and validate
        experiment = self.load_experiment_config(processed_config)
        
        # Save if path provided
        if output_path:
            self._save_config_to_file(experiment, output_path)
        
        return experiment
    
    def _apply_template_parameters(
        self, 
        template: Dict[str, Any], 
        parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Apply parameters to configuration template."""
        # Simple parameter substitution - could be enhanced with Jinja2
        import json
        template_str = json.dumps(template)
        
        for key, value in parameters.items():
            template_str = template_str.replace(f"${{{key}}}", str(value))
        
        return json.loads(template_str)
    
    def _save_config_to_file(
        self, 
        config: ExperimentConfigModel, 
        file_path: Union[str, Path]
    ) -> None:
        """Save configuration to file."""
        config_dict = config.dict()
        omega_config = OmegaConf.create(config_dict)
        
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(path, 'w') as f:
            OmegaConf.save(omega_config, f)
        
        self._config_logger.info(f"Saved configuration to {path}")
    
    def _generate_cache_key(
        self, 
        config_source: Union[str, Path, Dict[str, Any]], 
        defaults: Optional[Union[str, Path, Dict[str, Any]]] = None
    ) -> str:
        """Generate cache key for configuration."""
        import hashlib
        
        # Create a hash of the sources
        source_str = str(config_source)
        if defaults:
            source_str += str(defaults)
        
        return hashlib.md5(source_str.encode()).hexdigest()
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get configuration manager statistics.
        
        Returns:
            Dictionary with usage statistics
        """
        return {
            "loaded_experiments": len(self._loaded_experiments),
            "cache_enabled": self.enable_cache,
            "auto_fix_enabled": self.auto_fix_configs,
            "discovered_protocols": len(self.version_loader.registry.get_supported_protocols()),
            "loader_cache_size": len(self.loader._cache) if hasattr(self.loader, '_cache') else 0,
            "version_registry_size": len(self.version_loader.registry._versions)
        }
    
    def clear_cache(self) -> None:
        """Clear all caches."""
        self._loaded_experiments.clear()
        self._validation_cache.clear()
        self.loader.clear_cache()
        self.version_loader.clear_cache()
        
        self._config_logger.info("All caches cleared")
    
    def __repr__(self) -> str:
        stats = self.get_statistics()
        return (
            f"ConfigurationManagerV2("
            f"experiments={stats['loaded_experiments']}, "
            f"protocols={stats['discovered_protocols']}, "
            f"cache={'enabled' if stats['cache_enabled'] else 'disabled'})"
        )


# Global configuration manager instance - lazy initialized
config_manager_v2 = None

def get_config_manager_v2() -> ConfigurationManagerV2:
    """Get the global configuration manager instance (lazy initialization)."""
    global config_manager_v2
    if config_manager_v2 is None:
        config_manager_v2 = ConfigurationManagerV2()
    return config_manager_v2


# Convenience functions for common operations
def load_experiment(
    config_path: Union[str, Path], 
    validate: bool = True,
    auto_fix: bool = True
) -> ExperimentConfigModel:
    """Convenience function to load experiment configuration.
    
    Args:
        config_path: Path to configuration file
        validate: Whether to validate the configuration
        auto_fix: Whether to auto-fix configuration issues
        
    Returns:
        Loaded experiment configuration
    """
    return get_config_manager_v2().load_experiment_config(
        config_path, 
        validate=validate, 
        auto_fix=auto_fix
    )


def validate_service(service_dict: Dict[str, Any]) -> ServiceConfigModel:
    """Convenience function to validate service configuration.
    
    Args:
        service_dict: Service configuration dictionary
        
    Returns:
        Validated service configuration
    """
    return get_config_manager_v2().validate_service_configuration(service_dict)


def discover_versions(protocol: Optional[str] = None) -> Dict[str, List[str]]:
    """Convenience function to discover available protocol versions.
    
    Args:
        protocol: Optional protocol filter
        
    Returns:
        Dictionary mapping protocols to available versions
    """
    return get_config_manager_v2().discover_available_versions(protocol)