"""TestDataMixin — per-test data access for ResultsService.

Provides methods for listing tests, retrieving test detail, parsing
event logs, reading service logs, and loading analysis results.
"""

import json
import logging
from pathlib import Path
from typing import Any, Optional

from panther.core.utils.file_utils import FileUtils

logger = logging.getLogger(__name__)


class TestDataMixin:
    """Mixin providing per-test data access methods for ResultsService."""

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
                    "has_analysis": TestDataMixin._has_analysis(test_dir),
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
                                "has_analysis": TestDataMixin._has_analysis(d),
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
