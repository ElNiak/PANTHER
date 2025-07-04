"""
Unit tests for ATLAS Hierarchical Cache Manager
Tests cache operations, project isolation, and performance features
"""

import os
import tempfile
import shutil
import pytest
import time
from pathlib import Path
from unittest.mock import patch

from src.atlas_commands.caching.hierarchical_cache_manager import (
    HierarchicalCacheManager,
    CacheEntry,
    CacheManifest,
    CACHE_VERSION
)


class TestHierarchicalCacheManager:
    """Test suite for hierarchical cache manager"""
    
    @pytest.fixture
    def temp_atlas_dir(self):
        """Create temporary .atlas directory for testing"""
        temp_dir = tempfile.mkdtemp()
        atlas_dir = Path(temp_dir) / ".atlas"
        atlas_dir.mkdir(parents=True, exist_ok=True)
        
        # Mock home directory
        with patch.object(Path, 'home', return_value=Path(temp_dir)):
            yield atlas_dir
        
        # Cleanup
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def cache_manager(self, temp_atlas_dir):
        """Create cache manager instance for testing"""
        with patch.object(Path, 'home', return_value=temp_atlas_dir.parent):
            manager = HierarchicalCacheManager("test-project")
            return manager
    
    def test_project_hash_generation(self, cache_manager):
        """Test project hash generation is consistent"""
        hash1 = cache_manager._generate_project_hash("test-project")
        hash2 = cache_manager._generate_project_hash("test-project")
        hash3 = cache_manager._generate_project_hash("other-project")
        
        assert hash1 == hash2  # Same project = same hash
        assert hash1 != hash3  # Different project = different hash
        assert len(hash1) == 16  # Expected hash length
    
    def test_cache_directory_creation(self, cache_manager):
        """Test cache directories are created correctly"""
        expected_dirs = [
            cache_manager.global_cache_root / "models",
            cache_manager.global_cache_root / "tools",
            cache_manager.global_cache_root / "shared_artifacts",
            cache_manager.project_cache_root / ".atlas",
            cache_manager.project_cache_root / "cache" / "symbols" / "python",
            cache_manager.project_cache_root / "cache" / "analysis",
            cache_manager.project_cache_root / "state"
        ]
        
        for directory in expected_dirs:
            assert directory.exists(), f"Directory {directory} was not created"
    
    def test_cache_entry_creation(self, cache_manager):
        """Test cache entry creation and retrieval"""
        test_data = {"key": "value", "number": 42}
        cache_type = "test_cache"
        key = "test_key"
        
        # Set cache entry
        success = cache_manager.set_cache(cache_type, key, test_data)
        assert success
        
        # Get cache entry
        retrieved_data = cache_manager.get_cache(cache_type, key)
        assert retrieved_data == test_data
        
        # Verify cache file exists
        cache_path = cache_manager.get_cache_path(cache_type)
        cache_file = cache_path / f"{key}.cache"
        assert cache_file.exists()
    
    def test_content_hash_invalidation(self, cache_manager):
        """Test content hash-based cache invalidation"""
        cache_type = "test_cache"
        key = "test_key"
        
        # Set initial data
        data1 = {"version": 1}
        cache_manager.set_cache(cache_type, key, data1)
        retrieved1 = cache_manager.get_cache(cache_type, key)
        assert retrieved1 == data1
        
        # Update data with different content
        data2 = {"version": 2}
        cache_manager.set_cache(cache_type, key, data2)
        retrieved2 = cache_manager.get_cache(cache_type, key)
        assert retrieved2 == data2
        assert retrieved2 != data1
    
    def test_cache_levels(self, cache_manager):
        """Test global vs project cache levels"""
        test_data = {"shared": True}
        cache_type = "models"
        key = "shared_model"
        
        # Set global cache
        success = cache_manager.set_cache(cache_type, key, test_data, cache_level="global")
        assert success
        
        # Retrieve from global cache
        retrieved = cache_manager.get_cache(cache_type, key, cache_level="global")
        assert retrieved == test_data
        
        # Verify global path is used
        global_path = cache_manager.get_cache_path(cache_type, "global")
        project_path = cache_manager.get_cache_path(cache_type, "project")
        assert str(global_path) != str(project_path)
        assert "global" in str(global_path)
        assert "projects" in str(project_path)
    
    def test_cache_invalidation(self, cache_manager):
        """Test cache invalidation functionality"""
        cache_type = "test_cache"
        key1 = "key1"
        key2 = "key2"
        data = {"test": True}
        
        # Set multiple cache entries
        cache_manager.set_cache(cache_type, key1, data)
        cache_manager.set_cache(cache_type, key2, data)
        
        # Verify both exist
        assert cache_manager.get_cache(cache_type, key1) is not None
        assert cache_manager.get_cache(cache_type, key2) is not None
        
        # Invalidate specific key
        cache_manager.invalidate_cache(cache_type, key1)
        assert cache_manager.get_cache(cache_type, key1) is None
        assert cache_manager.get_cache(cache_type, key2) is not None
        
        # Invalidate entire cache type
        cache_manager.invalidate_cache(cache_type)
        assert cache_manager.get_cache(cache_type, key2) is None
    
    def test_performance_stats(self, cache_manager):
        """Test performance statistics tracking"""
        cache_type = "test_cache"
        key = "test_key"
        data = {"test": True}
        
        # Initial stats
        stats = cache_manager.get_performance_stats()
        initial_hits = stats["hits"]
        initial_misses = stats["misses"]
        
        # Cache miss
        result = cache_manager.get_cache(cache_type, key)
        assert result is None
        
        stats = cache_manager.get_performance_stats()
        assert stats["misses"] == initial_misses + 1
        
        # Cache set and hit
        cache_manager.set_cache(cache_type, key, data)
        result = cache_manager.get_cache(cache_type, key)
        assert result == data
        
        stats = cache_manager.get_performance_stats()
        assert stats["hits"] == initial_hits + 1
        assert stats["hit_rate_percent"] > 0
    
    def test_cache_version_compatibility(self, cache_manager):
        """Test cache version handling"""
        cache_type = "test_cache"
        key = "test_key"
        data = {"test": True}
        
        # Set cache entry
        cache_manager.set_cache(cache_type, key, data)
        
        # Manually modify cache entry to old version
        cache_path = cache_manager.get_cache_path(cache_type)
        cache_file = cache_path / f"{key}.cache"
        
        import pickle
        with open(cache_file, 'rb') as f:
            entry = pickle.load(f)
        
        # Modify version to simulate old cache
        entry.version = "v2024-01-01"
        
        with open(cache_file, 'wb') as f:
            pickle.dump(entry, f)
        
        # Attempt to retrieve - should invalidate due to version mismatch
        result = cache_manager.get_cache(cache_type, key)
        assert result is None
        
        # Cache file should be removed
        assert not cache_file.exists()
    
    def test_cache_size_calculation(self, cache_manager):
        """Test cache size information calculation"""
        # Set some cache data
        for i in range(3):
            cache_manager.set_cache("test_cache", f"key_{i}", {"data": "x" * 100})
            cache_manager.set_cache("models", f"model_{i}", {"data": "x" * 1000}, cache_level="global")
        
        size_info = cache_manager.get_cache_size_info()
        
        assert "global_cache_mb" in size_info
        assert "project_cache_mb" in size_info
        assert "total_cache_mb" in size_info
        assert "estimated_savings_mb" in size_info
        
        # Size may be 0 due to small test data, but structure should be valid
        assert size_info["global_cache_mb"] >= 0
        assert size_info["project_cache_mb"] >= 0
        assert size_info["total_cache_mb"] >= 0
    
    def test_cache_optimization(self, cache_manager):
        """Test cache optimization functionality"""
        cache_type = "test_cache"
        
        # Create some cache entries with old timestamps
        for i in range(5):
            cache_manager.set_cache(cache_type, f"key_{i}", {"data": i})
        
        # Manually modify timestamps to simulate old entries
        cache_path = cache_manager.get_cache_path(cache_type)
        old_time = time.time() - (31 * 24 * 60 * 60)  # 31 days ago
        
        import pickle
        for cache_file in cache_path.glob("*.cache"):
            with open(cache_file, 'rb') as f:
                entry = pickle.load(f)
            
            entry.last_accessed = old_time
            entry.hit_count = 1  # Low hit count
            
            with open(cache_file, 'wb') as f:
                pickle.dump(entry, f)
        
        # Count files before optimization
        files_before = len(list(cache_path.glob("*.cache")))
        
        # Run optimization
        cache_manager.optimize_cache()
        
        # Count files after optimization (should be fewer)
        files_after = len(list(cache_path.glob("*.cache")))
        assert files_after < files_before
    
    def test_threading_safety(self, cache_manager):
        """Test cache operations are thread-safe"""
        import threading
        import time
        
        cache_type = "test_cache"
        results = []
        errors = []
        
        def cache_worker(worker_id):
            try:
                for i in range(10):
                    key = f"worker_{worker_id}_key_{i}"
                    data = {"worker": worker_id, "iteration": i}
                    
                    # Set cache
                    success = cache_manager.set_cache(cache_type, key, data)
                    results.append(("set", success))
                    
                    # Get cache
                    retrieved = cache_manager.get_cache(cache_type, key)
                    results.append(("get", retrieved == data))
                    
                    time.sleep(0.001)  # Small delay
            except Exception as e:
                errors.append(e)
        
        # Start multiple threads
        threads = []
        for i in range(3):
            thread = threading.Thread(target=cache_worker, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Wait for completion
        for thread in threads:
            thread.join()
        
        # Verify no errors occurred
        assert len(errors) == 0, f"Threading errors: {errors}"
        
        # Verify all operations succeeded
        set_results = [r[1] for r in results if r[0] == "set"]
        get_results = [r[1] for r in results if r[0] == "get"]
        
        assert all(set_results), "Some cache set operations failed"
        assert all(get_results), "Some cache get operations failed"


class TestCacheEntry:
    """Test cache entry data structure"""
    
    def test_cache_entry_creation(self):
        """Test cache entry creation"""
        data = {"test": "data"}
        content_hash = "abc123"
        
        entry = CacheEntry(
            version=CACHE_VERSION,
            timestamp=time.time(),
            content_hash=content_hash,
            data=data
        )
        
        assert entry.version == CACHE_VERSION
        assert entry.content_hash == content_hash
        assert entry.data == data
        assert entry.hit_count == 0
        assert entry.last_accessed == 0


class TestCacheManifest:
    """Test cache manifest functionality"""
    
    def test_manifest_creation(self):
        """Test cache manifest creation"""
        manifest = CacheManifest(
            project_id="test-project",
            cache_version=CACHE_VERSION,
            created_at="2025-07-01T00:00:00",
            last_updated="2025-07-01T00:00:00",
            cache_stats={"entries": 0, "size_bytes": 0},
            invalidation_triggers=[]
        )
        
        assert manifest.project_id == "test-project"
        assert manifest.cache_version == CACHE_VERSION
        assert manifest.cache_stats["entries"] == 0


if __name__ == "__main__":
    pytest.main([__file__])