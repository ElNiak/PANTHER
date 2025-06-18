#!/usr/bin/env python3
"""
Test script to verify dynamic config resolution works correctly.
"""

import sys
from pathlib import Path

# Add panther to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from panther.plugins.plugin_config_resolver import PluginConfigResolver
from panther.plugins.plugin_discovery import PluginDiscovery


def test_config_resolution():
    """Test dynamic config resolution for various environment types."""
    
    # Initialize components
    plugin_dirs = [
        str(Path(__file__).parent.parent.parent / "panther" / "plugins" / "environments")
    ]
    
    plugin_discovery = PluginDiscovery(plugin_dirs)
    config_resolver = PluginConfigResolver()
    
    # Test environment types
    test_environments = [
        # Execution environments
        {"type": "strace", "category": "execution"},
        {"type": "gperf_cpu", "category": "execution"},
        {"type": "gperf_heap", "category": "execution"},
        {"type": "memcheck", "category": "execution"},
        {"type": "helgrind", "category": "execution"},
        {"type": "iterations", "category": "execution"},
        # Network environments
        {"type": "docker_compose", "category": "network"},
        {"type": "localhost_single_container", "category": "network"},
        {"type": "shadow_ns", "category": "network"},
    ]
    
    print("Testing dynamic config resolution...\n")
    
    for env_info in test_environments:
        env_type = env_info["type"]
        category = env_info["category"]
        
        print(f"Testing {env_type} ({category} environment):")
        
        # Test config class resolution
        config_class = config_resolver.resolve_environment_config_class(
            env_type, plugin_discovery
        )
        
        if config_class:
            print(f"  ✓ Resolved config class: {config_class.__name__}")
            print(f"    Module: {config_class.__module__}")
            
            # Test instantiation
            try:
                config_dict = {"type": env_type}
                config_instance = config_resolver.create_environment_config_dynamic(
                    config_dict, plugin_discovery
                )
                print(f"  ✓ Created instance: {type(config_instance).__name__}")
                
                # Check base class
                from panther.config.core.models.environment import (
                    ExecutionEnvironmentConfig,
                    NetworkEnvironmentConfig
                )
                
                if category == "execution":
                    is_correct = isinstance(config_instance, ExecutionEnvironmentConfig)
                else:
                    is_correct = isinstance(config_instance, NetworkEnvironmentConfig)
                
                if is_correct:
                    print(f"  ✓ Correct base class inheritance")
                else:
                    print(f"  ✗ Incorrect base class inheritance")
                    
            except Exception as e:
                print(f"  ✗ Failed to instantiate: {e}")
        else:
            print(f"  ✗ Failed to resolve config class")
        
        print()
    
    # Test fallback behavior
    print("Testing fallback behavior for unknown plugin:")
    unknown_config = config_resolver.create_environment_config_dynamic(
        {"type": "unknown_plugin"}, plugin_discovery
    )
    print(f"  Fallback type: {type(unknown_config).__name__}")
    print()


def test_validation_mixin():
    """Test that validation mixin uses dynamic resolution."""
    from panther.config.core.mixins.validation_ops import ValidationOperationsMixin
    
    print("Testing ValidationOperationsMixin integration:\n")
    
    # Create a mock config manager with the mixin
    class MockConfigManager(ValidationOperationsMixin):
        def __init__(self):
            super().__init__()
            from panther.plugins.plugin_discovery import PluginDiscovery
            from panther.plugins.plugin_config_resolver import PluginConfigResolver
            
            plugin_dirs = [
                str(Path(__file__).parent.parent.parent / "panther" / "plugins" / "environments")
            ]
            self.plugin_discovery = PluginDiscovery(plugin_dirs)
            self.config_resolver = PluginConfigResolver()
    
    manager = MockConfigManager()
    
    # Test various environment configs
    test_configs = [
        {"type": "strace"},
        {"type": "docker_compose", "version": "3.9"},
        {"type": "shadow_ns"},
        {"type": "unknown_type"},  # Should use fallback
    ]
    
    for config in test_configs:
        try:
            result = manager.validate_environment_config(config)
            print(f"  Config type '{config['type']}': {type(result).__name__}")
        except Exception as e:
            print(f"  Config type '{config['type']}': Error - {e}")
    
    print()


if __name__ == "__main__":
    print("=" * 60)
    print("Dynamic Config Resolution Test")
    print("=" * 60)
    print()
    
    test_config_resolution()
    test_validation_mixin()
    
    print("Test completed!")