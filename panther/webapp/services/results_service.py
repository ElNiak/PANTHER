"""Service layer for browsing experiment results."""

import json
import logging
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)


class ResultsService:
    """Scans the outputs directory for past experiment results."""

    def __init__(self, output_dir: str = "outputs"):
        self.output_dir = Path(output_dir)

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
        if (exp_dir / "experiment_summary.json").exists():
            return "completed"
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

    def _read_log(self, exp_dir: Path) -> Optional[str]:
        """Read the main log file if it exists."""
        for pattern in ["*.log", "logs/*.log", "experiment.log"]:
            logs = list(exp_dir.glob(pattern))
            if logs:
                try:
                    # TODO: For very large logs, read_text() loads the
                    # entire file before slicing. Consider a tail-based
                    # approach (e.g. deque with maxlen) for multi-GB logs.
                    lines = logs[0].read_text().splitlines()
                    return "\n".join(lines[-500:])
                except OSError:
                    pass
        return None

    def _read_report(self, exp_dir: Path) -> Optional[str]:
        """Read the report markdown if it exists."""
        for name in ["report.md", "README.md", "summary.md"]:
            report = exp_dir / name
            if report.exists():
                try:
                    return report.read_text()
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
