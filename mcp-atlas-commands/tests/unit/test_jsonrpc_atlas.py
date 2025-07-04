#!/usr/bin/env python3
"""
Test ATLAS MCP server using direct JSON-RPC commands.
Tests the server as it would be used by an MCP client.
"""

import json
import subprocess
import asyncio
import time
from typing import Dict, Any, List

class ATLASJSONRPCTester:
    """Test ATLAS MCP server via JSON-RPC stdio protocol"""
    
    def __init__(self):
        self.server_process = None
        self.test_results = {
            "start_time": time.time(),
            "tests": [],
            "errors": [],
            "server_info": {}
        }
    
    async def start_server(self):
        """Start the ATLAS MCP server process"""
        print("Starting ATLAS MCP server...")
        
        try:
            # Start server process with stdio communication
            self.server_process = await asyncio.create_subprocess_exec(
                "python", "-m", "atlas_commands.server",
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd="/Users/elniak/Documents/Project/Software-Engineer-AI-Agent-Atlas/mcp-atlas-commands/src"
            )
            
            print("✓ Server process started")
            return True
            
        except Exception as e:
            print(f"✗ Failed to start server: {e}")
            return False
    
    async def send_jsonrpc_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Send JSON-RPC message to server and get response"""
        if not self.server_process:
            raise RuntimeError("Server not started")
        
        # Send message
        message_json = json.dumps(message) + "\n"
        self.server_process.stdin.write(message_json.encode())
        await self.server_process.stdin.drain()
        
        # Read response
        response_line = await self.server_process.stdout.readline()
        if not response_line:
            raise RuntimeError("No response from server")
        
        try:
            response = json.loads(response_line.decode().strip())
            return response
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Invalid JSON response: {response_line.decode()}")
    
    async def test_initialize(self):
        """Test MCP initialization"""
        print("\n=== Testing MCP Initialization ===")
        
        init_message = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {}
                },
                "clientInfo": {
                    "name": "atlas-test-client",
                    "version": "1.0.0"
                }
            }
        }
        
        try:
            response = await self.send_jsonrpc_message(init_message)
            
            if "result" in response:
                print("✓ Server initialized successfully")
                self.test_results["server_info"] = response["result"]
                
                # Send initialized notification
                initialized_message = {
                    "jsonrpc": "2.0",
                    "method": "notifications/initialized"
                }
                await self.send_jsonrpc_message(initialized_message)
                
                return True
            else:
                print(f"✗ Initialization failed: {response}")
                return False
                
        except Exception as e:
            print(f"✗ Initialization error: {e}")
            return False
    
    async def test_tools_list(self):
        """Test tools/list request"""
        print("\n=== Testing Tools List ===")
        
        list_message = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/list",
            "params": {}
        }
        
        try:
            response = await self.send_jsonrpc_message(list_message)
            
            if "result" in response and "tools" in response["result"]:
                tools = response["result"]["tools"]
                print(f"✓ Found {len(tools)} tools")
                
                # Show first few tools
                for i, tool in enumerate(tools[:5]):
                    print(f"  - {tool.get('name', 'unnamed')}: {tool.get('description', 'no description')[:50]}...")
                
                if len(tools) > 5:
                    print(f"  ... and {len(tools) - 5} more tools")
                
                self.test_results["tools_count"] = len(tools)
                self.test_results["sample_tools"] = tools[:10]
                return tools
            else:
                print(f"✗ Tools list failed: {response}")
                return []
                
        except Exception as e:
            print(f"✗ Tools list error: {e}")
            return []
    
    async def test_tool_call(self, tool_name: str, arguments: Dict[str, Any]):
        """Test individual tool call"""
        call_message = {
            "jsonrpc": "2.0",
            "id": 3,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            }
        }
        
        start_time = time.time()
        
        try:
            response = await self.send_jsonrpc_message(call_message)
            execution_time = time.time() - start_time
            
            if "result" in response:
                content = response["result"].get("content", [])
                print(f"  ✓ {tool_name}: {execution_time:.4f}s")
                
                # Show result content summary
                if content:
                    first_content = content[0]
                    if isinstance(first_content, dict) and "text" in first_content:
                        text = first_content["text"]
                        if len(text) > 100:
                            print(f"    Result: {text[:100]}...")
                        else:
                            print(f"    Result: {text}")
                
                test_result = {
                    "tool": tool_name,
                    "success": True,
                    "execution_time": execution_time,
                    "content_count": len(content),
                    "error": None
                }
                
            elif "error" in response:
                print(f"  ✗ {tool_name}: {response['error'].get('message', 'Unknown error')}")
                test_result = {
                    "tool": tool_name,
                    "success": False,
                    "execution_time": execution_time,
                    "content_count": 0,
                    "error": response["error"]
                }
            else:
                print(f"  ✗ {tool_name}: Invalid response format")
                test_result = {
                    "tool": tool_name,
                    "success": False,
                    "execution_time": execution_time,
                    "content_count": 0,
                    "error": "Invalid response format"
                }
            
            self.test_results["tests"].append(test_result)
            return test_result
            
        except Exception as e:
            execution_time = time.time() - start_time
            print(f"  ✗ {tool_name}: {str(e)}")
            
            test_result = {
                "tool": tool_name,
                "success": False,
                "execution_time": execution_time,
                "content_count": 0,
                "error": str(e)
            }
            
            self.test_results["tests"].append(test_result)
            return test_result
    
    async def test_sample_tools(self, tools: List[Dict[str, Any]]):
        """Test a sample of available tools"""
        print("\n=== Testing Sample Tools ===")
        
        # Define test cases for common tools
        test_cases = {
            "create_task_metadata": {
                "project_name": "TEST_PROJECT",
                "task_id": "test_task_001",
                "task_type": "testing",
                "description": "JSON-RPC test task"
            },
            "list_project_tasks": {
                "project_name": "TEST_PROJECT"
            },
            "validate_file_operation": {
                "operation": "read",
                "file_path": "/tmp/test.txt",
                "expected_outcome": "success"
            },
            "adaptive_command_selection": {
                "task_description": "test task",
                "domain": "testing"
            },
            "create_entities": {
                "entities": [{
                    "name": "test_entity",
                    "entityType": "test",
                    "observations": ["test observation"]
                }]
            }
        }
        
        tools_to_test = []
        
        # Find tools we have test cases for
        for tool in tools[:20]:  # Test first 20 tools max
            tool_name = tool.get("name", "")
            if tool_name in test_cases:
                tools_to_test.append((tool_name, test_cases[tool_name]))
            elif tool_name.startswith("mcp__atlas-commands__"):
                # Strip prefix for ATLAS tools
                clean_name = tool_name.replace("mcp__atlas-commands__", "")
                if clean_name in test_cases:
                    tools_to_test.append((tool_name, test_cases[clean_name]))
        
        # If no specific test cases, try some tools with empty arguments
        if not tools_to_test:
            for tool in tools[:5]:
                tool_name = tool.get("name", "")
                tools_to_test.append((tool_name, {}))
        
        print(f"Testing {len(tools_to_test)} tools...")
        
        for tool_name, arguments in tools_to_test:
            await self.test_tool_call(tool_name, arguments)
    
    async def test_shutdown(self):
        """Test graceful shutdown"""
        print("\n=== Testing Shutdown ===")
        
        try:
            # Send shutdown notification (no response expected)
            shutdown_message = {
                "jsonrpc": "2.0",
                "method": "notifications/cancelled"
            }
            
            await self.send_jsonrpc_message(shutdown_message)
            
            # Close stdin to signal end
            self.server_process.stdin.close()
            
            # Wait for process to terminate
            await asyncio.wait_for(self.server_process.wait(), timeout=5.0)
            
            print("✓ Server shut down gracefully")
            return True
            
        except asyncio.TimeoutError:
            print("⚠ Server did not shut down within timeout, terminating...")
            self.server_process.terminate()
            await self.server_process.wait()
            return False
        except Exception as e:
            print(f"✗ Shutdown error: {e}")
            return False
    
    def generate_report(self):
        """Generate test report"""
        total_time = time.time() - self.test_results["start_time"]
        
        successful_tests = [t for t in self.test_results["tests"] if t["success"]]
        failed_tests = [t for t in self.test_results["tests"] if not t["success"]]
        
        print("\n" + "="*60)
        print("ATLAS MCP JSON-RPC Test Report")
        print("="*60)
        print(f"Test Duration: {total_time:.2f} seconds")
        print(f"Tools Available: {self.test_results.get('tools_count', 0)}")
        print(f"Tools Tested: {len(self.test_results['tests'])}")
        print(f"Successful: {len(successful_tests)}")
        print(f"Failed: {len(failed_tests)}")
        
        if successful_tests:
            avg_time = sum(t["execution_time"] for t in successful_tests) / len(successful_tests)
            print(f"Average Execution Time: {avg_time:.4f}s")
        
        if failed_tests:
            print(f"\nFailed Tools:")
            for test in failed_tests:
                print(f"  - {test['tool']}: {test['error']}")
        
        success_rate = len(successful_tests) / len(self.test_results["tests"]) * 100 if self.test_results["tests"] else 0
        print(f"\nSuccess Rate: {success_rate:.1f}%")
        
        if success_rate == 100 and len(successful_tests) > 0:
            print("🎉 ALL TESTED TOOLS WORKING!")
        elif success_rate >= 80:
            print("✅ MOSTLY WORKING - Good status")
        elif success_rate >= 50:
            print("⚠️ PARTIALLY WORKING - Needs attention")
        else:
            print("❌ MAJOR ISSUES - Critical problems")
        
        return success_rate >= 80
    
    async def run_full_test_suite(self):
        """Run complete JSON-RPC test suite"""
        print("ATLAS MCP JSON-RPC Test Suite")
        print("="*40)
        
        try:
            # Start server
            if not await self.start_server():
                return False
            
            # Initialize MCP protocol
            if not await self.test_initialize():
                return False
            
            # Get tools list
            tools = await self.test_tools_list()
            if not tools:
                return False
            
            # Test sample tools
            await self.test_sample_tools(tools)
            
            # Shutdown
            await self.test_shutdown()
            
            # Generate report
            return self.generate_report()
            
        except Exception as e:
            print(f"Test suite error: {e}")
            if self.server_process:
                self.server_process.terminate()
                await self.server_process.wait()
            return False

async def main():
    """Main test runner"""
    tester = ATLASJSONRPCTester()
    success = await tester.run_full_test_suite()
    return 0 if success else 1

if __name__ == "__main__":
    import sys
    result = asyncio.run(main())
    sys.exit(result)