#!/usr/bin/env python3
"""
Focused Registry Integration Test - Direct tool execution comparison
Tests registry vs legacy tool execution patterns
"""

import asyncio
import time
import json
from pathlib import Path
from typing import Dict, List, Any

# Direct imports for testing
from ...refactor_config import RefactorConfig, get_config, enable_phase_0
from ...tool_registry import ToolRegistry
from ...handlers.task_management import TaskManagementHandler
from .tool_catalog import ToolCatalog

class FocusedRegistryTest:
    """Direct registry vs legacy testing without full server overhead"""
    
    def __init__(self):
        self.catalog = ToolCatalog()
        self.results = {
            "start_time": time.time(),
            "registry_results": {},
            "legacy_simulation": {},
            "performance_comparison": {},
            "summary": {}
        }
    
    def setup_registry_config(self) -> RefactorConfig:
        """Setup registry-enabled configuration"""
        config = RefactorConfig()
        config.enable_tool_registry = True
        config.enable_consistent_error_handling = True
        config.fallback_to_legacy = False
        config.debug_registry = True
        return config
    
    def setup_legacy_config(self) -> RefactorConfig:
        """Setup legacy configuration"""
        config = RefactorConfig()
        config.enable_tool_registry = False
        config.enable_consistent_error_handling = False
        config.fallback_to_legacy = True
        config.debug_registry = False
        return config
    
    async def test_registry_tools(self) -> Dict[str, Any]:
        """Test tools through registry system"""
        print("=== Testing Registry Implementation ===")
        
        # Setup registry
        config = self.setup_registry_config()
        registry = ToolRegistry()
        
        # Initialize storage manager for handlers
        from ...storage.task_storage_manager import TaskStorageManager
        storage_manager = TaskStorageManager("/tmp/atlas_test_storage")
        
        # Register task management handler (9 tools from Phase 0)
        task_handler = TaskManagementHandler(storage_manager=storage_manager)
        registry.register_handler(task_handler)
        
        registry_results = {
            "tools_tested": 0,
            "successful_calls": 0,
            "failed_calls": 0,
            "tool_results": {},
            "total_execution_time": 0.0
        }
        
        # Test task management tools (confirmed working in Phase 0)
        task_tools = self.catalog.get_category_tools("task_management")
        
        for tool_name in task_tools:
            print(f"  Testing registry: {tool_name}")
            
            test_params = self.catalog.get_test_parameters(tool_name)
            start_time = time.time()
            
            try:
                # Test through registry dispatcher
                result = await registry.dispatch(tool_name, test_params)
                execution_time = time.time() - start_time
                
                registry_results["tool_results"][tool_name] = {
                    "success": True,
                    "result": result,
                    "execution_time": execution_time,
                    "error": None
                }
                registry_results["successful_calls"] += 1
                    
            except Exception as e:
                execution_time = time.time() - start_time
                registry_results["tool_results"][tool_name] = {
                    "success": False,
                    "result": None,
                    "execution_time": execution_time,
                    "error": str(e)
                }
                registry_results["failed_calls"] += 1
            
            registry_results["tools_tested"] += 1
            registry_results["total_execution_time"] += registry_results["tool_results"][tool_name]["execution_time"]
        
        return registry_results
    
    async def test_legacy_simulation(self) -> Dict[str, Any]:
        """Simulate legacy tool execution patterns"""
        print("=== Testing Legacy Simulation ===")
        
        # Setup legacy config
        config = self.setup_legacy_config()
        
        legacy_results = {
            "tools_tested": 0,
            "successful_calls": 0,
            "failed_calls": 0,
            "tool_results": {},
            "total_execution_time": 0.0
        }
        
        # Test same task management tools directly
        task_tools = self.catalog.get_category_tools("task_management")
        from ...storage.task_storage_manager import TaskStorageManager
        storage_manager = TaskStorageManager("/tmp/atlas_test_storage")
        task_handler = TaskManagementHandler(storage_manager=storage_manager)
        
        for tool_name in task_tools:
            print(f"  Testing legacy: {tool_name}")
            
            test_params = self.catalog.get_test_parameters(tool_name)
            start_time = time.time()
            
            try:
                # Direct handler execution (simulating legacy if-elif chain)
                if hasattr(task_handler, tool_name):
                    method = getattr(task_handler, tool_name)
                    result = await method(test_params)
                    execution_time = time.time() - start_time
                    
                    legacy_results["tool_results"][tool_name] = {
                        "success": True,
                        "result": result,
                        "execution_time": execution_time,
                        "error": None
                    }
                    legacy_results["successful_calls"] += 1
                else:
                    legacy_results["tool_results"][tool_name] = {
                        "success": False,
                        "result": None,
                        "execution_time": time.time() - start_time,
                        "error": "Method not found in handler"
                    }
                    legacy_results["failed_calls"] += 1
                    
            except Exception as e:
                execution_time = time.time() - start_time
                legacy_results["tool_results"][tool_name] = {
                    "success": False,
                    "result": None,
                    "execution_time": execution_time,
                    "error": str(e)
                }
                legacy_results["failed_calls"] += 1
            
            legacy_results["tools_tested"] += 1
            legacy_results["total_execution_time"] += legacy_results["tool_results"][tool_name]["execution_time"]
        
        return legacy_results
    
    def compare_results(self, registry_results: Dict, legacy_results: Dict) -> Dict[str, Any]:
        """Compare registry vs legacy results"""
        
        comparison = {
            "tool_comparison": {},
            "performance_summary": {
                "registry_avg_time": registry_results["total_execution_time"] / registry_results["tools_tested"] if registry_results["tools_tested"] > 0 else 0,
                "legacy_avg_time": legacy_results["total_execution_time"] / legacy_results["tools_tested"] if legacy_results["tools_tested"] > 0 else 0,
                "registry_overhead": 0.0,
                "overhead_percentage": 0.0
            },
            "behavior_analysis": {
                "identical_success": 0,
                "identical_failure": 0,
                "success_mismatch": 0,
                "total_tools": 0
            }
        }
        
        # Compare each tool
        for tool_name in registry_results["tool_results"]:
            if tool_name in legacy_results["tool_results"]:
                registry_result = registry_results["tool_results"][tool_name]
                legacy_result = legacy_results["tool_results"][tool_name]
                
                # Performance comparison
                perf_ratio = (registry_result["execution_time"] / legacy_result["execution_time"] 
                            if legacy_result["execution_time"] > 0 else 1.0)
                
                # Behavior comparison
                registry_success = registry_result["success"]
                legacy_success = legacy_result["success"]
                
                behavior_match = registry_success == legacy_success
                
                comparison["tool_comparison"][tool_name] = {
                    "registry_success": registry_success,
                    "legacy_success": legacy_success,
                    "behavior_match": behavior_match,
                    "performance_ratio": perf_ratio,
                    "registry_time": registry_result["execution_time"],
                    "legacy_time": legacy_result["execution_time"]
                }
                
                # Update summary stats
                if registry_success and legacy_success:
                    comparison["behavior_analysis"]["identical_success"] += 1
                elif not registry_success and not legacy_success:
                    comparison["behavior_analysis"]["identical_failure"] += 1
                else:
                    comparison["behavior_analysis"]["success_mismatch"] += 1
                
                comparison["behavior_analysis"]["total_tools"] += 1
        
        # Calculate performance overhead
        reg_avg = comparison["performance_summary"]["registry_avg_time"]
        leg_avg = comparison["performance_summary"]["legacy_avg_time"]
        
        comparison["performance_summary"]["registry_overhead"] = reg_avg - leg_avg
        comparison["performance_summary"]["overhead_percentage"] = (
            (reg_avg - leg_avg) / leg_avg * 100 if leg_avg > 0 else 0
        )
        
        return comparison
    
    def generate_summary(self, registry_results: Dict, legacy_results: Dict, comparison: Dict) -> Dict[str, Any]:
        """Generate comprehensive test summary"""
        
        behavior = comparison["behavior_analysis"]
        performance = comparison["performance_summary"]
        
        summary = {
            "test_duration": time.time() - self.results["start_time"],
            "tools_tested": behavior["total_tools"],
            "behavior_match_rate": (behavior["identical_success"] + behavior["identical_failure"]) / behavior["total_tools"] * 100 if behavior["total_tools"] > 0 else 0,
            "registry_success_rate": registry_results["successful_calls"] / registry_results["tools_tested"] * 100 if registry_results["tools_tested"] > 0 else 0,
            "legacy_success_rate": legacy_results["successful_calls"] / legacy_results["tools_tested"] * 100 if legacy_results["tools_tested"] > 0 else 0,
            "performance_overhead_ms": performance["registry_overhead"] * 1000,
            "performance_overhead_percentage": performance["overhead_percentage"],
            "registry_production_ready": behavior["success_mismatch"] == 0,
            "performance_acceptable": abs(performance["overhead_percentage"]) < 15,  # Allow 15% overhead
            "overall_verdict": "PASS" if (behavior["success_mismatch"] == 0 and abs(performance["overhead_percentage"]) < 15) else "FAIL"
        }
        
        return summary
    
    async def run_focused_test(self) -> Dict[str, Any]:
        """Run focused registry integration test"""
        
        print("ATLAS MCP Registry Integration Test")
        print("=" * 40)
        
        # Test registry implementation
        registry_results = await self.test_registry_tools()
        self.results["registry_results"] = registry_results
        
        # Test legacy simulation
        legacy_results = await self.test_legacy_simulation()
        self.results["legacy_simulation"] = legacy_results
        
        # Compare results
        comparison = self.compare_results(registry_results, legacy_results)
        self.results["performance_comparison"] = comparison
        
        # Generate summary
        summary = self.generate_summary(registry_results, legacy_results, comparison)
        self.results["summary"] = summary
        
        # Print results
        self.print_results(summary, comparison)
        
        return self.results
    
    def print_results(self, summary: Dict, comparison: Dict):
        """Print test results"""
        
        print("\n" + "=" * 40)
        print("REGISTRY INTEGRATION TEST RESULTS")
        print("=" * 40)
        
        print(f"Tools Tested: {summary['tools_tested']}")
        print(f"Behavior Match Rate: {summary['behavior_match_rate']:.1f}%")
        print(f"Registry Success Rate: {summary['registry_success_rate']:.1f}%")
        print(f"Legacy Success Rate: {summary['legacy_success_rate']:.1f}%")
        print(f"Performance Overhead: {summary['performance_overhead_percentage']:.1f}%")
        print(f"Production Ready: {'✅ YES' if summary['registry_production_ready'] else '❌ NO'}")
        print(f"Performance Acceptable: {'✅ YES' if summary['performance_acceptable'] else '❌ NO'}")
        
        print(f"\nOVERALL VERDICT: {summary['overall_verdict']}")
        
        if summary['overall_verdict'] == "PASS":
            print("🎉 Registry ready for Phase 1 rollout!")
        else:
            print("⚠️  Registry needs fixes before deployment")
        
        # Save detailed results
        results_file = Path(__file__).parent / "registry_integration_results.json"
        with open(results_file, "w") as f:
            json.dump(self.results, f, indent=2, default=str)
        
        print(f"\nDetailed results saved to: {results_file}")

async def main():
    """Run focused registry integration test"""
    tester = FocusedRegistryTest()
    results = await tester.run_focused_test()
    return results

if __name__ == "__main__":
    asyncio.run(main())