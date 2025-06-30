"""Metrics collection functionality for test cases."""

import time
from functools import wraps
from typing import Any, Callable, Dict, Optional


class MetricsMixin:
    """Mixin providing metrics collection capabilities for test cases."""
    
    def __init__(self, *args, **kwargs):
        """Initialize the mixin."""
        super().__init__(*args, **kwargs)
        # Initialize _operation_timers if not already set
        if not hasattr(self, '_operation_timers'):
            self._operation_timers = {}
    
    def timed_operation(self, operation_name: str, phase: str = "TEST_EXECUTION") -> Callable:
        """
        Decorator for timing operations and emitting metrics.
        
        Args:
            operation_name: Name of the operation being timed
            phase: Phase of the test execution
            
        Returns:
            Decorator function
        """
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs) -> Any:
                start_time = time.time()
                try:
                    result = func(*args, **kwargs)
                    duration = time.time() - start_time
                    self._emit_timing_metric(operation_name, duration, phase)
                    return result
                except Exception as e:
                    duration = time.time() - start_time
                    self._emit_timing_metric(operation_name, duration, phase, error=True)
                    raise
            return wrapper
        return decorator
    
    def start_timer(self, operation_name: str) -> None:
        """Start timing an operation."""
        self._operation_timers[operation_name] = time.time()
        self.logger.debug(f"Started timer for operation: {operation_name}")
    
    def stop_timer(self, operation_name: str, phase: str = "TEST_EXECUTION") -> float:
        """
        Stop timing an operation and emit metric.
        
        Args:
            operation_name: Name of the operation
            phase: Phase of the test execution
            
        Returns:
            Duration in seconds
        """
        if operation_name not in self._operation_timers:
            self.logger.warning(f"No timer found for operation: {operation_name}")
            return 0.0
        
        start_time = self._operation_timers.pop(operation_name)
        duration = time.time() - start_time
        self._emit_timing_metric(operation_name, duration, phase)
        return duration
    
    def _emit_timing_metric(
        self, 
        operation_name: str, 
        duration: float, 
        phase: str = "TEST_EXECUTION",
        error: bool = False
    ) -> None:
        """
        Emit a timing metric event.
        
        Args:
            operation_name: Name of the operation
            duration: Duration in seconds
            phase: Phase of the test execution
            error: Whether an error occurred
        """
        if not self.metrics_collector:
            return
            
        # Use full operation name including test name
        full_operation_name = f"{operation_name}_{self.test_name}"
        
        self.logger.debug(
            f"Emitting timing metric: {full_operation_name} - {duration:.2f}s"
        )
        
        try:
            self.metrics_emitter.emit_timing_metric(
                operation_name=full_operation_name,
                duration=duration,
                phase=phase,
                test_case=self.test_config.name,
                component="test_case",
                metadata={
                    "error": error,
                    "test_name": self.test_name,
                    "operation": operation_name
                }
            )
        except Exception as e:
            self.logger.error(f"Failed to emit timing metric: {e}")
    
    def emit_counter_metric(
        self, 
        counter_name: str, 
        value: int = 1,
        increment: bool = True,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Emit a counter metric event.
        
        Args:
            counter_name: Name of the counter
            value: Counter value
            increment: Whether to increment the counter
            metadata: Additional metadata
        """
        if not self.metrics_collector:
            return
            
        self.logger.debug(f"Emitting counter metric: {counter_name} - {value}")
        
        try:
            self.metrics_emitter.emit_counter_metric(
                counter_name=counter_name,
                value=value,
                increment=increment,
                test_case=self.test_config.name,
                metadata=metadata or {}
            )
        except Exception as e:
            self.logger.error(f"Failed to emit counter metric: {e}")
    
    def emit_gauge_metric(
        self,
        gauge_name: str,
        value: float,
        unit: str = "count",
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Emit a gauge metric event.
        
        Args:
            gauge_name: Name of the gauge
            value: Gauge value
            unit: Unit of measurement
            metadata: Additional metadata
        """
        if not self.metrics_collector:
            return
            
        self.logger.debug(f"Emitting gauge metric: {gauge_name} - {value} {unit}")
        
        try:
            self.metrics_emitter.emit_gauge_metric(
                gauge_name=gauge_name,
                value=value,
                unit=unit,
                test_case=self.test_config.name,
                metadata=metadata or {}
            )
        except Exception as e:
            self.logger.error(f"Failed to emit gauge metric: {e}")
    
    def with_metrics(self, phase: str = "TEST_EXECUTION") -> Callable:
        """
        Context manager for timing code blocks.
        
        Usage:
            with self.with_metrics("setup_services"):
                self.setup_services()
        """
        class MetricsContext:
            def __init__(self, mixin, operation_name, phase):
                self.mixin = mixin
                self.operation_name = operation_name
                self.phase = phase
                
            def __enter__(self):
                self.mixin.start_timer(self.operation_name)
                return self
                
            def __exit__(self, exc_type, exc_val, exc_tb):
                self.mixin.stop_timer(self.operation_name, self.phase)
                return False
        
        return lambda operation_name: MetricsContext(self, operation_name, phase)