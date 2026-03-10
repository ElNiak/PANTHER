"""Service layer for browsing experiment results."""

import json
import logging
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

_MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


def _read_text_bounded(path: Path, max_bytes: int = _MAX_FILE_SIZE) -> str:
    """Read text file with size limit to prevent OOM."""
    if path.stat().st_size > max_bytes:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            return f.read(max_bytes)
    return path.read_text(encoding="utf-8", errors="replace")


class ResultsService:
    """Scans the outputs directory for past experiment results."""

    def __init__(self, output_dir: str = "outputs"):
        """Initialize with the root outputs directory path."""
        self.output_dir = Path(output_dir)
        self._summary_cache: dict[str, dict] = {}

    def count_experiments(self) -> int:
        """Count the number of experiment result directories."""
        return len(self.list_experiments())

    def list_experiments(self) -> list[dict[str, Any]]:
        """List all experiment results found in the output directory.

        Returns a list of dicts with: date, name, test_count, status.
        """
        if not self.output_dir.exists():
            return []

        experiments = []
        try:
            # outputs/<date>/<experiment_id>/
            for date_dir in sorted(self.output_dir.iterdir(), reverse=True):
                if not date_dir.is_dir() or date_dir.name.startswith("."):
                    continue
                for exp_dir in sorted(date_dir.iterdir()):
                    if not exp_dir.is_dir() or exp_dir.name.startswith("."):
                        continue
                    experiments.append(
                        {
                            "date": date_dir.name,
                            "name": exp_dir.name,
                            "path": str(exp_dir),
                            "test_count": self._count_tests(exp_dir),
                            "status": self._detect_status(exp_dir),
                        }
                    )
        except OSError as e:
            logger.warning("Error scanning output directory: %s", e)

        return experiments

    def get_experiment_detail(self, name: str) -> Optional[dict[str, Any]]:
        """Get detailed info for a specific experiment result.

        Loads core ExperimentSummary data from experiment_summary.json when
        available, falling back to filesystem heuristics.
        """
        for exp in self.list_experiments():
            if exp["name"] == name:
                exp_path = Path(exp["path"])
                detail = dict(exp)

                # Enrich with core ExperimentSummary data when available
                summary_data = self._load_experiment_summary_json(exp_path)
                if summary_data:
                    detail["core_summary"] = summary_data
                    tests_info = summary_data.get("tests", {})
                    if isinstance(tests_info, dict):
                        detail["test_count"] = tests_info.get(
                            "total", detail["test_count"]
                        )
                    detail["status"] = summary_data.get("status", detail["status"])

                if not summary_data:
                    # Fallback: compute summary on-the-fly from logs/outputs
                    computed = self.get_experiment_summary(str(exp_path))
                    if computed:
                        detail["core_summary"] = computed
                        tests_info = computed.get("tests", {})
                        if isinstance(tests_info, dict):
                            detail["test_count"] = tests_info.get(
                                "total", detail["test_count"]
                            )
                        detail["status"] = computed.get("status", detail["status"])

                detail["log_content"] = self._read_log(exp_path)
                detail["report_content"] = self._read_report(exp_path)
                detail["artifacts"] = self._list_artifacts(exp_path)
                return detail
        return None

    def _count_tests(self, exp_dir: Path) -> int:
        """Count test result files in an experiment directory."""
        json_count = 0
        any_count = 0
        for f in exp_dir.rglob("test_*"):
            any_count += 1
            if f.suffix == ".json":
                json_count += 1
        return json_count or any_count

    def _detect_status(self, exp_dir: Path) -> str:
        """Detect experiment status from result files."""
        if (exp_dir / "FAILED").exists():
            return "failed"
        summary = self._load_experiment_summary_json(exp_dir)
        if summary:
            return summary.get("status", "completed")
        if (exp_dir / "report.md").exists():
            return "completed"
        return "unknown"

    def _load_experiment_summary_json(self, exp_dir: Path) -> Optional[dict]:
        """Load experiment_summary.json (core ExperimentSummary.to_dict() output)."""
        summary_json = exp_dir / "experiment_summary.json"
        if summary_json.exists():
            try:
                return json.loads(summary_json.read_text())
            except (OSError, json.JSONDecodeError) as e:
                logger.debug("Could not load experiment_summary.json: %s", e)
        return None

    def read_log_lines(self, exp_path: str, tail: int = 1000) -> list[str]:
        """Read log lines as a list for easy filtering.

        Args:
            exp_path: Path to experiment directory.
            tail: Maximum number of lines to return (from end of file).

        Returns:
            List of log line strings.
        """
        exp_dir = Path(exp_path)
        for pattern in ["*.log", "logs/*.log", "experiment.log"]:
            logs = list(exp_dir.glob(pattern))
            if logs:
                try:
                    lines = _read_text_bounded(logs[0]).splitlines()
                    return lines[-tail:]
                except OSError:
                    pass
        return []

    def _read_log(self, exp_dir: Path) -> Optional[str]:
        """Read the main log file if it exists."""
        lines = self.read_log_lines(str(exp_dir), tail=500)
        return "\n".join(lines) if lines else None

    def _read_report(self, exp_dir: Path) -> Optional[str]:
        """Read the report markdown if it exists."""
        for name in ["report.md", "README.md", "summary.md"]:
            report = exp_dir / name
            if report.exists():
                try:
                    return _read_text_bounded(report)
                except OSError:
                    pass
        return None

    def _list_artifacts(self, exp_dir: Path) -> list[dict[str, str]]:
        """List downloadable artifacts in the experiment directory."""
        artifacts = []
        for f in exp_dir.rglob("*"):
            if f.is_file() and f.suffix in {".pcap", ".json", ".csv", ".yaml", ".log"}:
                artifacts.append({"name": f.name, "path": str(f)})
        return artifacts

    def get_experiment_summary(self, experiment_path: str) -> Optional[dict]:
        """Parse ExperimentSummary using core StatusCollector (cached)."""
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
        """Extract per-test pass/fail/duration data (chart-ready)."""
        summary = self.get_experiment_summary(experiment_path)
        if not summary:
            return []
        tests_info = summary.get("tests", {})
        return tests_info.get("results", [])

    def get_service_health(self, experiment_path: str) -> list[dict]:
        """Extract service health summaries."""
        summary = self.get_experiment_summary(experiment_path)
        if not summary:
            return []
        return summary.get("services", [])

    def get_metrics_timeseries(self, experiment_path: str) -> list[dict]:
        """Parse metrics*.json into time-series data for ECharts.

        Returns normalized [{"timestamp": ..., "metric": ..., "value": ...}].
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
        """Normalize metrics data from different formats."""
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

    def get_aggregate_stats(self, experiment_path: str) -> dict:
        """Return {total, passed, failed, success_rate, duration}."""
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
