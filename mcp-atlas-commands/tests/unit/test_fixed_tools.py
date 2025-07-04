#!/usr/bin/env python3
"""
Test ATLAS tools after configuration fix
"""

import json
import subprocess

def test_task_management_fix():
    """Test if task management tools now work with config fix"""
    
    test_tools = [
        {"name": "create_task_metadata", "args": {"project_name": "TEST", "task_id": "test1", "task_type": "test", "description": "test"}},
        {"name": "list_project_tasks", "args": {"project_name": "TEST"}},
        {"name": "get_task_context", "args": {"project_name": "TEST", "task_id": "test1"}},
    ]
    
    print("Testing Task Management Tools After Config Fix")
    print("=" * 60)
    
    success_count = 0
    
    for tool_test in test_tools:
        tool_name = tool_test["name"]
        arguments = tool_test["args"]
        
        print(f"Testing {tool_name}...", end="")
        
        messages = [
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "clientInfo": {"name": "atlas-fix-test", "version": "1.0.0"}
                }
            },
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {"name": tool_name, "arguments": arguments}
            }
        ]
        
        input_data = ""
        for msg in messages:
            input_data += json.dumps(msg) + "\n"
        
        try:
            result = subprocess.run(
                ["docker", "run", "--rm", "-i", "-e", "ATLAS_ENABLE_TOOL_REGISTRY=true", "atlas-commands-mcp:latest"],
                input=input_data,
                text=True,
                capture_output=True,
                timeout=10
            )
            
            if result.stdout:
                responses = result.stdout.strip().split('\n')
                for response_line in responses:
                    if response_line.strip():
                        try:
                            response = json.loads(response_line)
                            if response.get('id') == 2:  # Tool call response
                                if 'result' in response:
                                    content = response['result'].get('content', [])
                                    if content and isinstance(content[0], dict):
                                        text = content[0].get('text', '')
                                        
                                        # Check if config error is gone
                                        if "'config'" in text and "has no attribute" in text:
                                            print(f" ✗ Still has config error")
                                        elif "error" in text.lower() or "exception" in text.lower():
                                            print(f" ⚠️  Different error: {text[:60]}...")
                                        else:
                                            print(f" ✓ Working!")
                                            success_count += 1
                                    else:
                                        print(f" ✓ Working!")
                                        success_count += 1
                                elif 'error' in response:
                                    print(f" ✗ JSON-RPC error: {response['error'].get('message', 'Unknown')}")
                                break
                        except json.JSONDecodeError:
                            continue
                else:
                    print(f" ✗ No valid response")
            else:
                print(f" ✗ No output")
                
        except Exception as e:
            print(f" ✗ {str(e)}")
    
    print(f"\nResults: {success_count}/{len(test_tools)} task management tools working")
    
    if success_count == len(test_tools):
        print("🎉 Configuration fix successful!")
        return True
    elif success_count > 0:
        print("⚠️ Partial improvement - some tools still need work")
        return False
    else:
        print("❌ Configuration fix didn't resolve the issues")
        return False

if __name__ == "__main__":
    success = test_task_management_fix()
    exit(0 if success else 1)