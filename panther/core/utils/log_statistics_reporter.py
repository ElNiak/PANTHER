"""
Log Statistics Reporter

This module provides reporting and display functionality for logging statistics,
including real-time console output and comprehensive report generation.
"""

import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from .log_statistics_collector import LogStatisticsCollector


class LogStatisticsReporter:
    """
    Reporter for logging statistics with multiple output formats and display options.

    Provides both real-time statistics display and comprehensive report generation
    capabilities for analyzing logging behavior and performance.
    """

    def __init__(self, collector: LogStatisticsCollector):
        """
        Initialize the statistics reporter.

        Args:
            collector: The statistics collector to report from
        """
        self.collector = collector
        self.report_templates = {
            "summary": self._format_summary_section,
            "features": self._format_features_section,
            "performance": self._format_performance_section,
            "errors": self._format_errors_section,
            "recommendations": self._format_recommendations_section,
        }

    def print_real_time_stats(
        self,
        show_features: bool = True,
        show_performance: bool = True,
        compact: bool = False,
    ) -> None:
        """
        Print live statistics to console.

        Args:
            show_features: Whether to include feature breakdown
            show_performance: Whether to include performance metrics
            compact: Whether to use compact display format
        """
        try:
            stats = self.collector.get_real_time_stats()

            if compact:
                self._print_compact_stats(stats)
            else:
                self._print_detailed_stats(stats, show_features, show_performance)

        except Exception as e:
            print(f"Error displaying real-time statistics: {e}")

    def _print_compact_stats(self, stats: Dict[str, Any]) -> None:
        """Print compact one-line statistics."""
        session = stats["session_info"]
        errors = stats["error_statistics"]
        perf = stats["performance_metrics"]

        print(
            f"📊 Logs: {session['total_messages']} | "
            f"Rate: {session['messages_per_second']:.1f}/s | "
            f"Errors: {errors['total_errors']} ({errors['error_rate_percent']:.1f}%) | "
            f"Memory: {perf.get('memory_usage_mb', 0):.1f}MB"
        )

    def _print_detailed_stats(
        self, stats: Dict[str, Any], show_features: bool, show_performance: bool
    ) -> None:
        """Print detailed multi-line statistics."""
        session = stats["session_info"]
        distribution = stats["message_distribution"]
        errors = stats["error_statistics"]
        performance = stats["performance_metrics"]
        buffer_info = stats["buffer_info"]

        # Header
        print("\n" + "=" * 60)
        print("🐾 PANTHER Logging Statistics - Real-time View")
        print("=" * 60)

        # Session info
        print(f"📅 Session Duration: {session['duration_seconds']:.1f}s")
        print(f"📝 Total Messages: {session['total_messages']}")
        print(f"⚡ Current Rate: {session['messages_per_second']:.2f} messages/sec")

        # Level distribution
        print(f"\n📊 Message Levels:")
        total = session["total_messages"]
        for level, count in distribution["by_level"].items():
            percentage = (count / max(total, 1)) * 100
            bar = self._create_progress_bar(percentage, 20)
            print(f"  {level:8s}: {count:6d} ({percentage:5.1f}%) {bar}")

        # Feature breakdown
        if show_features and distribution["by_feature"]:
            print(f"\n🔧 Top Active Features:")
            for i, (feature, count) in enumerate(
                list(distribution["by_feature"].items())[:5]
            ):
                percentage = (count / max(total, 1)) * 100
                print(f"  {i+1}. {feature:20s}: {count:6d} ({percentage:5.1f}%)")

        # Error statistics
        if errors["total_errors"] > 0:
            print(f"\n❌ Error Statistics:")
            print(f"  Total Errors: {errors['total_errors']}")
            print(f"  Error Rate: {errors['error_rate_percent']:.2f}%")
            print(f"  Recent Errors: {errors['recent_error_count']}")

        # Performance metrics
        if show_performance:
            print(f"\n⚡ Performance Metrics:")
            print(f"  Memory Usage: {performance.get('memory_usage_mb', 0):.1f} MB")
            print(f"  Peak Rate: {performance.get('peak_message_rate', 0):.1f} msg/s")
            print(
                f"  Buffer Usage: {buffer_info['usage_percent']:.1f}% ({buffer_info['current_size']}/{buffer_info['max_size']})"
            )

            if performance.get("collection_overhead_ms"):
                avg_overhead = sum(performance["collection_overhead_ms"]) / len(
                    performance["collection_overhead_ms"]
                )
                print(f"  Avg Overhead: {avg_overhead:.2f} ms/message")

        print("=" * 60)

    def _create_progress_bar(self, percentage: float, width: int = 20) -> str:
        """Create a simple ASCII progress bar."""
        filled = int((percentage / 100) * width)
        bar = "█" * filled + "░" * (width - filled)
        return f"[{bar}]"

    def generate_text_report(self, sections: Optional[List[str]] = None) -> str:
        """
        Generate human-readable text report.

        Args:
            sections: List of sections to include ('summary', 'features', 'performance', 'errors', 'recommendations')

        Returns:
            Formatted text report
        """
        if sections is None:
            sections = [
                "summary",
                "features",
                "performance",
                "errors",
                "recommendations",
            ]

        try:
            report = self.collector.generate_summary_report()

            lines = []
            lines.append("PANTHER LOGGING STATISTICS REPORT")
            lines.append("=" * 50)
            lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            lines.append("")

            for section in sections:
                if section in self.report_templates:
                    section_content = self.report_templates[section](report)
                    if section_content:
                        lines.extend(section_content)
                        lines.append("")

            return "\n".join(lines)

        except Exception as e:
            return f"Error generating text report: {e}"

    def _format_summary_section(self, report: Dict[str, Any]) -> List[str]:
        """Format the summary section of the report."""
        lines = []
        summary = report["summary"]
        session = summary["session_info"]
        distribution = summary["message_distribution"]

        lines.append("📊 SUMMARY")
        lines.append("-" * 20)
        lines.append(f"Collection Period: {session['duration_seconds']:.1f} seconds")
        lines.append(f"Total Messages: {session['total_messages']}")
        lines.append(
            f"Average Rate: {session['messages_per_second']:.2f} messages/second"
        )
        lines.append("")

        lines.append("Message Distribution by Level:")
        total = session["total_messages"]
        for level, count in distribution["by_level"].items():
            percentage = (count / max(total, 1)) * 100
            lines.append(f"  {level:10s}: {count:8d} ({percentage:6.2f}%)")

        return lines

    def _format_features_section(self, report: Dict[str, Any]) -> List[str]:
        """Format the features section of the report."""
        lines = []
        feature_analysis = report.get("feature_analysis", {})

        if not feature_analysis:
            return lines

        lines.append("🔧 FEATURE ANALYSIS")
        lines.append("-" * 20)

        # Sort features by total messages
        sorted_features = sorted(
            feature_analysis.items(),
            key=lambda x: x[1].get("total_messages", 0),
            reverse=True,
        )

        for feature, data in sorted_features[:10]:  # Top 10 features
            total_msgs = data.get("total_messages", 0)
            rate = data.get("message_rate", 0)
            modules = data.get("unique_modules", 0)
            duration = data.get("active_duration", 0)

            lines.append(f"  {feature}:")
            lines.append(f"    Messages: {total_msgs}")
            lines.append(f"    Rate: {rate:.2f} msg/s")
            lines.append(f"    Modules: {modules}")
            lines.append(f"    Duration: {duration:.1f}s")

            # Level distribution for this feature
            level_dist = data.get("level_distribution", {})
            if level_dist:
                level_summary = ", ".join(
                    [f"{k}:{v}" for k, v in level_dist.items() if v > 0]
                )
                lines.append(f"    Levels: {level_summary}")
            lines.append("")

        return lines

    def _format_performance_section(self, report: Dict[str, Any]) -> List[str]:
        """Format the performance section of the report."""
        lines = []
        perf_analysis = report.get("performance_analysis", {})

        if perf_analysis.get("performance_tracking_disabled"):
            lines.append("⚡ PERFORMANCE ANALYSIS")
            lines.append("-" * 20)
            lines.append("Performance tracking is disabled")
            return lines

        lines.append("⚡ PERFORMANCE ANALYSIS")
        lines.append("-" * 20)

        # Collection overhead
        overhead = perf_analysis.get("collection_overhead", {})
        if overhead:
            lines.append("Collection Overhead:")
            lines.append(
                f"  Average: {overhead.get('average_ms', 0):.2f} ms per message"
            )
            lines.append(f"  Total: {overhead.get('total_ms', 0):.2f} ms")
            lines.append(
                f"  Range: {overhead.get('min_ms', 0):.2f} - {overhead.get('max_ms', 0):.2f} ms"
            )
            lines.append(f"  Samples: {overhead.get('samples', 0)}")
            lines.append("")

        # Message rates
        rates = perf_analysis.get("message_rates", {})
        if rates:
            lines.append("Message Rates:")
            lines.append(
                f"  Current: {rates.get('current_per_second', 0):.2f} messages/second"
            )
            lines.append(
                f"  Peak: {rates.get('peak_per_second', 0):.2f} messages/second"
            )
            lines.append("")

        # Memory usage
        memory = perf_analysis.get("memory_usage", {})
        if memory:
            lines.append("Memory Usage:")
            lines.append(f"  Current: {memory.get('current_mb', 0):.2f} MB")
            lines.append(
                f"  Buffer Usage: {memory.get('buffer_usage_percent', 0):.1f}%"
            )

        return lines

    def _format_errors_section(self, report: Dict[str, Any]) -> List[str]:
        """Format the errors section of the report."""
        lines = []
        error_analysis = report.get("error_analysis", {})

        if not error_analysis or error_analysis.get("total_errors", 0) == 0:
            return lines

        lines.append("❌ ERROR ANALYSIS")
        lines.append("-" * 20)
        lines.append(f"Total Errors: {error_analysis.get('total_errors', 0)}")

        # Errors by feature
        errors_by_feature = error_analysis.get("errors_by_feature", {})
        if errors_by_feature:
            lines.append("")
            lines.append("Errors by Feature:")
            for feature, count in sorted(
                errors_by_feature.items(), key=lambda x: x[1], reverse=True
            )[:5]:
                lines.append(f"  {feature}: {count}")

        # Common error patterns
        patterns = error_analysis.get("common_error_patterns", {})
        if patterns:
            lines.append("")
            lines.append("Common Error Patterns:")
            for pattern, count in list(patterns.items())[:5]:
                lines.append(f"  '{pattern}': {count} occurrences")

        # Recent errors
        recent = error_analysis.get("recent_errors", [])
        if recent:
            lines.append("")
            lines.append("Recent Errors:")
            for error in recent[-3:]:  # Last 3 errors
                timestamp = error.get("timestamp", "Unknown")
                message = error.get("message", "No message")[:80]
                feature = error.get("feature", "unknown")
                lines.append(f"  [{timestamp}] {feature}: {message}")

        return lines

    def _format_recommendations_section(self, report: Dict[str, Any]) -> List[str]:
        """Format the recommendations section of the report."""
        lines = []
        recommendations = report.get("recommendations", [])

        if not recommendations:
            return lines

        lines.append("💡 RECOMMENDATIONS")
        lines.append("-" * 20)
        for i, rec in enumerate(recommendations, 1):
            lines.append(f"{i}. {rec}")

        return lines

    def generate_json_report(self, pretty: bool = True) -> str:
        """
        Generate JSON statistics report.

        Args:
            pretty: Whether to format JSON with indentation

        Returns:
            JSON formatted statistics report
        """
        try:
            report = self.collector.generate_summary_report()

            if pretty:
                return json.dumps(report, indent=2, default=str)
            else:
                return json.dumps(report, default=str)

        except Exception as e:
            return json.dumps({"error": f"Failed to generate JSON report: {e}"})

    def generate_csv_report(self) -> str:
        """
        Generate CSV statistics report.

        Returns:
            CSV formatted statistics report
        """
        try:
            report = self.collector.generate_summary_report()
            summary = report["summary"]

            lines = ["metric,value,category"]

            # Session info
            session = summary["session_info"]
            lines.append(f"total_messages,{session['total_messages']},session")
            lines.append(f"duration_seconds,{session['duration_seconds']},session")
            lines.append(
                f"messages_per_second,{session['messages_per_second']},session"
            )

            # Level distribution
            for level, count in summary["message_distribution"]["by_level"].items():
                lines.append(f"level_{level.lower()},{count},levels")

            # Feature distribution
            for feature, count in summary["message_distribution"]["by_feature"].items():
                lines.append(f"feature_{feature},{count},features")

            # Error statistics
            error_stats = summary["error_statistics"]
            lines.append(f"total_errors,{error_stats['total_errors']},errors")
            lines.append(
                f"error_rate_percent,{error_stats['error_rate_percent']},errors"
            )

            # Performance metrics
            perf = summary["performance_metrics"]
            if (
                not isinstance(perf, dict)
                or "performance_tracking_disabled" not in perf
            ):
                lines.append(
                    f"memory_usage_mb,{perf.get('memory_usage_mb', 0)},performance"
                )
                lines.append(
                    f"peak_message_rate,{perf.get('peak_message_rate', 0)},performance"
                )

            return "\n".join(lines)

        except Exception as e:
            return f"error,Failed to generate CSV report: {e},error"

    def export_to_file(self, filepath: Path, format: str = "json", **kwargs) -> bool:
        """
        Export statistics to file.

        Args:
            filepath: Path where to save the report
            format: Export format ('json', 'csv', 'text')
            **kwargs: Additional arguments for specific formats

        Returns:
            True if export successful, False otherwise
        """
        try:
            filepath = Path(filepath)
            filepath.parent.mkdir(parents=True, exist_ok=True)

            if format.lower() == "json":
                content = self.generate_json_report(pretty=kwargs.get("pretty", True))
            elif format.lower() == "csv":
                content = self.generate_csv_report()
            elif format.lower() == "text":
                sections = kwargs.get("sections", None)
                content = self.generate_text_report(sections=sections)
            else:
                raise ValueError(f"Unsupported export format: {format}")

            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)

            return True

        except Exception as e:
            print(f"Error exporting statistics to {filepath}: {e}")
            return False

    def save_real_time_snapshot(self, filepath: Path) -> bool:
        """
        Save current real-time statistics as a snapshot.

        Args:
            filepath: Path where to save the snapshot

        Returns:
            True if save successful, False otherwise
        """
        try:
            stats = self.collector.get_real_time_stats()

            filepath = Path(filepath)
            filepath.parent.mkdir(parents=True, exist_ok=True)

            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(stats, f, indent=2, default=str)

            return True

        except Exception as e:
            print(f"Error saving real-time snapshot to {filepath}: {e}")
            return False

    def compare_with_baseline(self, baseline_path: Path) -> Dict[str, Any]:
        """
        Compare current statistics with a baseline report.

        Args:
            baseline_path: Path to baseline statistics file

        Returns:
            Comparison results
        """
        try:
            # Load baseline
            with open(baseline_path, "r", encoding="utf-8") as f:
                baseline = json.load(f)

            # Get current stats
            current = self.collector.get_real_time_stats()

            # Compare key metrics
            comparison = {
                "comparison_timestamp": datetime.now(),
                "baseline_file": str(baseline_path),
                "metrics_comparison": {},
                "differences": [],
            }

            # Compare session info
            if "session_info" in baseline and "session_info" in current:
                baseline_session = baseline["session_info"]
                current_session = current["session_info"]

                for metric in ["total_messages", "messages_per_second"]:
                    if metric in baseline_session and metric in current_session:
                        baseline_val = baseline_session[metric]
                        current_val = current_session[metric]
                        diff_percent = (
                            (current_val - baseline_val) / max(baseline_val, 1)
                        ) * 100

                        comparison["metrics_comparison"][metric] = {
                            "baseline": baseline_val,
                            "current": current_val,
                            "difference_percent": diff_percent,
                        }

                        if abs(diff_percent) > 10:  # Significant difference
                            comparison["differences"].append(
                                f"{metric}: {diff_percent:+.1f}% change from baseline"
                            )

            return comparison

        except Exception as e:
            return {"error": f"Failed to compare with baseline: {e}"}


def create_console_reporter(collector: LogStatisticsCollector) -> LogStatisticsReporter:
    """
    Factory function to create a console-optimized reporter.

    Args:
        collector: The statistics collector instance

    Returns:
        Configured LogStatisticsReporter for console output
    """
    return LogStatisticsReporter(collector)
