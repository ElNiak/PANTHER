#!/usr/bin/env python3
"""
Main test runner for comprehensive ATLAS MCP testing
Executes all testing modules in the plugins system
"""

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from atlas_commands.plugins.testing.tool_catalog import ToolCatalog
from atlas_commands.plugins.testing.registry_tester import RegistryTester

class ComprehensiveTestRunner:
    """Main orchestrator for all ATLAS MCP testing"""
    
    def __init__(self):
        self.catalog = ToolCatalog()
        self.registry_tester = RegistryTester()
        self.test_results = {
            "test_session": {
                "start_time": datetime.now().isoformat(),
                "test_type": "comprehensive_registry_legacy_comparison",
                "tool_count": self.catalog.get_tool_count()
            },
            "catalog_validation": {},
            "registry_testing": {},
            "final_summary": {}
        }
    
    def validate_tool_catalog(self) -> Dict[str, Any]:
        """Validate the tool catalog before testing"""
        print("=== Tool Catalog Validation ===")
        
        validation = self.catalog.validate_catalog()
        
        print(f"Total Tools: {validation['total_tools']}")
        print(f"Expected: {validation['expected_tools']}")
        print(f"Complete: {'✅' if validation['is_complete'] else '❌'}")
        print(f"Duplicates: {'❌' if validation['has_duplicates'] else '✅'}")
        
        if validation['has_duplicates']:
            print(f"Duplicate Count: {validation['duplicate_count']}")
        
        print("\nCategory Breakdown:")
        for category, count in validation['category_counts'].items():
            print(f"  {category}: {count} tools")
        
        return validation
    
    async def run_critical_tools_first(self) -> Dict[str, Any]:
        """Test critical tool categories first (high priority)"""
        critical_categories = ["task_management", "hierarchical", "validation"]
        
        print("\n=== Critical Tools Testing (High Priority) ===")
        return await self.registry_tester.run_comprehensive_test(critical_categories)
    
    async def run_remaining_tools(self) -> Dict[str, Any]:
        """Test remaining tool categories"""
        remaining_categories = ["workflow_intelligence", "storage_memory", "observability"]
        
        print("\n=== Remaining Tools Testing ===")
        return await self.registry_tester.run_comprehensive_test(remaining_categories)
    
    def generate_final_report(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """Generate final comprehensive test report"""
        
        summary = results.get("summary", {})
        performance = results.get("performance_metrics", {})
        
        report = {
            "test_completion": {
                "all_tools_tested": summary.get("total_tools_tested", 0),
                "behavior_match_rate": summary.get("behavior_match_percentage", 0),
                "production_ready": summary.get("registry_production_ready", False),
                "test_duration": summary.get("test_duration_seconds", 0)
            },
            "performance_analysis": {
                "avg_overhead_percentage": performance.get("overall_summary", {}).get("overhead_percentage", 0),
                "acceptable_overhead": performance.get("overall_summary", {}).get("overhead_percentage", 0) < 10,
                "performance_details": performance.get("tool_performance", {})
            },
            "category_breakdown": {},
            "recommendations": []
        }
        
        # Analyze category results
        for category, result in results.get("category_results", {}).items():
            report["category_breakdown"][category] = {
                "tools_count": result["tools_count"],
                "success_rate": result["successful_tests"] / result["tools_count"] * 100 if result["tools_count"] > 0 else 0,
                "behavior_match_rate": result["behavior_matches"] / result["tools_count"] * 100 if result["tools_count"] > 0 else 0,
                "has_errors": len(result["error_tools"]) > 0,
                "error_count": len(result["error_tools"])
            }
        
        # Generate recommendations
        if report["test_completion"]["production_ready"]:
            report["recommendations"].append("✅ Registry implementation ready for Phase 1 rollout")
        else:
            report["recommendations"].append("❌ Registry needs fixes before Phase 1")
        
        if report["performance_analysis"]["acceptable_overhead"]:
            report["recommendations"].append("✅ Performance overhead is acceptable")
        else:
            report["recommendations"].append("⚠️ Registry performance overhead needs optimization")
        
        # Check for error patterns
        error_categories = [
            cat for cat, details in report["category_breakdown"].items()
            if details["has_errors"]
        ]
        
        if error_categories:
            report["recommendations"].append(
                f"🔧 Fix errors in categories: {', '.join(error_categories)}"
            )
        
        return report
    
    def save_results(self, results: Dict[str, Any], filename: str = None) -> Path:
        """Save test results to JSON file"""
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"comprehensive_test_results_{timestamp}.json"
        
        results_file = Path(__file__).parent / filename
        
        with open(results_file, "w") as f:
            json.dump(results, f, indent=2, default=str)
        
        return results_file
    
    async def run_full_test_suite(self) -> Dict[str, Any]:
        """Execute complete test suite"""
        
        print("ATLAS MCP Comprehensive Testing Suite")
        print("=" * 50)
        
        # 1. Validate tool catalog
        catalog_validation = self.validate_tool_catalog()
        self.test_results["catalog_validation"] = catalog_validation
        
        if not catalog_validation["is_complete"]:
            print("❌ Tool catalog incomplete - aborting tests")
            return self.test_results
        
        # 2. Run registry vs legacy testing
        print("\n🚀 Starting Registry vs Legacy Integration Testing")
        registry_results = await self.registry_tester.run_comprehensive_test()
        self.test_results["registry_testing"] = registry_results
        
        # 3. Generate final report
        final_report = self.generate_final_report(registry_results)
        self.test_results["final_summary"] = final_report
        
        # 4. Save results
        results_file = self.save_results(self.test_results)
        
        # 5. Print final summary
        self.print_final_summary(final_report, results_file)
        
        return self.test_results
    
    def print_final_summary(self, report: Dict[str, Any], results_file: Path):
        """Print comprehensive final summary"""
        
        print("\n" + "=" * 60)
        print("COMPREHENSIVE TEST SUMMARY")
        print("=" * 60)
        
        completion = report["test_completion"]
        performance = report["performance_analysis"]
        
        print(f"Tools Tested: {completion['all_tools_tested']}")
        print(f"Behavior Match Rate: {completion['behavior_match_rate']:.1f}%")
        print(f"Production Ready: {'✅ YES' if completion['production_ready'] else '❌ NO'}")
        print(f"Performance Overhead: {performance['avg_overhead_percentage']:.1f}%")
        print(f"Acceptable Performance: {'✅ YES' if performance['acceptable_overhead'] else '❌ NO'}")
        print(f"Test Duration: {completion['test_duration']:.1f}s")
        
        print("\nCategory Breakdown:")
        for category, details in report["category_breakdown"].items():
            status = "✅" if details["behavior_match_rate"] == 100 else "❌"
            print(f"  {status} {category}: {details['behavior_match_rate']:.1f}% match rate")
        
        print("\nRecommendations:")
        for rec in report["recommendations"]:
            print(f"  {rec}")
        
        print(f"\nDetailed results saved to: {results_file}")
        
        # Final verdict
        if completion['production_ready'] and performance['acceptable_overhead']:
            print("\n🎉 REGISTRY READY FOR PHASE 1 ROLLOUT!")
        else:
            print("\n⚠️  REGISTRY NEEDS FIXES BEFORE DEPLOYMENT")

async def main():
    """Main entry point for comprehensive testing"""
    runner = ComprehensiveTestRunner()
    results = await runner.run_full_test_suite()
    return results

if __name__ == "__main__":
    asyncio.run(main())