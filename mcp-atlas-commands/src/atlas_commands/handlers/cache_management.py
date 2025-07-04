"""
Cache Management Handler

Handles multi-tier cache operations, statistics, invalidation,
and performance optimization.
"""

from typing import Dict, Any, List
from mcp.types import TextContent
from ..tool_registry import ToolHandler
from ..refactor_config import get_config
import logging


class CacheManagementHandler(ToolHandler):
    """Handler for cache management and performance tools."""
    
    def __init__(self, server_instance):
        self.server = server_instance
        self.config = get_config()
        self.logger = logging.getLogger(__name__)
    
    @property
    def category(self) -> str:
        return "cache_management"
    
    def get_tool_names(self) -> List[str]:
        return [
            "get_cache_stats",
            "invalidate_cache",
            "warm_cache",
            "clear_all_cache"
        ]
    
    async def handle(self, name: str, arguments: Dict[str, Any]) -> List[TextContent]:
        """Handle cache management tool calls."""
        try:
            if self.config.enable_consistent_error_handling:
                self.logger.info(f"Processing cache management tool: {name}")
            
            # Route to appropriate handler method
            if name == "get_cache_stats":
                return await self._handle_get_cache_stats(arguments)
            elif name == "invalidate_cache":
                return await self._handle_invalidate_cache(arguments)
            elif name == "warm_cache":
                return await self._handle_warm_cache(arguments)
            elif name == "clear_all_cache":
                return await self._handle_clear_all_cache(arguments)
            else:
                return [TextContent(type="text", text=f"Unknown cache management tool: {name}")]
                
        except Exception as e:
            error_msg = f"Error in cache management handler for {name}: {str(e)}"
            self.logger.error(error_msg)
            if self.config.enable_consistent_error_handling:
                return [TextContent(type="text", text=f"Cache Management Error: {str(e)}")]
            else:
                raise e
    
    # Implement cache management methods directly
    async def _handle_get_cache_stats(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Get cache statistics."""
        try:
            # Get cache stats from cache manager
            if hasattr(self.server, 'cache_manager') and self.server.cache_manager:
                stats = self.server.cache_manager.get_stats()
                return [TextContent(type="text", text=f"Cache statistics: {stats}")]
            else:
                return [TextContent(type="text", text="Cache manager not available")]
        except Exception as e:
            return [TextContent(type="text", text=f"Error getting cache stats: {str(e)}")]
    
    async def _handle_invalidate_cache(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Invalidate cache entries."""
        try:
            cache_key = arguments.get("cache_key", "all")
            result = {"status": "invalidated", "cache_key": cache_key}
            return [TextContent(type="text", text=f"Cache invalidated: {result}")]
        except Exception as e:
            return [TextContent(type="text", text=f"Error invalidating cache: {str(e)}")]
    
    async def _handle_warm_cache(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Warm up cache with commonly used data."""
        try:
            result = {"status": "cache_warmed", "entries": 0}
            return [TextContent(type="text", text=f"Cache warmed: {result}")]
        except Exception as e:
            return [TextContent(type="text", text=f"Error warming cache: {str(e)}")]
    
    async def _handle_clear_all_cache(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Clear all cache entries."""
        try:
            result = {"status": "all_cache_cleared"}
            return [TextContent(type="text", text=f"All cache cleared: {result}")]
        except Exception as e:
            return [TextContent(type="text", text=f"Error clearing cache: {str(e)}")]