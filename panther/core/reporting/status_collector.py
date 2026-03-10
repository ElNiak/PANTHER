"""Status collector for aggregating experiment and test results.

This module provides functionality to collect and aggregate test results,
execution times, failure information, and resource usage from experiment outputs.
"""

import json
import logging
import re
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Pattern to strip ANSI escape sequences from log content
_ANSI_ESCAPE = re.compile(r"\x1b\[[0-9;]*m")


class TestStatus(Enum):
    """Test execution status."""

    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    TIMEOUT = "timeout"
    INTERRUPTED = "interrupted"
    UNKNOWN = "unknown"


class ExperimentStatus(Enum):
    """Overall experiment status."""

    COMPLETED = "completed"
    FAILED = "failed"
    INTERRUPTED = "interrupted"
    TIMEOUT = "timeout"
    UNKNOWN = "unknown"


@dataclass
class TestResult:
    """Individual test result information."""

    name: str
    status: TestStatus
    duration: float
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    error_message: Optional[str] = None
    logs_path: Optional[str] = None
    fast_fail_triggered: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "name": self.name,
            "status": self.status.value,
            "duration": self.duration,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "error_message": self.error_message,
            "logs_path": self.logs_path,
            "fast_fail_triggered": self.fast_fail_triggered,
        }


@dataclass
class FastFailInfo:
    """Fast-fail system information."""

    enabled: bool
    test_level: bool = False
    triggered: bool = False
    reason: Optional[str] = None
    error_category: Optional[str] = None
    termination_time: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "enabled": self.enabled,
            "test_level": self.test_level,
            "triggered": self.triggered,
            "reason": self.reason,
            "error_category": self.error_category,
            "termination_time": (
                self.termination_time.isoformat() if self.termination_time else None
            ),
        }


@dataclass
class ResourceUsage:
    """Resource usage information."""

    peak_memory_mb: Optional[float] = None
    disk_usage_mb: Optional[float] = None
    docker_images_created: Optional[int] = None
    total_log_size_mb: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return asdict(self)


@dataclass
class ServiceHealthSummary:
    """Per-service health info for reporting."""

    service_name: str
    service_type: str
    status: str  # "healthy", "degraded", "failed", "unknown"
    exit_code: Optional[int] = None
    crashed: bool = False
    compilation_succeeded: bool = True
    phases_completed: Optional[Dict[str, bool]] = None
    error_summary: Optional[str] = None
    output_completeness: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return asdict(self)


@dataclass
class ExperimentSummary:
    """Complete experiment summary."""

    experiment_id: str
    status: ExperimentStatus
    start_time: Optional[datetime]
    end_time: Optional[datetime]
    duration: Optional[timedelta]
    configuration_file: Optional[str]
    tests: List[TestResult]
    fast_fail: FastFailInfo
    resources: ResourceUsage
    services: Optional[List[ServiceHealthSummary]] = None

    @property
    def total_tests(self) -> int:
        """Total number of tests."""
        return len(self.tests)

    @property
    def passed_tests(self) -> int:
        """Number of passed tests."""
        return len([t for t in self.tests if t.status == TestStatus.PASSED])

    @property
    def failed_tests(self) -> int:
        """Number of failed tests."""
        return len([t for t in self.tests if t.status == TestStatus.FAILED])

    @property
    def skipped_tests(self) -> int:
        """Number of skipped tests."""
        return len([t for t in self.tests if t.status == TestStatus.SKIPPED])

    @property
    def timeout_tests(self) -> int:
        """Number of timed-out tests."""
        return len([t for t in self.tests if t.status == TestStatus.TIMEOUT])

    @property
    def interrupted_tests(self) -> int:
        """Number of interrupted tests."""
        return len([t for t in self.tests if t.status == TestStatus.INTERRUPTED])

    @property
    def unknown_tests(self) -> int:
        """Number of tests with unknown status."""
        return len([t for t in self.tests if t.status == TestStatus.UNKNOWN])

    @property
    def success_rate(self) -> float:
        """Success rate percentage."""
        if self.total_tests == 0:
            return 0.0
        return (self.passed_tests / self.total_tests) * 100

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "experiment_id": self.experiment_id,
            "status": self.status.value,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "duration_seconds": (
                self.duration.total_seconds() if self.duration else None
            ),
            "configuration_file": self.configuration_file,
            "tests": {
                "total": self.total_tests,
                "passed": self.passed_tests,
                "failed": self.failed_tests,
                "skipped": self.skipped_tests,
                "timeout": self.timeout_tests,
                "interrupted": self.interrupted_tests,
                "unknown": self.unknown_tests,
                "success_rate": self.success_rate,
                "results": [test.to_dict() for test in self.tests],
            },
            "fast_fail": self.fast_fail.to_dict(),
            "resources": self.resources.to_dict(),
            "services": ([s.to_dict() for s in self.services] if self.services else []),
        }


class StatusCollector:
    """Collects and aggregates experiment and test status information."""

    def __init__(self, experiment_dir: Path):
        """Initialize status collector.

        Args:
            experiment_dir: Path to experiment output directory
        """
        self.experiment_dir = Path(experiment_dir)
        self.logger = logging.getLogger(__name__)

    def collect_experiment_summary(self) -> ExperimentSummary:
        """Collect complete experiment summary.

        Returns:
            ExperimentSummary: Complete experiment information
        """
        experiment_id = self.experiment_dir.name

        # Extract experiment-level information
        experiment_info = self._extract_experiment_info()
        fast_fail_info = self._extract_fast_fail_info()
        resource_usage = self._extract_resource_usage()

        # Collect test results
        test_results = self._collect_test_results()

        # Extract service health from analysis artifacts
        service_health = self._extract_service_health()

        # Aggregate test-level fast_fail into experiment-level
        if not fast_fail_info.triggered:
            for test in test_results:
                if test.fast_fail_triggered:
                    fast_fail_info.triggered = True
                    fast_fail_info.reason = (
                        fast_fail_info.reason
                        or f"Fast-fail triggered by test: {test.name}"
                    )
                    break

        # Determine overall experiment status
        experiment_status = self._determine_experiment_status(
            test_results, fast_fail_info
        )

        return ExperimentSummary(
            experiment_id=experiment_id,
            status=experiment_status,
            start_time=experiment_info.get("start_time"),
            end_time=experiment_info.get("end_time"),
            duration=experiment_info.get("duration"),
            configuration_file=experiment_info.get("config_file"),
            tests=test_results,
            fast_fail=fast_fail_info,
            resources=resource_usage,
            services=service_health if service_health else None,
        )

    def _extract_experiment_info(self) -> Dict[str, Any]:
        """Extract experiment-level information from logs."""
        info = {}

        # Parse experiment.log for timing and configuration info
        experiment_log = self.experiment_dir / "experiment.log"
        if experiment_log.exists():
            try:
                with open(experiment_log, "r", encoding="utf-8") as f:
                    content = f.read()

                # Extract start time (first log entry)
                start_match = re.search(
                    r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})", content
                )
                if start_match:
                    info["start_time"] = datetime.strptime(
                        start_match.group(1), "%Y-%m-%d %H:%M:%S"
                    )

                # Extract configuration file
                config_match = re.search(
                    r"(?:Loading|Using|Config(?:uration)?)[:\s]+([^\s]+\.ya?ml)",
                    content,
                )
                if config_match:
                    info["config_file"] = config_match.group(1)
                elif re.search(r"experiment_config\.yaml", content):
                    info["config_file"] = "experiment_config.yaml"

                # Extract end time (last log entry)
                lines = content.strip().split("\n")
                if lines:
                    last_line = lines[-1]
                    end_match = re.search(
                        r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})", last_line
                    )
                    if end_match:
                        info["end_time"] = datetime.strptime(
                            end_match.group(1), "%Y-%m-%d %H:%M:%S"
                        )

                # Calculate duration
                if "start_time" in info and "end_time" in info:
                    info["duration"] = info["end_time"] - info["start_time"]
                elif "start_time" in info:
                    # Fallback: use file modification time as approximate end
                    try:
                        mtime = datetime.fromtimestamp(experiment_log.stat().st_mtime)
                        info["end_time"] = mtime
                        info["duration"] = mtime - info["start_time"]
                    except OSError:
                        pass

            except Exception as e:
                self.logger.warning(f"Failed to parse experiment.log: {e}")

        # Fallback: check if config file exists in experiment directory
        if "config_file" not in info:
            for name in [
                "experiment_config.yaml",
                "experiment_config.yml",
                "config.yaml",
            ]:
                config_path = self.experiment_dir / name
                if config_path.exists():
                    info["config_file"] = str(config_path)
                    break

        return info

    def _extract_fast_fail_info(self) -> FastFailInfo:
        """Extract fast-fail system information."""
        fast_fail_info = FastFailInfo(enabled=False)

        # Check experiment.log for fast-fail configuration
        experiment_log = self.experiment_dir / "experiment.log"
        if experiment_log.exists():
            try:
                with open(experiment_log, "r", encoding="utf-8") as f:
                    content = f.read()

                # Look for fast-fail configuration
                if "fast_fail(enabled=True" in content:
                    fast_fail_info.enabled = True
                elif "fast_fail(enabled=False" in content:
                    fast_fail_info.enabled = False

                # Check for test_level control
                if "test_level=True" in content or "test_level=true" in content:
                    fast_fail_info.test_level = True

                # Look for fast-fail termination
                termination_patterns = [
                    r"Critical error, terminating experiment",
                    r"Error cascade detected",
                    r"Fast-fail terminating",
                    r"Experiment terminated due to fast-fail",
                ]

                for pattern in termination_patterns:
                    match = re.search(pattern, content, re.IGNORECASE)
                    if match:
                        fast_fail_info.triggered = True
                        fast_fail_info.reason = match.group(0)
                        break

                # Look for error categories
                category_patterns = [
                    r"DOCKER_BUILD",
                    r"SERVICE_START",
                    r"NETWORK_SETUP",
                    r"TIMEOUT",
                    r"RESOURCE",
                    r"CASCADE",
                ]

                for category in category_patterns:
                    if category in content:
                        fast_fail_info.error_category = category
                        break

            except Exception as e:
                self.logger.warning(f"Failed to extract fast-fail info: {e}")

        # Fallback: check experiment_config.yaml (more reliable than log parsing)
        config_file = self.experiment_dir / "experiment_config.yaml"
        if config_file.exists():
            try:
                import yaml

                with open(config_file, "r", encoding="utf-8") as f:
                    config = yaml.safe_load(f)
                ff_config = config.get("fast_fail", {}) if config else {}
                if isinstance(ff_config, dict):
                    if ff_config.get("enabled"):
                        fast_fail_info.enabled = True
                    if ff_config.get("test_level"):
                        fast_fail_info.test_level = True
            except Exception as e:
                self.logger.warning("Failed to parse config YAML for fast-fail: %s", e)

        return fast_fail_info

    def _extract_resource_usage(self) -> ResourceUsage:
        """Extract resource usage information."""
        resources = ResourceUsage()

        try:
            # Calculate total log size
            total_size = 0
            for log_file in self.experiment_dir.rglob("*.log"):
                try:
                    total_size += log_file.stat().st_size
                except (OSError, FileNotFoundError):
                    continue

            resources.total_log_size_mb = total_size / (1024 * 1024)

            # Check for metrics files
            metrics_files = list(self.experiment_dir.rglob("metrics*.json"))
            if metrics_files:
                for metrics_file in metrics_files:
                    try:
                        with open(metrics_file, "r", encoding="utf-8") as f:
                            metrics_data = json.load(f)

                        # Extract memory usage if available
                        # Try multiple formats: direct, resource_metrics, summary
                        memory_mb = None
                        if "memory" in metrics_data:
                            memory_mb = metrics_data["memory"].get("peak_mb")
                        if not memory_mb and "resource_metrics" in metrics_data:
                            rm = metrics_data["resource_metrics"]
                            if isinstance(rm, dict):
                                mem_usage = rm.get("memory_usage", {})
                                memory_mb = mem_usage.get("peak")
                        if memory_mb and (
                            not resources.peak_memory_mb
                            or memory_mb > resources.peak_memory_mb
                        ):
                            resources.peak_memory_mb = memory_mb

                        # Extract disk usage if available
                        disk_mb = None
                        if "disk" in metrics_data:
                            disk_mb = metrics_data["disk"].get("used_mb")
                        if not disk_mb and "resource_metrics" in metrics_data:
                            rm = metrics_data["resource_metrics"]
                            if isinstance(rm, dict):
                                disk_mb = rm.get("disk_usage_mb")
                        if disk_mb and (
                            not resources.disk_usage_mb
                            or disk_mb > resources.disk_usage_mb
                        ):
                            resources.disk_usage_mb = disk_mb

                    except (json.JSONDecodeError, OSError) as e:
                        self.logger.debug(
                            f"Failed to parse metrics file {metrics_file}: {e}"
                        )

            # Count Docker images (docker-compose files indicate Docker usage)
            docker_compose_files = list(
                self.experiment_dir.rglob("docker-compose*.yml")
            )
            if docker_compose_files:
                resources.docker_images_created = len(docker_compose_files)

        except Exception as e:
            self.logger.warning(f"Failed to extract resource usage: {e}")

        return resources

    def _collect_test_results(self) -> List[TestResult]:
        """Collect results for all tests in the experiment."""
        test_results = []

        # Find all test directories (typically named after tests)
        test_dirs = [
            d
            for d in self.experiment_dir.iterdir()
            if d.is_dir() and d.name not in ["logs", "metrics", "outputs"]
        ]

        for test_dir in test_dirs:
            test_result = self._extract_test_result(test_dir)
            if test_result:
                test_results.append(test_result)

        return test_results

    def _extract_test_result(self, test_dir: Path) -> Optional[TestResult]:
        """Extract result information for a single test."""
        test_name = test_dir.name
        test_log = test_dir / "test.log"

        if not test_log.exists():
            return TestResult(
                name=test_name,
                status=TestStatus.UNKNOWN,
                duration=0.0,
                logs_path=str(test_dir.relative_to(self.experiment_dir)),
            )

        try:
            with open(test_log, "r", encoding="utf-8") as f:
                content = f.read()

            # Extract timing information
            start_time, end_time, duration = self._extract_test_timing(content)

            # Determine test status
            status = self._determine_test_status(content, test_dir)

            # Extract error message if failed
            error_message = None
            if status in [
                TestStatus.FAILED,
                TestStatus.TIMEOUT,
                TestStatus.INTERRUPTED,
            ]:
                error_message = self._extract_error_message(content)

            # Check if fast-fail was triggered for this test
            fast_fail_patterns = [
                "fast-fail triggered",
                "fast_fail(triggered=true",
                "terminating experiment due to",
                "fast-fail terminating",
            ]
            fast_fail_triggered = any(
                pattern in content.lower() for pattern in fast_fail_patterns
            )

            return TestResult(
                name=test_name,
                status=status,
                duration=duration,
                start_time=start_time,
                end_time=end_time,
                error_message=error_message,
                logs_path=str(test_dir.relative_to(self.experiment_dir)),
                fast_fail_triggered=fast_fail_triggered,
            )

        except Exception as e:
            self.logger.warning(f"Failed to extract test result for {test_name}: {e}")
            return TestResult(
                name=test_name,
                status=TestStatus.UNKNOWN,
                duration=0.0,
                logs_path=str(test_dir.relative_to(self.experiment_dir)),
            )

    def _extract_test_timing(
        self, content: str
    ) -> Tuple[Optional[datetime], Optional[datetime], float]:
        """Extract timing information from test log content."""
        lines = content.strip().split("\n")
        start_time = None
        end_time = None
        duration = 0.0

        # Extract start time (first log entry)
        if lines:
            start_match = re.search(r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})", lines[0])
            if start_match:
                start_time = datetime.strptime(
                    start_match.group(1), "%Y-%m-%d %H:%M:%S"
                )

        # Extract end time (last log entry)
        if lines:
            end_match = re.search(r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})", lines[-1])
            if end_match:
                end_time = datetime.strptime(end_match.group(1), "%Y-%m-%d %H:%M:%S")

        # Calculate duration
        if start_time and end_time:
            duration = (end_time - start_time).total_seconds()

        return start_time, end_time, duration

    def _determine_test_status(self, content: str, test_dir: Path) -> TestStatus:
        """Determine test status from analysis results, log content, and directory structure."""
        # 1. Check analysis_results.json first (authoritative source)
        analysis_file = test_dir / "analysis" / "analysis_results.json"
        if analysis_file.exists():
            try:
                with open(analysis_file, "r", encoding="utf-8") as f:
                    analysis = json.load(f)
                has_any_result = False
                for _tester_name, tester_data in analysis.items():
                    results = tester_data if isinstance(tester_data, dict) else {}
                    # Check nested "results" key or top-level
                    result_data = results.get("results", results)
                    if result_data.get("passed") is False:
                        return TestStatus.FAILED
                    elif result_data.get("passed") is True:
                        has_any_result = True
                # Only return PASSED if all testers passed (none returned False)
                if has_any_result:
                    return TestStatus.PASSED
            except (json.JSONDecodeError, OSError, KeyError) as e:
                self.logger.warning(
                    "analysis_results.json at %s failed to parse: %s. "
                    "Falling back to keyword-based status detection.",
                    analysis_file,
                    e,
                )

        # 2. Fall back to keyword matching with specific patterns
        #    (Match log-level prefixed patterns, not bare words)
        content_lower = content.lower()

        failure_indicators = [
            "- error -",
            "- critical -",
            "explicitly failed:",
            "docker build failed",
            "service start failed",
            "port conflict",
        ]

        timeout_indicators = [
            "timed out",
            "timeout exceeded",
            "timeout: failed to run",
        ]

        if any(indicator in content_lower for indicator in timeout_indicators):
            return TestStatus.TIMEOUT

        if any(indicator in content_lower for indicator in failure_indicators):
            return TestStatus.FAILED

        # Check for success indicators
        success_indicators = [
            "test completed successfully",
            "execution completed successfully",
            "all tests passed",
        ]

        if any(indicator in content_lower for indicator in success_indicators):
            return TestStatus.PASSED

        # Check for interruption indicators
        interruption_indicators = [
            "experiment interrupted",
            "terminated by signal",
            "killed by signal",
            "aborted by user",
        ]

        if any(indicator in content_lower for indicator in interruption_indicators):
            return TestStatus.INTERRUPTED

        # 3. Check directory structure for additional clues
        logs_dir = test_dir / "logs"
        if logs_dir.exists():
            # If logs directory exists but is empty, likely failed early
            log_files = list(logs_dir.rglob("*.log"))
            if not log_files:
                return TestStatus.FAILED

            # Check for error files
            error_files = list(logs_dir.rglob("*.err.log"))
            if error_files:
                for error_file in error_files:
                    try:
                        if error_file.stat().st_size > 0:  # Non-empty error file
                            return TestStatus.FAILED
                    except OSError:
                        continue

        # If we can't determine status clearly, assume unknown
        return TestStatus.UNKNOWN

    def _extract_error_message(self, content: str) -> Optional[str]:
        """Extract error message from log content."""
        content = _ANSI_ESCAPE.sub("", content)
        lines = content.split("\n")

        # Look for lines containing error keywords
        error_keywords = ["ERROR", "CRITICAL", "Exception", "Failed", "failed"]

        for line in lines:
            if any(keyword in line for keyword in error_keywords):
                # Clean up the line (remove timestamps, log levels, etc.)
                cleaned_line = re.sub(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}", "", line)
                cleaned_line = re.sub(r"\[.*?\]", "", cleaned_line)
                cleaned_line = cleaned_line.strip(" -")

                if cleaned_line:
                    return cleaned_line[:200]  # Limit to 200 characters

        return None

    def _extract_service_health(self) -> List[ServiceHealthSummary]:
        """Extract service health from analysis/service_health.json files."""
        summaries: List[ServiceHealthSummary] = []

        # Find all test directories
        test_dirs = [
            d
            for d in self.experiment_dir.iterdir()
            if d.is_dir() and d.name not in ("logs", "metrics", "outputs")
        ]

        for test_dir in test_dirs:
            health_file = test_dir / "analysis" / "service_health.json"
            if not health_file.exists():
                continue
            try:
                with open(health_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for entry in data:
                    summaries.append(
                        ServiceHealthSummary(
                            service_name=entry.get("service_name", "unknown"),
                            service_type=entry.get("service_type", "unknown"),
                            status=entry.get("status", "unknown"),
                            exit_code=entry.get("exit_code"),
                            crashed=entry.get("crashed", False),
                            compilation_succeeded=entry.get(
                                "compilation_succeeded", True
                            ),
                            phases_completed=entry.get("phases_completed"),
                            error_summary=entry.get("error_summary"),
                            output_completeness=entry.get("output_completeness", 0.0),
                        )
                    )
            except (json.JSONDecodeError, OSError, KeyError) as e:
                self.logger.warning(
                    "Failed to parse service health from %s: %s", health_file, e
                )

        return summaries

    def _determine_experiment_status(
        self, test_results: List[TestResult], fast_fail_info: FastFailInfo
    ) -> ExperimentStatus:
        """Determine overall experiment status."""
        if fast_fail_info.triggered:
            return ExperimentStatus.FAILED

        if not test_results:
            # Check experiment log for plugin failure or early termination
            experiment_log = self.experiment_dir / "experiment.log"
            if experiment_log.exists():
                try:
                    with open(experiment_log, "r", encoding="utf-8") as f:
                        content = f.read().lower()
                    failure_indicators = [
                        "plugin validation failed",
                        "plugin loading failed",
                        "docker build failed",
                        "service start failed",
                        "initialization failed",
                        "critical error",
                        "experiment failed",
                        "finished_early",
                    ]
                    if any(ind in content for ind in failure_indicators):
                        return ExperimentStatus.FAILED
                except OSError:
                    pass
            return ExperimentStatus.UNKNOWN

        failed_tests = [t for t in test_results if t.status == TestStatus.FAILED]
        timeout_tests = [t for t in test_results if t.status == TestStatus.TIMEOUT]
        interrupted_tests = [
            t for t in test_results if t.status == TestStatus.INTERRUPTED
        ]

        if interrupted_tests:
            return ExperimentStatus.INTERRUPTED

        if timeout_tests:
            return ExperimentStatus.TIMEOUT

        if failed_tests:
            return ExperimentStatus.FAILED

        # Check if all tests passed
        passed_tests = [t for t in test_results if t.status == TestStatus.PASSED]
        if passed_tests and len(passed_tests) == len(test_results):
            return ExperimentStatus.COMPLETED

        return ExperimentStatus.UNKNOWN
