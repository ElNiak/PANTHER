#!/usr/bin/env python3
"""
Test proper MCP protocol implementation
"""

import json
import subprocess
import sys
import time
from datetime import datetime

def test_mcp_protocol_sequence():
    """Test proper MCP protocol sequence: initialize -> initialized -> tools/list"""
    
    print("=== Testing Complete MCP Protocol Sequence ===")
    
    # Step 1: Initialize request
    initialize_request = {
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
                "name": "test-client",
                "version": "1.0.0"
            }
        }
    }
    
    # Step 2: Initialized notification  
    initialized_notification = {
        "jsonrpc": "2.0",
        "method": "notifications/initialized"
    }
    
    # Step 3: List tools request
    list_tools_request = {
        "jsonrpc": "2.0", 
        "id": 2,
        "method": "tools/list"
    }
    
    # Combine all requests with proper delimiters
    protocol_sequence = "\n".join([
        json.dumps(initialize_request),
        json.dumps(initialized_notification), 
        json.dumps(list_tools_request)
    ])
    
    try:
        # Run via docker with complete protocol sequence
        cmd = [
            "docker", "run", "-i", "--rm",
            "-v", "/Users/elniak/Documents/Project/Software-Engineer-AI-Agent-Atlas/REPOS:/app/REPOS",
            "-e", "ATLAS_STORAGE_PATH=/app/REPOS", 
            "-e", "PROJECT_NAME=ATLAS_TEST",
            "-e", "ATLAS_ENABLE_MEMORY=true",
            "-e", "ATLAS_LOG_PERFORMANCE=true",
            "atlas-commands-mcp:latest",
            "python", "-m", "atlas_commands.server"
        ]
        
        print("Sending MCP protocol sequence:")
        print("1. Initialize request")
        print("2. Initialized notification") 
        print("3. Tools/list request")
        print()
        
        # Send complete protocol sequence
        result = subprocess.run(
            cmd,
            input=protocol_sequence,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        print(f"Return code: {result.returncode}")
        print(f"STDERR:\n{result.stderr}")
        print()
        
        if result.stdout:
            # Parse line-by-line responses
            lines = result.stdout.strip().split('\n')
            print(f"Received {len(lines)} response lines:")
            
            for i, line in enumerate(lines, 1):
                try:
                    response = json.loads(line)
                    print(f"Response {i}: {json.dumps(response, indent=2)}")
                    
                    # Check if this is the tools/list response
                    if 'result' in response and 'tools' in response.get('result', {}):
                        tools = response['result']['tools']
                        print(f"✅ Found {len(tools)} tools in response {i}")
                        
                        # Show first few tools
                        for j, tool in enumerate(tools[:3]):
                            print(f"  Tool {j+1}: {tool.get('name', 'unnamed')}")
                        
                        return True
                        
                except json.JSONDecodeError as e:
                    print(f"Response {i} (non-JSON): {line}")
            
            # Check for errors in any response
            for i, line in enumerate(lines, 1):
                try:
                    response = json.loads(line)
                    if 'error' in response:
                        print(f"❌ Error in response {i}: {response['error']}")
                        return False
                except:
                    continue
                    
        return False
        
    except subprocess.TimeoutExpired:
        print("❌ Request timed out")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    return False

def test_simple_tools_list_only():
    """Test just tools/list without proper initialization (should fail)"""
    
    print("\n=== Testing tools/list Without Initialization (Should Fail) ===")
    
    list_tools_request = {
        "jsonrpc": "2.0",
        "id": 1, 
        "method": "tools/list"
    }
    
    try:
        cmd = [
            "docker", "run", "-i", "--rm",
            "-v", "/Users/elniak/Documents/Project/Software-Engineer-AI-Agent-Atlas/REPOS:/app/REPOS",
            "-e", "ATLAS_STORAGE_PATH=/app/REPOS",
            "atlas-commands-mcp:latest",
            "python", "-m", "atlas_commands.server"
        ]
        
        result = subprocess.run(
            cmd,
            input=json.dumps(list_tools_request),
            capture_output=True,
            text=True,
            timeout=15
        )
        
        if result.stdout:
            try:
                response = json.loads(result.stdout)
                if 'error' in response and response['error']['code'] == -32602:
                    print("✅ Correctly rejected tools/list without initialization")
                    print(f"Error: {response['error']['message']}")
                    return True
                else:
                    print(f"❌ Unexpected response: {response}")
            except json.JSONDecodeError:
                print(f"❌ Invalid JSON response: {result.stdout}")
        
        return False
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    """Run all protocol tests"""
    print("=== Atlas MCP Protocol Testing ===")
    print(f"Test started at: {datetime.now()}")
    
    tests = [
        ("Complete MCP Protocol", test_mcp_protocol_sequence),
        ("Invalid Request (No Init)", test_simple_tools_list_only),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n{'='*60}")
        print(f"Running: {test_name}")
        print('='*60)
        
        try:
            result = test_func()
            results.append((test_name, result))
            print(f"\nResult: {'✅ PASSED' if result else '❌ FAILED'}")
        except Exception as e:
            print(f"❌ EXCEPTION: {e}")
            results.append((test_name, False))
    
    # Summary
    print(f"\n{'='*60}")
    print("FINAL SUMMARY")
    print('='*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name}: {status}")
    
    print(f"\nOverall: {passed}/{total} tests passed ({(passed/total)*100:.1f}%)")
    
    return results

if __name__ == "__main__":
    main()