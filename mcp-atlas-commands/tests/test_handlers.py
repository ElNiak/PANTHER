"""
Unit tests for all ATLAS MCP Handler implementations.

Tests each of the 10 handler categories to ensure proper tool routing,
error handling, and integration with the registry pattern.
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

# Mock the config module
config_mock = Mock()
config_mock.enable_consistent_error_handling = True
config_mock.enable_tool_registry = True

with patch('atlas_commands.refactor_config.get_config', return_value=config_mock):
    # Import handlers after mocking
    from atlas_commands.handlers.task_management import TaskManagementHandler
    from atlas_commands.handlers.hierarchical_management import HierarchicalManagementHandler
    from atlas_commands.handlers.validation import ValidationHandler
    from atlas_commands.handlers.workflow_intelligence import WorkflowIntelligenceHandler
    from atlas_commands.handlers.observability import ObservabilityHandler
    from atlas_commands.handlers.nested_storage import NestedStorageHandler
    from atlas_commands.handlers.memory_management import MemoryManagementHandler
    from atlas_commands.handlers.cache_management import CacheManagementHandler
    from atlas_commands.handlers.embeddings import EmbeddingsHandler
    from atlas_commands.handlers.legacy import LegacyHandler


class MockServer:
    """Mock server for testing handlers."""
    
    def __init__(self):
        self.call_log = []
        
    async def _handle_create_task_metadata(self, args):
        self.call_log.append(("create_task_metadata", args))
        return [MockTextContent("text", "Mock task metadata created")]
        
    async def _handle_create_hierarchical_task(self, args):
        self.call_log.append(("create_hierarchical_task", args))
        return [MockTextContent("text", "Mock hierarchical task created")]
        
    async def _handle_validate_file_operation(self, args):
        self.call_log.append(("validate_file_operation", args))
        return [MockTextContent("text", "Mock file validation")]
        
    async def _handle_orchestrate_intelligent_tasks(self, args):
        self.call_log.append(("orchestrate_intelligent_tasks", args))
        return [MockTextContent("text", "Mock intelligent orchestration")]
        
    async def _handle_get_observability_status(self, args):
        self.call_log.append(("get_observability_status", args))
        return [MockTextContent("text", "Mock observability status")]
        
    async def _handle_create_nested_subtask(self, args):
        self.call_log.append(("create_nested_subtask", args))
        return [MockTextContent("text", "Mock nested subtask")]
        
    async def _handle_memory_health_check(self, args):
        self.call_log.append(("memory_health_check", args))
        return [MockTextContent("text", "Mock memory health")]
        
    async def _handle_get_cache_stats(self, args):
        self.call_log.append(("get_cache_stats", args))
        return [MockTextContent("text", "Mock cache stats")]
        
    async def _handle_search_similar_tasks(self, args):
        self.call_log.append(("search_similar_tasks", args))
        return [MockTextContent("text", "Mock similar tasks")]
        
    async def _handle_original_tool(self, name, args):
        self.call_log.append(("original_tool", name, args))
        return [MockTextContent("text", f"Mock legacy tool {name}")]


class MockStorageManager:
    """Mock storage manager for TaskManagementHandler."""
    pass


class TestHandlerCategories:
    """Test all handler categories for proper implementation."""
    
    def setup_method(self):
        """Setup for each test."""
        self.mock_server = MockServer()
        self.mock_storage = MockStorageManager()
        
    def test_task_management_handler(self):
        """Test TaskManagementHandler."""
        handler = TaskManagementHandler(
            storage_manager=self.mock_storage,
            memory_manager=None
        )
        
        assert handler.category == "task_management"
        tools = handler.get_tool_names()
        
        expected_tools = [
            "create_task_metadata", "update_task_status", "add_task_artifact",
            "get_task_context", "list_project_tasks", "create_task_backup",
            "archive_task", "filter_tasks", "calculate_task_progress"
        ]
        
        assert len(tools) == 9
        for tool in expected_tools:
            assert tool in tools
            
    def test_hierarchical_management_handler(self):
        """Test HierarchicalManagementHandler."""
        handler = HierarchicalManagementHandler(self.mock_server)
        
        assert handler.category == "hierarchical_management"
        tools = handler.get_tool_names()
        
        expected_tools = [
            "create_hierarchical_task", "get_task_hierarchy", "update_hierarchical_status",
            "create_task_dependency", "get_progress_rollup", "query_hierarchical_context",
            "create_hierarchical_backup", "list_checkpoints", "restore_from_checkpoint"
        ]
        
        assert len(tools) == 9
        for tool in expected_tools:
            assert tool in tools
            
    def test_validation_handler(self):
        """Test ValidationHandler."""
        handler = ValidationHandler(self.mock_server)
        
        assert handler.category == "validation"
        tools = handler.get_tool_names()
        
        expected_tools = [
            "validate_file_operation", "validate_naming_convention",
            "validate_code_standards", "enforce_git_protocol"
        ]
        
        assert len(tools) == 4
        for tool in expected_tools:
            assert tool in tools
            
    def test_workflow_intelligence_handler(self):
        """Test WorkflowIntelligenceHandler."""
        handler = WorkflowIntelligenceHandler(self.mock_server)
        
        assert handler.category == "workflow_intelligence"
        tools = handler.get_tool_names()
        
        expected_tools = [
            "orchestrate_intelligent_tasks", "adaptive_command_selection",
            "analyze_workflow_patterns", "track_progress_milestones"
        ]
        
        assert len(tools) == 4
        for tool in expected_tools:
            assert tool in tools
            
    def test_observability_handler(self):
        """Test ObservabilityHandler."""
        handler = ObservabilityHandler(self.mock_server)
        
        assert handler.category == "observability"
        tools = handler.get_tool_names()
        
        expected_tools = [
            "get_observability_status", "get_metrics_summary",
            "export_traces", "set_trace_sampling"
        ]
        
        assert len(tools) == 4
        for tool in expected_tools:
            assert tool in tools
            
    def test_nested_storage_handler(self):
        """Test NestedStorageHandler."""
        handler = NestedStorageHandler(self.mock_server)
        
        assert handler.category == "nested_storage"
        tools = handler.get_tool_names()
        
        expected_tools = [
            "create_nested_subtask", "get_nested_task",
            "update_nested_task", "migrate_to_nested_storage"
        ]
        
        assert len(tools) == 4
        for tool in expected_tools:
            assert tool in tools
            
    def test_memory_management_handler(self):
        """Test MemoryManagementHandler."""
        handler = MemoryManagementHandler(self.mock_server)
        
        assert handler.category == "memory_management"
        tools = handler.get_tool_names()
        
        expected_tools = [
            "memory_health_check", "memory_force_backup", "memory_restore",
            "memory_analytics", "memory_cleanup"
        ]
        
        assert len(tools) == 5
        for tool in expected_tools:
            assert tool in tools
            
    def test_cache_management_handler(self):
        """Test CacheManagementHandler."""
        handler = CacheManagementHandler(self.mock_server)
        
        assert handler.category == "cache_management"
        tools = handler.get_tool_names()
        
        expected_tools = [
            "get_cache_stats", "invalidate_cache", "warm_cache", "clear_all_cache"
        ]
        
        assert len(tools) == 4
        for tool in expected_tools:
            assert tool in tools
            
    def test_embeddings_handler(self):
        """Test EmbeddingsHandler."""
        handler = EmbeddingsHandler(self.mock_server)
        
        assert handler.category == "embeddings"
        tools = handler.get_tool_names()
        
        expected_tools = [
            "search_similar_tasks", "discover_related_concepts", "find_solution_patterns",
            "train_task_embeddings", "get_embeddings_stats"
        ]
        
        assert len(tools) == 5
        for tool in expected_tools:
            assert tool in tools
            
    def test_legacy_handler(self):
        """Test LegacyHandler."""
        handler = LegacyHandler(self.mock_server)
        
        assert handler.category == "legacy"
        tools = handler.get_tool_names()
        
        expected_tools = [
            "create_unified_checklist", "update_checklist_item", "get_checklist_progress",
            "create_todowrite_integration", "create_memory_entity", "create_workflow",
            "validate_command", "track_command_pattern", "get_pattern_recommendations",
            "compact_memory_graph"
        ]
        
        assert len(tools) == 10
        for tool in expected_tools:
            assert tool in tools
            
    @pytest.mark.asyncio
    async def test_handler_tool_dispatch(self):
        """Test tool dispatch through handlers."""
        # Test hierarchical handler
        handler = HierarchicalManagementHandler(self.mock_server)
        result = await handler.handle("create_hierarchical_task", {"test": "data"})
        
        assert len(result) == 1
        assert result[0].text == "Mock hierarchical task created"
        assert ("create_hierarchical_task", {"test": "data"}) in self.mock_server.call_log
        
    @pytest.mark.asyncio
    async def test_handler_unknown_tool(self):
        """Test handlers handle unknown tools gracefully."""
        handler = ValidationHandler(self.mock_server)
        result = await handler.handle("unknown_tool", {})
        
        assert len(result) == 1
        assert "Unknown validation tool: unknown_tool" in result[0].text
        
    @pytest.mark.asyncio
    async def test_handler_error_handling(self):
        """Test handler error handling."""
        # Create handler with server that raises exception
        error_server = Mock()
        error_server._handle_validate_file_operation = AsyncMock(side_effect=RuntimeError("Test error"))
        
        handler = ValidationHandler(error_server)
        result = await handler.handle("validate_file_operation", {})
        
        assert len(result) == 1
        assert "Validation Error: Test error" in result[0].text
        
    def test_all_handlers_total_tools(self):
        """Test that all handlers together account for all 58 tools."""
        handlers = [
            TaskManagementHandler(self.mock_storage, None),
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
        
        total_tools = sum(len(handler.get_tool_names()) for handler in handlers)
        assert total_tools == 58, f"Expected 58 tools, got {total_tools}"
        
        # Verify no duplicate tools across handlers
        all_tools = []
        for handler in handlers:
            all_tools.extend(handler.get_tool_names())
            
        assert len(all_tools) == len(set(all_tools)), "Duplicate tools found across handlers"


if __name__ == "__main__":
    # Simple test runner for development
    print("🧪 Running ATLAS MCP Handler Tests")
    print("=" * 50)
    
    # Test handler creation and tool counts
    mock_server = MockServer()
    mock_storage = MockStorageManager()
    
    handlers = [
        ("TaskManagement", TaskManagementHandler(mock_storage, None)),
        ("HierarchicalManagement", HierarchicalManagementHandler(mock_server)),
        ("Validation", ValidationHandler(mock_server)),
        ("WorkflowIntelligence", WorkflowIntelligenceHandler(mock_server)),
        ("Observability", ObservabilityHandler(mock_server)),
        ("NestedStorage", NestedStorageHandler(mock_server)),
        ("MemoryManagement", MemoryManagementHandler(mock_server)),
        ("CacheManagement", CacheManagementHandler(mock_server)),
        ("Embeddings", EmbeddingsHandler(mock_server)),
        ("Legacy", LegacyHandler(mock_server))
    ]
    
    total_tools = 0
    for name, handler in handlers:
        tool_count = len(handler.get_tool_names())
        total_tools += tool_count
        print(f"✅ {name}: {tool_count} tools, category: {handler.category}")
    
    print(f"\n📊 Total Tools: {total_tools}/58")
    print(f"✅ All handlers created successfully!")
    print("\n🎉 Use pytest for comprehensive testing.")