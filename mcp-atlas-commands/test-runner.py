#!/usr/bin/env python3
"""
ATLAS MCP Test Runner - Automated testing framework for ATLAS MCP integration
"""

import json
import time
import asyncio
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime
import subprocess
import sys
import os

# Import the working MCP client
from mcp_client_working import AtlasMcpClient

@dataclass
class TestResult:
    test_id: str
    description: str
    status: str  # "passed", "failed", "skipped"
    execution_time: float
    error: Optional[str] = None
    response: Optional[Dict[str, Any]] = None
    timestamp: str = ""

class AtlasMcpTestRunner:
    def __init__(self, container_name: str = "atlas-commands-mcp"):
        self.container_name = container_name
        self.client = AtlasMcpClient(container_name)
        self.results: List[TestResult] = []
        self.setup_logging()
        
    def setup_logging(self):
        """Setup logging for test execution."""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('atlas_mcp_tests.log'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)

    def run_basic_connectivity_tests(self) -> bool:
        """Run basic connectivity and tool availability tests."""
        self.logger.info("🚀 Starting basic connectivity tests...")
        
        # Test 1: MCP initialization
        start_time = time.time()
        try:
            if not self.client.start_session():
                self.add_result("connectivity_001", "MCP initialization", "failed", 
                              time.time() - start_time, "Failed to initialize MCP session")
                return False
            
            self.add_result("connectivity_001", "MCP initialization", "passed", 
                          time.time() - start_time)
            
        except Exception as e:
            self.add_result("connectivity_001", "MCP initialization", "failed",
                          time.time() - start_time, str(e))
            return False
        
        # Test 2: List all tools
        start_time = time.time()
        try:
            tools_response = self.client.list_tools()
            if tools_response and "result" in tools_response:
                tool_count = len(tools_response["result"]["tools"])
                self.logger.info(f"✅ Found {tool_count} tools")
                self.add_result("connectivity_002", f"List tools ({tool_count} found)", 
                              "passed", time.time() - start_time, response=tools_response)
                
                # Verify we have expected tool count (49 tools)
                if tool_count < 40:  # Allow some flexibility
                    self.logger.warning(f"⚠️  Expected ~49 tools, found {tool_count}")
            else:
                self.add_result("connectivity_002", "List tools", "failed",
                              time.time() - start_time, "No tools returned")
                return False
                
        except Exception as e:
            self.add_result("connectivity_002", "List tools", "failed",
                          time.time() - start_time, str(e))
            return False
        
        return True

    def run_task_management_tests(self) -> bool:
        """Run task management functionality tests."""
        self.logger.info("📋 Starting task management tests...")
        
        # Test 1: Create hierarchical task
        start_time = time.time()
        try:
            response = self.client.call_tool("create_hierarchical_task", {
                "project_name": "Software-Engineer-AI-Agent-Atlas",
                "task_id": f"test-task-{int(time.time())}",
                "title": "Test Task Creation",
                "description": "Automated test task for MCP integration",
                "priority": "medium",
                "category": "testing"
            })
            
            if response and "result" in response:
                self.add_result("task_001", "Create hierarchical task", "passed",
                              time.time() - start_time, response=response)
            else:
                self.add_result("task_001", "Create hierarchical task", "failed",
                              time.time() - start_time, "No valid response")
                return False
                
        except Exception as e:
            self.add_result("task_001", "Create hierarchical task", "failed",
                          time.time() - start_time, str(e))
            return False

        # Test 2: List project tasks
        start_time = time.time()
        try:
            response = self.client.call_tool("list_project_tasks", {
                "project_name": "Software-Engineer-AI-Agent-Atlas"
            })
            
            if response and "result" in response:
                self.add_result("task_002", "List project tasks", "passed",
                              time.time() - start_time, response=response)
            else:
                self.add_result("task_002", "List project tasks", "failed",
                              time.time() - start_time, "No valid response")
                
        except Exception as e:
            self.add_result("task_002", "List project tasks", "failed",
                          time.time() - start_time, str(e))
        
        return True

    def run_memory_graph_tests(self) -> bool:
        """Run memory graph functionality tests."""
        self.logger.info("🧠 Starting memory graph tests...")
        
        # Test 1: Create memory entity
        start_time = time.time()
        try:
            response = self.client.call_tool("create_memory_entity", {
                "name": f"TestEntity_{int(time.time())}",
                "entity_type": "TestComponent",
                "observations": [
                    "This is a test entity created during MCP integration testing",
                    "Entity created successfully through MCP client"
                ]
            })
            
            if response and "result" in response:
                self.add_result("memory_001", "Create memory entity", "passed",
                              time.time() - start_time, response=response)
            else:
                self.add_result("memory_001", "Create memory entity", "failed",
                              time.time() - start_time, "No valid response")
                return False
                
        except Exception as e:
            self.add_result("memory_001", "Create memory entity", "failed",
                          time.time() - start_time, str(e))
            return False
        
        return True

    def run_workflow_tests(self) -> bool:
        """Run workflow orchestration tests."""
        self.logger.info("⚙️ Starting workflow tests...")
        
        # Test 1: Adaptive command selection
        start_time = time.time()
        try:
            response = self.client.call_tool("adaptive_command_selection", {
                "current_context": {
                    "project_type": "mcp_integration",
                    "phase": "testing",
                    "last_action": "created_test_task"
                },
                "user_intent": "Continue testing MCP integration",
                "max_suggestions": 3
            })
            
            if response and "result" in response:
                self.add_result("workflow_001", "Adaptive command selection", "passed",
                              time.time() - start_time, response=response)
            else:
                self.add_result("workflow_001", "Adaptive command selection", "failed",
                              time.time() - start_time, "No valid response")
                
        except Exception as e:
            self.add_result("workflow_001", "Adaptive command selection", "failed",
                          time.time() - start_time, str(e))
        
        return True

    def run_performance_tests(self) -> bool:
        """Run performance and monitoring tests."""
        self.logger.info("📊 Starting performance tests...")
        
        # Test 1: Get cache stats
        start_time = time.time()
        try:
            response = self.client.call_tool("get_cache_stats", {
                "include_breakdown": True
            })
            
            if response and "result" in response:
                self.add_result("performance_001", "Get cache stats", "passed",
                              time.time() - start_time, response=response)
            else:
                self.add_result("performance_001", "Get cache stats", "failed",
                              time.time() - start_time, "No valid response")
                
        except Exception as e:
            self.add_result("performance_001", "Get cache stats", "failed",
                          time.time() - start_time, str(e))
        
        # Test 2: Memory health check
        start_time = time.time()
        try:
            response = self.client.call_tool("memory_health_check", {})
            
            if response and "result" in response:
                self.add_result("performance_002", "Memory health check", "passed",
                              time.time() - start_time, response=response)
            else:
                self.add_result("performance_002", "Memory health check", "failed",
                              time.time() - start_time, "No valid response")
                
        except Exception as e:
            self.add_result("performance_002", "Memory health check", "failed",
                          time.time() - start_time, str(e))
        
        return True

    def add_result(self, test_id: str, description: str, status: str, 
                   execution_time: float, error: str = None, response: Dict = None):
        """Add test result to results list."""
        result = TestResult(
            test_id=test_id,
            description=description,
            status=status,
            execution_time=execution_time,
            error=error,
            response=response,
            timestamp=datetime.now().isoformat()
        )
        self.results.append(result)

    def run_full_test_suite(self):
        """Run complete test suite."""
        self.logger.info("🎯 Starting ATLAS MCP Full Test Suite")
        self.logger.info("=" * 60)
        
        test_phases = [
            ("Basic Connectivity", self.run_basic_connectivity_tests),
            ("Task Management", self.run_task_management_tests),
            ("Memory Graph", self.run_memory_graph_tests),
            ("Workflow Orchestration", self.run_workflow_tests),
            ("Performance Monitoring", self.run_performance_tests)
        ]
        
        total_start_time = time.time()
        
        for phase_name, test_function in test_phases:
            self.logger.info(f"\n📍 Phase: {phase_name}")
            phase_start = time.time()
            
            try:
                success = test_function()
                phase_time = time.time() - phase_start
                
                if success:
                    self.logger.info(f"✅ {phase_name} completed in {phase_time:.2f}s")
                else:
                    self.logger.error(f"❌ {phase_name} failed in {phase_time:.2f}s")
                    
            except Exception as e:
                phase_time = time.time() - phase_start
                self.logger.error(f"💥 {phase_name} crashed in {phase_time:.2f}s: {e}")
        
        total_time = time.time() - total_start_time
        self.logger.info(f"\n🏁 Test suite completed in {total_time:.2f}s")
        
        # Generate summary
        self.generate_test_report()

    def generate_test_report(self):
        """Generate comprehensive test report."""
        passed = len([r for r in self.results if r.status == "passed"])
        failed = len([r for r in self.results if r.status == "failed"])
        total = len(self.results)
        
        self.logger.info("\n" + "="*60)
        self.logger.info("📊 TEST SUMMARY REPORT")
        self.logger.info("="*60)
        self.logger.info(f"Total Tests: {total}")
        self.logger.info(f"Passed: {passed} ✅")
        self.logger.info(f"Failed: {failed} ❌")
        self.logger.info(f"Success Rate: {(passed/total*100):.1f}%")
        
        if failed > 0:
            self.logger.info("\n❌ FAILED TESTS:")
            for result in self.results:
                if result.status == "failed":
                    self.logger.info(f"  - {result.test_id}: {result.description}")
                    if result.error:
                        self.logger.info(f"    Error: {result.error}")
        
        # Save detailed results to JSON
        self.save_results_to_file()

    def save_results_to_file(self):
        """Save test results to JSON file."""
        results_data = {
            "test_run": {
                "timestamp": datetime.now().isoformat(),
                "container": self.container_name,
                "total_tests": len(self.results),
                "passed": len([r for r in self.results if r.status == "passed"]),
                "failed": len([r for r in self.results if r.status == "failed"])
            },
            "results": [
                {
                    "test_id": r.test_id,
                    "description": r.description,
                    "status": r.status,
                    "execution_time": r.execution_time,
                    "error": r.error,
                    "timestamp": r.timestamp
                } for r in self.results
            ]
        }
        
        filename = f"atlas_mcp_test_results_{int(time.time())}.json"
        with open(filename, 'w') as f:
            json.dump(results_data, f, indent=2)
        
        self.logger.info(f"📄 Detailed results saved to: {filename}")

    def apply_quick_fixes(self):
        """Apply automated fixes for common issues."""
        self.logger.info("🔧 Applying quick fixes...")
        
        # Check container health
        result = subprocess.run(
            ["docker", "ps", "--filter", f"name={self.container_name}", "--format", "{{.Status}}"],
            capture_output=True, text=True
        )
        
        if "healthy" not in result.stdout:
            self.logger.info("🔄 Restarting unhealthy container...")
            subprocess.run(["docker", "restart", self.container_name])
            time.sleep(10)
        
        # Clear caches if needed
        try:
            self.client.call_tool("clear_all_cache", {})
            self.logger.info("🧹 Cache cleared")
        except:
            self.logger.warning("⚠️  Could not clear cache")

    def cleanup(self):
        """Cleanup test session."""
        if self.client:
            self.client.close_session()

def main():
    """Main test execution."""
    if len(sys.argv) > 1:
        container_name = sys.argv[1]
    else:
        container_name = "atlas-commands-mcp"
    
    runner = AtlasMcpTestRunner(container_name)
    
    try:
        # Check if we should apply fixes first
        if "--fix" in sys.argv:
            runner.apply_quick_fixes()
            time.sleep(5)
        
        # Run tests
        if "--quick" in sys.argv:
            runner.run_basic_connectivity_tests()
        else:
            runner.run_full_test_suite()
            
    except KeyboardInterrupt:
        runner.logger.info("\n🛑 Test run interrupted by user")
    except Exception as e:
        runner.logger.error(f"💥 Test runner crashed: {e}")
    finally:
        runner.cleanup()

if __name__ == "__main__":
    main()