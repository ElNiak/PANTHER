#!/usr/bin/env python3
"""
Test Phase 0 of ATLAS MCP server refactoring.

This script tests the new configuration system and tool registry
with feature flags disabled (safe operation).
"""

import asyncio
import sys
import os

# Add the src directory to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from atlas_commands.refactor_config import get_config, enable_phase_0
from atlas_commands.tool_registry import ToolRegistry
from atlas_commands.handlers.task_management import TaskManagementHandler


async def test_configuration():
    """Test the configuration system."""
    print("=== Testing Configuration System ===")
    
    config = get_config()
    print(f"Default config - Registry enabled: {config.enable_tool_registry}")
    print(f"Default config - Error handling: {config.enable_consistent_error_handling}")
    print(f"Default config - Fallback: {config.fallback_to_legacy}")
    
    # Enable Phase 0
    enable_phase_0()
    updated_config = get_config()
    print(f"Phase 0 config - Logging: {updated_config.enable_logging_improvements}")
    print(f"Phase 0 config - Debug: {updated_config.debug_tool_dispatch}")
    print("✅ Configuration system working")
    

def test_tool_registry():
    """Test the tool registry system."""
    print("\n=== Testing Tool Registry ===")
    
    registry = ToolRegistry()
    print(f"Empty registry tools: {len(registry.list_tools())}")
    
    # Create a mock task handler (without storage manager for testing)
    class MockTaskHandler(TaskManagementHandler):
        def __init__(self):
            # Skip parent init to avoid needing storage_manager
            from atlas_commands.handlers.base import BaseToolHandler
            BaseToolHandler.__init__(self, storage_manager=None)
    
    handler = MockTaskHandler()
    registry.register_handler(handler)
    
    print(f"Registry with handler tools: {len(registry.list_tools())}")
    print(f"Tool categories: {registry.list_categories()}")
    print(f"Task management tools: {registry.get_tools_by_category('task_management')}")
    
    # Test registry stats
    stats = registry.get_registry_stats()
    print(f"Registry stats: {stats}")
    print("✅ Tool registry working")


async def main():
    """Run all Phase 0 tests."""
    print("Phase 0 Refactoring Tests - ATLAS MCP Server")
    print("=" * 50)
    
    try:
        await test_configuration()
        test_tool_registry()
        
        print("\n🎉 All Phase 0 tests passed!")
        print("Ready to proceed to Phase 1 (registry with fallback)")
        
    except Exception as e:
        print(f"\n❌ Phase 0 tests failed: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)