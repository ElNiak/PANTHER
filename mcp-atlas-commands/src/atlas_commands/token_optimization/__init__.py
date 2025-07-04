"""
Token Optimization Module for ATLAS MCP Tools

Implements research-backed token optimization techniques:
- Collider-style filtering (35.1% reduction)
- Content pruning (32% reduction) 
- Progressive disclosure
- Semantic compression with information preservation

Target: 25-30% average token reduction across all tool responses.
"""

from .collider_filter import (
    ColliderStyleTokenFilter,
    FilteringStrategy,
    ContentPriority,
    TokenAnalysis,
    FilteringResult
)
from .token_optimizer import (
    TokenOptimizer,
    ResponseMode,
    ContentType,
    OptimizedResponse,
    optimize_tool_response,
    optimize_tool_response_with_collider,
    set_response_mode,
    get_response_mode,
    success,
    error,
    progress
)

__all__ = [
    'ColliderStyleTokenFilter',
    'FilteringStrategy', 
    'ContentPriority',
    'TokenAnalysis',
    'FilteringResult',
    'TokenOptimizer',
    'ResponseMode',
    'ContentType',
    'OptimizedResponse',
    'optimize_tool_response',
    'optimize_tool_response_with_collider',
    'set_response_mode',
    'get_response_mode',
    'success',
    'error',
    'progress'
]