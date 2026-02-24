"""Tests for Bug #8: StatusCollector improvements.

Tests cover:
- _determine_test_status keyword detection (timeout, interrupted, passed, failed)
- _determine_experiment_status aggregation logic
- Fast-fail detection from log content
- Resource usage extraction from metrics JSON files
- ExperimentSummary success_rate calculation
"""

import json

import pytest

pytestmark = [pytest.mark.unit]

from panther.core.reporting.status_collector import (
    ExperimentStatus,
    ExperimentSummary,
    FastFailInfo,
    ResourceUsage,
    StatusCollector,
    TestResult,
    TestStatus,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write_test_log(test_dir, content):
    """Write a test.log file inside a test directory."""
    test_dir.mkdir(parents=True, exist_ok=True)
    (test_dir / "test.log").write_text(content)


def _make_collector(tmp_path):
    """Create a StatusCollector pointing at a temporary experiment dir."""
    return StatusCollector(experiment_dir=tmp_path)


# ---------------------------------------------------------------------------
# TestDetermineTestStatus
# ---------------------------------------------------------------------------


class TestDetermineTestStatus:
    """Verify _determine_test_status correctly classifies log content."""

    def test_timeout_from_timed_out(self, tmp_path):
        test_dir = tmp_path / "test1"
        _write_test_log(
            test_dir, "2024-01-01 00:00:00 Service timed out waiting for port"
        )
        collector = _make_collector(tmp_path)
        status = collector._determine_test_status(
            (test_dir / "test.log").read_text(), test_dir
        )
        assert status == TestStatus.TIMEOUT

    def test_timeout_exceeded(self, tmp_path):
        test_dir = tmp_path / "test1"
        _write_test_log(test_dir, "2024-01-01 00:00:00 timeout exceeded for service")
        collector = _make_collector(tmp_path)
        status = collector._determine_test_status(
            (test_dir / "test.log").read_text(), test_dir
        )
        assert status == TestStatus.TIMEOUT

    @pytest.mark.parametrize(
        "keyword",
        [
            "experiment interrupted by user",
            "terminated by signal SIGTERM",
            "killed by signal SIGKILL",
            "aborted by user",
        ],
    )
    def test_interrupted_keywords(self, tmp_path, keyword):
        test_dir = tmp_path / "test1"
        _write_test_log(test_dir, f"2024-01-01 00:00:00 {keyword}")
        collector = _make_collector(tmp_path)
        status = collector._determine_test_status(
            (test_dir / "test.log").read_text(), test_dir
        )
        assert status == TestStatus.INTERRUPTED

    def test_unknown_when_no_indicators(self, tmp_path):
        test_dir = tmp_path / "test1"
        _write_test_log(
            test_dir, "2024-01-01 00:00:00 - INFO - Nothing special happened"
        )
        collector = _make_collector(tmp_path)
        status = collector._determine_test_status(
            (test_dir / "test.log").read_text(), test_dir
        )
        assert status == TestStatus.UNKNOWN

    @pytest.mark.parametrize(
        "keyword",
        [
            "test completed successfully",
            "execution completed successfully",
            "all tests passed",
        ],
    )
    def test_passed_from_success_keywords(self, tmp_path, keyword):
        test_dir = tmp_path / "test1"
        _write_test_log(test_dir, f"2024-01-01 00:00:00 {keyword}")
        collector = _make_collector(tmp_path)
        status = collector._determine_test_status(
            (test_dir / "test.log").read_text(), test_dir
        )
        assert status == TestStatus.PASSED

    def test_failure_from_error_indicator(self, tmp_path):
        test_dir = tmp_path / "test1"
        _write_test_log(test_dir, "2024-01-01 00:00:00 - ERROR - Something went wrong")
        collector = _make_collector(tmp_path)
        status = collector._determine_test_status(
            (test_dir / "test.log").read_text(), test_dir
        )
        assert status == TestStatus.FAILED

    def test_docker_build_failed_indicator(self, tmp_path):
        test_dir = tmp_path / "test1"
        _write_test_log(test_dir, "2024-01-01 00:00:00 docker build failed for service")
        collector = _make_collector(tmp_path)
        status = collector._determine_test_status(
            (test_dir / "test.log").read_text(), test_dir
        )
        assert status == TestStatus.FAILED

    def test_analysis_results_passed_overrides_keywords(self, tmp_path):
        """analysis_results.json is the authoritative source."""
        test_dir = tmp_path / "test1"
        _write_test_log(test_dir, "2024-01-01 00:00:00 - ERROR - something")
        analysis_dir = test_dir / "analysis"
        analysis_dir.mkdir(parents=True)
        analysis_data = {"ivy": {"results": {"passed": True}}}
        (analysis_dir / "analysis_results.json").write_text(json.dumps(analysis_data))

        collector = _make_collector(tmp_path)
        status = collector._determine_test_status(
            (test_dir / "test.log").read_text(), test_dir
        )
        assert status == TestStatus.PASSED


# ---------------------------------------------------------------------------
# TestDetermineExperimentStatus
# ---------------------------------------------------------------------------


class TestDetermineExperimentStatus:
    """Verify _determine_experiment_status aggregation logic."""

    def _make_test_result(self, status):
        return TestResult(name="t", status=status, duration=1.0)

    def test_completed_when_all_passed(self, tmp_path):
        collector = _make_collector(tmp_path)
        results = [self._make_test_result(TestStatus.PASSED) for _ in range(3)]
        ff = FastFailInfo(enabled=False)
        assert (
            collector._determine_experiment_status(results, ff)
            == ExperimentStatus.COMPLETED
        )

    def test_failed_when_any_failed(self, tmp_path):
        collector = _make_collector(tmp_path)
        results = [
            self._make_test_result(TestStatus.PASSED),
            self._make_test_result(TestStatus.FAILED),
        ]
        ff = FastFailInfo(enabled=False)
        assert (
            collector._determine_experiment_status(results, ff)
            == ExperimentStatus.FAILED
        )

    def test_timeout_when_timeout_tests_exist(self, tmp_path):
        collector = _make_collector(tmp_path)
        results = [
            self._make_test_result(TestStatus.PASSED),
            self._make_test_result(TestStatus.TIMEOUT),
        ]
        ff = FastFailInfo(enabled=False)
        assert (
            collector._determine_experiment_status(results, ff)
            == ExperimentStatus.TIMEOUT
        )

    def test_interrupted_when_interrupted_tests(self, tmp_path):
        collector = _make_collector(tmp_path)
        results = [
            self._make_test_result(TestStatus.PASSED),
            self._make_test_result(TestStatus.INTERRUPTED),
        ]
        ff = FastFailInfo(enabled=False)
        assert (
            collector._determine_experiment_status(results, ff)
            == ExperimentStatus.INTERRUPTED
        )

    def test_unknown_when_no_tests(self, tmp_path):
        collector = _make_collector(tmp_path)
        ff = FastFailInfo(enabled=False)
        assert (
            collector._determine_experiment_status([], ff) == ExperimentStatus.UNKNOWN
        )

    def test_fast_fail_overrides_experiment_status(self, tmp_path):
        collector = _make_collector(tmp_path)
        results = [self._make_test_result(TestStatus.PASSED)]
        ff = FastFailInfo(enabled=True, triggered=True, reason="Critical error")
        assert (
            collector._determine_experiment_status(results, ff)
            == ExperimentStatus.FAILED
        )


# ---------------------------------------------------------------------------
# TestFastFailDetection
# ---------------------------------------------------------------------------


class TestFastFailDetection:
    """Verify _extract_fast_fail_info parses fast-fail patterns from logs."""

    @pytest.mark.parametrize(
        "pattern",
        [
            "Critical error, terminating experiment",
            "Error cascade detected in services",
            "Fast-fail terminating experiment now",
            "Experiment terminated due to fast-fail policy",
        ],
    )
    def test_termination_patterns(self, tmp_path, pattern):
        (tmp_path / "experiment.log").write_text(
            f"2024-01-01 00:00:00 fast_fail(enabled=True)\n"
            f"2024-01-01 00:01:00 {pattern}\n"
        )
        collector = _make_collector(tmp_path)
        ff = collector._extract_fast_fail_info()
        assert ff.enabled is True
        assert ff.triggered is True

    def test_disabled_by_default(self, tmp_path):
        (tmp_path / "experiment.log").write_text(
            "2024-01-01 00:00:00 fast_fail(enabled=False)\n"
            "2024-01-01 00:01:00 all good\n"
        )
        collector = _make_collector(tmp_path)
        ff = collector._extract_fast_fail_info()
        assert ff.enabled is False
        assert ff.triggered is False

    def test_no_experiment_log(self, tmp_path):
        collector = _make_collector(tmp_path)
        ff = collector._extract_fast_fail_info()
        assert ff.enabled is False
        assert ff.triggered is False


# ---------------------------------------------------------------------------
# TestResourceUsageExtraction
# ---------------------------------------------------------------------------


class TestResourceUsageExtraction:
    """Verify _extract_resource_usage parses metrics JSON and counts files."""

    def test_extracts_memory_from_metrics_json(self, tmp_path):
        metrics_data = {"memory": {"peak_mb": 512.5}}
        (tmp_path / "metrics.json").write_text(json.dumps(metrics_data))
        collector = _make_collector(tmp_path)
        resources = collector._extract_resource_usage()
        assert resources.peak_memory_mb == 512.5

    def test_extracts_memory_from_resource_metrics_format(self, tmp_path):
        metrics_data = {"resource_metrics": {"memory_usage": {"peak": 1024.0}}}
        (tmp_path / "metrics.json").write_text(json.dumps(metrics_data))
        collector = _make_collector(tmp_path)
        resources = collector._extract_resource_usage()
        assert resources.peak_memory_mb == 1024.0

    def test_handles_corrupted_metrics_json(self, tmp_path):
        (tmp_path / "metrics.json").write_text("{ invalid json !!!")
        collector = _make_collector(tmp_path)
        resources = collector._extract_resource_usage()
        assert resources.peak_memory_mb is None

    def test_counts_docker_compose_files(self, tmp_path):
        for i in range(3):
            (tmp_path / f"docker-compose-{i}.yml").write_text("version: '3'")
        collector = _make_collector(tmp_path)
        resources = collector._extract_resource_usage()
        assert resources.docker_images_created == 3


# ---------------------------------------------------------------------------
# TestExperimentSummary
# ---------------------------------------------------------------------------


class TestExperimentSummary:
    """Verify ExperimentSummary computed properties."""

    def _make_summary(self, tests):
        return ExperimentSummary(
            experiment_id="exp-1",
            status=ExperimentStatus.COMPLETED,
            start_time=None,
            end_time=None,
            duration=None,
            configuration_file=None,
            tests=tests,
            fast_fail=FastFailInfo(enabled=False),
            resources=ResourceUsage(),
        )

    def test_success_rate_calculation(self):
        tests = [
            TestResult(name="t1", status=TestStatus.PASSED, duration=1.0),
            TestResult(name="t2", status=TestStatus.PASSED, duration=1.0),
            TestResult(name="t3", status=TestStatus.FAILED, duration=1.0),
            TestResult(name="t4", status=TestStatus.TIMEOUT, duration=1.0),
        ]
        summary = self._make_summary(tests)
        assert summary.success_rate == 50.0
        assert summary.total_tests == 4
        assert summary.passed_tests == 2
        assert summary.failed_tests == 1
        assert summary.timeout_tests == 1

    def test_success_rate_zero_tests(self):
        summary = self._make_summary([])
        assert summary.success_rate == 0.0
        assert summary.total_tests == 0
