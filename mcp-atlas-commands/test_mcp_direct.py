#!/usr/bin/env python3
"""Direct test of MCP atlas-commands server without Docker."""

import json
import asyncio
import sys
import os

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from atlas_commands.server import EnhancedAtlasCommandsServer

async def test_mcp_direct():
    """Test MCP server directly."""
    print("🧪 Testing MCP Server Directly with Redis\n")
    
    # Set environment variables for Redis
    os.environ['REDIS_URL'] = 'redis://localhost:6379/0'
    os.environ['ATLAS_STORAGE_PATH'] = '/Users/elniak/Documents/Project/Software-Engineer-AI-Agent-Atlas/REPOS'
    os.environ['PROJECT_NAME'] = 'ATLAS_REDIS_TEST'
    os.environ['ATLAS_MEMORY_CONTROL_PATH'] = '/tmp/atlas-memory-control'
    
    # Initialize server
    server_instance = EnhancedAtlasCommandsServer()
    
    # Test cache stats
    print("Testing get_cache_stats...")
    try:
        result = await server_instance.cache_handler.handle("get_cache_stats", {})
        print(f"✅ get_cache_stats result: {result[0].text}")
    except Exception as e:
        print(f"❌ get_cache_stats error: {e}")
    
    # Test cache warming
    print("\nTesting warm_cache...")
    try:
        result = await server_instance.cache_handler.handle("warm_cache", {"cache_type": "test"})
        print(f"✅ warm_cache result: {result[0].text}")
    except Exception as e:
        print(f"❌ warm_cache error: {e}")
    
    # Test invalidate cache
    print("\nTesting invalidate_cache...")
    try:
        result = await server_instance.cache_handler.handle("invalidate_cache", {"cache_key": "test_key"})
        print(f"✅ invalidate_cache result: {result[0].text}")
    except Exception as e:
        print(f"❌ invalidate_cache error: {e}")
    
    # Test clear all cache
    print("\nTesting clear_all_cache...")
    try:
        result = await server_instance.cache_handler.handle("clear_all_cache", {})
        print(f"✅ clear_all_cache result: {result[0].text}")
    except Exception as e:
        print(f"❌ clear_all_cache error: {e}")
    
    print("\n✅ Direct MCP Redis tests completed!")

if __name__ == "__main__":
    asyncio.run(test_mcp_direct())