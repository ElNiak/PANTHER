#!/usr/bin/env python3
"""Test the persistent atlas-commands MCP server."""

import subprocess
import json
import time

def test_persistent_mcp():
    """Test connecting to the persistent MCP server."""
    print("Testing persistent atlas-commands MCP server...")
    
    # Use docker exec instead of run
    cmd = ["docker", "exec", "-i", "atlas-mcp-persistent", "python", "-m", "atlas_commands.server"]
    
    process = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    # Send initialization request
    init_request = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "0.1.0",
            "capabilities": {},
            "clientInfo": {
                "name": "test-client",
                "version": "1.0.0"
            }
        }
    }
    
    try:
        # Send request immediately (no wait needed for persistent container)
        process.stdin.write(json.dumps(init_request) + '\n')
        process.stdin.flush()
        
        # Read response
        start_time = time.time()
        while time.time() - start_time < 10:  # 10 second timeout
            line = process.stdout.readline()
            if line:
                try:
                    response = json.loads(line)
                    print(f"✅ Received response: {json.dumps(response, indent=2)}")
                    return True
                except json.JSONDecodeError:
                    continue
                    
        print("❌ Timeout")
        return False
        
    finally:
        process.terminate()
        process.wait()

if __name__ == "__main__":
    test_persistent_mcp()