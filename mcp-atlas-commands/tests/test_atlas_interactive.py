#!/usr/bin/env python3
"""
Interactive test for Atlas MCP server with proper initialization
"""

import json
import subprocess
import time
import threading
from datetime import datetime

def test_atlas_interactive():
    """Test Atlas MCP server interactively"""
    
    print("=== Atlas MCP Interactive Test ===")
    print(f"Started at: {datetime.now()}")
    
    # Start the server
    cmd = [
        "docker", "run", "-i", "--rm",
        "-v", "/Users/elniak/Documents/Project/Software-Engineer-AI-Agent-Atlas/REPOS:/app/REPOS",
        "-e", "ATLAS_STORAGE_PATH=/app/REPOS",
        "-e", "PROJECT_NAME=ATLAS_TEST",
        "-e", "ATLAS_ENABLE_MEMORY=true",
        "-e", "ATLAS_LOG_PERFORMANCE=true",
        "-e", "ATLAS_FALLBACK_LEGACY=true",
        "atlas-commands-mcp:latest",
        "python", "-m", "atlas_commands.server"
    ]
    
    print("Starting Atlas MCP server...")
    
    try:
        process = subprocess.Popen(
            cmd,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )
        
        # Give server time to initialize
        print("Waiting for server initialization...")
        time.sleep(3)
        
        # Test 1: Initialize
        print("\n1. Testing initialization...")
        init_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "roots": {
                        "listChanged": True
                    },
                    "sampling": {}
                },
                "clientInfo": {
                    "name": "atlas-test-client",
                    "version": "1.0.0"
                }
            }
        }
        
        process.stdin.write(json.dumps(init_request) + "\n")
        process.stdin.flush()
        
        # Read response
        response = process.stdout.readline()
        print(f"Init response: {response.strip()}")
        
        # Test 2: List tools
        print("\n2. Testing tools/list...")
        list_tools_request = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list"
        }
        
        process.stdin.write(json.dumps(list_tools_request) + "\n")
        process.stdin.flush()
        
        # Read response
        response = process.stdout.readline()
        print(f"Tools list response: {response.strip()}")
        
        if response.strip():
            try:
                tools_data = json.loads(response.strip())
                if "result" in tools_data and "tools" in tools_data["result"]:
                    tools = tools_data["result"]["tools"]
                    print(f"✅ Found {len(tools)} tools")
                    
                    # Show first few tools
                    for i, tool in enumerate(tools[:5]):
                        print(f"  - {tool['name']}")
                    
                    if len(tools) > 5:
                        print(f"  ... and {len(tools) - 5} more")
                else:
                    print("❌ No tools found in response")
            except json.JSONDecodeError:
                print("❌ Invalid JSON in tools response")
        
        # Test 3: Call a simple tool
        print("\n3. Testing tool call...")
        if "tools" in locals() and len(tools) > 0:
            # Find a simple tool to test
            test_tool = None
            for tool in tools:
                if "list_project_tasks" in tool['name'] or "get_observability_status" in tool['name']:
                    test_tool = tool
                    break
            
            if test_tool:
                call_request = {
                    "jsonrpc": "2.0",
                    "id": 3,
                    "method": "tools/call",
                    "params": {
                        "name": test_tool['name'],
                        "arguments": {
                            "project_name": "ATLAS_TEST"
                        }
                    }
                }
                
                process.stdin.write(json.dumps(call_request) + "\n")
                process.stdin.flush()
                
                # Read response
                response = process.stdout.readline()
                print(f"Tool call response: {response.strip()}")
                
                if response.strip():
                    try:
                        call_data = json.loads(response.strip())
                        if "result" in call_data:
                            print(f"✅ Tool call successful: {test_tool['name']}")
                        else:
                            print(f"❌ Tool call failed: {call_data}")
                    except json.JSONDecodeError:
                        print("❌ Invalid JSON in tool call response")
            else:
                print("❌ No suitable test tool found")
        
        # Cleanup
        process.stdin.close()
        process.wait(timeout=5)
        
        print("\n✅ Interactive test completed")
        
    except subprocess.TimeoutExpired:
        process.kill()
        print("❌ Server process timed out")
    except Exception as e:
        print(f"❌ Error: {e}")
        if 'process' in locals():
            process.kill()

def test_tools_via_existing_connection():
    """Test using existing Claude connection to MCP"""
    print("\n=== Testing via Claude MCP Connection ===")
    
    # Read the current .mcp.json to see what's configured
    try:
        with open("/Users/elniak/Documents/Project/Software-Engineer-AI-Agent-Atlas/.mcp.json", "r") as f:
            mcp_config = json.load(f)
        
        atlas_config = mcp_config.get("mcpServers", {}).get("atlas-commands", {})
        if atlas_config:
            print("✅ Atlas MCP server configured in .mcp.json")
            print(f"Command: {atlas_config.get('command')}")
            print(f"Args: {atlas_config.get('args', [])}")
            
            # Check environment variables
            env_vars = atlas_config.get('env', {})
            for key, value in env_vars.items():
                print(f"  {key}: {value}")
                
            return True
        else:
            print("❌ Atlas MCP server not found in .mcp.json")
            return False
            
    except Exception as e:
        print(f"❌ Error reading .mcp.json: {e}")
        return False

def main():
    """Run all tests"""
    print("=== Comprehensive Atlas MCP Testing ===")
    
    # Test 1: Check configuration
    config_ok = test_tools_via_existing_connection()
    
    # Test 2: Interactive server test
    if config_ok:
        test_atlas_interactive()
    else:
        print("Skipping interactive test due to configuration issues")
    
    print(f"\nTest completed at: {datetime.now()}")

if __name__ == "__main__":
    main()