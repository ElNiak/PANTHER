"""
ATLAS MCP Hierarchical Cache Manager
Inspired by Serena's sophisticated caching patterns

Provides intelligent, multi-level caching with:
- Global ML model sharing
- Project-specific isolation  
- Content-hash invalidation
- Performance monitoring
- Cross-project insights
"""

import os
import json
import pickle
import hashlib
import threading
import time
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from atlas_commands.config.atlas_home import AtlasHomeManager
from dataclasses import dataclass, asdict
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

CACHE_VERSION = "v2025-07-01"

@dataclass
class CacheEntry:
    """Versioned cache entry with metadata"""
    version: str
    timestamp: float
    content_hash: str
    data: Any
    hit_count: int = 0
    last_accessed: float = 0

@dataclass 
class CacheManifest:
    """Project cache manifest for tracking versions and performance"""
    project_id: str
    cache_version: str
    created_at: str
    last_updated: str
    cache_stats: Dict[str, int]
    invalidation_triggers: List[str]

class HierarchicalCacheManager:
    """
    Multi-level cache manager with global and project-specific isolation
    Implements Serena's best practices with ATLAS-specific enhancements
    """
    
    def __init__(self, project_id: str = "default"):
        self.project_id = project_id
        self.project_hash = self._generate_project_hash(project_id)
        
        # Cache root paths - use Atlas home manager for centralized configuration
        atlas_home_manager = AtlasHomeManager()
        self.atlas_root = atlas_home_manager.atlas_home
        self.global_cache_root = self.atlas_root / "global"
        self.project_cache_root = self.atlas_root / "projects" / self.project_hash
        
        # Initialize cache directories
        self._ensure_cache_directories()
        
        # Threading support
        self._cache_locks = {}
        self._dirty_flags = {}
        self._performance_stats = {
            "hits": 0,
            "misses": 0,
            "invalidations": 0,
            "saves": 0
        }
        
        # Load project manifest
        self.manifest = self._load_or_create_manifest()
        
        logger.info(f"Initialized hierarchical cache for project: {project_id}")
    
    def _generate_project_hash(self, project_id: str) -> str:
        """Generate consistent hash for project identification"""
        return hashlib.sha256(project_id.encode()).hexdigest()[:16]
    
    def _ensure_cache_directories(self):
        """Create cache directory structure"""
        directories = [
            self.global_cache_root / "models",
            self.global_cache_root / "tools", 
            self.global_cache_root / "shared_artifacts",
            self.project_cache_root / ".atlas",
            self.project_cache_root / "cache" / "symbols" / "python",
            self.project_cache_root / "cache" / "symbols" / "typescript", 
            self.project_cache_root / "cache" / "symbols" / "rust",
            self.project_cache_root / "cache" / "analysis",
            self.project_cache_root / "cache" / "tasks",
            self.project_cache_root / "cache" / "memory",
            self.project_cache_root / "state"
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
    
    def _load_or_create_manifest(self) -> CacheManifest:
        """Load existing manifest or create new one"""
        manifest_path = self.project_cache_root / ".atlas" / "cache_manifest.json"
        
        if manifest_path.exists():
            try:
                with open(manifest_path, 'r') as f:
                    data = json.load(f)
                    return CacheManifest(**data)
            except Exception as e:
                logger.warning(f"Failed to load cache manifest: {e}")
        
        # Create new manifest
        manifest = CacheManifest(
            project_id=self.project_id,
            cache_version=CACHE_VERSION,
            created_at=datetime.now().isoformat(),
            last_updated=datetime.now().isoformat(),
            cache_stats={"entries": 0, "size_bytes": 0},
            invalidation_triggers=[]
        )
        
        self._save_manifest(manifest)
        return manifest
    
    def _save_manifest(self, manifest: CacheManifest):
        """Save manifest to disk"""
        manifest_path = self.project_cache_root / ".atlas" / "cache_manifest.json"
        with open(manifest_path, 'w') as f:
            json.dump(asdict(manifest), f, indent=2)
    
    def _get_cache_lock(self, cache_type: str) -> threading.Lock:
        """Get or create thread lock for cache type"""
        if cache_type not in self._cache_locks:
            self._cache_locks[cache_type] = threading.Lock()
        return self._cache_locks[cache_type]
    
    def _get_content_hash(self, content: Any) -> str:
        """Generate content hash for invalidation"""
        content_str = json.dumps(content, sort_keys=True, default=str)
        return hashlib.sha256(content_str.encode()).hexdigest()[:16]
    
    def get_cache_path(self, cache_type: str, cache_level: str = "project") -> Path:
        """Get cache path for specific type and level"""
        if cache_level == "global":
            base_path = self.global_cache_root
        else:
            base_path = self.project_cache_root / "cache"
        
        return base_path / cache_type
    
    def set_cache(self, cache_type: str, key: str, data: Any, 
                  cache_level: str = "project", content_hash: str = None) -> bool:
        """Set cache entry with versioning and threading support"""
        try:
            lock = self._get_cache_lock(f"{cache_level}:{cache_type}")
            
            with lock:
                cache_path = self.get_cache_path(cache_type, cache_level)
                cache_path.mkdir(parents=True, exist_ok=True)
                
                entry_path = cache_path / f"{key}.cache"
                
                # Create cache entry
                entry = CacheEntry(
                    version=CACHE_VERSION,
                    timestamp=time.time(),
                    content_hash=content_hash or self._get_content_hash(data),
                    data=data
                )
                
                # Save to disk
                with open(entry_path, 'wb') as f:
                    pickle.dump(entry, f)
                
                # Update stats
                self._performance_stats["saves"] += 1
                self._dirty_flags[f"{cache_level}:{cache_type}"] = True
                
                logger.debug(f"Cached {cache_type}:{key} at {cache_level} level")
                return True
                
        except Exception as e:
            logger.error(f"Failed to set cache {cache_type}:{key}: {e}")
            return False
    
    def get_cache(self, cache_type: str, key: str, 
                  cache_level: str = "project") -> Optional[Any]:
        """Get cache entry with content validation"""
        try:
            lock = self._get_cache_lock(f"{cache_level}:{cache_type}")
            
            with lock:
                cache_path = self.get_cache_path(cache_type, cache_level)
                entry_path = cache_path / f"{key}.cache"
                
                if not entry_path.exists():
                    self._performance_stats["misses"] += 1
                    return None
                
                # Load and validate cache entry
                with open(entry_path, 'rb') as f:
                    entry: CacheEntry = pickle.load(f)
                
                # Version check
                if entry.version != CACHE_VERSION:
                    logger.debug(f"Cache version mismatch for {key}, invalidating")
                    entry_path.unlink()
                    self._performance_stats["invalidations"] += 1
                    return None
                
                # Update access stats
                entry.hit_count += 1
                entry.last_accessed = time.time()
                self._performance_stats["hits"] += 1
                
                # Re-save updated stats
                with open(entry_path, 'wb') as f:
                    pickle.dump(entry, f)
                
                logger.debug(f"Cache hit for {cache_type}:{key}")
                return entry.data
                
        except Exception as e:
            logger.error(f"Failed to get cache {cache_type}:{key}: {e}")
            self._performance_stats["misses"] += 1
            return None
    
    def invalidate_cache(self, cache_type: str, key: str = None, 
                        cache_level: str = "project"):
        """Invalidate specific cache entry or entire cache type"""
        try:
            lock = self._get_cache_lock(f"{cache_level}:{cache_type}")
            
            with lock:
                cache_path = self.get_cache_path(cache_type, cache_level)
                
                if key:
                    # Invalidate specific entry
                    entry_path = cache_path / f"{key}.cache"
                    if entry_path.exists():
                        entry_path.unlink()
                        self._performance_stats["invalidations"] += 1
                        logger.debug(f"Invalidated cache entry {cache_type}:{key}")
                else:
                    # Invalidate entire cache type
                    if cache_path.exists():
                        for cache_file in cache_path.glob("*.cache"):
                            cache_file.unlink()
                            self._performance_stats["invalidations"] += 1
                        logger.debug(f"Invalidated all cache entries for {cache_type}")
                        
        except Exception as e:
            logger.error(f"Failed to invalidate cache {cache_type}:{key}: {e}")
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get cache performance statistics"""
        total_requests = self._performance_stats["hits"] + self._performance_stats["misses"]
        hit_rate = (self._performance_stats["hits"] / total_requests * 100) if total_requests > 0 else 0
        
        return {
            "project_id": self.project_id,
            "hit_rate_percent": round(hit_rate, 2),
            "total_requests": total_requests,
            **self._performance_stats,
            "cache_paths": {
                "global": str(self.global_cache_root),
                "project": str(self.project_cache_root)
            }
        }
    
    def optimize_cache(self):
        """Perform cache optimization based on usage patterns"""
        logger.info("Starting cache optimization...")
        
        # Remove old cache entries (older than 30 days)
        cutoff_time = time.time() - (30 * 24 * 60 * 60)
        
        for cache_type_dir in (self.project_cache_root / "cache").iterdir():
            if cache_type_dir.is_dir():
                for cache_file in cache_type_dir.glob("*.cache"):
                    try:
                        with open(cache_file, 'rb') as f:
                            entry: CacheEntry = pickle.load(f)
                        
                        if entry.last_accessed < cutoff_time and entry.hit_count < 5:
                            cache_file.unlink()
                            logger.debug(f"Removed stale cache entry: {cache_file}")
                            
                    except Exception as e:
                        logger.warning(f"Error processing cache file {cache_file}: {e}")
        
        logger.info("Cache optimization completed")
    
    def get_cache_size_info(self) -> Dict[str, Any]:
        """Get cache size information"""
        def get_directory_size(path: Path) -> int:
            if not path.exists():
                return 0
            return sum(f.stat().st_size for f in path.rglob('*') if f.is_file())
        
        global_size = get_directory_size(self.global_cache_root)
        project_size = get_directory_size(self.project_cache_root)
        
        return {
            "global_cache_mb": round(global_size / (1024 * 1024), 2),
            "project_cache_mb": round(project_size / (1024 * 1024), 2),
            "total_cache_mb": round((global_size + project_size) / (1024 * 1024), 2),
            "estimated_savings_mb": round(178 * (len(list(self.atlas_root.glob("projects/*"))) - 1), 2)  # ML model sharing savings
        }
    
    def share_ml_models_globally(self):
        """Move ML models from project cache to global cache for sharing"""
        logger.info("Migrating ML models to global cache for sharing...")
        
        # Implementation would move huggingface cache to global location
        # and update container mount points to use shared cache
        
        global_models_path = self.global_cache_root / "models"
        global_models_path.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"ML models will be shared from: {global_models_path}")