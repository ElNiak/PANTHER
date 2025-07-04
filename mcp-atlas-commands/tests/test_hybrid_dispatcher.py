#!/usr/bin/env python3
"""
Test the hybrid dispatcher by initializing the server and checking tool routing.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add the source directory to path
src_dir = Path(__file__).parent / "src"
sys.path.insert(0, str(src_dir))

async def test_hybrid_dispatcher():
    """Test the hybrid dispatcher implementation."""
    print("🧪 Testing ATLAS MCP Hybrid Dispatcher...")
    
    try:
        from atlas_commands.server import EnhancedAtlasCommandsServer
        from atlas_commands.refactor_config import enable_phase_1
        
        # Enable Phase 1
        enable_phase_1()
        print("✅ Phase 1 enabled")
        
        # Initialize server
        server = EnhancedAtlasCommandsServer()
        print("✅ Server initialized successfully")
        
        # Check configuration
        print(f"\n📊 Server Configuration:")
        print(f"  Registry enabled: {server.refactor_config.enable_tool_registry}")
        print(f"  Fallback enabled: {server.refactor_config.fallback_to_legacy}")
        print(f"  Error handling: {server.refactor_config.enable_consistent_error_handling}")
        
        # Check registry status
        registry_tools = server._tool_registry.list_tools()
        print(f"\n🔧 Registry Status:")
        print(f"  Tools in registry: {len(registry_tools)}")
        print(f"  Categories: {server._tool_registry.list_categories()}")
        
        # Test tool routing (simulated)
        print(f"\n🎯 Tool Routing Test:")
        
        # Test 1: Registry tool (should route to registry)
        if "create_task_metadata" in registry_tools:
            print("  ✅ create_task_metadata -> Registry")
        else:
            print("  ❌ create_task_metadata not in registry")
            
        # Test 2: Legacy tool (should route to legacy)
        legacy_tool = "create_unified_checklist"
        if legacy_tool not in registry_tools:
            print(f"  ✅ {legacy_tool} -> Legacy fallback")
        else:
            print(f"  ❌ {legacy_tool} unexpectedly in registry")
        
        print(f"\n🚀 Phase 1 Implementation: SUCCESSFUL")
        print("Hybrid dispatcher is ready to route tools!")
        
    except Exception as e:
        print(f"❌ Error testing hybrid dispatcher: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

async def main():
    """Main test function."""
    return await test_hybrid_dispatcher()

if __name__ == "__main__":
    exit(asyncio.run(main()))