"""Structured logging with OpenTelemetry correlation."""

import logging
import json
import sys
from typing import Dict, Any, Optional
from datetime import datetime

try:
    from opentelemetry import trace
    from opentelemetry.trace import get_current_span
    OTEL_AVAILABLE = True
except ImportError:
    OTEL_AVAILABLE = False
    trace = None


class StructuredFormatter(logging.Formatter):
    """JSON formatter with OpenTelemetry trace correlation."""
    
    def __init__(self, include_trace: bool = True, extra_fields: Optional[Dict[str, Any]] = None):
        """Initialize structured formatter.
        
        Args:
            include_trace: Whether to include trace/span IDs
            extra_fields: Additional fields to include in every log record
        """
        super().__init__()
        self.include_trace = include_trace and OTEL_AVAILABLE
        self.extra_fields = extra_fields or {}
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as structured JSON."""
        log_entry = {
            "timestamp": datetime.utcfromtimestamp(record.created).isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        # Add trace information if available
        if self.include_trace:
            trace_info = self._get_trace_info()
            if trace_info:
                log_entry.update(trace_info)
        
        # Add exception information if present
        if record.exc_info:
            log_entry["exception"] = {
                "type": record.exc_info[0].__name__ if record.exc_info[0] else None,
                "message": str(record.exc_info[1]) if record.exc_info[1] else None,
                "traceback": self.formatException(record.exc_info)
            }
        
        # Add extra fields from logger calls
        for key, value in record.__dict__.items():
            if key not in ['name', 'msg', 'args', 'levelname', 'levelno', 'pathname', 
                          'filename', 'module', 'lineno', 'funcName', 'created', 'msecs',
                          'relativeCreated', 'thread', 'threadName', 'processName',
                          'process', 'getMessage', 'exc_info', 'exc_text', 'stack_info']:
                log_entry[key] = value
        
        # Add configured extra fields
        log_entry.update(self.extra_fields)
        
        return json.dumps(log_entry, default=str, separators=(',', ':'))
    
    def _get_trace_info(self) -> Optional[Dict[str, str]]:
        """Get current trace and span information."""
        if not OTEL_AVAILABLE:
            return None
        
        try:
            span = get_current_span()
            if span and span.is_recording():
                span_context = span.get_span_context()
                return {
                    "trace_id": format(span_context.trace_id, "032x"),
                    "span_id": format(span_context.span_id, "016x"),
                    "trace_flags": span_context.trace_flags
                }
        except Exception:
            pass
        
        return None


class AtlasLogger:
    """Enhanced logger with ATLAS-specific functionality."""
    
    def __init__(self, name: str, extra_context: Optional[Dict[str, Any]] = None):
        """Initialize ATLAS logger.
        
        Args:
            name: Logger name
            extra_context: Additional context to include in all logs
        """
        self.logger = logging.getLogger(name)
        self.extra_context = extra_context or {}
    
    def _log_with_context(self, level: int, message: str, **kwargs):
        """Log message with additional context."""
        # Extract standard logging parameters
        exc_info = kwargs.pop('exc_info', None)
        stack_info = kwargs.pop('stack_info', None)
        
        # Merge extra context with kwargs for additional fields
        log_kwargs = {**self.extra_context, **kwargs}
        
        # Use extra parameter to pass additional fields
        self.logger.log(level, message, extra=log_kwargs, exc_info=exc_info, stack_info=stack_info)
    
    def debug(self, message: str, **kwargs):
        """Log debug message."""
        self._log_with_context(logging.DEBUG, message, **kwargs)
    
    def info(self, message: str, **kwargs):
        """Log info message."""
        self._log_with_context(logging.INFO, message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """Log warning message."""
        self._log_with_context(logging.WARNING, message, **kwargs)
    
    def error(self, message: str, **kwargs):
        """Log error message."""
        self._log_with_context(logging.ERROR, message, **kwargs)
    
    def critical(self, message: str, **kwargs):
        """Log critical message."""
        self._log_with_context(logging.CRITICAL, message, **kwargs)
    
    def log_tool_call(self, tool_name: str, arguments: Dict[str, Any], duration: Optional[float] = None):
        """Log MCP tool call."""
        self.info(
            f"MCP tool call: {tool_name}",
            tool_name=tool_name,
            argument_count=len(arguments),
            duration_ms=duration * 1000 if duration else None,
            component="mcp_tool"
        )
    
    def log_cache_operation(self, operation: str, namespace: str, key: str, hit: Optional[bool] = None):
        """Log cache operation."""
        self.debug(
            f"Cache {operation}: {namespace}:{key}",
            cache_operation=operation,
            cache_namespace=namespace,
            cache_key=key,
            cache_hit=hit,
            component="cache"
        )
    
    def log_task_operation(self, operation: str, project: str, task_id: str, status: Optional[str] = None):
        """Log task operation."""
        self.info(
            f"Task {operation}: {project}/{task_id}",
            task_operation=operation,
            task_project=project,
            task_id=task_id,
            task_status=status,
            component="task_storage"
        )
    
    def log_error_with_context(self, error: Exception, context: Dict[str, Any]):
        """Log error with additional context."""
        # Avoid overriding reserved logging attributes
        safe_context = {k: v for k, v in context.items() 
                       if k not in ['exc_info', 'exc_text', 'stack_info', 'args', 'msg']}
        
        self.error(
            f"Error: {type(error).__name__}: {str(error)}",
            error_type=type(error).__name__,
            error_message=str(error),
            **safe_context,
            exc_info=True
        )


def setup_structured_logging(
    level: str = "INFO",
    enable_trace_correlation: bool = True,
    enable_console_output: bool = True,
    log_file: Optional[str] = None,
    extra_fields: Optional[Dict[str, Any]] = None
) -> None:
    """Setup structured logging for ATLAS MCP.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        enable_trace_correlation: Whether to include trace/span IDs
        enable_console_output: Whether to log to console
        log_file: Optional log file path
        extra_fields: Additional fields to include in all logs
    """
    # Convert level string to logging constant
    numeric_level = getattr(logging, level.upper(), logging.INFO)
    
    # Create formatter
    formatter = StructuredFormatter(
        include_trace=enable_trace_correlation,
        extra_fields=extra_fields
    )
    
    # Get root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Add console handler (use stderr to avoid interfering with JSON-RPC on stdout)
    if enable_console_output:
        console_handler = logging.StreamHandler(sys.stderr)
        console_handler.setFormatter(formatter)
        console_handler.setLevel(numeric_level)
        root_logger.addHandler(console_handler)
    
    # Add file handler if specified
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        file_handler.setLevel(numeric_level)
        root_logger.addHandler(file_handler)
    
    # Set specific logger levels
    logging.getLogger("atlas_commands").setLevel(numeric_level)
    logging.getLogger("mcp").setLevel(numeric_level)
    
    # Suppress noisy third-party loggers
    logging.getLogger("opentelemetry").setLevel(logging.WARNING)
    logging.getLogger("redis").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)


def get_logger(name: str, extra_context: Optional[Dict[str, Any]] = None) -> AtlasLogger:
    """Get an ATLAS logger instance.
    
    Args:
        name: Logger name
        extra_context: Additional context for all logs from this logger
        
    Returns:
        AtlasLogger instance
    """
    return AtlasLogger(name, extra_context)