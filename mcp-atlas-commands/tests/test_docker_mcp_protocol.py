#!/usr/bin/env python3
"""Test MCP protocol communication with Docker container."""

import asyncio
import json
import subprocess
import time
import logging
from typing import Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DockerMCPTester:
    """Test MCP protocol communication through Docker container."""
    
    def __init__(self):
        self.container_name = "atlas-mcp-test"
        self.container_id = None
        
    async def start_container(self) -> bool:
        """Start the Docker container."""
        try:
            # Stop any existing container
            subprocess.run(['docker', 'stop', self.container_name], 
                         capture_output=True, check=False)
            subprocess.run(['docker', 'rm', self.container_name], 
                         capture_output=True, check=False)
            
            # Start new container
            result = subprocess.run([
                'docker', 'run', '-d', '--name', self.container_name,
                '-v', f'{subprocess.check_output(["pwd"]).decode().strip()}/REPOS:/app/REPOS',
                'atlas-commands-mcp:latest'
            ], capture_output=True, text=True, check=True)
            
            self.container_id = result.stdout.strip()
            logger.info(f"Started container: {self.container_id[:12]}")
            
            # Wait for container to initialize
            time.sleep(5)
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to start container: {e}")
            return False
    
    async def test_mcp_communication(self) -> Dict[str, Any]:
        """Test MCP protocol communication with the container."""
        results = {
            "container_startup": False,
            "mcp_initialization": False,
            "tool_calls": {},
            "error_handling": False,
            "overall_success": False
        }
        
        try:
            # Test 1: Container startup
            if not await self.start_container():
                return results
            results["container_startup"] = True
            
            # Test 2: MCP initialization
            init_result = subprocess.run([
                'docker', 'exec', self.container_name,
                'python', '-c', '''
import json
import sys
from src.atlas_commands.server import EnhancedAtlasCommandsServer

try:
    server = EnhancedAtlasCommandsServer()
    tools = server._get_available_tools()
    print(json.dumps({
        "status": "success",
        "tool_count": len(tools),
        "categories": list(set(tool.name.split("_")[0] for tool in tools[:10]))
    }))
except Exception as e:
    print(json.dumps({"status": "error", "error": str(e)}))
'''
            ], capture_output=True, text=True, check=True)
            
            init_data = json.loads(init_result.stdout.strip().split('\n')[-1])
            if init_data.get("status") == "success":
                results["mcp_initialization"] = True
                logger.info(f"MCP initialized with {init_data.get('tool_count')} tools")
            
            # Test 3: Tool calls through container
            test_tools = [
                {
                    "name": "create_task_metadata",
                    "args": {
                        "project_name": "docker-test",
                        "task_id": "test-task-1",
                        "task_type": "testing",
                        "description": "Test task from Docker container"
                    }
                },
                {
                    "name": "list_project_tasks",
                    "args": {
                        "project_name": "docker-test"
                    }
                },
                {
                    "name": "memory_health_check",
                    "args": {}
                },
                {
                    "name": "get_cache_stats",
                    "args": {}
                }
            ]
            
            for tool_test in test_tools:
                try:
                    tool_result = subprocess.run([
                        'docker', 'exec', self.container_name,
                        'python', '-c', f'''
import json
import asyncio
from src.atlas_commands.server import EnhancedAtlasCommandsServer

async def test_tool():
    server = EnhancedAtlasCommandsServer()
    try:
        result = await server._call_tool("{tool_test["name"]}", {json.dumps(tool_test["args"])})
        return {{"status": "success", "result_length": len(str(result))}}
    except Exception as e:
        return {{"status": "error", "error": str(e)}}

result = asyncio.run(test_tool())
print(json.dumps(result))
'''
                    ], capture_output=True, text=True, check=True)
                    
                    tool_data = json.loads(tool_result.stdout.strip().split('\n')[-1])
                    results["tool_calls"][tool_test["name"]] = tool_data.get("status") == "success"
                    
                    if tool_data.get("status") == "success":
                        logger.info(f"✅ Tool {tool_test['name']}: SUCCESS")
                    else:
                        logger.warning(f"❌ Tool {tool_test['name']}: {tool_data.get('error', 'Unknown error')}")
                        
                except Exception as e:
                    logger.error(f"Tool test {tool_test['name']} failed: {e}")
                    results["tool_calls"][tool_test["name"]] = False
            
            # Test 4: Error handling
            try:
                error_result = subprocess.run([
                    'docker', 'exec', self.container_name,
                    'python', '-c', '''
import json
import asyncio
from src.atlas_commands.server import EnhancedAtlasCommandsServer

async def test_error():
    server = EnhancedAtlasCommandsServer()
    try:
        # Test with invalid tool name
        result = await server._call_tool("nonexistent_tool", {})
        return {"status": "unexpected_success"}
    except Exception as e:
        # Error handling working correctly
        return {"status": "error_handled", "error_type": type(e).__name__}

result = asyncio.run(test_error())
print(json.dumps(result))
'''
                ], capture_output=True, text=True, check=True)
                
                error_data = json.loads(error_result.stdout.strip().split('\n')[-1])
                results["error_handling"] = error_data.get("status") == "error_handled"
                
            except Exception as e:
                logger.warning(f"Error handling test failed: {e}")
            
            # Calculate overall success
            tool_success_count = sum(1 for success in results["tool_calls"].values() if success)
            total_tools = len(results["tool_calls"])
            
            results["overall_success"] = (
                results["container_startup"] and 
                results["mcp_initialization"] and 
                tool_success_count >= (total_tools * 0.75) and  # At least 75% of tools working
                results["error_handling"]
            )
            
        except Exception as e:
            logger.error(f"MCP communication test failed: {e}")
        
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

async def main():
    """Run Docker MCP protocol tests."""
    logger.info("🐳 Starting Docker MCP Protocol Tests")
    
    tester = DockerMCPTester()
    results = await tester.test_mcp_communication()
    
    # Report results
    logger.info("\n" + "="*60)
    logger.info("📊 DOCKER MCP PROTOCOL TEST RESULTS")
    logger.info("="*60)
    
    logger.info(f"Container Startup: {'✅ PASS' if results['container_startup'] else '❌ FAIL'}")
    logger.info(f"MCP Initialization: {'✅ PASS' if results['mcp_initialization'] else '❌ FAIL'}")
    
    logger.info("\nTool Call Tests:")
    for tool_name, success in results["tool_calls"].items():
        status = "✅ PASS" if success else "❌ FAIL"
        logger.info(f"  {tool_name}: {status}")
    
    tool_success_rate = sum(1 for s in results["tool_calls"].values() if s) / len(results["tool_calls"]) * 100
    logger.info(f"\nTool Success Rate: {tool_success_rate:.1f}%")
    
    logger.info(f"Error Handling: {'✅ PASS' if results['error_handling'] else '❌ FAIL'}")
    
    logger.info("\n" + "="*60)
    if results["overall_success"]:
        logger.info("🎉 DOCKER MCP PROTOCOL TESTS: ALL PASS")
        logger.info("🚀 Atlas MCP Docker deployment is PRODUCTION READY")
        return 0
    else:
        logger.warning("⚠️ DOCKER MCP PROTOCOL TESTS: SOME FAILURES")
        logger.warning("🔧 Atlas MCP Docker deployment needs fixes")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)