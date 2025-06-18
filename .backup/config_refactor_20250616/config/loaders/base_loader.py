"""Base configuration loader interface and mixins."""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Type, Union
from pathlib import Path

from pydantic import ValidationError

from panther.config.models.base import ConfigModel
from panther.core.exceptions.error_handler_mixin import ErrorHandlerMixin


class ConfigurationLoadingError(Exception):
    """Raised when configuration loading fails."""
    
    def __init__(self, message: str, source: str = None, line: int = None):
        self.source = source
        self.line = line
        super().__init__(message)


class ConfigurationValidationError(Exception):
    """Raised when configuration validation fails."""
    
    def __init__(self, message: str, errors: List[str] = None):
        self.errors = errors or []
        super().__init__(message)


class CachingMixin:
    """Mixin providing caching functionality for loaders."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._cache: Dict[str, Any] = {}
        self._cache_enabled = True
    
    def enable_cache(self) -> None:
        """Enable caching for this loader."""
        self._cache_enabled = True
    
    def disable_cache(self) -> None:
        """Disable caching for this loader."""
        self._cache_enabled = False
        self.clear_cache()
    
    def clear_cache(self) -> None:
        """Clear the cache."""
        self._cache.clear()
    
    def get_from_cache(self, key: str) -> Optional[Any]:
        """Get item from cache."""
        if not self._cache_enabled:
            return None
        return self._cache.get(key)
    
    def put_in_cache(self, key: str, value: Any) -> None:
        """Put item in cache."""
        if self._cache_enabled:
            self._cache[key] = value
    
    def is_cached(self, key: str) -> bool:
        """Check if item is in cache."""
        return self._cache_enabled and key in self._cache


class AbstractConfigLoader(ABC, ErrorHandlerMixin, CachingMixin):
    """Abstract base class for configuration loaders."""
    
    def __init__(self, enable_cache: bool = True):
        super().__init__()
        self._loader_logger = logging.getLogger(self.__class__.__name__)
        self._cache_enabled = enable_cache
    
    @abstractmethod
    def load(self, source: Union[str, Path, Dict[str, Any]]) -> Dict[str, Any]:
        """Load configuration from the given source.
        
        Args:
            source: Configuration source (file path, URL, or dict)
            
        Returns:
            Dictionary containing the loaded configuration
            
        Raises:
            ConfigurationLoadingError: If loading fails
        """
        pass
    
    @abstractmethod
    def validate(self, config: Dict[str, Any]) -> bool:
        """Validate the loaded configuration.
        
        Args:
            config: Configuration dictionary to validate
            
        Returns:
            True if configuration is valid
            
        Raises:
            ConfigurationValidationError: If validation fails
        """
        pass
    
    @abstractmethod
    def get_schema(self) -> Type[ConfigModel]:
        """Get the schema/model type for this loader.
        
        Returns:
            The ConfigModel subclass for validation
        """
        pass
    
    def load_and_validate(self, source: Union[str, Path, Dict[str, Any]]) -> ConfigModel:
        """Load and validate configuration in one step.
        
        Args:
            source: Configuration source
            
        Returns:
            Validated ConfigModel instance
            
        Raises:
            ConfigurationLoadingError: If loading fails
            ConfigurationValidationError: If validation fails
        """
        # Check cache first
        cache_key = str(source) if not isinstance(source, dict) else str(hash(frozenset(source.items())))
        cached_result = self.get_from_cache(cache_key)
        if cached_result is not None:
            self._loader_logger.debug(f"Using cached configuration for {cache_key}")
            return cached_result
        
        try:
            # Load configuration
            config_dict = self.load(source)
            
            # Validate structure
            self.validate(config_dict)
            
            # Create and validate model
            schema_class = self.get_schema()
            config_model = schema_class.from_dict(config_dict)
            
            # Cache the result
            self.put_in_cache(cache_key, config_model)
            
            self._loader_logger.debug(f"Successfully loaded and validated configuration from {source}")
            return config_model
            
        except ValidationError as e:
            error_messages = []
            for error in e.errors():
                field_path = " -> ".join(str(x) for x in error["loc"])
                error_messages.append(f"{field_path}: {error['msg']}")
            
            raise ConfigurationValidationError(
                f"Configuration validation failed: {'; '.join(error_messages)}",
                errors=error_messages
            )
        except Exception as e:
            self.handle_error(
                f"Failed to load configuration from {source}",
                ConfigurationLoadingError,
                original_exception=e
            )
    
    def supports_source_type(self, source: Union[str, Path, Dict[str, Any]]) -> bool:
        """Check if this loader supports the given source type.
        
        Args:
            source: Source to check
            
        Returns:
            True if this loader can handle the source type
        """
        # Default implementation - override in subclasses
        return True


class FileBasedLoaderMixin:
    """Mixin for loaders that work with files."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.supported_extensions: List[str] = []
    
    def supports_file(self, file_path: Union[str, Path]) -> bool:
        """Check if this loader supports the file type.
        
        Args:
            file_path: Path to the file
            
        Returns:
            True if the file type is supported
        """
        path = Path(file_path)
        return path.suffix.lower() in self.supported_extensions
    
    def validate_file_exists(self, file_path: Union[str, Path]) -> Path:
        """Validate that the file exists and is readable.
        
        Args:
            file_path: Path to validate
            
        Returns:
            Validated Path object
            
        Raises:
            ConfigurationLoadingError: If file doesn't exist or isn't readable
        """
        path = Path(file_path)
        
        if not path.exists():
            raise ConfigurationLoadingError(
                f"Configuration file not found: {path}",
                source=str(path)
            )
        
        if not path.is_file():
            raise ConfigurationLoadingError(
                f"Configuration path is not a file: {path}",
                source=str(path)
            )
        
        if not path.stat().st_size > 0:
            raise ConfigurationLoadingError(
                f"Configuration file is empty: {path}",
                source=str(path)
            )
        
        return path


class NetworkLoaderMixin:
    """Mixin for loaders that work with network resources."""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.timeout = 30  # Default timeout in seconds
        self.retries = 3   # Default number of retries
    
    def supports_url(self, url: str) -> bool:
        """Check if this loader supports the URL scheme.
        
        Args:
            url: URL to check
            
        Returns:
            True if the URL scheme is supported
        """
        supported_schemes = ["http", "https", "ftp", "ftps"]
        return any(url.startswith(f"{scheme}://") for scheme in supported_schemes)


class CompositeLoader(AbstractConfigLoader):
    """Composite loader that delegates to multiple child loaders."""
    
    def __init__(self, loaders: List[AbstractConfigLoader], enable_cache: bool = True):
        super().__init__(enable_cache=enable_cache)
        self.loaders = loaders
    
    def load(self, source: Union[str, Path, Dict[str, Any]]) -> Dict[str, Any]:
        """Load configuration using the first supporting loader."""
        for loader in self.loaders:
            if loader.supports_source_type(source):
                return loader.load(source)
        
        raise ConfigurationLoadingError(
            f"No loader found for source type: {type(source)}"
        )
    
    def validate(self, config: Dict[str, Any]) -> bool:
        """Validate using the first loader that supports the config."""
        # Use the first loader for validation
        if self.loaders:
            return self.loaders[0].validate(config)
        return True
    
    def get_schema(self) -> Type[ConfigModel]:
        """Get schema from the first loader."""
        if self.loaders:
            return self.loaders[0].get_schema()
        raise ConfigurationLoadingError("No loaders available for schema")
    
    def supports_source_type(self, source: Union[str, Path, Dict[str, Any]]) -> bool:
        """Check if any child loader supports the source type."""
        return any(loader.supports_source_type(source) for loader in self.loaders)