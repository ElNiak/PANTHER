"""Centralized Atlas home directory configuration.

This module provides a unified way to manage all Atlas MCP output paths,
ensuring all files are organized under a configurable base directory.
"""

import os
from pathlib import Path
from typing import Dict, Optional


class AtlasHomeManager:
    """Manages centralized Atlas home directory configuration."""
    
    def __init__(self, atlas_home: Optional[str] = None):
        """Initialize Atlas home manager.
        
        Args:
            atlas_home: Base directory for all Atlas outputs. 
                       Defaults to ATLAS_HOME env var or ~/.atlas/
        """
        if atlas_home:
            self.atlas_home = Path(atlas_home)
        else:
            # Priority: ATLAS_HOME env var > ~/.atlas/ default
            default_home = os.path.expanduser("~/.atlas")
            atlas_home_str = os.environ.get('ATLAS_HOME', default_home)
            self.atlas_home = Path(atlas_home_str)
        
        # Ensure base directory exists
        self.atlas_home.mkdir(parents=True, exist_ok=True)
        
        # Initialize standard subdirectories
        self._init_standard_dirs()
    
    def _init_standard_dirs(self) -> None:
        """Initialize standard Atlas subdirectories."""
        standard_dirs = [
            'projects',      # Project-specific storage (replaces /app/REPOS)
            'cache',         # Cache files (L3 file cache)
            'logs',          # Log files
            'backups',       # Backup files
            'coordination',  # Cross-project coordination
            'temp',          # Temporary files
            'models'         # ML models and embeddings
        ]
        
        for dir_name in standard_dirs:
            (self.atlas_home / dir_name).mkdir(parents=True, exist_ok=True)
    
    def get_projects_dir(self) -> Path:
        """Get projects directory (replaces /app/REPOS)."""
        return self.atlas_home / 'projects'
    
    def get_cache_dir(self) -> Path:
        """Get cache directory for L3 file cache."""
        return self.atlas_home / 'cache'
    
    def get_logs_dir(self) -> Path:
        """Get logs directory."""
        return self.atlas_home / 'logs'
    
    def get_coordination_dir(self) -> Path:
        """Get coordination directory for cross-project data."""
        return self.atlas_home / 'coordination'
    
    def get_temp_dir(self) -> Path:
        """Get temporary files directory."""
        return self.atlas_home / 'temp'
    
    def get_models_dir(self) -> Path:
        """Get ML models directory."""
        return self.atlas_home / 'models'
    
    def get_project_dir(self, project_name: str) -> Path:
        """Get directory for specific project.
        
        Args:
            project_name: Name of the project
            
        Returns:
            Path to project directory
        """
        project_dir = self.get_projects_dir() / project_name
        project_dir.mkdir(parents=True, exist_ok=True)
        return project_dir
    
    def get_all_paths(self) -> Dict[str, Path]:
        """Get all standard Atlas paths.
        
        Returns:
            Dictionary mapping path names to Path objects
        """
        return {
            'atlas_home': self.atlas_home,
            'projects': self.get_projects_dir(),
            'cache': self.get_cache_dir(),
            'logs': self.get_logs_dir(),
            'coordination': self.get_coordination_dir(),
            'temp': self.get_temp_dir(),
            'models': self.get_models_dir()
        }
    


# Global instance for convenient access
_atlas_home_manager: Optional[AtlasHomeManager] = None


def get_atlas_home_manager() -> AtlasHomeManager:
    """Get the global Atlas home manager instance."""
    global _atlas_home_manager
    if _atlas_home_manager is None:
        _atlas_home_manager = AtlasHomeManager()
    return _atlas_home_manager


def get_atlas_home() -> Path:
    """Get the Atlas home directory path."""
    return get_atlas_home_manager().atlas_home


def get_projects_dir() -> Path:
    """Get the projects directory (replaces /app/REPOS)."""
    return get_atlas_home_manager().get_projects_dir()


def get_cache_dir() -> Path:
    """Get the cache directory."""
    return get_atlas_home_manager().get_cache_dir()


def get_coordination_dir() -> Path:
    """Get the coordination directory."""
    return get_atlas_home_manager().get_coordination_dir()


# Environment variable helpers
def setup_atlas_environment() -> Dict[str, str]:
    """Set up environment variables for Atlas home integration.
    
    Returns:
        Dictionary of environment variables to set
    """
    manager = get_atlas_home_manager()
    
    return {
        'ATLAS_HOME': str(manager.atlas_home),
        'ATLAS_PROJECTS_DIR': str(manager.get_projects_dir()),
        'ATLAS_CACHE_DIR': str(manager.get_cache_dir()),
        'ATLAS_LOGS_DIR': str(manager.get_logs_dir()),
        'ATLAS_COORDINATION_DIR': str(manager.get_coordination_dir()),
        'ATLAS_TEMP_DIR': str(manager.get_temp_dir()),
        'ATLAS_MODELS_DIR': str(manager.get_models_dir())
    }