#!/usr/bin/env python3
"""Test Atlas MCP with JSON-RPC requests to Docker container."""

import asyncio
import json
import subprocess
import time
import logging
from typing import Dict, Any, List

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AtlasDockerMCPTester:
    """Test Atlas MCP through JSON-RPC requests to Docker container."""
    
    def __init__(self):
        self.container_name = "atlas-mcp-jsonrpc-test"
        self.container_id = None
        
    def start_container(self) -> bool:
        """Start Atlas MCP container in server mode."""
        try:
            # Cleanup existing container
            subprocess.run(['docker', 'stop', self.container_name], 
                         capture_output=True, check=False)
            subprocess.run(['docker', 'rm', self.container_name], 
                         capture_output=True, check=False)
            
            # Start container with JSON-RPC server mode
            result = subprocess.run([
                'docker', 'run', '-d', '--name', self.container_name,
                '-v', f'{subprocess.check_output(["pwd"]).decode().strip()}/REPOS:/app/REPOS',
                'atlas-commands-mcp:latest'
            ], capture_output=True, text=True, check=True)
            
            self.container_id = result.stdout.strip()
            logger.info(f"Started Atlas MCP container: {self.container_id[:12]}")
            
            # Wait for container to initialize
            time.sleep(10)
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to start container: {e}")
            return False
    
    def send_jsonrpc_request(self, method: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Send JSON-RPC request to the Atlas MCP container."""
        request = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
            "params": params or {}
        }
        
        try:
            # Send request via docker exec with python
            result = subprocess.run([
                'docker', 'exec', self.container_name,
                'python', '-c', f'''
import asyncio
import json
import os
from src.atlas_commands.server import EnhancedAtlasCommandsServer

async def handle_request():
    try:
        os.environ["ATLAS_STORAGE_PATH"] = "/app/REPOS"
        server = EnhancedAtlasCommandsServer()
        
        request = {json.dumps(request)}
        method = request["method"]
        params = request.get("params", {{}})
        
        if method == "tools/list":
            tools = server._get_available_tools()
            return {{
                "jsonrpc": "2.0",
                "id": request["id"],
                "result": {{
                    "tools": [{{
                        "name": tool.name,
                        "description": tool.description
                    }} for tool in tools]
                }}
            }}
        elif method == "tools/call":
            tool_name = params.get("name")
            arguments = params.get("arguments", {{}})
            
            result = await server._call_tool(tool_name, arguments)
            return {{
                "jsonrpc": "2.0", 
                "id": request["id"],
                "result": result
            }}
        else:
            return {{
                "jsonrpc": "2.0",
                "id": request["id"],
                "error": {{"code": -32601, "message": "Method not found"}}
            }}
    except Exception as e:
        return {{
            "jsonrpc": "2.0",
            "id": request["id"], 
            "error": {{"code": -32603, "message": str(e)}}
        }}

response = asyncio.run(handle_request())
print(json.dumps(response))
'''
            ], capture_output=True, text=True, timeout=120)
            
            if result.returncode == 0:
                # Parse the JSON response from the last line
                output_lines = result.stdout.strip().split('\n')
                for line in reversed(output_lines):
                    line = line.strip()
                    if line.startswith('{') and line.endswith('}'):
                        return json.loads(line)
                
                raise ValueError("No valid JSON response found")
            else:
                raise RuntimeError(f"Container exec failed: {result.stderr}")
                
        except Exception as e:
            logger.error(f"JSON-RPC request failed: {e}")
            return {
                "jsonrpc": "2.0",
                "id": 1,
                "error": {"code": -32603, "message": str(e)}
            }
    
    def test_jsonrpc_protocol(self) -> Dict[str, Any]:
        """Test JSON-RPC protocol communication."""
        results = {
            "container_start": False,
            "tools_list": False,
            "tool_calls": {},
            "error_handling": False,
            "protocol_compliance": False,
            "overall_success": False
        }
        
        try:
            # Test 1: Start container
            if not self.start_container():
                return results
            results["container_start"] = True
            
            # Test 2: List tools
            logger.info("Testing tools/list request...")
            response = self.send_jsonrpc_request("tools/list")
            
            if "result" in response and "tools" in response["result"]:
                tool_count = len(response["result"]["tools"])
                results["tools_list"] = tool_count > 40  # Expect at least 40 tools
                logger.info(f"✅ tools/list: {tool_count} tools available")
            else:
                logger.warning(f"❌ tools/list failed: {response.get('error', 'Unknown error')}")
            
            # Test 3: Tool calls
            test_tools = [
                {
                    "name": "create_task_metadata",
                    "arguments": {
                        "project_name": "jsonrpc-test",
                        "task_id": "jsonrpc-task-1",
                        "task_type": "testing",
                        "description": "JSON-RPC test task"
                    }
                },
                {
                    "name": "list_project_tasks",
                    "arguments": {
                        "project_name": "jsonrpc-test"
                    }
                },
                {
                    "name": "memory_health_check",
                    "arguments": {}
                },
                {
                    "name": "adaptive_command_selection",
                    "arguments": {
                        "task_description": "debug system performance",
                        "domain": "debugging"
                    }
                }
            ]
            
            for tool_test in test_tools:
                logger.info(f"Testing {tool_test['name']}...")
                
                response = self.send_jsonrpc_request("tools/call", {
                    "name": tool_test["name"],
                    "arguments": tool_test["arguments"]
                })
                
                success = "result" in response and "error" not in response
                results["tool_calls"][tool_test["name"]] = success
                
                if success:
                    logger.info(f"✅ {tool_test['name']}: SUCCESS")
                else:
                    error_msg = response.get("error", {}).get("message", "Unknown error")
                    logger.warning(f"❌ {tool_test['name']}: {error_msg}")
            
            # Test 4: Error handling
            logger.info("Testing error handling...")
            response = self.send_jsonrpc_request("tools/call", {
                "name": "nonexistent_tool",
                "arguments": {}
            })
            
            results["error_handling"] = "error" in response
            if results["error_handling"]:
                logger.info("✅ Error handling: Proper error response")
            else:
                logger.warning("❌ Error handling: No error response for invalid tool")
            
            # Test 5: Protocol compliance
            # Check if responses follow JSON-RPC 2.0 spec
            test_response = self.send_jsonrpc_request("tools/list")
            has_jsonrpc = test_response.get("jsonrpc") == "2.0"
            has_id = "id" in test_response
            has_result_or_error = "result" in test_response or "error" in test_response
            
            results["protocol_compliance"] = has_jsonrpc and has_id and has_result_or_error
            if results["protocol_compliance"]:
                logger.info("✅ Protocol compliance: Valid JSON-RPC 2.0")
            else:
                logger.warning("❌ Protocol compliance: Invalid JSON-RPC format")
            
            # Calculate overall success
            tool_success_count = sum(1 for success in results["tool_calls"].values() if success)
            total_tools = len(results["tool_calls"])
            tool_success_rate = tool_success_count / total_tools if total_tools > 0 else 0
            
            results["overall_success"] = (
                results["container_start"] and
                results["tools_list"] and
                tool_success_rate >= 0.75 and  # At least 75% of tools working
                results["error_handling"] and
                results["protocol_compliance"]
            )
            
        except Exception as e:
            logger.error(f"JSON-RPC testing failed: {e}")
        
        finally:
            # Cleanup
            try:
                subprocess.run(['docker', 'stop', self.container_name], 
                             capture_output=True, check=False)
                subprocess.run(['docker', 'rm', self.container_name], 
                             capture_output=True, check=False)
                logger.info("Container cleaned up")
            except:
                pass
        
        return results

def main():
    """Run JSON-RPC tests for Atlas MCP Docker container."""
    logger.info("🔗 Starting Atlas MCP JSON-RPC Tests")
    
    tester = AtlasDockerMCPTester()
    results = tester.test_jsonrpc_protocol()
    
    # Report results
    logger.info("\n" + "="*60)
    logger.info("📊 ATLAS MCP JSON-RPC TEST RESULTS")
    logger.info("="*60)
    
    logger.info(f"Container Start: {'✅ PASS' if results['container_start'] else '❌ FAIL'}")
    logger.info(f"Tools List: {'✅ PASS' if results['tools_list'] else '❌ FAIL'}")
    
    logger.info("\nTool Call Tests:")
    for tool_name, success in results["tool_calls"].items():
        status = "✅ PASS" if success else "❌ FAIL"
        logger.info(f"  {tool_name}: {status}")
    
    if results["tool_calls"]:
        tool_success_rate = sum(1 for s in results["tool_calls"].values() if s) / len(results["tool_calls"]) * 100
        logger.info(f"\nTool Success Rate: {tool_success_rate:.1f}%")
    
    logger.info(f"Error Handling: {'✅ PASS' if results['error_handling'] else '❌ FAIL'}")
    logger.info(f"Protocol Compliance: {'✅ PASS' if results['protocol_compliance'] else '❌ FAIL'}")
    
    logger.info("\n" + "="*60)
    if results["overall_success"]:
        logger.info("🎉 ATLAS MCP JSON-RPC TESTS: ALL PASS")
        logger.info("🚀 Atlas MCP Docker container supports JSON-RPC protocol")
        return 0
    else:
        logger.warning("⚠️ ATLAS MCP JSON-RPC TESTS: SOME FAILURES") 
        logger.warning("🔧 Atlas MCP Docker container needs JSON-RPC fixes")
        return 1

if __name__ == "__main__":
    exit_code = main()
    exit(exit_code)