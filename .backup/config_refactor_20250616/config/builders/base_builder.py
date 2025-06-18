"""Base configuration builder interface and utilities."""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Type, TypeVar, Union

from omegaconf import DictConfig

from panther.config.loaders import AbstractConfigLoader
from panther.config.mergers import ConfigMerger, MergeContext
from panther.config.models.base import ConfigModel
from panther.config.validators import AbstractValidator, ValidationResult
from panther.core.exceptions.error_handler_mixin import ErrorHandlerMixin

T = TypeVar('T', bound=ConfigModel)


class BuildContext:
    """Context for configuration building operations."""
    
    def __init__(self):
        self.sources: List[str] = []
        self.defaults_applied: bool = False
        self.validation_performed: bool = False
        self.merge_conflicts: List[Dict[str, Any]] = []
        self.warnings: List[str] = []
        self.metadata: Dict[str, Any] = {}
    
    def add_source(self, source: str) -> None:
        """Add a configuration source to the context."""
        self.sources.append(source)
    
    def add_warning(self, warning: str) -> None:
        """Add a warning to the context."""
        self.warnings.append(warning)
    
    def set_metadata(self, key: str, value: Any) -> None:
        """Set metadata for the build context."""
        self.metadata[key] = value
    
    def get_build_summary(self) -> Dict[str, Any]:
        """Get a summary of the build operation."""
        return {
            "sources": self.sources,
            "defaults_applied": self.defaults_applied,
            "validation_performed": self.validation_performed,
            "merge_conflicts": len(self.merge_conflicts),
            "warnings": len(self.warnings),
            "metadata": self.metadata
        }


class AbstractConfigBuilder(ABC, ErrorHandlerMixin):
    """Abstract base class for configuration builders."""
    
    def __init__(self, name: Optional[str] = None):
        super().__init__()
        self.name = name or self.__class__.__name__
        self._builder_logger = logging.getLogger(f"builder.{self.name}")
        
        # Builder components
        self._loaders: List[AbstractConfigLoader] = []
        self._validators: List[AbstractValidator] = []
        self._merger = ConfigMerger()
        
        # Builder state
        self._defaults: Optional[Dict[str, Any]] = None
        self._overrides: Dict[str, Any] = {}
        self._context = BuildContext()
    
    @abstractmethod
    def build(self) -> T:
        """Build and return the configuration model.
        
        Returns:
            Built and validated configuration model
        """
        pass
    
    @abstractmethod
    def get_target_model_class(self) -> Type[T]:
        """Get the target model class for this builder.
        
        Returns:
            ConfigModel subclass that this builder creates
        """
        pass
    
    def with_defaults(self, defaults: Union[Dict[str, Any], DictConfig, ConfigModel]) -> "AbstractConfigBuilder":
        """Set default configuration values.
        
        Args:
            defaults: Default configuration values
            
        Returns:
            Self for method chaining
        """
        if isinstance(defaults, ConfigModel):
            self._defaults = defaults.dict()
        elif isinstance(defaults, DictConfig):
            self._defaults = defaults
        else:
            self._defaults = defaults
        
        self._builder_logger.debug("Default configuration set")
        return self
    
    def with_overrides(self, overrides: Dict[str, Any]) -> "AbstractConfigBuilder":
        """Set configuration overrides.
        
        Args:
            overrides: Configuration overrides
            
        Returns:
            Self for method chaining
        """
        self._overrides.update(overrides)
        self._builder_logger.debug(f"Added {len(overrides)} configuration overrides")
        return self
    
    def with_loader(self, loader: AbstractConfigLoader) -> "AbstractConfigBuilder":
        """Add a configuration loader.
        
        Args:
            loader: Configuration loader to add
            
        Returns:
            Self for method chaining
        """
        self._loaders.append(loader)
        self._builder_logger.debug(f"Added loader: {loader.__class__.__name__}")
        return self
    
    def with_validator(self, validator: AbstractValidator) -> "AbstractConfigBuilder":
        """Add a configuration validator.
        
        Args:
            validator: Configuration validator to add
            
        Returns:
            Self for method chaining
        """
        self._validators.append(validator)
        self._builder_logger.debug(f"Added validator: {validator.__class__.__name__}")
        return self
    
    def validate(self, config: Union[Dict[str, Any], ConfigModel]) -> ValidationResult:
        """Validate configuration using registered validators.
        
        Args:
            config: Configuration to validate
            
        Returns:
            Validation result
        """
        from panther.config.validators import CompositeValidator
        
        if not self._validators:
            self._builder_logger.warning("No validators registered")
            return ValidationResult(is_valid=True)
        
        composite_validator = CompositeValidator(self._validators)
        result = composite_validator.validate(config)
        
        self._context.validation_performed = True
        self._builder_logger.debug(f"Validation completed: {result.get_error_summary()}")
        
        return result
    
    def _load_configuration(
        self, 
        source: Union[str, Dict[str, Any]], 
        loader: Optional[AbstractConfigLoader] = None
    ) -> Dict[str, Any]:
        """Load configuration from source.
        
        Args:
            source: Configuration source
            loader: Optional specific loader to use
            
        Returns:
            Loaded configuration dictionary
        """
        if isinstance(source, dict):
            self._context.add_source("dictionary")
            return source
        
        # Find appropriate loader
        if loader is None:
            for candidate_loader in self._loaders:
                if candidate_loader.supports_source_type(source):
                    loader = candidate_loader
                    break
        
        if loader is None:
            raise ValueError(f"No loader found for source: {source}")
        
        self._context.add_source(str(source))
        config = loader.load(source)
        
        self._builder_logger.debug(f"Loaded configuration from {source}")
        return config
    
    def _merge_configurations(
        self, 
        *configs: Union[Dict[str, Any], DictConfig],
        merge_context: Optional[MergeContext] = None
    ) -> DictConfig:
        """Merge multiple configurations.
        
        Args:
            *configs: Configurations to merge
            merge_context: Optional merge context
            
        Returns:
            Merged configuration
        """
        if not configs:
            return DictConfig({})
        
        merged = self._merger.merge(*configs, context=merge_context)
        
        if merge_context and merge_context.conflicts:
            self._context.merge_conflicts.extend(merge_context.conflicts)
            self._builder_logger.warning(f"Merge completed with {len(merge_context.conflicts)} conflicts")
        
        return merged
    
    def _apply_defaults(self, config: DictConfig) -> DictConfig:
        """Apply default configuration values.
        
        Args:
            config: Configuration to apply defaults to
            
        Returns:
            Configuration with defaults applied
        """
        if self._defaults is None:
            return config
        
        merged = self._merger.merge_with_defaults(config, self._defaults)
        self._context.defaults_applied = True
        
        self._builder_logger.debug("Default configuration applied")
        return merged
    
    def _apply_overrides(self, config: DictConfig) -> DictConfig:
        """Apply configuration overrides.
        
        Args:
            config: Configuration to apply overrides to
            
        Returns:
            Configuration with overrides applied
        """
        if not self._overrides:
            return config
        
        merged = self._merger.merge(config, self._overrides)
        
        self._builder_logger.debug(f"Applied {len(self._overrides)} configuration overrides")
        return merged
    
    def _build_model(self, config: DictConfig) -> T:
        """Build the target model from configuration.
        
        Args:
            config: Configuration dictionary
            
        Returns:
            Built model instance
        """
        model_class = self.get_target_model_class()
        model = model_class.from_omega(config)
        
        self._builder_logger.debug(f"Built {model_class.__name__} model")
        return model
    
    def get_build_context(self) -> BuildContext:
        """Get the current build context.
        
        Returns:
            Build context with operation details
        """
        return self._context
    
    def reset(self) -> "AbstractConfigBuilder":
        """Reset the builder state.
        
        Returns:
            Self for method chaining
        """
        self._defaults = None
        self._overrides.clear()
        self._context = BuildContext()
        
        self._builder_logger.debug("Builder state reset")
        return self


class FluentConfigBuilder(AbstractConfigBuilder):
    """Base class for fluent configuration builders."""
    
    def from_file(self, file_path: str) -> "FluentConfigBuilder":
        """Load configuration from file.
        
        Args:
            file_path: Path to configuration file
            
        Returns:
            Self for method chaining
        """
        self._primary_source = file_path
        return self
    
    def from_dict(self, config: Dict[str, Any]) -> "FluentConfigBuilder":
        """Load configuration from dictionary.
        
        Args:
            config: Configuration dictionary
            
        Returns:
            Self for method chaining
        """
        self._primary_source = config
        return self
    
    def merge_from_file(self, file_path: str) -> "FluentConfigBuilder":
        """Add additional configuration file to merge.
        
        Args:
            file_path: Path to additional configuration file
            
        Returns:
            Self for method chaining
        """
        if not hasattr(self, '_additional_sources'):
            self._additional_sources = []
        self._additional_sources.append(file_path)
        return self
    
    def merge_from_dict(self, config: Dict[str, Any]) -> "FluentConfigBuilder":
        """Add additional configuration dictionary to merge.
        
        Args:
            config: Additional configuration dictionary
            
        Returns:
            Self for method chaining
        """
        if not hasattr(self, '_additional_sources'):
            self._additional_sources = []
        self._additional_sources.append(config)
        return self
    
    def build(self) -> T:
        """Build configuration from all sources.
        
        Returns:
            Built and validated configuration model
        """
        if not hasattr(self, '_primary_source'):
            raise ValueError("No primary configuration source set")
        
        # Load primary configuration
        primary_config = self._load_configuration(self._primary_source)
        configs_to_merge = [primary_config]
        
        # Load additional configurations
        if hasattr(self, '_additional_sources'):
            for source in self._additional_sources:
                additional_config = self._load_configuration(source)
                configs_to_merge.append(additional_config)
        
        # Merge all configurations
        merged_config = self._merge_configurations(*configs_to_merge)
        
        # Apply defaults and overrides
        final_config = self._apply_defaults(merged_config)
        final_config = self._apply_overrides(final_config)
        
        # Build model
        model = self._build_model(final_config)
        
        # Validate
        validation_result = self.validate(model)
        if not validation_result.is_valid:
            error_summary = validation_result.format_errors()
            raise ValueError(f"Configuration validation failed:\n{error_summary}")
        
        return model


class ConfigBuilderFactory:
    """Factory for creating configuration builders."""
    
    _builders: Dict[str, Type[AbstractConfigBuilder]] = {}
    
    @classmethod
    def register_builder(
        cls, 
        name: str, 
        builder_class: Type[AbstractConfigBuilder]
    ) -> None:
        """Register a configuration builder.
        
        Args:
            name: Builder name
            builder_class: Builder class
        """
        cls._builders[name] = builder_class
    
    @classmethod
    def create_builder(cls, name: str, **kwargs) -> AbstractConfigBuilder:
        """Create a configuration builder by name.
        
        Args:
            name: Builder name
            **kwargs: Builder initialization arguments
            
        Returns:
            Configuration builder instance
        """
        if name not in cls._builders:
            raise ValueError(f"Unknown builder: {name}. Available: {list(cls._builders.keys())}")
        
        builder_class = cls._builders[name]
        return builder_class(**kwargs)
    
    @classmethod
    def get_available_builders(cls) -> List[str]:
        """Get list of available builder names.
        
        Returns:
            List of registered builder names
        """
        return list(cls._builders.keys())