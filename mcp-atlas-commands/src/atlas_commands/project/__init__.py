"""
ATLAS MCP Multi-Project Support

This package provides lightweight project isolation for ATLAS MCP by extending
existing components with project-scoped operations while maintaining backward
compatibility and following DRY, SOLID, and KISS principles.
"""

from .context_manager import (
    ProjectContextManager,
    ProjectContext,
    ProjectContextValidator,
    ProjectMismatchError,
    ContextViolationError,
    get_project_context_manager,
    reset_project_context_manager
)

from .decorators import (
    ProjectAwareTaskManager,
    ProjectAwareMemoryManager,
    ProjectAwareStorageManager
)

__all__ = [
    'ProjectContextManager',
    'ProjectContext', 
    'ProjectContextValidator',
    'ProjectMismatchError',
    'ContextViolationError',
    'get_project_context_manager',
    'reset_project_context_manager',
    'ProjectAwareTaskManager',
    'ProjectAwareMemoryManager',
    'ProjectAwareStorageManager'
]