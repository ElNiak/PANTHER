#!/usr/bin/env python3
"""
Test ATLAS MCP server using Docker container with JSON-RPC commands.
"""

import json
import subprocess
import time

def test_atlas_server_jsonrpc():
    """Test ATLAS server with JSON-RPC via Docker"""
    print("ATLAS MCP Docker JSON-RPC Test")
    print("="*40)
    
    # Test JSON-RPC messages
    test_messages = [
        # Initialize
        {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}},
                "clientInfo": {"name": "atlas-test", "version": "1.0.0"}
            }
        },
        # Initialized notification
        {
            "jsonrpc": "2.0",
            "method": "notifications/initialized"
        },
        # List tools
        {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
            "params": {}
        },
        # Test a tool call
        {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": "create_task_metadata",
                "arguments": {
                    "project_name": "TEST_PROJECT",
                    "task_id": "test_task_001",
                    "task_type": "testing",
                    "description": "Docker JSON-RPC test task"
                }
            }
        }
    ]
    
    # Prepare input for Docker container
    input_data = ""
    for msg in test_messages:
        input_data += json.dumps(msg) + "\n"
    
    print("Testing ATLAS MCP server via Docker...")
    print("Input messages:")
    for i, msg in enumerate(test_messages, 1):
        method = msg.get("method", "notification")
        print(f"  {i}. {method}")
    
    try:
        # Run Docker container with input
        result = subprocess.run(
            ["docker", "run", "--rm", "-i", "-e", "ATLAS_ENABLE_TOOL_REGISTRY=true", "atlas-commands-mcp:latest"],
            input=input_data,
            text=True,
            capture_output=True,
            timeout=30
        )
        
        print(f"\nDocker exit code: {result.returncode}")
        
        if result.stdout:
            print("\nServer responses:")
            responses = result.stdout.strip().split('\n')
            for i, response_line in enumerate(responses, 1):
                if response_line.strip():
                    try:
                        response = json.loads(response_line)
                        print(f"  {i}. Response ID {response.get('id', 'N/A')}: {response.get('result', response.get('error', 'No result'))}")
                        
                        # Special handling for tools list
                        if response.get('id') == 2 and 'result' in response:
                            tools = response['result'].get('tools', [])
                            print(f"     Found {len(tools)} tools")
                            if tools:
                                print(f"     Sample tools: {[t.get('name', 'unnamed')[:30] for t in tools[:3]]}")
                        
                        # Special handling for tool call
                        if response.get('id') == 3:
                            if 'result' in response:
                                content = response['result'].get('content', [])
                                print(f"     Tool call succeeded, {len(content)} content items")
                            elif 'error' in response:
                                error = response['error']
                                print(f"     Tool call failed: {error.get('message', 'Unknown error')}")
                        
                    except json.JSONDecodeError:
                        print(f"  {i}. Raw: {response_line[:100]}...")
        
        if result.stderr:
            print(f"\nServer stderr:")
            stderr_lines = result.stderr.strip().split('\n')
            for line in stderr_lines[-5:]:  # Show last 5 lines
                if line.strip():
                    print(f"  {line}")
        
        # Analyze results
        success_count = 0
        if result.stdout:
            responses = result.stdout.strip().split('\n')
            for response_line in responses:
                if response_line.strip():
                    try:
                        response = json.loads(response_line)
                        if 'result' in response:
                            success_count += 1
                    except:
                        pass
        
        print(f"\nTest Results:")
        print(f"  Successful responses: {success_count}")
        print(f"  Server started: {'✓' if result.returncode == 0 else '✗'}")
        print(f"  JSON-RPC working: {'✓' if success_count > 0 else '✗'}")
        
        if success_count >= 2:  # Initialize + tools list at minimum
            print("🎉 ATLAS MCP Server JSON-RPC working!")
            return True
        else:
            print("⚠️ ATLAS MCP Server has issues")
            return False
            
    except subprocess.TimeoutExpired:
        print("✗ Test timed out - server may be hanging")
        return False
    except Exception as e:
        print(f"✗ Test failed: {e}")
        return False

def test_specific_tools():
    """Test specific ATLAS tools with realistic parameters"""
    print("\n" + "="*40)
    print("Testing Specific ATLAS Tools")
    print("="*40)
    
    tool_tests = [
        {
            "name": "list_project_tasks",
            "arguments": {"project_name": "TEST_PROJECT"}
        },
        {
            "name": "validate_file_operation", 
            "arguments": {
                "operation": "read",
                "file_path": "/tmp/test.txt",
                "expected_outcome": "success"
            }
        },
        {
            "name": "create_entities",
            "arguments": {
                "entities": [{
                    "name": "test_entity_docker",
                    "entityType": "test",
                    "observations": ["Docker JSON-RPC test observation"]
                }]
            }
        }
    ]
    
    for i, tool_test in enumerate(tool_tests, 1):
        print(f"\nTesting tool {i}: {tool_test['name']}")
        
        messages = [
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize", 
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "clientInfo": {"name": "atlas-tool-test", "version": "1.0.0"}
                }
            },
            {
                "jsonrpc": "2.0",
                "method": "notifications/initialized"
            },
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {
                    "name": tool_test["name"],
                    "arguments": tool_test["arguments"]
                }
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
                timeout=15
            )
            
            if result.stdout:
                responses = result.stdout.strip().split('\n')
                for response_line in responses:
                    if response_line.strip():
                        try:
                            response = json.loads(response_line)
                            if response.get('id') == 2:  # Our tool call
                                if 'result' in response:
                                    content = response['result'].get('content', [])
                                    print(f"  ✓ Success: {len(content)} content items")
                                    if content and isinstance(content[0], dict):
                                        text = content[0].get('text', '')[:100]
                                        print(f"    Result preview: {text}...")
                                elif 'error' in response:
                                    error = response['error']
                                    print(f"  ✗ Error: {error.get('message', 'Unknown')}")
                                break
                        except:
                            continue
            else:
                print(f"  ✗ No response")
                
        except Exception as e:
            print(f"  ✗ Test failed: {e}")

if __name__ == "__main__":
    success = test_atlas_server_jsonrpc()
    if success:
        test_specific_tools()
    exit(0 if success else 1)