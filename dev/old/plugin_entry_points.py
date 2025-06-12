"""
Entry point-based plugin discovery for PANTHER.

This module provides functions to discover plugins via entry points,
complementing the traditional file-based plugin discovery.
"""

import importlib.metadata
import logging
from typing import Any

logger = logging.getLogger("plugin_entry_points")


def discover_protocol_plugins() -> dict[str, Any]:
    """
    Discover protocol plugins registered via entry points.

    Returns:
        Dict[str, Any]: Dictionary mapping plugin names to loaded plugin classes
    """
    plugins = {}
    try:
        eps = importlib.metadata.entry_points(group="panther.plugins.protocols")
        for ep in eps:
            try:
                plugin_class = ep.load()
                plugins[ep.name] = plugin_class
                logger.info("Discovered protocol plugin via entry point: %s", ep.name)
            except Exception as e:
                logger.warning("Failed to load protocol plugin '%s': %s", ep.name, e)
    except Exception as e:
        logger.warning("Error discovering protocol plugins via entry points: %s", e)

    return plugins


def discover_execution_environment_plugins() -> dict[str, Any]:
    """
    Discover execution environment plugins registered via entry points.

    Returns:
        Dict[str, Any]: Dictionary mapping plugin names to loaded plugin classes
    """
    plugins = {}
    try:
        eps = importlib.metadata.entry_points(group="panther.plugins.environments.execution")
        for ep in eps:
            try:
                plugin_class = ep.load()
                plugins[ep.name] = plugin_class
                logger.info("Discovered execution environment plugin via entry point: %s", ep.name)
            except Exception as e:
                logger.warning("Failed to load execution environment plugin '%s': %s", ep.name, e)
    except Exception as e:
        logger.warning("Error discovering execution environment plugins via entry points: %s", e)

    return plugins


def discover_network_environment_plugins() -> dict[str, Any]:
    """
    Discover network environment plugins registered via entry points.

    Returns:
        Dict[str, Any]: Dictionary mapping plugin names to loaded plugin classes
    """
    plugins = {}
    try:
        eps = importlib.metadata.entry_points(group="panther.plugins.environments.network")
        for ep in eps:
            try:
                plugin_class = ep.load()
                plugins[ep.name] = plugin_class
                logger.info("Discovered network environment plugin via entry point: %s", ep.name)
            except (ImportError, AttributeError) as e:
                logger.warning("Failed to load network environment plugin '%s': %s", ep.name, e)
    except Exception as e:
        logger.warning("Error discovering network environment plugins via entry points: %s", e)

    return plugins


def discover_all_plugins() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
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
