"""Registry vs Legacy Integration Testing Module"""

import asyncio
import time
from typing import Dict, List, Any, Tuple
from pathlib import Path

from .tool_catalog import ToolCatalog
from ...server import EnhancedAtlasCommandsServer
from ...refactor_config import RefactorConfig

class RegistryTester:
    """Test registry vs legacy dispatcher implementations"""
    
    def __init__(self):
        self.catalog = ToolCatalog()
        self.results = {
            "test_start_time": time.time(),
            "category_results": {},
            "performance_metrics": {},
            "behavior_analysis": {},
            "error_summary": {"registry": 0, "legacy": 0}
        }
    
    async def setup_test_servers(self) -> Tuple[EnhancedAtlasCommandsServer, EnhancedAtlasCommandsServer]:
        """Create registry-enabled and legacy test servers"""
        
        # Registry server (Phase 1 configuration)
        registry_config = RefactorConfig()
        registry_config.enable_registry = True
        registry_config.enable_fallback = True
        registry_config.enable_error_handling = True
        registry_config.enable_logging = True
        registry_server = EnhancedAtlasCommandsServer(config=registry_config)
        
        # Legacy server (original configuration)
        legacy_config = RefactorConfig()
        legacy_config.enable_registry = False
        legacy_config.enable_fallback = False
        legacy_config.enable_error_handling = False
        legacy_config.enable_logging = True
        legacy_server = EnhancedAtlasCommandsServer(config=legacy_config)
        
        return registry_server, legacy_server
    
    async def test_single_tool(self, tool_name: str, server: EnhancedAtlasCommandsServer, 
                             server_type: str) -> Dict[str, Any]:
        """Test individual tool on specific server implementation"""
        
        test_params = self.catalog.get_test_parameters(tool_name)
        start_time = time.time()
        
        try:
            # Mock MCP tool call request
            request = {
                "method": "tools/call",
                "params": {
                    "name": f"mcp__atlas-commands__{tool_name}",
                    "arguments": test_params
                }
            }
            
            # Execute through server's tool handling
            result = await server.handle_call_tool(
                f"mcp__atlas-commands__{tool_name}", 
                test_params
            )
            
            execution_time = time.time() - start_time
            
            return {
                "success": True,
                "result": result,
                "execution_time": execution_time,
                "error": None,
                "server_type": server_type,
                "tool_name": tool_name
            }
            
        except Exception as e:
            execution_time = time.time() - start_time
            
            return {
                "success": False,
                "result": None,
                "execution_time": execution_time,
                "error": str(e),
                "server_type": server_type,
                "tool_name": tool_name
            }
    
    def analyze_behavior_difference(self, registry_result: Dict, 
                                  legacy_result: Dict) -> Dict[str, Any]:
        """Analyze behavioral differences between implementations"""
        
        analysis = {
            "identical_success": False,
            "identical_failure": False,
            "behavior_match": False,
            "performance_ratio": 0.0,
            "differences": []
        }
        
        # Check success/failure patterns
        registry_success = registry_result["success"]
        legacy_success = legacy_result["success"]
        
        if registry_success == legacy_success:
            if registry_success:
                analysis["identical_success"] = True
                analysis["behavior_match"] = True
            else:
                analysis["identical_failure"] = True
                analysis["behavior_match"] = True
        else:
            analysis["differences"].append(
                f"Success mismatch: registry={registry_success}, legacy={legacy_success}"
            )
        
        # Performance comparison
        if legacy_result["execution_time"] > 0:
            analysis["performance_ratio"] = (
                registry_result["execution_time"] / legacy_result["execution_time"]
            )
        
        # Result structure comparison (basic)
        if registry_success and legacy_success:
            registry_has_result = registry_result["result"] is not None
            legacy_has_result = legacy_result["result"] is not None
            
            if registry_has_result != legacy_has_result:
                analysis["differences"].append(
                    f"Result presence mismatch: registry={registry_has_result}, legacy={legacy_has_result}"
                )
        
        return analysis
    
    async def test_tool_category(self, category: str) -> Dict[str, Any]:
        """Test all tools in a specific category"""
        
        tools = self.catalog.get_category_tools(category)
        print(f"\n=== Testing {category.title().replace('_', ' ')} Category ===")
        print(f"Tools: {len(tools)}")
        
        registry_server, legacy_server = await self.setup_test_servers()
        
        category_results = {
            "category": category,
            "tools_count": len(tools),
            "successful_tests": 0,
            "behavior_matches": 0,
            "performance_summary": {
                "registry_total_time": 0.0,
                "legacy_total_time": 0.0,
                "avg_performance_ratio": 0.0
            },
            "tool_results": {},
            "error_tools": []
        }
        
        performance_ratios = []
        
        for tool_name in tools:
            print(f"  Testing {tool_name}...")
            
            # Test with registry implementation
            registry_result = await self.test_single_tool(
                tool_name, registry_server, "registry"
            )
            
            # Test with legacy implementation
            legacy_result = await self.test_single_tool(
                tool_name, legacy_server, "legacy"
            )
            
            # Analyze behavior differences
            behavior_analysis = self.analyze_behavior_difference(
                registry_result, legacy_result
            )
            
            # Store detailed results
            category_results["tool_results"][tool_name] = {
                "registry": registry_result,
                "legacy": legacy_result,
                "analysis": behavior_analysis
            }
            
            # Update summary metrics
            if behavior_analysis["behavior_match"]:
                category_results["behavior_matches"] += 1
            
            if registry_result["success"] and legacy_result["success"]:
                category_results["successful_tests"] += 1
            
            # Track errors
            if not registry_result["success"] or not legacy_result["success"]:
                category_results["error_tools"].append({
                    "tool": tool_name,
                    "registry_error": registry_result.get("error"),
                    "legacy_error": legacy_result.get("error")
                })
            
            # Performance tracking
            category_results["performance_summary"]["registry_total_time"] += registry_result["execution_time"]
            category_results["performance_summary"]["legacy_total_time"] += legacy_result["execution_time"]
            
            if behavior_analysis["performance_ratio"] > 0:
                performance_ratios.append(behavior_analysis["performance_ratio"])
        
        # Calculate average performance ratio
        if performance_ratios:
            category_results["performance_summary"]["avg_performance_ratio"] = (
                sum(performance_ratios) / len(performance_ratios)
            )
        
        return category_results
    
    async def run_performance_benchmark(self, iterations: int = 5) -> Dict[str, Any]:
        """Run focused performance benchmark on critical tools"""
        
        # Focus on most frequently used tools
        benchmark_tools = [
            "create_task_metadata", "update_task_status", "get_task_context",
            "create_hierarchical_task", "validate_file_operation"
        ]
        
        print(f"\n=== Performance Benchmark ({iterations} iterations) ===")
        
        registry_server, legacy_server = await self.setup_test_servers()
        
        benchmark_results = {
            "iterations": iterations,
            "tools_tested": len(benchmark_tools),
            "tool_performance": {},
            "overall_summary": {
                "registry_avg_time": 0.0,
                "legacy_avg_time": 0.0,
                "overhead_percentage": 0.0
            }
        }
        
        total_registry_time = 0.0
        total_legacy_time = 0.0
        
        for tool_name in benchmark_tools:
            print(f"  Benchmarking {tool_name}...")
            
            registry_times = []
            legacy_times = []
            
            # Run multiple iterations
            for i in range(iterations):
                # Registry timing
                registry_result = await self.test_single_tool(
                    tool_name, registry_server, "registry"
                )
                registry_times.append(registry_result["execution_time"])
                
                # Legacy timing
                legacy_result = await self.test_single_tool(
                    tool_name, legacy_server, "legacy"
                )
                legacy_times.append(legacy_result["execution_time"])
            
            # Calculate statistics
            avg_registry = sum(registry_times) / len(registry_times)
            avg_legacy = sum(legacy_times) / len(legacy_times)
            overhead = avg_registry - avg_legacy
            overhead_pct = (overhead / avg_legacy * 100) if avg_legacy > 0 else 0
            
            benchmark_results["tool_performance"][tool_name] = {
                "registry_avg_ms": avg_registry * 1000,
                "legacy_avg_ms": avg_legacy * 1000,
                "overhead_ms": overhead * 1000,
                "overhead_percentage": overhead_pct,
                "performance_ratio": avg_registry / avg_legacy if avg_legacy > 0 else 1.0
            }
            
            total_registry_time += avg_registry
            total_legacy_time += avg_legacy
        
        # Overall summary
        benchmark_results["overall_summary"]["registry_avg_time"] = total_registry_time / len(benchmark_tools)
        benchmark_results["overall_summary"]["legacy_avg_time"] = total_legacy_time / len(benchmark_tools)
        benchmark_results["overall_summary"]["overhead_percentage"] = (
            (total_registry_time - total_legacy_time) / total_legacy_time * 100
            if total_legacy_time > 0 else 0
        )
        
        return benchmark_results
    
    def generate_test_summary(self) -> Dict[str, Any]:
        """Generate comprehensive test summary"""
        
        total_tools = 0
        total_successful = 0
        total_behavior_matches = 0
        total_categories = 0
        
        for category_result in self.results["category_results"].values():
            total_categories += 1
            total_tools += category_result["tools_count"]
            total_successful += category_result["successful_tests"]
            total_behavior_matches += category_result["behavior_matches"]
        
        test_duration = time.time() - self.results["test_start_time"]
        
        summary = {
            "test_duration_seconds": test_duration,
            "categories_tested": total_categories,
            "total_tools_tested": total_tools,
            "successful_tool_tests": total_successful,
            "behavior_match_count": total_behavior_matches,
            "behavior_match_percentage": (total_behavior_matches / total_tools * 100) if total_tools > 0 else 0,
            "registry_production_ready": total_behavior_matches == total_tools,
            "performance_overhead": self.results.get("performance_metrics", {}).get("overall_summary", {}).get("overhead_percentage", 0),
            "test_timestamp": self.results["test_start_time"]
        }
        
        return summary
    
    async def run_comprehensive_test(self, categories: List[str] = None) -> Dict[str, Any]:
        """Run comprehensive registry vs legacy testing"""
        
        if categories is None:
            categories = list(self.catalog.TOOL_CATEGORIES.keys())
        
        print("Starting Comprehensive Registry vs Legacy Testing")
        print("=" * 60)
        print(f"Categories to test: {categories}")
        print(f"Total tools: {self.catalog.get_tool_count()}")
        
        # Test each category
        for category in categories:
            category_result = await self.test_tool_category(category)
            self.results["category_results"][category] = category_result
        
        # Run performance benchmark
        performance_result = await self.run_performance_benchmark()
        self.results["performance_metrics"] = performance_result
        
        # Generate summary
        summary = self.generate_test_summary()
        self.results["summary"] = summary
        
        return self.results