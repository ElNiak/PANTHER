"""
Entry point-based plugin discovery for PANTHER.

This module provides functions to discover plugins via entry points,
complementing the traditional file-based plugin discovery.
"""

import importlib.metadata
import logging
from typing import Dict, List, Any, Optional, Tuple

logger = logging.getLogger("plugin_entry_points")

def discover_protocol_plugins() -> Dict[str, Any]:
    """
    Discover protocol plugins registered via entry points.
    
    Returns:
        Dict[str, Any]: Dictionary mapping plugin names to loaded plugin classes
    """
    plugins = {}
    try:
        eps = importlib.metadata.entry_points(group='panther.plugins.protocols')
        for ep in eps:
            try:
                plugin_class = ep.load()
                plugins[ep.name] = plugin_class
                logger.info(f"Discovered protocol plugin via entry point: {ep.name}")
            except Exception as e:
                logger.warning(f"Failed to load protocol plugin '{ep.name}': {e}")
    except Exception as e:
        logger.warning(f"Error discovering protocol plugins via entry points: {e}")
    
    return plugins

def discover_execution_environment_plugins() -> Dict[str, Any]:
    """
    Discover execution environment plugins registered via entry points.
    
    Returns:
        Dict[str, Any]: Dictionary mapping plugin names to loaded plugin classes
    """
    plugins = {}
    try:
        eps = importlib.metadata.entry_points(group='panther.plugins.environments.execution')
        for ep in eps:
            try:
                plugin_class = ep.load()
                plugins[ep.name] = plugin_class
                logger.info(f"Discovered execution environment plugin via entry point: {ep.name}")
            except Exception as e:
                logger.warning(f"Failed to load execution environment plugin '{ep.name}': {e}")
    except Exception as e:
        logger.warning(f"Error discovering execution environment plugins via entry points: {e}")
    
    return plugins

def discover_network_environment_plugins() -> Dict[str, Any]:
    """
    Discover network environment plugins registered via entry points.
    
    Returns:
        Dict[str, Any]: Dictionary mapping plugin names to loaded plugin classes
    """
    plugins = {}
    try:
        eps = importlib.metadata.entry_points(group='panther.plugins.environments.network')
        for ep in eps:
            try:
                plugin_class = ep.load()
                plugins[ep.name] = plugin_class
                logger.info(f"Discovered network environment plugin via entry point: {ep.name}")
            except Exception as e:
                logger.warning(f"Failed to load network environment plugin '{ep.name}': {e}")
    except Exception as e:
        logger.warning(f"Error discovering network environment plugins via entry points: {e}")
    
    return plugins

def discover_all_plugins() -> Tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any]]:
    """
    Discover all plugins registered via entry points.
    
    Returns:
        Tuple[Dict[str, Any], Dict[str, Any], Dict[str, Any]]: A tuple containing:
            - Protocol plugins
            - Execution environment plugins
            - Network environment plugins
    """
    protocol_plugins = discover_protocol_plugins()
    execution_env_plugins = discover_execution_environment_plugins()
    network_env_plugins = discover_network_environment_plugins()
    
    return protocol_plugins, execution_env_plugins, network_env_plugins
