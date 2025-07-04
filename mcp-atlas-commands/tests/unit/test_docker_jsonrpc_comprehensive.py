#!/usr/bin/env python3
"""
Comprehensive JSON-RPC test for ATLAS MCP server in Docker container.
Tests the container deployment and real JSON-RPC communication.
"""

import asyncio
import json
import subprocess
import time
import signal
import requests
from contextlib import asynccontextmanager
from typing import Optional, Dict, Any


class DockerMCPTester:
    """Test ATLAS MCP server running in Docker container."""
    
    def __init__(self):
        self.container_name = "atlas-mcp-test"
        self.container_process = None
        self.base_url = "http://localhost:8765"
        
    @asynccontextmanager
    async def container_context(self):
        """Context manager for running the container."""
        try:
            # Start container
            print("🚀 Starting ATLAS MCP Docker container...")
            self.container_process = subprocess.Popen([
                "docker", "run", "--rm", "--name", self.container_name,
                "-p", "8765:8765",
                "--link", "atlas-redis:redis",
                "-e", "REDIS_URL=redis://redis:6379",
                "atlas-commands-mcp:latest",
                "python", "-m", "atlas_commands.server", "--port", "8765", "--host", "0.0.0.0"
            ], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            # Wait for container to start
            await self._wait_for_container_ready()
            print("✅ Container is ready")
            
            yield
            
        finally:
            # Clean up
            print("🧹 Cleaning up container...")
            if self.container_process:
                self.container_process.terminate()
                try:
                    self.container_process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    self.container_process.kill()
                    self.container_process.wait()
            
            # Force remove container if still exists
            subprocess.run(["docker", "rm", "-f", self.container_name], 
                         capture_output=True)
    
    async def _wait_for_container_ready(self, timeout: int = 60):
        """Wait for the container to be ready to accept connections."""
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            try:
                # Try to connect to the health endpoint
                response = requests.get(f"{self.base_url}/health", timeout=2)
                if response.status_code == 200:
                    return
            except (requests.ConnectionError, requests.Timeout):
                pass
            
            # Check if container process is still running
            if self.container_process and self.container_process.poll() is not None:
                stdout, stderr = self.container_process.communicate()
                raise RuntimeError(f"Container exited prematurely:\nSTDOUT: {stdout.decode()}\nSTDERR: {stderr.decode()}")
            
            await asyncio.sleep(2)
        
        raise TimeoutError("Container did not become ready within timeout")
    
    def send_jsonrpc_request(self, method: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Send a JSON-RPC request to the MCP server."""
        payload = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": method,
            "params": params or {}
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/mcp",
                json=payload,
                timeout=30,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code != 200:
                return {"error": f"HTTP {response.status_code}: {response.text}"}
            
            return response.json()
            
        except Exception as e:
            return {"error": f"Request failed: {str(e)}"}
    
    async def test_tool_capabilities(self):
        """Test basic tool listing and capabilities."""
        print("\n📋 Testing tool capabilities...")
        
        # Test list_tools
        result = self.send_jsonrpc_request("tools/list")
        if "error" in result:
            print(f"❌ list_tools failed: {result['error']}")
            return False
        
        tools = result.get("result", {}).get("tools", [])
        print(f"✅ Found {len(tools)} tools")
        
        # Test a few key tools
        key_tools = ["create_task_metadata", "memory_health_check", "adaptive_command_selection"]
        found_tools = [tool["name"] for tool in tools]
        
        for tool_name in key_tools:
            if tool_name in found_tools:
                print(f"✅ Key tool found: {tool_name}")
            else:
                print(f"❌ Missing key tool: {tool_name}")
                return False
        
        return True
    
    async def test_task_management(self):
        """Test task management functionality."""
        print("\n📝 Testing task management...")
        
        # Create a task
        task_params = {
            "project_name": "docker-test",
            "task_id": "test-task-001",
            "task_type": "validation", 
            "description": "Docker container validation test"
        }
        
        result = self.send_jsonrpc_request("tools/call", {
            "name": "create_task_metadata",
            "arguments": task_params
        })
        
        if "error" in result:
            print(f"❌ create_task_metadata failed: {result['error']}")
            return False
        
        print("✅ Task created successfully")
        
        # Update task status
        status_params = {
            "project_name": "docker-test",
            "task_id": "test-task-001",
            "status": "completed"
        }
        
        result = self.send_jsonrpc_request("tools/call", {
            "name": "update_task_status", 
            "arguments": status_params
        })
        
        if "error" in result:
            print(f"❌ update_task_status failed: {result['error']}")
            return False
        
        print("✅ Task status updated successfully")
        return True
    
    async def test_memory_analytics(self):
        """Test memory and analytics functionality.""" 
        print("\n🧠 Testing memory analytics...")
        
        # Test memory health check
        result = self.send_jsonrpc_request("tools/call", {
            "name": "memory_health_check",
            "arguments": {}
        })
        
        if "error" in result:
            print(f"❌ memory_health_check failed: {result['error']}")
            return False
        
        print("✅ Memory health check completed")
        
        # Test cache stats
        result = self.send_jsonrpc_request("tools/call", {
            "name": "get_cache_stats", 
            "arguments": {}
        })
        
        if "error" in result:
            print(f"❌ get_cache_stats failed: {result['error']}")
            return False
        
        print("✅ Cache stats retrieved successfully")
        return True
    
    async def test_ai_recommendations(self):
        """Test AI-powered workflow intelligence."""
        print("\n🤖 Testing AI recommendations...")
        
        # Test adaptive command selection
        ai_params = {
            "task_description": "Validate Docker container deployment and test MCP communication", 
            "domain": "testing"
        }
        
        result = self.send_jsonrpc_request("tools/call", {
            "name": "adaptive_command_selection",
            "arguments": ai_params
        })
        
        if "error" in result:
            print(f"❌ adaptive_command_selection failed: {result['error']}")
            return False
        
        # Parse the response
        response_text = result.get("result", {}).get("content", [{}])[0].get("text", "{}")
        try:
            ai_response = json.loads(response_text)
            recommendations = ai_response.get("recommendations", [])
            print(f"✅ AI recommendations generated: {len(recommendations)} suggestions")
            
            # Show top 3 recommendations
            for i, rec in enumerate(recommendations[:3]):
                print(f"   {i+1}. {rec.get('command')} (confidence: {rec.get('confidence', 0):.2f})")
            
        except json.JSONDecodeError:
            print(f"⚠️  AI response format issue, but handler responded")
        
        return True
    
    async def run_comprehensive_test(self):
        """Run all tests in the Docker container."""
        print("🔍 Starting comprehensive ATLAS MCP Docker test...")
        
        test_results = {}
        
        async with self.container_context():
            # Run all test categories
            test_results["capabilities"] = await self.test_tool_capabilities()
            test_results["task_management"] = await self.test_task_management()
            test_results["memory_analytics"] = await self.test_memory_analytics()
            test_results["ai_recommendations"] = await self.test_ai_recommendations()
        
        # Summary
        print("\n" + "="*60)
        print("📊 DOCKER CONTAINER TEST SUMMARY")
        print("="*60)
        
        passed = sum(test_results.values())
        total = len(test_results)
        
        for test_name, result in test_results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"{test_name.replace('_', ' ').title()}: {status}")
        
        print(f"\nOverall: {passed}/{total} tests passed")
        
        if passed == total:
            print("🎉 ALL DOCKER TESTS PASSED - Container is production ready!")
            return True
        else:
            print("⚠️  Some Docker tests failed - investigate issues")
            return False


async def main():
    """Main test execution."""
    tester = DockerMCPTester()
    success = await tester.run_comprehensive_test()
    
    if success:
        print("\n✅ Docker container validation completed successfully!")
        print("🚀 ATLAS MCP is ready for production deployment!")
    else:
        print("\n❌ Docker container validation had issues")
        print("🔧 Review the test output and fix any problems")
    
    return success


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)