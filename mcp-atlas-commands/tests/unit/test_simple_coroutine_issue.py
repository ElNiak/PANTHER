#!/usr/bin/env python3
"""Simple test to debug the coroutine issue with get_task_context tool."""

import json
import subprocess
import time

def test_get_task_context():
    """Test the get_task_context tool to isolate the coroutine issue."""
    
    # First send initialization request
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
    
    # Send initialized notification (required after initialization)
    initialized_notification = {
        "jsonrpc": "2.0",
        "method": "notifications/initialized",
        "params": {}
    }
    
    # List available tools first
    list_tools_request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/list",
        "params": {}
    }
    
    # Then send the actual tool request
    tool_request = {
        "jsonrpc": "2.0",
        "id": 2,
        "method": "tools/call",
        "params": {
            "name": "get_task_context", 
            "arguments": {
                "project_name": "test-project",
                "task_id": "test-task-001"
            }
        }
    }
    
    print("Testing get_task_context tool with proper initialization...")
    print(f"Init request: {json.dumps(init_request, indent=2)}")
    print(f"Tool request: {json.dumps(tool_request, indent=2)}")
    
    # Run docker command
    cmd = [
        'docker', 'run', '--rm', '-i',
        '-e', 'ATLAS_ENABLE_TOOL_REGISTRY=true',
        'atlas-commands-mcp:latest'
    ]
    
    try:
        # Start the process
        process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Send all requests with proper MCP protocol sequence
        combined_input = (json.dumps(init_request) + '\n' + 
                         json.dumps(initialized_notification) + '\n' + 
                         json.dumps(list_tools_request) + '\n' + 
                         json.dumps(tool_request) + '\n')
        stdout, stderr = process.communicate(input=combined_input, timeout=30)
        
        print("\n=== STDOUT ===")
        print(stdout)
        print("\n=== STDERR ===") 
        print(stderr)
        
        # Try to parse the response
        if stdout.strip():
            lines = stdout.strip().split('\n')
            for line in lines:
                try:
                    response = json.loads(line)
                    if 'jsonrpc' in response:
                        print(f"\n=== JSON-RPC RESPONSE ===")
                        print(json.dumps(response, indent=2))
                        
                        if 'error' in response:
                            error_msg = response['error'].get('message', 'Unknown error')
                            print(f"\n❌ Error: {error_msg}")
                            if 'coroutine' in error_msg.lower():
                                print("🔍 FOUND THE COROUTINE ISSUE!")
                        elif 'result' in response:
                            print(f"\n✅ Success!")
                        break
                except json.JSONDecodeError:
                    continue
        
        return process.returncode
        
    except subprocess.TimeoutExpired:
        print("❌ Test timed out")
        process.kill()
        return 1
    except Exception as e:
        print(f"❌ Test error: {e}")
        return 1

if __name__ == "__main__":
    exit_code = test_get_task_context()
    exit(exit_code)