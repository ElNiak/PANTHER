"""
Smart Cache Invalidation System with File Dependency Tracking
Phase 2 implementation of ATLAS Hierarchical Cache Architecture
"""

import hashlib
import json
import os
import time
from pathlib import Path
from typing import Dict, List, Set, Optional, Any
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor
import threading

from .hierarchical_cache_manager import CacheEntry, HierarchicalCacheManager


@dataclass
class FileDependency:
    """Represents a file dependency relationship"""
    file_path: str
    content_hash: str
    last_modified: float
    dependent_caches: Set[str]  # Cache types that depend on this file
    dependency_type: str  # 'import', 'include', 'reference', etc.


@dataclass
class CacheDependencyGraph:
    """Graph of cache dependencies for invalidation cascade"""
    dependencies: Dict[str, Set[str]]  # file_path -> set of dependent cache keys
    reverse_dependencies: Dict[str, Set[str]]  # cache_key -> set of file dependencies
    last_updated: float


class ContentHashValidator:
    """Validates cache entries using content hashes and manages dependency invalidation"""
    
    def __init__(self, cache_manager: HierarchicalCacheManager):
        self.cache_manager = cache_manager
        self.dependencies: Dict[str, FileDependency] = {}
        self.dependency_graph = CacheDependencyGraph({}, {}, time.time())
        self._lock = threading.Lock()
        
        # Initialize dependency tracking directory
        self.deps_path = cache_manager.project_cache_root / "dependencies"
        self.deps_path.mkdir(parents=True, exist_ok=True)
        
        # Load existing dependencies
        self._load_dependencies()
    
    def get_file_hash(self, file_path: str) -> Optional[str]:
        """Calculate content hash for a file"""
        try:
            file_path_obj = Path(file_path)
            if not file_path_obj.exists():
                return None
                
            with open(file_path_obj, 'rb') as f:
                content = f.read()
                return hashlib.sha256(content).hexdigest()[:16]  # 16-char hash
        except Exception:
            return None
    
    def validate_cache_entry(self, file_path: str, cache_entry: CacheEntry) -> bool:
        """Validate if cache entry is still valid based on file content hash"""
        if not cache_entry.content_hash:
            return True  # No content hash means no validation needed
            
        current_hash = self.get_file_hash(file_path)
        if current_hash is None:
            return False  # File doesn't exist, cache is invalid
            
        return current_hash == cache_entry.content_hash
    
    def register_file_dependency(self, file_path: str, cache_type: str, 
                                cache_key: str, dependency_type: str = "reference"):
        """Register a file as dependency for a cache entry"""
        with self._lock:
            abs_file_path = str(Path(file_path).resolve())
            
            # Update file dependency info
            if abs_file_path not in self.dependencies:
                self.dependencies[abs_file_path] = FileDependency(
                    file_path=abs_file_path,
                    content_hash=self.get_file_hash(abs_file_path) or "",
                    last_modified=os.path.getmtime(abs_file_path) if Path(abs_file_path).exists() else 0,
                    dependent_caches=set(),
                    dependency_type=dependency_type
                )
            
            # Add cache to dependent caches
            cache_id = f"{cache_type}:{cache_key}"
            self.dependencies[abs_file_path].dependent_caches.add(cache_id)
            
            # Update dependency graph
            if abs_file_path not in self.dependency_graph.dependencies:
                self.dependency_graph.dependencies[abs_file_path] = set()
            self.dependency_graph.dependencies[abs_file_path].add(cache_id)
            
            if cache_id not in self.dependency_graph.reverse_dependencies:
                self.dependency_graph.reverse_dependencies[cache_id] = set()
            self.dependency_graph.reverse_dependencies[cache_id].add(abs_file_path)
            
            self.dependency_graph.last_updated = time.time()
    
    def find_dependent_caches(self, file_path: str) -> Set[str]:
        """Find all cache entries that depend on a file"""
        abs_file_path = str(Path(file_path).resolve())
        
        if abs_file_path in self.dependency_graph.dependencies:
            return self.dependency_graph.dependencies[abs_file_path].copy()
        return set()
    
    def invalidate_dependent_caches(self, file_path: str) -> Dict[str, int]:
        """Invalidate all caches that depend on a file"""
        invalidation_stats = {"invalidated": 0, "errors": 0}
        
        dependent_caches = self.find_dependent_caches(file_path)
        
        for cache_id in dependent_caches:
            try:
                cache_type, cache_key = cache_id.split(":", 1)
                self.cache_manager.invalidate_cache(cache_type, cache_key)
                invalidation_stats["invalidated"] += 1
            except Exception:
                invalidation_stats["errors"] += 1
        
        return invalidation_stats
    
    def validate_all_dependencies(self) -> Dict[str, Any]:
        """Validate all file dependencies and invalidate stale caches"""
        validation_stats = {
            "files_checked": 0,
            "files_changed": 0,
            "caches_invalidated": 0,
            "errors": 0
        }
        
        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = []
            
            for file_path, dependency in self.dependencies.items():
                future = executor.submit(self._validate_single_dependency, file_path, dependency)
                futures.append(future)
            
            for future in futures:
                try:
                    result = future.result()
                    validation_stats["files_checked"] += 1
                    if result["changed"]:
                        validation_stats["files_changed"] += 1
                        validation_stats["caches_invalidated"] += result["invalidated"]
                except Exception:
                    validation_stats["errors"] += 1
        
        return validation_stats
    
    def _validate_single_dependency(self, file_path: str, dependency: FileDependency) -> Dict[str, Any]:
        """Validate a single file dependency"""
        result = {"changed": False, "invalidated": 0}
        
        if not Path(file_path).exists():
            # File was deleted, invalidate all dependent caches
            invalidation_stats = self.invalidate_dependent_caches(file_path)
            result["changed"] = True
            result["invalidated"] = invalidation_stats["invalidated"]
            
            # Remove from dependencies
            with self._lock:
                if file_path in self.dependencies:
                    del self.dependencies[file_path]
            return result
        
        # Check if file content changed
        current_hash = self.get_file_hash(file_path)
        current_mtime = os.path.getmtime(file_path)
        
        if (current_hash != dependency.content_hash or 
            current_mtime > dependency.last_modified):
            
            # File changed, invalidate dependent caches
            invalidation_stats = self.invalidate_dependent_caches(file_path)
            result["changed"] = True
            result["invalidated"] = invalidation_stats["invalidated"]
            
            # Update dependency info
            with self._lock:
                dependency.content_hash = current_hash or ""
                dependency.last_modified = current_mtime
        
        return result
    
    def get_dependency_stats(self) -> Dict[str, Any]:
        """Get statistics about dependency tracking"""
        with self._lock:
            total_files = len(self.dependencies)
            total_caches = len(self.dependency_graph.reverse_dependencies)
            
            # Calculate dependency types distribution
            dependency_types = {}
            for dep in self.dependencies.values():
                dep_type = dep.dependency_type
                dependency_types[dep_type] = dependency_types.get(dep_type, 0) + 1
            
            return {
                "total_tracked_files": total_files,
                "total_dependent_caches": total_caches,
                "dependency_types": dependency_types,
                "last_validation": self.dependency_graph.last_updated,
                "average_dependents_per_file": total_caches / max(total_files, 1)
            }
    
    def optimize_dependencies(self) -> Dict[str, Any]:
        """Clean up stale dependencies and optimize graph"""
        optimization_stats = {
            "removed_files": 0,
            "removed_caches": 0,
            "orphaned_caches": 0
        }
        
        with self._lock:
            # Remove dependencies for non-existent files
            files_to_remove = []
            for file_path in self.dependencies:
                if not Path(file_path).exists():
                    files_to_remove.append(file_path)
            
            for file_path in files_to_remove:
                del self.dependencies[file_path]
                if file_path in self.dependency_graph.dependencies:
                    del self.dependency_graph.dependencies[file_path]
                optimization_stats["removed_files"] += 1
            
            # Remove orphaned cache references
            all_cache_ids = set()
            for dep in self.dependencies.values():
                all_cache_ids.update(dep.dependent_caches)
            
            orphaned_caches = set(self.dependency_graph.reverse_dependencies.keys()) - all_cache_ids
            for cache_id in orphaned_caches:
                del self.dependency_graph.reverse_dependencies[cache_id]
                optimization_stats["orphaned_caches"] += 1
        
        self._save_dependencies()
        return optimization_stats
    
    def _load_dependencies(self):
        """Load dependency tracking data from disk"""
        deps_file = self.deps_path / "dependencies.json"
        if not deps_file.exists():
            return
        
        try:
            with open(deps_file, 'r') as f:
                data = json.load(f)
            
            # Reconstruct dependencies
            for file_path, dep_data in data.get("dependencies", {}).items():
                self.dependencies[file_path] = FileDependency(
                    file_path=dep_data["file_path"],
                    content_hash=dep_data["content_hash"],
                    last_modified=dep_data["last_modified"],
                    dependent_caches=set(dep_data["dependent_caches"]),
                    dependency_type=dep_data["dependency_type"]
                )
            
            # Reconstruct dependency graph
            graph_data = data.get("dependency_graph", {})
            self.dependency_graph = CacheDependencyGraph(
                dependencies={k: set(v) for k, v in graph_data.get("dependencies", {}).items()},
                reverse_dependencies={k: set(v) for k, v in graph_data.get("reverse_dependencies", {}).items()},
                last_updated=graph_data.get("last_updated", time.time())
            )
            
        except Exception:
            # If loading fails, start fresh
            self.dependencies = {}
            self.dependency_graph = CacheDependencyGraph({}, {}, time.time())
    
    def _save_dependencies(self):
        """Save dependency tracking data to disk"""
        deps_file = self.deps_path / "dependencies.json"
        
        try:
            # Convert dependencies to serializable format
            deps_data = {}
            for file_path, dep in self.dependencies.items():
                deps_data[file_path] = {
                    "file_path": dep.file_path,
                    "content_hash": dep.content_hash,
                    "last_modified": dep.last_modified,
                    "dependent_caches": list(dep.dependent_caches),
                    "dependency_type": dep.dependency_type
                }
            
            # Convert dependency graph to serializable format
            graph_data = {
                "dependencies": {k: list(v) for k, v in self.dependency_graph.dependencies.items()},
                "reverse_dependencies": {k: list(v) for k, v in self.dependency_graph.reverse_dependencies.items()},
                "last_updated": self.dependency_graph.last_updated
            }
            
            data = {
                "dependencies": deps_data,
                "dependency_graph": graph_data,
                "version": "v2025-07-01"
            }
            
            with open(deps_file, 'w') as f:
                json.dump(data, f, indent=2)
                
        except Exception:
            # If saving fails, continue silently
            pass


class SmartCacheInvalidator:
    """High-level interface for smart cache invalidation"""
    
    def __init__(self, cache_manager: HierarchicalCacheManager):
        self.cache_manager = cache_manager
        self.validator = ContentHashValidator(cache_manager)
    
    def track_file_dependency(self, file_path: str, cache_type: str, cache_key: str, 
                             dependency_type: str = "reference"):
        """Track a file as dependency for a cache entry"""
        self.validator.register_file_dependency(file_path, cache_type, cache_key, dependency_type)
    
    def invalidate_if_changed(self, file_path: str) -> bool:
        """Check if file changed and invalidate dependent caches"""
        current_hash = self.validator.get_file_hash(file_path)
        if file_path not in self.validator.dependencies:
            return False
        
        stored_hash = self.validator.dependencies[file_path].content_hash
        if current_hash != stored_hash:
            self.validator.invalidate_dependent_caches(file_path)
            return True
        return False
    
    def validate_all_caches(self) -> Dict[str, Any]:
        """Validate all cached data against file dependencies"""
        return self.validator.validate_all_dependencies()
    
    def get_cache_health_report(self) -> Dict[str, Any]:
        """Generate comprehensive cache health report"""
        dependency_stats = self.validator.get_dependency_stats()
        cache_stats = self.cache_manager.get_performance_stats()
        
        return {
            "dependency_tracking": dependency_stats,
            "cache_performance": cache_stats,
            "timestamp": time.time(),
            "validation_needed": time.time() - dependency_stats["last_validation"] > 3600  # 1 hour
        }