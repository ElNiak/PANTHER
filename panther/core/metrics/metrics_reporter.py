"""
Metrics Reporter Module

This module provides reporting and analysis capabilities for collected metrics,
generating human-readable reports and summaries of experiment performance.
"""

import logging
from pathlib import Path
from typing import Any
from datetime import datetime
from .metrics_collector import MetricsCollector, MetricType


class MetricsReporter:
    """
    Generates reports and summaries from collected metrics.

    Provides various reporting formats including text summaries,
    detailed analysis, and performance insights.
    """

    def __init__(self, metrics_collector: MetricsCollector):
        """
        Initialize the metrics reporter.

        Args:
            metrics_collector: MetricsCollector instance with collected metrics
        """
        self.metrics_collector = metrics_collector
        self.logger = logging.getLogger(self.__class__.__name__)

    def generate_report(self, output_path: str) -> bool:
        """
        Generate a detailed metrics report and save it to a file.

        Args:
            output_path: The path where the report file should be saved

        Returns:
            bool: True if report was successfully generated, False otherwise
        """
        try:
            # Generate the report content
            report_content = self.generate_summary_report()

            # Add detailed sections
            report_content += "\n\n" + self.generate_detailed_timing_section()
            report_content += "\n\n" + self.generate_resource_usage_section()
            report_content += "\n\n" + self.generate_errors_section()

            # Write to file
            with open(output_path, "w") as f:
                f.write(report_content)

            self.logger.info("Metrics report generated at %s", output_path)
            return True
        except Exception as e:
            self.logger.error("Failed to generate metrics report: %s", e)
            return False

    def generate_detailed_timing_section(self) -> str:
        """Generate a detailed section for timing metrics"""
        try:
            timing_metrics = [
                m for m in self.metrics_collector.metrics if m.metric_type == MetricType.TIMING
            ]

            if not timing_metrics:
                return "DETAILED TIMING\n============\nNo timing metrics recorded."

            lines = [
                "DETAILED TIMING",
                "==============",
            ]

            # Group by component and test case
            by_component = {}
            for metric in timing_metrics:
                try:
                    # Safely get component with a fallback value
                    component = "global"
                    if hasattr(metric, "component"):
                        if metric.component is not None:
                            component = metric.component

                    if component not in by_component:
                        by_component[component] = []

                    by_component[component].append(metric)
                except Exception as e:
                    self.logger.warning("Skipping metric in detailed timing section due to: %s", e)

            for component, metrics in by_component.items():
                lines.append(f"\nComponent: {component}")
                lines.append("-" * 40)

                # Sort by duration (descending) with error handling
                try:
                    metrics.sort(
                        key=lambda x: (
                            getattr(x, "value", 0)
                            if isinstance(getattr(x, "value", 0), (int, float))
                            else 0
                        ),
                        reverse=True,
                    )
                except Exception as e:
                    self.logger.warning("Failed to sort metrics by value: %s", e)

                for metric in metrics:
                    try:
                        # Safe access to metric attributes with fallbacks
                        metric_name = getattr(metric, "name", "unnamed")

                        # Handle test_case safely
                        test_case = ""
                        if hasattr(metric, "test_case") and metric.test_case:
                            test_case = f" [{metric.test_case}]"

                        # Handle phase safely - it might be an enum or string
                        phase = ""
                        if hasattr(metric, "phase") and metric.phase:
                            try:
                                if hasattr(metric.phase, "value"):
                                    phase = f" ({metric.phase.value})"
                                else:
                                    phase = f" ({metric.phase})"
                            except Exception:
                                phase = " (unknown phase)"

                        # Handle value safely
                        value = getattr(metric, "value", 0)
                        if isinstance(value, (int, float)):
                            lines.append(f"{metric_name}{test_case}{phase}: {value:.4f}s")
                        else:
                            lines.append(f"{metric_name}{test_case}{phase}: {value}s")

                    except Exception as e:
                        self.logger.warning("Error processing timing metric: %s", e)
                        lines.append(f"[Error processing metric data: {e}]")

            return "\n".join(lines)

        except Exception as e:
            self.logger.error("Failed to generate detailed timing section: %s", e)
            return "DETAILED TIMING\n============\nError generating timing details."

    def generate_resource_usage_section(self) -> str:
        """Generate a detailed section for resource usage metrics"""
        try:
            # Get resource metrics with safe access to metric_type and component
            resource_metrics = []
            for m in self.metrics_collector.metrics:
                try:
                    if (
                        hasattr(m, "metric_type")
                        and m.metric_type == MetricType.GAUGE
                        and hasattr(m, "component")
                        and m.component == "resource_monitor"
                    ):
                        resource_metrics.append(m)
                except Exception:
                    # Skip metrics that don't fit or cause errors
                    continue

            if not resource_metrics:
                return "RESOURCE USAGE\n=============\nNo resource metrics recorded."

            lines = [
                "RESOURCE USAGE",
                "=============",
                "\nPeak Resource Usage:",
            ]

            # Find peak values for key metrics
            resource_types = {
                "cpu_percent": "CPU Usage",
                "memory_percent": "Memory Usage",
                "memory_used_mb": "Memory Used",
                "disk_read_mb_total": "Disk Read",
                "disk_write_mb_total": "Disk Write",
                "network_sent_mb_total": "Network Sent",
                "network_recv_mb_total": "Network Received",
            }

            by_type = {}
            for metric in resource_metrics:
                try:
                    metric_name = getattr(metric, "name", "")
                    if metric_name in resource_types:
                        # Only compare if the metric has a numeric value
                        metric_value = getattr(metric, "value", 0)
                        if not isinstance(metric_value, (int, float)):
                            try:
                                # Try to convert to float if it's a string
                                metric_value = float(metric_value)
                            except (ValueError, TypeError):
                                # Skip metrics with non-numeric values
                                continue

                    if metric_name not in by_type or metric_value > getattr(
                        by_type[metric_name], "value", 0
                    ):
                        by_type[metric_name] = metric
                except Exception as e:
                    self.logger.debug("Skipped resource metric due to: %s", e)

            for name, metric in by_type.items():
                try:
                    display_name = resource_types[name]
                    value = getattr(metric, "value", 0)

                    # Make sure value is numeric
                    if not isinstance(value, (int, float)):
                        try:
                            value = float(value)
                        except (ValueError, TypeError):
                            lines.append(f"{display_name}: Invalid value")
                            continue

                    if name.endswith("_percent"):
                        lines.append(f"{display_name}: {value:.1f}%")
                    elif name.endswith("_mb") or name.endswith("_mb_total"):
                        lines.append(f"{display_name}: {value:.2f} MB")
                    else:
                        lines.append(f"{display_name}: {value}")
                except Exception as e:
                    self.logger.debug("Error formatting resource metric: %s", e)
                    lines.append(f"{resource_types.get(name, name)}: Error formatting value")

            return "\n".join(lines)

        except Exception as e:
            self.logger.error("Failed to generate resource usage section: %s", e)
            return "RESOURCE USAGE\n=============\nError generating resource usage details."

    def generate_errors_section(self) -> str:
        """Generate a section reporting on errors that occurred"""
        try:
            # Safe access to metrics with error handling
            error_metrics = []
            for m in self.metrics_collector.metrics:
                try:
                    if hasattr(m, "metric_type") and m.metric_type == MetricType.ERROR:
                        error_metrics.append(m)
                except Exception:
                    # Skip metrics that cause errors
                    continue

            if not error_metrics:
                return "ERRORS\n======\nNo errors recorded during execution."

            lines = [
                "ERRORS",
                "======",
                f"\nTotal Errors: {len(error_metrics)}",
            ]

            for i, metric in enumerate(error_metrics, 1):
                try:
                    # Safe access to metadata with default values
                    metadata = getattr(metric, "metadata", {}) or {}

                    # Get error details safely
                    error_type = "Unknown"
                    if isinstance(metadata, dict):
                        error_type = metadata.get("error_type", "Unknown")
                    elif hasattr(metadata, "get"):
                        error_type = metadata.get("error_type", "Unknown")

                    # Get error message safely
                    error_msg = "No details available"
                    if isinstance(metadata, dict):
                        error_msg = metadata.get("error_message", "No details available")
                    elif hasattr(metadata, "get"):
                        error_msg = metadata.get("error_message", "No details available")

                    # Safe access to component with fallback
                    component = "unknown"
                    if hasattr(metric, "component"):
                        if metric.component is not None:
                            component = metric.component

                    # Safe access to phase with fallback
                    phase = "unknown phase"
                    if hasattr(metric, "phase") and metric.phase is not None:
                        try:
                            if hasattr(metric.phase, "value"):
                                phase = metric.phase.value
                            else:
                                phase = str(metric.phase)
                        except Exception:
                            pass

                    lines.append(f"\nError #{i}:")
                    lines.append(f"  Type: {error_type}")
                    lines.append(f"  Component: {component}")
                    lines.append(f"  Phase: {phase}")
                    lines.append(f"  Message: {error_msg}")

                except Exception as e:
                    self.logger.warning("Error processing error metric: %s", e)
                    lines.append(f"\nError #{i}: [Error processing error data: {e}]")

            return "\n".join(lines)

        except Exception as e:
            self.logger.error("Failed to generate errors section: %s", e)
            return "ERRORS\n======\nError generating error details section."

    def generate_summary_report(self) -> str:
        """
        Generate a summary report of the experiment metrics.

        Returns:
            Formatted summary report string
        """
        try:
            stats = self.metrics_collector.get_summary_stats()

            if not stats:
                return "No metrics data available for reporting."

            report_lines = [
                "=" * 60,
                "PANTHER EXPERIMENT METRICS SUMMARY",
                "=" * 60,
            ]

            # Safe access to stats values with default fallbacks
            try:
                report_lines.append(f"Experiment: {stats.get('experiment_name', 'Unnamed')}")
            except Exception:
                report_lines.append("Experiment: (name unavailable)")

            try:
                duration = stats.get("experiment_duration", 0)
                if isinstance(duration, (int, float)):
                    report_lines.append(f"Duration: {duration:.2f} seconds")
                else:
                    report_lines.append(f"Duration: {duration} seconds")
            except Exception:
                report_lines.append("Duration: (unavailable)")

            try:
                report_lines.append(f"Total Metrics: {stats.get('total_metrics', 0)}")
            except Exception:
                report_lines.append("Total Metrics: (unknown)")

            try:
                report_lines.append(f"Errors: {stats.get('error_count', 0)}")
            except Exception:
                report_lines.append("Errors: (unknown)")

            report_lines.append("")
            report_lines.append("METRIC TYPES:")
            report_lines.append("-" * 20)

            try:
                metric_types = stats.get("metric_types", {})
                if metric_types:
                    for metric_type, count in metric_types.items():
                        report_lines.append(f"  {metric_type}: {count}")
                else:
                    report_lines.append("  No metric types recorded")
            except Exception:
                report_lines.append("  (Metric types unavailable)")

            if stats.get("phases"):
                try:
                    report_lines.extend(["", "EXECUTION PHASES:", "-" * 20])
                    for phase, count in stats.get("phases", {}).items():
                        phase_name = phase
                        # Handle case where phase is an enum with value attribute
                        if hasattr(phase, "value"):
                            phase_name = phase.value
                        elif not isinstance(phase, str):
                            phase_name = str(phase)
                        report_lines.append(f"  {phase_name}: {count} metrics")
                except Exception:
                    report_lines.append("  (Phase information unavailable)")

            if stats.get("test_cases"):
                try:
                    report_lines.extend(["", "TEST CASES:", "-" * 20])
                    for test_case in stats.get("test_cases", []):
                        try:
                            test_metrics = self.metrics_collector.get_metrics(test_case=test_case)
                            errors = len(
                                [m for m in test_metrics if m.metric_type == MetricType.ERROR]
                            )
                            status = "FAILED" if errors > 0 else "PASSED"
                            report_lines.append(
                                f"  {test_case}: {len(test_metrics)} metrics [{status}]"
                            )
                        except Exception:
                            report_lines.append(f"  {test_case}: (metrics unavailable)")
                except Exception:
                    report_lines.append("  (Test case information unavailable)")

            if stats.get("components"):
                try:
                    report_lines.extend(["", "COMPONENTS:", "-" * 20])
                    for component in stats.get("components", []):
                        try:
                            comp_metrics = self.metrics_collector.get_metrics(component=component)
                            report_lines.append(f"  {component}: {len(comp_metrics)} metrics")
                        except Exception:
                            report_lines.append(f"  {component}: (metrics unavailable)")
                except Exception:
                    report_lines.append("  (Component information unavailable)")

            if stats.get("timing_stats"):
                try:
                    timing = stats.get("timing_stats", {})
                    report_lines.extend(
                        [
                            "",
                            "TIMING STATISTICS:",
                            "-" * 20,
                        ]
                    )

                    # Safe access to timing stats with appropriate type handling
                    count = timing.get("count", 0)
                    total = timing.get("total", 0)
                    avg = timing.get("avg", 0)
                    min_time = timing.get("min", 0)
                    max_time = timing.get("max", 0)

                    report_lines.append(f"  Operations: {count}")

                    # Format timing values safely
                    if isinstance(total, (int, float)):
                        report_lines.append(f"  Total Time: {total:.3f}s")
                    else:
                        report_lines.append(f"  Total Time: {total}s")

                    if isinstance(avg, (int, float)):
                        report_lines.append(f"  Average: {avg:.3f}s")
                    else:
                        report_lines.append(f"  Average: {avg}s")

                    if isinstance(min_time, (int, float)):
                        report_lines.append(f"  Min: {min_time:.3f}s")
                    else:
                        report_lines.append(f"  Min: {min_time}s")

                    if isinstance(max_time, (int, float)):
                        report_lines.append(f"  Max: {max_time:.3f}s")
                    else:
                        report_lines.append(f"  Max: {max_time}s")

                except Exception:
                    report_lines.append("  (Timing statistics unavailable)")

            report_lines.append("=" * 60)

            return "\n".join(report_lines)

        except Exception as e:
            self.logger.error("Failed to generate summary report: %s", e)
            return f"Error generating report: {e}\n\nPlease check the logs for more information."

    def generate_detailed_report(self) -> str:
        """
        Generate a detailed report including timing breakdown and error analysis.

        Returns:
            Formatted detailed report string
        """
        report_lines = [
            "=" * 80,
            "PANTHER EXPERIMENT DETAILED METRICS REPORT",
            "=" * 80,
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "",
        ]

        # Add summary section
        report_lines.extend(self.generate_summary_report().split("\n"))
        report_lines.append("")

        # Timing analysis
        timing_analysis = self._analyze_timing_metrics()
        if timing_analysis:
            report_lines.extend(["TIMING ANALYSIS:", "-" * 40])
            report_lines.extend(timing_analysis)
            report_lines.append("")

        # Error analysis
        error_analysis = self._analyze_error_metrics()
        if error_analysis:
            report_lines.extend(["ERROR ANALYSIS:", "-" * 40])
            report_lines.extend(error_analysis)
            report_lines.append("")

        # Resource usage analysis
        resource_analysis = self._analyze_resource_metrics()
        if resource_analysis:
            report_lines.extend(["RESOURCE USAGE ANALYSIS:", "-" * 40])
            report_lines.extend(resource_analysis)
            report_lines.append("")

        # Phase breakdown
        phase_analysis = self._analyze_phase_metrics()
        if phase_analysis:
            report_lines.extend(["PHASE BREAKDOWN:", "-" * 40])
            report_lines.extend(phase_analysis)
            report_lines.append("")

        report_lines.append("=" * 80)

        return "\n".join(report_lines)

    def _analyze_timing_metrics(self) -> list[str]:
        """Analyze timing metrics and generate insights."""
        timing_metrics = self.metrics_collector.get_metrics(metric_type=MetricType.TIMING)

        if not timing_metrics:
            return ["No timing metrics available."]

        # Group by operation name
        timing_by_operation = {}
        timing_by_phase = {}
        timing_by_test_case = {}

        for metric in timing_metrics:
            # By operation
            op_name = metric.name.replace("_duration", "")
            if op_name not in timing_by_operation:
                timing_by_operation[op_name] = []
            timing_by_operation[op_name].append(metric.value)

            # By phase
            if metric.phase:
                phase_name = metric.phase.value
                if phase_name not in timing_by_phase:
                    timing_by_phase[phase_name] = []
                timing_by_phase[phase_name].append(metric.value)

            # By test case
            if metric.test_case:
                if metric.test_case not in timing_by_test_case:
                    timing_by_test_case[metric.test_case] = []
                timing_by_test_case[metric.test_case].append(metric.value)

        lines = []

        # Top slowest operations
        if timing_by_operation:
            lines.append("Slowest Operations:")
            operation_totals = {op: sum(times) for op, times in timing_by_operation.items()}
            sorted_ops = sorted(operation_totals.items(), key=lambda x: x[1], reverse=True)[:10]

            for op, total_time in sorted_ops:
                times = timing_by_operation[op]
                avg_time = sum(times) / len(times)
                lines.append(
                    f"  {op}: {total_time:.3f}s total, {avg_time:.3f}s avg ({len(times)} calls)"
                )

        # Phase timing
        if timing_by_phase:
            lines.append("")
            lines.append("Phase Timing:")
            phase_totals = {phase: sum(times) for phase, times in timing_by_phase.items()}
            sorted_phases = sorted(phase_totals.items(), key=lambda x: x[1], reverse=True)

            for phase, total_time in sorted_phases:
                lines.append(f"  {phase}: {total_time:.3f}s")

        # Test case timing
        if timing_by_test_case:
            lines.append("")
            lines.append("Test Case Timing:")
            test_totals = {test: sum(times) for test, times in timing_by_test_case.items()}
            sorted_tests = sorted(test_totals.items(), key=lambda x: x[1], reverse=True)

            for test, total_time in sorted_tests:
                lines.append(f"  {test}: {total_time:.3f}s")

        return lines

    def _analyze_error_metrics(self) -> list[str]:
        """Analyze error metrics and generate insights."""
        error_metrics = self.metrics_collector.get_metrics(metric_type=MetricType.ERROR)

        if not error_metrics:
            return ["No errors recorded during experiment."]

        lines = []

        # Group errors by type
        errors_by_type = {}
        errors_by_phase = {}
        errors_by_test_case = {}

        for metric in error_metrics:
            error_type = metric.metadata.get("error_type", "unknown")
            error_message = metric.metadata.get("error_message", "No message")

            # By type
            if error_type not in errors_by_type:
                errors_by_type[error_type] = []
            errors_by_type[error_type].append(error_message)

            # By phase
            if metric.phase:
                phase_name = metric.phase.value
                if phase_name not in errors_by_phase:
                    errors_by_phase[phase_name] = 0
                errors_by_phase[phase_name] += 1

            # By test case
            if metric.test_case:
                if metric.test_case not in errors_by_test_case:
                    errors_by_test_case[metric.test_case] = 0
                errors_by_test_case[metric.test_case] += 1

        lines.append(f"Total Errors: {len(error_metrics)}")
        lines.append("")

        # Errors by type
        lines.append("Error Types:")
        for error_type, messages in errors_by_type.items():
            lines.append(f"  {error_type}: {len(messages)} occurrences")
            for i, message in enumerate(messages[:3]):  # Show first 3 messages
                lines.append(f"    - {message}")
            if len(messages) > 3:
                lines.append(f"    ... and {len(messages) - 3} more")

        # Errors by phase
        if errors_by_phase:
            lines.append("")
            lines.append("Errors by Phase:")
            for phase, count in sorted(errors_by_phase.items(), key=lambda x: x[1], reverse=True):
                lines.append(f"  {phase}: {count} errors")

        # Errors by test case
        if errors_by_test_case:
            lines.append("")
            lines.append("Errors by Test Case:")
            for test_case, count in sorted(
                errors_by_test_case.items(), key=lambda x: x[1], reverse=True
            ):
                lines.append(f"  {test_case}: {count} errors")

        return lines

    def _analyze_resource_metrics(self) -> list[str]:
        """Analyze resource usage metrics."""
        resource_metrics = self.metrics_collector.get_metrics(component="resource_monitor")

        if not resource_metrics:
            return ["No resource monitoring data available."]

        lines = []

        # Calculate resource statistics
        cpu_values = [m.value for m in resource_metrics if m.name == "cpu_percent"]
        memory_values = [m.value for m in resource_metrics if m.name == "memory_percent"]
        memory_used_values = [m.value for m in resource_metrics if m.name == "memory_used_mb"]

        if cpu_values:
            lines.append("CPU Usage:")
            lines.append(f"  Average: {sum(cpu_values) / len(cpu_values):.1f}%")
            lines.append(f"  Peak: {max(cpu_values):.1f}%")
            lines.append(f"  Samples: {len(cpu_values)}")

        if memory_values:
            lines.append("Memory Usage:")
            lines.append(f"  Average: {sum(memory_values) / len(memory_values):.1f}%")
            lines.append(f"  Peak: {max(memory_values):.1f}%")
            lines.append(f"  Samples: {len(memory_values)}")

        if memory_used_values:
            lines.append("Memory Used:")
            lines.append(f"  Average: {sum(memory_used_values) / len(memory_used_values):.0f} MB")
            lines.append(f"  Peak: {max(memory_used_values):.0f} MB")

        # Check for resource alerts
        alerts = []
        if cpu_values and max(cpu_values) > 90:
            alerts.append("HIGH CPU: Peak CPU usage exceeded 90%")
        if memory_values and max(memory_values) > 90:
            alerts.append("HIGH MEMORY: Peak memory usage exceeded 90%")

        if alerts:
            lines.append("")
            lines.append("Resource Alerts:")
            for alert in alerts:
                lines.append(f"  ⚠️  {alert}")

        return lines

    def _analyze_phase_metrics(self) -> list[str]:
        """Analyze metrics by experiment phase."""
        all_metrics = self.metrics_collector.get_metrics()

        if not all_metrics:
            return ["No metrics available for phase analysis."]

        lines = []

        # Group metrics by phase
        metrics_by_phase = {}
        for metric in all_metrics:
            if metric.phase:
                phase_name = metric.phase.value
                if phase_name not in metrics_by_phase:
                    metrics_by_phase[phase_name] = []
                metrics_by_phase[phase_name].append(metric)

        if not metrics_by_phase:
            return ["No phase information available in metrics."]

        # Analyze each phase
        for phase_name in sorted(metrics_by_phase.keys()):
            phase_metrics = metrics_by_phase[phase_name]

            timing_metrics = [m for m in phase_metrics if m.metric_type == MetricType.TIMING]
            error_metrics = [m for m in phase_metrics if m.metric_type == MetricType.ERROR]

            lines.append(f"{phase_name}:")
            lines.append(f"  Total metrics: {len(phase_metrics)}")

            if timing_metrics:
                total_time = sum(m.value for m in timing_metrics)
                lines.append(
                    f"  Timing operations: {len(timing_metrics)} ({total_time:.3f}s total)"
                )

            if error_metrics:
                lines.append(f"  Errors: {len(error_metrics)}")

            lines.append("")

        return lines

    def save_summary_report(self, output_path: Path) -> None:
        """
        Save summary report to file.

        Args:
            output_path: Path where to save the report
        """
        try:
            report = self.generate_summary_report()
            output_path.parent.mkdir(parents=True, exist_ok=True)

            with open(output_path, "w", encoding="utf-8") as f:
                f.write(report)

            self.logger.info("Summary report saved to: %s", output_path)

        except Exception as e:
            self.logger.error("Failed to save summary report: %s", e)

    def save_detailed_report(self, output_path: Path) -> None:
        """
        Save detailed report to file.

        Args:
            output_path: Path where to save the report
        """
        try:
            report = self.generate_detailed_report()
            output_path.parent.mkdir(parents=True, exist_ok=True)

            with open(output_path, "w", encoding="utf-8") as f:
                f.write(report)

            self.logger.info("Detailed report saved to: %s", output_path)

        except Exception as e:
            self.logger.error("Failed to save detailed report: %s", e)

    def get_performance_insights(self) -> dict[str, Any]:
        """
        Generate performance insights and recommendations.

        Returns:
            Dictionary containing performance insights
        """
        insights = {
            "performance_score": "unknown",
            "bottlenecks": [],
            "recommendations": [],
            "alerts": [],
        }

        # Analyze timing patterns
        timing_metrics = self.metrics_collector.get_metrics(metric_type=MetricType.TIMING)
        if timing_metrics:
            operation_times = {}
            for metric in timing_metrics:
                op_name = metric.name.replace("_duration", "")
                if op_name not in operation_times:
                    operation_times[op_name] = []
                operation_times[op_name].append(metric.value)

            # Identify bottlenecks
            for op, times in operation_times.items():
                avg_time = sum(times) / len(times)
                if avg_time > 10:  # More than 10 seconds average
                    insights["bottlenecks"].append(
                        {
                            "operation": op,
                            "average_time": avg_time,
                            "total_time": sum(times),
                            "call_count": len(times),
                        }
                    )

        # Analyze resource usage
        resource_metrics = self.metrics_collector.get_metrics(component="resource_monitor")
        if resource_metrics:
            cpu_values = [m.value for m in resource_metrics if m.name == "cpu_percent"]
            memory_values = [m.value for m in resource_metrics if m.name == "memory_percent"]

            if cpu_values:
                avg_cpu = sum(cpu_values) / len(cpu_values)
                peak_cpu = max(cpu_values)

                if peak_cpu > 95:
                    insights["alerts"].append("Critical: CPU usage reached 95%+")
                    insights["recommendations"].append("Consider reducing CPU-intensive operations")
                elif avg_cpu > 80:
                    insights["alerts"].append("Warning: High average CPU usage")

            if memory_values:
                avg_memory = sum(memory_values) / len(memory_values)
                peak_memory = max(memory_values)

                if peak_memory > 95:
                    insights["alerts"].append("Critical: Memory usage reached 95%+")
                    insights["recommendations"].append("Consider optimizing memory usage")
                elif avg_memory > 80:
                    insights["alerts"].append("Warning: High average memory usage")

        # Calculate overall performance score
        error_count = len(self.metrics_collector.get_metrics(metric_type=MetricType.ERROR))
        stats = self.metrics_collector.get_summary_stats()

        if error_count == 0:
            if len(insights["alerts"]) == 0:
                insights["performance_score"] = "excellent"
            elif len(insights["alerts"]) < 3:
                insights["performance_score"] = "good"
            else:
                insights["performance_score"] = "fair"
        else:
            insights["performance_score"] = "poor"

        return insights
