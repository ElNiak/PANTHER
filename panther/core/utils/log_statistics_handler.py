"""Log Statistics Handler.

Custom logging handler that intercepts log messages and feeds them to the
statistics collector for real-time analysis and reporting.
"""

import logging
import threading
import time
from typing import Optional

from .feature_registry import feature_registry
from .log_statistics_collector import LogStatisticsCollector


class LogStatisticsHandler(logging.Handler):
    """Custom logging handler for collecting statistics from log messages.

    This handler intercepts all log messages and forwards them to the
    statistics collector while maintaining minimal performance impact.
    """

    def __init__(self, collector: LogStatisticsCollector, level: int = logging.NOTSET):
        """Initialize the statistics handler.

        Args:
            collector: The statistics collector to feed messages to
            level: Minimum logging level to handle
        """
        super().__init__(level)
        self.collector = collector
        self._lock = threading.RLock()
        self._enabled = True
        self._message_count = 0
        self._last_flush = time.time()
        self._flush_interval = 5.0  # Flush every 5 seconds

        # Performance tracking
        self._processing_times = []
        self._max_processing_time = 0.0

    def emit(self, record: logging.LogRecord) -> None:
        """Process a log record and send it to the statistics collector.

        Args:
            record: The log record to process
        """
        if not self._enabled:
            return

        start_time = time.perf_counter()

        try:
            with self._lock:
                # Enhance record with additional information
                self._enhance_record(record)

                # Send to collector
                self.collector.record_log_message(record)

                # Track processing performance
                processing_time = time.perf_counter() - start_time
                self._track_performance(processing_time)

                # Increment message count
                self._message_count += 1

                # Periodic flush
                current_time = time.time()
                if current_time - self._last_flush >= self._flush_interval:
                    self.flush()
                    self._last_flush = current_time

        except Exception as e:
            # Avoid infinite recursion if statistics collection fails
            # Don't use logging here as it could cause recursion
            print(f"Error in LogStatisticsHandler.emit: {e}")

    def _enhance_record(self, record: logging.LogRecord) -> None:
        """Enhance the log record with additional metadata.

        Args:
            record: The log record to enhance
        """
        # Add timestamp if not present
        if not hasattr(record, "created"):
            record.created = time.time()

        # Extract module name from pathname if available
        if hasattr(record, "pathname") and not hasattr(record, "module"):
            try:
                # Extract module name from file path
                pathname = record.pathname
                if "panther" in pathname:
                    # Extract relative path from panther directory
                    parts = pathname.split("panther")[-1].split("/")
                    module_parts = [p for p in parts if p and not p.endswith(".py")]
                    if module_parts:
                        record.module = ".".join(module_parts)
                    else:
                        record.module = record.name
                else:
                    record.module = record.name
            except Exception:
                record.module = record.name
        elif not hasattr(record, "module"):
            record.module = record.name

        # Detect and add feature information
        if not hasattr(record, "feature"):
            feature = self._detect_feature(record)
            if feature:
                record.feature = feature

        # Add message length for analysis
        if not hasattr(record, "message_length"):
            try:
                record.message_length = len(record.getMessage())
            except Exception:
                record.message_length = 0

    def _detect_feature(self, record: logging.LogRecord) -> Optional[str]:
        """Detect the feature associated with a log record.

        Args:
            record: The log record to analyze

        Returns:
            Detected feature name or None
        """
        # Try various sources for feature detection
        sources = [
            getattr(record, "module", ""),
            record.name,
            getattr(record, "pathname", ""),
        ]

        for source in sources:
            if source:
                feature = feature_registry.detect_feature(source)
                if feature:
                    return feature

        return None

    def _track_performance(self, processing_time: float) -> None:
        """Track performance metrics for the handler.

        Args:
            processing_time: Time taken to process the last message
        """
        # Keep track of processing times (last 1000)
        self._processing_times.append(processing_time)
        if len(self._processing_times) > 1000:
            self._processing_times.pop(0)

        # Update max processing time
        if processing_time > self._max_processing_time:
            self._max_processing_time = processing_time

    def flush(self) -> None:
        """Flush any buffered records.

        This method is called periodically to ensure statistics are up-to-date.
        """
        try:
            # Force collector to update any internal buffers or calculations
            if hasattr(self.collector, "flush"):
                self.collector.flush()
        except Exception as e:
            print(f"Error in LogStatisticsHandler.flush: {e}")

    def close(self) -> None:
        """Close the handler and clean up resources."""
        try:
            self._enabled = False
            self.flush()
            super().close()
        except Exception as e:
            print(f"Error in LogStatisticsHandler.close: {e}")

    def enable(self) -> None:
        """Enable statistics collection."""
        with self._lock:
            self._enabled = True

    def disable(self) -> None:
        """Disable statistics collection."""
        with self._lock:
            self._enabled = False

    def is_enabled(self) -> bool:
        """Check if statistics collection is enabled."""
        return self._enabled

    def get_handler_stats(self) -> dict:
        """Get performance statistics for this handler.

        Returns:
            Dictionary containing handler performance metrics
        """
        with self._lock:
            if not self._processing_times:
                return {
                    "messages_processed": self._message_count,
                    "performance_tracking": False,
                }

            avg_time = sum(self._processing_times) / len(self._processing_times)
            total_time = sum(self._processing_times)

            return {
                "messages_processed": self._message_count,
                "average_processing_time_ms": avg_time * 1000,
                "max_processing_time_ms": self._max_processing_time * 1000,
                "total_processing_time_ms": total_time * 1000,
                "performance_samples": len(self._processing_times),
                "enabled": self._enabled,
                "overhead_percentage": (
                    total_time / max(time.time() - self._last_flush, 1)
                )
                * 100,
            }

    def reset_stats(self) -> None:
        """Reset handler performance statistics."""
        with self._lock:
            self._message_count = 0
            self._processing_times.clear()
            self._max_processing_time = 0.0
            self._last_flush = time.time()


class BufferedLogStatisticsHandler(LogStatisticsHandler):
    """Buffered version of LogStatisticsHandler for high-volume logging.

    This handler buffers log records and processes them in batches
    to reduce overhead in high-throughput scenarios.
    """

    def __init__(
        self,
        collector: LogStatisticsCollector,
        buffer_size: int = 100,
        flush_interval: float = 1.0,
        level: int = logging.NOTSET,
    ):
        """Initialize the buffered statistics handler.

        Args:
            collector: The statistics collector to feed messages to
            buffer_size: Number of records to buffer before processing
            flush_interval: Maximum time between flushes (seconds)
            level: Minimum logging level to handle
        """
        super().__init__(collector, level)
        self._buffer = []
        self._buffer_size = buffer_size
        self._flush_interval = flush_interval
        self._last_flush = time.time()
        self._flush_thread = None
        self._stop_flush_thread = threading.Event()

        # Start background flush thread
        self._start_flush_thread()

    def emit(self, record: logging.LogRecord) -> None:
        """Buffer a log record for batch processing.

        Args:
            record: The log record to buffer
        """
        if not self._enabled:
            return

        with self._lock:
            # Enhance record
            self._enhance_record(record)

            # Add to buffer
            self._buffer.append(record)

            # Flush if buffer is full
            if len(self._buffer) >= self._buffer_size:
                self._flush_buffer()

    def _flush_buffer(self) -> None:
        """Process all buffered records."""
        if not self._buffer:
            return

        start_time = time.perf_counter()

        try:
            # Process all buffered records
            for record in self._buffer:
                self.collector.record_log_message(record)
                self._message_count += 1

            # Clear buffer
            self._buffer.clear()
            self._last_flush = time.time()

            # Track performance
            processing_time = time.perf_counter() - start_time
            self._track_performance(processing_time)

        except Exception as e:
            print(f"Error in BufferedLogStatisticsHandler._flush_buffer: {e}")
            self._buffer.clear()  # Clear buffer to prevent memory buildup

    def _start_flush_thread(self) -> None:
        """Start background thread for periodic flushing."""

        def flush_worker():
            while not self._stop_flush_thread.wait(self._flush_interval):
                with self._lock:
                    if self._buffer:
                        self._flush_buffer()

        self._flush_thread = threading.Thread(target=flush_worker, daemon=True)
        self._flush_thread.start()

    def flush(self) -> None:
        """Force flush of buffered records."""
        with self._lock:
            self._flush_buffer()
        super().flush()

    def close(self) -> None:
        """Close the handler and clean up resources."""
        # Stop flush thread
        if self._flush_thread and self._flush_thread.is_alive():
            self._stop_flush_thread.set()
            self._flush_thread.join(timeout=2.0)

        # Flush remaining records
        with self._lock:
            self._flush_buffer()

        super().close()

    def get_buffer_stats(self) -> dict:
        """Get buffer-specific statistics.

        Returns:
            Dictionary containing buffer performance metrics
        """
        with self._lock:
            handler_stats = self.get_handler_stats()
            handler_stats.update(
                {
                    "buffer_size": self._buffer_size,
                    "current_buffer_length": len(self._buffer),
                    "buffer_usage_percent": (len(self._buffer) / self._buffer_size)
                    * 100,
                    "flush_interval_seconds": self._flush_interval,
                    "buffered_handler": True,
                }
            )
            return handler_stats


def create_statistics_handler(
    collector: LogStatisticsCollector, handler_type: str = "standard", **kwargs
) -> LogStatisticsHandler:
    """Factory function to create appropriate statistics handler.

    Args:
        collector: The statistics collector instance
        handler_type: Type of handler ('standard' or 'buffered')
        **kwargs: Additional arguments for handler configuration

    Returns:
        Configured LogStatisticsHandler instance
    """
    if handler_type == "buffered":
        return BufferedLogStatisticsHandler(collector, **kwargs)
    else:
        return LogStatisticsHandler(collector, **kwargs)
