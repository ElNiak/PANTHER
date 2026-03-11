"""ResultsService -- browsing, analysis, and charting of experiment results.

This module provides read-only access to the output artifacts produced by
completed PANTHER experiments.  It scans the filesystem-based output
directory, parses structured summary files (``experiment_summary.json``),
reads per-test event logs (``events.jsonl``), and normalises metrics data
into chart-ready time-series records.

Output directory structure (produced by PANTHER's reporting subsystem):
    ::

        outputs/
          <YYYY-MM-DD_HH-MM-SS[_name]>/        # one experiment run
            experiment_summary.json             # machine-readable summary
            experiment_events.log               # top-level event stream
            EXPERIMENT_REPORT.md                # human-readable report
            <test_name>/                        # one test case
              test_config.yaml                  # frozen config snapshot
              test.log                          # combined log
              events.jsonl                      # structured event stream
              error_events.jsonl                # error-only subset
              logs/
                <service_name>/                 # one service (IUT / tester)
                  <phase>/                      # execution phase
                    stdout.log
                    stderr.log
                    compilation_status.txt
              analysis/                         # post-run analysis JSONs
              metrics*.json                     # resource usage snapshots

All public methods return plain Python dicts/lists that can be directly
serialised to JSON for the NiceGUI frontend.  Large files are read through
``FileUtils.read_text_bounded`` to cap memory usage.
"""

import json
import logging
from pathlib import Path
from typing import Any, Optional

from panther.core.utils.file_utils import FileUtils

logger = logging.getLogger(__name__)


class ResultsService:
    """Read-only service for browsing, summarising, and charting experiment results.

    ResultsService scans the filesystem-based output directory produced by
    PANTHER's reporting subsystem (``panther.core.reporting``,
    ``panther.core.results``, ``panther.core.outputs``) and exposes its
    contents through a set of methods that return plain Python dicts and
    lists suitable for direct JSON serialisation to the NiceGUI frontend.

    The service delegates heavy analysis work to
    ``StatusCollector`` (PANTHER's core report aggregator) and caches
    ``ExperimentSummary`` objects in memory to avoid re-parsing on
    repeated accesses within the same page view.

    Output directory conventions:
        Each experiment run produces a timestamped directory under
        ``outputs/`` named ``YYYY-MM-DD_HH-MM-SS[_name]``.  Inside, each
        test case gets its own subdirectory containing logs, events, analysis
        results, and artifacts (pcap files, JSON reports, etc.).  See the
        module docstring for the full directory tree layout.

    Attributes:
        output_dir: ``Path`` to the root outputs directory.

    Example::

        svc = ResultsService("outputs")
        for exp in svc.list_experiments():
            detail = svc.get_experiment_detail(exp["name"])
            print(detail["status"], detail["test_count"])
    """

    def __init__(self, output_dir: str = "outputs"):
        """Create a ResultsService pointing at the given output root.

        Args:
            output_dir: Filesystem path to the directory that contains
                experiment result subdirectories.  Defaults to ``"outputs"``
                (relative to the working directory).
        """
        self.output_dir = Path(output_dir)
        self._summary_cache: dict[str, dict] = {}

    def count_experiments(self) -> int:
        """Return the number of experiment result directories.

        Returns:
            Integer count of experiment directories found under
            ``output_dir``.
        """
        return len(self.list_experiments())

    def list_experiments(self) -> list[dict[str, Any]]:
        """List all experiment result directories, newest first.

        Scans the top-level children of ``output_dir``, skipping hidden
        directories and non-directory entries.

        Returns:
            A list of dicts, each with keys:

            - ``date`` -- the ``YYYY-MM-DD`` prefix extracted from the
              directory name.
            - ``name`` -- the full directory name.
            - ``path`` -- absolute string path to the directory.
            - ``test_count`` -- number of test subdirectories detected.
            - ``status`` -- ``"completed"``, ``"failed"``, or ``"unknown"``.
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
        """Return enriched detail for a single experiment by directory name.

        Loads the machine-readable ``experiment_summary.json`` (produced by
        PANTHER's ``ExperimentSummary.to_dict()``) when available, and falls
        back to on-the-fly computation via ``StatusCollector`` otherwise.
        The result is augmented with log content, report markdown, and a
        list of downloadable artifacts.

        Args:
            name: The experiment directory name (e.g.
                ``"2025-03-10_14-30-00_quic_test"``).

        Returns:
            A dict with keys ``date``, ``name``, ``path``, ``test_count``,
            ``status``, ``core_summary``, ``log_content``,
            ``report_content``, and ``artifacts``.  Returns ``None`` if no
            experiment with that name exists.
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
        """Read the experiment's main log file and return the last *tail* lines.

        Searches for ``experiment.log``, then any ``*.log``, then
        ``logs/*.log`` under the experiment directory.  Uses
        ``FileUtils.read_text_bounded`` to cap memory usage on very large
        log files.

        Args:
            exp_path: Filesystem path to the experiment directory.
            tail: Maximum number of lines to return from the end of the
                file.

        Returns:
            A list of log line strings (without trailing newlines).
            Returns an empty list if no log file is found.
        """
        exp_dir = Path(exp_path)
        for pattern in ["experiment.log", "*.log", "logs/*.log"]:
            logs = list(exp_dir.glob(pattern))
            if logs:
                try:
                    lines = FileUtils.read_text_bounded(logs[0]).splitlines()
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
                    return FileUtils.read_text_bounded(report)
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
                    rel = Path(f.name)
                    test_name = ""
                artifacts.append(
                    {"name": f.name, "path": str(rel), "test_name": test_name}
                )
        return artifacts

    # ------------------------------------------------------------------
    # New data access methods
    # ------------------------------------------------------------------

    def list_tests(self, experiment_path: str) -> list[dict[str, Any]]:
        """Return a per-test summary list for an experiment.

        Reads structured data from ``experiment_summary.json`` when
        available, and falls back to filesystem heuristics (scanning for
        subdirectories that contain ``test_config.yaml`` or ``test.log``).
        Each entry is enriched with filesystem-derived flags indicating
        whether events and analysis data are available.

        Args:
            experiment_path: Filesystem path to the experiment directory.

        Returns:
            A list of dicts, each with keys: ``name``, ``status``,
            ``duration``, ``start_time``, ``end_time``,
            ``error_message``, ``has_events`` (bool), ``has_analysis``
            (bool), ``service_count`` (int).
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
                    "has_analysis": ResultsService._has_analysis(test_dir),
                    "service_count": self._count_services(test_dir),
                }
                results.append(entry)
        else:
            # Fallback: scan filesystem for test directories
            if exp_dir.exists():
                try:
                    dirs = sorted(exp_dir.iterdir())
                except OSError as e:
                    logger.warning("Error scanning experiment dir %s: %s", exp_dir, e)
                    dirs = []
                for d in dirs:
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
                                "has_analysis": ResultsService._has_analysis(d),
                                "service_count": self._count_services(d),
                            }
                        )
        return results

    @staticmethod
    def _has_analysis(test_dir: Path) -> bool:
        """Check if test_dir/analysis/ exists and has files."""
        analysis_dir = test_dir / "analysis"
        if not analysis_dir.is_dir():
            return False
        try:
            return any(analysis_dir.iterdir())
        except OSError:
            return False

    def _count_services(self, test_dir: Path) -> int:
        """Count service directories under test_dir/logs/."""
        logs_dir = test_dir / "logs"
        if not logs_dir.is_dir():
            return 0
        try:
            return sum(
                1
                for d in logs_dir.iterdir()
                if d.is_dir() and not d.name.startswith(".")
            )
        except OSError:
            return 0

    def get_test_detail(
        self, experiment_path: str, test_name: str
    ) -> Optional[dict[str, Any]]:
        """Return rich detail for a single test within an experiment.

        Combines data from the experiment summary JSON (if available), the
        service log tree (directory hierarchy under ``logs/``), analysis
        results (JSON files under ``analysis/``), and a list of
        test-level artifacts.

        Args:
            experiment_path: Filesystem path to the experiment directory.
            test_name: Name of the test subdirectory.

        Returns:
            A dict with keys ``info`` (test metadata dict), ``services``
            (list of service log trees), ``analysis`` (dict of analysis
            JSON keyed by filename stem, or ``None``), and ``artifacts``
            (list of ``{name, path}`` dicts).  Returns ``None`` if the
            test directory does not exist.
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
        try:
            for f in test_dir.iterdir():
                if f.is_file() and f.suffix in artifact_exts:
                    artifacts.append({"name": f.name, "path": f.name})
        except OSError as e:
            logger.warning("Error listing test artifacts in %s: %s", test_dir, e)

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
        try:
            svc_entries = sorted(logs_dir.iterdir())
        except OSError as e:
            logger.warning("Error reading logs dir %s: %s", logs_dir, e)
            return []
        for svc_dir in svc_entries:
            if not svc_dir.is_dir() or svc_dir.name.startswith("."):
                continue
            # Skip non-service directories (docker_* logs are at logs/ root level)
            if svc_dir.name.startswith("docker_") or svc_dir.name.endswith(".log"):
                continue

            phases = []
            try:
                phase_entries = sorted(svc_dir.iterdir())
            except OSError:
                phase_entries = []
            for phase_dir in phase_entries:
                if not phase_dir.is_dir():
                    continue
                files = []
                try:
                    file_entries = sorted(phase_dir.iterdir())
                except OSError:
                    file_entries = []
                for f in file_entries:
                    if f.is_file():
                        try:
                            rel_path = f.relative_to(test_dir)
                        except ValueError:
                            rel_path = f.name
                        files.append(
                            {
                                "name": f.name,
                                "size": f.stat().st_size,
                                "path": str(rel_path),
                            }
                        )
                if files:
                    phases.append({"phase_name": phase_dir.name, "files": files})

            services.append({"service_name": svc_dir.name, "phases": phases})
        return services

    def get_test_events(
        self, experiment_path: str, test_name: str
    ) -> list[dict[str, Any]]:
        """Parse per-test event log files and return normalised event dicts.

        Reads both ``events.jsonl`` (all events) and ``error_events.jsonl``
        (error-only subset) from the test directory.  Event field names are
        normalised (``type`` -> ``event_type``, ``id`` -> ``event_id``) and
        each event is tagged with a ``_source`` field indicating which file
        it came from.  Malformed JSON lines are skipped with a warning.

        Args:
            experiment_path: Filesystem path to the experiment directory.
            test_name: Name of the test subdirectory.

        Returns:
            A list of event dicts sorted by ``timestamp``.
        """
        test_dir = Path(experiment_path) / test_name
        events: list[dict[str, Any]] = []

        for filename in ["events.jsonl", "error_events.jsonl"]:
            events_file = test_dir / filename
            if events_file.exists():
                try:
                    text = FileUtils.read_text_bounded(events_file)
                    skipped = 0
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
                            skipped += 1
                            continue
                    if skipped:
                        logger.warning(
                            "Skipped %d malformed line(s) in %s", skipped, events_file
                        )
                except OSError as e:
                    logger.debug("Failed to read %s: %s", events_file, e)

        # Sort by timestamp
        events.sort(key=lambda e: e.get("timestamp", ""))
        return events

    def get_experiment_events(self, experiment_path: str) -> list[dict[str, Any]]:
        """Parse the top-level experiment event log file.

        Reads ``experiment_events.log`` which may contain either
        JSON-Lines structured events or plain-text log lines.  Plain-text
        lines are wrapped in a dict with ``event_type: "log"``.

        Args:
            experiment_path: Filesystem path to the experiment directory.

        Returns:
            A list of event dicts sorted by ``timestamp``.
        """
        exp_dir = Path(experiment_path)
        events: list[dict[str, Any]] = []

        # Try experiment_events.log (may contain structured or plain text)
        events_log = exp_dir / "experiment_events.log"
        if events_log.exists():
            try:
                text = FileUtils.read_text_bounded(events_log)
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
        """Read stdout/stderr log content for each execution phase of a service.

        The directory layout is:
        ``<experiment>/<test>/logs/<service>/<phase>/stdout.log|stderr.log``

        If a ``compilation_status.txt`` file exists in a phase directory,
        its content is included under the ``"compilation_status"`` key.

        Args:
            experiment_path: Filesystem path to the experiment directory.
            test_name: Name of the test subdirectory.
            service_name: Name of the service (e.g. ``"picoquic_server"``).

        Returns:
            A dict keyed by phase name, where each value is a dict with
            keys ``"stdout"`` and ``"stderr"`` (each ``str`` or ``None``),
            and optionally ``"compilation_status"``.  Phases with no
            non-empty content are omitted.  Returns an empty dict if the
            service directory does not exist.
        """
        svc_dir = Path(experiment_path) / test_name / "logs" / service_name
        if not svc_dir.is_dir():
            return {}

        result: dict[str, dict[str, Optional[str]]] = {}
        try:
            phase_dirs = sorted(svc_dir.iterdir())
        except OSError as e:
            logger.warning("Error reading service dir %s: %s", svc_dir, e)
            return {}
        for phase_dir in phase_dirs:
            if not phase_dir.is_dir():
                continue
            phase_data: dict[str, Optional[str]] = {}
            for log_name in ["stdout.log", "stderr.log"]:
                log_file = phase_dir / log_name
                if log_file.exists():
                    try:
                        content = FileUtils.read_text_bounded(log_file)
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
                    phase_data["compilation_status"] = FileUtils.read_text_bounded(
                        comp_status
                    )
                except OSError as e:
                    logger.warning("Error reading %s: %s", comp_status, e)

            if any(v for v in phase_data.values()):
                result[phase_dir.name] = phase_data

        return result

    def get_analysis_results(
        self, experiment_path: str, test_name: str
    ) -> Optional[dict[str, Any]]:
        """Read post-run analysis JSON files from the test's ``analysis/`` directory.

        Args:
            experiment_path: Filesystem path to the experiment directory.
            test_name: Name of the test subdirectory.

        Returns:
            A dict mapping filename stems to their parsed JSON content, or
            ``None`` if the ``analysis/`` directory does not exist or
            contains no parseable JSON files.
        """
        analysis_dir = Path(experiment_path) / test_name / "analysis"
        if not analysis_dir.is_dir():
            return None

        results: dict[str, Any] = {}
        try:
            entries = list(analysis_dir.iterdir())
        except OSError as e:
            logger.warning("Error reading analysis dir %s: %s", analysis_dir, e)
            return None
        for f in entries:
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
