"""
Server Integration for ATLAS MCP Multi-Project Support

This module integrates project-aware components with the existing ATLAS server
while maintaining backward compatibility and minimal code changes.

Design Principles:
- Minimal changes to existing server initialization
- Backward compatible with single-project setups
- Project awareness is opt-in via environment variables
- Preserve all existing functionality and performance
"""

import os
import logging
from typing import Optional, Dict, Any

from .context_manager import (
    ProjectContextManager, 
    get_project_context_manager,
    ProjectMismatchError,
    ContextViolationError
)
from .decorators import (
    ProjectAwareTaskManager,
    ProjectAwareMemoryManager,
    ProjectAwareStorageManager
)

# Setup logging
logger = logging.getLogger(__name__)


class ProjectAwareServerMixin:
    """
    Mixin to add project awareness to existing ATLAS server.
    
    Design: Mixin pattern allows adding project functionality to existing
    server without modifying the base server class (Open/Closed Principle).
    """
    
    def __init__(self, *args, **kwargs):
        # Call parent constructor first
        super().__init__(*args, **kwargs)
        
        # Initialize project context if enabled
        self.project_context_enabled = self._should_enable_project_context()
        
        if self.project_context_enabled:
            self._initialize_project_context()
            self._wrap_managers_with_project_awareness()
            logger.info(f"Project context enabled for project: {self.project_context.project_id}")
        else:
            logger.info("Project context disabled - running in single-project mode")
    
    def _should_enable_project_context(self) -> bool:
        """Check if project context should be enabled based on environment."""
        # Enable if any project-specific environment variables are set
        project_env_vars = [
            'ATLAS_PROJECT_ID',
            'ATLAS_WORKSPACE_ISOLATION',
            'ATLAS_PROJECT_ROOT'
        ]
        
        return any(os.environ.get(var) for var in project_env_vars)
    
    def _initialize_project_context(self):
        """Initialize project context manager."""
        try:
            self.project_context = get_project_context_manager()
            logger.info(
                f"Initialized project context: {self.project_context.project_id} "
                f"(isolation={self.project_context.workspace_isolation})"
            )
        except Exception as e:
            logger.error(f"Failed to initialize project context: {e}")
            self.project_context_enabled = False
            raise
    
    def _wrap_managers_with_project_awareness(self):
        """Wrap existing managers with project-aware decorators."""
        if not hasattr(self, 'project_context'):
            return
        
        try:
            # Store original managers for fallback
            self._original_storage_manager = getattr(self, 'storage_manager', None)
            self._original_memory_manager = getattr(self, 'memory_manager', None)
            
            # Create project-aware managers that wrap existing ones
            self.project_task_manager = ProjectAwareTaskManager(self.project_context)
            self.project_memory_manager = ProjectAwareMemoryManager(self.project_context)
            self.project_storage_manager = ProjectAwareStorageManager(self.project_context)
            
            logger.info("Project-aware managers initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize project-aware managers: {e}")
            # Fallback to original managers
            self.project_context_enabled = False
            raise
    
    def get_task_manager(self):
        """Get appropriate task manager based on project context."""
        if self.project_context_enabled and hasattr(self, 'project_task_manager'):
            return self.project_task_manager
        return getattr(self, 'storage_manager', None)
    
    def get_memory_manager(self):
        """Get appropriate memory manager based on project context."""
        if self.project_context_enabled and hasattr(self, 'project_memory_manager'):
            return self.project_memory_manager
        return getattr(self, 'memory_manager', None)
    
    def get_storage_manager(self):
        """Get appropriate storage manager based on project context."""
        if self.project_context_enabled and hasattr(self, 'project_storage_manager'):
            return self.project_storage_manager
        return getattr(self, 'storage_manager', None)
    
    def validate_project_operation(self, operation: str, **kwargs) -> bool:
        """Validate operation against project context if enabled."""
        if not self.project_context_enabled:
            return True  # No validation needed in single-project mode
        
        try:
            validator = getattr(self.project_context, 'validator', None)
            if validator:
                return validator.validate_operation(operation, kwargs)
            return True
        except (ProjectMismatchError, ContextViolationError):
            raise
        except Exception as e:
            logger.warning(f"Project validation failed: {e}")
            return False


def create_project_aware_server(base_server_class):
    """
    Factory function to create project-aware server class.
    
    This allows adding project awareness to any existing server class
    without modifying the original class (Open/Closed Principle).
    """
    
    class ProjectAwareServer(ProjectAwareServerMixin, base_server_class):
        """Project-aware server that extends base server functionality."""
        
        def __init__(self, *args, **kwargs):
            # Initialize project awareness first
            super().__init__(*args, **kwargs)
            
            # Log server initialization
            if hasattr(self, 'project_context'):
                logger.info(
                    f"Project-aware ATLAS server initialized for project: "
                    f"{self.project_context.project_id}"
                )
            else:
                logger.info("ATLAS server initialized in single-project mode")
    
    return ProjectAwareServer


def patch_tool_handlers_for_project_context(server_instance):
    """
    Patch existing tool handlers to use project-aware managers.
    
    This function modifies existing tool handlers to use project-aware
    managers while preserving all existing functionality.
    """
    if not hasattr(server_instance, 'project_context_enabled') or not server_instance.project_context_enabled:
        return  # No patching needed for single-project mode
    
    try:
        # Patch task management handlers
        if hasattr(server_instance, '_tool_registry'):
            registry = server_instance._tool_registry
            
            # Get existing handlers
            task_handler = registry.get_handler('task_management')
            memory_handler = registry.get_handler('memory_management')
            
            if task_handler:
                # Replace storage manager in task handler with project-aware version
                task_handler.storage_manager = server_instance.get_task_manager()
                logger.info("Patched task management handler with project-aware manager")
            
            if memory_handler:
                # Replace memory manager in memory handler with project-aware version
                memory_handler.memory_manager = server_instance.get_memory_manager()
                logger.info("Patched memory management handler with project-aware manager")
        
        logger.info("Tool handlers successfully patched for project context")
        
    except Exception as e:
        logger.error(f"Failed to patch tool handlers: {e}")
        # Continue without project awareness
        server_instance.project_context_enabled = False


def add_project_validation_to_handler(handler_method):
    """
    Decorator to add project validation to existing handler methods.
    
    This decorator can be applied to existing MCP tool handler methods
    to add project validation without modifying the core logic.
    """
    
    def wrapper(self, *args, **kwargs):
        # Check if server has project context enabled
        server = getattr(self, 'server', None) or getattr(self, '_server', None)
        
        if server and hasattr(server, 'project_context_enabled') and server.project_context_enabled:
            try:
                # Validate project operation
                operation_name = handler_method.__name__
                server.validate_project_operation(operation_name, **kwargs)
            except (ProjectMismatchError, ContextViolationError) as e:
                logger.error(f"Project validation failed for {operation_name}: {e}")
                raise
            except Exception as e:
                logger.warning(f"Project validation error for {operation_name}: {e}")
                # Continue without validation
        
        # Call original handler method
        return handler_method(self, *args, **kwargs)
    
    return wrapper


class ProjectContextMiddleware:
    """
    Middleware to handle project context in MCP requests.
    
    Design: Middleware pattern allows intercepting and modifying
    requests/responses without changing core handler logic.
    """
    
    def __init__(self, server_instance):
        self.server = server_instance
        self.project_context_enabled = getattr(server_instance, 'project_context_enabled', False)
        
        if self.project_context_enabled:
            self.project_context = getattr(server_instance, 'project_context', None)
    
    def process_request(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Process incoming MCP request with project context."""
        if not self.project_context_enabled:
            return params  # No processing needed
        
        try:
            # Add project context to request params if not present
            if 'project_name' not in params and hasattr(self.project_context, 'project_id'):
                params['project_name'] = self.project_context.project_id
            
            # Validate project-related parameters
            if hasattr(self.server, 'validate_project_operation'):
                self.server.validate_project_operation(method, **params)
            
            logger.debug(f"Processed {method} request with project context")
            
        except (ProjectMismatchError, ContextViolationError):
            raise
        except Exception as e:
            logger.warning(f"Project context processing failed for {method}: {e}")
            # Continue without project processing
        
        return params
    
    def process_response(self, method: str, response: Any) -> Any:
        """Process outgoing MCP response with project context."""
        if not self.project_context_enabled:
            return response  # No processing needed
        
        try:
            # Add project metadata to response if it's a dict
            if isinstance(response, dict) and hasattr(self.project_context, 'project_id'):
                response['project_id'] = self.project_context.project_id
                response['project_context'] = self.project_context.get_project_context_dict()
            
            logger.debug(f"Processed {method} response with project context")
            
        except Exception as e:
            logger.warning(f"Project context response processing failed for {method}: {e}")
            # Continue without project processing
        
        return response


def setup_project_context_logging(project_context: ProjectContextManager):
    """Setup project-specific logging configuration."""
    try:
        # Create project-specific log file if workspace isolation is enabled
        if project_context.workspace_isolation:
            log_dir = project_context.get_project_scoped_path('logs')
            log_file = log_dir / f"atlas_{project_context.project_id}.log"
            
            # Add project-specific file handler
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(logging.INFO)
            
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - [%(project_id)s] - %(message)s'
            )
            file_handler.setFormatter(formatter)
            
            # Add project ID to log records
            class ProjectContextFilter(logging.Filter):
                def filter(self, record):
                    record.project_id = project_context.project_id
                    return True
            
            file_handler.addFilter(ProjectContextFilter())
            
            # Add handler to root logger
            logging.getLogger().addHandler(file_handler)
            
            logger.info(f"Project-specific logging configured: {log_file}")
    
    except Exception as e:
        logger.warning(f"Failed to setup project-specific logging: {e}")


# Backward compatibility check
def ensure_backward_compatibility():
    """Ensure project features don't break existing single-project setups."""
    
    # Check if running in compatibility mode
    if not os.environ.get('ATLAS_PROJECT_ID') and not os.environ.get('ATLAS_WORKSPACE_ISOLATION'):
        logger.info("Running in backward compatibility mode (single-project)")
        return True
    
    # Validate project environment configuration
    project_id = os.environ.get('ATLAS_PROJECT_ID', 'default')
    project_root = os.environ.get('ATLAS_PROJECT_ROOT', '/app/workspace')
    
    if not os.path.exists(project_root):
        logger.warning(f"Project root does not exist: {project_root}")
        return False
    
    logger.info(f"Project configuration validated: {project_id} at {project_root}")
    return True