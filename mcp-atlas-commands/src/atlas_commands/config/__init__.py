"""Atlas configuration management."""

from .atlas_home import (
    AtlasHomeManager,
    get_atlas_home_manager,
    get_atlas_home,
    get_projects_dir,
    get_cache_dir,
    get_coordination_dir,
    setup_atlas_environment
)

__all__ = [
    'AtlasHomeManager',
    'get_atlas_home_manager', 
    'get_atlas_home',
    'get_projects_dir',
    'get_cache_dir',
    'get_coordination_dir',
    'setup_atlas_environment'
]