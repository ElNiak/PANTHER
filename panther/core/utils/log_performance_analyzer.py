"""
Log Performance Analyzer

Performance analysis module for logging system overhead, bottlenecks,
and optimization recommendations based on resource usage and timing metrics.
"""

import logging
import math
import time
from collections import defaultdict, deque
from datetime import datetime, timedelta
from statistics import mean, median, stdev
from typing import Any, Dict, List, Optional, Tuple

try:
    import psutil

    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

from .log_statistics_collector import LogStatisticsCollector


class LogPerformanceAnalyzer:
    """
    Advanced analyzer for logging system performance and resource usage.

    Provides detailed analysis of logging overhead, memory usage patterns,
    processing bottlenecks, and performance optimization recommendations.
    """

    def __init__(self, collector: LogStatisticsCollector):
        """
        Initialize the performance analyzer.

        Args:
            collector: The statistics collector to analyze
        """
        self.collector = collector

        # Performance monitoring
        self.baseline_metrics = None
        self.performance_samples = deque(maxlen=1000)
        self.resource_snapshots = deque(maxlen=100)

        # Analysis configuration
        self.config = {
            "overhead_concern_threshold": 10.0,  # ms per message
            "memory_concern_threshold": 100.0,  # MB
            "cpu_concern_threshold": 5.0,  # % CPU usage
            "throughput_concern_threshold": 100,  # messages/second
            "latency_percentiles": [50, 95, 99],  # Percentiles to analyze
            "sample_window_minutes": 5,  # Window for rate calculations
        }

        # Cache for expensive calculations
        self._analysis_cache = {}
        self._cache_timestamps = {}
        self._cache_ttl = 15  # Cache TTL in seconds

    def analyze_logging_overhead(self, detailed: bool = True) -> Dict[str, Any]:
        """
        Analyze performance impact of logging system.

        Args:
            detailed: Whether to include detailed breakdown analysis

        Returns:
            Comprehensive performance analysis
        """
        cache_key = f"overhead_{detailed}"
        if self._is_cache_valid(cache_key):
            return self._analysis_cache[cache_key]

        try:
            perf_metrics = self.collector.performance_metrics

            if not perf_metrics.get("collection_overhead_ms"):
                return {
                    "status": "no_performance_data",
                    "message": "Performance tracking is disabled or no data available",
                }

            overhead_times = list(perf_metrics["collection_overhead_ms"])

            analysis = {
                "timestamp": datetime.now(),
                "summary": self._analyze_overhead_summary(overhead_times),
                "distribution": self._analyze_overhead_distribution(overhead_times),
                "trends": self._analyze_overhead_trends(overhead_times),
                "bottlenecks": self._identify_bottlenecks(),
                "resource_impact": self._analyze_resource_impact(),
                "recommendations": [],
            }

            if detailed:
                analysis["detailed_breakdown"] = self._detailed_overhead_breakdown()
                analysis[
                    "comparative_analysis"
                ] = self._comparative_performance_analysis()

            # Generate recommendations
            analysis["recommendations"] = self._generate_performance_recommendations(
                analysis
            )

            # Cache result
            self._analysis_cache[cache_key] = analysis
            self._cache_timestamps[cache_key] = datetime.now()

            return analysis

        except Exception as e:
            logging.getLogger(__name__).error("Error analyzing logging overhead: %s", e)
            return {"error": f"Failed to analyze logging overhead: {e}"}

    def _analyze_overhead_summary(self, overhead_times: List[float]) -> Dict[str, Any]:
        """Analyze basic overhead statistics."""
        if not overhead_times:
            return {"no_data": True}

        # Convert to milliseconds for readability
        times_ms = [t for t in overhead_times]

        total_time = sum(times_ms)
        avg_time = mean(times_ms)

        return {
            "total_samples": len(times_ms),
            "total_overhead_ms": total_time,
            "average_overhead_ms": avg_time,
            "median_overhead_ms": median(times_ms),
            "min_overhead_ms": min(times_ms),
            "max_overhead_ms": max(times_ms),
            "std_deviation_ms": stdev(times_ms) if len(times_ms) > 1 else 0.0,
            "overhead_per_message_ms": avg_time,
            "is_concerning": avg_time > self.config["overhead_concern_threshold"],
        }

    def _analyze_overhead_distribution(
        self, overhead_times: List[float]
    ) -> Dict[str, Any]:
        """Analyze distribution of overhead times."""
        if not overhead_times:
            return {"no_data": True}

        times_ms = [t for t in overhead_times]

        # Calculate percentiles
        sorted_times = sorted(times_ms)
        n = len(sorted_times)

        percentiles = {}
        for p in self.config["latency_percentiles"]:
            idx = int((p / 100.0) * (n - 1))
            percentiles[f"p{p}"] = sorted_times[idx]

        # Distribution buckets
        max_time = max(times_ms)
        bucket_size = max_time / 10  # 10 buckets
        buckets = defaultdict(int)

        for time_ms in times_ms:
            bucket = int(time_ms / bucket_size) if bucket_size > 0 else 0
            buckets[bucket] += 1

        # Outlier detection (values > 2 standard deviations)
        avg = mean(times_ms)
        std = stdev(times_ms) if len(times_ms) > 1 else 0
        outlier_threshold = avg + (2 * std)
        outliers = [t for t in times_ms if t > outlier_threshold]

        return {
            "percentiles": percentiles,
            "distribution_buckets": dict(buckets),
            "outliers": {
                "count": len(outliers),
                "threshold_ms": outlier_threshold,
                "max_outlier_ms": max(outliers) if outliers else 0,
                "outlier_percentage": (len(outliers) / len(times_ms)) * 100,
            },
        }

    def _analyze_overhead_trends(self, overhead_times: List[float]) -> Dict[str, Any]:
        """Analyze trends in overhead over time."""
        if len(overhead_times) < 10:
            return {"insufficient_data": True}

        # Split into windows for trend analysis
        window_size = len(overhead_times) // 5  # 5 windows
        windows = []

        for i in range(0, len(overhead_times), window_size):
            window = overhead_times[i : i + window_size]
            if len(window) >= 5:  # Minimum window size
                windows.append(
                    {
                        "start_idx": i,
                        "end_idx": i + len(window),
                        "avg_overhead_ms": mean(window),
                        "max_overhead_ms": max(window),
                        "sample_count": len(window),
                    }
                )

        # Calculate trend
        if len(windows) >= 2:
            first_avg = windows[0]["avg_overhead_ms"]
            last_avg = windows[-1]["avg_overhead_ms"]
            trend_direction = "increasing" if last_avg > first_avg else "decreasing"
            trend_magnitude = abs(last_avg - first_avg) / first_avg * 100
        else:
            trend_direction = "unknown"
            trend_magnitude = 0

        return {
            "windows": windows,
            "trend": {
                "direction": trend_direction,
                "magnitude_percent": trend_magnitude,
                "is_concerning": trend_direction == "increasing"
                and trend_magnitude > 20,
            },
        }

    def _identify_bottlenecks(self) -> Dict[str, Any]:
        """Identify potential performance bottlenecks."""
        bottlenecks = {"detected": [], "analysis": {}, "severity": "low"}

        perf_metrics = self.collector.performance_metrics
        overhead_times = list(perf_metrics.get("collection_overhead_ms", []))

        if not overhead_times:
            return bottlenecks

        avg_overhead = mean(overhead_times)
        max_overhead = max(overhead_times)

        # Check for various bottleneck indicators

        # 1. High average overhead
        if avg_overhead > self.config["overhead_concern_threshold"]:
            bottlenecks["detected"].append("high_average_overhead")
            bottlenecks["analysis"]["high_average_overhead"] = {
                "description": f"Average overhead ({avg_overhead:.2f}ms) exceeds threshold",
                "impact": "moderate",
                "recommendation": "Consider using buffered handler or reducing log verbosity",
            }

        # 2. High variance in overhead
        if len(overhead_times) > 1:
            std = stdev(overhead_times)
            cv = std / avg_overhead  # Coefficient of variation

            if cv > 0.5:  # High variability
                bottlenecks["detected"].append("high_variance")
                bottlenecks["analysis"]["high_variance"] = {
                    "description": f"High variance in processing times (CV: {cv:.2f})",
                    "impact": "low",
                    "recommendation": "Investigate sporadic performance spikes",
                }

        # 3. Memory pressure
        current_memory = perf_metrics.get("memory_usage_mb", 0)
        if current_memory > self.config["memory_concern_threshold"]:
            bottlenecks["detected"].append("high_memory_usage")
            bottlenecks["analysis"]["high_memory_usage"] = {
                "description": f"High memory usage ({current_memory:.1f}MB)",
                "impact": "moderate",
                "recommendation": "Reduce buffer size or enable compression",
            }

        # 4. Buffer pressure
        buffer_usage = self.collector.performance_metrics.get("buffer_usage", 0)
        buffer_size = self.collector.buffer_size
        buffer_percentage = (buffer_usage / buffer_size) * 100 if buffer_size > 0 else 0

        if buffer_percentage > 90:
            bottlenecks["detected"].append("buffer_pressure")
            bottlenecks["analysis"]["buffer_pressure"] = {
                "description": f"Buffer usage at {buffer_percentage:.1f}%",
                "impact": "high",
                "recommendation": "Increase buffer size or reduce logging volume",
            }

        # Determine overall severity
        high_impact = sum(
            1 for b in bottlenecks["analysis"].values() if b["impact"] == "high"
        )
        moderate_impact = sum(
            1 for b in bottlenecks["analysis"].values() if b["impact"] == "moderate"
        )

        if high_impact > 0:
            bottlenecks["severity"] = "high"
        elif moderate_impact > 0:
            bottlenecks["severity"] = "moderate"

        return bottlenecks

    def _analyze_resource_impact(self) -> Dict[str, Any]:
        """Analyze system resource impact of logging."""
        resource_analysis = {"memory": {}, "cpu": {}, "io": {}, "overall_impact": "low"}

        # Memory analysis
        current_memory = self.collector.performance_metrics.get("memory_usage_mb", 0)
        resource_analysis["memory"] = {
            "current_usage_mb": current_memory,
            "is_concerning": current_memory > self.config["memory_concern_threshold"],
            "trend": "unknown",  # Could be enhanced with historical data
        }

        # Message processing rate analysis
        msg_rate = self.collector.performance_metrics.get("messages_per_second", 0)
        peak_rate = self.collector.performance_metrics.get("peak_message_rate", 0)

        resource_analysis["throughput"] = {
            "current_rate": msg_rate,
            "peak_rate": peak_rate,
            "is_concerning": msg_rate > self.config["throughput_concern_threshold"],
        }

        # Determine overall impact
        concerns = 0
        if resource_analysis["memory"]["is_concerning"]:
            concerns += 1
        if resource_analysis["throughput"]["is_concerning"]:
            concerns += 1

        if concerns >= 2:
            resource_analysis["overall_impact"] = "high"
        elif concerns == 1:
            resource_analysis["overall_impact"] = "moderate"

        return resource_analysis

    def _detailed_overhead_breakdown(self) -> Dict[str, Any]:
        """Provide detailed breakdown of overhead sources."""
        # This would require more instrumentation in the actual collector
        # For now, provide analysis based on available data

        total_messages = self.collector.stats["total_messages"]
        total_overhead = self.collector.performance_metrics.get(
            "total_collection_time_ms", 0
        )

        breakdown = {
            "total_overhead_ms": total_overhead,
            "total_messages": total_messages,
            "overhead_per_message_ms": total_overhead / max(total_messages, 1),
            "estimated_components": {
                "feature_detection": "~20%",
                "statistics_recording": "~40%",
                "buffer_management": "~20%",
                "performance_tracking": "~20%",
            },
            "note": "Component breakdown is estimated based on typical patterns",
        }

        return breakdown

    def _comparative_performance_analysis(self) -> Dict[str, Any]:
        """Compare performance against baseline and benchmarks."""
        comparison = {
            "baseline_comparison": {},
            "benchmark_comparison": {},
            "efficiency_metrics": {},
        }

        # Compare with baseline if available
        if self.baseline_metrics:
            current_avg = mean(
                list(
                    self.collector.performance_metrics.get(
                        "collection_overhead_ms", [0]
                    )
                )
            )
            baseline_avg = self.baseline_metrics.get("average_overhead_ms", current_avg)

            comparison["baseline_comparison"] = {
                "current_avg_ms": current_avg,
                "baseline_avg_ms": baseline_avg,
                "change_percent": (
                    ((current_avg - baseline_avg) / baseline_avg) * 100
                    if baseline_avg > 0
                    else 0
                ),
                "performance_status": (
                    "degraded" if current_avg > baseline_avg * 1.1 else "stable"
                ),
            }

        # Benchmark comparison (industry standards)
        current_avg = mean(
            list(self.collector.performance_metrics.get("collection_overhead_ms", [0]))
        )
        comparison["benchmark_comparison"] = {
            "current_overhead_ms": current_avg,
            "industry_benchmark_ms": 1.0,  # Typical logging overhead
            "vs_benchmark": (
                "good"
                if current_avg < 2.0
                else "concerning"
                if current_avg > 5.0
                else "acceptable"
            ),
        }

        # Efficiency metrics
        total_time = self.collector.stats["session_duration"]
        logging_time = (
            self.collector.performance_metrics.get("total_collection_time_ms", 0) / 1000
        )
        efficiency = max(0, 100 - ((logging_time / max(total_time, 0.001)) * 100))

        comparison["efficiency_metrics"] = {
            "logging_efficiency_percent": efficiency,
            "time_spent_logging_percent": (logging_time / max(total_time, 0.001)) * 100,
            "efficiency_rating": (
                "excellent"
                if efficiency > 99
                else "good"
                if efficiency > 95
                else "concerning"
            ),
        }

        return comparison

    def _generate_performance_recommendations(
        self, analysis: Dict[str, Any]
    ) -> List[str]:
        """Generate performance optimization recommendations."""
        recommendations = []

        summary = analysis.get("summary", {})
        bottlenecks = analysis.get("bottlenecks", {})
        resource_impact = analysis.get("resource_impact", {})

        # High overhead recommendations
        if summary.get("is_concerning", False):
            avg_overhead = summary.get("average_overhead_ms", 0)
            recommendations.append(
                f"High average overhead detected ({avg_overhead:.2f}ms per message). "
                "Consider switching to buffered handler or reducing log verbosity."
            )

        # Bottleneck-specific recommendations
        detected_bottlenecks = bottlenecks.get("detected", [])

        if "high_memory_usage" in detected_bottlenecks:
            recommendations.append(
                "High memory usage detected. Consider reducing buffer size "
                "or increasing flush frequency."
            )

        if "buffer_pressure" in detected_bottlenecks:
            recommendations.append(
                "Buffer pressure detected. Increase buffer size or implement "
                "more aggressive flushing strategy."
            )

        if "high_variance" in detected_bottlenecks:
            recommendations.append(
                "High variance in processing times detected. "
                "Investigate potential system resource contention."
            )

        # Resource impact recommendations
        if resource_impact.get("overall_impact") == "high":
            recommendations.append(
                "High overall resource impact. Consider disabling statistics collection "
                "in production or reducing collection frequency."
            )

        # Throughput recommendations
        throughput_info = resource_impact.get("throughput", {})
        if throughput_info.get("is_concerning", False):
            recommendations.append(
                f"High message rate ({throughput_info.get('current_rate', 0):.1f}/s) detected. "
                "Consider using async logging or buffered handlers."
            )

        # General optimization recommendations
        overhead_times = list(
            self.collector.performance_metrics.get("collection_overhead_ms", [])
        )
        if overhead_times:
            avg_overhead = mean(overhead_times)

            if avg_overhead > 1.0:  # > 1ms average
                recommendations.append(
                    "Consider disabling performance tracking to reduce overhead "
                    "if detailed metrics are not needed."
                )

            if len(overhead_times) > 500:  # Large number of samples
                recommendations.append(
                    "Large number of performance samples collected. "
                    "Consider reducing sample retention to save memory."
                )

        return recommendations

    def recommend_optimizations(self) -> List[Dict[str, Any]]:
        """
        Recommend specific optimizations with implementation details.

        Returns:
            List of optimization recommendations with details
        """
        analysis = self.analyze_logging_overhead(detailed=True)

        optimizations = []

        # Handler optimization
        overhead_times = list(
            self.collector.performance_metrics.get("collection_overhead_ms", [])
        )
        if overhead_times and mean(overhead_times) > 5.0:
            optimizations.append(
                {
                    "category": "handler",
                    "priority": "high",
                    "title": "Switch to Buffered Handler",
                    "description": "High per-message overhead detected. Buffered handler can reduce impact.",
                    "implementation": {
                        "config_change": 'statistics.handler_type = "buffered"',
                        "buffer_size": "statistics.handler_buffer_size = 50",
                        "flush_interval": "statistics.flush_interval = 0.5",
                    },
                    "expected_improvement": "50-80% reduction in per-message overhead",
                }
            )

        # Buffer size optimization
        buffer_usage = self.collector.performance_metrics.get("buffer_usage", 0)
        if buffer_usage > self.collector.buffer_size * 0.9:
            optimizations.append(
                {
                    "category": "buffer",
                    "priority": "medium",
                    "title": "Increase Buffer Size",
                    "description": "Buffer near capacity. Increasing size can prevent data loss.",
                    "implementation": {
                        "config_change": f"statistics.buffer_size = {self.collector.buffer_size * 2}"
                    },
                    "expected_improvement": "Prevent buffer overflow and data loss",
                }
            )

        # Memory optimization
        current_memory = self.collector.performance_metrics.get("memory_usage_mb", 0)
        if current_memory > 50:  # > 50MB
            optimizations.append(
                {
                    "category": "memory",
                    "priority": "medium",
                    "title": "Reduce Memory Usage",
                    "description": "High memory usage detected. Several options available.",
                    "implementation": {
                        "reduce_buffer": "statistics.buffer_size = 500",
                        "disable_performance": "statistics.track_performance = false",
                        "shorter_retention": "Reduce message buffer retention period",
                    },
                    "expected_improvement": "30-60% memory usage reduction",
                }
            )

        # Feature-level optimization
        feature_stats = self.collector.stats.get("by_feature", {})
        if feature_stats:
            high_volume_features = [
                (feature, count)
                for feature, count in feature_stats.items()
                if count > self.collector.stats["total_messages"] * 0.2
            ]

            if high_volume_features:
                top_feature, count = max(high_volume_features, key=lambda x: x[1])
                optimizations.append(
                    {
                        "category": "feature_levels",
                        "priority": "high",
                        "title": f"Reduce Verbosity for {top_feature}",
                        "description": f'Feature generates {count} messages ({count/self.collector.stats["total_messages"]*100:.1f}% of total)',
                        "implementation": {
                            "config_change": f"logging.feature_levels.{top_feature} = WARNING"
                        },
                        "expected_improvement": f'Reduce total log volume by up to {count/self.collector.stats["total_messages"]*100:.1f}%',
                    }
                )

        return optimizations

    def set_baseline(self) -> None:
        """Set current performance metrics as baseline for comparison."""
        overhead_times = list(
            self.collector.performance_metrics.get("collection_overhead_ms", [])
        )

        if overhead_times:
            self.baseline_metrics = {
                "timestamp": datetime.now(),
                "average_overhead_ms": mean(overhead_times),
                "median_overhead_ms": median(overhead_times),
                "max_overhead_ms": max(overhead_times),
                "sample_count": len(overhead_times),
                "memory_usage_mb": self.collector.performance_metrics.get(
                    "memory_usage_mb", 0
                ),
            }

    def get_performance_summary(self) -> Dict[str, Any]:
        """Get a quick performance summary."""
        overhead_times = list(
            self.collector.performance_metrics.get("collection_overhead_ms", [])
        )

        if not overhead_times:
            return {"status": "no_data"}

        avg_overhead = mean(overhead_times)
        memory_usage = self.collector.performance_metrics.get("memory_usage_mb", 0)

        # Determine status
        if avg_overhead > self.config["overhead_concern_threshold"]:
            status = "concerning"
        elif avg_overhead > self.config["overhead_concern_threshold"] / 2:
            status = "moderate"
        else:
            status = "good"

        return {
            "status": status,
            "average_overhead_ms": avg_overhead,
            "memory_usage_mb": memory_usage,
            "sample_count": len(overhead_times),
            "recommendations_available": status != "good",
        }

    def _is_cache_valid(self, cache_key: str) -> bool:
        """Check if cached analysis is still valid."""
        if cache_key not in self._analysis_cache:
            return False

        timestamp = self._cache_timestamps.get(cache_key)
        if not timestamp:
            return False

        age = (datetime.now() - timestamp).total_seconds()
        return age < self._cache_ttl

    def clear_cache(self) -> None:
        """Clear all cached analysis results."""
        self._analysis_cache.clear()
        self._cache_timestamps.clear()


def create_performance_analyzer(
    collector: LogStatisticsCollector,
) -> LogPerformanceAnalyzer:
    """
    Factory function to create a performance analyzer.

    Args:
        collector: Statistics collector instance

    Returns:
        Configured LogPerformanceAnalyzer instance
    """
    return LogPerformanceAnalyzer(collector)
