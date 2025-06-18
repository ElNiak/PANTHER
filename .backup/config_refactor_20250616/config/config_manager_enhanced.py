"""
Configuration Manager - now uses the new V2 modular architecture.

This file maintains backward compatibility while delegating to the new ConfigurationManagerV2.
The original implementation has been backed up to backup_originals/config_manager_original.py
"""

# Import the new V2 implementation
from panther.config.config_manager_v2 import (
    ConfigurationManagerV2,
    load_experiment,
    validate_service,
    discover_versions
)
from panther.config.config_manager_refactored import (
    ConfigManagerRefactored as ConfigManagerLegacy,
)

# Import specific classes for backward compatibility
from panther.config.managers.configuration_builder import ConfigurationBuilder
from panther.config.managers.configuration_validator import (
    ConfigurationValidator,
    ValidationResult,
)
from panther.config.managers.plugin_discovery import PluginDiscovery, PluginMetadata
from panther.config.managers.plugin_file_manager import PluginFileManager, PluginType
from panther.config.managers.plugin_schema_loader_simple import (
    PluginSchemaLoader,
    SchemaInfo,
)

# Export main classes for backward compatibility
__all__ = [
    "ConfigManager",
    "ConfigurationBuilder",
    "ConfigurationValidator",
    "ValidationResult",
    "PluginDiscovery",
    "PluginMetadata",
    "PluginFileManager",
    "PluginType",
    "PluginSchemaLoader",
    "SchemaInfo",
]

# Create a hybrid ConfigManager that maintains legacy interface
class ConfigManager:
    """Hybrid configuration manager that bridges legacy and V2 systems."""
    
    def __init__(self, experiment_file: str = None, plugin_dir: str = None, debug_override: bool = False, **kwargs):
        """Initialize both legacy and V2 managers for backward compatibility."""
        # Initialize the new V2 configuration manager
        self.config_manager_v2 = ConfigurationManagerV2(plugin_dir=plugin_dir)
        
        # Initialize legacy manager for fallback compatibility
        self.legacy_manager = ConfigManagerLegacy(experiment_file, plugin_dir)
        
        # Store parameters for backward compatibility
        self.experiment_file = experiment_file
        self.plugin_dir = plugin_dir
        self.debug_override = debug_override
        
        # Apply debug override if needed
        if debug_override:
            import logging
            logging.getLogger().setLevel(logging.DEBUG)
    
    def load_and_validate_experiment_config(self):
        """Load and validate experiment configuration using V2 system."""
        if not self.experiment_file:
            raise ValueError("No experiment file specified")
        
        try:
            # For now, let's use the legacy system to avoid compatibility issues
            # TODO: Once all service managers are updated to work with V2 format, switch to V2
            
            # Check if this is a complex configuration that might need legacy handling
            import yaml
            with open(self.experiment_file, 'r') as f:
                raw_config = yaml.safe_load(f)
            
            # Try V2 system first - we've fixed the compatibility issues
            try:
                self.config_manager_v2._config_logger.info(
                    "Attempting to use V2 config system"
                )
                experiment_config = self.config_manager_v2.load_experiment_config(
                    self.experiment_file,
                    validate=True,
                    auto_fix=True
                )
                
                # Convert to OmegaConf format for backward compatibility
                self.config_manager_v2._config_logger.info(
                    "Successfully loaded config with V2 system"
                )
                return experiment_config.to_omega()
                
            except Exception as v2_error:
                # Check for legacy-specific fields like implementation.test
                needs_legacy = self._check_needs_legacy_handling(raw_config)
                
                if needs_legacy:
                    self.config_manager_v2._config_logger.warning(
                        f"V2 config system failed ({v2_error}), falling back to legacy system"
                    )
                    return self.legacy_manager.load_and_validate_experiment_config()
                else:
                    # Re-raise the V2 error if legacy isn't needed
                    raise v2_error
            
        except Exception as e:
            # Fallback to legacy system if V2 fails
            self.config_manager_v2._config_logger.warning(
                f"V2 config loading failed: {e}. Falling back to legacy system."
            )
            return self.legacy_manager.load_and_validate_experiment_config()
    
    def _check_needs_legacy_handling(self, config_dict):
        """Check if configuration needs legacy handling due to compatibility issues."""
        # Check for legacy-specific fields in services
        tests = config_dict.get('tests', [])
        for test in tests:
            services = test.get('services', {})
            for service_name, service_config in services.items():
                implementation = service_config.get('implementation', {})
                # Check for legacy fields like 'test' in implementation
                if 'test' in implementation:
                    return True
                # Check for other legacy patterns as needed
        return False
    
    def load_and_validate_global_config(self):
        """Load and validate global configuration."""
        # For now, delegate to legacy system for global config
        # TODO: Implement global config loading in V2 system
        return self.legacy_manager.load_and_validate_global_config()
    
    def validate_experiment_config(self, config_dict):
        """Validate experiment configuration."""
        try:
            # Try V2 validation first
            from panther.config.models import ExperimentConfigModel
            experiment_config = ExperimentConfigModel.from_dict(config_dict)
            self.config_manager_v2._validate_experiment_config(experiment_config)
            return True
            
        except Exception as e:
            # Fallback to legacy validation
            self.config_manager_v2._config_logger.warning(
                f"V2 validation failed: {e}. Using legacy validation."
            )
            return self.legacy_manager.validate_experiment_config(config_dict)


# Create a backward compatible ConfigLoader class
class ConfigLoader(ConfigManager):
    """Backward compatible ConfigLoader that delegates to enhanced ConfigManager."""
    
    def list_plugin_parameters(self, plugin_name: str, plugin_type: str = None, protocol: str = None):
        """
        List all configurable parameters for a specified plugin.
        This method provides backward compatibility by delegating to plugin discovery.
        """
        try:
            # Use the plugin discovery system
            from panther.plugins.plugin_discovery import PluginDiscovery
            from pathlib import Path
            
            # Get plugin directory path
            base_plugin_dir = Path(__file__).parent.parent / "plugins"
            discovery = PluginDiscovery([str(base_plugin_dir)])
            
            # Get plugin metadata
            plugins_dict = discovery.list_available_plugins()
            
            # Find the plugin
            for plugin_type_key, plugin_names in plugins_dict.items():
                if plugin_name in plugin_names:
                    # Get plugin info
                    plugin_info = discovery.get_plugin_info(plugin_name)
                    if plugin_info:
                        # Try to get schema information
                        try:
                            from panther.config.managers.plugin_schema_loader_simple import PluginSchemaLoader
                            schema_loader = PluginSchemaLoader()
                            
                            # Load the schema for this plugin
                            schema_info = schema_loader.load_schema(plugin_type_key, plugin_name)
                            if schema_info:
                                return schema_info.get_parameters()
                            
                        except Exception as e:
                            print(f"Could not load schema for {plugin_name}: {e}")
                        
                        # Fallback: return basic info based on plugin_info
                        return {
                            'name': {'type': 'str', 'default': plugin_name, 'description': 'Plugin name'},
                            'type': {'type': 'str', 'default': plugin_type, 'description': 'Plugin type'},
                            'implementation_info': {'type': 'dict', 'default': plugin_info, 'description': 'Plugin implementation details'}
                        }
                            
            # Fallback: return basic info if plugin not found
            return {
                'name': {'type': 'str', 'default': plugin_name, 'description': 'Plugin name'},
                'type': {'type': 'str', 'default': plugin_type, 'description': 'Plugin type'}
            }
            
        except Exception as e:
            print(f"Error getting plugin parameters: {e}")
            return {}
    
    def _auto_detect_plugin_type(self, plugin_name: str, protocol: str = None):
        """Auto-detect plugin type for backward compatibility."""
        # Use plugin discovery to find the plugin type
        try:
            from panther.plugins.plugin_discovery import PluginDiscovery
            from pathlib import Path
            
            base_plugin_dir = Path(__file__).parent.parent / "plugins"
            discovery = PluginDiscovery([str(base_plugin_dir)])
            plugins_dict = discovery.list_available_plugins()
            
            for plugin_type_key, plugin_names in plugins_dict.items():
                if plugin_name in plugin_names:
                    return plugin_type_key
                        
            return None
            
        except Exception:
            return None
