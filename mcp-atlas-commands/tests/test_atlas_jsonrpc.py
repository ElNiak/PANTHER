#!/usr/bin/env python3
"""
Direct JSON-RPC test for Atlas MCP server
"""

import json
import subprocess
import sys
from datetime import datetime

def test_atlas_jsonrpc():
    """Test Atlas MCP server via JSON-RPC"""
    
    # Test 1: List tools
    print("=== Test 1: List Available Tools ===")
    list_tools_request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "tools/list"
    }
    
    try:
        # Run via docker with JSON-RPC input
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
        
        # Send JSON-RPC request
        result = subprocess.run(
            cmd, 
            input=json.dumps(list_tools_request),
            capture_output=True, 
            text=True, 
            timeout=30
        )
        
        print(f"Return code: {result.returncode}")
        print(f"STDOUT:\n{result.stdout}")
        print(f"STDERR:\n{result.stderr}")
        
        if result.stdout:
            try:
                response = json.loads(result.stdout)
                print(f"✅ JSON Response received: {len(response.get('result', {}).get('tools', []))} tools")
                return response
            except json.JSONDecodeError as e:
                print(f"❌ Invalid JSON response: {e}")
        
    except subprocess.TimeoutExpired:
        print("❌ Request timed out")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    return None

def test_simple_docker_command():
    """Test basic docker functionality"""
    print("\n=== Test 2: Basic Docker Test ===")
    
    try:
        cmd = [
            "docker", "run", "--rm",
            "atlas-commands-mcp:latest",
            "python", "-c", "print('Docker container working'); import atlas_commands; print(f'Atlas commands module loaded: {atlas_commands.__file__}')"
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        
        print(f"Return code: {result.returncode}")
        print(f"STDOUT:\n{result.stdout}")
        print(f"STDERR:\n{result.stderr}")
        
        if result.returncode == 0:
            print("✅ Docker container and Atlas module working")
            return True
        else:
            print("❌ Docker container test failed")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def test_server_health():
    """Test server health check"""
    print("\n=== Test 3: Server Health Check ===")
    
    try:
        cmd = [
            "docker", "run", "--rm",
            "-v", "/Users/elniak/Documents/Project/Software-Engineer-AI-Agent-Atlas/REPOS:/app/REPOS",
            "-e", "ATLAS_STORAGE_PATH=/app/REPOS",
            "atlas-commands-mcp:latest",
            "python", "-c", 
            """
import sys
sys.path.append('/app/src')
try:
    from atlas_commands.server import *
    print('✅ Server module imports successful')
    
    # Try to list available handlers
    import os
    print(f'Storage path: {os.environ.get("ATLAS_STORAGE_PATH", "Not set")}')
    print('✅ Environment variables loaded')
    
except Exception as e:
    print(f'❌ Import error: {e}')
    import traceback
    traceback.print_exc()
"""
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        
        print(f"Return code: {result.returncode}")
        print(f"STDOUT:\n{result.stdout}")
        print(f"STDERR:\n{result.stderr}")
        
        return result.returncode == 0
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

def main():
    """Run all tests"""
    print("=== Atlas MCP Server Direct Testing ===")
    print(f"Test started at: {datetime.now()}")
    
    # Run tests in sequence
    tests = [
        ("Docker & Module Test", test_simple_docker_command),
        ("Server Health Check", test_server_health),
        ("JSON-RPC Interface", test_atlas_jsonrpc),
    ]
    
    results = []
    for test_name, test_func in tests:
        print(f"\n{'='*50}")
        print(f"Running: {test_name}")
        print('='*50)
        
        try:
            result = test_func()
            results.append((test_name, result))
            print(f"Result: {'✅ PASSED' if result else '❌ FAILED'}")
        except Exception as e:
            print(f"❌ EXCEPTION: {e}")
            results.append((test_name, False))
    
    # Summary
    print(f"\n{'='*50}")
    print("FINAL SUMMARY")
    print('='*50)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name}: {status}")
    
    print(f"\nOverall: {passed}/{total} tests passed ({(passed/total)*100:.1f}%)")
    
    return results

if __name__ == "__main__":
    main()