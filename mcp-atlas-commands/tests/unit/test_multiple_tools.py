#\!/usr/bin/env python3
"""Test multiple Atlas MCP tools to confirm coroutine issue is resolved."""

import json
import subprocess

def test_multiple_tools():
    """Test several tools to confirm all async/await issues are resolved."""
    
    # Initialize properly
    init_request = {
        "jsonrpc": "2.0",
        "id": 0,
        "method": "initialize",
        "params": {
            "protocolVersion": "2025-06-18",
            "capabilities": {},
            "clientInfo": {"name": "atlas-test", "version": "1.0.0"}
        }
    }
    
    initialized_notification = {
        "jsonrpc": "2.0",
        "method": "notifications/initialized",
        "params": {}
    }
    
    # Test multiple tools that were previously problematic
    test_tools = [
        {
            "id": 1,
            "name": "get_task_context",
            "arguments": {"project_name": "test", "task_id": "test-001"}
        },
        {
            "id": 2,
            "name": "list_project_tasks",
            "arguments": {"project_name": "test"}
        },
        {
            "id": 3,
            "name": "test_simple_tool",
            "arguments": {"test": "value"}
        },
        {
            "id": 4,
            "name": "get_observability_status",
            "arguments": {}
        },
        {
            "id": 5,
            "name": "get_cache_stats",
            "arguments": {}
        }
    ]
    
    # Build requests
    requests = [json.dumps(init_request), json.dumps(initialized_notification)]
    for tool in test_tools:
        request = {
            "jsonrpc": "2.0",
            "id": tool["id"],
            "method": "tools/call",
            "params": {
                "name": tool["name"],
                "arguments": tool["arguments"]
            }
        }
        requests.append(json.dumps(request))
    
    combined_input = '\n'.join(requests) + '\n'
    
    print("Testing multiple tools to confirm coroutine fix...")
    
    cmd = [
        'docker', 'run', '--rm', '-i',
        '-e', 'ATLAS_ENABLE_TOOL_REGISTRY=true',
        'atlas-commands-mcp:latest'
    ]
    
    try:
        process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        stdout, stderr = process.communicate(input=combined_input, timeout=30)
        
        # Parse responses
        if stdout.strip():
            lines = stdout.strip().split('\n')
            results = []
            
            for line in lines:
                try:
                    response = json.loads(line)
                    if 'id' in response and response['id'] > 0:  # Skip init response
                        results.append(response)
                except json.JSONDecodeError:
                    continue
            
            print(f"\n🎯 Tested {len(results)} tools:")
            success_count = 0
            
            for i, result in enumerate(results):
                tool_name = test_tools[i]["name"] if i < len(test_tools) else "unknown"
                
                if 'error' in result:
                    error_msg = result['error'].get('message', 'Unknown error')
                    print(f"❌ {tool_name}: {error_msg}")
                    if 'coroutine' in error_msg.lower():
                        print(f"   🔥 COROUTINE ERROR DETECTED\!")
                elif 'result' in result:
                    print(f"✅ {tool_name}: Success")
                    success_count += 1
                else:
                    print(f"⚠️  {tool_name}: Unexpected response format")
            
            print(f"\n📊 Results: {success_count}/{len(results)} tools successful")
            
            if success_count == len(results):
                print("🎉 ALL TOOLS WORKING - COROUTINE ISSUE COMPLETELY RESOLVED\!")
            else:
                print("⚠️  Some tools still have issues")
                
        return process.returncode
        
    except subprocess.TimeoutExpired:
        print("❌ Test timed out")
        process.kill()
        return 1
    except Exception as e:
        print(f"❌ Test error: {e}")
        return 1

if __name__ == "__main__":
    exit_code = test_multiple_tools()
    exit(exit_code)
