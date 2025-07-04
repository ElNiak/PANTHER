"""Metrics collection and management for ATLAS MCP."""

import time
import logging
from typing import Dict, Any, Optional, Union
from datetime import datetime
from collections import defaultdict, Counter

try:
    from opentelemetry import metrics
    from opentelemetry.metrics import Counter, Histogram, Gauge, UpDownCounter
    OTEL_AVAILABLE = True
except ImportError:
    OTEL_AVAILABLE = False
    metrics = None

logger = logging.getLogger(__name__)


class Metrics:
    """Centralized metrics collection for ATLAS MCP."""
    
    def __init__(self, meter_name: str = "atlas-mcp"):
        """Initialize metrics collector.
        
        Args:
            meter_name: Name for the OpenTelemetry meter
        """
        self.meter_name = meter_name
        self.enabled = OTEL_AVAILABLE
        
        # Get meter
        self.meter = metrics.get_meter(meter_name) if self.enabled else None
        
        # Initialize metrics
        self._create_metrics()
        
        # Fallback metrics (when OTel unavailable)
        self.fallback_metrics = defaultdict(int)
        self.fallback_timings = defaultdict(list)
        
    def _create_metrics(self) -> None:
        """Create OpenTelemetry metrics instruments."""
        if not self.enabled or not self.meter:
            return
        
        try:
            # Counters - monotonically increasing values
            self.tool_calls_total = self.meter.create_counter(
                name="mcp_tool_calls_total",
                description="Total number of MCP tool calls",
                unit="1"
            )
            
            self.cache_operations_total = self.meter.create_counter(
                name="mcp_cache_operations_total", 
                description="Total number of cache operations",
                unit="1"
            )
            
            self.task_operations_total = self.meter.create_counter(
                name="mcp_task_operations_total",
                description="Total number of task operations", 
                unit="1"
            )
            
            self.errors_total = self.meter.create_counter(
                name="mcp_errors_total",
                description="Total number of errors",
                unit="1"
            )
            
            # Histograms - distribution of values
            self.tool_call_duration = self.meter.create_histogram(
                name="mcp_tool_call_duration_seconds",
                description="Duration of MCP tool calls",
                unit="s"
            )
            
            self.cache_operation_duration = self.meter.create_histogram(
                name="mcp_cache_operation_duration_seconds",
                description="Duration of cache operations",
                unit="s"
            )
            
            self.task_operation_duration = self.meter.create_histogram(
                name="mcp_task_operation_duration_seconds", 
                description="Duration of task operations",
                unit="s"
            )
            
            # Gauges - current values
            self.active_tasks = self.meter.create_up_down_counter(
                name="mcp_active_tasks",
                description="Number of currently active tasks",
                unit="1"
            )
            
            self.cache_size = self.meter.create_up_down_counter(
                name="mcp_cache_size_entries",
                description="Number of entries in cache",
                unit="1"
            )
            
            logger.info("OpenTelemetry metrics initialized")
            
        except Exception as e:
            logger.error(f"Failed to create metrics: {e}")
            self.enabled = False
    
    def record_tool_call(self, tool_name: str, duration: float, success: bool = True,
                        attributes: Optional[Dict[str, Any]] = None) -> None:
        """Record MCP tool call metrics.
        
        Args:
            tool_name: Name of the tool called
            duration: Duration in seconds
            success: Whether the call was successful
            attributes: Additional attributes for the metric
        """
        attrs = {"tool": tool_name, "success": success}
        if attributes:
            attrs.update(attributes)
        
        if self.enabled:
            try:
                self.tool_calls_total.add(1, attrs)
                self.tool_call_duration.record(duration, attrs)
                
                if not success:
                    error_attrs = {"tool": tool_name, "type": "tool_error"}
                    self.errors_total.add(1, error_attrs)
                    
            except Exception as e:
                logger.warning(f"Failed to record tool call metrics: {e}")
        
        # Fallback metrics
        self.fallback_metrics[f"tool_calls_{tool_name}_{success}"] += 1
        self.fallback_timings[f"tool_duration_{tool_name}"].append(duration)
    
    def record_cache_operation(self, operation: str, namespace: str, duration: float,
                              hit: Optional[bool] = None, size: Optional[int] = None) -> None:
        """Record cache operation metrics.
        
        Args:
            operation: Cache operation (get, set, invalidate, etc.)
            namespace: Cache namespace
            duration: Duration in seconds
            hit: Cache hit (for get operations)
            size: Size of cached data
        """
        attrs = {"operation": operation, "namespace": namespace}
        if hit is not None:
            attrs["hit"] = hit
        
        if self.enabled:
            try:
                self.cache_operations_total.add(1, attrs)
                self.cache_operation_duration.record(duration, attrs)
                
            except Exception as e:
                logger.warning(f"Failed to record cache metrics: {e}")
        
        # Fallback metrics
        self.fallback_metrics[f"cache_{operation}_{namespace}"] += 1
        self.fallback_timings[f"cache_duration_{operation}"].append(duration)
        
        if hit is not None:
            self.fallback_metrics[f"cache_hit_{namespace}"] += 1 if hit else 0
            self.fallback_metrics[f"cache_miss_{namespace}"] += 0 if hit else 1
    
    def record_task_operation(self, operation: str, project: str, duration: float,
                             task_id: Optional[str] = None, status: Optional[str] = None) -> None:
        """Record task operation metrics.
        
        Args:
            operation: Task operation (create, update, get, list, etc.)
            project: Project name
            duration: Duration in seconds
            task_id: Task ID (optional)
            status: Task status (optional)
        """
        attrs = {"operation": operation, "project": project}
        if status:
            attrs["status"] = status
        
        if self.enabled:
            try:
                self.task_operations_total.add(1, attrs)
                self.task_operation_duration.record(duration, attrs)
                
            except Exception as e:
                logger.warning(f"Failed to record task metrics: {e}")
        
        # Fallback metrics
        self.fallback_metrics[f"task_{operation}_{project}"] += 1
        self.fallback_timings[f"task_duration_{operation}"].append(duration)
    
    def update_active_tasks(self, project: str, delta: int) -> None:
        """Update active tasks gauge.
        
        Args:
            project: Project name
            delta: Change in active tasks (+1 for new, -1 for completed)
        """
        attrs = {"project": project}
        
        if self.enabled:
            try:
                self.active_tasks.add(delta, attrs)
            except Exception as e:
                logger.warning(f"Failed to update active tasks: {e}")
        
        # Fallback metrics
        self.fallback_metrics[f"active_tasks_{project}"] += delta
    
    def update_cache_size(self, namespace: str, size: int) -> None:
        """Update cache size gauge.
        
        Args:
            namespace: Cache namespace
            size: Current cache size
        """
        attrs = {"namespace": namespace}
        
        if self.enabled:
            try:
                # This is a gauge, so we set the absolute value
                current_size = self.fallback_metrics.get(f"cache_size_{namespace}", 0)
                delta = size - current_size
                self.cache_size.add(delta, attrs)
                
            except Exception as e:
                logger.warning(f"Failed to update cache size: {e}")
        
        # Fallback metrics
        self.fallback_metrics[f"cache_size_{namespace}"] = size
    
    def record_error(self, error_type: str, component: str, message: str = "",
                    attributes: Optional[Dict[str, Any]] = None) -> None:
        """Record error metrics.
        
        Args:
            error_type: Type of error
            component: Component where error occurred
            message: Error message
            attributes: Additional attributes
        """
        attrs = {"type": error_type, "component": component}
        if attributes:
            attrs.update(attributes)
        
        if self.enabled:
            try:
                self.errors_total.add(1, attrs)
            except Exception as e:
                logger.warning(f"Failed to record error metrics: {e}")
        
        # Fallback metrics
        self.fallback_metrics[f"errors_{error_type}_{component}"] += 1
    
    def get_fallback_metrics(self) -> Dict[str, Any]:
        """Get fallback metrics when OpenTelemetry is not available."""
        metrics_summary = {}
        
        # Convert counters to dict
        for metric_name, count in self.fallback_metrics.items():
            metrics_summary[metric_name] = count
        
        # Calculate timing statistics
        for timing_name, durations in self.fallback_timings.items():
            if durations:
                metrics_summary[f"{timing_name}_avg"] = sum(durations) / len(durations)
                metrics_summary[f"{timing_name}_min"] = min(durations)
                metrics_summary[f"{timing_name}_max"] = max(durations)
                metrics_summary[f"{timing_name}_count"] = len(durations)
        
        return metrics_summary
    
    def get_health_metrics(self) -> Dict[str, Any]:
        """Get health and status metrics."""
        health = {
            "metrics_enabled": self.enabled,
            "otel_available": OTEL_AVAILABLE,
            "meter_name": self.meter_name,
            "timestamp": datetime.utcnow().isoformat()
        }
        
        if not self.enabled:
            # Include fallback metrics
            health["fallback_metrics"] = self.get_fallback_metrics()
        
        return health


class MetricsCollector:
    """Context manager for collecting metrics during operations."""
    
    def __init__(self, metrics: Metrics, operation_type: str, **attributes):
        """Initialize metrics collector.
        
        Args:
            metrics: Metrics instance
            operation_type: Type of operation being measured
            **attributes: Additional attributes for metrics
        """
        self.metrics = metrics
        self.operation_type = operation_type
        self.attributes = attributes
        self.start_time = None
        self.success = True
        self.error = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.start_time is None:
            return
        
        duration = time.time() - self.start_time
        
        if exc_type is not None:
            self.success = False
            self.error = exc_val
        
        # Record metrics based on operation type
        if self.operation_type == "tool_call":
            tool_name = self.attributes.get("tool", "unknown")
            self.metrics.record_tool_call(tool_name, duration, self.success, self.attributes)
        
        elif self.operation_type == "cache":
            operation = self.attributes.get("operation", "unknown")
            namespace = self.attributes.get("namespace", "unknown")
            hit = self.attributes.get("hit")
            self.metrics.record_cache_operation(operation, namespace, duration, hit)
        
        elif self.operation_type == "task":
            operation = self.attributes.get("operation", "unknown")
            project = self.attributes.get("project", "unknown")
            status = self.attributes.get("status")
            task_id = self.attributes.get("task_id")
            self.metrics.record_task_operation(operation, project, duration, task_id, status)
        
        # Record error if operation failed
        if not self.success and self.error:
            error_type = type(self.error).__name__
            component = self.attributes.get("component", self.operation_type)
            self.metrics.record_error(error_type, component, str(self.error), self.attributes)
    
    def set_success(self, success: bool):
        """Manually set operation success status."""
        self.success = success
    
    def add_attributes(self, **attributes):
        """Add additional attributes to the metrics."""
        self.attributes.update(attributes)