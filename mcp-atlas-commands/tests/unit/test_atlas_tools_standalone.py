#!/usr/bin/env python3
"""
Standalone test for ATLAS MCP tools without requiring MCP server dependencies.
Tests the tool registry functionality and handler integration.
"""

import sys
import os
import asyncio
import time
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Mock MCP types for testing
class TextContent:
    def __init__(self, text: str):
        self.text = text
        self.type = "text"

def mock_mcp_types():
    """Mock MCP types module for testing"""
    import types
    mcp_module = types.ModuleType('mcp')
    types_module = types.ModuleType('types')
    types_module.TextContent = TextContent
    mcp_module.types = types_module
    sys.modules['mcp'] = mcp_module
    sys.modules['mcp.types'] = types_module

# Apply mock before importing ATLAS modules
mock_mcp_types()

from atlas_commands.tool_registry import ToolRegistry, ToolHandler
from atlas_commands.plugins.testing.tool_catalog import ToolCatalog

class MockTaskManagementHandler(ToolHandler):
    """Mock handler for testing task management tools"""
    
    @property
    def category(self) -> str:
        return "task_management"
    
    async def handle(self, name: str, arguments: dict) -> list:
        """Mock handler that returns success response"""
        return [TextContent(f"Mock response for {name} with args: {arguments}")]
    
    def get_tool_names(self) -> list:
        return [
            "create_task_metadata", "update_task_status", "get_task_context",
            "list_project_tasks", "create_task_backup", "archive_task"
        ]

class MockValidationHandler(ToolHandler):
    """Mock handler for testing validation tools"""
    
    @property
    def category(self) -> str:
        return "validation"
    
    async def handle(self, name: str, arguments: dict) -> list:
        """Mock handler that simulates validation"""
        if name == "validate_file_operation":
            return [TextContent("File operation validated successfully")]
        elif name == "validate_naming_convention":
            return [TextContent("Naming convention is valid")]
        else:
            return [TextContent(f"Validation complete for {name}")]
    
    def get_tool_names(self) -> list:
        return ["validate_file_operation", "validate_naming_convention", "validate_code_standards"]

class ATLASToolsTester:
    """Standalone tester for ATLAS tools registry"""
    
    def __init__(self):
        self.catalog = ToolCatalog()
        self.registry = ToolRegistry()
        self.test_results = {
            "start_time": time.time(),
            "tests_run": 0,
            "tests_passed": 0,
            "tests_failed": 0,
            "errors": [],
            "performance": []
        }
    
    def setup_registry(self):
        """Setup the tool registry with mock handlers"""
        print("Setting up tool registry...")
        
        # Register mock handlers
        task_handler = MockTaskManagementHandler()
        validation_handler = MockValidationHandler()
        
        self.registry.register_handler(task_handler)
        self.registry.register_handler(validation_handler)
        
        print(f"✓ Registered {len(self.registry.list_categories())} categories")
        print(f"✓ Total tools available: {len(self.registry.list_tools())}")
    
    def test_registry_structure(self):
        """Test basic registry structure and functionality"""
        print("\n=== Testing Registry Structure ===")
        
        # Test categories
        categories = self.registry.list_categories()
        print(f"Categories: {categories}")
        assert len(categories) >= 2, "Should have at least 2 categories"
        
        # Test tools listing
        tools = self.registry.list_tools()
        print(f"Total tools: {len(tools)}")
        assert len(tools) >= 5, "Should have at least 5 tools"
        
        # Test category-specific tools
        for category in categories:
            category_tools = self.registry.get_tools_by_category(category)
            print(f"  {category}: {len(category_tools)} tools")
            assert len(category_tools) > 0, f"Category {category} should have tools"
        
        print("✓ Registry structure tests passed")
        return True
    
    async def test_tool_execution(self, tool_name: str, test_params: dict):
        """Test individual tool execution"""
        start_time = time.time()
        
        try:
            # Get handler for tool
            handler = self.registry.get_handler(tool_name)
            
            # Execute tool
            result = await handler.handle(tool_name, test_params)
            
            execution_time = time.time() - start_time
            
            # Validate result
            assert result is not None, "Result should not be None"
            assert len(result) > 0, "Result should contain content"
            assert hasattr(result[0], 'text'), "Result should be TextContent"
            
            self.test_results["tests_passed"] += 1
            self.test_results["performance"].append({
                "tool": tool_name,
                "time": execution_time,
                "success": True
            })
            
            print(f"  ✓ {tool_name}: {execution_time:.4f}s")
            return True
            
        except Exception as e:
            execution_time = time.time() - start_time
            self.test_results["tests_failed"] += 1
            self.test_results["errors"].append({
                "tool": tool_name,
                "error": str(e),
                "time": execution_time
            })
            print(f"  ✗ {tool_name}: {str(e)}")
            return False
        finally:
            self.test_results["tests_run"] += 1
    
    async def test_category_tools(self, category: str):
        """Test all tools in a category"""
        print(f"\n=== Testing {category.title()} Tools ===")
        
        tools = self.registry.get_tools_by_category(category)
        if not tools:
            print(f"  No tools found for category: {category}")
            return
        
        success_count = 0
        
        for tool_name in tools:
            # Get test parameters from catalog
            test_params = self.catalog.get_test_parameters(tool_name)
            
            # Test the tool
            success = await self.test_tool_execution(tool_name, test_params)
            if success:
                success_count += 1
        
        print(f"  Category Results: {success_count}/{len(tools)} tools passed")
        return success_count == len(tools)
    
    async def test_performance_benchmark(self):
        """Test performance of key tools"""
        print("\n=== Performance Benchmark ===")
        
        # Test core tools multiple times
        benchmark_tools = ["create_task_metadata", "validate_file_operation"]
        iterations = 5
        
        for tool_name in benchmark_tools:
            if tool_name not in self.registry.list_tools():
                print(f"  Skipping {tool_name} - not available")
                continue
                
            print(f"  Benchmarking {tool_name} ({iterations} iterations)...")
            
            times = []
            test_params = self.catalog.get_test_parameters(tool_name)
            
            for i in range(iterations):
                start_time = time.time()
                
                try:
                    handler = self.registry.get_handler(tool_name)
                    await handler.handle(tool_name, test_params)
                    execution_time = time.time() - start_time
                    times.append(execution_time)
                except Exception as e:
                    print(f"    Iteration {i+1} failed: {e}")
                    continue
            
            if times:
                avg_time = sum(times) / len(times)
                min_time = min(times)
                max_time = max(times)
                print(f"    Average: {avg_time:.4f}s, Min: {min_time:.4f}s, Max: {max_time:.4f}s")
        
        print("✓ Performance benchmark completed")
    
    def generate_report(self):
        """Generate test report"""
        total_time = time.time() - self.test_results["start_time"]
        
        print("\n" + "="*60)
        print("ATLAS Tools Registry Test Report")
        print("="*60)
        print(f"Total test duration: {total_time:.2f} seconds")
        print(f"Tests run: {self.test_results['tests_run']}")
        print(f"Tests passed: {self.test_results['tests_passed']}")
        print(f"Tests failed: {self.test_results['tests_failed']}")
        
        success_rate = (self.test_results['tests_passed'] / self.test_results['tests_run'] * 100) if self.test_results['tests_run'] > 0 else 0
        print(f"Success rate: {success_rate:.1f}%")
        
        if self.test_results['errors']:
            print(f"\nErrors ({len(self.test_results['errors'])}):")
            for error in self.test_results['errors']:
                print(f"  - {error['tool']}: {error['error']}")
        
        # Performance summary
        if self.test_results['performance']:
            successful_tests = [p for p in self.test_results['performance'] if p['success']]
            if successful_tests:
                avg_time = sum(p['time'] for p in successful_tests) / len(successful_tests)
                print(f"\nAverage execution time: {avg_time:.4f} seconds")
        
        print(f"\n{'✓ ALL TESTS PASSED' if self.test_results['tests_failed'] == 0 else '⚠ SOME TESTS FAILED'}")
        
        return self.test_results['tests_failed'] == 0
    
    async def run_all_tests(self):
        """Run comprehensive test suite"""
        print("ATLAS MCP Tools Registry Test Suite")
        print("="*50)
        
        # Setup
        self.setup_registry()
        
        # Test registry structure
        self.test_registry_structure()
        
        # Test categories
        categories = self.registry.list_categories()
        for category in categories:
            await self.test_category_tools(category)
        
        # Performance tests
        await self.test_performance_benchmark()
        
        # Generate report
        return self.generate_report()

async def main():
    """Main test runner"""
    tester = ATLASToolsTester()
    success = await tester.run_all_tests()
    
    # Exit with appropriate code
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    asyncio.run(main())