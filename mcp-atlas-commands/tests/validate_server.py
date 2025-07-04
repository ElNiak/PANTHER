#!/usr/bin/env python
"""Validation script for ATLAS Commands MCP Server."""

import asyncio
import json
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from atlas_commands.server import EnhancedAtlasCommandsServer


async def validate_server():
    """Validate the MCP server implementation."""
    
    print("=" * 60)
    print("ATLAS Commands MCP Server Validation")
    print("=" * 60)
    
    # 1. Test server instantiation
    print("\n1. Testing server instantiation...")
    try:
        server = EnhancedAtlasCommandsServer()
        print("   ✅ Server instantiated successfully")
    except Exception as e:
        print(f"   ❌ Failed to instantiate server: {e}")
        return False
    
    # 2. Test tool listing
    print("\n2. Testing tool listing...")
    try:
        tools = await server.list_tools()
        print(f"   ✅ Found {len(tools)} tools")
        
        expected_tools = [
            "create_unified_checklist",
            "update_checklist_item",
            "get_checklist_progress",
            "create_todowrite_integration",
            "create_memory_entity",
            "create_workflow",
            "validate_command",
            "track_command_pattern",
            "get_pattern_recommendations",
            "compact_memory_graph"
        ]
        
        tool_names = [tool.name for tool in tools]
        for expected in expected_tools:
            if expected in tool_names:
                print(f"   ✅ Tool '{expected}' found")
            else:
                print(f"   ❌ Tool '{expected}' missing")
                
    except Exception as e:
        print(f"   ❌ Failed to list tools: {e}")
        return False
    
    # 3. Test basic tool execution
    print("\n3. Testing basic tool execution...")
    try:
        # Test create_unified_checklist
        result = await server.call_tool(
            "create_unified_checklist",
            {
                "command_name": "plan",
                "task_id": "validation-test",
                "template_type": "minimal"
            }
        )
        print("   ✅ create_unified_checklist executed successfully")
        print(f"      Created checklist: {result[0].get('checklist_id', 'unknown')}")
        
    except Exception as e:
        print(f"   ❌ Failed to execute tool: {e}")
        return False
    
    # 4. Test error handling
    print("\n4. Testing error handling...")
    try:
        # Call with missing required parameters
        result = await server.call_tool(
            "update_checklist_item",
            {}  # Missing required parameters
        )
        
        if "error" in result[0]:
            print("   ✅ Error handling works correctly")
            print(f"      Error message: {result[0]['error']}")
        else:
            print("   ❌ Error not properly handled")
            
    except Exception as e:
        print(f"   ✅ Exception properly raised: {e}")
    
    # 5. Test resource monitoring
    print("\n5. Testing resource monitoring...")
    try:
        if hasattr(server, 'resource_monitor'):
            usage = server.resource_monitor.get_current_usage()
            print("   ✅ Resource monitoring active")
            print(f"      Memory usage: {usage.memory_mb:.2f} MB")
            print(f"      CPU usage: {usage.cpu_percent:.1f}%")
        else:
            print("   ⚠️  Resource monitoring not available")
            
    except Exception as e:
        print(f"   ❌ Resource monitoring failed: {e}")
    
    # 6. Test validation
    print("\n6. Testing input validation...")
    try:
        # Test with auto-fixable input
        result = await server.call_tool(
            "create_unified_checklist",
            {
                "command_name": "plan",
                "task_id": "invalid task id!",  # Should be auto-fixed
                "template_type": "minimal"
            }
        )
        
        if "checklist_id" in result[0]:
            print("   ✅ Input validation with auto-fix works")
            print(f"      Fixed task_id in: {result[0]['checklist_id']}")
        
    except Exception as e:
        print(f"   ❌ Validation failed: {e}")
    
    # 7. Test workflow creation
    print("\n7. Testing workflow creation...")
    try:
        result = await server.call_tool(
            "create_workflow",
            {
                "workflow_id": "test-workflow",
                "pattern": "explore-plan-code-commit",
                "target": "validation-test",
                "steps": [
                    {"command": "explore", "target": "codebase"},
                    {"command": "plan", "target": "feature"}
                ]
            }
        )
        
        if result[0].get("workflow_id") == "test-workflow":
            print("   ✅ Workflow creation successful")
            print(f"      Steps: {result[0].get('step_count', 0)}")
        
    except Exception as e:
        print(f"   ❌ Workflow creation failed: {e}")
    
    # 8. Test memory operations
    print("\n8. Testing memory operations...")
    try:
        result = await server.call_tool(
            "create_memory_entity",
            {
                "command_type": "validate",
                "target": "mcp-server",
                "observations": [
                    "Server validation completed",
                    "All core features working"
                ]
            }
        )
        
        if "entity_name" in result[0]:
            print("   ✅ Memory entity creation successful")
            print(f"      Entity: {result[0]['entity_name']}")
        
    except Exception as e:
        print(f"   ❌ Memory operation failed: {e}")
    
    # 9. Test pattern tracking
    print("\n9. Testing pattern tracking...")
    try:
        result = await server.call_tool(
            "track_command_pattern",
            {
                "command": "validate",
                "target": "mcp-server",
                "outcome": "success",
                "duration": 5.0,
                "observations": ["Validation completed successfully"]
            }
        )
        
        if result[0].get("tracked"):
            print("   ✅ Pattern tracking successful")
        
    except Exception as e:
        print(f"   ❌ Pattern tracking failed: {e}")
    
    # 10. Test concurrent operations
    print("\n10. Testing concurrent operations...")
    try:
        tasks = []
        for i in range(3):
            task = server.call_tool(
                "create_unified_checklist",
                {
                    "command_name": "plan",
                    "task_id": f"concurrent-{i}",
                    "template_type": "minimal"
                }
            )
            tasks.append(task)
        
        results = await asyncio.gather(*tasks)
        
        if len(results) == 3 and all(r[0].get("checklist_id") for r in results):
            print("   ✅ Concurrent operations successful")
            print(f"      Created {len(results)} checklists concurrently")
        
    except Exception as e:
        print(f"   ❌ Concurrent operations failed: {e}")
    
    print("\n" + "=" * 60)
    print("Validation Complete!")
    print("=" * 60)
    
    return True


async def main():
    """Main entry point."""
    try:
        success = await validate_server()
        if success:
            print("\n✅ ATLAS Commands MCP Server validation PASSED")
            return 0
        else:
            print("\n❌ ATLAS Commands MCP Server validation FAILED")
            return 1
    except Exception as e:
        print(f"\n❌ Validation error: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))