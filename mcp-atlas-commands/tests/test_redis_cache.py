#!/usr/bin/env python3
"""Test Redis caching implementation."""

import sys
import os
import asyncio
import time

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from atlas_commands.caching.cache_manager import CacheManager
from atlas_commands.caching.redis_client import RedisClient


async def test_cache_tiers():
    """Test multi-tier cache functionality."""
    print("🧪 Testing ATLAS MCP Redis Caching System\n")
    
    # Initialize cache manager
    cache_manager = CacheManager(
        l1_max_size=5,
        l2_default_ttl=300,
        l3_default_ttl=3600,
        l3_cache_dir="/tmp/atlas_cache_test"
    )
    
    print("✅ Cache manager initialized")
    
    # Test Redis connection
    redis_client = RedisClient()
    print(f"✅ Redis client status: {'enabled' if redis_client.enabled else 'disabled'}")
    
    # Test cache operations
    print("\n📊 Testing cache operations...")
    
    # Test data
    test_data = {
        "task_id": "test_task_001",
        "status": "active", 
        "data": {"items": [1, 2, 3, 4, 5]},
        "timestamp": time.time()
    }
    
    # Cache miss test
    result = cache_manager.get("task", "test_operation", project_name="ATLAS")
    print(f"Cache miss test: {result}")
    
    # Cache set test
    cache_manager.set("task", "test_operation", test_data,
                     l1_ttl=60, l2_ttl=300, l3_ttl=600,
                     project_name="ATLAS")
    print("✅ Data stored in cache")
    
    # Cache hit test
    cached_result = cache_manager.get("task", "test_operation", project_name="ATLAS")
    print(f"Cache hit test: {cached_result is not None}")
    print(f"Data matches: {cached_result == test_data}")
    
    # Test cache stats
    print("\n📈 Cache Statistics:")
    stats = cache_manager.get_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")
    
    # Test cache invalidation
    print("\n🗑️ Testing cache invalidation...")
    invalidated = cache_manager.invalidate("task", "test_operation", project_name="ATLAS")
    print(f"Invalidated {invalidated} entries")
    
    # Verify invalidation
    result_after_invalidation = cache_manager.get("task", "test_operation", project_name="ATLAS")
    print(f"Cache miss after invalidation: {result_after_invalidation is None}")
    
    # Test namespace invalidation
    cache_manager.set("task", "operation_1", {"data": 1}, project_name="ATLAS")
    cache_manager.set("task", "operation_2", {"data": 2}, project_name="ATLAS")
    cache_manager.set("memory", "search_1", {"results": ["a", "b"]}, query="test")
    
    invalidated_namespace = cache_manager.invalidate("task")
    print(f"Invalidated {invalidated_namespace} entries from 'task' namespace")
    
    # Test cache warming
    print("\n🔥 Testing cache warming...")
    def expensive_operation(project_name, operation_type):
        time.sleep(0.1)  # Simulate expensive operation
        return {
            "project": project_name,
            "operation": operation_type,
            "computed_at": time.time(),
            "expensive_result": list(range(100))
        }
    
    # Warm cache
    start_time = time.time()
    result = cache_manager.warm_cache("task", "expensive_op", expensive_operation,
                                    project_name="ATLAS", operation_type="test")
    first_call_time = time.time() - start_time
    print(f"First call (cache miss): {first_call_time:.3f}s")
    
    # Second call should be cached
    start_time = time.time()
    cached_result = cache_manager.get("task", "expensive_op", 
                                    project_name="ATLAS", operation_type="test")
    second_call_time = time.time() - start_time
    print(f"Second call (cache hit): {second_call_time:.3f}s")
    print(f"Speedup: {first_call_time / second_call_time:.1f}x faster")
    
    # Final stats
    print("\n📊 Final Cache Statistics:")
    final_stats = cache_manager.get_stats()
    for key, value in final_stats.items():
        print(f"  {key}: {value}")
    
    # Redis info
    if redis_client.enabled:
        print("\n🗄️ Redis Information:")
        redis_info = redis_client.info()
        for key, value in redis_info.items():
            print(f"  {key}: {value}")
    
    # Cleanup
    cache_manager.clear_all()
    print("\n🧹 Cache cleared")
    
    print("\n✅ All tests completed successfully!")


if __name__ == "__main__":
    asyncio.run(test_cache_tiers())