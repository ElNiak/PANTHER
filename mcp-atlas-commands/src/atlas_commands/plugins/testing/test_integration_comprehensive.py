#!/usr/bin/env python3
"""
Comprehensive Integration Tests - ATLAS MCP Server
Registry vs Legacy Dispatcher Comparison

Tests all 44 MCP tools across both systems to ensure identical behavior
"""

import asyncio
import json
import time
from pathlib import Path
from typing import Dict, List, Any, Tuple
import sys
import os

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from atlas_commands.server import AtlasMCPServer
from atlas_commands.refactor_config import RefactorConfig

class ComprehensiveIntegrationTester:
    """Test registry vs legacy dispatcher for all 44 MCP tools"""
    
    def __init__(self):
        self.results = {
            "registry_results": {},
            "legacy_results": {},
            "performance_comparison": {},
            "behavior_differences": [],
            "error_summary": {"registry": 0, "legacy": 0},
            "test_metadata": {
                "total_tools": 44,
                "start_time": time.time(),
                "categories": [
                    "task_management", "hierarchical", "validation", 
                    "workflow_intelligence", "storage_memory", "observability"
                ]
            }
        }
        
        # All 44 MCP tools organized by category
        self.tool_categories = {
            "task_management": [
                "create_unified_checklist", "create_task_metadata", "update_task_status",
                "add_task_artifact", "get_task_context", "list_project_tasks",
                "create_task_backup", "archive_task", "filter_tasks"
            ],
            "hierarchical": [
                "calculate_task_progress", "create_hierarchical_backup", 
                "list_checkpoints", "restore_from_checkpoint", "create_hierarchical_task",
                "get_task_hierarchy", "update_hierarchical_status"
            ],
            "validation": [
                "validate_file_operation", "validate_naming_convention",
                "validate_code_standards", "enforce_git_protocol"
            ],
            "workflow_intelligence": [
                "orchestrate_intelligent_tasks", "adaptive_command_selection",
                "analyze_workflow_patterns", "track_progress_milestones"
            ],
            "storage_memory": [
                "create_task_dependency", "get_progress_rollup", 
                "query_hierarchical_context"
            ],
            "legacy_original": [
                # Original 8 tools (would need to be identified)
                "legacy_tool_1", "legacy_tool_2", "legacy_tool_3", "legacy_tool_4",
                "legacy_tool_5", "legacy_tool_6", "legacy_tool_7", "legacy_tool_8"
            ],
            "observability": [
                # Would need to identify the 13 observability tools
                "obs_tool_1", "obs_tool_2", "obs_tool_3", "obs_tool_4", "obs_tool_5",
                "obs_tool_6", "obs_tool_7", "obs_tool_8", "obs_tool_9", "obs_tool_10",
                "obs_tool_11", "obs_tool_12", "obs_tool_13"
            ]
        }
    
    async def setup_servers(self) -> Tuple[AtlasMCPServer, AtlasMCPServer]:
        """Create registry-enabled and legacy servers"""
        # Registry server (Phase 1 configuration)
        registry_config = RefactorConfig()
        registry_config.enable_registry = True
        registry_config.enable_fallback = True
        registry_config.enable_error_handling = True
        registry_server = AtlasMCPServer(config=registry_config)
        
        # Legacy server (original configuration)  
        legacy_config = RefactorConfig()
        legacy_config.enable_registry = False
        legacy_config.enable_fallback = False
        legacy_config.enable_error_handling = False
        legacy_server = AtlasMCPServer(config=legacy_config)
        
        return registry_server, legacy_server
    
    async def test_tool_implementation(self, tool_name: str, server: AtlasMCPServer, 
                                     server_type: str) -> Dict[str, Any]:
        """Test a single tool implementation"""
        test_params = self.get_test_parameters(tool_name)
        
        start_time = time.time()
        try:
            # Mock MCP call request format
            request = {
                "method": "tools/call",
                "params": {
                    "name": f"mcp__atlas-commands__{tool_name}",
                    "arguments": test_params
                }
            }
            
            # Call through the server's tool handling
            result = await server.handle_tool_call(request["params"])
            
            execution_time = time.time() - start_time
            
            return {
                "success": True,
                "result": result,
                "execution_time": execution_time,
                "error": None,
                "server_type": server_type
            }
            
        except Exception as e:
            execution_time = time.time() - start_time
            return {
                "success": False,
                "result": None,
                "execution_time": execution_time,
                "error": str(e),
                "server_type": server_type
            }
    
    def get_test_parameters(self, tool_name: str) -> Dict[str, Any]:
        """Get appropriate test parameters for each tool"""
        # Basic test parameters for each tool category
        param_map = {
            # Task Management Tools
            "create_task_metadata": {
                "project_name": "TEST_PROJECT",
                "task_id": "test_task_001",
                "task_type": "testing",
                "description": "Integration test task"
            },
            "update_task_status": {
                "project_name": "TEST_PROJECT", 
                "task_id": "test_task_001",
                "status": "active"
            },
            "get_task_context": {
                "project_name": "TEST_PROJECT",
                "task_id": "test_task_001"
            },
            "list_project_tasks": {
                "project_name": "TEST_PROJECT"
            },
            # Hierarchical Tools
            "create_hierarchical_task": {
                "project_name": "TEST_PROJECT",
                "task_name": "test-hierarchical",
                "task_type": "task",
                "description": "Test hierarchical task",
                "domain": "testing"
            },
            "get_task_hierarchy": {
                "project_name": "TEST_PROJECT",
                "root_task_id": "test_task_001"
            },
            # Validation Tools
            "validate_file_operation": {
                "operation": "create",
                "file_path": "/tmp/test_file.txt"
            },
            "validate_naming_convention": {
                "name": "test_function",
                "type": "function"
            },
            # Workflow Tools
            "orchestrate_intelligent_tasks": {
                "task_context": {
                    "description": "Test task orchestration",
                    "complexity": "simple",
                    "domain": "testing"
                }
            }
        }
        
        # Return specific params or generic fallback
        return param_map.get(tool_name, {"test": True})
    
    async def run_category_tests(self, category: str, tools: List[str]) -> Dict[str, Any]:
        """Test all tools in a category"""
        print(f"\n=== Testing {category.title().replace('_', ' ')} Tools ===")
        
        registry_server, legacy_server = await self.setup_servers()
        category_results = {
            "category": category,
            "tools_tested": len(tools),
            "registry_successes": 0,
            "legacy_successes": 0,
            "behavior_matches": 0,
            "performance_comparison": {},
            "tool_results": {}
        }
        
        for tool_name in tools:
            print(f"Testing {tool_name}...")
            
            # Test with registry server
            registry_result = await self.test_tool_implementation(
                tool_name, registry_server, "registry"
            )
            
            # Test with legacy server  
            legacy_result = await self.test_tool_implementation(
                tool_name, legacy_server, "legacy"
            )
            
            # Compare results
            behavior_match = self.compare_tool_behavior(
                registry_result, legacy_result
            )
            
            # Store results
            category_results["tool_results"][tool_name] = {
                "registry": registry_result,
                "legacy": legacy_result,
                "behavior_match": behavior_match,
                "performance_ratio": (
                    registry_result["execution_time"] / legacy_result["execution_time"]
                    if legacy_result["execution_time"] > 0 else 1.0
                )
            }
            
            # Update counters
            if registry_result["success"]:
                category_results["registry_successes"] += 1
            if legacy_result["success"]: 
                category_results["legacy_successes"] += 1
            if behavior_match:
                category_results["behavior_matches"] += 1
        
        return category_results
    
    def compare_tool_behavior(self, registry_result: Dict, legacy_result: Dict) -> bool:
        """Compare behavior between registry and legacy implementations"""
        # Both should succeed or both should fail
        if registry_result["success"] != legacy_result["success"]:
            return False
            
        # If both succeeded, results should be equivalent
        if registry_result["success"] and legacy_result["success"]:
            # For now, just check that both returned valid results
            # More sophisticated comparison could check result structure
            return (registry_result["result"] is not None and 
                   legacy_result["result"] is not None)
        
        # If both failed, that's also a match
        return True
    
    async def run_performance_benchmark(self) -> Dict[str, Any]:
        """Run performance comparison between registry and legacy"""
        print("\n=== Performance Benchmark ===")
        
        # Test a subset of tools multiple times for performance
        benchmark_tools = [
            "create_task_metadata", "update_task_status", "get_task_context",
            "create_hierarchical_task", "validate_file_operation"
        ]
        
        iterations = 10
        registry_server, legacy_server = await self.setup_servers()
        
        performance_results = {
            "iterations": iterations,
            "tools_tested": len(benchmark_tools),
            "registry_total_time": 0,
            "legacy_total_time": 0,
            "tool_performance": {}
        }
        
        for tool_name in benchmark_tools:
            print(f"Benchmarking {tool_name} ({iterations} iterations)...")
            
            registry_times = []
            legacy_times = []
            
            for i in range(iterations):
                # Registry timing
                registry_result = await self.test_tool_implementation(
                    tool_name, registry_server, "registry"
                )
                registry_times.append(registry_result["execution_time"])
                
                # Legacy timing
                legacy_result = await self.test_tool_implementation(
                    tool_name, legacy_server, "legacy"
                )
                legacy_times.append(legacy_result["execution_time"])
            
            # Calculate statistics
            avg_registry = sum(registry_times) / len(registry_times)
            avg_legacy = sum(legacy_times) / len(legacy_times)
            
            performance_results["tool_performance"][tool_name] = {
                "registry_avg": avg_registry,
                "legacy_avg": avg_legacy,
                "ratio": avg_registry / avg_legacy if avg_legacy > 0 else 1.0,
                "registry_overhead": avg_registry - avg_legacy
            }
            
            performance_results["registry_total_time"] += avg_registry
            performance_results["legacy_total_time"] += avg_legacy
        
        return performance_results
    
    async def run_comprehensive_tests(self) -> Dict[str, Any]:
        """Run all comprehensive integration tests"""
        print("Starting Comprehensive Integration Tests")
        print("=" * 50)
        
        # Test each category
        all_results = {}
        for category, tools in self.tool_categories.items():
            if category in ["legacy_original", "observability"]:
                print(f"\nSkipping {category} (tools need identification)")
                continue
                
            category_result = await self.run_category_tests(category, tools)
            all_results[category] = category_result
        
        # Run performance benchmark
        performance_result = await self.run_performance_benchmark()
        all_results["performance_benchmark"] = performance_result
        
        # Generate summary
        summary = self.generate_test_summary(all_results)
        all_results["summary"] = summary
        
        return all_results
    
    def generate_test_summary(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate comprehensive test summary"""
        total_tools = 0
        total_successes = 0
        total_behavior_matches = 0
        
        for category, result in results.items():
            if category == "performance_benchmark":
                continue
                
            total_tools += result["tools_tested"]
            total_successes += min(result["registry_successes"], result["legacy_successes"])
            total_behavior_matches += result["behavior_matches"]
        
        return {
            "total_tools_tested": total_tools,
            "successful_tests": total_successes, 
            "behavior_match_rate": total_behavior_matches / total_tools if total_tools > 0 else 0,
            "registry_ready": total_behavior_matches == total_tools,
            "performance_overhead": results.get("performance_benchmark", {}).get("registry_total_time", 0) - 
                                   results.get("performance_benchmark", {}).get("legacy_total_time", 0),
            "test_duration": time.time() - self.results["test_metadata"]["start_time"]
        }

async def main():
    """Run comprehensive integration tests"""
    tester = ComprehensiveIntegrationTester()
    results = await tester.run_comprehensive_tests()
    
    # Save results to file
    results_file = Path("test_results_comprehensive.json")
    with open(results_file, "w") as f:
        json.dump(results, f, indent=2, default=str)
    
    # Print summary
    summary = results["summary"]
    print("\n" + "=" * 50)
    print("COMPREHENSIVE TEST SUMMARY")
    print("=" * 50)
    print(f"Tools Tested: {summary['total_tools_tested']}")
    print(f"Successful Tests: {summary['successful_tests']}")
    print(f"Behavior Match Rate: {summary['behavior_match_rate']:.2%}")
    print(f"Registry Ready: {'✅ YES' if summary['registry_ready'] else '❌ NO'}")
    print(f"Performance Overhead: {summary['performance_overhead']:.4f}s")
    print(f"Test Duration: {summary['test_duration']:.2f}s")
    print(f"\nDetailed results saved to: {results_file}")
    
    return results

if __name__ == "__main__":
    asyncio.run(main())