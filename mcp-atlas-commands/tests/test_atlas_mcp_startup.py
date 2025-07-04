#!/usr/bin/env python3
"""Test script to verify atlas-commands MCP server startup."""

import subprocess
import json
import time
import sys

def test_atlas_mcp_startup():
    """Test the atlas-commands MCP server startup."""
    print("Testing atlas-commands MCP server startup...")
    
    # Docker command matching the .mcp.json configuration
    docker_cmd = [
        "docker", "run", "-i", "--rm",
        "-v", "/Users/elniak/Documents/Project/Software-Engineer-AI-Agent-Atlas/REPOS:/app/REPOS",
        "-v", "claude-memory-control:/app/memory-control",
        "-e", "ATLAS_STORAGE_PATH=/app/REPOS",
        "-e", "ATLAS_ENABLE_MEMORY=true",
        "-e", "ATLAS_ENABLE_TOOL_REGISTRY=true",
        "-e", "ATLAS_ENABLE_ERROR_HANDLING=false",
        "-e", "ATLAS_LOG_PERFORMANCE=true",
        "-e", "ATLAS_FALLBACK_LEGACY=false",
        "-e", "PROJECT_NAME=PANTHER",
        "-e", "REDIS_URL=redis://host.docker.internal:6379/0",
        "-e", "ATLAS_COMPRESSION_STRATEGY=adaptive",
        "-e", "ATLAS_COMPRESSION_MIN_SIZE=500",
        "-e", "ATLAS_COMPRESSION_ENABLE_LEARNING=true",
        "-e", "ATLAS_COMPRESSION_DEFAULT_QUALITY=0.85",
        "--add-host", "host.docker.internal:host-gateway",
        "atlas-commands-mcp:latest",
        "python", "-m", "atlas_commands.server"
    ]
    
    # Start the process
    process = subprocess.Popen(
        docker_cmd,
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
        # Wait a bit for server to start
        print("Waiting for server to initialize...")
        time.sleep(5)
        
        # Send request
        process.stdin.write(json.dumps(init_request) + '\n')
        process.stdin.flush()
        
        # Read response with timeout
        start_time = time.time()
        response_data = ""
        while time.time() - start_time < 30:  # 30 second timeout
            line = process.stdout.readline()
            if line:
                response_data += line
                if line.strip():  # Got a complete line
                    try:
                        response = json.loads(line)
                        print(f"Received response: {json.dumps(response, indent=2)}")
                        
                        if "result" in response:
                            print("✅ Server initialized successfully!")
                            return True
                        elif "error" in response:
                            print(f"❌ Server error: {response['error']}")
                            return False
                    except json.JSONDecodeError:
                        continue
            
            # Check if process has terminated
            if process.poll() is not None:
                stderr = process.stderr.read()
                print(f"❌ Process terminated. stderr: {stderr}")
                return False
                
        print("❌ Timeout waiting for response")
        return False
        
    finally:
        # Clean up
        process.terminate()
        process.wait()

if __name__ == "__main__":
    success = test_atlas_mcp_startup()
    sys.exit(0 if success else 1)