"""
Metrics Data Loader for CLI commands.

Discovers and loads persisted metrics data from experiment output directories,
providing a clean interface for CLI commands to read real metrics.
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class MetricsDataLoader:
    """Load metrics data from experiment output directories.

    Discovers experiment directories, locates metrics JSON files,
    and provides structured access to metrics data for CLI consumption.
    """

    def __init__(self, output_dir: Path = Path("outputs")):
        self.output_dir = Path(output_dir)

    def find_latest_experiment(self) -> Optional[Path]:
        """Find the most recently modified experiment directory.

        Only considers directories that look like experiment outputs
        (timestamp-named dirs), excluding utility directories like 'metrics/'.

        Returns:
            Path to latest experiment directory, or None if none found.
        """
        if not self.output_dir.exists():
            return None

        experiment_dirs = [
            d for d in self.output_dir.iterdir()
            if d.is_dir() and d.name not in ("metrics", ".cache", "__pycache__")
        ]
        if not experiment_dirs:
            return None

        return max(experiment_dirs, key=lambda d: d.stat().st_mtime)

    def find_experiments_with_metrics(self) -> List[Path]:
        """Find all experiment directories that contain metrics data.

        Returns:
            List of experiment directory paths that have metrics JSON files.
        """
        if not self.output_dir.exists():
            return []

        results = []
        for d in self.output_dir.iterdir():
            if d.is_dir():
                metrics_dir = d / "metrics"
                if metrics_dir.exists() and list(metrics_dir.glob("metrics*.json")):
                    results.append(d)

        return sorted(results, key=lambda d: d.stat().st_mtime, reverse=True)

    def load_metrics(
        self, experiment_dir: Optional[Path] = None
    ) -> Tuple[Optional[Dict[str, Any]], Optional[Path]]:
        """Load metrics data from an experiment directory.

        If no experiment_dir is given, auto-discovers the latest experiment
        with metrics data.

        Args:
            experiment_dir: Specific experiment directory to load from.

        Returns:
            Tuple of (metrics_data_dict, experiment_path) or (None, None).
        """
        if experiment_dir is None:
            experiments = self.find_experiments_with_metrics()
            if not experiments:
                return None, None
            experiment_dir = experiments[0]

        metrics_file = experiment_dir / "metrics" / "metrics.json"
        if not metrics_file.exists():
            return None, experiment_dir

        try:
            with open(metrics_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data, experiment_dir
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Failed to load metrics from %s: %s", metrics_file, e)
            return None, experiment_dir

    # -- get_available_metrics and helpers --

    def get_available_metrics(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract available metric names/types/counts from loaded data.

        Args:
            data: Loaded metrics JSON data.

        Returns:
            List of dicts with keys: name, category, count.
        """
        results: List[Dict[str, Any]] = []
        results.extend(self._extract_timing_metrics(data))
        results.extend(self._extract_resource_metrics(data))
        results.extend(self._extract_phase_metrics(data))
        results.extend(self._extract_error_metrics(data))
        results.extend(self._extract_raw_metrics(data))
        return results

    @staticmethod
    def _extract_timing_metrics(data: Dict[str, Any]) -> List[Dict[str, Any]]:
        timing = data.get("timing_metrics", {})
        return [{"name": name, "category": "timing", "count": 1} for name in timing]

    @staticmethod
    def _extract_resource_metrics(data: Dict[str, Any]) -> List[Dict[str, Any]]:
        results = []
        resource = data.get("resource_metrics", {})
        if isinstance(resource, dict):
            for section_name in ("cpu_usage", "memory_usage"):
                section = resource.get(section_name)
                if section and isinstance(section, dict):
                    results.append(
                        {
                            "name": section_name,
                            "category": "resource",
                            "count": resource.get("samples_count", 0),
                        }
                    )
        return results

    @staticmethod
    def _extract_phase_metrics(data: Dict[str, Any]) -> List[Dict[str, Any]]:
        results = []
        phases = data.get("phase_metrics", {})
        for phase_name, phase_data in phases.items():
            count = phase_data.get("count", 0) if isinstance(phase_data, dict) else 0
            if count > 0:
                results.append(
                    {"name": phase_name, "category": "phase", "count": count}
                )
        return results

    @staticmethod
    def _extract_error_metrics(data: Dict[str, Any]) -> List[Dict[str, Any]]:
        errors = data.get("error_metrics", {})
        total_errors = errors.get("total_errors", 0) if isinstance(errors, dict) else 0
        if total_errors > 0:
            return [{"name": "errors", "category": "error", "count": total_errors}]
        return []

    @staticmethod
    def _extract_raw_metrics(data: Dict[str, Any]) -> List[Dict[str, Any]]:
        results = []
        raw = data.get("raw_metrics", {})
        if isinstance(raw, dict):
            for section_key in ("counters", "gauges", "histograms"):
                section = raw.get(section_key, {})
                if isinstance(section, dict):
                    for name, value in section.items():
                        count = (
                            len(value)
                            if isinstance(value, list)
                            else (0 if value is None else 1)
                        )
                        results.append(
                            {"name": name, "category": section_key, "count": count}
                        )
        return results

    # -- get_metric_values and helpers --

    def get_metric_values(
        self, data: Dict[str, Any], name: str, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Get time-series values for a specific metric.

        Args:
            data: Loaded metrics JSON data.
            name: Metric name to look up.
            limit: Max number of values to return.

        Returns:
            List of dicts with keys: timestamp, value (and optionally others).
        """
        results: List[Dict[str, Any]] = []
        results.extend(self._search_timing(data, name))
        results.extend(self._search_resource(data, name))
        results.extend(self._search_phases(data, name))
        results.extend(self._search_errors(data, name))
        results.extend(self._search_raw_sections(data, name, limit))
        results.extend(self._search_raw_resource_list(data, name, limit))
        results.extend(self._search_raw_errors_list(data, name, limit))
        return results[:limit]

    @staticmethod
    def _search_timing(data: Dict[str, Any], name: str) -> List[Dict[str, Any]]:
        timing = data.get("timing_metrics", {})
        if name in timing:
            return [{"name": name, "value": timing[name], "type": "timing"}]
        return []

    @staticmethod
    def _search_resource(data: Dict[str, Any], name: str) -> List[Dict[str, Any]]:
        results = []
        resource = data.get("resource_metrics", {})
        if isinstance(resource, dict) and name in resource:
            section = resource[name]
            if isinstance(section, dict):
                for stat_name, stat_value in section.items():
                    results.append(
                        {
                            "name": f"{name}.{stat_name}",
                            "value": stat_value,
                            "type": "resource",
                        }
                    )
        return results

    @staticmethod
    def _search_phases(data: Dict[str, Any], name: str) -> List[Dict[str, Any]]:
        results = []
        phase = data.get("phase_metrics", {})
        if isinstance(phase, dict):
            for phase_name, phase_data in phase.items():
                if isinstance(phase_data, dict) and name.lower() in phase_name.lower():
                    results.append({
                        "name": phase_name,
                        "timestamp": None,
                        "value": phase_data,
                        "type": "phase",
                    })
        return results

    @staticmethod
    def _search_errors(data: Dict[str, Any], name: str) -> List[Dict[str, Any]]:
        errors = data.get("error_metrics", {})
        if isinstance(errors, dict) and name.lower() in ("errors", "error"):
            error_summary = {k: v for k, v in errors.items() if not isinstance(v, (dict, list))}
            if error_summary:
                return [{
                    "name": "error_summary",
                    "timestamp": None,
                    "value": error_summary,
                    "type": "error",
                }]
        return []

    @staticmethod
    def _search_raw_sections(
        data: Dict[str, Any], name: str, limit: int
    ) -> List[Dict[str, Any]]:
        results = []
        raw = data.get("raw_metrics", {})
        if not isinstance(raw, dict):
            return results
        for section_key in ("counters", "gauges", "histograms"):
            section = raw.get(section_key, {})
            if isinstance(section, dict) and name in section:
                val = section[name]
                if isinstance(val, list):
                    for item in val[:limit]:
                        results.append(
                            {"name": name, "value": item, "type": section_key}
                        )
                else:
                    results.append(
                        {"name": name, "value": val, "type": section_key}
                    )
        return results

    @staticmethod
    def _search_raw_resource_list(
        data: Dict[str, Any], name: str, limit: int
    ) -> List[Dict[str, Any]]:
        results = []
        raw = data.get("raw_metrics", {})
        if not isinstance(raw, dict):
            return results
        resource_list = raw.get("resource_metrics", [])
        if isinstance(resource_list, list):
            matching = [r for r in resource_list if r.get("name") == name]
            for item in matching[:limit]:
                results.append(
                    {
                        "name": name,
                        "value": item.get("value"),
                        "timestamp": item.get("timestamp"),
                        "type": "resource",
                    }
                )
        return results

    @staticmethod
    def _search_raw_errors_list(
        data: Dict[str, Any], name: str, limit: int
    ) -> List[Dict[str, Any]]:
        results = []
        raw = data.get("raw_metrics", {})
        if not isinstance(raw, dict):
            return results
        errors_list = raw.get("errors", [])
        if isinstance(errors_list, list) and name in ("errors", "error_occurred"):
            for item in errors_list[:limit]:
                results.append(
                    {
                        "name": "error",
                        "value": item.get("metadata", {}).get(
                            "error_message", "unknown"
                        ),
                        "timestamp": item.get("timestamp"),
                        "type": "error",
                    }
                )
        return results

    # -- get_summary and helpers --

    def get_summary(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Get summary statistics from loaded metrics data.

        Args:
            data: Loaded metrics JSON data.

        Returns:
            Summary dict with export_metadata, timing stats, resource stats, errors.
        """
        summary: Dict[str, Any] = {}
        summary.update(self._summarize_export_metadata(data))
        summary.update(self._summarize_overview(data))
        summary.update(self._summarize_timing(data))
        summary.update(self._summarize_resources(data))
        summary.update(self._summarize_errors(data))
        return summary

    @staticmethod
    def _summarize_export_metadata(data: Dict[str, Any]) -> Dict[str, Any]:
        export_meta = data.get("export_metadata", {})
        if export_meta:
            return {
                "export_timestamp": export_meta.get("timestamp", "unknown"),
                "export_format": export_meta.get("export_format", "unknown"),
            }
        return {}

    @staticmethod
    def _summarize_overview(data: Dict[str, Any]) -> Dict[str, Any]:
        summary: Dict[str, Any] = {}
        data_summary = data.get("summary", {})
        if data_summary:
            summary["total_experiments"] = data_summary.get("total_experiments", 0)
            summary["successful_experiments"] = data_summary.get(
                "successful_experiments", 0
            )
            summary["failed_experiments"] = data_summary.get("failed_experiments", 0)
            summary["total_test_cases"] = data_summary.get("total_test_cases", 0)
            summary["error_count"] = data_summary.get("error_count", 0)
            total_time = data_summary.get("total_execution_time")
            if total_time is not None:
                summary["total_execution_time"] = f"{total_time:.2f}s"
        return summary

    @staticmethod
    def _summarize_timing(data: Dict[str, Any]) -> Dict[str, Any]:
        timing = data.get("timing_metrics", {})
        if timing:
            values = [v for v in timing.values() if isinstance(v, (int, float))]
            if values:
                return {
                    "timing_metric_count": len(values),
                    "total_timing": f"{sum(values):.2f}s",
                }
        return {}

    @staticmethod
    def _summarize_resources(data: Dict[str, Any]) -> Dict[str, Any]:
        summary: Dict[str, Any] = {}
        resource = data.get("resource_metrics", {})
        if isinstance(resource, dict):
            cpu = resource.get("cpu_usage", {})
            mem = resource.get("memory_usage", {})
            if isinstance(cpu, dict) and cpu.get("average") is not None:
                summary["avg_cpu"] = f"{cpu['average']:.1f}%"
                summary["peak_cpu"] = f"{cpu.get('peak', 0):.1f}%"
            if isinstance(mem, dict) and mem.get("average") is not None:
                summary["avg_memory"] = f"{mem['average']:.1f}%"
                summary["peak_memory"] = f"{mem.get('peak', 0):.1f}%"
            summary["resource_samples"] = resource.get("samples_count", 0)
        return summary

    @staticmethod
    def _summarize_errors(data: Dict[str, Any]) -> Dict[str, Any]:
        summary: Dict[str, Any] = {}
        errors = data.get("error_metrics", {})
        if isinstance(errors, dict):
            summary["total_errors"] = errors.get("total_errors", 0)
            categories = errors.get("error_categories", {})
            if categories:
                summary["error_categories"] = categories
        return summary
