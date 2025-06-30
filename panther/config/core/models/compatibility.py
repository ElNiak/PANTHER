"""
Compatibility module for transition to dynamic plugin config resolution.

This module provides compatibility shims to help during the migration from
hardcoded plugin configs to dynamic discovery.
"""

import warnings
from typing import Type, Any

# Import base classes that plugins should use
from .environment import ExecutionEnvironmentConfig as BaseExecutionEnvironmentConfig
from .environment import NetworkEnvironmentConfig as BaseNetworkEnvironmentConfig
from .plugin import ExecutionEnvironmentPluginConfig, NetworkEnvironmentPluginConfig


def create_compatibility_wrapper(plugin_config_class: Type) -> Type:
    """
    Create a compatibility wrapper for plugin config classes.
    
    This handles plugin configs that:
    1. Use dataclasses instead of Pydantic
    2. Import from old locations
    3. Don't inherit from the proper plugin base classes
    
    Args:
        plugin_config_class: The original plugin config class
        
    Returns:
        A wrapped class that's compatible with the new system
    """
    # Check if it's already a proper Pydantic model
    if hasattr(plugin_config_class, '__pydantic_model__'):
        return plugin_config_class
    
    # For dataclass-based configs, we need to handle them specially
    if hasattr(plugin_config_class, '__dataclass_fields__'):
        # Create a Pydantic version dynamically
        # This is a temporary solution during migration
        warnings.warn(
            f"Plugin config {plugin_config_class.__name__} is using dataclasses. "
            "Please migrate to Pydantic models inheriting from ExecutionEnvironmentPluginConfig "
            "or NetworkEnvironmentPluginConfig.",
            DeprecationWarning,
            stacklevel=2
        )
        
        # For now, return the dataclass as-is
        # The system will use the base class fallback
        return plugin_config_class
    
    return plugin_config_class


def get_proper_base_class(config_instance: Any) -> Type:
    """
    Determine the proper base class for a config instance.
    
    Args:
        config_instance: Config instance to check
        
    Returns:
        The appropriate base class
    """
    # Check class name or module to determine type
    class_name = type(config_instance).__name__
    module_name = type(config_instance).__module__
    
    if 'execution_environment' in module_name:
        return BaseExecutionEnvironmentConfig
    elif 'network_environment' in module_name:
        return BaseNetworkEnvironmentConfig
    else:
        # Try to infer from class name
        execution_keywords = ['strace', 'gperf', 'memcheck', 'helgrind', 'iterations']
        if any(keyword in class_name.lower() for keyword in execution_keywords):
            return BaseExecutionEnvironmentConfig
        else:
            return BaseNetworkEnvironmentConfig