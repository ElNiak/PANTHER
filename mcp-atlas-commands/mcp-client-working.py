#!/usr/bin/env python3
"""
Working MCP client for ATLAS command system.
Handles proper JSON-RPC communication via Docker container stdio.
"""

import json
import subprocess
import sys
import time
import os
from typing import Dict, Any, Optional

class AtlasMcpClient:
    def __init__(self, container_name: str = "atlas-commands-mcp"):
        self.container_name = container_name
        self.process = None
        self.initialized = False
        
    def start_session(self):
        """Start MCP session with container."""
        try:
            # Start docker exec with persistent stdin/stdout
            cmd = ["docker", "exec", "-i", self.container_name, "python", "-m", "atlas_commands.server"]
            self.process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=0  # Unbuffered
            )
            
            # Initialize MCP protocol
            self._send_initialize()
            return True
            
        except Exception as e:
            print(f"Failed to start MCP session: {e}")
            return False
    
    def _send_initialize(self):
        """Send MCP initialization sequence."""
        # Send initialize request
        init_request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "atlas-client", "version": "1.0.0"}
            }
        }
        
        print("📤 Sending initialization request...")
        self._send_json(init_request)
        
        # Wait for response
        response = self._read_response(timeout=15)
        if response and response.get("id") == 1:
            print("✅ MCP initialization successful")
            
            # Send initialized notification
            notification = {
                "jsonrpc": "2.0",
                "method": "notifications/initialized"
            }
            self._send_json(notification)
            self.initialized = True
        else:
            print(f"❌ MCP initialization failed - response: {response}")
            if self.process and self.process.stderr:
                stderr_output = self.process.stderr.read()
                if stderr_output:
                    print(f"Server stderr: {stderr_output}")
            
    def _send_json(self, data: Dict[str, Any]):
        """Send JSON-RPC message."""
        if not self.process:
            raise RuntimeError("Session not started")
            
        message = json.dumps(data) + "\n"
        self.process.stdin.write(message)
        self.process.stdin.flush()
        
    def _read_response(self, timeout: int = 30) -> Optional[Dict[str, Any]]:
        """Read JSON-RPC response with timeout."""
        if not self.process:
            return None
            
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                # Use a shorter timeout for readline to avoid blocking
                import select
                ready, _, _ = select.select([self.process.stdout], [], [], 0.5)
                if ready:
                    line = self.process.stdout.readline()
                    if line.strip():
                        try:
                            data = json.loads(line.strip())
                            print(f"📥 Received: {data}")
                            return data
                        except json.JSONDecodeError as e:
                            print(f"JSON decode error: {e}, line: {line}")
                            continue
            except Exception as e:
                print(f"Error reading response: {e}")
                break
                
            # Check if process died
            if self.process.poll() is not None:
                print("Process terminated unexpectedly")
                break
                
        print(f"Timeout after {timeout}s waiting for response")
        return None
        
    def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Call MCP tool and return response."""
        if not self.initialized:
            print("❌ Session not initialized")
            return None
            
        request_id = int(time.time() * 1000) % 1000000  # Unique ID
        
        request = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            }
        }
        
        print(f"📤 Calling tool: {tool_name}")
        self._send_json(request)
        
        # Read response
        response = self._read_response()
        if response and response.get("id") == request_id:
            return response
        else:
            print(f"❌ No response received for {tool_name}")
            return None
            
    def list_tools(self) -> Optional[Dict[str, Any]]:
        """List available MCP tools."""
        if not self.initialized:
            print("❌ Session not initialized")
            return None
            
        request = {
            "jsonrpc": "2.0", 
            "id": 2,
            "method": "tools/list"
        }
        
        print("📤 Listing tools...")
        self._send_json(request)
        
        response = self._read_response()
        if response and response.get("id") == 2:
            return response
        else:
            print("❌ Failed to list tools")
            return None
            
    def close_session(self):
        """Close MCP session."""
        if self.process:
            self.process.terminate()
            self.process.wait(timeout=5)
            self.process = None
        self.initialized = False

def main():
    """Main CLI interface."""
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python mcp-client-working.py list-tools")
        print("  python mcp-client-working.py call <tool_name> <json_args>")
        print("  python mcp-client-working.py test")
        return
        
    command = sys.argv[1]
    client = AtlasMcpClient()
    
    try:
        if not client.start_session():
            print("❌ Failed to start MCP session")
            return
            
        if command == "list-tools":
            response = client.list_tools()
            if response and "result" in response:
                tools = response["result"]["tools"]
                print(f"✅ Found {len(tools)} tools:")
                for tool in tools[:10]:  # Show first 10
                    print(f"  - {tool['name']}: {tool['description']}")
                if len(tools) > 10:
                    print(f"  ... and {len(tools) - 10} more")
            
        elif command == "call" and len(sys.argv) >= 4:
            tool_name = sys.argv[2]
            try:
                arguments = json.loads(sys.argv[3])
            except json.JSONDecodeError:
                print("❌ Invalid JSON arguments")
                return
                
            response = client.call_tool(tool_name, arguments)
            if response and "result" in response:
                result = response["result"]
                if isinstance(result, list) and len(result) > 0:
                    print("✅ Tool response:")
                    print(result[0].get("text", str(result)))
                else:
                    print("✅ Tool response:", result)
            elif response and "error" in response:
                print("❌ Tool error:", response["error"])
                
        elif command == "test":
            print("🧪 Testing MCP communication...")
            
            # Test 1: List tools
            tools_response = client.list_tools()
            if tools_response:
                tool_count = len(tools_response["result"]["tools"])
                print(f"✅ Test 1 passed: {tool_count} tools available")
            else:
                print("❌ Test 1 failed: Could not list tools")
                return
                
            # Test 2: Call a simple tool
            test_response = client.call_tool("list_project_tasks", {"project_name": "TEST"})
            if test_response:
                print("✅ Test 2 passed: Tool call successful")
                if "result" in test_response:
                    result = test_response["result"]
                    if isinstance(result, list) and len(result) > 0:
                        print("📄 Response preview:", result[0].get("text", "")[:200])
            else:
                print("❌ Test 2 failed: Tool call failed")
                
        else:
            print("❌ Unknown command or missing arguments")
            
    except KeyboardInterrupt:
        print("\n🛑 Interrupted by user")
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        client.close_session()

if __name__ == "__main__":
    main()