"""Pytest plugin for collecting test session metrics."""

import time
from pathlib import Path
from typing import Dict, Optional

import defusedxml.ElementTree as ET
import pytest

from panther.builder_metrics.core import flush, record
from panther.builder_metrics.resource_sampler import ResourceSampler


class PantherMetricsPlugin:
    """Pytest plugin for collecting metrics during test sessions."""

    def __init__(self):
        """Initialize metrics plugin with default values."""
        self.session_start_time: Optional[float] = None
        self.resource_sampler: Optional[ResourceSampler] = None
        self.test_results: Dict[str, int] = {
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "errors": 0,
        }

    def pytest_sessionstart(self, session: pytest.Session) -> None:
        """Called after the Session object has been created."""
        self.session_start_time = time.perf_counter()

        # Start resource monitoring
        self.resource_sampler = ResourceSampler(interval=1.0)
        self.resource_sampler.start()

    def pytest_runtest_logreport(self, report: pytest.TestReport) -> None:
        """Called for each phase of test execution."""
        # Only count final outcomes (call phase)
        if report.when == "call":
            if report.passed:
                self.test_results["passed"] += 1
            elif report.failed:
                self.test_results["failed"] += 1
            elif report.skipped:
                self.test_results["skipped"] += 1
        elif report.when in ("setup", "teardown") and report.failed:
            self.test_results["errors"] += 1

    def pytest_sessionfinish(self, session: pytest.Session) -> None:
        """Called after whole test run finished."""
        if self.session_start_time is None:
            return

        # Calculate total test time
        total_seconds = time.perf_counter() - self.session_start_time

        # Stop resource monitoring and get metrics
        resource_metrics = {}
        if self.resource_sampler:
            resource_metrics = self.resource_sampler.stop()

        # Count total test items
        total_items = sum(self.test_results.values())

        # Record basic test metrics
        record("pytest.total_seconds", total_seconds, {"stage": "tests"})
        record("pytest.item_count", float(total_items), {"stage": "tests"})
        record("pytest.passed", float(self.test_results["passed"]), {"stage": "tests"})
        record("pytest.failed", float(self.test_results["failed"]), {"stage": "tests"})
        record(
            "pytest.skipped", float(self.test_results["skipped"]), {"stage": "tests"}
        )
        record("pytest.errors", float(self.test_results["errors"]), {"stage": "tests"})

        # Record resource metrics
        for metric_name, value in resource_metrics.items():
            record(metric_name, value, {"stage": "tests"})

        # Try to get coverage information
        coverage_pct = self._get_coverage_percentage()
        if coverage_pct is not None:
            record("pytest.coverage_pct", coverage_pct, {"stage": "tests"})

        # Flush all metrics
        extra_data = {
            "test_results": self.test_results.copy(),
            "session_duration": total_seconds,
        }
        flush("tests", extra_data)

    def _get_coverage_percentage(self) -> Optional[float]:
        """Extract coverage percentage from coverage reports."""
        # Try to find coverage.xml file
        project_root = Path.cwd()
        coverage_files = [
            project_root / "coverage.xml",
            project_root / "htmlcov" / "coverage.xml",
            project_root / ".coverage.xml",
        ]

        for coverage_file in coverage_files:
            if coverage_file.exists():
                try:
                    return self._parse_coverage_xml(coverage_file)
                except Exception:
                    continue

        # Try to get from pytest-cov plugin if available
        return None

    def _parse_coverage_xml(self, coverage_file: Path) -> Optional[float]:
        """Parse coverage percentage from coverage.xml file."""
        try:
            tree = ET.parse(coverage_file)
            root = tree.getroot()

            # Look for coverage element with line-rate attribute
            coverage_elem = root.find("coverage")
            if coverage_elem is not None:
                line_rate = coverage_elem.get("line-rate")
                if line_rate:
                    return float(line_rate) * 100

            # Alternative: look for package/class elements
            for package in root.findall(".//package"):
                line_rate = package.get("line-rate")
                if line_rate:
                    return float(line_rate) * 100

        except (ET.ParseError, ValueError, TypeError):
            pass

        return None


def pytest_configure(config: pytest.Config) -> None:
    """Register the metrics plugin."""
    if not hasattr(config, "_panther_metrics_plugin"):
        plugin = PantherMetricsPlugin()
        config.pluginmanager.register(plugin, "panther_metrics")
        config._panther_metrics_plugin = plugin


def pytest_unconfigure(config: pytest.Config) -> None:
    """Unregister the metrics plugin."""
    plugin = getattr(config, "_panther_metrics_plugin", None)
    if plugin:
        config.pluginmanager.unregister(plugin)
