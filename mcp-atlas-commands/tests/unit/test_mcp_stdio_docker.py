#!/usr/bin/env python3
"""
Test ATLAS MCP server in Docker container using stdio transport.
This tests the actual MCP protocol as it would be used by Claude.
"""

import asyncio
import json
import subprocess
import sys
from typing import Dict, Any, Optional


class MCPStdioTester:
    """Test MCP server using stdio transport in Docker."""
    
    def __init__(self):
        self.process: Optional[subprocess.Popen] = None
        self.request_id = 0
    
    def get_next_id(self) -> int:
        """Get next request ID."""
        self.request_id += 1
        return self.request_id
    
    async def start_server(self):
        """Start the MCP server in Docker container."""
        print("🚀 Starting ATLAS MCP server in Docker...")
        
        # Start the container with stdio
        self.process = subprocess.Popen([
            "docker", "run", "--rm", "-i",
            "--link", "atlas-redis:redis",
            "-e", "REDIS_URL=redis://redis:6379",
            "atlas-commands-mcp:latest",
            "python", "-m", "atlas_commands.server"
        ], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        print("✅ Docker container started")
        
        # Initialize the MCP session
        await self.send_initialize()
    
    async def send_request(self, method: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Send a JSON-RPC request to the MCP server."""
        if not self.process:
            raise RuntimeError("Server not started")
        
        request = {
            "jsonrpc": "2.0",
            "id": self.get_next_id(),
            "method": method
        }
        
        if params:
            request["params"] = params
        
        # Send request
        request_line = json.dumps(request) + "\n"
        print(f"→ Sending: {method}")
        self.process.stdin.write(request_line)
        self.process.stdin.flush()
        
        # Read response
        try:
            response_line = self.process.stdout.readline()
            if not response_line:
                stderr_output = self.process.stderr.read()
                raise RuntimeError(f"No response from server. STDERR: {stderr_output}")
            
            response = json.loads(response_line.strip())
            print(f"← Received: {response.get('result', {}).get('_meta', {}).get('progressToken', 'success')}")
            return response
            
        except json.JSONDecodeError as e:
            print(f"❌ Invalid JSON response: {response_line}")
            raise
    
    async def send_initialize(self):
        """Send initialize request to start MCP session."""
        params = {
            "protocolVersion": "2024-11-05", 
            "capabilities": {
                "tools": {}
            },
            "clientInfo": {
                "name": "atlas-mcp-tester",
                "version": "1.0.0"
            }
        }
        
        response = await self.send_request("initialize", params)
        
        if "error" in response:
            raise RuntimeError(f"Initialize failed: {response['error']}")
        
        print("✅ MCP session initialized")
        
        # Send initialized notification
        notification = {
            "jsonrpc": "2.0",
            "method": "notifications/initialized"
        }
        
        notification_line = json.dumps(notification) + "\n"
        self.process.stdin.write(notification_line)
        self.process.stdin.flush()
        
        return response
    
    async def test_list_tools(self):
        """Test listing available tools."""
        print("\n📋 Testing tools/list...")
        
        response = await self.send_request("tools/list")
        
        if "error" in response:
            print(f"❌ tools/list failed: {response['error']}")
            return False
        
        tools = response.get("result", {}).get("tools", [])
        print(f"✅ Found {len(tools)} tools")
        
        # Show first few tools
        for tool in tools[:5]:
            print(f"   - {tool.get('name', 'unknown')}")
        
        if len(tools) > 5:
            print(f"   ... and {len(tools) - 5} more")
        
        return len(tools) > 0
    
    async def test_call_tool(self, tool_name: str, arguments: Dict[str, Any] = None):
        """Test calling a specific tool."""
        print(f"\n🔧 Testing tools/call with {tool_name}...")
        
        params = {
            "name": tool_name
        }
        
        if arguments:
            params["arguments"] = arguments
        
        response = await self.send_request("tools/call", params)
        
        if "error" in response:
            print(f"❌ {tool_name} failed: {response['error']}")
            return False
        
        result = response.get("result", {})
        content = result.get("content", [])
        
        print(f"✅ {tool_name} completed with {len(content)} content items")
        
        # Show first content item if available
        if content:
            first_content = content[0]
            text = first_content.get("text", "")
            if len(text) > 100:
                print(f"   Response: {text[:100]}...")
            else:
                print(f"   Response: {text}")
        
        return True
    
    async def run_tests(self):
        """Run comprehensive MCP protocol tests."""
        print("🔍 Starting ATLAS MCP stdio protocol tests...")
        
        test_results = {}
        
        try:
            await self.start_server()
            
            # Test basic functionality
            test_results["list_tools"] = await self.test_list_tools()
            
            # Test specific tools
            test_tools = [
                ("memory_health_check", {}),
                ("get_cache_stats", {}),
                ("create_task_metadata", {
                    "project_name": "stdio-test",
                    "task_id": "stdio-test-001", 
                    "task_type": "validation",
                    "description": "MCP stdio protocol test"
                }),
                ("adaptive_command_selection", {
                    "task_description": "Test MCP protocol communication",
                    "domain": "testing"
                })
            ]
            
            for tool_name, arguments in test_tools:
                test_results[tool_name] = await self.test_call_tool(tool_name, arguments)
            
        except Exception as e:
            print(f"❌ Test execution failed: {e}")
            return False
        
        finally:
            await self.cleanup()
        
        # Summary
        print("\n" + "="*60)
        print("📊 MCP STDIO PROTOCOL TEST SUMMARY")
        print("="*60)
        
        passed = sum(test_results.values())
        total = len(test_results)
        
        for test_name, result in test_results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{test_name.replace('_', ' ').title()}: {status}")
        
        print(f"\nOverall: {passed}/{total} tests passed")
        
        if passed == total:
            print("🎉 ALL MCP PROTOCOL TESTS PASSED!")
            print("🚀 ATLAS MCP Docker container is production ready!")
            return True
        else:
            print("⚠️  Some MCP protocol tests failed")
            return False
    
    async def cleanup(self):
        """Clean up the server process."""
        if self.process:
            print("🧹 Cleaning up server process...")
            self.process.terminate()
            try:
                await asyncio.wait_for(asyncio.create_task(self._wait_for_process()), timeout=10)
            except asyncio.TimeoutError:
                print("⚠️  Process didn't terminate gracefully, killing...")
                self.process.kill()
                await asyncio.create_task(self._wait_for_process())
    
    async def _wait_for_process(self):
        """Wait for process to terminate."""
        while self.process.poll() is None:
            await asyncio.sleep(0.1)


async def main():
    """Main test execution."""
    tester = MCPStdioTester()
    success = await tester.run_tests()
    
    if success:
        print("\n✅ MCP stdio protocol validation completed successfully!")
        print("🚀 Docker container is ready for Claude integration!")
    else:
        print("\n❌ MCP protocol validation had issues")
        print("🔧 Review the test output and investigate problems")
    
    return success


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)