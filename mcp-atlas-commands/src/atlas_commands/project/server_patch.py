"""
Minimal Server Patch for Project Awareness

This module provides a minimal, non-intrusive way to add project awareness
to the existing EnhancedAtlasCommandsServer without modifying the core server code.

Design: Monkey patching with fallback to preserve existing functionality.
"""

import os
import logging
from typing import Optional

# Import project components
from .context_manager import get_project_context_manager, ProjectContextManager
from .decorators import ProjectAwareTaskManager, ProjectAwareMemoryManager
from .server_integration import (
    ProjectContextMiddleware,
    patch_tool_handlers_for_project_context,
    setup_project_context_logging,
    ensure_backward_compatibility
)

logger = logging.getLogger(__name__)


def patch_server_for_project_context(server_instance) -> bool:
    """
    Patch existing server instance with project awareness.
    
    This function adds project functionality to an existing server instance
    without modifying the original server class. It's designed to be safe
    and backward compatible.
    
    Returns True if project context was successfully enabled, False otherwise.
    """
    try:
        # Check if project context should be enabled
        if not _should_enable_project_context():
            logger.info("Project context disabled - running in single-project mode")
            return False
        
        # Ensure backward compatibility
        if not ensure_backward_compatibility():
            logger.warning("Backward compatibility check failed - disabling project context")
            return False
        
        # Initialize project context
        project_context = get_project_context_manager()
        server_instance.project_context = project_context
        server_instance.project_context_enabled = True
        
        # Setup project-specific logging
        setup_project_context_logging(project_context)
        
        # Create project-aware managers
        server_instance.project_task_manager = ProjectAwareTaskManager(project_context)
        server_instance.project_memory_manager = ProjectAwareMemoryManager(project_context)
        
        # Create middleware for request/response processing
        server_instance.project_middleware = ProjectContextMiddleware(server_instance)
        
        # Patch existing methods with project-aware versions
        _patch_server_methods(server_instance)
        
        # Patch tool handlers
        patch_tool_handlers_for_project_context(server_instance)
        
        logger.info(f"Project context successfully enabled for project: {project_context.project_id}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to enable project context: {e}")
        # Ensure server can still function without project context
        server_instance.project_context_enabled = False
        return False


def _should_enable_project_context() -> bool:
    """Check if project context should be enabled based on environment."""
    project_env_vars = [
        'ATLAS_PROJECT_ID',
        'ATLAS_WORKSPACE_ISOLATION', 
        'ATLAS_PROJECT_ROOT'
    ]
    
    return any(os.environ.get(var) for var in project_env_vars)


def _patch_server_methods(server_instance):
    """Patch server methods to use project-aware managers when available."""
    
    # Store original methods for fallback
    server_instance._original_get_storage_manager = getattr(server_instance, 'storage_manager', None)
    server_instance._original_get_memory_manager = getattr(server_instance, 'memory_manager', None)
    
    # Add getter methods for project-aware managers
    def get_effective_task_manager():
        """Get the appropriate task manager based on project context."""
        if (hasattr(server_instance, 'project_context_enabled') and 
            server_instance.project_context_enabled and
            hasattr(server_instance, 'project_task_manager')):
            return server_instance.project_task_manager
        return server_instance.storage_manager
    
    def get_effective_memory_manager():
        """Get the appropriate memory manager based on project context."""
        if (hasattr(server_instance, 'project_context_enabled') and 
            server_instance.project_context_enabled and
            hasattr(server_instance, 'project_memory_manager')):
            return server_instance.project_memory_manager
        return server_instance.memory_manager
    
    # Add methods to server instance
    server_instance.get_effective_task_manager = get_effective_task_manager
    server_instance.get_effective_memory_manager = get_effective_memory_manager


def create_project_aware_tool_wrapper(original_tool_method, server_instance):
    """
    Create a wrapper for tool methods that adds project context processing.
    
    This wrapper intercepts tool calls and adds project validation/processing
    while preserving the original tool behavior.
    """
    
    async def wrapped_tool_method(*args, **kwargs):
        # Check if project context is enabled
        if (hasattr(server_instance, 'project_context_enabled') and 
            server_instance.project_context_enabled and
            hasattr(server_instance, 'project_middleware')):
            
            try:
                # Process request with project context
                method_name = getattr(original_tool_method, '__name__', 'unknown')
                kwargs = server_instance.project_middleware.process_request(method_name, kwargs)
                
                # Call original tool method
                result = await original_tool_method(*args, **kwargs)
                
                # Process response with project context
                result = server_instance.project_middleware.process_response(method_name, result)
                
                return result
                
            except Exception as e:
                logger.error(f"Project context processing failed: {e}")
                # Fallback to original method
                return await original_tool_method(*args, **kwargs)
        else:
            # No project context - call original method directly
            return await original_tool_method(*args, **kwargs)
    
    return wrapped_tool_method


def apply_project_patches_to_tools(server_instance):
    """
    Apply project awareness patches to tool methods.
    
    This function wraps tool methods with project context processing
    while preserving all original functionality.
    """
    if not hasattr(server_instance, 'project_context_enabled') or not server_instance.project_context_enabled:
        return
    
    try:
        # List of tool methods that should have project context applied
        tool_methods_to_patch = [
            'create_task_metadata',
            'update_task_status', 
            'add_task_artifact',
            'get_task_context',
            'list_project_tasks',
            'create_hierarchical_task',
            'create_entities',
            'search_nodes',
            'create_relations',
            'read_graph'
        ]
        
        # Patch tool methods if they exist
        for method_name in tool_methods_to_patch:
            if hasattr(server_instance, method_name):
                original_method = getattr(server_instance, method_name)
                wrapped_method = create_project_aware_tool_wrapper(original_method, server_instance)
                setattr(server_instance, f'_original_{method_name}', original_method)
                setattr(server_instance, method_name, wrapped_method)
                logger.debug(f"Patched tool method: {method_name}")
        
        logger.info("Project patches applied to tool methods")
        
    except Exception as e:
        logger.error(f"Failed to apply project patches to tools: {e}")


def initialize_project_context_if_needed(server_class):
    """
    Class decorator to add project context initialization to server classes.
    
    This decorator can be applied to the existing server class to add
    project awareness without modifying the original class definition.
    """
    
    original_init = server_class.__init__
    
    def enhanced_init(self, *args, **kwargs):
        # Call original initialization
        original_init(self, *args, **kwargs)
        
        # Add project context if enabled
        project_enabled = patch_server_for_project_context(self)
        
        if project_enabled:
            # Apply project patches to tool methods
            apply_project_patches_to_tools(self)
            
            logger.info("Enhanced server initialization completed with project context")
        else:
            logger.info("Enhanced server initialization completed in single-project mode")
    
    server_class.__init__ = enhanced_init
    return server_class


# Environment variable configuration for project context
def configure_project_environment():
    """Configure environment variables for project context."""
    
    # Default configuration for backward compatibility
    defaults = {
        'ATLAS_PROJECT_ID': os.environ.get('ATLAS_PROJECT_ID', 'default'),
        'ATLAS_PROJECT_ROOT': os.environ.get('ATLAS_PROJECT_ROOT', '/app/workspace'),
        'ATLAS_CACHE_ROOT': os.environ.get('ATLAS_CACHE_ROOT', '/app/cache'),
        'ATLAS_WORKSPACE_ISOLATION': os.environ.get('ATLAS_WORKSPACE_ISOLATION', 'false')
    }
    
    # Only set defaults if not already configured
    for key, value in defaults.items():
        if key not in os.environ:
            os.environ[key] = value
    
    logger.debug(f"Project environment configured: {defaults}")


# Auto-configuration on import
configure_project_environment()