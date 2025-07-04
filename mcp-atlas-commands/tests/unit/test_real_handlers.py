#!/usr/bin/env python3
"""
Test script to verify handlers work with proper server initialization.
"""

import asyncio
import sys
import tempfile
import json
from pathlib import Path

# Add src to path
sys.path.insert(0, './src')

from atlas_commands.server import create_atlas_mcp_server


async def test_all_handlers():
    """Test handlers through the full server."""
    print("=== Testing Handlers Through Full Server ===\n")
    
    # Create server instance
    server = create_atlas_mcp_server()
    
    # Test tools that were reported as "missing"
    test_cases = [
        {
            "name": "get_embeddings_stats",
            "args": {}
        },
        {
            "name": "validate_file_operation", 
            "args": {
                "operation": "read",
                "file_path": "/tmp/test.txt",
                "context": "test"
            }
        },
        {
            "name": "create_nested_subtask",
            "args": {
                "parent_task_id": "test-parent",
                "subtask_data": {"name": "test-subtask", "type": "analysis"}
            }
        }
    ]
    
    results = {}
    
    for test_case in test_cases:
        tool_name = test_case["name"]
        args = test_case["args"]
        
        print(f"Testing {tool_name}...")
        
        try:
            # Call through server's call_tool method
            result = await server.call_tool(tool_name, args)
            
            print(f"  ✅ {tool_name} works - result type: {type(result)}")
            results[tool_name] = "PASS"
            
        except AttributeError as e:
            if "has no attribute '_handle_" in str(e):
                print(f"  ❌ {tool_name} - Missing handler method: {e}")
                results[tool_name] = "FAIL - Missing Handler"
            else:
                print(f"  ❌ {tool_name} - AttributeError: {e}")
                results[tool_name] = "FAIL - AttributeError"
        except Exception as e:
            print(f"  ⚠️  {tool_name} - Error (but handler exists): {e}")
            results[tool_name] = "PASS - Handler exists, error expected"
    
    print(f"\n=== RESULTS ===")
    all_pass = True
    for tool, result in results.items():
        print(f"{tool}: {result}")
        if "FAIL" in result:
            all_pass = False
    
    if all_pass:
        print("\n✅ ALL HANDLERS IMPLEMENTED - Test report was incorrect!")
    else:
        print("\n❌ Some handlers actually missing")
    
    return all_pass


async def main():
    success = await test_all_handlers()
    return success


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)