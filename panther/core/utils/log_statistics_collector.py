"""Log Statistics Collector.

This module provides comprehensive collection and analysis of logging statistics
across PANTHER's granular feature logging system.
"""

import logging
import threading
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import psutil

from .feature_registry import feature_registry


class LogStatisticsCollector:
    """Collects and analyzes logging statistics in real-time.

    Tracks message counts, feature activity, performance metrics,
    and provides comprehensive reporting capabilities.
    """

    def __init__(self, buffer_size: int = 1000, track_performance: bool = True):
        """Initialize the statistics collector.

        Args:
            buffer_size: Maximum number of recent messages to keep in memory
            track_performance: Whether to track performance metrics
        """
        self._lock = threading.RLock()
        self.buffer_size = buffer_size
        self.track_performance = track_performance

        # Core statistics
        self.stats = {
            "total_messages": 0,
            "by_level": defaultdict(int),
            "by_feature": defaultdict(int),
            "by_module": defaultdict(int),
            "by_time_interval": defaultdict(int),
            "error_patterns": defaultdict(int),
            "start_time": datetime.now(),
            "last_update": datetime.now(),
            "session_duration": 0.0,
        }

        # Performance metrics
        self.performance_metrics = {
            "collection_overhead_ms": deque(maxlen=1000),
            "buffer_usage": 0,
            "memory_usage_mb": 0.0,
            "messages_per_second": 0.0,
            "peak_message_rate": 0.0,
            "total_collection_time_ms": 0.0,
        }

        # Message buffer for detailed analysis
        self.message_buffer = deque(maxlen=buffer_size)

        # Time-based statistics (last 60 seconds)
        self.time_windows = {
            "1min": deque(maxlen=60),
            "5min": deque(maxlen=300),
            "15min": deque(maxlen=900),
        }

        # Feature patterns and error tracking
        self.feature_patterns = {}
        self.error_tracking = {
            "by_feature": defaultdict(int),
            "by_module": defaultdict(int),
            "recent_errors": deque(maxlen=100),
            "error_rate_per_minute": deque(maxlen=60),
        }

        # Performance monitoring
        if self.track_performance:
            self._start_performance_monitoring()

    def record_log_message(self, record: logging.LogRecord) -> None:
        """Record a log message and update statistics.

        Args:
            record: The logging record to process
        """
        start_time = time.perf_counter()

        with self._lock:
            try:
                # Basic message counting
                self.stats["total_messages"] += 1
                self.stats["by_level"][record.levelname] += 1
                self.stats["last_update"] = datetime.now()

                # Session duration
                self.stats["session_duration"] = (
                    self.stats["last_update"] - self.stats["start_time"]
                ).total_seconds()

                # Module tracking
                module_name = getattr(record, "module", record.name)
                self.stats["by_module"][module_name] += 1

                # Feature detection and tracking
                feature = self._detect_feature_from_record(record)
                if feature:
                    self.stats["by_feature"][feature] += 1

                    # Track feature patterns
                    if feature not in self.feature_patterns:
                        self.feature_patterns[feature] = {
                            "total_messages": 0,
                            "by_level": defaultdict(int),
                            "modules": set(),
                            "first_seen": datetime.now(),
                            "last_seen": datetime.now(),
                        }

                    pattern = self.feature_patterns[feature]
                    pattern["total_messages"] += 1
                    pattern["by_level"][record.levelname] += 1
                    pattern["modules"].add(module_name)
                    pattern["last_seen"] = datetime.now()

                # Error tracking
                if record.levelno >= logging.ERROR:
                    self.error_tracking["by_feature"][feature or "unknown"] += 1
                    self.error_tracking["by_module"][module_name] += 1
                    self.error_tracking["recent_errors"].append(
                        {
                            "timestamp": datetime.now(),
                            "level": record.levelname,
                            "module": module_name,
                            "feature": feature,
                            "message": record.getMessage()[
                                :200
                            ],  # Truncate long messages
                        }
                    )

                # Time interval tracking
                current_minute = datetime.now().replace(second=0, microsecond=0)
                self.stats["by_time_interval"][current_minute] += 1

                # Message buffer
                self.message_buffer.append(
                    {
                        "timestamp": datetime.now(),
                        "level": record.levelname,
                        "module": module_name,
                        "feature": feature,
                        "message_length": len(record.getMessage()),
                    }
                )

                # Time window tracking
                current_time = time.time()
                for window in self.time_windows.values():
                    window.append(current_time)

                # Performance metrics
                if self.track_performance:
                    collection_time = (time.perf_counter() - start_time) * 1000
                    self.performance_metrics["collection_overhead_ms"].append(
                        collection_time
                    )
                    self.performance_metrics[
                        "total_collection_time_ms"
                    ] += collection_time
                    self.performance_metrics["buffer_usage"] = len(self.message_buffer)

                    # Update message rate
                    self._update_message_rate()

            except Exception as e:
                # Avoid infinite recursion if logging statistics collection fails
                print(f"Error in log statistics collection: {e}")

    def _detect_feature_from_record(self, record: logging.LogRecord) -> Optional[str]:
        """Detect feature from logging record.

        Args:
            record: The logging record

        Returns:
            Detected feature name or None
        """
        # Try module name first
        module_name = getattr(record, "module", record.name)
        feature = feature_registry.detect_feature(module_name)
        if feature:
            return feature

        # Try full logger name
        feature = feature_registry.detect_feature(record.name)
        if feature:
            return feature

        # Try pathname if available
        if hasattr(record, "pathname"):
            feature = feature_registry.detect_feature(record.pathname)
            if feature:
                return feature

        return None

    def _update_message_rate(self) -> None:
        """Update messages per second calculation."""
        if len(self.time_windows["1min"]) < 2:
            return

        current_time = time.time()
        one_min_ago = current_time - 60

        # Count messages in last minute
        recent_messages = sum(1 for t in self.time_windows["1min"] if t >= one_min_ago)
        self.performance_metrics["messages_per_second"] = recent_messages / 60.0

        # Update peak rate
        if (
            self.performance_metrics["messages_per_second"]
            > self.performance_metrics["peak_message_rate"]
        ):
            self.performance_metrics["peak_message_rate"] = self.performance_metrics[
                "messages_per_second"
            ]

    def _start_performance_monitoring(self) -> None:
        """Start background performance monitoring."""

        def monitor():
            while True:
                try:
                    # Memory usage
                    process = psutil.Process()
                    self.performance_metrics["memory_usage_mb"] = (
                        process.memory_info().rss / 1024 / 1024
                    )
                    time.sleep(5)  # Update every 5 seconds
                except Exception:
                    time.sleep(10)  # Retry in 10 seconds if psutil fails

        monitor_thread = threading.Thread(target=monitor, daemon=True)
        monitor_thread.start()

    def get_real_time_stats(self) -> Dict[str, Any]:
        """Get current statistics snapshot.

        Returns:
            Dictionary containing current statistics
        """
        with self._lock:
            # Calculate rates
            current_time = datetime.now()
            duration = (current_time - self.stats["start_time"]).total_seconds()
            message_rate = self.stats["total_messages"] / max(duration, 1)

            # Top features by activity
            top_features = dict(
                sorted(
                    self.stats["by_feature"].items(), key=lambda x: x[1], reverse=True
                )[:10]
            )

            # Top modules by activity
            top_modules = dict(
                sorted(
                    self.stats["by_module"].items(), key=lambda x: x[1], reverse=True
                )[:10]
            )

            # Error rate
            error_count = self.stats["by_level"].get("ERROR", 0) + self.stats[
                "by_level"
            ].get("CRITICAL", 0)
            error_rate = (error_count / max(self.stats["total_messages"], 1)) * 100

            return {
                "timestamp": current_time,
                "session_info": {
                    "start_time": self.stats["start_time"],
                    "duration_seconds": duration,
                    "total_messages": self.stats["total_messages"],
                    "messages_per_second": message_rate,
                },
                "message_distribution": {
                    "by_level": dict(self.stats["by_level"]),
                    "by_feature": top_features,
                    "by_module": top_modules,
                },
                "error_statistics": {
                    "total_errors": error_count,
                    "error_rate_percent": error_rate,
                    "errors_by_feature": dict(self.error_tracking["by_feature"]),
                    "recent_error_count": len(self.error_tracking["recent_errors"]),
                },
                "performance_metrics": dict(self.performance_metrics),
                "buffer_info": {
                    "current_size": len(self.message_buffer),
                    "max_size": self.buffer_size,
                    "usage_percent": (len(self.message_buffer) / self.buffer_size)
                    * 100,
                },
            }

    def generate_summary_report(self) -> Dict[str, Any]:
        """Generate comprehensive statistics report.

        Returns:
            Detailed statistics report
        """
        with self._lock:
            real_time_stats = self.get_real_time_stats()

            # Feature analysis
            feature_analysis = self._analyze_features()

            # Time distribution analysis
            time_analysis = self._analyze_time_distribution()

            # Performance analysis
            performance_analysis = self._analyze_performance()

            # Error pattern analysis
            error_analysis = self._analyze_error_patterns()

            return {
                "report_metadata": {
                    "generated_at": datetime.now(),
                    "collection_period": real_time_stats["session_info"][
                        "duration_seconds"
                    ],
                    "total_messages_analyzed": self.stats["total_messages"],
                },
                "summary": real_time_stats,
                "feature_analysis": feature_analysis,
                "time_analysis": time_analysis,
                "performance_analysis": performance_analysis,
                "error_analysis": error_analysis,
                "recommendations": self._generate_recommendations(),
            }

    def _analyze_features(self) -> Dict[str, Any]:
        """Analyze feature-specific statistics."""
        feature_stats = {}

        for feature, pattern in self.feature_patterns.items():
            total_msgs = pattern["total_messages"]
            duration = (pattern["last_seen"] - pattern["first_seen"]).total_seconds()

            feature_stats[feature] = {
                "total_messages": total_msgs,
                "message_rate": total_msgs / max(duration, 1),
                "level_distribution": dict(pattern["by_level"]),
                "unique_modules": len(pattern["modules"]),
                "active_duration": duration,
                "first_seen": pattern["first_seen"],
                "last_seen": pattern["last_seen"],
            }

        return feature_stats

    def _analyze_time_distribution(self) -> Dict[str, Any]:
        """Analyze message distribution over time."""
        # Group by hour for time analysis
        hourly_distribution = defaultdict(int)
        for timestamp, count in self.stats["by_time_interval"].items():
            hour = timestamp.replace(minute=0, second=0, microsecond=0)
            hourly_distribution[hour] += count

        return {
            "hourly_distribution": dict(hourly_distribution),
            "peak_hour": (
                max(hourly_distribution.items(), key=lambda x: x[1])
                if hourly_distribution
                else None
            ),
            "message_intervals": dict(self.stats["by_time_interval"]),
        }

    def _analyze_performance(self) -> Dict[str, Any]:
        """Analyze performance impact of logging."""
        if not self.performance_metrics["collection_overhead_ms"]:
            return {"performance_tracking_disabled": True}

        overhead_times = list(self.performance_metrics["collection_overhead_ms"])

        return {
            "collection_overhead": {
                "average_ms": sum(overhead_times) / len(overhead_times),
                "total_ms": self.performance_metrics["total_collection_time_ms"],
                "max_ms": max(overhead_times),
                "min_ms": min(overhead_times),
                "samples": len(overhead_times),
            },
            "message_rates": {
                "current_per_second": self.performance_metrics["messages_per_second"],
                "peak_per_second": self.performance_metrics["peak_message_rate"],
            },
            "memory_usage": {
                "current_mb": self.performance_metrics["memory_usage_mb"],
                "buffer_usage_percent": (len(self.message_buffer) / self.buffer_size)
                * 100,
            },
        }

    def _analyze_error_patterns(self) -> Dict[str, Any]:
        """Analyze error patterns and frequencies."""
        recent_errors = list(self.error_tracking["recent_errors"])

        # Error frequency by feature
        error_by_feature = dict(self.error_tracking["by_feature"])

        # Error patterns
        error_patterns = defaultdict(int)
        for error in recent_errors:
            # Simple pattern detection based on first few words
            words = error["message"].split()[:3]
            pattern = " ".join(words) if words else "unknown"
            error_patterns[pattern] += 1

        return {
            "total_errors": len(recent_errors),
            "errors_by_feature": error_by_feature,
            "errors_by_module": dict(self.error_tracking["by_module"]),
            "common_error_patterns": dict(
                sorted(error_patterns.items(), key=lambda x: x[1], reverse=True)[:10]
            ),
            "recent_errors": recent_errors[-10:],  # Last 10 errors
        }

    def _generate_recommendations(self) -> List[str]:
        """Generate optimization recommendations based on statistics."""
        recommendations = []

        # Check for high-volume features
        total_messages = self.stats["total_messages"]
        for feature, count in self.stats["by_feature"].items():
            if count > total_messages * 0.3:  # More than 30% of messages
                recommendations.append(
                    f"Consider reducing log level for '{feature}' feature (generating {count}/{total_messages} messages)"
                )

        # Check for error rates
        error_count = self.stats["by_level"].get("ERROR", 0) + self.stats[
            "by_level"
        ].get("CRITICAL", 0)
        if error_count > total_messages * 0.1:  # More than 10% errors
            recommendations.append(
                f"High error rate detected: {error_count}/{total_messages} messages are errors"
            )

        # Check performance impact
        if (
            self.track_performance
            and self.performance_metrics["collection_overhead_ms"]
        ):
            avg_overhead = sum(
                self.performance_metrics["collection_overhead_ms"]
            ) / len(self.performance_metrics["collection_overhead_ms"])
            if avg_overhead > 5.0:  # More than 5ms average
                recommendations.append(
                    f"Logging collection overhead is high ({avg_overhead:.2f}ms average per message)"
                )

        # Check buffer usage
        if len(self.message_buffer) > self.buffer_size * 0.9:
            recommendations.append(
                "Message buffer is near capacity - consider increasing buffer size or reducing log verbosity"
            )

        return recommendations

    def reset_statistics(self) -> None:
        """Reset all collected statistics."""
        with self._lock:
            self.stats = {
                "total_messages": 0,
                "by_level": defaultdict(int),
                "by_feature": defaultdict(int),
                "by_module": defaultdict(int),
                "by_time_interval": defaultdict(int),
                "error_patterns": defaultdict(int),
                "start_time": datetime.now(),
                "last_update": datetime.now(),
                "session_duration": 0.0,
            }

            self.performance_metrics = {
                "collection_overhead_ms": deque(maxlen=1000),
                "buffer_usage": 0,
                "memory_usage_mb": 0.0,
                "messages_per_second": 0.0,
                "peak_message_rate": 0.0,
                "total_collection_time_ms": 0.0,
            }

            self.message_buffer.clear()
            self.feature_patterns.clear()

            for window in self.time_windows.values():
                window.clear()

            self.error_tracking = {
                "by_feature": defaultdict(int),
                "by_module": defaultdict(int),
                "recent_errors": deque(maxlen=100),
                "error_rate_per_minute": deque(maxlen=60),
            }

    def export_statistics(self, format: str = "json") -> str:
        """Export statistics in specified format.

        Args:
            format: Export format ('json', 'csv', 'text')

        Returns:
            Formatted statistics string
        """
        report = self.generate_summary_report()

        if format == "json":
            import json

            return json.dumps(report, indent=2, default=str)
        elif format == "csv":
            return self._export_csv(report)
        elif format == "text":
            return self._export_text(report)
        else:
            raise ValueError(f"Unsupported export format: {format}")

    def _export_csv(self, report: Dict) -> str:
        """Export statistics as CSV format."""
        lines = ["metric,value"]

        # Basic statistics
        session = report["summary"]["session_info"]
        lines.append(f"total_messages,{session['total_messages']}")
        lines.append(f"duration_seconds,{session['duration_seconds']}")
        lines.append(f"messages_per_second,{session['messages_per_second']}")

        # Level distribution
        for level, count in report["summary"]["message_distribution"][
            "by_level"
        ].items():
            lines.append(f"level_{level.lower()},{count}")

        # Feature distribution
        for feature, count in report["summary"]["message_distribution"][
            "by_feature"
        ].items():
            lines.append(f"feature_{feature},{count}")

        return "\n".join(lines)

    def _export_text(self, report: Dict) -> str:
        """Export statistics as human-readable text."""
        lines = ["PANTHER Logging Statistics Report"]
        lines.append("=" * 40)
        lines.append("")

        # Session info
        session = report["summary"]["session_info"]
        lines.append(f"Session Duration: {session['duration_seconds']:.1f} seconds")
        lines.append(f"Total Messages: {session['total_messages']}")
        lines.append(f"Messages/Second: {session['messages_per_second']:.2f}")
        lines.append("")

        # Level distribution
        lines.append("Message Distribution by Level:")
        for level, count in report["summary"]["message_distribution"][
            "by_level"
        ].items():
            percentage = (count / session["total_messages"]) * 100
            lines.append(f"  {level}: {count} ({percentage:.1f}%)")
        lines.append("")

        # Top features
        lines.append("Top Active Features:")
        for feature, count in list(
            report["summary"]["message_distribution"]["by_feature"].items()
        )[:5]:
            percentage = (count / session["total_messages"]) * 100
            lines.append(f"  {feature}: {count} ({percentage:.1f}%)")
        lines.append("")

        # Recommendations
        if report.get("recommendations"):
            lines.append("Recommendations:")
            for rec in report["recommendations"]:
                lines.append(f"  • {rec}")

        return "\n".join(lines)
