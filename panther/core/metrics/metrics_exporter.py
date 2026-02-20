from typing import Any, Dict, List, Union

"""
Metrics Exporter Module for PANTHER

This module provides functionality to export metrics data to various formats
including JSON, CSV, and dashboard-compatible formats.
"""

import csv
import json
import logging
import time
from datetime import datetime
from pathlib import Path

from .metrics_collector import MetricsCollector, MetricType, Phase

logger = logging.getLogger(__name__)


class MetricsExporter:
    """

    Handles exporting metrics data to various formats and destinations.
    """

    def __init__(self, metrics_collector: MetricsCollector):
        """
        Initialize the metrics exporter.

        Args:
            metrics_collector: The metrics collector instance to export from
        """
        self.metrics_collector = metrics_collector
        self.export_timestamp = datetime.now()

    def export_to_json(
        self, output_path: Union[str, Path], include_raw_data: bool = True
    ) -> bool:
        """
        Export metrics to JSON format.

        Args:
            output_path: Path to save the JSON file
            include_raw_data: Whether to include raw metric data points

        Returns:
            bool: True if export was successful, False otherwise
        """
        try:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            export_data = {
                "export_metadata": {
                    "timestamp": self.export_timestamp.isoformat(),
                    "panther_version": self._get_panther_version(),
                    "export_format": "json",
                    "include_raw_data": include_raw_data,
                },
                "summary": self._get_summary_data(),
                "timing_metrics": self._get_timing_metrics(),
                "resource_metrics": self._get_resource_metrics(),
                "phase_metrics": self._get_phase_metrics(),
                "error_metrics": self._get_error_metrics(),
                "artifact_metrics": self._get_artifact_metrics(),
            }

            if include_raw_data:
                export_data["raw_metrics"] = self._get_raw_metrics()

            # Define a custom JSON serializer for enums and other complex objects
            def json_serializer(obj):
                if hasattr(obj, "value"):  # Handle enums
                    return obj.value
                elif hasattr(obj, "__dict__"):  # Handle objects with dictionaries
                    return obj.__dict__
                else:
                    return str(obj)

            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(export_data, f, indent=2, default=json_serializer)

            logger.info("Metrics exported to JSON: %s", output_path)
            return True

        except Exception as e:
            logger.error("Failed to export metrics to JSON: %s", e)
            return False

    def export_to_csv(self, output_dir: Union[str, Path]) -> bool:
        """
        Export metrics to CSV format (multiple files for different metric types).

        Args:
            output_dir: Directory to save CSV files

        Returns:
            bool: True if export was successful, False otherwise
        """
        try:
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)

            timestamp_str = self.export_timestamp.strftime("%Y%m%d_%H%M%S")

            # Export timing metrics
            self._export_timing_csv(output_dir / f"timing_metrics_{timestamp_str}.csv")

            # Export resource metrics
            self._export_resource_csv(
                output_dir / f"resource_metrics_{timestamp_str}.csv"
            )

            # Export error metrics
            self._export_error_csv(output_dir / f"error_metrics_{timestamp_str}.csv")

            # Export summary metrics
            self._export_summary_csv(
                output_dir / f"summary_metrics_{timestamp_str}.csv"
            )

            logger.info("Metrics exported to CSV files in: %s", output_dir)
            return True

        except Exception as e:
            logger.error("Failed to export metrics to CSV: %s", e)
            return False

    def export_prometheus_format(self, output_path: Union[str, Path]) -> bool:
        """
        Export metrics in Prometheus format for monitoring systems.

        Args:
            output_path: Path to save the Prometheus format file

        Returns:
            bool: True if export was successful, False otherwise
        """
        try:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            prometheus_data = []

            # Add timing metrics
            for metric_name, value in self.metrics_collector.timing_metrics.items():
                safe_name = metric_name.replace(" ", "_").replace("-", "_").lower()
                prometheus_data.append(f"panther_timing_{safe_name}_seconds {value}")

            # Add counters
            for metric_name, value in self.metrics_collector.counters.items():
                safe_name = metric_name.replace(" ", "_").replace("-", "_").lower()
                prometheus_data.append(f"panther_counter_{safe_name}_total {value}")

            # Add gauges
            for metric_name, value in self.metrics_collector.gauges.items():
                safe_name = metric_name.replace(" ", "_").replace("-", "_").lower()
                prometheus_data.append(f"panther_gauge_{safe_name} {value}")

            # Add resource metrics (latest values)
            resource_metrics = self.metrics_collector.get_metrics(
                component="resource_monitor"
            )
            cpu_metrics = [m for m in resource_metrics if m.name == "cpu_percent"]
            memory_metrics = [m for m in resource_metrics if m.name == "memory_percent"]
            disk_read_metrics = [
                m for m in resource_metrics if m.name == "disk_read_mb_total"
            ]
            disk_write_metrics = [
                m for m in resource_metrics if m.name == "disk_write_mb_total"
            ]

            # Get latest values if available
            if cpu_metrics:
                latest_cpu = max(cpu_metrics, key=lambda x: x.timestamp)
                prometheus_data.append(f"panther_cpu_usage_percent {latest_cpu.value}")

            if memory_metrics:
                latest_memory = max(memory_metrics, key=lambda x: x.timestamp)
                prometheus_data.append(
                    f"panther_memory_usage_percent {latest_memory.value}"
                )

            if disk_read_metrics:
                latest_disk_read = max(disk_read_metrics, key=lambda x: x.timestamp)
                prometheus_data.append(
                    f"panther_disk_io_mb_read {latest_disk_read.value}"
                )

            if disk_write_metrics:
                latest_disk_write = max(disk_write_metrics, key=lambda x: x.timestamp)
                prometheus_data.append(
                    f"panther_disk_io_mb_write {latest_disk_write.value}"
                )

            with open(output_path, "w", encoding="utf-8") as f:
                f.write("\n".join(prometheus_data))
                f.write("\n")

            logger.info("Metrics exported to Prometheus format: %s", output_path)
            return True

        except Exception as e:
            logger.error("Failed to export metrics to Prometheus format: %s", e)
            return False

    def export_dashboard_json(self, output_path: Union[str, Path]) -> bool:
        """
        Export metrics in a format optimized for dashboard consumption.

        Args:
            output_path: Path to save the dashboard JSON file

        Returns:
            bool: True if export was successful, False otherwise
        """
        try:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            dashboard_data = {
                "dashboard_metadata": {
                    "timestamp": self.export_timestamp.isoformat(),
                    "refresh_interval": 30,  # seconds
                    "data_retention": "24h",
                },
                "summary_cards": self._get_dashboard_summary(),
                "time_series": self._get_dashboard_timeseries(),
                "charts": self._get_dashboard_charts(),
                "alerts": self._get_dashboard_alerts(),
            }

            # Define a custom JSON serializer for enums and other complex objects
            def json_serializer(obj):
                if hasattr(obj, "value"):  # Handle enums
                    return obj.value
                elif hasattr(obj, "__dict__"):  # Handle objects with dictionaries
                    return obj.__dict__
                else:
                    return str(obj)

            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(dashboard_data, f, indent=2, default=json_serializer)

            logger.info("Dashboard metrics exported: %s", output_path)
            return True

        except Exception as e:
            logger.error("Failed to export dashboard metrics: %s", e)
            return False

    def prepare_metrics_data(self) -> bool:
        """
        Prepare metrics data for export by performing any necessary preprocessing.

        Returns:
            bool: True if preparation was successful, False otherwise
        """
        try:
            # Perform any necessary data validation and formatting
            metrics = self.metrics_collector.get_metrics()

            if not metrics:
                logger.warning("No metrics data available for export")
                return True  # Still considered successful

            # Basic validation
            for metric in metrics:
                if not hasattr(metric, "name") or not hasattr(metric, "value"):
                    logger.warning("Invalid metric found: %s", metric)
                    continue

            logger.info("Prepared %s metrics for export", len(metrics))
            return True

        except Exception as e:
            logger.error("Failed to prepare metrics data: %s", e)
            return False

    def format_resource_metrics(self) -> bool:
        """
        Format resource metrics to ensure they're serializable.

        Returns:
            bool: True if formatting was successful, False otherwise
        """
        try:
            resource_metrics = self.metrics_collector.get_metrics(
                metric_type=MetricType.RESOURCE
            )

            for metric in resource_metrics:
                # Ensure values are JSON serializable
                if hasattr(metric, "value") and metric.value is not None:
                    try:
                        json.dumps(metric.value)
                    except (TypeError, ValueError):
                        # Convert non-serializable values to strings
                        metric.value = str(metric.value)

            logger.debug("Formatted %s resource metrics", len(resource_metrics))
            return True

        except Exception as e:
            logger.error("Failed to format resource metrics: %s", e)
            return False

    def prepare_dashboard_metrics(self) -> bool:
        """
        Prepare metrics data specifically for dashboard export format.

        Returns:
            bool: True if preparation was successful, False otherwise
        """
        try:
            # Get all metrics and organize them for dashboard display
            all_metrics = self.metrics_collector.get_metrics()

            if not all_metrics:
                logger.warning("No metrics available for dashboard preparation")
                return True

            # Group metrics by component and phase for dashboard visualization
            dashboard_data = {
                "summary": self._get_dashboard_summary(),
                "timeseries": self._get_dashboard_timeseries(),
                "charts": self._get_dashboard_charts(),
            }

            # Store prepared dashboard data for export
            self._dashboard_data = dashboard_data

            logger.info("Prepared dashboard data with %s metrics", len(all_metrics))
            return True

        except Exception as e:
            logger.error("Failed to prepare dashboard metrics: %s", e)
            return False

    @staticmethod
    def _get_panther_version() -> str:
        """Get PANTHER version dynamically from package metadata."""
        try:
            from panther import __version__
            return __version__
        except Exception:
            return "unknown"

    def _get_summary_data(self) -> Dict[str, Any]:
        """Get summary metrics data."""
        return {
            "total_experiments": self.metrics_collector.get_counter(
                "experiments_total"
            ),
            "successful_experiments": self.metrics_collector.get_counter(
                "experiments_successful"
            ),
            "failed_experiments": self.metrics_collector.get_counter(
                "experiments_failed"
            ),
            "total_test_cases": self.metrics_collector.get_counter("test_cases_total"),
            "successful_test_cases": self.metrics_collector.get_counter(
                "test_cases_successful"
            ),
            "failed_test_cases": self.metrics_collector.get_counter(
                "test_cases_failed"
            ),
            "total_execution_time": self.metrics_collector.get_timing_metric(
                "total_execution_time"
            ),
            "average_test_duration": self._calculate_average_test_duration(),
            "error_count": len(self.metrics_collector.errors),
        }

    def _get_timing_metrics(self) -> Dict[str, float]:
        """Get all timing metrics."""
        return dict(self.metrics_collector.timing_metrics)

    def _get_resource_metrics(self) -> Dict[str, Any]:
        """Get resource usage metrics."""
        try:
            resource_metrics = self.metrics_collector.get_metrics(
                component="resource_monitor"
            )
            if not resource_metrics:
                return {}

            # Filter metrics by type with error handling
            cpu_metrics = []
            memory_metrics = []

            for m in resource_metrics:
                try:
                    if hasattr(m, "name"):
                        if m.name == "cpu_percent":
                            cpu_metrics.append(m)
                        elif m.name == "memory_percent":
                            memory_metrics.append(m)
                except Exception:
                    # Skip problematic metrics
                    continue

            # Extract values with error handling
            cpu_values = []
            memory_values = []

            for m in cpu_metrics:
                try:
                    if hasattr(m, "value"):
                        cpu_values.append(m.value)
                except Exception:
                    continue

            for m in memory_metrics:
                try:
                    if hasattr(m, "value"):
                        memory_values.append(m.value)
                except Exception:
                    continue

            # Calculate statistics safely
            cpu_avg = sum(cpu_values) / len(cpu_values) if cpu_values else 0
            cpu_peak = max(cpu_values) if cpu_values else 0
            cpu_min = min(cpu_values) if cpu_values else 0

            mem_avg = sum(memory_values) / len(memory_values) if memory_values else 0
            mem_peak = max(memory_values) if memory_values else 0
            mem_min = min(memory_values) if memory_values else 0

            return {
                "cpu_usage": {"average": cpu_avg, "peak": cpu_peak, "min": cpu_min},
                "memory_usage": {"average": mem_avg, "peak": mem_peak, "min": mem_min},
                "samples_count": len(resource_metrics),
            }

        except Exception as e:
            logger.error("Error generating resource metrics summary: %s", e)
            return {
                "cpu_usage": {"average": 0, "peak": 0, "min": 0},
                "memory_usage": {"average": 0, "peak": 0, "min": 0},
                "samples_count": 0,
                "error": str(e),
            }

    def _get_phase_metrics(self) -> Dict[str, Dict[str, Any]]:
        """Get metrics broken down by execution phase."""
        phase_data = {}

        for phase in Phase:
            phase_key = phase.value
            phase_data[phase_key] = {
                "total_time": 0,
                "count": 0,
                "errors": 0,
                "success_rate": 0,
            }

        # Aggregate phase-specific metrics using the .phase field on each metric
        for metric in self.metrics_collector.metrics:
            if metric.metric_type == MetricType.TIMING and metric.phase is not None:
                phase_key = metric.phase.value
                if phase_key in phase_data:
                    phase_data[phase_key]["total_time"] += metric.value
                    phase_data[phase_key]["count"] += 1

        # Calculate success rates
        for phase_key in phase_data:
            if phase_data[phase_key]["count"] > 0:
                error_count = sum(
                    1
                    for error in self.metrics_collector.errors
                    if error.phase and phase_key.lower() in error.phase.value.lower()
                )
                phase_data[phase_key]["errors"] = error_count
                success_count = phase_data[phase_key]["count"] - error_count
                phase_data[phase_key]["success_rate"] = (
                    success_count / phase_data[phase_key]["count"]
                )

        return phase_data

    def _get_error_metrics(self) -> Dict[str, Any]:
        """Get error analysis metrics."""
        if not self.metrics_collector.errors:
            return {"total_errors": 0, "error_categories": {}, "error_timeline": []}

        error_categories = {}
        for error in self.metrics_collector.errors:
            try:
                # Use error_type from metadata, with robust attribute checking
                if hasattr(error, "metadata"):
                    category = error.metadata.get("error_type", "unknown")
                else:
                    category = "unknown"

                if category not in error_categories:
                    error_categories[category] = 0
                error_categories[category] += 1
            except Exception as e:
                logger.debug("Error processing error category: %s", e)
                # Add to 'unknown' category
                if "unknown" not in error_categories:
                    error_categories["unknown"] = 0
                error_categories["unknown"] += 1

        # Convert error metrics to serializable dictionaries
        error_timeline = []
        for error in self.metrics_collector.errors:
            try:
                error_dict = {
                    "timestamp": (
                        error.timestamp if hasattr(error, "timestamp") else time.time()
                    ),
                    "phase": (
                        error.phase.value
                        if hasattr(error, "phase")
                        and error.phase
                        and hasattr(error.phase, "value")
                        else None
                    ),
                    "component": (
                        error.component if hasattr(error, "component") else None
                    ),
                    "test_case": (
                        error.test_case if hasattr(error, "test_case") else None
                    ),
                    "error_type": (
                        error.metadata.get("error_type", "unknown")
                        if hasattr(error, "metadata")
                        else "unknown"
                    ),
                    "error_message": (
                        error.metadata.get("error_message", "No message")
                        if hasattr(error, "metadata")
                        else "No message"
                    ),
                }
                error_timeline.append(error_dict)
            except Exception as e:
                logger.debug("Error processing error timeline item: %s", e)
                # Add a placeholder error entry
                error_timeline.append(
                    {
                        "timestamp": time.time(),
                        "phase": None,
                        "component": None,
                        "test_case": None,
                        "error_type": "serialization_error",
                        "error_message": f"Error processing metric: {str(e)}",
                    }
                )

        return {
            "total_errors": len(self.metrics_collector.errors),
            "error_categories": error_categories,
            "error_timeline": error_timeline,
        }

    def _get_artifact_metrics(self) -> Dict[str, Any]:
        """Get artifact size and count metrics."""
        return {
            "total_artifacts": self.metrics_collector.get_counter("artifacts_total"),
            "logs_generated": self.metrics_collector.get_counter("logs_generated"),
            "reports_generated": self.metrics_collector.get_counter(
                "reports_generated"
            ),
            "total_artifact_size_mb": self.metrics_collector.get_gauge(
                "total_artifact_size_mb"
            ),
        }

    def _get_raw_metrics(self) -> Dict[str, Any]:
        """Get all raw metric data."""
        # Convert Metric objects to dictionaries for JSON serialization
        metrics_as_dicts = []
        for metric in self.metrics_collector.metrics:
            try:
                # Handle different types of metric_type
                if hasattr(metric, "metric_type"):
                    if hasattr(metric.metric_type, "value"):
                        metric_type = metric.metric_type.value
                    elif isinstance(metric.metric_type, str):
                        metric_type = metric.metric_type
                    else:
                        metric_type = str(metric.metric_type)
                else:
                    metric_type = "unknown"

                # Handle different types of phase
                if hasattr(metric, "phase") and metric.phase:
                    if hasattr(metric.phase, "value"):
                        phase = metric.phase.value
                    elif isinstance(metric.phase, str):
                        phase = metric.phase
                    else:
                        phase = str(metric.phase)
                else:
                    phase = None

                metric_dict = {
                    "name": metric.name if hasattr(metric, "name") else "unknown",
                    "metric_type": metric_type,
                    "value": metric.value if hasattr(metric, "value") else None,
                    "timestamp": (
                        metric.timestamp
                        if hasattr(metric, "timestamp")
                        else time.time()
                    ),
                    "phase": phase,
                    "test_case": (
                        metric.test_case if hasattr(metric, "test_case") else None
                    ),
                    "component": (
                        metric.component if hasattr(metric, "component") else None
                    ),
                    "labels": (
                        dict(metric.labels)
                        if hasattr(metric, "labels") and metric.labels
                        else {}
                    ),
                    "metadata": (
                        dict(metric.metadata)
                        if hasattr(metric, "metadata") and metric.metadata
                        else {}
                    ),
                }
                metrics_as_dicts.append(metric_dict)
            except Exception as e:
                # Log and skip problematic metrics instead of crashing
                logger.error("Error processing metric for serialization: %s", e)
                continue

        # Process resource metrics for serialization
        resource_metrics = []
        try:
            # Safely get resource metrics
            resource_monitor_metrics = []
            try:
                resource_monitor_metrics = self.metrics_collector.get_metrics(
                    component="resource_monitor"
                )
            except Exception as e:
                logger.error("Failed to get resource monitor metrics: %s", e)

            for metric in resource_monitor_metrics:
                try:
                    # Get metric name safely
                    name = "unknown"
                    if hasattr(metric, "name"):
                        name = str(metric.name)

                    # Handle value specially to avoid 'str' object has no attribute 'value' error
                    value = None
                    if hasattr(metric, "value"):
                        if (
                            isinstance(metric.value, (int, float, bool))
                            or metric.value is None
                        ):
                            value = metric.value
                        else:
                            # For string or other object types, just use string representation
                            try:
                                # Try to convert to float if it's a numeric string
                                value = float(metric.value)
                            except (ValueError, TypeError):
                                value = str(metric.value)

                    # Get timestamp safely
                    timestamp = time.time()
                    if hasattr(metric, "timestamp") and metric.timestamp is not None:
                        if isinstance(metric.timestamp, (int, float)):
                            timestamp = metric.timestamp
                        else:
                            try:
                                timestamp = float(metric.timestamp)
                            except (ValueError, TypeError):
                                pass

                    # Get component safely
                    component = "resource_monitor"
                    if hasattr(metric, "component") and metric.component is not None:
                        component = str(metric.component)

                    resource_dict = {
                        "name": name,
                        "value": value,
                        "timestamp": timestamp,
                        "component": component,
                    }
                    resource_metrics.append(resource_dict)
                except Exception as e:
                    # Log and skip problematic resource metrics
                    logger.error("Error processing resource metric: %s", e)
                    continue
        except Exception as e:
            logger.error("Failed to process resource metrics section: %s", e)

        # Prepare the final metrics dictionary with robust error handling
        result = {}

        try:
            # Get timing metrics safely
            if hasattr(self.metrics_collector, "timing_metrics"):
                try:
                    result["timing_metrics"] = dict(
                        self.metrics_collector.timing_metrics
                    )
                except Exception as e:
                    logger.error("Error converting timing metrics: %s", e)
                    result["timing_metrics"] = {}
            else:
                result["timing_metrics"] = {}

            # Get counters safely
            if hasattr(self.metrics_collector, "counters"):
                try:
                    result["counters"] = dict(self.metrics_collector.counters)
                except Exception as e:
                    logger.error("Error converting counters: %s", e)
                    result["counters"] = {}
            else:
                result["counters"] = {}

            # Get gauges safely
            if hasattr(self.metrics_collector, "gauges"):
                try:
                    result["gauges"] = dict(self.metrics_collector.gauges)
                except Exception as e:
                    logger.error("Error converting gauges: %s", e)
                    result["gauges"] = {}
            else:
                result["gauges"] = {}

            # Get histograms safely
            result["histograms"] = {}
            if hasattr(self.metrics_collector, "histograms"):
                try:
                    result["histograms"] = self.metrics_collector.histograms
                except Exception as e:
                    logger.error("Error accessing histograms: %s", e)

            # Add resource metrics
            result["resource_metrics"] = resource_metrics

            # Filter error metrics safely
            try:
                result["errors"] = [
                    m for m in metrics_as_dicts if m.get("metric_type") == "error"
                ]
            except Exception as e:
                logger.error("Error filtering error metrics: %s", e)
                result["errors"] = []

        except Exception as e:
            logger.error("Error assembling raw metrics result: %s", e)

        return result

    def _calculate_average_test_duration(self) -> float:
        """Calculate average test case duration."""
        test_durations = []
        for metric_name, value in self.metrics_collector.timing_metrics.items():
            if "test_case" in metric_name.lower() and "duration" in metric_name.lower():
                test_durations.append(value)

        return sum(test_durations) / len(test_durations) if test_durations else 0

    def _export_timing_csv(self, output_path: Path) -> None:
        """Export timing metrics to CSV."""
        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Metric Name", "Duration (seconds)", "Type"])

            for metric_name, value in self.metrics_collector.timing_metrics.items():
                writer.writerow([metric_name, value, "timing"])

    def _export_resource_csv(self, output_path: Path) -> None:
        """Export resource metrics to CSV."""
        resource_metrics = self.metrics_collector.get_metrics(
            component="resource_monitor"
        )
        if not resource_metrics:
            return

        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)

            # Define standard columns for resource metrics
            headers = ["timestamp", "name", "value", "phase", "component"]
            writer.writerow(headers)

            for metric in resource_metrics:
                row = [
                    metric.timestamp,
                    metric.name,
                    metric.value,
                    metric.phase.value if metric.phase else "",
                    metric.component or "",
                ]
                writer.writerow(row)

    def _export_error_csv(self, output_path: Path) -> None:
        """Export error metrics to CSV."""
        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(
                ["Timestamp", "Phase", "Error Type", "Error Message", "Component"]
            )

            for error in self.metrics_collector.errors:
                writer.writerow(
                    [
                        error.timestamp,
                        error.phase.value if error.phase else "",
                        error.metadata.get("error_type", "unknown"),
                        error.metadata.get("error_message", ""),
                        error.component or "",
                    ]
                )

    def _export_summary_csv(self, output_path: Path) -> None:
        """Export summary metrics to CSV."""
        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Metric", "Value", "Type"])

            try:
                summary = self._get_summary_data()
                for key, value in summary.items():
                    writer.writerow([key, str(value), "summary"])
            except Exception as e:
                logger.error("Error exporting summary CSV: %s", e)
                # Write a placeholder if we can't get the real data
                writer.writerow(["error", "Failed to get summary data", "error"])

    def _get_dashboard_summary(self) -> List[Dict[str, Any]]:
        """Get summary cards for dashboard."""
        summary = self._get_summary_data()

        return [
            {
                "title": "Total Experiments",
                "value": summary["total_experiments"],
                "type": "counter",
                "color": "blue",
            },
            {
                "title": "Success Rate",
                "value": f"{(summary['successful_experiments'] / max(summary['total_experiments'], 1)) * 100:.1f}%",
                "type": "percentage",
                "color": (
                    "green"
                    if summary["successful_experiments"] > summary["failed_experiments"]
                    else "red"
                ),
            },
            {
                "title": "Total Execution Time",
                "value": f"{summary['total_execution_time']:.2f}s",
                "type": "duration",
                "color": "purple",
            },
            {
                "title": "Error Count",
                "value": summary["error_count"],
                "type": "counter",
                "color": "red" if summary["error_count"] > 0 else "green",
            },
        ]

    def _get_dashboard_timeseries(self) -> Dict[str, List[Dict[str, Any]]]:
        """Get time series data for dashboard charts."""
        resource_metrics = self.metrics_collector.get_metrics(
            component="resource_monitor"
        )

        # Group metrics by timestamp
        metrics_by_timestamp = {}
        for metric in resource_metrics:
            # Round timestamp to nearest second to group related metrics
            rounded_ts = round(metric.timestamp)
            if rounded_ts not in metrics_by_timestamp:
                metrics_by_timestamp[rounded_ts] = {"timestamp": rounded_ts}

            # Add metric value to the appropriate timestamp group
            metrics_by_timestamp[rounded_ts][metric.name] = metric.value

        # Convert to sorted list
        timeseries = sorted(metrics_by_timestamp.values(), key=lambda x: x["timestamp"])

        return {"resource_usage": timeseries}

    def _get_dashboard_charts(self) -> List[Dict[str, Any]]:
        """Get chart configurations for dashboard."""
        return [
            {
                "id": "resource_usage_chart",
                "type": "line",
                "title": "Resource Usage Over Time",
                "data_source": "resource_usage",
                "x_axis": "timestamp",
                "y_axes": ["cpu_percent", "memory_percent"],
            },
            {
                "id": "phase_duration_chart",
                "type": "bar",
                "title": "Average Duration by Phase",
                "data": self._get_phase_metrics(),
            },
        ]

    def _get_dashboard_alerts(self) -> List[Dict[str, Any]]:
        """Get alerts for dashboard."""
        alerts = []

        # High error rate alert
        summary = self._get_summary_data()
        if summary["total_experiments"] > 0:
            error_rate = summary["failed_experiments"] / summary["total_experiments"]
            if error_rate > 0.2:  # 20% failure rate
                alerts.append(
                    {
                        "level": "warning",
                        "message": f"High failure rate: {error_rate:.1%}",
                        "timestamp": self.export_timestamp.isoformat(),
                    }
                )

        # Resource usage alerts
        resource_metrics = self._get_resource_metrics()
        cpu_usage = resource_metrics.get("cpu_usage", {})
        if cpu_usage and cpu_usage.get("peak", 0) > 90:
            alerts.append(
                {
                    "level": "warning",
                    "message": f"High CPU usage detected: {cpu_usage['peak']:.1f}%",
                    "timestamp": self.export_timestamp.isoformat(),
                }
            )

        return alerts
