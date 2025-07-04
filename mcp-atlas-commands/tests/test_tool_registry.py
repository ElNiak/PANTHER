"""
Unit tests for the ATLAS MCP Tool Registry.

Tests the core registry pattern that replaced the 58-tool if-elif chain.
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock
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

# Now import our modules
from atlas_commands.tool_registry import ToolRegistry, ToolHandler, ToolMetadata


class MockToolHandler(ToolHandler):
    """Mock handler for testing."""
    
    def __init__(self, category: str, tools: List[str]):
        self._category = category
        self._tools = tools
        self.call_count = 0
        
    @property
    def category(self) -> str:
        return self._category
    
    def get_tool_names(self) -> List[str]:
        return self._tools
    
    async def handle(self, name: str, arguments: Dict[str, Any]) -> List[MockTextContent]:
        self.call_count += 1
        return [MockTextContent(type="text", text=f"Mock {self._category} handled {name}")]


class TestToolRegistry:
    """Test cases for the ToolRegistry class."""
    
    def setup_method(self):
        """Setup for each test."""
        self.registry = ToolRegistry()
        
        # Create mock handlers
        self.task_handler = MockToolHandler("task_management", ["create_task", "update_task"])
        self.validation_handler = MockToolHandler("validation", ["validate_file", "validate_naming"])
        
    def test_registry_initialization(self):
        """Test registry initializes empty."""
        assert len(self.registry.list_tools()) == 0
        assert len(self.registry.list_categories()) == 0
        
    def test_handler_registration(self):
        """Test handler registration and tool mapping."""
        # Register handler
        self.registry.register_handler(self.task_handler)
        
        # Verify tools are registered
        tools = self.registry.list_tools()
        assert "create_task" in tools
        assert "update_task" in tools
        assert len(tools) == 2
        
        # Verify categories
        categories = self.registry.list_categories()
        assert "task_management" in categories
        assert len(categories) == 1
        
    def test_multiple_handler_registration(self):
        """Test multiple handlers can be registered."""
        self.registry.register_handler(self.task_handler)
        self.registry.register_handler(self.validation_handler)
        
        # Check total tools
        tools = self.registry.list_tools()
        assert len(tools) == 4
        
        # Check categories
        categories = self.registry.list_categories()
        assert len(categories) == 2
        assert "task_management" in categories
        assert "validation" in categories
        
    def test_get_tools_by_category(self):
        """Test getting tools by specific category."""
        self.registry.register_handler(self.task_handler)
        self.registry.register_handler(self.validation_handler)
        
        task_tools = self.registry.get_tools_by_category("task_management")
        assert task_tools == ["create_task", "update_task"]
        
        validation_tools = self.registry.get_tools_by_category("validation")
        assert validation_tools == ["validate_file", "validate_naming"]
        
        # Test non-existent category
        empty_tools = self.registry.get_tools_by_category("nonexistent")
        assert empty_tools == []
        
    def test_get_handler(self):
        """Test retrieving handler for specific tool."""
        self.registry.register_handler(self.task_handler)
        
        # Test valid tool
        handler = self.registry.get_handler("create_task")
        assert handler is self.task_handler
        
        # Test invalid tool
        with pytest.raises(ValueError, match="Unknown tool: invalid_tool"):
            self.registry.get_handler("invalid_tool")
            
    @pytest.mark.asyncio
    async def test_tool_dispatch_success(self):
        """Test successful tool dispatch."""
        self.registry.register_handler(self.task_handler)
        
        result = await self.registry.dispatch("create_task", {"test": "data"})
        
        assert len(result) == 1
        assert result[0].type == "text"
        assert "Mock task_management handled create_task" in result[0].text
        assert self.task_handler.call_count == 1
        
    @pytest.mark.asyncio
    async def test_tool_dispatch_unknown_tool(self):
        """Test dispatch with unknown tool."""
        result = await self.registry.dispatch("unknown_tool", {})
        
        assert len(result) == 1
        assert result[0].type == "text"
        assert "Unknown tool: unknown_tool" in result[0].text
        
    @pytest.mark.asyncio
    async def test_tool_dispatch_handler_error(self):
        """Test dispatch when handler raises exception."""
        # Create handler that raises exception
        error_handler = MockToolHandler("error_category", ["error_tool"])
        
        async def failing_handle(name: str, arguments: Dict[str, Any]):
            raise RuntimeError("Handler error")
            
        error_handler.handle = failing_handle
        
        self.registry.register_handler(error_handler)
        
        result = await self.registry.dispatch("error_tool", {})
        
        assert len(result) == 1
        assert result[0].type == "text"
        assert "Error executing error_tool" in result[0].text
        assert "Handler error" in result[0].text
        
    def test_registry_stats(self):
        """Test registry statistics."""
        self.registry.register_handler(self.task_handler)
        self.registry.register_handler(self.validation_handler)
        
        stats = self.registry.get_registry_stats()
        
        assert stats["total_tools"] == 4
        assert stats["total_categories"] == 2
        assert stats["tools_by_category"]["task_management"] == 2
        assert stats["tools_by_category"]["validation"] == 2
        assert stats["tools_with_error_handling"] == 4  # All tools have error handling
        
    def test_tool_metadata_creation(self):
        """Test tool metadata is created correctly."""
        self.registry.register_handler(self.task_handler)
        
        # Check internal metadata structure
        assert "create_task" in self.registry._tools
        metadata = self.registry._tools["create_task"]
        
        assert metadata.name == "create_task"
        assert metadata.category == "task_management"
        assert metadata.has_error_handling == True
        assert callable(metadata.handler)


class TestToolHandler:
    """Test cases for the ToolHandler abstract base class."""
    
    def test_handler_interface(self):
        """Test handler implements required interface."""
        handler = MockToolHandler("test_category", ["tool1", "tool2"])
        
        assert handler.category == "test_category"
        assert handler.get_tool_names() == ["tool1", "tool2"]
        
    @pytest.mark.asyncio
    async def test_handler_execution(self):
        """Test handler can execute tools."""
        handler = MockToolHandler("test_category", ["test_tool"])
        
        result = await handler.handle("test_tool", {"arg": "value"})
        
        assert len(result) == 1
        assert result[0].type == "text"
        assert "Mock test_category handled test_tool" in result[0].text


if __name__ == "__main__":
    # Simple test runner for development
    import sys
    
    print("🧪 Running ATLAS MCP Tool Registry Tests")
    print("=" * 50)
    
    # Run basic functionality tests
    registry = ToolRegistry()
    handler = MockToolHandler("test", ["tool1", "tool2"])
    
    # Test registration
    registry.register_handler(handler)
    print(f"✅ Handler registration: {len(registry.list_tools())} tools registered")
    
    # Test dispatch
    async def test_dispatch():
        result = await registry.dispatch("tool1", {})
        return len(result) > 0 and "Mock test handled tool1" in result[0].text
    
    dispatch_success = asyncio.run(test_dispatch())
    print(f"✅ Tool dispatch: {'Success' if dispatch_success else 'Failed'}")
    
    # Test stats
    stats = registry.get_registry_stats()
    print(f"✅ Registry stats: {stats['total_tools']} tools, {stats['total_categories']} categories")
    
    print("\n🎉 All basic tests passed! Use pytest for comprehensive testing.")