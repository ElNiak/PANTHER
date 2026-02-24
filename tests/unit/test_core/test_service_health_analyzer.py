"""Tests for panther.core.outputs.service_health_analyzer."""

from pathlib import Path
from unittest.mock import Mock

import pytest

from panther.core.outputs.service_health_analyzer import (
    STANDARD_PHASES,
    ServiceHealth,
    ServiceHealthAnalyzer,
)


@pytest.fixture
def analyzer():
    return ServiceHealthAnalyzer()


@pytest.fixture
def service_log_dir(tmp_path):
    """Create a realistic service log directory structure."""
    log_dir = tmp_path / "picoquic"
    for phase in STANDARD_PHASES:
        (log_dir / phase).mkdir(parents=True)
    return log_dir


class TestServiceHealth:
    """Tests for the ServiceHealth dataclass."""

    def test_healthy_status(self):
        h = ServiceHealth(
            service_name="svc",
            service_type="iut",
            phases_completed={"runtime": True},
        )
        assert h.status == "healthy"

    def test_failed_on_crash(self):
        h = ServiceHealth(
            service_name="svc",
            service_type="iut",
            phases_completed={"runtime": True},
            crashed=True,
        )
        assert h.status == "failed"

    def test_failed_on_nonzero_exit(self):
        h = ServiceHealth(
            service_name="svc",
            service_type="iut",
            phases_completed={"runtime": True},
            exit_code=1,
        )
        assert h.status == "failed"

    def test_degraded_on_stderr_errors(self):
        h = ServiceHealth(
            service_name="svc",
            service_type="iut",
            phases_completed={"runtime": True},
            stderr_errors=["ERROR: something"],
        )
        assert h.status == "degraded"

    def test_unknown_when_no_phases(self):
        h = ServiceHealth(
            service_name="svc",
            service_type="iut",
            phases_completed={"runtime": False, "compile": False},
        )
        assert h.status == "unknown"

    def test_output_completeness(self):
        h = ServiceHealth(
            service_name="svc",
            service_type="iut",
            output_files_found=3,
            output_files_expected=6,
        )
        assert h.output_completeness == 0.5

    def test_output_completeness_zero_expected(self):
        h = ServiceHealth(
            service_name="svc",
            service_type="iut",
            output_files_found=0,
            output_files_expected=0,
        )
        assert h.output_completeness == 0.0

    def test_to_dict_includes_derived_fields(self):
        h = ServiceHealth(
            service_name="svc",
            service_type="iut",
            phases_completed={"runtime": True},
        )
        d = h.to_dict()
        assert d["status"] == "healthy"
        assert "output_completeness" in d


class TestServiceHealthAnalyzer:
    """Tests for the ServiceHealthAnalyzer class."""

    def test_nonexistent_log_dir(self, analyzer, tmp_path):
        result = analyzer.analyze_service("svc", "iut", tmp_path / "nonexistent")
        assert result.service_name == "svc"
        assert result.status == "unknown"

    def test_empty_phases(self, analyzer, service_log_dir):
        result = analyzer.analyze_service("svc", "iut", service_log_dir)
        # All phase dirs exist but are empty
        assert all(not v for v in result.phases_completed.values())
        assert result.compilation_succeeded  # No compile errors = success

    def test_phase_completeness_with_files(self, analyzer, service_log_dir):
        (service_log_dir / "runtime" / "stdout.log").write_text("output")
        (service_log_dir / "compile" / "stdout.log").write_text("compiling...")

        result = analyzer.analyze_service("svc", "iut", service_log_dir)

        assert result.phases_completed["runtime"] is True
        assert result.phases_completed["compile"] is True
        assert result.phases_completed["pre-compile"] is False
        assert result.phases_completed["test"] is False

    def test_compilation_failure_detected(self, analyzer, service_log_dir):
        (service_log_dir / "compile" / "stderr.log").write_text(
            "fatal error: file.h: No such file or directory\n"
            "compilation terminated.\n"
        )
        result = analyzer.analyze_service("svc", "iut", service_log_dir)
        assert result.compilation_succeeded is False

    def test_exit_code_extraction(self, analyzer, service_log_dir):
        (service_log_dir / "runtime" / "stdout.log").write_text(
            "Server started\nexit code: 42\n"
        )
        result = analyzer.analyze_service("svc", "iut", service_log_dir)
        assert result.exit_code == 42
        assert result.status == "failed"

    def test_crash_detection_sigsegv(self, analyzer, service_log_dir):
        (service_log_dir / "runtime" / "stderr.log").write_text(
            "Segmentation fault (core dumped)\n"
        )
        result = analyzer.analyze_service("svc", "iut", service_log_dir)
        assert result.crashed is True
        assert result.status == "failed"

    def test_stderr_errors_collected(self, analyzer, service_log_dir):
        (service_log_dir / "runtime" / "stderr.log").write_text(
            "INFO: Starting server\n"
            "ERROR: Connection refused\n"
            "INFO: Shutting down\n"
        )
        result = analyzer.analyze_service("svc", "iut", service_log_dir)
        assert len(result.stderr_errors) >= 1
        assert any("Connection refused" in e for e in result.stderr_errors)

    def test_log_size_calculation(self, analyzer, service_log_dir):
        content = "x" * 1000
        (service_log_dir / "runtime" / "stdout.log").write_text(content)
        (service_log_dir / "runtime" / "stderr.log").write_text(content)

        result = analyzer.analyze_service("svc", "iut", service_log_dir)
        assert result.log_size_bytes >= 2000

    def test_output_patterns_check(self, analyzer, service_log_dir):
        (service_log_dir / "runtime" / "trace.pcap").write_bytes(b"\x00")
        patterns = [("pcap", "*.pcap"), ("qlog", "*.qlog"), ("keys", "*keys.log")]

        result = analyzer.analyze_service("svc", "iut", service_log_dir, patterns)
        assert result.output_files_found == 1
        assert result.output_files_expected == 3
        assert result.has_output_artifacts is True

    def test_analyze_all_services(self, analyzer, tmp_path):
        # Create mock service managers
        sm1 = Mock()
        sm1.service_name = "server"
        sm1.get_output_patterns.return_value = []

        sm2 = Mock()
        sm2.service_name = "client"
        sm2.get_output_patterns.return_value = []

        # Create log dirs
        for name in ("server", "client"):
            log = tmp_path / name
            for phase in STANDARD_PHASES:
                (log / phase).mkdir(parents=True)
            (log / "runtime" / "stdout.log").write_text("ok")

        def get_log_dir(name):
            return tmp_path / name

        results = analyzer.analyze_all_services([sm1, sm2], get_log_dir)
        assert len(results) == 2
        assert results[0].service_name == "server"
        assert results[1].service_name == "client"

    def test_healthy_service_full(self, analyzer, service_log_dir):
        """A service with runtime output and no errors is healthy."""
        (service_log_dir / "compile" / "stdout.log").write_text("Build successful")
        (service_log_dir / "runtime" / "stdout.log").write_text("Server running")

        result = analyzer.analyze_service("svc", "iut", service_log_dir)
        assert result.status == "healthy"
        assert result.compilation_succeeded
        assert result.exit_code is None
        assert not result.crashed
