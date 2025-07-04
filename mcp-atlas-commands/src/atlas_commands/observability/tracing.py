"""Distributed tracing decorators and utilities."""

import functools
import inspect
import logging
from typing import Callable, Any, Dict, Optional
from datetime import datetime

try:
    from opentelemetry import trace
    from opentelemetry.trace import Status, StatusCode
    OTEL_AVAILABLE = True
except ImportError:
    OTEL_AVAILABLE = False
    trace = None

logger = logging.getLogger(__name__)


def trace_mcp_tool(operation_name: Optional[str] = None,
                   record_args: bool = True,
                   record_result: bool = False):
    """Decorator to trace MCP tool operations.
    
    Args:
        operation_name: Custom operation name (defaults to function name)
        record_args: Whether to record function arguments as span attributes
        record_result: Whether to record return value (use carefully with large data)
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            if not OTEL_AVAILABLE:
                return await func(*args, **kwargs)
            
            span_name = operation_name or f"mcp.tool.{func.__name__}"
            tracer = trace.get_tracer(__name__)
            
            with tracer.start_as_current_span(span_name) as span:
                try:
                    # Add standard attributes
                    span.set_attribute("mcp.tool.name", func.__name__)
                    span.set_attribute("mcp.operation.type", "tool_call")
                    span.set_attribute("mcp.timestamp", datetime.utcnow().isoformat())
                    
                    # Record arguments if requested
                    if record_args:
                        _record_function_args(span, args, kwargs)
                    
                    # Execute function
                    start_time = datetime.utcnow()
                    result = await func(*args, **kwargs)
                    end_time = datetime.utcnow()
                    
                    # Record timing
                    duration_ms = (end_time - start_time).total_seconds() * 1000
                    span.set_attribute("mcp.duration_ms", duration_ms)
                    
                    # Record result if requested
                    if record_result:
                        _record_function_result(span, result)
                    
                    # Mark as successful
                    span.set_status(Status(StatusCode.OK))
                    
                    return result
                    
                except Exception as e:
                    # Record exception
                    span.record_exception(e)
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    span.set_attribute("mcp.error.type", type(e).__name__)
                    span.set_attribute("mcp.error.message", str(e))
                    raise
        
        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            if not OTEL_AVAILABLE:
                return func(*args, **kwargs)
            
            span_name = operation_name or f"mcp.tool.{func.__name__}"
            tracer = trace.get_tracer(__name__)
            
            with tracer.start_as_current_span(span_name) as span:
                try:
                    # Add standard attributes
                    span.set_attribute("mcp.tool.name", func.__name__)
                    span.set_attribute("mcp.operation.type", "tool_call")
                    span.set_attribute("mcp.timestamp", datetime.utcnow().isoformat())
                    
                    # Record arguments if requested
                    if record_args:
                        _record_function_args(span, args, kwargs)
                    
                    # Execute function
                    start_time = datetime.utcnow()
                    result = func(*args, **kwargs)
                    end_time = datetime.utcnow()
                    
                    # Record timing
                    duration_ms = (end_time - start_time).total_seconds() * 1000
                    span.set_attribute("mcp.duration_ms", duration_ms)
                    
                    # Record result if requested
                    if record_result:
                        _record_function_result(span, result)
                    
                    # Mark as successful
                    span.set_status(Status(StatusCode.OK))
                    
                    return result
                    
                except Exception as e:
                    # Record exception
                    span.record_exception(e)
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    span.set_attribute("mcp.error.type", type(e).__name__)
                    span.set_attribute("mcp.error.message", str(e))
                    raise
        
        # Return appropriate wrapper based on function type
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    
    return decorator


def trace_cache_operation(operation: str):
    """Decorator to trace cache operations.
    
    Args:
        operation: Cache operation type (get, set, invalidate, etc.)
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if not OTEL_AVAILABLE:
                return func(*args, **kwargs)
            
            tracer = trace.get_tracer(__name__)
            span_name = f"cache.{operation}"
            
            with tracer.start_as_current_span(span_name) as span:
                try:
                    # Add cache-specific attributes
                    span.set_attribute("cache.operation", operation)
                    span.set_attribute("cache.function", func.__name__)
                    
                    # Add cache key if available
                    if len(args) >= 2:  # Assuming (self, namespace, key, ...)
                        span.set_attribute("cache.namespace", str(args[1]))
                        if len(args) >= 3:
                            span.set_attribute("cache.key", str(args[2]))
                    
                    # Execute function
                    start_time = datetime.utcnow()
                    result = func(*args, **kwargs)
                    end_time = datetime.utcnow()
                    
                    # Record timing
                    duration_ms = (end_time - start_time).total_seconds() * 1000
                    span.set_attribute("cache.duration_ms", duration_ms)
                    
                    # Record cache hit/miss for get operations
                    if operation == "get":
                        hit = result is not None
                        span.set_attribute("cache.hit", hit)
                        span.set_attribute("cache.miss", not hit)
                    
                    span.set_status(Status(StatusCode.OK))
                    return result
                    
                except Exception as e:
                    span.record_exception(e)
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    raise
        
        return wrapper
    return decorator


def trace_task_operation(operation: str):
    """Decorator to trace task storage operations.
    
    Args:
        operation: Task operation type (create, update, get, list, etc.)
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if not OTEL_AVAILABLE:
                return func(*args, **kwargs)
            
            tracer = trace.get_tracer(__name__)
            span_name = f"task.{operation}"
            
            with tracer.start_as_current_span(span_name) as span:
                try:
                    # Add task-specific attributes
                    span.set_attribute("task.operation", operation)
                    span.set_attribute("task.function", func.__name__)
                    
                    # Extract common task parameters
                    if len(args) >= 2:  # Assuming (self, project_name, ...)
                        span.set_attribute("task.project", str(args[1]))
                        if len(args) >= 3:
                            span.set_attribute("task.id", str(args[2]))
                    
                    # Execute function
                    start_time = datetime.utcnow()
                    result = func(*args, **kwargs)
                    end_time = datetime.utcnow()
                    
                    # Record timing
                    duration_ms = (end_time - start_time).total_seconds() * 1000
                    span.set_attribute("task.duration_ms", duration_ms)
                    
                    # Record result metadata
                    if operation == "list" and isinstance(result, list):
                        span.set_attribute("task.count", len(result))
                    elif operation in ["create", "update"] and isinstance(result, dict):
                        span.set_attribute("task.status", result.get("status", "unknown"))
                    
                    span.set_status(Status(StatusCode.OK))
                    return result
                    
                except Exception as e:
                    span.record_exception(e)
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    raise
        
        return wrapper
    return decorator


def _record_function_args(span, args: tuple, kwargs: Dict[str, Any]) -> None:
    """Record function arguments as span attributes."""
    try:
        # Record arg count
        span.set_attribute("mcp.args.count", len(args))
        span.set_attribute("mcp.kwargs.count", len(kwargs))
        
        # Record specific kwargs (avoid sensitive data)
        safe_kwargs = {}
        for key, value in kwargs.items():
            if key.lower() in ['password', 'token', 'secret', 'key']:
                safe_kwargs[key] = '[REDACTED]'
            elif isinstance(value, (str, int, float, bool)):
                safe_kwargs[key] = value
            elif isinstance(value, (list, dict)):
                safe_kwargs[key] = f"<{type(value).__name__}:{len(value)}>"
            else:
                safe_kwargs[key] = str(type(value).__name__)
        
        for key, value in safe_kwargs.items():
            span.set_attribute(f"mcp.args.{key}", str(value))
            
    except Exception as e:
        logger.warning(f"Failed to record function args: {e}")


def _record_function_result(span, result: Any) -> None:
    """Record function result as span attributes."""
    try:
        if result is None:
            span.set_attribute("mcp.result.type", "None")
        elif isinstance(result, (str, int, float, bool)):
            span.set_attribute("mcp.result.type", type(result).__name__)
            span.set_attribute("mcp.result.value", str(result)[:100])  # Truncate long values
        elif isinstance(result, list):
            span.set_attribute("mcp.result.type", "list")
            span.set_attribute("mcp.result.count", len(result))
        elif isinstance(result, dict):
            span.set_attribute("mcp.result.type", "dict")
            span.set_attribute("mcp.result.keys", len(result))
        else:
            span.set_attribute("mcp.result.type", type(result).__name__)
            
    except Exception as e:
        logger.warning(f"Failed to record function result: {e}")


def get_current_span():
    """Get the current active span."""
    if not OTEL_AVAILABLE:
        return None
    return trace.get_current_span()


def add_span_event(name: str, attributes: Optional[Dict[str, Any]] = None):
    """Add an event to the current span."""
    if not OTEL_AVAILABLE:
        return
    
    span = get_current_span()
    if span:
        span.add_event(name, attributes or {})