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

        Each directory under outputs/ is an experiment (single-level).
        Directory names follow: YYYY-MM-DD_HH-MM-SS[_name]
        """
        if not self.output_dir.exists():
            return []

        experiments = []
        try:
            for exp_dir in sorted(self.output_dir.iterdir(), reverse=True):
                if not exp_dir.is_dir() or exp_dir.name.startswith("."):
                    continue
                # Extract date from directory name (format: YYYY-MM-DD_HH-MM-SS[_name])
                date_part = (
                    exp_dir.name[:10] if len(exp_dir.name) >= 10 else exp_dir.name
                )
                experiments.append(
                    {
                        "date": date_part,
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
        """Count test subdirectories (contain test_config.yaml or test.log)."""
        count = 0
        try:
            for d in exp_dir.iterdir():
                if d.is_dir() and (
                    (d / "test_config.yaml").exists() or (d / "test.log").exists()
                ):
                    count += 1
        except OSError as e:
            logger.warning("Error counting tests in %s: %s", exp_dir, e)
        return count

    def _detect_status(self, exp_dir: Path) -> str:
        """Detect experiment status from result files."""
        if (exp_dir / "FAILED").exists():
            return "failed"
        summary = self._load_experiment_summary_json(exp_dir)
        if summary:
            return summary.get("status", "completed")
        for name in ["EXPERIMENT_REPORT.md", "report.md"]:
            if (exp_dir / name).exists():
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
        """Read log lines as a list for easy filtering."""
        exp_dir = Path(exp_path)
        for pattern in ["experiment.log", "*.log", "logs/*.log"]:
            logs = list(exp_dir.glob(pattern))
            if logs:
                try:
                    lines = _read_text_bounded(logs[0]).splitlines()
                    return lines[-tail:]
                except OSError as e:
                    logger.warning("Error reading log file %s: %s", logs[0], e)
        return []

    def _read_log(self, exp_dir: Path) -> Optional[str]:
        """Read the main log file if it exists."""
        lines = self.read_log_lines(str(exp_dir), tail=500)
        return "\n".join(lines) if lines else None

    def _read_report(self, exp_dir: Path) -> Optional[str]:
        """Read the report markdown if it exists."""
        for name in ["EXPERIMENT_REPORT.md", "report.md", "README.md", "summary.md"]:
            report = exp_dir / name
            if report.exists():
                try:
                    return _read_text_bounded(report)
                except OSError as e:
                    logger.warning("Error reading report %s: %s", report, e)
        return None

    def _list_artifacts(self, exp_dir: Path) -> list[dict[str, str]]:
        """List downloadable artifacts organized by test directory."""
        artifacts = []
        artifact_exts = {".pcap", ".json", ".csv", ".yaml", ".yml", ".log"}
        for f in exp_dir.rglob("*"):
            if f.is_file() and f.suffix in artifact_exts:
                # Determine which test this artifact belongs to
                try:
                    rel = f.relative_to(exp_dir)
                    test_name = rel.parts[0] if len(rel.parts) > 1 else ""
                except ValueError:
                    test_name = ""
                artifacts.append(
                    {"name": f.name, "path": str(f), "test_name": test_name}
                )
        return artifacts

    # ------------------------------------------------------------------
    # New data access methods
    # ------------------------------------------------------------------

    def list_tests(self, experiment_path: str) -> list[dict[str, Any]]:
        """Return per-test summary from experiment_summary.json enriched with fs info.

        Each dict: name, status, duration, start_time, end_time, error_message,
        has_events, has_analysis, service_count.
        """
        exp_dir = Path(experiment_path)
        summary = self._load_experiment_summary_json(exp_dir)

        results: list[dict[str, Any]] = []
        if summary:
            tests_info = summary.get("tests", {})
            for r in tests_info.get("results", []):
                test_name = r.get("name", "")
                test_dir = exp_dir / test_name
                entry = {
                    "name": test_name,
                    "status": r.get("status", "unknown"),
                    "duration": r.get("duration"),
                    "start_time": r.get("start_time"),
                    "end_time": r.get("end_time"),
                    "error_message": r.get("error_message"),
                    "has_events": (test_dir / "events.jsonl").exists(),
                    "has_analysis": (
                        (test_dir / "analysis").is_dir()
                        and any((test_dir / "analysis").iterdir())
                    ),
                    "service_count": self._count_services(test_dir),
                }
                results.append(entry)
        else:
            # Fallback: scan filesystem for test directories
            if exp_dir.exists():
                for d in sorted(exp_dir.iterdir()):
                    if d.is_dir() and (
                        (d / "test_config.yaml").exists() or (d / "test.log").exists()
                    ):
                        results.append(
                            {
                                "name": d.name,
                                "status": "unknown",
                                "duration": None,
                                "start_time": None,
                                "end_time": None,
                                "error_message": None,
                                "has_events": (d / "events.jsonl").exists(),
                                "has_analysis": (
                                    (d / "analysis").is_dir()
                                    and any((d / "analysis").iterdir())
                                    if (d / "analysis").is_dir()
                                    else False
                                ),
                                "service_count": self._count_services(d),
                            }
                        )
        return results

    def _count_services(self, test_dir: Path) -> int:
        """Count service directories under test_dir/logs/."""
        logs_dir = test_dir / "logs"
        if not logs_dir.is_dir():
            return 0
        return sum(
            1 for d in logs_dir.iterdir() if d.is_dir() and not d.name.startswith(".")
        )

    def get_test_detail(
        self, experiment_path: str, test_name: str
    ) -> Optional[dict[str, Any]]:
        """Return detailed info for a single test.

        Includes: test result info, services list, analysis results,
        available log tree, and test-level artifacts.
        """
        exp_dir = Path(experiment_path)
        test_dir = exp_dir / test_name
        if not test_dir.is_dir():
            return None

        # Get test result info from summary
        test_info: dict[str, Any] = {"name": test_name}
        summary = self._load_experiment_summary_json(exp_dir)
        if summary:
            for r in summary.get("tests", {}).get("results", []):
                if r.get("name") == test_name:
                    test_info.update(r)
                    break

        # Service log tree
        services = self._get_service_tree(test_dir)

        # Analysis results
        analysis = self.get_analysis_results(experiment_path, test_name)

        # Test-level artifacts
        artifact_exts = {".pcap", ".json", ".csv", ".yaml", ".yml", ".log", ".sh"}
        artifacts = []
        for f in test_dir.iterdir():
            if f.is_file() and f.suffix in artifact_exts:
                artifacts.append({"name": f.name, "path": str(f)})

        return {
            "info": test_info,
            "services": services,
            "analysis": analysis,
            "artifacts": artifacts,
        }

    def _get_service_tree(self, test_dir: Path) -> list[dict[str, Any]]:
        """Build service log tree for a test directory.

        Returns list of {service_name, phases: [{phase_name, files: [{name, size}]}]}
        """
        logs_dir = test_dir / "logs"
        if not logs_dir.is_dir():
            return []

        services = []
        for svc_dir in sorted(logs_dir.iterdir()):
            if not svc_dir.is_dir() or svc_dir.name.startswith("."):
                continue
            # Skip non-service directories (docker_* logs are at logs/ root level)
            if svc_dir.name.startswith("docker_") or svc_dir.name.endswith(".log"):
                continue

            phases = []
            for phase_dir in sorted(svc_dir.iterdir()):
                if not phase_dir.is_dir():
                    continue
                files = []
                for f in sorted(phase_dir.iterdir()):
                    if f.is_file():
                        files.append(
                            {"name": f.name, "size": f.stat().st_size, "path": str(f)}
                        )
                if files:
                    phases.append({"phase_name": phase_dir.name, "files": files})

            services.append({"service_name": svc_dir.name, "phases": phases})
        return services

    def get_test_events(
        self, experiment_path: str, test_name: str
    ) -> list[dict[str, Any]]:
        """Parse events.jsonl and error_events.jsonl for a test."""
        test_dir = Path(experiment_path) / test_name
        events: list[dict[str, Any]] = []

        for filename in ["events.jsonl", "error_events.jsonl"]:
            events_file = test_dir / filename
            if events_file.exists():
                try:
                    text = _read_text_bounded(events_file)
                    for line in text.splitlines():
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            event = json.loads(line)
                            # Normalize field names (some use event_type, some use type)
                            if "event_type" not in event and "type" in event:
                                event["event_type"] = event["type"]
                            if "event_id" not in event and "id" in event:
                                event["event_id"] = event["id"]
                            event["_source"] = filename
                            events.append(event)
                        except json.JSONDecodeError:
                            continue
                except OSError as e:
                    logger.debug("Failed to read %s: %s", events_file, e)

        # Sort by timestamp
        events.sort(key=lambda e: e.get("timestamp", ""))
        return events

    def get_experiment_events(self, experiment_path: str) -> list[dict[str, Any]]:
        """Parse top-level experiment event files."""
        exp_dir = Path(experiment_path)
        events: list[dict[str, Any]] = []

        # Try experiment_events.log (may contain structured or plain text)
        events_log = exp_dir / "experiment_events.log"
        if events_log.exists():
            try:
                text = _read_text_bounded(events_log)
                for line in text.splitlines():
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        event = json.loads(line)
                        if "event_type" not in event and "type" in event:
                            event["event_type"] = event["type"]
                        if "event_id" not in event and "id" in event:
                            event["event_id"] = event["id"]
                        events.append(event)
                    except json.JSONDecodeError:
                        # Plain text log line — wrap it
                        events.append(
                            {
                                "event_type": "log",
                                "timestamp": "",
                                "data": {"message": line},
                            }
                        )
            except OSError as e:
                logger.debug("Failed to read experiment_events.log: %s", e)

        events.sort(key=lambda e: e.get("timestamp", ""))
        return events

    def get_service_logs(
        self, experiment_path: str, test_name: str, service_name: str
    ) -> dict[str, dict[str, Optional[str]]]:
        """Return per-phase {stdout, stderr} log content for a service.

        Returns: {phase_name: {"stdout": content, "stderr": content}}
        """
        svc_dir = Path(experiment_path) / test_name / "logs" / service_name
        if not svc_dir.is_dir():
            return {}

        result: dict[str, dict[str, Optional[str]]] = {}
        for phase_dir in sorted(svc_dir.iterdir()):
            if not phase_dir.is_dir():
                continue
            phase_data: dict[str, Optional[str]] = {}
            for log_name in ["stdout.log", "stderr.log"]:
                log_file = phase_dir / log_name
                if log_file.exists():
                    try:
                        content = _read_text_bounded(log_file)
                        phase_data[log_name.replace(".log", "")] = (
                            content if content.strip() else None
                        )
                    except OSError:
                        phase_data[log_name.replace(".log", "")] = None
                else:
                    phase_data[log_name.replace(".log", "")] = None

            # Also include compilation_status.txt if present
            comp_status = phase_dir / "compilation_status.txt"
            if comp_status.exists():
                try:
                    phase_data["compilation_status"] = _read_text_bounded(comp_status)
                except OSError as e:
                    logger.warning("Error reading %s: %s", comp_status, e)

            if any(v for v in phase_data.values()):
                result[phase_dir.name] = phase_data

        return result

    def get_analysis_results(
        self, experiment_path: str, test_name: str
    ) -> Optional[dict[str, Any]]:
        """Read analysis results from test_dir/analysis/."""
        analysis_dir = Path(experiment_path) / test_name / "analysis"
        if not analysis_dir.is_dir():
            return None

        results: dict[str, Any] = {}
        for f in analysis_dir.iterdir():
            if f.is_file() and f.suffix == ".json":
                try:
                    data = json.loads(f.read_text())
                    results[f.stem] = data
                except (json.JSONDecodeError, OSError) as e:
                    logger.debug("Failed to parse analysis file %s: %s", f, e)
        return results if results else None

    # ------------------------------------------------------------------
    # Existing analysis/chart methods
    # ------------------------------------------------------------------

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
