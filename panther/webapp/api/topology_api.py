"""Topology API Endpoints.

FastAPI routes for topology editor operations.
"""

import logging
from fastapi import APIRouter, HTTPException
from panther.webapp.services.topology_service import get_topology_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/topology", tags=["topology"])


@router.get("/configs")
async def list_config_files():
    """List available YAML configuration files."""
    service = get_topology_service()
    return {"files": service.list_config_files()}


@router.get("/config/{filename}")
async def get_config_graph(filename: str):
    """Get graph representation of a configuration file.

    Args:
        filename: Name of the config file to load

    Returns:
        Graph data with nodes and edges
    """
    service = get_topology_service()
    
    config = service.load_config(filename)
    if not config:
        raise HTTPException(status_code=404, detail="Config file not found")
    
    graph = service.config_to_graph(config)
    return graph


@router.get("/config/{filename}/raw")
async def get_raw_config(filename: str):
    """Get raw configuration data.

    Args:
        filename: Name of the config file to load

    Returns:
        Raw config dictionary
    """
    service = get_topology_service()
    
    config = service.load_config(filename)
    if not config:
        raise HTTPException(status_code=404, detail="Config file not found")
    
    return config