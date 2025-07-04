#!/usr/bin/env python3
"""
Enable Phase 1 of the ATLAS MCP registry refactor.

This script enables the tool registry with fallback to legacy dispatcher.
"""

import os
import sys
from pathlib import Path

# Add the source directory to path
src_dir = Path(__file__).parent / "src"
sys.path.insert(0, str(src_dir))

from atlas_commands.refactor_config import enable_phase_1, get_config

def main():
    """Enable Phase 1 features and test the configuration."""
    print("🚀 Enabling ATLAS MCP Phase 1...")
    
    # Enable Phase 1 features
    enable_phase_1()
    
    # Get current config
    config = get_config()
    
    print("\n✅ Phase 1 Configuration:")
    print(f"  Tool Registry Enabled: {config.enable_tool_registry}")
    print(f"  Error Handling Enabled: {config.enable_consistent_error_handling}")
    print(f"  Fallback to Legacy: {config.fallback_to_legacy}")
    print(f"  Debug Tool Dispatch: {config.debug_tool_dispatch}")
    print(f"  Log Tool Performance: {config.log_tool_performance}")
    
    print("\n🔧 Phase 1 Features Active:")
    print("  - Tool registry with hybrid dispatcher")
    print("  - Consistent error handling for new tools")
    print("  - Safe fallback to legacy 44-tool if-elif chain")
    print("  - Performance logging and debugging")
    
    print("\n📊 Testing registry infrastructure...")
    
    try:
        from atlas_commands.tool_registry import ToolRegistry
        from atlas_commands.handlers import TaskManagementHandler
        from atlas_commands.storage.task_storage_manager import TaskStorageManager
        
        # Test registry setup
        registry = ToolRegistry()
        storage_manager = TaskStorageManager("/tmp/test")
        
        # Test handler registration
        task_handler = TaskManagementHandler(
            storage_manager=storage_manager,
            memory_manager=None
        )
        registry.register_handler(task_handler)
        
        registered_tools = registry.list_tools()
        categories = registry.list_categories()
        
        print(f"  ✅ Registry initialized successfully")
        print(f"  ✅ Task management handler registered")
        print(f"  ✅ {len(registered_tools)} tools available in registry")
        print(f"  ✅ {len(categories)} categories registered")
        
        print(f"\n📋 Registered Tools:")
        for tool in registered_tools:
            print(f"    - {tool}")
        
        print(f"\n📂 Categories:")
        for category in categories:
            tools_in_category = registry.get_tools_by_category(category)
            print(f"    - {category}: {len(tools_in_category)} tools")
        
    except Exception as e:
        print(f"  ❌ Error testing registry: {e}")
        return 1
    
    print("\n🎯 Phase 1 Status: READY")
    print("The hybrid dispatcher will:")
    print("  1. Try registry for known tools (task management)")
    print("  2. Fallback to legacy for all other tools")
    print("  3. Log performance metrics for analysis")
    
    return 0

if __name__ == "__main__":
    exit(main())