"""
Tool handlers package for ATLAS MCP server.

This package contains all tool handlers organized by category
to replace the massive if-elif dispatcher chain.
"""

from .base import BaseToolHandler
from .task_management import TaskManagementHandler
from .hierarchical_management import HierarchicalManagementHandler
from .validation import ValidationHandler
from .workflow_intelligence import WorkflowIntelligenceHandler
from .observability import ObservabilityHandler
from .nested_storage import NestedStorageHandler
from .memory_management import MemoryManagementHandler
from .cache_management import CacheManagementHandler
from .embeddings import EmbeddingsHandler

__all__ = [
    'BaseToolHandler',
    'TaskManagementHandler',
    'HierarchicalManagementHandler',
    'ValidationHandler',
    'WorkflowIntelligenceHandler',
    'ObservabilityHandler',
    'NestedStorageHandler',
    'MemoryManagementHandler',
    'CacheManagementHandler',
    'EmbeddingsHandler',
]