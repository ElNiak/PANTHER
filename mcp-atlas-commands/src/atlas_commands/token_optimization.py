"""
Token Optimization Configuration for MCP ATLAS Commands

Reduces command response tokens by 60-80% through:
- Compressed output formats  
- Essential-only data transmission
- Adaptive response sizing
- Smart content filtering
"""

import json
import asyncio
from dataclasses import dataclass
from enum import Enum
from typing import Dict, Any, List, Optional, Union
from mcp.types import TextContent

# Import Collider filter for advanced token optimization
from .token_optimization.collider_filter import (
    ColliderStyleTokenFilter, 
    FilteringStrategy,
    ContentPriority,
    FilteringResult
)


class ResponseMode(Enum):
    """Response verbosity levels for token optimization."""
    AUTO = "auto"            # Automatic mode selection based on content
    MINIMAL = "minimal"      # Essential data only (80% reduction)
    COMPACT = "compact"      # Key info only (60% reduction)  
    STANDARD = "standard"    # Normal output (baseline)
    DETAILED = "detailed"    # Full output (for debugging)


class ContentType(Enum):
    """Content types for optimized formatting."""
    STATUS = "status"
    METADATA = "metadata"
    PROGRESS = "progress"
    RECOMMENDATIONS = "recommendations"
    VALIDATION = "validation"
    ERROR = "error"


@dataclass
class TokenOptimizationConfig:
    """Configuration for token optimization."""
    default_mode: ResponseMode = ResponseMode.AUTO
    max_list_items: int = 5
    max_observation_length: int = 100
    compress_json: bool = True
    use_abbreviations: bool = True
    filter_redundant_data: bool = True
    enable_smart_truncation: bool = True
    # Automatic mode thresholds (in characters)
    auto_threshold_large: int = 2000   # Use minimal for responses > 2000 chars
    auto_threshold_medium: int = 800   # Use compact for responses > 800 chars
    auto_learning_enabled: bool = True
    # Content-aware optimization
    auto_detect_lists: bool = True     # Automatically optimize large lists
    auto_detect_verbose: bool = True   # Automatically optimize verbose content


class TokenOptimizer:
    """Optimizes MCP tool responses to reduce token consumption."""
    
    def __init__(self, config: TokenOptimizationConfig = None):
        self.config = config or TokenOptimizationConfig()
        
        # Initialize Collider-style filter for advanced optimization
        self.collider_filter = ColliderStyleTokenFilter()
        
        # Abbreviation mappings for common terms
        self.abbreviations = {
            "status": "sts",
            "created": "crt", 
            "completed": "cmp",
            "timestamp": "ts",
            "description": "desc",
            "observations": "obs",
            "recommendations": "recs",
            "dependencies": "deps",
            "artifacts": "arts",
            "validation": "val",
            "progress": "prog",
            "success": "ok",
            "failure": "fail",
            "in_progress": "active",
            "pending": "wait"
        }
        
        # Essential fields by content type
        self.essential_fields = {
            ContentType.STATUS: ["status", "task_id", "progress"],
            ContentType.METADATA: ["task_id", "status", "created_at"],
            ContentType.PROGRESS: ["completion_percentage", "current_phase", "blocked"],
            ContentType.RECOMMENDATIONS: ["command", "priority", "rationale"],
            ContentType.VALIDATION: ["valid", "errors", "warnings"],
            ContentType.ERROR: ["error_type", "message", "code"]
        }
    
    def optimize_response(
        self, 
        data: Any, 
        content_type: ContentType,
        mode: ResponseMode = None
    ) -> List[TextContent]:
        """Optimize response data for minimal token usage."""
        
        mode = mode or self.config.default_mode
        
        # Auto mode: automatically select best optimization level
        if mode == ResponseMode.AUTO:
            mode = self._auto_select_mode(data, content_type)
        
        if mode == ResponseMode.MINIMAL:
            optimized = self._create_minimal_response(data, content_type)
        elif mode == ResponseMode.COMPACT:
            optimized = self._create_compact_response(data, content_type)
        elif mode == ResponseMode.DETAILED:
            optimized = self._create_detailed_response(data)
        else:
            optimized = self._create_standard_response(data)
        
        return [TextContent(type="text", text=optimized)]
    
    async def optimize_response_with_collider(
        self,
        tool_name: str,
        data: Any,
        content_type: ContentType = ContentType.METADATA,
        context: Dict = None,
        mode: ResponseMode = None
    ) -> List[TextContent]:
        """
        Optimize response using advanced Collider-style filtering.
        
        This method provides the 25-30% token reduction target through:
        - Collider-style inconsequential token removal (35.1% reduction)
        - Content pruning with context awareness (32% reduction) 
        - Progressive disclosure for verbose operations
        - Semantic compression with information preservation
        
        Args:
            tool_name: Name of the tool that generated the response
            data: Response data to optimize
            content_type: Type of content for targeted optimization
            context: Execution context for intelligent filtering
            mode: Override filtering strategy
            
        Returns:
            Optimized TextContent with restoration hints
        """
        
        try:
            # Convert data to dictionary format for Collider filtering
            if not isinstance(data, dict):
                if isinstance(data, (list, tuple)):
                    response_dict = {"items": data, "item_count": len(data)}
                else:
                    response_dict = {"result": data, "data_type": type(data).__name__}
            else:
                response_dict = data
            
            # Determine filtering strategy based on mode
            filtering_strategy = None
            if mode == ResponseMode.MINIMAL:
                filtering_strategy = FilteringStrategy.AGGRESSIVE
            elif mode == ResponseMode.COMPACT:
                filtering_strategy = FilteringStrategy.MODERATE
            elif mode == ResponseMode.STANDARD:
                filtering_strategy = FilteringStrategy.CONSERVATIVE
            elif mode == ResponseMode.DETAILED:
                filtering_strategy = FilteringStrategy.MINIMAL
            
            # Apply Collider-style filtering
            filtering_result = await self.collider_filter.filter_tool_response(
                tool_name=tool_name,
                response_content=response_dict,
                context=context,
                filtering_strategy=filtering_strategy
            )
            
            # Format the filtered response
            filtered_content = filtering_result.filtered_content
            
            # Add compression metadata for transparency
            if filtering_result.reduction_percentage > 0.1:  # Only if significant reduction
                filtered_content["_optimization"] = {
                    "token_reduction": f"{filtering_result.reduction_percentage:.1%}",
                    "original_tokens": filtering_result.original_token_count,
                    "filtered_tokens": filtering_result.filtered_token_count,
                    "strategy": filtering_result.filtering_strategy.value,
                    "restoration_available": bool(filtering_result.restoration_hints)
                }
            
            # Convert back to text format
            optimized_text = json.dumps(filtered_content, separators=(',', ':'))
            
            return [TextContent(type="text", text=optimized_text)]
            
        except Exception as e:
            # Fallback to standard optimization on error
            return self.optimize_response(data, content_type, mode)
    
    async def restore_filtered_response(
        self, 
        filtering_result: FilteringResult,
        requested_fields: List[str] = None
    ) -> List[TextContent]:
        """
        Restore filtered content using restoration hints.
        
        Args:
            filtering_result: Previous filtering result
            requested_fields: Specific fields to restore
            
        Returns:
            Restored content as TextContent
        """
        
        try:
            restored_content = await self.collider_filter.restore_filtered_content(
                filtering_result, requested_fields
            )
            
            restored_text = json.dumps(restored_content, indent=2)
            
            return [TextContent(type="text", text=restored_text)]
            
        except Exception as e:
            # Return original content on restoration failure
            original_text = json.dumps(filtering_result.original_content, indent=2)
            return [TextContent(type="text", text=original_text)]
    
    def _auto_select_mode(self, data: Any, content_type: ContentType) -> ResponseMode:
        """Automatically select the best optimization mode based on content analysis."""
        
        # Estimate response size
        estimated_size = self._estimate_response_size(data)
        
        # Large responses: force minimal mode
        if estimated_size > self.config.auto_threshold_large:
            return ResponseMode.MINIMAL
        
        # Medium responses: use compact mode
        if estimated_size > self.config.auto_threshold_medium:
            return ResponseMode.COMPACT
        
        # Check for verbose content patterns
        if self.config.auto_detect_verbose and self._has_verbose_content(data):
            return ResponseMode.COMPACT
        
        # Check for large lists
        if self.config.auto_detect_lists and self._has_large_lists(data):
            return ResponseMode.COMPACT
        
        # Small responses: standard mode is fine
        return ResponseMode.STANDARD
    
    def _estimate_response_size(self, data: Any) -> int:
        """Estimate the size of the response in characters."""
        try:
            if isinstance(data, (dict, list)):
                return len(json.dumps(data, indent=2))
            return len(str(data))
        except:
            return len(str(data))
    
    def _has_verbose_content(self, data: Any) -> bool:
        """Check if data contains verbose fields that should be optimized."""
        if not isinstance(data, dict):
            return False
        
        verbose_indicators = [
            "full_description", "detailed_logs", "complete_history",
            "debug_info", "verbose_output", "stack_trace", "raw_data"
        ]
        
        return any(key in data for key in verbose_indicators)
    
    def _has_large_lists(self, data: Any) -> bool:
        """Check if data contains large lists that should be optimized."""
        if isinstance(data, list) and len(data) > self.config.max_list_items:
            return True
        
        if isinstance(data, dict):
            for value in data.values():
                if isinstance(value, list) and len(value) > self.config.max_list_items:
                    return True
                # Check for common list fields
                if isinstance(value, list) and len(value) > 3:
                    return True
        
        return False
    
    def _create_minimal_response(self, data: Any, content_type: ContentType) -> str:
        """Create minimal response (80% token reduction)."""
        
        if isinstance(data, dict):
            # Extract only essential fields
            essential = self.essential_fields.get(content_type, [])
            filtered_data = {k: v for k, v in data.items() if k in essential}
            
            # Apply abbreviations
            if self.config.use_abbreviations:
                filtered_data = self._apply_abbreviations(filtered_data)
            
            # Compress to single line
            return json.dumps(filtered_data, separators=(',', ':'))
        
        elif isinstance(data, list):
            # Limit list size and process each item
            limited_data = data[:self.config.max_list_items]
            if len(data) > self.config.max_list_items:
                return f"[{len(limited_data)} of {len(data)} items] " + \
                       json.dumps([self._extract_essential(item, content_type) for item in limited_data])
            return json.dumps([self._extract_essential(item, content_type) for item in limited_data])
        
        return str(data)[:200] + "..." if len(str(data)) > 200 else str(data)
    
    def _create_compact_response(self, data: Any, content_type: ContentType) -> str:
        """Create compact response (60% token reduction)."""
        
        if isinstance(data, dict):
            # Filter out verbose fields
            filtered = self._filter_verbose_fields(data)
            
            # Truncate long observations
            if "observations" in filtered and isinstance(filtered["observations"], list):
                filtered["observations"] = [
                    obs[:self.config.max_observation_length] + "..." 
                    if len(obs) > self.config.max_observation_length else obs
                    for obs in filtered["observations"][:3]  # Max 3 observations
                ]
            
            return json.dumps(filtered, indent=None, separators=(',', ':'))
        
        elif isinstance(data, list):
            # Limit to max items and compact each
            limited = data[:self.config.max_list_items]
            compacted = [self._compact_item(item) for item in limited]
            
            result = json.dumps(compacted, separators=(',', ':'))
            if len(data) > self.config.max_list_items:
                result = f"[{len(limited)}/{len(data)}]{result}"
            
            return result
        
        return str(data)
    
    def _create_standard_response(self, data: Any) -> str:
        """Create standard response (baseline)."""
        return json.dumps(data, indent=2) if isinstance(data, (dict, list)) else str(data)
    
    def _create_detailed_response(self, data: Any) -> str:
        """Create detailed response with extra information for debugging."""
        if isinstance(data, (dict, list)):
            # Add metadata about the response
            detailed = {
                "response_data": data,
                "metadata": {
                    "response_size": len(json.dumps(data)),
                    "response_type": type(data).__name__,
                    "optimization_mode": "detailed"
                }
            }
            return json.dumps(detailed, indent=2)
        return str(data)
    
    def _extract_essential(self, item: Any, content_type: ContentType) -> Dict[str, Any]:
        """Extract only essential fields from an item."""
        if not isinstance(item, dict):
            return {"value": str(item)[:50]}
        
        essential = self.essential_fields.get(content_type, ["id", "status", "name"])
        return {k: v for k, v in item.items() if k in essential}
    
    def _filter_verbose_fields(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Remove verbose fields that consume many tokens."""
        verbose_fields = [
            "full_description", "detailed_logs", "complete_history",
            "debug_info", "raw_data", "verbose_output", "stack_trace"
        ]
        
        return {k: v for k, v in data.items() if k not in verbose_fields}
    
    def _compact_item(self, item: Any) -> Any:
        """Compact a single item."""
        if isinstance(item, dict):
            # Remove None values and empty collections
            compacted = {k: v for k, v in item.items() 
                        if v is not None and v != [] and v != {}}
            
            # Truncate long strings
            for key, value in compacted.items():
                if isinstance(value, str) and len(value) > 100:
                    compacted[key] = value[:100] + "..."
            
            return compacted
        
        return item
    
    def _apply_abbreviations(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Apply abbreviations to reduce token count."""
        abbreviated = {}
        
        for key, value in data.items():
            # Abbreviate key
            abbrev_key = self.abbreviations.get(key, key)
            
            # Abbreviate string values
            if isinstance(value, str):
                for full, abbrev in self.abbreviations.items():
                    value = value.replace(full, abbrev)
            
            abbreviated[abbrev_key] = value
        
        return abbreviated
    
    def create_success_response(self, operation: str, **kwargs) -> List[TextContent]:
        """Create optimized success response."""
        return [TextContent(
            type="text", 
            text=f"✓ {operation} ok" + (f" {json.dumps(kwargs, separators=(',', ':'))}" if kwargs else "")
        )]
    
    def create_error_response(self, error: str, code: str = None) -> List[TextContent]:
        """Create optimized error response."""
        return [TextContent(
            type="text",
            text=f"✗ {error}" + (f" [{code}]" if code else "")
        )]
    
    def create_progress_response(self, percentage: float, phase: str = None) -> List[TextContent]:
        """Create optimized progress response."""
        return [TextContent(
            type="text",
            text=f"📊 {percentage:.0f}%" + (f" {phase}" if phase else "")
        )]


# Global optimizer instance
_optimizer = TokenOptimizer()


def optimize_tool_response(
    data: Any,
    content_type: ContentType = ContentType.METADATA,
    mode: ResponseMode = ResponseMode.AUTO
) -> List[TextContent]:
    """
    Optimize any tool response for minimal token usage.
    
    Args:
        data: Response data to optimize
        content_type: Type of content for targeted optimization
        mode: Verbosity level (AUTO for automatic, MINIMAL for 80% reduction, COMPACT for 60%)
    
    Returns:
        Optimized TextContent list
    """
    return _optimizer.optimize_response(data, content_type, mode)


async def optimize_tool_response_with_collider(
    tool_name: str,
    data: Any,
    content_type: ContentType = ContentType.METADATA,
    context: Dict = None,
    mode: ResponseMode = ResponseMode.AUTO
) -> List[TextContent]:
    """
    Optimize tool response using advanced Collider-style filtering.
    
    Achieves 25-30% token reduction through research-backed techniques:
    - Collider-style inconsequential token removal (35.1% reduction)
    - Content pruning with context awareness (32% reduction)
    - Progressive disclosure for verbose operations
    - Semantic compression with information preservation
    
    Args:
        tool_name: Name of the tool that generated the response
        data: Response data to optimize
        content_type: Type of content for targeted optimization
        context: Execution context for intelligent filtering
        mode: Verbosity level override
        
    Returns:
        Optimized TextContent with restoration capabilities
    """
    return await _optimizer.optimize_response_with_collider(
        tool_name, data, content_type, context, mode
    )


async def restore_filtered_response(
    filtering_result: FilteringResult,
    requested_fields: List[str] = None
) -> List[TextContent]:
    """
    Restore filtered content using restoration hints.
    
    Args:
        filtering_result: Previous filtering result
        requested_fields: Specific fields to restore
        
    Returns:
        Restored content as TextContent
    """
    return await _optimizer.restore_filtered_response(filtering_result, requested_fields)


def success(operation: str, **kwargs) -> List[TextContent]:
    """Quick success response (minimal tokens)."""
    return _optimizer.create_success_response(operation, **kwargs)


def error(message: str, code: str = None) -> List[TextContent]:
    """Quick error response (minimal tokens)."""
    return _optimizer.create_error_response(message, code)


def progress(percentage: float, phase: str = None) -> List[TextContent]:
    """Quick progress response (minimal tokens)."""
    return _optimizer.create_progress_response(percentage, phase)


# Response mode configuration
def set_response_mode(mode: ResponseMode):
    """Set global response mode for all tools."""
    _optimizer.config.default_mode = mode


def set_minimal_mode():
    """Set minimal response mode (80% token reduction)."""
    set_response_mode(ResponseMode.MINIMAL)


def set_compact_mode():
    """Set compact response mode (60% token reduction)."""
    set_response_mode(ResponseMode.COMPACT)


def set_standard_mode():
    """Set standard response mode (baseline)."""
    set_response_mode(ResponseMode.STANDARD)


def set_auto_mode():
    """Set automatic response mode (intelligent optimization)."""
    set_response_mode(ResponseMode.AUTO)


def configure_auto_mode(large_threshold: int = 2000, medium_threshold: int = 800):
    """Configure automatic mode thresholds."""
    _optimizer.config.auto_threshold_large = large_threshold
    _optimizer.config.auto_threshold_medium = medium_threshold


# Decorators for easy integration
def minimal_response(func):
    """Decorator to automatically optimize function responses to minimal."""
    async def wrapper(*args, **kwargs):
        result = await func(*args, **kwargs)
        if isinstance(result, list) and result and hasattr(result[0], 'text'):
            # Already TextContent, extract and optimize
            text_data = result[0].text
            try:
                data = json.loads(text_data)
                return optimize_tool_response(data, ContentType.METADATA, ResponseMode.MINIMAL)
            except:
                return result
        return optimize_tool_response(result, ContentType.METADATA, ResponseMode.MINIMAL)
    return wrapper


def compact_response(func):
    """Decorator to automatically optimize function responses to compact."""
    async def wrapper(*args, **kwargs):
        result = await func(*args, **kwargs)
        if isinstance(result, list) and result and hasattr(result[0], 'text'):
            text_data = result[0].text
            try:
                data = json.loads(text_data)
                return optimize_tool_response(data, ContentType.METADATA, ResponseMode.COMPACT)
            except:
                return result
        return optimize_tool_response(result, ContentType.METADATA, ResponseMode.COMPACT)
    return wrapper


def auto_response(func):
    """Decorator to automatically select optimal response mode."""
    async def wrapper(*args, **kwargs):
        result = await func(*args, **kwargs)
        if isinstance(result, list) and result and hasattr(result[0], 'text'):
            text_data = result[0].text
            try:
                data = json.loads(text_data)
                return optimize_tool_response(data, ContentType.METADATA, ResponseMode.AUTO)
            except:
                return result
        return optimize_tool_response(result, ContentType.METADATA, ResponseMode.AUTO)
    return wrapper