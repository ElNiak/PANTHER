#!/usr/bin/env python3
"""Test the fixed cache manager."""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'mcp-atlas-commands', 'src'))

from atlas_commands.caching.cache_manager import CacheManager

def test_cache_manager():
    """Test that the cache manager works without parameter conflicts."""
    cache = CacheManager()
    
    # Test basic set/get
    cache.set("test", "key1", "value1")
    result = cache.get("test", "key1")
    print(f"Basic test: {result}")
    
    # Test with kwargs (this was causing the error)
    cache.set("test", "key2", "value2", l1_ttl=300, l2_ttl=1800, project_name="ATLAS", task_id="test-task")
    result = cache.get("test", "key2", project_name="ATLAS", task_id="test-task")
    print(f"Kwargs test: {result}")
    
    print("Cache manager test successful!")

if __name__ == "__main__":
    test_cache_manager()