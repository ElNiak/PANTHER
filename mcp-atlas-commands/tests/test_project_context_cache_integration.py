"""
Integration tests for Project Context Manager with Hierarchical Cache
Tests the integration between project management and cache operations
"""

import os
import tempfile
import shutil
import pytest
from pathlib import Path
from unittest.mock import patch

from src.atlas_commands.project.context_manager import ProjectContextManager
from src.atlas_commands.caching.hierarchical_cache_manager import HierarchicalCacheManager


class TestProjectContextCacheIntegration:
    """Test integration between project context and hierarchical cache"""
    
    @pytest.fixture
    def temp_dirs(self):
        """Create temporary directories for testing"""
        temp_dir = tempfile.mkdtemp()
        project_root = Path(temp_dir) / "project"
        cache_root = Path(temp_dir) / "cache"
        atlas_root = Path(temp_dir) / ".atlas"
        
        project_root.mkdir(parents=True, exist_ok=True)
        cache_root.mkdir(parents=True, exist_ok=True)
        atlas_root.mkdir(parents=True, exist_ok=True)
        
        yield {
            "temp_dir": temp_dir,
            "project_root": project_root,
            "cache_root": cache_root,
            "atlas_root": atlas_root
        }
        
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def context_manager(self, temp_dirs):
        """Create project context manager with hierarchical cache"""
        with patch.dict(os.environ, {
            'ATLAS_PROJECT_ID': 'test-project',
            'ATLAS_PROJECT_ROOT': str(temp_dirs["project_root"]),
            'ATLAS_CACHE_ROOT': str(temp_dirs["cache_root"]),
            'ATLAS_WORKSPACE_ISOLATION': 'true'
        }):
            with patch.object(Path, 'home', return_value=temp_dirs["atlas_root"].parent):
                manager = ProjectContextManager()
                return manager
    
    def test_cache_manager_initialization(self, context_manager):
        """Test hierarchical cache manager is initialized correctly"""
        assert context_manager.cache_manager is not None
        assert isinstance(context_manager.cache_manager, HierarchicalCacheManager)
        assert context_manager.cache_manager.project_id == "test-project"
    
    def test_cache_path_integration(self, context_manager):
        """Test cache path resolution uses hierarchical cache"""
        cache_type = "symbols"
        
        # Get cache path through context manager
        cache_path = context_manager.get_cache_path(cache_type)
        
        # Should use hierarchical cache manager
        if context_manager.cache_manager:
            expected_path = context_manager.cache_manager.get_cache_path(cache_type)
            assert cache_path == expected_path
        
        # Path should be project-specific
        assert "test-project" in str(cache_path) or context_manager.project_fingerprint in str(cache_path)
    
    def test_cache_data_operations(self, context_manager):
        """Test data caching through context manager"""
        cache_type = "test_symbols"
        key = "python_main"
        test_data = {
            "symbols": [
                {"name": "main", "type": "function", "line": 10},
                {"name": "helper", "type": "function", "line": 20}
            ],
            "language": "python",
            "file_hash": "abc123"
        }
        
        # Cache data
        success = context_manager.cache_data(cache_type, key, test_data)
        assert success
        
        # Retrieve data
        retrieved = context_manager.get_cached_data(cache_type, key)
        assert retrieved == test_data
        
        # Test with global cache level
        global_key = "shared_model"
        global_data = {"model": "sentence-transformer", "size_mb": 178}
        
        success = context_manager.cache_data("models", global_key, global_data, cache_level="global")
        assert success
        
        retrieved_global = context_manager.get_cached_data("models", global_key, cache_level="global")
        assert retrieved_global == global_data
    
    def test_cache_invalidation_integration(self, context_manager):
        """Test cache invalidation through context manager"""
        cache_type = "analysis"
        key1 = "complexity_report"
        key2 = "security_scan"
        
        data1 = {"complexity": 5.2, "functions": 12}
        data2 = {"vulnerabilities": 0, "warnings": 3}
        
        # Cache data
        context_manager.cache_data(cache_type, key1, data1)
        context_manager.cache_data(cache_type, key2, data2)
        
        # Verify both cached
        assert context_manager.get_cached_data(cache_type, key1) == data1
        assert context_manager.get_cached_data(cache_type, key2) == data2
        
        # Invalidate specific key
        context_manager.invalidate_cache(cache_type, key1)
        assert context_manager.get_cached_data(cache_type, key1) is None
        assert context_manager.get_cached_data(cache_type, key2) == data2
        
        # Invalidate entire cache type
        context_manager.invalidate_cache(cache_type)
        assert context_manager.get_cached_data(cache_type, key2) is None
    
    def test_performance_stats_integration(self, context_manager):
        """Test performance statistics through context manager"""
        # Perform some cache operations
        for i in range(5):
            context_manager.cache_data("test", f"key_{i}", {"value": i})
            context_manager.get_cached_data("test", f"key_{i}")
        
        # Get performance stats
        stats = context_manager.get_cache_performance_stats()
        
        assert "project_id" in stats
        assert stats["project_id"] == "test-project"
        assert "hit_rate_percent" in stats
        assert stats["hits"] > 0
    
    def test_cache_optimization_integration(self, context_manager):
        """Test cache optimization through context manager"""
        # Cache some data
        for i in range(10):
            context_manager.cache_data("temp", f"key_{i}", {"temp": i})
        
        # Run optimization
        context_manager.optimize_cache()
        
        # Should complete without errors
        assert True
    
    def test_project_isolation(self, temp_dirs):
        """Test that different projects have isolated caches"""
        with patch.object(Path, 'home', return_value=temp_dirs["atlas_root"].parent):
            # Create two project context managers
            with patch.dict(os.environ, {
                'ATLAS_PROJECT_ID': 'project-a',
                'ATLAS_PROJECT_ROOT': str(temp_dirs["project_root"]),
                'ATLAS_CACHE_ROOT': str(temp_dirs["cache_root"]),
                'ATLAS_WORKSPACE_ISOLATION': 'true'
            }):
                manager_a = ProjectContextManager()
            
            with patch.dict(os.environ, {
                'ATLAS_PROJECT_ID': 'project-b',
                'ATLAS_PROJECT_ROOT': str(temp_dirs["project_root"]),
                'ATLAS_CACHE_ROOT': str(temp_dirs["cache_root"]),
                'ATLAS_WORKSPACE_ISOLATION': 'true'
            }):
                manager_b = ProjectContextManager()
        
        # Cache data in project A
        cache_type = "symbols"
        key = "shared_key"
        data_a = {"project": "a", "data": "project-a-specific"}
        data_b = {"project": "b", "data": "project-b-specific"}
        
        manager_a.cache_data(cache_type, key, data_a)
        manager_b.cache_data(cache_type, key, data_b)
        
        # Verify isolation - each project gets its own data
        retrieved_a = manager_a.get_cached_data(cache_type, key)
        retrieved_b = manager_b.get_cached_data(cache_type, key)
        
        assert retrieved_a == data_a
        assert retrieved_b == data_b
        assert retrieved_a != retrieved_b
    
    def test_ml_model_sharing(self, temp_dirs):
        """Test ML models are shared globally between projects"""
        with patch.object(Path, 'home', return_value=temp_dirs["atlas_root"].parent):
            # Create two project context managers
            with patch.dict(os.environ, {
                'ATLAS_PROJECT_ID': 'project-a',
                'ATLAS_PROJECT_ROOT': str(temp_dirs["project_root"]),
                'ATLAS_CACHE_ROOT': str(temp_dirs["cache_root"]),
                'ATLAS_WORKSPACE_ISOLATION': 'true'
            }):
                manager_a = ProjectContextManager()
            
            with patch.dict(os.environ, {
                'ATLAS_PROJECT_ID': 'project-b',
                'ATLAS_PROJECT_ROOT': str(temp_dirs["project_root"]),
                'ATLAS_CACHE_ROOT': str(temp_dirs["cache_root"]),
                'ATLAS_WORKSPACE_ISOLATION': 'true'
            }):
                manager_b = ProjectContextManager()
        
        # Cache ML model globally from project A
        model_key = "sentence-transformer"
        model_data = {"model_path": "/models/all-MiniLM-L6-v2", "size_mb": 178}
        
        manager_a.cache_data("models", model_key, model_data, cache_level="global")
        
        # Project B should be able to access the same model
        retrieved_by_b = manager_b.get_cached_data("models", model_key, cache_level="global")
        assert retrieved_by_b == model_data
        
        # Both projects should report the same global cache path
        path_a = manager_a.get_cache_path("models", "global")
        path_b = manager_b.get_cache_path("models", "global")
        assert path_a == path_b
    
    def test_fallback_to_legacy_cache(self, temp_dirs):
        """Test fallback when hierarchical cache is not available"""
        with patch.object(Path, 'home', return_value=temp_dirs["atlas_root"].parent):
            with patch.dict(os.environ, {
                'ATLAS_PROJECT_ID': 'test-project',
                'ATLAS_PROJECT_ROOT': str(temp_dirs["project_root"]),
                'ATLAS_CACHE_ROOT': str(temp_dirs["cache_root"]),
                'ATLAS_WORKSPACE_ISOLATION': 'true'
            }):
                # Create manager and manually disable hierarchical cache
                manager = ProjectContextManager()
                manager.cache_manager = None  # Simulate cache manager not available
        
        # Should still work with fallback
        cache_type = "symbols"
        key = "test_key"
        data = {"fallback": True}
        
        success = manager.cache_data(cache_type, key, data)
        assert success
        
        retrieved = manager.get_cached_data(cache_type, key)
        assert retrieved == data
        
        # Performance stats should indicate legacy mode
        stats = manager.get_cache_performance_stats()
        assert stats["cache_manager"] == "legacy"
    
    def test_content_hash_cache_invalidation(self, context_manager):
        """Test content-hash based cache invalidation"""
        cache_type = "symbols"
        key = "file_symbols"
        
        # Original content
        original_data = {"symbols": ["func1", "func2"], "file_hash": "abc123"}
        context_manager.cache_data(cache_type, key, original_data, content_hash="abc123")
        
        # Retrieve original
        retrieved = context_manager.get_cached_data(cache_type, key)
        assert retrieved == original_data
        
        # Updated content with new hash
        updated_data = {"symbols": ["func1", "func2", "func3"], "file_hash": "def456"}
        context_manager.cache_data(cache_type, key, updated_data, content_hash="def456")
        
        # Should get updated content
        retrieved_updated = context_manager.get_cached_data(cache_type, key)
        assert retrieved_updated == updated_data
        assert retrieved_updated != original_data


if __name__ == "__main__":
    pytest.main([__file__])