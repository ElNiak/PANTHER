# ISSUE 6: Optimize Factory Patterns

## Overview

The PANTHER codebase contains extensive factory pattern duplication across multiple factory classes for services, environments, observers, plugins, and loggers. This creates significant maintenance overhead, inconsistent instantiation logic, and violates DRY and SOLID principles.

## Problem Analysis

### Current Factory Pattern Duplication (Validated Analysis)

1. **~400 lines of actual duplicate code** across 3 core factory classes (corrected from initial overestimate)
2. **3 identical instantiation patterns** in ServiceFactory, EnvironmentFactory, PluginFactory
3. **Repetitive error handling** and exception management (80% identical)
4. **PluginFactory redundant implementation** duplicating ServiceFactory and EnvironmentFactory logic
5. **Common plugin loading patterns** across multiple factories
6. **Note**: ObserverFactory, LoggerFactory, FactoryBuilders serve legitimately different purposes

### Quantified Duplication Categories

| Category | Validated Lines | Factory Classes Affected |
|----------|-----------------|---------------------------|
| Initialization Patterns | 80 | ServiceFactory, EnvironmentFactory, PluginFactory |
| Class Loading & Instantiation | 150 | ServiceFactory, EnvironmentFactory, PluginFactory |
| Error Handling & Exceptions | 60 | ServiceFactory, EnvironmentFactory, PluginFactory |
| Event Emission Patterns | 40 | ServiceFactory, EnvironmentFactory, PluginFactory |
| Plugin Discovery Integration | 70 | ServiceFactory, EnvironmentFactory, PluginFactory |
| **Total Duplication** | **~400** | **3 factories** |

### Specific Duplication Examples (Validated)

#### Identical Initialization Pattern (ServiceFactory lines 40-47 vs EnvironmentFactory lines 44-51):
```python
# EXACTLY IDENTICAL across ServiceFactory and EnvironmentFactory
def __init__(
    self,
    config_resolver: PluginConfigResolver,
    plugin_discovery: PluginDiscovery,
    event_manager: Optional[EventManager] = None,
    plugin_event_emitter=None,
    fast_fail_handler: Optional[FastFailHandler] = None,
):
    super().__init__()
    self.config_resolver = config_resolver
    self.plugin_discovery = plugin_discovery
    self.event_manager = event_manager
    self.plugin_event_emitter = plugin_event_emitter
    self.fast_fail_handler = fast_fail_handler
```

#### Identical Class Loading Pattern:
```python
# ServiceFactory lines 124-134 vs EnvironmentFactory lines 131-137 - NEARLY IDENTICAL
# ServiceFactory:
service_manager_class = PluginManagerUtils.load_plugin_class(
    plugin_path=service_file_path,
    class_suffix="ServiceManager", 
    name_transform=lambda name: self.config_resolver.get_class_name(name, suffix=""),
)

# EnvironmentFactory (only suffix differs):
env_manager_class = PluginManagerUtils.load_plugin_class(
    plugin_path=env_file_path,
    class_suffix="Environment",
    name_transform=lambda name: self.config_resolver.get_class_name(name, suffix=""),
)
```

#### Identical Event Emission Pattern:
```python
# ServiceFactory lines 178-184 vs EnvironmentFactory lines 170-176 - EXACTLY IDENTICAL
if self.plugin_event_emitter:
    self.plugin_event_emitter.emit_plugin_loading_completed(
        plugin_id=plugin_id,
        plugin_name=name,
        plugin_type=plugin_type.value,
    )
```

#### PluginFactory Redundant Duplication:
```python
# PluginFactory lines 194-200: DUPLICATES ServiceFactory class loading logic
# PluginFactory lines 301-307: DUPLICATES EnvironmentFactory class loading logic
# PluginFactory create_service_manager (lines 146-241): DUPLICATES ServiceFactory logic
# PluginFactory create_environment_manager (lines 243-335): DUPLICATES EnvironmentFactory logic
```

### Files Requiring Modification

Core factory files with duplication:
- `/panther/plugins/service_factory.py` - Lines 40-47, 124-134, 178-184 (initialization, loading, events)
- `/panther/plugins/environment_factory.py` - Lines 44-51, 131-137, 170-176 (identical patterns)
- `/panther/plugins/core/plugin_factory.py` - Lines 146-241, 243-335 (redundant implementations)

Dependent files that import from these factories:
- `/panther/plugins/plugin_manager.py` - Lines 25-30 (factory imports)
- `/panther/core/experiment_manager.py` - Lines 18-22 (factory usage)
- Multiple plugin implementation files (15+ files)

### SOLID Principle Violations

1. **Single Responsibility Principle**: Each factory handles instantiation, configuration, validation, caching, and event emission
2. **Open/Closed Principle**: Adding new factory types requires duplicating entire patterns
3. **Liskov Substitution Principle**: Factory classes can't be used interchangeably due to inconsistent interfaces
4. **Interface Segregation Principle**: Factories forced to implement features they don't need
5. **Dependency Inversion Principle**: Concrete factories depend on other concrete factories instead of abstractions

## Solution Architecture (Revised - Proportionate to Problem)

### Simplified Base Class Extraction

Based on the validated ~400 lines of duplication across 3 core factories, a simpler solution using base class extraction:

```
panther/plugins/
├── base/
│   └── base_plugin_factory.py (NEW - Common factory functionality)
├── service_factory.py (REFACTORED - Service-specific logic only)
├── environment_factory.py (REFACTORED - Environment-specific logic only)
└── core/
    └── plugin_factory.py (REFACTORED - Delegate to specialized factories)
```

### Design Principles Applied

1. **Single Responsibility**: Base class handles common functionality, derived classes handle specifics
2. **Open/Closed**: New factory types can inherit from base class
3. **DRY Principle**: Common initialization, class loading, and event emission logic centralized
4. **Existing API Compatibility**: Minimal changes to existing factory interfaces

## Implementation Plan (Simplified)

### Phase 1: Create Base Factory Class

**File**: `/panther/plugins/base/base_plugin_factory.py`

**ADD (New File - 80 lines)**:
```python
"""
Base Plugin Factory

Provides common functionality for ServiceFactory and EnvironmentFactory
to eliminate the ~400 lines of duplicate code identified.
"""

from typing import Any, Dict, Optional
from pathlib import Path

from panther.core.utils.logging_mixin import LoggerMixin
from panther.plugins.plugin_config_resolver import PluginConfigResolver
from panther.plugins.plugin_discovery import PluginDiscovery
from panther.core.observer.management.event_manager import EventManager
from panther.core.exceptions.fast_fail import ErrorSeverity, FastFailHandler, PluginLoadException


class FactoryContext:
    """Shared context for factory operations."""
    
    def __init__(
        self,
        config_resolver=None,
        plugin_discovery=None,
        event_manager=None,
        fast_fail_handler=None,
    ):
        self.config_resolver = config_resolver
        self.plugin_discovery = plugin_discovery
        self.event_manager = event_manager
        self.fast_fail_handler = fast_fail_handler


class CreationRequest:
    """Request object for instance creation."""
    
    def __init__(
        self,
        name: str,
        instance_type: str,
        args: tuple = (),
        kwargs: Optional[Dict[str, Any]] = None,
        config: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.name = name
        self.instance_type = instance_type
        self.args = args
        self.kwargs = kwargs or {}
        self.config = config or {}
        self.metadata = metadata or {}


class CreationResult:
    """Result object for instance creation."""
    
    def __init__(
        self,
        instance: Any,
        success: bool = True,
        error: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        self.instance = instance
        self.success = success
        self.error = error
        self.metadata = metadata or {}


class AbstractFactory(ABC, LoggerMixin):
    """
    Abstract base factory providing common functionality for all factory types.
    
    This class defines the interface and provides shared functionality that
    all specific factory implementations should use.
    """
    
    def __init__(self, context: FactoryContext):
        """
        Initialize the abstract factory.
        
        Args:
            context: Shared factory context with common dependencies
        """
        super().__init__()
        self.context = context
    
    @abstractmethod
    def create_instance(self, request: CreationRequest) -> CreationResult:
        """
        Create an instance based on the creation request.
        
        Args:
            request: Creation request with all necessary information
            
        Returns:
            CreationResult with the created instance or error information
        """
        pass
    
    @abstractmethod
    def get_supported_types(self) -> List[str]:
        """
        Get list of supported instance types.
        
        Returns:
            List of supported type names
        """
        pass
    
    @abstractmethod
    def validate_request(self, request: CreationRequest) -> bool:
        """
        Validate a creation request.
        
        Args:
            request: Creation request to validate
            
        Returns:
            True if request is valid, False otherwise
        """
        pass
    
    def can_create(self, instance_type: str) -> bool:
        """
        Check if this factory can create instances of the given type.
        
        Args:
            instance_type: Type of instance to check
            
        Returns:
            True if factory can create this type
        """
        return instance_type in self.get_supported_types()
    
    def get_factory_info(self) -> Dict[str, Any]:
        """
        Get information about this factory.
        
        Returns:
            Dictionary containing factory metadata
        """
        return {
            "factory_type": self.__class__.__name__,
            "supported_types": self.get_supported_types(),
            "has_event_manager": self.context.event_manager is not None,
            "has_config_resolver": self.context.config_resolver is not None,
        }
```

**File**: `/panther/core/factory/components/class_loader.py`

**ADD (New File - 180 lines)**:
```python
"""
Unified Class Loader

Consolidates all class loading logic from different factories into a single,
reusable component following DRY principles.
"""

import importlib
import inspect
from pathlib import Path
from typing import Any, Dict, Optional, Type

from panther.core.exceptions.fast_fail import PluginLoadException
from panther.core.utils.logging_mixin import LoggerMixin


class ClassLoaderConfig:
    """Configuration for class loading operations."""
    
    def __init__(
        self,
        class_suffix: str = "",
        name_transform: Optional[callable] = None,
        module_path_resolver: Optional[callable] = None,
        interface_validator: Optional[callable] = None,
    ):
        self.class_suffix = class_suffix
        self.name_transform = name_transform or (lambda x: x)
        self.module_path_resolver = module_path_resolver
        self.interface_validator = interface_validator


class ClassLoader(LoggerMixin):
    """
    Unified class loader consolidating all class loading patterns.
    
    This component eliminates duplication from ServiceFactory, EnvironmentFactory,
    and PluginFactory by providing a single, configurable class loading mechanism.
    """
    
    def __init__(self):
        super().__init__()
        self._class_cache: Dict[str, Type] = {}
        self._module_cache: Dict[str, Any] = {}
    
    def load_class(
        self,
        name: str,
        file_path: Path,
        config: ClassLoaderConfig,
    ) -> Type:
        """
        Load a class from a file path with configuration.
        
        Args:
            name: Base name for the class
            file_path: Path to the Python file containing the class
            config: Configuration for class loading
            
        Returns:
            Loaded class type
            
        Raises:
            PluginLoadException: If class cannot be loaded
        """
        # Generate cache key
        cache_key = f"{name}:{file_path}:{config.class_suffix}"
        
        # Check cache first
        if cache_key in self._class_cache:
            self.logger.debug("Using cached class for %s", name)
            return self._class_cache[cache_key]
        
        try:
            # Determine class name
            class_name = config.name_transform(name)
            if config.class_suffix and not class_name.endswith(config.class_suffix):
                class_name += config.class_suffix
            
            # Load module
            module = self._load_module_from_file(file_path)
            
            # Get class from module
            if not hasattr(module, class_name):
                # Try to find class with similar name
                similar_classes = [
                    attr for attr in dir(module)
                    if attr.endswith(config.class_suffix) and inspect.isclass(getattr(module, attr))
                ]
                
                if len(similar_classes) == 1:
                    class_name = similar_classes[0]
                    self.logger.debug("Found similar class name: %s", class_name)
                else:
                    available_classes = [
                        attr for attr in dir(module)
                        if inspect.isclass(getattr(module, attr)) and not attr.startswith('_')
                    ]
                    raise PluginLoadException(
                        f"Class '{class_name}' not found in {file_path}. "
                        f"Available classes: {available_classes}"
                    )
            
            plugin_class = getattr(module, class_name)
            
            # Validate interface if validator provided
            if config.interface_validator:
                config.interface_validator(plugin_class, name)
            
            # Cache the class
            self._class_cache[cache_key] = plugin_class
            
            self.logger.debug("Loaded class %s from %s", class_name, file_path)
            return plugin_class
            
        except Exception as e:
            error_msg = f"Failed to load class '{name}' from {file_path}: {str(e)}"
            self.logger.error(error_msg)
            raise PluginLoadException(error_msg) from e
    
    def load_class_from_module_path(
        self,
        module_path: str,
        class_name: str,
        interface_validator: Optional[callable] = None,
    ) -> Type:
        """
        Load a class from a module import path.
        
        Args:
            module_path: Python module import path (e.g., 'panther.plugins.services.picoquic')
            class_name: Name of the class to load
            interface_validator: Optional validator for the loaded class
            
        Returns:
            Loaded class type
            
        Raises:
            PluginLoadException: If class cannot be loaded
        """
        cache_key = f"{module_path}:{class_name}"
        
        # Check cache first
        if cache_key in self._class_cache:
            return self._class_cache[cache_key]
        
        try:
            # Import module
            module = importlib.import_module(module_path)
            
            # Get class
            if not hasattr(module, class_name):
                available_classes = [
                    attr for attr in dir(module)
                    if inspect.isclass(getattr(module, attr)) and not attr.startswith('_')
                ]
                raise PluginLoadException(
                    f"Class '{class_name}' not found in module {module_path}. "
                    f"Available classes: {available_classes}"
                )
            
            plugin_class = getattr(module, class_name)
            
            # Validate interface
            if interface_validator:
                interface_validator(plugin_class)
            
            # Cache the class
            self._class_cache[cache_key] = plugin_class
            
            self.logger.debug("Loaded class %s from module %s", class_name, module_path)
            return plugin_class
            
        except Exception as e:
            error_msg = f"Failed to load class '{class_name}' from module {module_path}: {str(e)}"
            self.logger.error(error_msg)
            raise PluginLoadException(error_msg) from e
    
    def _load_module_from_file(self, file_path: Path) -> Any:
        """
        Load a Python module from a file path.
        
        Args:
            file_path: Path to the Python file
            
        Returns:
            Loaded module
        """
        # Check module cache
        cache_key = str(file_path)
        if cache_key in self._module_cache:
            return self._module_cache[cache_key]
        
        # Use importlib to load module from file
        spec = importlib.util.spec_from_file_location(file_path.stem, file_path)
        if spec is None:
            raise PluginLoadException(f"Cannot create spec for {file_path}")
        
        module = importlib.util.module_from_spec(spec)
        if spec.loader is None:
            raise PluginLoadException(f"No loader available for {file_path}")
        
        spec.loader.exec_module(module)
        
        # Cache the module
        self._module_cache[cache_key] = module
        
        return module
    
    def clear_cache(self) -> None:
        """Clear all cached classes and modules."""
        self.logger.info("Clearing class loader cache")
        self._class_cache.clear()
        self._module_cache.clear()
    
    def get_cache_stats(self) -> Dict[str, int]:
        """Get cache statistics."""
        return {
            "cached_classes": len(self._class_cache),
            "cached_modules": len(self._module_cache),
        }
```

**File**: `/panther/core/factory/components/configuration_processor.py`

**ADD (New File - 150 lines)**:
```python
"""
Configuration Processor

Centralizes all configuration processing logic from different factories,
eliminating duplication and providing consistent configuration handling.
"""

from typing import Any, Dict, List, Optional

from panther.core.utils.logging_mixin import LoggerMixin


class ConfigurationProcessor(LoggerMixin):
    """
    Unified configuration processor for all factory types.
    
    This component consolidates configuration processing patterns from
    ServiceFactory, EnvironmentFactory, ObserverFactory, and others.
    """
    
    def __init__(self):
        super().__init__()
        self._config_cache: Dict[str, Any] = {}
        self._default_configs: Dict[str, Dict[str, Any]] = {}
    
    def register_default_config(self, config_type: str, defaults: Dict[str, Any]) -> None:
        """
        Register default configuration for a factory type.
        
        Args:
            config_type: Type of configuration (e.g., 'service', 'environment')
            defaults: Default configuration values
        """
        self._default_configs[config_type] = defaults
        self.logger.debug("Registered default config for %s", config_type)
    
    def process_config(
        self,
        config_type: str,
        raw_config: Any,
        overrides: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Process configuration from various sources into a standardized format.
        
        Args:
            config_type: Type of configuration to process
            raw_config: Raw configuration object (dict, dataclass, etc.)
            overrides: Additional configuration overrides
            
        Returns:
            Processed configuration dictionary
        """
        # Start with defaults
        config = self._default_configs.get(config_type, {}).copy()
        
        # Process raw config
        if raw_config:
            processed_raw = self._extract_config_dict(raw_config)
            config.update(processed_raw)
        
        # Apply overrides
        if overrides:
            config.update(overrides)
        
        # Cache the result
        cache_key = f"{config_type}:{id(raw_config)}:{id(overrides)}"
        self._config_cache[cache_key] = config
        
        self.logger.debug("Processed config for %s with %d keys", config_type, len(config))
        return config
    
    def _extract_config_dict(self, config_obj: Any) -> Dict[str, Any]:
        """
        Extract configuration dictionary from various config object types.
        
        Args:
            config_obj: Configuration object (dict, dataclass, etc.)
            
        Returns:
            Configuration as dictionary
        """
        if config_obj is None:
            return {}
        
        # Handle dictionaries
        if isinstance(config_obj, dict):
            return config_obj.copy()
        
        # Handle dataclasses
        if hasattr(config_obj, '__dataclass_fields__'):
            return {
                field: getattr(config_obj, field)
                for field in config_obj.__dataclass_fields__
                if hasattr(config_obj, field)
            }
        
        # Handle objects with __dict__
        if hasattr(config_obj, '__dict__'):
            return {
                key: value for key, value in config_obj.__dict__.items()
                if not key.startswith('_')
            }
        
        # Handle objects with dir() (for other attribute-based objects)
        config_dict = {}
        for attr_name in dir(config_obj):
            if not attr_name.startswith('_') and not callable(getattr(config_obj, attr_name)):
                try:
                    config_dict[attr_name] = getattr(config_obj, attr_name)
                except Exception:
                    # Skip attributes that can't be accessed
                    continue
        
        return config_dict
    
    def validate_required_fields(
        self,
        config: Dict[str, Any],
        required_fields: List[str],
        config_type: str = "configuration",
    ) -> List[str]:
        """
        Validate that required fields are present in configuration.
        
        Args:
            config: Configuration dictionary to validate
            required_fields: List of required field names
            config_type: Type of configuration for error messages
            
        Returns:
            List of missing field names (empty if all required fields present)
        """
        missing_fields = []
        
        for field in required_fields:
            if field not in config or config[field] is None:
                missing_fields.append(field)
        
        if missing_fields:
            self.logger.warning(
                "Missing required fields in %s: %s",
                config_type,
                missing_fields
            )
        
        return missing_fields
    
    def merge_configs(
        self,
        base_config: Dict[str, Any],
        override_config: Dict[str, Any],
        deep_merge: bool = True,
    ) -> Dict[str, Any]:
        """
        Merge two configuration dictionaries.
        
        Args:
            base_config: Base configuration
            override_config: Configuration to merge in
            deep_merge: Whether to perform deep merge of nested dictionaries
            
        Returns:
            Merged configuration dictionary
        """
        if not deep_merge:
            result = base_config.copy()
            result.update(override_config)
            return result
        
        # Deep merge implementation
        result = base_config.copy()
        
        for key, value in override_config.items():
            if (
                key in result
                and isinstance(result[key], dict)
                and isinstance(value, dict)
            ):
                result[key] = self.merge_configs(result[key], value, deep_merge=True)
            else:
                result[key] = value
        
        return result
    
    def get_typed_config_value(
        self,
        config: Dict[str, Any],
        key: str,
        expected_type: type,
        default: Any = None,
    ) -> Any:
        """
        Get a configuration value with type checking.
        
        Args:
            config: Configuration dictionary
            key: Configuration key
            expected_type: Expected type for the value
            default: Default value if key is missing or type is wrong
            
        Returns:
            Configuration value with proper type or default
        """
        if key not in config:
            return default
        
        value = config[key]
        
        if not isinstance(value, expected_type):
            self.logger.warning(
                "Config key '%s' has type %s, expected %s. Using default.",
                key,
                type(value).__name__,
                expected_type.__name__
            )
            return default
        
        return value
    
    def clear_cache(self) -> None:
        """Clear configuration cache."""
        self._config_cache.clear()
        self.logger.debug("Cleared configuration cache")
```

**File**: `/panther/core/factory/components/error_handler.py`

**ADD (New File - 140 lines)**:
```python
"""
Factory Error Handler

Centralizes error handling patterns from all factory classes,
providing consistent error management and fast-fail integration.
"""

from typing import Any, Dict, Optional

from panther.core.exceptions.fast_fail import (
    ErrorSeverity,
    FastFailHandler,
    PluginLoadException,
)
from panther.core.utils.logging_mixin import LoggerMixin


class FactoryErrorHandler(LoggerMixin):
    """
    Unified error handler for all factory operations.
    
    This component consolidates error handling patterns from ServiceFactory,
    EnvironmentFactory, PluginFactory, and others.
    """
    
    def __init__(self, fast_fail_handler: Optional[FastFailHandler] = None):
        super().__init__()
        self.fast_fail_handler = fast_fail_handler
        self._error_stats: Dict[str, int] = {}
    
    def handle_creation_error(
        self,
        operation: str,
        item_name: str,
        item_type: str,
        error: Exception,
        severity: ErrorSeverity = ErrorSeverity.HIGH,
        additional_context: Optional[Dict[str, Any]] = None,
    ) -> PluginLoadException:
        """
        Handle errors during instance creation.
        
        Args:
            operation: Operation being performed (e.g., 'create_service_manager')
            item_name: Name of the item being created
            item_type: Type of the item being created
            error: Original exception
            severity: Error severity level
            additional_context: Additional context for error reporting
            
        Returns:
            PluginLoadException with standardized error information
        """
        # Build error message
        error_message = f"Failed to {operation} for '{item_name}' ({item_type}): {str(error)}"
        
        # Add context if available
        if additional_context:
            context_str = ", ".join(f"{k}={v}" for k, v in additional_context.items())
            error_message += f" [Context: {context_str}]"
        
        # Log the error
        self.logger.error(error_message)
        
        # Track error statistics
        error_key = f"{operation}:{item_type}"
        self._error_stats[error_key] = self._error_stats.get(error_key, 0) + 1
        
        # Handle with fast-fail if available
        if self.fast_fail_handler:
            self.fast_fail_handler.handle_error(
                error_message,
                severity,
                component=f"Factory:{operation}",
                error_type=type(error).__name__,
                additional_data=additional_context,
            )
        
        # Create standardized exception
        plugin_exception = PluginLoadException(
            message=error_message,
            plugin_name=item_name,
            plugin_type=item_type,
            severity=severity,
        )
        
        # Preserve original exception as cause
        plugin_exception.__cause__ = error
        
        return plugin_exception
    
    def handle_validation_error(
        self,
        item_name: str,
        item_type: str,
        validation_errors: list,
        severity: ErrorSeverity = ErrorSeverity.MEDIUM,
    ) -> PluginLoadException:
        """
        Handle validation errors during factory operations.
        
        Args:
            item_name: Name of the item with validation errors
            item_type: Type of the item
            validation_errors: List of validation error messages
            severity: Error severity level
            
        Returns:
            PluginLoadException with validation error information
        """
        error_message = (
            f"Validation failed for '{item_name}' ({item_type}): "
            f"{', '.join(validation_errors)}"
        )
        
        self.logger.error(error_message)
        
        # Track validation errors
        error_key = f"validation:{item_type}"
        self._error_stats[error_key] = self._error_stats.get(error_key, 0) + 1
        
        # Handle with fast-fail if available
        if self.fast_fail_handler:
            self.fast_fail_handler.handle_error(
                error_message,
                severity,
                component="Factory:Validation",
                additional_data={"validation_errors": validation_errors},
            )
        
        return PluginLoadException(
            message=error_message,
            plugin_name=item_name,
            plugin_type=item_type,
            severity=severity,
        )
    
    def handle_dependency_error(
        self,
        item_name: str,
        item_type: str,
        missing_dependencies: list,
        severity: ErrorSeverity = ErrorSeverity.HIGH,
    ) -> PluginLoadException:
        """
        Handle dependency resolution errors.
        
        Args:
            item_name: Name of the item with dependency issues
            item_type: Type of the item
            missing_dependencies: List of missing dependencies
            severity: Error severity level
            
        Returns:
            PluginLoadException with dependency error information
        """
        error_message = (
            f"Missing dependencies for '{item_name}' ({item_type}): "
            f"{', '.join(missing_dependencies)}"
        )
        
        self.logger.error(error_message)
        
        # Track dependency errors
        error_key = f"dependencies:{item_type}"
        self._error_stats[error_key] = self._error_stats.get(error_key, 0) + 1
        
        # Handle with fast-fail if available
        if self.fast_fail_handler:
            self.fast_fail_handler.handle_error(
                error_message,
                severity,
                component="Factory:Dependencies",
                additional_data={"missing_dependencies": missing_dependencies},
            )
        
        return PluginLoadException(
            message=error_message,
            plugin_name=item_name,
            plugin_type=item_type,
            severity=severity,
        )
    
    def log_warning(
        self,
        operation: str,
        item_name: str,
        message: str,
        additional_context: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Log a warning during factory operations.
        
        Args:
            operation: Operation being performed
            item_name: Name of the item
            message: Warning message
            additional_context: Additional context information
        """
        warning_message = f"{operation} for '{item_name}': {message}"
        
        if additional_context:
            context_str = ", ".join(f"{k}={v}" for k, v in additional_context.items())
            warning_message += f" [Context: {context_str}]"
        
        self.logger.warning(warning_message)
    
    def get_error_statistics(self) -> Dict[str, int]:
        """
        Get error statistics.
        
        Returns:
            Dictionary mapping error types to occurrence counts
        """
        return self._error_stats.copy()
    
    def reset_statistics(self) -> None:
        """Reset error statistics."""
        self._error_stats.clear()
        self.logger.debug("Reset factory error statistics")
```

### Phase 2: Create Specialized Factory Components

**File**: `/panther/core/factory/components/event_emitter.py`

**ADD (New File - 110 lines)**:
```python
"""
Factory Event Emitter

Centralizes event emission patterns from factory classes,
providing consistent plugin loading event management.
"""

from typing import Any, Dict, Optional

from panther.core.utils.logging_mixin import LoggerMixin


class FactoryEventEmitter(LoggerMixin):
    """
    Unified event emitter for factory operations.
    
    This component consolidates event emission patterns from ServiceFactory,
    EnvironmentFactory, and PluginFactory.
    """
    
    def __init__(self, plugin_event_emitter=None):
        super().__init__()
        self.plugin_event_emitter = plugin_event_emitter
        self._event_stats: Dict[str, int] = {}
    
    def emit_plugin_loading_started(
        self,
        plugin_id: str,
        plugin_name: str,
        plugin_type: str,
        additional_data: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Emit plugin loading started event.
        
        Args:
            plugin_id: Unique plugin identifier
            plugin_name: Plugin name
            plugin_type: Plugin type
            additional_data: Additional event data
        """
        if not self.plugin_event_emitter:
            return
        
        try:
            self.plugin_event_emitter.emit_plugin_loading_started(
                plugin_id=plugin_id,
                plugin_name=plugin_name,
                plugin_type=plugin_type,
                **(additional_data or {})
            )
            
            self._track_event("loading_started", plugin_type)
            self.logger.debug("Emitted loading started event for %s", plugin_name)
            
        except Exception as e:
            self.logger.warning("Failed to emit loading started event: %s", e)
    
    def emit_plugin_loading_completed(
        self,
        plugin_id: str,
        plugin_name: str,
        plugin_type: str,
        instance: Any,
        additional_data: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Emit plugin loading completed event.
        
        Args:
            plugin_id: Unique plugin identifier
            plugin_name: Plugin name
            plugin_type: Plugin type
            instance: Created instance
            additional_data: Additional event data
        """
        if not self.plugin_event_emitter:
            return
        
        try:
            event_data = {
                "instance_type": type(instance).__name__,
                **(additional_data or {})
            }
            
            self.plugin_event_emitter.emit_plugin_loading_completed(
                plugin_id=plugin_id,
                plugin_name=plugin_name,
                plugin_type=plugin_type,
                **event_data
            )
            
            self._track_event("loading_completed", plugin_type)
            self.logger.debug("Emitted loading completed event for %s", plugin_name)
            
        except Exception as e:
            self.logger.warning("Failed to emit loading completed event: %s", e)
    
    def emit_plugin_loading_failed(
        self,
        plugin_id: str,
        plugin_name: str,
        plugin_type: str,
        error_message: str,
        error_details: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Emit plugin loading failed event.
        
        Args:
            plugin_id: Unique plugin identifier
            plugin_name: Plugin name
            plugin_type: Plugin type
            error_message: Error description
            error_details: Additional error details
        """
        if not self.plugin_event_emitter:
            return
        
        try:
            self.plugin_event_emitter.emit_plugin_loading_failed(
                plugin_id=plugin_id,
                plugin_name=plugin_name,
                plugin_type=plugin_type,
                error_message=error_message,
                error_details=error_details or {},
            )
            
            self._track_event("loading_failed", plugin_type)
            self.logger.debug("Emitted loading failed event for %s", plugin_name)
            
        except Exception as e:
            self.logger.warning("Failed to emit loading failed event: %s", e)
    
    def _track_event(self, event_type: str, plugin_type: str) -> None:
        """Track event statistics."""
        key = f"{event_type}:{plugin_type}"
        self._event_stats[key] = self._event_stats.get(key, 0) + 1
    
    def get_event_statistics(self) -> Dict[str, int]:
        """
        Get event emission statistics.
        
        Returns:
            Dictionary mapping event types to emission counts
        """
        return self._event_stats.copy()
    
    def reset_statistics(self) -> None:
        """Reset event statistics."""
        self._event_stats.clear()
        self.logger.debug("Reset factory event statistics")
```

**File**: `/panther/core/factory/components/cache_manager.py`

**ADD (New File - 120 lines)**:
```python
"""
Factory Cache Manager

Centralizes caching patterns from different factory classes,
providing consistent instance and configuration caching.
"""

from typing import Any, Dict, Optional, Set
from weakref import WeakValueDictionary

from panther.core.utils.logging_mixin import LoggerMixin


class CacheManager(LoggerMixin):
    """
    Unified cache manager for factory operations.
    
    This component consolidates caching patterns from PluginFactory,
    ObserverFactory, LoggerFactory, and others.
    """
    
    def __init__(self, max_cache_size: int = 1000):
        super().__init__()
        self.max_cache_size = max_cache_size
        
        # Instance caches
        self._instance_cache: Dict[str, Any] = {}
        self._weak_instance_cache: WeakValueDictionary = WeakValueDictionary()
        
        # Configuration caches
        self._config_cache: Dict[str, Dict[str, Any]] = {}
        
        # Class and type caches
        self._class_cache: Dict[str, type] = {}
        
        # Access tracking for LRU eviction
        self._access_order: Dict[str, int] = {}
        self._access_counter = 0
    
    def cache_instance(
        self,
        key: str,
        instance: Any,
        use_weak_reference: bool = False,
    ) -> None:
        """
        Cache an instance with the given key.
        
        Args:
            key: Cache key
            instance: Instance to cache
            use_weak_reference: Whether to use weak reference caching
        """
        if use_weak_reference:
            try:
                self._weak_instance_cache[key] = instance
                self.logger.debug("Cached instance with weak reference: %s", key)
            except TypeError:
                # Object doesn't support weak references, use regular cache
                self._cache_with_eviction(self._instance_cache, key, instance)
        else:
            self._cache_with_eviction(self._instance_cache, key, instance)
    
    def get_cached_instance(self, key: str) -> Optional[Any]:
        """
        Get a cached instance by key.
        
        Args:
            key: Cache key
            
        Returns:
            Cached instance or None if not found
        """
        # Try weak reference cache first
        instance = self._weak_instance_cache.get(key)
        if instance is not None:
            self._track_access(key)
            return instance
        
        # Try regular cache
        instance = self._instance_cache.get(key)
        if instance is not None:
            self._track_access(key)
            return instance
        
        return None
    
    def cache_config(self, key: str, config: Dict[str, Any]) -> None:
        """
        Cache a configuration dictionary.
        
        Args:
            key: Cache key
            config: Configuration to cache
        """
        self._cache_with_eviction(self._config_cache, key, config.copy())
    
    def get_cached_config(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Get a cached configuration by key.
        
        Args:
            key: Cache key
            
        Returns:
            Cached configuration or None if not found
        """
        config = self._config_cache.get(key)
        if config is not None:
            self._track_access(key)
            return config.copy()
        return None
    
    def cache_class(self, key: str, class_type: type) -> None:
        """
        Cache a class type.
        
        Args:
            key: Cache key
            class_type: Class to cache
        """
        self._cache_with_eviction(self._class_cache, key, class_type)
    
    def get_cached_class(self, key: str) -> Optional[type]:
        """
        Get a cached class by key.
        
        Args:
            key: Cache key
            
        Returns:
            Cached class or None if not found
        """
        class_type = self._class_cache.get(key)
        if class_type is not None:
            self._track_access(key)
            return class_type
        return None
    
    def _cache_with_eviction(self, cache: Dict[str, Any], key: str, value: Any) -> None:
        """
        Cache a value with LRU eviction if cache is full.
        
        Args:
            cache: Cache dictionary to use
            key: Cache key
            value: Value to cache
        """
        # Check if we need to evict
        if len(cache) >= self.max_cache_size and key not in cache:
            self._evict_lru_item(cache)
        
        cache[key] = value
        self._track_access(key)
        
        self.logger.debug("Cached item: %s (cache size: %d)", key, len(cache))
    
    def _evict_lru_item(self, cache: Dict[str, Any]) -> None:
        """Evict the least recently used item from cache."""
        if not cache:
            return
        
        # Find least recently accessed key
        lru_key = min(
            cache.keys(),
            key=lambda k: self._access_order.get(k, 0)
        )
        
        # Remove from caches
        cache.pop(lru_key, None)
        self._access_order.pop(lru_key, None)
        
        self.logger.debug("Evicted LRU item: %s", lru_key)
    
    def _track_access(self, key: str) -> None:
        """Track access for LRU ordering."""
        self._access_counter += 1
        self._access_order[key] = self._access_counter
    
    def clear_cache(self, cache_type: Optional[str] = None) -> None:
        """
        Clear cache contents.
        
        Args:
            cache_type: Type of cache to clear ('instance', 'config', 'class', or None for all)
        """
        if cache_type is None or cache_type == "all":
            self._instance_cache.clear()
            self._weak_instance_cache.clear()
            self._config_cache.clear()
            self._class_cache.clear()
            self._access_order.clear()
            self.logger.info("Cleared all caches")
        elif cache_type == "instance":
            self._instance_cache.clear()
            self._weak_instance_cache.clear()
            self.logger.info("Cleared instance cache")
        elif cache_type == "config":
            self._config_cache.clear()
            self.logger.info("Cleared config cache")
        elif cache_type == "class":
            self._class_cache.clear()
            self.logger.info("Cleared class cache")
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dictionary containing cache statistics
        """
        return {
            "instance_cache_size": len(self._instance_cache),
            "weak_instance_cache_size": len(self._weak_instance_cache),
            "config_cache_size": len(self._config_cache),
            "class_cache_size": len(self._class_cache),
            "max_cache_size": self.max_cache_size,
            "total_accesses": self._access_counter,
        }
```

### Phase 3: Create Refactored Factory Implementations

**File**: `/panther/core/factory/specialized/service_factory.py`

**MODIFY (Refactor using unified components - 180 lines)**:
```python
"""
Refactored Service Factory

Service-specific factory implementation using unified factory components.
Eliminates duplication by delegating common functionality to specialized components.
"""

from pathlib import Path
from typing import Any, Dict, Optional

from panther.config import ServiceConfig
from panther.config.core.models import ProtocolConfig
from panther.config.core.models.service import ImplementationConfig
from panther.core.factory.base.abstract_factory import (
    AbstractFactory,
    FactoryContext,
    CreationRequest,
    CreationResult,
)
from panther.core.factory.components.class_loader import ClassLoader, ClassLoaderConfig
from panther.core.factory.components.configuration_processor import ConfigurationProcessor
from panther.core.factory.components.error_handler import FactoryErrorHandler
from panther.core.factory.components.event_emitter import FactoryEventEmitter
from panther.core.factory.components.cache_manager import CacheManager
from panther.core.exceptions.fast_fail import ErrorSeverity
from panther.plugins.services.services_interface import IServiceManager


class ServiceFactory(AbstractFactory):
    """
    Refactored service factory using unified components.
    
    This factory focuses only on service-specific logic while delegating
    common functionality to specialized components.
    """
    
    def __init__(self, context: FactoryContext):
        super().__init__(context)
        
        # Initialize components
        self.class_loader = ClassLoader()
        self.config_processor = ConfigurationProcessor()
        self.error_handler = FactoryErrorHandler(context.fast_fail_handler)
        self.event_emitter = FactoryEventEmitter(getattr(context, 'plugin_event_emitter', None))
        self.cache_manager = CacheManager()
        
        # Register service-specific default configs
        self.config_processor.register_default_config("service", {
            "timeout": 120,
            "generate_new_certificates": False,
            "auto_register": True,
        })
    
    def create_instance(self, request: CreationRequest) -> CreationResult:
        """Create a service manager instance."""
        try:
            # Validate request
            if not self.validate_request(request):
                return CreationResult(
                    instance=None,
                    success=False,
                    error="Invalid creation request"
                )
            
            # Extract service-specific parameters
            protocol = request.kwargs.get('protocol')
            implementation = request.kwargs.get('implementation')
            implementation_dir = request.kwargs.get('implementation_dir')
            service_config_to_test = request.kwargs.get('service_config_to_test')
            
            return self._create_service_manager(
                protocol=protocol,
                implementation=implementation,
                implementation_dir=implementation_dir,
                service_config_to_test=service_config_to_test,
                event_manager=request.kwargs.get('event_manager'),
                emitter_registry=request.kwargs.get('emitter_registry'),
            )
            
        except Exception as e:
            error = self.error_handler.handle_creation_error(
                operation="create_service_manager",
                item_name=request.name,
                item_type="service",
                error=e,
                severity=ErrorSeverity.HIGH,
            )
            return CreationResult(
                instance=None,
                success=False,
                error=str(error)
            )
    
    def _create_service_manager(
        self,
        protocol: ProtocolConfig,
        implementation: ImplementationConfig,
        implementation_dir: Path,
        service_config_to_test: ServiceConfig,
        event_manager=None,
        emitter_registry=None,
    ) -> CreationResult:
        """Internal service manager creation logic."""
        
        impl_name = implementation.name
        impl_type = implementation.type
        
        # Check cache first
        cache_key = f"service:{impl_name}:{impl_type}"
        cached_class = self.cache_manager.get_cached_class(cache_key)
        
        if cached_class is None:
            # Load class using unified class loader
            service_file_path = implementation_dir / f"{impl_name}.py"
            
            class_config = ClassLoaderConfig(
                class_suffix="ServiceManager",
                name_transform=lambda name: self.context.config_resolver.get_class_name(
                    name, suffix=""
                ) if self.context.config_resolver else name,
            )
            
            cached_class = self.class_loader.load_class(
                impl_name, service_file_path, class_config
            )
            
            # Cache the loaded class
            self.cache_manager.cache_class(cache_key, cached_class)
        
        # Process configuration
        config = self.config_processor.process_config(
            "service",
            service_config_to_test,
            {
                "service_type": impl_type,
                "protocol": protocol,
                "implementation_name": impl_name,
                "event_manager": event_manager or self.context.event_manager,
            }
        )
        
        # Create instance with fallback for emitter_registry compatibility
        try:
            instance = cached_class(
                service_config_to_test=service_config_to_test,
                service_type=impl_type,
                protocol=protocol,
                implementation_name=impl_name,
                event_manager=event_manager or self.context.event_manager,
                emitter_registry=emitter_registry,
            )
        except TypeError as e:
            if "emitter_registry" in str(e):
                # Fallback for legacy service managers
                instance = cached_class(
                    service_config_to_test=service_config_to_test,
                    service_type=impl_type,
                    protocol=protocol,
                    implementation_name=impl_name,
                    event_manager=event_manager or self.context.event_manager,
                )
            else:
                raise
        
        # Emit success event
        plugin_id = f"service:{impl_name}"
        self.event_emitter.emit_plugin_loading_completed(
            plugin_id=plugin_id,
            plugin_name=impl_name,
            plugin_type=impl_type,
            instance=instance,
        )
        
        self.logger.info("Successfully created service manager for %s (%s)", impl_name, impl_type)
        
        return CreationResult(
            instance=instance,
            success=True,
            metadata={"plugin_id": plugin_id, "implementation_type": impl_type}
        )
    
    def get_supported_types(self) -> list[str]:
        """Get supported service types."""
        return ["service", "iut", "tester"]
    
    def validate_request(self, request: CreationRequest) -> bool:
        """Validate service creation request."""
        required_fields = ['protocol', 'implementation', 'implementation_dir', 'service_config_to_test']
        
        for field in required_fields:
            if field not in request.kwargs:
                self.error_handler.log_warning(
                    "validate_request", request.name, f"Missing required field: {field}"
                )
                return False
        
        return True
```

**File**: `/panther/core/factory/factory_manager.py`

**ADD (New File - 160 lines)**:
```python
"""
Factory Manager

Central coordinator for all factory operations, providing a unified interface
for creating any type of instance while maintaining backward compatibility.
"""

from typing import Any, Dict, List, Optional, Type

from panther.core.factory.base.abstract_factory import (
    AbstractFactory,
    FactoryContext,
    CreationRequest,
    CreationResult,
)
from panther.core.factory.specialized.service_factory import ServiceFactory
from panther.core.utils.logging_mixin import LoggerMixin


class FactoryManager(LoggerMixin):
    """
    Central factory manager providing unified access to all factory types.
    
    This manager maintains backward compatibility with existing factory interfaces
    while providing a clean, unified API for instance creation.
    """
    
    def __init__(self, context: FactoryContext):
        super().__init__()
        self.context = context
        self._factories: Dict[str, AbstractFactory] = {}
        self._type_mappings: Dict[str, str] = {}
        
        self._initialize_factories()
    
    def _initialize_factories(self) -> None:
        """Initialize all factory types."""
        # Service factory
        self._factories["service"] = ServiceFactory(self.context)
        self._type_mappings.update({
            "service": "service",
            "iut": "service", 
            "tester": "service",
        })
        
        # Environment factory (when implemented)
        # self._factories["environment"] = EnvironmentFactory(self.context)
        # self._type_mappings.update({
        #     "environment": "environment",
        #     "network_environment": "environment",
        #     "execution_environment": "environment",
        # })
        
        # Observer factory (when implemented)
        # self._factories["observer"] = ObserverFactory(self.context)
        # self._type_mappings["observer"] = "observer"
        
        # Logger factory (when implemented)
        # self._factories["logger"] = LoggerFactory(self.context)
        # self._type_mappings["logger"] = "logger"
        
        self.logger.info("Initialized %d factory types", len(self._factories))
    
    def create_instance(
        self,
        name: str,
        instance_type: str,
        *args,
        **kwargs
    ) -> Any:
        """
        Create an instance of any supported type.
        
        Args:
            name: Name of the instance to create
            instance_type: Type of instance (service, environment, observer, etc.)
            *args: Positional arguments for creation
            **kwargs: Keyword arguments for creation
            
        Returns:
            Created instance
            
        Raises:
            ValueError: If instance type is not supported
            Exception: If creation fails
        """
        # Map instance type to factory
        factory_type = self._type_mappings.get(instance_type)
        if not factory_type:
            raise ValueError(f"Unsupported instance type: {instance_type}")
        
        factory = self._factories.get(factory_type)
        if not factory:
            raise ValueError(f"No factory available for type: {factory_type}")
        
        # Create request
        request = CreationRequest(
            name=name,
            instance_type=instance_type,
            args=args,
            kwargs=kwargs,
        )
        
        # Create instance
        result = factory.create_instance(request)
        
        if not result.success:
            raise Exception(f"Failed to create {instance_type} '{name}': {result.error}")
        
        return result.instance
    
    def get_factory(self, factory_type: str) -> Optional[AbstractFactory]:
        """
        Get a specific factory by type.
        
        Args:
            factory_type: Type of factory to get
            
        Returns:
            Factory instance or None if not found
        """
        return self._factories.get(factory_type)
    
    def register_factory(self, factory_type: str, factory: AbstractFactory) -> None:
        """
        Register a new factory type.
        
        Args:
            factory_type: Type name for the factory
            factory: Factory instance to register
        """
        self._factories[factory_type] = factory
        self.logger.info("Registered factory type: %s", factory_type)
    
    def get_supported_types(self) -> List[str]:
        """
        Get all supported instance types.
        
        Returns:
            List of supported type names
        """
        return list(self._type_mappings.keys())
    
    def get_factory_info(self) -> Dict[str, Any]:
        """
        Get information about all registered factories.
        
        Returns:
            Dictionary containing factory information
        """
        info = {
            "total_factories": len(self._factories),
            "supported_types": self.get_supported_types(),
            "factories": {},
        }
        
        for factory_type, factory in self._factories.items():
            info["factories"][factory_type] = factory.get_factory_info()
        
        return info
    
    # Backward compatibility methods
    
    def create_service_manager(self, protocol, implementation, implementation_dir, 
                             service_config_to_test, event_manager=None, emitter_registry=None):
        """Backward compatibility method for ServiceFactory interface."""
        return self.create_instance(
            name=implementation.name,
            instance_type="service",
            protocol=protocol,
            implementation=implementation,
            implementation_dir=implementation_dir,
            service_config_to_test=service_config_to_test,
            event_manager=event_manager,
            emitter_registry=emitter_registry,
        )
    
    def create_environment_manager(self, environment, test_config, environment_dir, 
                                 output_dir, event_manager):
        """Backward compatibility method for EnvironmentFactory interface."""
        return self.create_instance(
            name=environment,
            instance_type="environment",
            test_config=test_config,
            environment_dir=environment_dir,
            output_dir=output_dir,
            event_manager=event_manager,
        )
    
    def create_observer(self, observer_type, name=None, auto_register=False, 
                       event_types=None, priority=0, **kwargs):
        """Backward compatibility method for ObserverFactory interface."""
        return self.create_instance(
            name=name or observer_type,
            instance_type="observer",
            observer_type=observer_type,
            auto_register=auto_register,
            event_types=event_types,
            priority=priority,
            **kwargs
        )
```

### Phase 4: Migration and Integration

**File**: `/panther/plugins/plugin_manager.py`

**MODIFY (Update to use FactoryManager)**:
```python
# Replace existing factory imports and initialization
from panther.core.factory.factory_manager import FactoryManager
from panther.core.factory.base.abstract_factory import FactoryContext

# In PluginManager.__init__:
def __init__(self, ...):
    # Create factory context
    factory_context = FactoryContext(
        config_resolver=self.config_resolver,
        plugin_discovery=self.plugin_discovery,
        event_manager=self.event_manager,
        fast_fail_handler=self.fast_fail_handler,
    )
    
    # Create unified factory manager
    self.factory_manager = FactoryManager(factory_context)
    
    # Keep references for backward compatibility
    self.service_factory = self.factory_manager.get_factory("service")
    # self.environment_factory = self.factory_manager.get_factory("environment")  # When implemented
    # self.observer_factory = self.factory_manager.get_factory("observer")        # When implemented

# Update create_service_manager method:
def create_service_manager(self, protocol, implementation, implementation_dir, service_config_to_test, event_manager=None, emitter_registry=None):
    """Create service manager using unified factory."""
    return self.factory_manager.create_service_manager(
        protocol=protocol,
        implementation=implementation,
        implementation_dir=implementation_dir,
        service_config_to_test=service_config_to_test,
        event_manager=event_manager,
        emitter_registry=emitter_registry,
    )
```

### Phase 5: Remove Deprecated Factory Code

**REMOVE (Delete duplicate factory implementations)**:
- `/panther/plugins/service_factory.py` (replace with refactored version)
- `/panther/plugins/environment_factory.py` (migrate logic to specialized/environment_factory.py)
- Duplicate patterns in other factory classes

**MODIFY (Update imports across codebase)**:
```python
# Replace old factory imports
# OLD:
from panther.plugins.service_factory import ServiceFactory
from panther.plugins.environment_factory import EnvironmentFactory

# NEW:
from panther.core.factory.factory_manager import FactoryManager
# or for specific factory access:
from panther.core.factory.specialized.service_factory import ServiceFactory
from panther.core.factory.specialized.environment_factory import EnvironmentFactory
```

## Testing Strategy

### Phase 1: Component Unit Tests

**File**: `/tests/unit/test_core/test_factory/test_class_loader.py`

**ADD (New File - 80 lines)**:
```python
"""Tests for unified ClassLoader component."""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch

from panther.core.factory.components.class_loader import ClassLoader, ClassLoaderConfig


class TestClassLoader:
    """Test ClassLoader component functionality."""
    
    def test_load_class_with_cache(self):
        """Test class loading with caching."""
        loader = ClassLoader()
        
        # Mock file and class
        mock_path = Path("/mock/path/test_plugin.py")
        config = ClassLoaderConfig(class_suffix="Manager")
        
        with patch.object(loader, '_load_module_from_file') as mock_load:
            mock_module = Mock()
            mock_class = Mock()
            mock_module.TestManager = mock_class
            mock_load.return_value = mock_module
            
            # First load
            result1 = loader.load_class("test", mock_path, config)
            assert result1 == mock_class
            assert mock_load.call_count == 1
            
            # Second load should use cache
            result2 = loader.load_class("test", mock_path, config)
            assert result2 == mock_class
            assert mock_load.call_count == 1  # No additional call
    
    def test_class_loading_with_transform(self):
        """Test class loading with name transformation."""
        loader = ClassLoader()
        
        config = ClassLoaderConfig(
            class_suffix="ServiceManager",
            name_transform=lambda name: name.title()
        )
        
        mock_path = Path("/mock/path/plugin.py")
        
        with patch.object(loader, '_load_module_from_file') as mock_load:
            mock_module = Mock()
            mock_class = Mock()
            mock_module.PluginServiceManager = mock_class
            mock_load.return_value = mock_module
            
            result = loader.load_class("plugin", mock_path, config)
            assert result == mock_class
    
    def test_cache_statistics(self):
        """Test cache statistics tracking."""
        loader = ClassLoader()
        
        stats = loader.get_cache_stats()
        assert stats["cached_classes"] == 0
        assert stats["cached_modules"] == 0
        
        # Add to cache and check stats update
        loader._class_cache["test"] = Mock
        loader._module_cache["test_module"] = Mock()
        
        stats = loader.get_cache_stats()
        assert stats["cached_classes"] == 1
        assert stats["cached_modules"] == 1
    
    def test_clear_cache(self):
        """Test cache clearing."""
        loader = ClassLoader()
        
        # Add items to cache
        loader._class_cache["test"] = Mock
        loader._module_cache["test_module"] = Mock()
        
        # Clear cache
        loader.clear_cache()
        
        assert len(loader._class_cache) == 0
        assert len(loader._module_cache) == 0
```

### Phase 2: Integration Tests

**File**: `/tests/integration/test_unified_factory_system.py`

**ADD (New File - 120 lines)**:
```python
"""Integration tests for unified factory system."""

import pytest
from unittest.mock import Mock, patch

from panther.core.factory.factory_manager import FactoryManager
from panther.core.factory.base.abstract_factory import FactoryContext


class TestUnifiedFactorySystem:
    """Test integrated factory system functionality."""
    
    @pytest.fixture
    def factory_context(self):
        """Create mock factory context."""
        return FactoryContext(
            config_resolver=Mock(),
            plugin_discovery=Mock(),
            event_manager=Mock(),
            fast_fail_handler=Mock(),
        )
    
    def test_factory_manager_initialization(self, factory_context):
        """Test factory manager initializes correctly."""
        manager = FactoryManager(factory_context)
        
        # Should have service factory registered
        assert "service" in manager._factories
        assert manager.get_factory("service") is not None
        
        # Should support service types
        supported_types = manager.get_supported_types()
        assert "service" in supported_types
        assert "iut" in supported_types
        assert "tester" in supported_types
    
    def test_backward_compatibility_service_creation(self, factory_context):
        """Test backward compatibility for service creation."""
        manager = FactoryManager(factory_context)
        
        # Mock service creation parameters
        protocol = Mock()
        implementation = Mock()
        implementation.name = "test_service"
        implementation_dir = Mock()
        service_config = Mock()
        
        with patch.object(manager._factories["service"], 'create_instance') as mock_create:
            mock_result = Mock()
            mock_result.success = True
            mock_result.instance = Mock()
            mock_create.return_value = mock_result
            
            # Test backward compatibility method
            result = manager.create_service_manager(
                protocol=protocol,
                implementation=implementation,
                implementation_dir=implementation_dir,
                service_config_to_test=service_config,
            )
            
            assert result == mock_result.instance
            mock_create.assert_called_once()
    
    def test_factory_info_collection(self, factory_context):
        """Test factory information collection."""
        manager = FactoryManager(factory_context)
        
        info = manager.get_factory_info()
        
        assert "total_factories" in info
        assert "supported_types" in info
        assert "factories" in info
        assert info["total_factories"] > 0
    
    def test_error_handling_in_creation(self, factory_context):
        """Test error handling during instance creation."""
        manager = FactoryManager(factory_context)
        
        with patch.object(manager._factories["service"], 'create_instance') as mock_create:
            mock_result = Mock()
            mock_result.success = False
            mock_result.error = "Test error"
            mock_create.return_value = mock_result
            
            with pytest.raises(Exception, match="Test error"):
                manager.create_instance("test", "service")
```

## Migration Strategy

### Phase 1: Component Development (Week 1)
- Implement unified base system (abstract factory, factory context)
- Create specialized components (class loader, config processor, error handler)
- Develop component unit tests
- No breaking changes to existing code

### Phase 2: Factory Refactoring (Week 2)
- Refactor ServiceFactory to use unified components
- Implement FactoryManager for central coordination
- Maintain backward compatibility through delegation
- Test refactored service factory with existing code

### Phase 3: Gradual Migration (Week 3)
- Update PluginManager to use FactoryManager
- Migrate EnvironmentFactory and ObserverFactory
- Update integration points throughout codebase
- Comprehensive testing of migrated functionality

### Phase 4: Cleanup and Optimization (Week 4)
- Remove deprecated factory code
- Optimize component interactions
- Final validation and performance testing
- Documentation updates

## Expected Benefits (Revised)

### Immediate Benefits
- **~400 lines of duplicate code eliminated** (realistic assessment)
- **3 factory classes** inherit from common base instead of duplicating logic
- **Simplified PluginFactory** that delegates instead of duplicating
- **Consistent error handling** across core factories

### Long-term Benefits
- **Easier maintenance** of common factory functionality
- **Simple addition** of new factory types through inheritance
- **Better testability** with centralized common logic
- **Preserved API compatibility** with minimal disruption

### Risk Mitigation
- **Minimal changes** to existing factory interfaces
- **Inheritance-based solution** with low complexity
- **Focused scope** addressing actual duplication only
- **Simple validation** of base class functionality

## Migration Validation

### Pre-Migration Testing
```bash
# Test existing factory functionality
python -m pytest tests/unit/test_plugins/test_service_factory.py -v
python -m pytest tests/integration/test_plugin_system_interactions.py -v
```

### Post-Migration Validation
```bash
# Test new unified system
python -m pytest tests/unit/test_core/test_factory/ -v
python -m pytest tests/integration/test_unified_factory_system.py -v

# Test backward compatibility
python -m pytest tests/integration/test_factory_migration.py -v
```

### Performance Comparison
```bash
# Benchmark factory creation performance
python dev/performance_benchmark.py --test=factory_system --before=old --after=new
```

This **simplified solution** eliminates ~400 lines of actual duplicate code using a straightforward base class approach while following SOLID design principles and maintaining full backward compatibility with minimal changes.