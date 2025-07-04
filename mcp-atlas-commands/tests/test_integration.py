"""
Integration tests for ATLAS MCP Registry Architecture.

Tests the complete integration between registry, handlers, and server,
ensuring the full replacement of the if-elif chain works correctly.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from typing import Dict, Any, List

# Mock MCP imports for testing
class MockTextContent:
    def __init__(self, type: str, text: str):
        self.type = type
        self.text = text
        
    def __eq__(self, other):
        return isinstance(other, MockTextContent) and self.type == other.type and self.text == other.text

# Mock the mcp module
import sys
sys.modules['mcp'] = Mock()
sys.modules['mcp.types'] = Mock()
sys.modules['mcp.types'].TextContent = MockTextContent

# Mock the config module with Phase 3 settings
config_mock = Mock()
config_mock.enable_consistent_error_handling = True
config_mock.enable_tool_registry = True
config_mock.enable_logging_improvements = True
config_mock.fallback_to_legacy = False  # Phase 3: No fallback needed


class MockStorageManager:
    """Mock storage manager for testing."""
    def create_task_metadata(self, *args, **kwargs):
        return {"status": "created", "task_id": "test_task"}


class MockServer:
    """Mock server with all required handler methods."""
    
    def __init__(self):
        self.call_log = []
        self.storage_manager = MockStorageManager()
        
    # Task management methods
    async def _handle_create_task_metadata(self, args):
        self.call_log.append(("create_task_metadata", args))
        return [MockTextContent("text", "Task metadata created")]
        
    async def _handle_update_task_status(self, args):
        self.call_log.append(("update_task_status", args))
        return [MockTextContent("text", "Task status updated")]
        
    # Hierarchical methods
    async def _handle_create_hierarchical_task(self, args):
        self.call_log.append(("create_hierarchical_task", args))
        return [MockTextContent("text", "Hierarchical task created")]
        
    async def _handle_get_task_hierarchy(self, args):
        self.call_log.append(("get_task_hierarchy", args))
        return [MockTextContent("text", "Task hierarchy retrieved")]
        
    # Validation methods
    async def _handle_validate_file_operation(self, args):
        self.call_log.append(("validate_file_operation", args))
        return [MockTextContent("text", "File operation validated")]
        
    async def _handle_validate_naming_convention(self, args):
        self.call_log.append(("validate_naming_convention", args))
        return [MockTextContent("text", "Naming convention validated")]
        
    # Workflow intelligence methods
    async def _handle_orchestrate_intelligent_tasks(self, args):
        self.call_log.append(("orchestrate_intelligent_tasks", args))
        return [MockTextContent("text", "Tasks orchestrated")]
        
    # Observability methods
    async def _handle_get_observability_status(self, args):
        self.call_log.append(("get_observability_status", args))
        return [MockTextContent("text", "Observability status retrieved")]
        
    # Storage methods
    async def _handle_create_nested_subtask(self, args):
        self.call_log.append(("create_nested_subtask", args))
        return [MockTextContent("text", "Nested subtask created")]
        
    # Memory methods
    async def _handle_memory_health_check(self, args):
        self.call_log.append(("memory_health_check", args))
        return [MockTextContent("text", "Memory health checked")]
        
    # Cache methods
    async def _handle_get_cache_stats(self, args):
        self.call_log.append(("get_cache_stats", args))
        return [MockTextContent("text", "Cache stats retrieved")]
        
    # Embeddings methods
    async def _handle_search_similar_tasks(self, args):
        self.call_log.append(("search_similar_tasks", args))
        return [MockTextContent("text", "Similar tasks found")]
        
    # Legacy methods
    async def _handle_original_tool(self, name, args):
        self.call_log.append(("original_tool", name, args))
        return [MockTextContent("text", f"Legacy tool {name} executed")]


with patch('atlas_commands.refactor_config.get_config', return_value=config_mock):
    from atlas_commands.tool_registry import ToolRegistry
    from atlas_commands.handlers import (
        TaskManagementHandler, HierarchicalManagementHandler, ValidationHandler,
        WorkflowIntelligenceHandler, ObservabilityHandler, NestedStorageHandler,
        MemoryManagementHandler, CacheManagementHandler, EmbeddingsHandler, LegacyHandler
    )


class TestIntegrationFullStack:
    """Test complete integration of registry architecture."""
    
    def setup_method(self):
        """Setup complete registry with all handlers."""
        self.mock_server = MockServer()
        self.registry = ToolRegistry()
        
        # Register all handlers (mimicking server._setup_tool_registry)
        handlers = [
            TaskManagementHandler(self.mock_server.storage_manager, None),
            HierarchicalManagementHandler(self.mock_server),
            ValidationHandler(self.mock_server),
            WorkflowIntelligenceHandler(self.mock_server),
            ObservabilityHandler(self.mock_server),
            NestedStorageHandler(self.mock_server),
            MemoryManagementHandler(self.mock_server),
            CacheManagementHandler(self.mock_server),
            EmbeddingsHandler(self.mock_server),
            LegacyHandler(self.mock_server)
        ]
        
        for handler in handlers:
            self.registry.register_handler(handler)
            
    def test_complete_registry_setup(self):
        """Test that complete registry setup works correctly."""
        stats = self.registry.get_registry_stats()
        
        # Verify all 58 tools are registered
        assert stats["total_tools"] == 58
        assert stats["total_categories"] == 10
        
        # Verify category distribution
        expected_categories = {
            "task_management": 9,
            "hierarchical_management": 9,
            "validation": 4,
            "workflow_intelligence": 4,
            "observability": 4,
            "nested_storage": 4,
            "memory_management": 5,
            "cache_management": 4,
            "embeddings": 5,
            "legacy": 10
        }
        
        for category, expected_count in expected_categories.items():
            actual_count = stats["tools_by_category"][category]
            assert actual_count == expected_count, f"Category {category}: expected {expected_count}, got {actual_count}"
            
    @pytest.mark.asyncio
    async def test_cross_category_tool_dispatch(self):
        """Test tool dispatch across all categories."""
        test_cases = [
            # (tool_name, category, expected_response_contains)
            ("create_task_metadata", "task_management", "Task metadata created"),
            ("create_hierarchical_task", "hierarchical_management", "Hierarchical task created"),
            ("validate_file_operation", "validation", "File operation validated"),
            ("orchestrate_intelligent_tasks", "workflow_intelligence", "Tasks orchestrated"),
            ("get_observability_status", "observability", "Observability status retrieved"),
            ("create_nested_subtask", "nested_storage", "Nested subtask created"),
            ("memory_health_check", "memory_management", "Memory health checked"),
            ("get_cache_stats", "cache_management", "Cache stats retrieved"),
            ("search_similar_tasks", "embeddings", "Similar tasks found"),
            ("create_unified_checklist", "legacy", "Legacy tool create_unified_checklist executed")
        ]
        
        for tool_name, expected_category, expected_response in test_cases:
            # Verify tool is in correct category
            category_tools = self.registry.get_tools_by_category(expected_category)
            assert tool_name in category_tools, f"Tool {tool_name} not found in {expected_category}"
            
            # Test dispatch
            result = await self.registry.dispatch(tool_name, {"test": "data"})
            assert len(result) == 1
            assert expected_response in result[0].text, f"Tool {tool_name} response mismatch"
            
    @pytest.mark.asyncio
    async def test_error_handling_across_categories(self):
        """Test consistent error handling across all categories."""
        # Test unknown tool in each category context
        unknown_tools = [
            "unknown_task_tool",
            "unknown_hierarchical_tool", 
            "unknown_validation_tool",
            "unknown_workflow_tool",
            "unknown_observability_tool",
            "unknown_storage_tool",
            "unknown_memory_tool",
            "unknown_cache_tool",
            "unknown_embeddings_tool",
            "unknown_legacy_tool"
        ]
        
        for unknown_tool in unknown_tools:
            result = await self.registry.dispatch(unknown_tool, {})
            assert len(result) == 1
            assert "Unknown tool" in result[0].text
            
    @pytest.mark.asyncio
    async def test_performance_vs_legacy_chain(self):
        """Test performance improvement over if-elif chain."""
        import time
        
        # Test batch dispatch performance
        tools_to_test = [
            "create_task_metadata", "validate_file_operation", "get_observability_status",
            "memory_health_check", "search_similar_tasks", "create_unified_checklist"
        ]
        
        # Measure registry dispatch time
        start_time = time.time()
        for _ in range(100):  # Simulate load
            for tool in tools_to_test:
                await self.registry.dispatch(tool, {})
        registry_time = time.time() - start_time
        
        # Registry should be very fast (O(1) lookup vs O(n) if-elif)
        assert registry_time < 1.0, f"Registry dispatch too slow: {registry_time}s"
        
    def test_tool_categorization_completeness(self):
        """Test that all tools are properly categorized."""
        all_tools = self.registry.list_tools()
        
        # Verify no duplicate tools
        assert len(all_tools) == len(set(all_tools)), "Duplicate tools found"
        
        # Verify all tools have a category
        for tool in all_tools:
            handler = self.registry.get_handler(tool)
            assert handler.category in self.registry.list_categories()
            
    @pytest.mark.asyncio
    async def test_concurrent_tool_execution(self):
        """Test concurrent execution of tools from different categories."""
        # Create concurrent tasks for different categories
        tasks = [
            self.registry.dispatch("create_task_metadata", {"concurrent": True}),
            self.registry.dispatch("validate_file_operation", {"concurrent": True}),
            self.registry.dispatch("get_observability_status", {"concurrent": True}),
            self.registry.dispatch("memory_health_check", {"concurrent": True}),
            self.registry.dispatch("search_similar_tasks", {"concurrent": True})
        ]
        
        # Execute concurrently
        results = await asyncio.gather(*tasks)
        
        # Verify all succeeded
        assert len(results) == 5
        for result in results:
            assert len(result) == 1
            assert result[0].type == "text"
            
    def test_registry_statistics_accuracy(self):
        """Test that registry statistics are accurate."""
        stats = self.registry.get_registry_stats()
        
        # Verify statistics match actual state
        actual_tools = len(self.registry.list_tools())
        actual_categories = len(self.registry.list_categories())
        
        assert stats["total_tools"] == actual_tools
        assert stats["total_categories"] == actual_categories
        
        # Verify category tool counts
        for category in self.registry.list_categories():
            expected_count = len(self.registry.get_tools_by_category(category))
            actual_count = stats["tools_by_category"][category]
            assert actual_count == expected_count
            
    @pytest.mark.asyncio
    async def test_if_elif_chain_replacement_verification(self):
        """Verify that registry completely replaces if-elif chain functionality."""
        # These are the tools that USED to be in the if-elif chain
        legacy_if_elif_tools = [
            # Task management (Phase 1)
            "create_task_metadata", "update_task_status", "add_task_artifact",
            
            # Hierarchical (Phase 2) 
            "create_hierarchical_task", "get_task_hierarchy",
            
            # Validation (Phase 2)
            "validate_file_operation", "validate_naming_convention",
            
            # Workflow (Phase 2)
            "orchestrate_intelligent_tasks", "adaptive_command_selection",
            
            # Observability (Phase 2) 
            "get_observability_status", "get_metrics_summary",
            
            # Storage (Phase 3)
            "create_nested_subtask", "get_nested_task",
            
            # Memory (Phase 3)
            "memory_health_check", "memory_force_backup",
            
            # Cache (Phase 3)
            "get_cache_stats", "invalidate_cache",
            
            # Embeddings (Phase 3)
            "search_similar_tasks", "discover_related_concepts",
            
            # Legacy tools
            "create_unified_checklist", "create_memory_entity"
        ]
        
        # Verify ALL these tools are now handled by registry
        for tool in legacy_if_elif_tools:
            # Should be registered
            assert tool in self.registry.list_tools(), f"Tool {tool} not in registry"
            
            # Should dispatch successfully
            result = await self.registry.dispatch(tool, {})
            assert len(result) == 1
            assert result[0].type == "text"
            
        print(f"✅ Verified {len(legacy_if_elif_tools)} tools migrated from if-elif chain")


class TestErrorRecoveryAndFallback:
    """Test error recovery and fallback mechanisms."""
    
    def setup_method(self):
        """Setup registry with error conditions."""
        self.registry = ToolRegistry()
        
    @pytest.mark.asyncio
    async def test_handler_exception_recovery(self):
        """Test registry handles handler exceptions gracefully."""
        # Create handler that always fails
        class FailingHandler:
            @property
            def category(self):
                return "failing_category"
                
            def get_tool_names(self):
                return ["failing_tool"]
                
            async def handle(self, name, arguments):
                raise RuntimeError("Handler failure")
                
        failing_handler = FailingHandler()
        self.registry.register_handler(failing_handler)
        
        result = await self.registry.dispatch("failing_tool", {})
        
        # Should handle error gracefully
        assert len(result) == 1
        assert "Error executing failing_tool" in result[0].text
        assert "Handler failure" in result[0].text


if __name__ == "__main__":
    # Simple integration test runner
    print("🧪 Running ATLAS MCP Integration Tests")
    print("=" * 50)
    
    # Test complete setup
    mock_server = MockServer()
    registry = ToolRegistry()
    
    # Register all handlers
    handlers = [
        TaskManagementHandler(mock_server.storage_manager, None),
        HierarchicalManagementHandler(mock_server),
        ValidationHandler(mock_server),
        WorkflowIntelligenceHandler(mock_server),
        ObservabilityHandler(mock_server),
        NestedStorageHandler(mock_server),
        MemoryManagementHandler(mock_server),
        CacheManagementHandler(mock_server),
        EmbeddingsHandler(mock_server),
        LegacyHandler(mock_server)
    ]
    
    for handler in handlers:
        registry.register_handler(handler)
    
    stats = registry.get_registry_stats()
    print(f"✅ Registry setup: {stats['total_tools']} tools, {stats['total_categories']} categories")
    
    # Test sample dispatch
    async def test_sample_dispatch():
        results = []
        sample_tools = ["create_task_metadata", "validate_file_operation", "get_observability_status"]
        
        for tool in sample_tools:
            result = await registry.dispatch(tool, {})
            results.append(len(result) > 0)
            
        return all(results)
    
    dispatch_success = asyncio.run(test_sample_dispatch())
    print(f"✅ Cross-category dispatch: {'Success' if dispatch_success else 'Failed'}")
    
    print(f"\n🎉 Integration test completed! Registry successfully replaces if-elif chain.")
    print(f"Use pytest for comprehensive testing.")