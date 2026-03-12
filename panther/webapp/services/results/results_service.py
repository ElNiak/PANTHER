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

import itertools
import json
import logging
from pathlib import Path
from typing import Any, Optional

from panther.core.utils.file_utils import FileUtils
from panther.webapp.services.results.analytics_mixin import AnalyticsMixin
from panther.webapp.services.results.test_data_mixin import TestDataMixin

logger = logging.getLogger(__name__)


class ResultsService(TestDataMixin, AnalyticsMixin):
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
        logger.debug("ResultsService initialized with output_dir: %s", self.output_dir)

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

        logger.debug(
            "Found %d experiment directories in %s", len(experiments), self.output_dir
        )
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
        logger.debug("Fetching detail for experiment: %s", name)
        exp_path = self.output_dir / name
        if not exp_path.is_dir():
            logger.debug("Experiment not found: %s", name)
            return None

        date_part = name[:10] if len(name) >= 10 else name
        detail: dict[str, Any] = {
            "date": date_part,
            "name": name,
            "path": str(exp_path),
            "test_count": self._count_tests(exp_path),
            "status": self._detect_status(exp_path),
        }

        # Enrich with core ExperimentSummary data when available
        summary_data = self._load_experiment_summary_json(exp_path)
        if summary_data:
            detail["core_summary"] = summary_data
            tests_info = summary_data.get("tests", {})
            if isinstance(tests_info, dict):
                detail["test_count"] = tests_info.get("total", detail["test_count"])
            detail["status"] = summary_data.get("status", detail["status"])

        if not summary_data:
            # Fallback: compute summary on-the-fly from logs/outputs
            computed = self.get_experiment_summary(str(exp_path))
            if computed:
                detail["core_summary"] = computed
                tests_info = computed.get("tests", {})
                if isinstance(tests_info, dict):
                    detail["test_count"] = tests_info.get("total", detail["test_count"])
                detail["status"] = computed.get("status", detail["status"])

        detail["log_content"] = self._read_log(exp_path)
        detail["report_content"] = self._read_report(exp_path)
        detail["artifacts"] = self._list_artifacts(exp_path)
        return detail

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

    _MAX_ARTIFACT_FILES = 500

    def _list_artifacts(self, exp_dir: Path) -> list[dict[str, str]]:
        """List downloadable artifacts organized by test directory.

        Caps results at ``_MAX_ARTIFACT_FILES`` to avoid excessive memory
        use on large experiment outputs.
        """
        artifacts = []
        artifact_exts = {".pcap", ".json", ".csv", ".yaml", ".yml", ".log"}
        matching = (
            f for f in exp_dir.rglob("*") if f.is_file() and f.suffix in artifact_exts
        )
        for f in itertools.islice(matching, self._MAX_ARTIFACT_FILES):
            try:
                rel = f.relative_to(exp_dir)
                test_name = rel.parts[0] if len(rel.parts) > 1 else ""
            except ValueError:
                rel = Path(f.name)
                test_name = ""
            artifacts.append({"name": f.name, "path": str(rel), "test_name": test_name})
        if len(artifacts) == self._MAX_ARTIFACT_FILES:
            logger.warning(
                "Artifact listing for %s capped at %d files",
                exp_dir,
                self._MAX_ARTIFACT_FILES,
            )
        return artifacts
