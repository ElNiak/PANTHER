import importlib
import logging
import dataclasses
import inspect
import os
from pathlib import Path
from typing import get_type_hints, Dict, Any, Optional, List, Tuple

from panther.plugins.plugin_loader import PluginLoader

# Plugin type constants
PLUGIN_TYPES = ["iut", "tester", "network_environment", "execution_environment"]
# Common protocols for service plugins
COMMON_PROTOCOLS = ["quic", "http", "minip"]

def find_plugin(plugin_name: str) -> Tuple[str, Optional[str]]:
    """
    Find a plugin's type and protocol by its name.
    
    :param plugin_name: The name of the plugin to find
    :return: Tuple of (plugin_type, protocol) if found, or raises ValueError if not found
    """
    logger = logging.getLogger("PluginFinder")
    
    # First check environment plugins (network_environment and execution_environment)
    for plugin_type in ["network_environment", "execution_environment"]:
        module_path = f"panther.plugins.environments.{plugin_type}.{plugin_name}.config_schema"
        try:
            importlib.import_module(module_path)
            logger.debug(f"Found plugin '{plugin_name}' of type '{plugin_type}'")
            return plugin_type, None
        except ImportError:
            pass
    
    # Then check service plugins (iut and tester)
    for plugin_type in ["iut", "tester"]:
        # First try without protocol
        module_path = f"panther.plugins.services.{plugin_type}.{plugin_name}.config_schema"
        try:
            importlib.import_module(module_path)
            logger.debug(f"Found plugin '{plugin_name}' of type '{plugin_type}'")
            return plugin_type, None
        except ImportError:
            # Then try with each common protocol
            for protocol in COMMON_PROTOCOLS:
                module_path = f"panther.plugins.services.{plugin_type}.{protocol}.{plugin_name}.config_schema"
                try:
                    importlib.import_module(module_path)
                    logger.debug(f"Found plugin '{plugin_name}' of type '{plugin_type}' under protocol '{protocol}'")
                    return plugin_type, protocol
                except ImportError:
                    pass
    
    raise ValueError(f"Could not find plugin '{plugin_name}' in any plugin type or protocol")

def list_plugin_parameters(plugin_name: str, plugin_type: Optional[str] = None, protocol: Optional[str] = None) -> Dict[str, Any]:
    """
    List all configurable parameters for a specified plugin.
    
    :param plugin_name: The plugin name (e.g., "shadow_ns", "picoquic", "quiche").
    :param plugin_type: Optional plugin type (e.g., "network_environment", "execution_environment", "iut", "tester").
                        If not provided, it will be auto-detected.
    :param protocol: Optional protocol name for IUT/tester plugins (e.g., "quic", "http").
                    If not provided, it will be auto-detected for protocol-specific plugins.
    :return: Dictionary of parameters with their types, defaults, and descriptions.
    """
    logger = logging.getLogger("PluginParameters")
    
    # Auto-detect plugin type and protocol if not specified
    if not plugin_type:
        try:
            detected_type, detected_protocol = find_plugin(plugin_name)
            plugin_type = detected_type
            if not protocol:
                protocol = detected_protocol
                
            logger.debug(f"Auto-detected plugin: type={plugin_type}, protocol={protocol}")
            print(f"Auto-detected plugin type: {plugin_type}")
            if protocol:
                print(f"Auto-detected protocol: {protocol}")
                
        except ValueError as e:
            print(f"Error: {e}")
            print("Please specify --plugin-type manually")
            return {}
    
    try:
        # Determine the correct module path based on plugin type
        if plugin_type in ["iut", "tester"]:
            # Use the protocol if specified for IUT/tester plugins
            if protocol:
                module_path = f"panther.plugins.services.{plugin_type}.{protocol}.{plugin_name}.config_schema"
                try:
                    plugin_module = importlib.import_module(module_path)
                    logger.debug(f"Found plugin schema at {module_path} with protocol {protocol}")
                except ImportError as e:
                    raise ImportError(f"Plugin schema not found at {module_path}: {e}")
            else:
                # Try direct path first
                try:
                    module_path = f"panther.plugins.services.{plugin_type}.{plugin_name}.config_schema"
                    plugin_module = importlib.import_module(module_path)
                    logger.debug(f"Found plugin schema at {module_path}")
                except ImportError:
                    # If not found, search in different protocol directories
                    found = False
                    for p in COMMON_PROTOCOLS:
                        try:
                            module_path = f"panther.plugins.services.{plugin_type}.{p}.{plugin_name}.config_schema"
                            plugin_module = importlib.import_module(module_path)
                            found = True
                            protocol = p  # Remember which protocol we found
                            logger.debug(f"Found plugin schema at {module_path}")
                            print(f"Found plugin under protocol: {p}")
                            break
                        except ImportError:
                            continue
                    
                    if not found:
                        raise ImportError(
                            f"Plugin schema for '{plugin_name}' not found. "
                            f"For {plugin_type} plugins, consider specifying the protocol with --protocol option."
                        )
        else:
            # For environment plugins
            module_path = f"panther.plugins.environments.{plugin_type}.{plugin_name}.config_schema"
            try:
                plugin_module = importlib.import_module(module_path)
                logger.debug(f"Found plugin schema at {module_path}")
            except ImportError as e:
                raise ImportError(f"Plugin schema not found at {module_path}: {e}")
        
        # Get the class name using the plugin loader helper
        class_name = PluginLoader.get_class_name(plugin_name)
        try:
            config_class = getattr(plugin_module, class_name)
        except AttributeError:
            raise AttributeError(f"No config class '{class_name}' found in module {module_path}")
        
        # Format and return the parameters
        parameters = {}
        
        # Use dataclasses introspection to get fields
        if dataclasses.is_dataclass(config_class):
            fields = dataclasses.fields(config_class)
            type_hints = get_type_hints(config_class)
            
            for field in fields:
                param_info = {
                    "type": str(type_hints.get(field.name, "unknown")),
                    "default": field.default if field.default is not dataclasses.MISSING else None,
                    "required": field.default is dataclasses.MISSING,
                    "description": inspect.getdoc(field) or "No description available"
                }
                
                # Special handling for version field
                if field.name == "version" and hasattr(config_class, "load_versions_from_files"):
                    try:
                        version_info = config_class.load_versions_from_files()
                        param_info["value"] = version_info
                        param_info["note"] = "Dynamically loaded from version config files"
                        # Add more detailed information for version fields
                        if hasattr(version_info, "version"):
                            param_info["version_number"] = version_info.version
                        if hasattr(version_info, "commit"):
                            param_info["commit"] = version_info.commit
                    except Exception as e:
                        logger.warning(f"Failed to load version information: {e}")
                
                parameters[field.name] = param_info
        
        return parameters
        
    except ImportError as e:
        print(f"Plugin schema for '{plugin_name}' not found. Check if the plugin name is correct.")
        print(f"Error details: {e}")
        
        # Give helpful guidance for IUT/tester plugins
        if plugin_type in ["iut", "tester"] and not protocol:
            print(f"\nFor {plugin_type} plugins, try specifying the protocol with --protocol option.")
            print(f"Available protocols: {', '.join(COMMON_PROTOCOLS)}")
            print(f"Example: panther --list-plugin-params {plugin_name} --plugin-type {plugin_type} --protocol quic")
            
        return {}
    except AttributeError as e:
        print(f"Error retrieving parameters for plugin '{plugin_name}': {e}")
        return {}
    except Exception as e:
        print(f"Unexpected error while listing parameters for plugin '{plugin_name}': {e}")
        return {}