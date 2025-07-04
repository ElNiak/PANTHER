"""
Base tool handler class with consistent error handling and logging.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List
from mcp.types import TextContent
import logging
import traceback
import os

# Import token optimization
from ..token_optimization import (
    optimize_tool_response, 
    success, 
    error, 
    progress,
    ContentType, 
    ResponseMode,
    set_response_mode
)

# Import the registry's ToolHandler interface
from ..tool_registry import ToolHandler


class BaseToolHandler(ToolHandler):
    """
    Base class for all tool handlers.
    
    Provides consistent error handling, logging, and common functionality
    that was missing in the original if-elif dispatcher.
    """
    
    def __init__(self, storage_manager=None, memory_manager=None):
        self.storage_manager = storage_manager
        self.memory_manager = memory_manager
        self.logger = logging.getLogger(f"{__name__}.{self.__class__.__name__}")
        
        # Configure token optimization based on environment
        self.token_mode = self._get_token_optimization_mode()
    
    @property
    @abstractmethod
    def category(self) -> str:
        """Return the category this handler belongs to."""
        pass
    
    @abstractmethod
    def get_tool_names(self) -> List[str]:
        """Return list of tool names this handler supports."""
        pass
    
    @abstractmethod
    async def _handle_tool(self, name: str, arguments: Dict[str, Any]) -> List[TextContent]:
        """
        Handle the actual tool logic.
        
        Subclasses implement this method with their specific tool logic.
        """
        pass
    
    async def handle(self, name: str, arguments: Dict[str, Any]) -> List[TextContent]:
        """
        Handle a tool call with consistent error handling and logging.
        
        This method wraps _handle_tool with error handling that was
        inconsistent across the original 44 tools.
        """
        try:
            self.logger.info(f"BaseHandler.handle called for tool: {name}")
            self.logger.debug(f"Tool arguments: {arguments}")
            
            # Validate tool name
            if name not in self.get_tool_names():
                error_msg = f"Tool '{name}' not supported by {self.__class__.__name__}"
                self.logger.error(error_msg)
                return [TextContent(type="text", text=error_msg)]
            
            # Delegate to specific handler
            self.logger.info(f"Calling _handle_tool for {name}")
            result = await self._handle_tool(name, arguments)
            
            self.logger.info(f"_handle_tool returned result type: {type(result)}")
            if hasattr(result, '__class__'):
                self.logger.info(f"Result class: {result.__class__}")
            
            # Check if result is a coroutine (this should not happen)
            import asyncio
            if asyncio.iscoroutine(result):
                self.logger.error(f"ERROR: _handle_tool returned a coroutine instead of actual result!")
                await result  # Await it to avoid ResourceWarning
                return [TextContent(type="text", text=f"Internal error: coroutine returned from {name}")]
            
            self.logger.info(f"Successfully handled tool: {name}")
            return result
            
        except KeyError as e:
            error_msg = f"Missing required argument for {name}: {str(e)}"
            self.logger.error(error_msg)
            return [TextContent(type="text", text=error_msg)]
            
        except ValueError as e:
            error_msg = f"Invalid argument for {name}: {str(e)}"
            self.logger.error(error_msg)
            return [TextContent(type="text", text=error_msg)]
            
        except Exception as e:
            error_msg = f"Unexpected error in {name}: {str(e)}"
            self.logger.error(f"{error_msg}\n{traceback.format_exc()}")
            return [TextContent(type="text", text=error_msg)]
    
    def _validate_required_args(self, arguments: Dict[str, Any], required: List[str]) -> None:
        """Validate that required arguments are present."""
        missing = [arg for arg in required if arg not in arguments]
        if missing:
            raise KeyError(f"Missing required arguments: {missing}")
    
    def _get_optional_arg(self, arguments: Dict[str, Any], key: str, default: Any = None) -> Any:
        """Get an optional argument with a default value."""
        return arguments.get(key, default)
    
    def _get_token_optimization_mode(self) -> ResponseMode:
        """Get token optimization mode from environment."""
        mode_str = os.environ.get('ATLAS_TOKEN_MODE', 'auto').lower()
        
        mode_mapping = {
            'auto': ResponseMode.AUTO,          # automatic optimization
            'minimal': ResponseMode.MINIMAL,    # 80% reduction
            'compact': ResponseMode.COMPACT,    # 60% reduction  
            'standard': ResponseMode.STANDARD,  # baseline
            'detailed': ResponseMode.DETAILED   # full output
        }
        
        return mode_mapping.get(mode_str, ResponseMode.AUTO)
    
    def optimize_response(self, data: Any, content_type: ContentType = ContentType.METADATA) -> List[TextContent]:
        """Optimize response based on configured token mode."""
        return optimize_tool_response(data, content_type, self.token_mode)
    
    def success_response(self, operation: str, **kwargs) -> List[TextContent]:
        """Create optimized success response."""
        return success(operation, **kwargs)
    
    def error_response(self, message: str, code: str = None) -> List[TextContent]:
        """Create optimized error response."""
        return error(message, code)
    
    def progress_response(self, percentage: float, phase: str = None) -> List[TextContent]:
        """Create optimized progress response."""
        return progress(percentage, phase)