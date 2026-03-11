"""AnalyticsMixin — summary, metrics, and aggregation for ResultsService.

Provides methods for computing experiment summaries (via StatusCollector),
parsing metrics files into chart-ready time-series, and extracting
aggregate pass/fail statistics.
"""

import json
import logging
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


class AnalyticsMixin:
    """Mixin providing analytics and metrics methods for ResultsService."""

    def get_experiment_summary(self, experiment_path: str) -> Optional[dict]:
        """Compute or retrieve a cached experiment summary via StatusCollector.

        Delegates to ``StatusCollector`` (PANTHER's core reporting
        aggregator that walks an experiment's output tree and builds an
        ``ExperimentSummary`` dataclass).  The resulting dict is cached
        in memory so that repeated calls for the same experiment path do
        not trigger re-parsing.

        Args:
            experiment_path: Filesystem path to the experiment directory.

        Returns:
            The summary as a dict (from ``ExperimentSummary.to_dict()``),
            or ``None`` if summary collection fails.
        """
        if experiment_path in self._summary_cache:
            return self._summary_cache[experiment_path]

        from panther.core.reporting.status_collector import StatusCollector

        try:
            collector = StatusCollector(Path(experiment_path))
            summary = collector.collect_experiment_summary()
            result = summary.to_dict()
            self._summary_cache[experiment_path] = result
            return result
        except Exception as e:
            logger.warning("Failed to collect experiment summary: %s", e)
            return None

    def get_test_results(self, experiment_path: str) -> list[dict]:
        """Extract per-test pass/fail/duration records, ready for charting.

        Args:
            experiment_path: Filesystem path to the experiment directory.

        Returns:
            A list of result dicts as stored in the summary's
            ``tests.results`` array.  Returns an empty list if no
            summary is available.
        """
        summary = self.get_experiment_summary(experiment_path)
        if not summary:
            return []
        tests_info = summary.get("tests", {})
        return tests_info.get("results", [])

    def get_service_health(self, experiment_path: str) -> list[dict]:
        """Extract per-service health summaries from the experiment summary.

        Args:
            experiment_path: Filesystem path to the experiment directory.

        Returns:
            A list of service health dicts as stored in the summary's
            ``services`` array.  Returns an empty list if no summary is
            available.
        """
        summary = self.get_experiment_summary(experiment_path)
        if not summary:
            return []
        return summary.get("services", [])

    def get_metrics_timeseries(self, experiment_path: str) -> list[dict]:
        """Parse ``metrics*.json`` files into normalised time-series records.

        Walks the experiment directory tree, reads every file matching the
        ``metrics*.json`` glob, and normalises the content into a flat list
        of ``{timestamp, metric, value}`` records suitable for ECharts
        line/area charts.  Supports three common metrics-file formats
        (see ``_parse_metrics_file``).

        Args:
            experiment_path: Filesystem path to the experiment directory.

        Returns:
            A list of dicts with keys ``timestamp`` (str or ``None``),
            ``metric`` (dot-delimited name), and ``value`` (numeric).
        """
        exp_dir = Path(experiment_path)
        timeseries = []

        for metrics_file in exp_dir.rglob("metrics*.json"):
            try:
                data = json.loads(metrics_file.read_text())
                timeseries.extend(self._parse_metrics_file(data))
            except (json.JSONDecodeError, OSError) as e:
                logger.debug("Failed to parse metrics file %s: %s", metrics_file, e)

        return timeseries

    def _parse_metrics_file(self, data: dict) -> list[dict]:
        """Normalise a single metrics JSON dict into flat time-series records."""
        results = []
        timestamp = data.get("timestamp", None)

        # Format 1: {"memory": {...}} direct keys
        for key in ("memory", "cpu", "disk", "network"):
            if key in data and isinstance(data[key], dict):
                for metric_name, value in data[key].items():
                    if isinstance(value, (int, float)):
                        results.append(
                            {
                                "timestamp": timestamp,
                                "metric": f"{key}.{metric_name}",
                                "value": value,
                            }
                        )

        # Format 2: {"resource_metrics": {...}}
        if "resource_metrics" in data and isinstance(data["resource_metrics"], dict):
            rm = data["resource_metrics"]
            for metric_name, value in rm.items():
                if isinstance(value, (int, float)):
                    results.append(
                        {
                            "timestamp": timestamp,
                            "metric": f"resource.{metric_name}",
                            "value": value,
                        }
                    )
                elif isinstance(value, dict):
                    for sub_name, sub_value in value.items():
                        if isinstance(sub_value, (int, float)):
                            results.append(
                                {
                                    "timestamp": timestamp,
                                    "metric": f"resource.{metric_name}.{sub_name}",
                                    "value": sub_value,
                                }
                            )

        # Format 3: Direct metric keys (flat)
        if not results:
            for key, value in data.items():
                if key != "timestamp" and isinstance(value, (int, float)):
                    results.append(
                        {
                            "timestamp": timestamp,
                            "metric": key,
                            "value": value,
                        }
                    )

        return results

    def get_metrics_data(self, experiment_path: str) -> Optional[dict[str, Any]]:
        """Load raw metrics data via PANTHER's ``MetricsDataLoader``.

        Unlike ``get_metrics_timeseries`` (which normalises data into flat
        records), this method returns the metrics dict in whatever
        structure the ``MetricsDataLoader`` produces, preserving all
        original fields for detailed inspection.

        Args:
            experiment_path: Filesystem path to the experiment directory.

        Returns:
            The parsed metrics dict, or ``None`` if no metrics were
            collected for this experiment.
        """
        from panther.core.metrics import MetricsDataLoader

        exp_dir = Path(experiment_path)
        loader = MetricsDataLoader(output_dir=exp_dir.parent)
        data, _ = loader.load_metrics(experiment_dir=exp_dir)
        return data

    def get_aggregate_stats(self, experiment_path: str) -> dict:
        """Return aggregate pass/fail statistics for an experiment.

        Args:
            experiment_path: Filesystem path to the experiment directory.

        Returns:
            A dict with keys ``total`` (int), ``passed`` (int),
            ``failed`` (int), ``success_rate`` (float, 0.0--1.0), and
            ``duration`` (float seconds or ``None``).  Returns zeroed
            stats if no summary is available.
        """
        summary = self.get_experiment_summary(experiment_path)
        if not summary:
            return {
                "total": 0,
                "passed": 0,
                "failed": 0,
                "success_rate": 0.0,
                "duration": None,
            }

        tests = summary.get("tests", {})
        return {
            "total": tests.get("total", 0),
            "passed": tests.get("passed", 0),
            "failed": tests.get("failed", 0),
            "success_rate": tests.get("success_rate", 0.0),
            "duration": summary.get("duration_seconds"),
        }
