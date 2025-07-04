"""
Tool Registry Pattern for ATLAS MCP Server

This module implements a registry-based tool dispatcher to replace
the massive if-elif chain in the main server handler.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Callable, Awaitable
from dataclasses import dataclass
from mcp.types import TextContent
import logging


@dataclass
class ToolMetadata:
    """Metadata for a registered tool."""
    name: str
    category: str
    description: str
    handler: Callable[[Dict[str, Any]], Awaitable[List[TextContent]]]
    requires_auth: bool = False
    has_error_handling: bool = True


class ToolHandler(ABC):
    """Abstract base class for tool handlers."""
    
    @property
    @abstractmethod
    def category(self) -> str:
        """Return the category this handler belongs to."""
        pass
    
    @abstractmethod
    async def handle(self, name: str, arguments: Dict[str, Any]) -> List[TextContent]:
        """Handle the tool call."""
        pass
    
    @abstractmethod
    def get_tool_names(self) -> List[str]:
        """Return list of tool names this handler supports."""
        pass


class ToolRegistry:
    """
    Registry for managing tool handlers.
    
    Replaces the massive if-elif chain with a clean, extensible registry pattern.
    """
    
    def __init__(self):
        self._handlers: Dict[str, ToolHandler] = {}
        self._tools: Dict[str, ToolMetadata] = {}
        self._categories: Dict[str, List[str]] = {}
        self.logger = logging.getLogger(__name__)
    
    def register_handler(self, handler: ToolHandler) -> None:
        """Register a tool handler."""
        category = handler.category
        tool_names = handler.get_tool_names()
        
        # Register the handler
        self._handlers[category] = handler
        
        # Register individual tools
        for tool_name in tool_names:
            metadata = ToolMetadata(
                name=tool_name,
                category=category,
                description=f"Tool {tool_name} in category {category}",
                handler=handler.handle,
                has_error_handling=True  # Assume new handlers have error handling
            )
            self._tools[tool_name] = metadata
        
        # Update category mapping
        self._categories[category] = tool_names
        
        self.logger.info(f"Registered handler for category '{category}' with {len(tool_names)} tools")
    
    def get_handler(self, tool_name: str) -> ToolHandler:
        """Get the handler for a specific tool."""
        if tool_name not in self._tools:
            raise ValueError(f"Unknown tool: {tool_name}")
        
        metadata = self._tools[tool_name]
        return self._handlers[metadata.category]
    
    def list_tools(self) -> List[str]:
        """List all registered tools."""
        return list(self._tools.keys())
    
    def list_categories(self) -> List[str]:
        """List all tool categories."""
        return list(self._categories.keys())
    
    def get_tools_by_category(self, category: str) -> List[str]:
        """Get all tools in a specific category."""
        return self._categories.get(category, [])
    
    async def dispatch(self, tool_name: str, arguments: Dict[str, Any]) -> List[TextContent]:
            """
            Dispatch a tool call to the appropriate handler.
            
            This replaces the massive if-elif chain with clean registry lookup.
            """
            try:
                self.logger.info(f"ToolRegistry.dispatch called for: {tool_name}")
                
                if tool_name not in self._tools:
                    return [TextContent(type="text", text=f"Unknown tool: {tool_name}")]
                
                # Fix JSON serialization issue for complex object parameters
                processed_arguments = self._process_arguments(arguments)
                
                handler = self.get_handler(tool_name)
                self.logger.info(f"Got handler: {type(handler)} for tool: {tool_name}")
                
                self.logger.info(f"Calling handler.handle for {tool_name}")
                result = await handler.handle(tool_name, processed_arguments)
                
                self.logger.info(f"Handler returned result type: {type(result)}")
                
                # Check if result is a coroutine (this should not happen)
                import asyncio
                if asyncio.iscoroutine(result):
                    self.logger.error(f"ERROR: Handler returned a coroutine for {tool_name}!")
                    await result  # Await it to avoid ResourceWarning
                    return [TextContent(type="text", text=f"Internal coroutine error in {tool_name}")]
                
                return result
                
            except Exception as e:
                self.logger.error(f"Error dispatching tool {tool_name}: {str(e)}")
                import traceback
                self.logger.error(f"Traceback: {traceback.format_exc()}")
                return [TextContent(type="text", text=f"Error executing {tool_name}: {str(e)}")]
    
    def _process_arguments(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process and fix arguments that may have JSON serialization issues.
        
        Some MCP implementations pass complex objects as JSON strings instead of parsed objects.
        This method ensures all arguments are properly deserialized.
        """
        import json
        
        processed = {}
        
        for key, value in arguments.items():
            if isinstance(value, str):
                # Try to parse as JSON if it looks like a JSON object/array
                if (value.strip().startswith('{') and value.strip().endswith('}')) or \
                   (value.strip().startswith('[') and value.strip().endswith(']')):
                    try:
                        processed[key] = json.loads(value)
                        self.logger.debug(f"Parsed JSON string for argument '{key}'")
                    except json.JSONDecodeError:
                        # If parsing fails, keep as string
                        processed[key] = value
                else:
                    processed[key] = value
            else:
                processed[key] = value
        
        return processed
    
    def get_registry_stats(self) -> Dict[str, Any]:
        """Get statistics about the tool registry."""
        return {
            "total_tools": len(self._tools),
            "total_categories": len(self._categories),
            "tools_by_category": {cat: len(tools) for cat, tools in self._categories.items()},
            "tools_with_error_handling": sum(1 for tool in self._tools.values() if tool.has_error_handling)
        }