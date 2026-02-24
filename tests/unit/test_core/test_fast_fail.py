#!/usr/bin/env python3.10
"""Tests for the FastFailHandler using the real implementation.

Tests exercise the real FastFailHandler from
panther.core.exceptions.fast_fail, including error handling with
severity levels, cascade detection, error pattern analysis,
critical error checks, and history management.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from unittest.mock import patch

import pytest

from panther.core.exceptions.fast_fail import (
    AuthenticationException,
    CertificateException,
    ConfigurationException,
    CriticalAssertionException,
    DependencyException,
    DockerBuildException,
    DockerComposeException,
    ErrorCascadeException,
    ErrorCategory,
    ErrorSeverity,
    FastFailHandler,
    IvyCompilationException,
    NetworkSetupException,
    PantherException,
    PluginLoadException,
    PortConflictException,
    ResourceExhaustionException,
    ServiceStartException,
    TimeoutCascadeException,
)

pytestmark = [pytest.mark.unit, pytest.mark.fast_fail]


# ---------------------------------------------------------------------------
# PantherException hierarchy tests
# ---------------------------------------------------------------------------


class TestPantherException:
    """Test base PantherException and its attributes."""

    def test_basic_initialization(self):
        """PantherException stores severity, category, timestamp, and context."""
        exc = PantherException(
            "something broke",
            ErrorSeverity.MEDIUM,
            ErrorCategory.COMMAND_EXECUTION,
        )
        assert str(exc) == "something broke"
        assert exc.severity == ErrorSeverity.MEDIUM
        assert exc.category == ErrorCategory.COMMAND_EXECUTION
        assert isinstance(exc.timestamp, datetime)
        assert exc.context == {}

    def test_initialization_with_context(self):
        """PantherException stores arbitrary context dict."""
        ctx = {"host": "localhost", "port": 443}
        exc = PantherException(
            "details", ErrorSeverity.LOW, ErrorCategory.NETWORK_SETUP, context=ctx
        )
        assert exc.context == ctx

    def test_should_terminate_critical(self):
        """CRITICAL severity causes should_terminate to return True."""
        exc = PantherException("fatal", ErrorSeverity.CRITICAL, ErrorCategory.RESOURCE)
        assert exc.should_terminate() is True

    def test_should_terminate_non_critical(self):
        """Non-CRITICAL severities do not cause termination."""
        for sev in (ErrorSeverity.HIGH, ErrorSeverity.MEDIUM, ErrorSeverity.LOW):
            exc = PantherException("warn", sev, ErrorCategory.COMMAND_EXECUTION)
            assert exc.should_terminate() is False


class TestExceptionSubclasses:
    """Verify each PantherException subclass sets correct severity/category."""

    def test_docker_build_exception(self):
        exc = DockerBuildException("build fail", "myimg", "Dockerfile", "error log")
        assert exc.severity == ErrorSeverity.CRITICAL
        assert exc.category == ErrorCategory.DOCKER_BUILD
        assert exc.context["image_name"] == "myimg"
        assert exc.context["dockerfile"] == "Dockerfile"
        assert exc.context["build_error"] == "error log"

    def test_plugin_load_exception_default_severity(self):
        exc = PluginLoadException("load fail", "myplugin", "service")
        assert exc.severity == ErrorSeverity.HIGH
        assert exc.category == ErrorCategory.PLUGIN_LOAD
        assert exc.context["plugin_name"] == "myplugin"

    def test_plugin_load_exception_custom_severity(self):
        exc = PluginLoadException("warn", "p", "t", severity=ErrorSeverity.LOW)
        assert exc.severity == ErrorSeverity.LOW

    def test_service_start_exception(self):
        exc = ServiceStartException("start fail", "picoquic")
        assert exc.severity == ErrorSeverity.HIGH
        assert exc.category == ErrorCategory.SERVICE_START
        assert exc.context["service_name"] == "picoquic"

    def test_docker_compose_exception(self):
        exc = DockerComposeException("compose fail", "up -d", 1, "out", "err")
        assert exc.severity == ErrorSeverity.CRITICAL
        assert exc.category == ErrorCategory.DOCKER_RUNTIME
        assert exc.context["returncode"] == 1
        # stdout/stderr truncated to 500 chars
        assert exc.context["stdout"] == "out"
        assert exc.context["stderr"] == "err"

    def test_network_setup_exception(self):
        exc = NetworkSetupException("net fail", "bridge", "no interface")
        assert exc.severity == ErrorSeverity.CRITICAL
        assert exc.category == ErrorCategory.NETWORK_SETUP

    def test_port_conflict_exception(self):
        exc = PortConflictException("port taken", 8080, "webserver")
        assert exc.severity == ErrorSeverity.HIGH
        assert exc.category == ErrorCategory.NETWORK_SETUP
        assert exc.context["port"] == 8080

    def test_ivy_compilation_exception(self):
        exc = IvyCompilationException("compile fail", "test_quic", "error", 2)
        assert exc.severity == ErrorSeverity.CRITICAL
        assert exc.category == ErrorCategory.TEST_FRAMEWORK

    def test_resource_exhaustion_exception(self):
        exc = ResourceExhaustionException("no space", "disk", 100.0, 500.0)
        assert exc.severity == ErrorSeverity.CRITICAL
        assert exc.category == ErrorCategory.RESOURCE

    def test_certificate_exception(self):
        exc = CertificateException("cert fail", "/certs/ca.pem", "expired")
        assert exc.severity == ErrorSeverity.CRITICAL
        assert exc.category == ErrorCategory.SECURITY

    def test_configuration_exception(self):
        exc = ConfigurationException("bad config", "exp.yaml", "timeout", "negative")
        assert exc.severity == ErrorSeverity.HIGH
        assert exc.category == ErrorCategory.CONFIGURATION

    def test_timeout_cascade_exception(self):
        exc = TimeoutCascadeException("timeouts", 5, ["svc1", "svc2"])
        assert exc.severity == ErrorSeverity.HIGH
        assert exc.category == ErrorCategory.CASCADE

    def test_authentication_exception(self):
        exc = AuthenticationException("auth fail", "token", "registry")
        assert exc.severity == ErrorSeverity.HIGH
        assert exc.category == ErrorCategory.SECURITY

    def test_critical_assertion_exception(self):
        exc = CriticalAssertionException("assert fail", "equals", 42, 99)
        assert exc.severity == ErrorSeverity.HIGH
        assert exc.category == ErrorCategory.TEST_EXECUTION
        assert exc.context["expected"] == "42"
        assert exc.context["actual"] == "99"

    def test_dependency_exception(self):
        exc = DependencyException("dep fail", "numpy", "1.24", "1.20")
        assert exc.severity == ErrorSeverity.HIGH
        assert exc.category == ErrorCategory.DEPENDENCY
        assert exc.context["found_version"] == "1.20"

    def test_dependency_exception_not_found(self):
        exc = DependencyException("dep missing", "z3", "4.0")
        assert exc.context["found_version"] == "not found"

    def test_error_cascade_exception(self):
        exc = ErrorCascadeException("cascade", "timeout", 5, 3)
        assert exc.severity == ErrorSeverity.HIGH
        assert exc.category == ErrorCategory.CASCADE
        assert exc.context["error_count"] == 5
        assert exc.context["threshold"] == 3


# ---------------------------------------------------------------------------
# FastFailHandler tests
# ---------------------------------------------------------------------------


class TestFastFailHandlerInit:
    """Test FastFailHandler initialization and basic state."""

    def test_default_initialization(self, real_fast_fail_handler):
        """Handler starts with clean state and enabled."""
        h = real_fast_fail_handler
        assert h.enabled is True
        assert h.error_count == 0
        assert h.critical_error is None
        assert h.error_history == []
        assert isinstance(h.logger, logging.Logger)

    def test_disabled_handler(self):
        handler = FastFailHandler(enabled=False)
        assert handler.enabled is False

    def test_custom_logger(self):
        custom_logger = logging.getLogger("test.custom")
        handler = FastFailHandler(logger=custom_logger)
        assert handler.logger is custom_logger

    def test_default_cascade_thresholds(self, real_fast_fail_handler):
        """Handler has sensible default cascade thresholds."""
        h = real_fast_fail_handler
        assert h.cascade_thresholds[ErrorCategory.TIMEOUT] == 3
        assert h.cascade_thresholds[ErrorCategory.DOCKER_RUNTIME] == 2
        assert h.cascade_thresholds[ErrorCategory.SERVICE_START] == 3
        assert h.cascade_thresholds[ErrorCategory.NETWORK_SETUP] == 2
        assert h.cascade_thresholds[ErrorCategory.COMMAND_EXECUTION] == 5
        assert h.cascade_thresholds[ErrorCategory.TEST_EXECUTION] == 4


class TestHandleError:
    """Test handle_error() with different error types and severities."""

    def test_low_severity_continues(self, real_fast_fail_handler):
        """LOW severity errors return True (continue execution)."""
        err = PantherException(
            "minor", ErrorSeverity.LOW, ErrorCategory.COMMAND_EXECUTION
        )
        result = real_fast_fail_handler.handle_error(err)
        assert result is True
        assert real_fast_fail_handler.error_count == 1

    def test_medium_severity_continues(self, real_fast_fail_handler):
        """MEDIUM severity errors return True (continue execution)."""
        err = PantherException("warning", ErrorSeverity.MEDIUM, ErrorCategory.TIMEOUT)
        result = real_fast_fail_handler.handle_error(err)
        assert result is True

    def test_high_severity_stops_current_operation(self, real_fast_fail_handler):
        """HIGH severity errors return False (stop current operation)."""
        err = PantherException("bad", ErrorSeverity.HIGH, ErrorCategory.DOCKER_RUNTIME)
        result = real_fast_fail_handler.handle_error(err, raise_on_critical=False)
        assert result is False

    def test_critical_raises_by_default(self, real_fast_fail_handler):
        """CRITICAL errors are re-raised when raise_on_critical is True."""
        err = PantherException("fatal", ErrorSeverity.CRITICAL, ErrorCategory.RESOURCE)
        with pytest.raises(PantherException, match="fatal"):
            real_fast_fail_handler.handle_error(err)

    def test_critical_returns_false_when_not_raising(self, real_fast_fail_handler):
        """CRITICAL errors return False when raise_on_critical is False."""
        err = PantherException("fatal", ErrorSeverity.CRITICAL, ErrorCategory.RESOURCE)
        result = real_fast_fail_handler.handle_error(err, raise_on_critical=False)
        assert result is False

    def test_critical_error_stored(self, real_fast_fail_handler):
        """CRITICAL errors are stored on the handler for later retrieval."""
        err = PantherException("fatal", ErrorSeverity.CRITICAL, ErrorCategory.RESOURCE)
        real_fast_fail_handler.handle_error(err, raise_on_critical=False)
        assert real_fast_fail_handler.critical_error is err

    def test_disabled_handler_always_continues(self):
        """When disabled, handle_error always returns True regardless of severity."""
        handler = FastFailHandler(enabled=False)
        critical = PantherException(
            "fatal", ErrorSeverity.CRITICAL, ErrorCategory.RESOURCE
        )
        result = handler.handle_error(critical, raise_on_critical=False)
        # When disabled, returns True (continue) for everything
        assert result is True

    def test_regular_exception_wrapped(self, real_fast_fail_handler):
        """Non-PantherException errors are wrapped as MEDIUM/COMMAND_EXECUTION."""
        err = ValueError("raw python error")
        result = real_fast_fail_handler.handle_error(err)
        assert result is True  # MEDIUM severity => continue
        assert real_fast_fail_handler.error_count == 1
        # Stored in history as a PantherException wrapping the original
        _, stored = real_fast_fail_handler.error_history[0]
        assert isinstance(stored, PantherException)
        assert stored.category == ErrorCategory.COMMAND_EXECUTION
        assert stored.severity == ErrorSeverity.MEDIUM

    def test_error_history_grows(self, real_fast_fail_handler):
        """Each handle_error call appends to error_history."""
        for i in range(5):
            err = PantherException(
                f"error {i}", ErrorSeverity.LOW, ErrorCategory.COMMAND_EXECUTION
            )
            real_fast_fail_handler.handle_error(err)
        assert len(real_fast_fail_handler.error_history) == 5
        assert real_fast_fail_handler.error_count == 5

    def test_error_history_trimmed_at_100(self, real_fast_fail_handler):
        """Error history is trimmed to the last 100 entries."""
        for i in range(110):
            err = PantherException(
                f"e{i}", ErrorSeverity.LOW, ErrorCategory.COMMAND_EXECUTION
            )
            real_fast_fail_handler.handle_error(err)
        assert len(real_fast_fail_handler.error_history) <= 100
        assert real_fast_fail_handler.error_count == 110

    def test_handle_docker_build_exception(self, real_fast_fail_handler):
        """DockerBuildException (CRITICAL) is raised by handle_error."""
        err = DockerBuildException("build fail", "img", "Dockerfile")
        with pytest.raises(DockerBuildException):
            real_fast_fail_handler.handle_error(err)

    def test_handle_service_start_exception(self, real_fast_fail_handler):
        """ServiceStartException (HIGH) stops current operation without raising."""
        err = ServiceStartException("start fail", "picoquic")
        result = real_fast_fail_handler.handle_error(err, raise_on_critical=False)
        assert result is False


class TestCascadeDetection:
    """Test detect_cascade() and cascade-related behavior."""

    def test_no_cascade_below_threshold(self, real_fast_fail_handler):
        """No cascade when error count is below threshold."""
        err = PantherException("timeout", ErrorSeverity.MEDIUM, ErrorCategory.TIMEOUT)
        # Threshold for TIMEOUT is 3; add 2 errors (below threshold)
        real_fast_fail_handler.error_history.append((datetime.now(), err))
        real_fast_fail_handler.error_history.append((datetime.now(), err))
        result = real_fast_fail_handler.detect_cascade(err)
        assert result is None

    def test_cascade_at_threshold(self, real_fast_fail_handler):
        """Cascade detected when error count reaches threshold."""
        err = PantherException("timeout", ErrorSeverity.MEDIUM, ErrorCategory.TIMEOUT)
        # TIMEOUT threshold is 3; add 3 errors to history (including current)
        for _ in range(3):
            real_fast_fail_handler.error_history.append((datetime.now(), err))
        result = real_fast_fail_handler.detect_cascade(err)
        assert result is not None
        assert isinstance(result, ErrorCascadeException)
        assert result.category == ErrorCategory.CASCADE

    def test_cascade_only_same_category(self, real_fast_fail_handler):
        """Cascade detection only counts errors of the same category."""
        timeout_err = PantherException("t", ErrorSeverity.MEDIUM, ErrorCategory.TIMEOUT)
        docker_err = PantherException(
            "d", ErrorSeverity.MEDIUM, ErrorCategory.DOCKER_RUNTIME
        )
        # Mix categories: 2 timeout + 2 docker (both below their thresholds)
        now = datetime.now()
        real_fast_fail_handler.error_history.extend(
            [
                (now, timeout_err),
                (now, docker_err),
                (now, timeout_err),
                (now, docker_err),
            ]
        )
        # TIMEOUT threshold=3, only 2 timeout errors => no cascade
        assert real_fast_fail_handler.detect_cascade(timeout_err) is None
        # DOCKER_RUNTIME threshold=2, exactly 2 docker errors => cascade
        assert real_fast_fail_handler.detect_cascade(docker_err) is not None

    def test_cascade_respects_time_window(self, real_fast_fail_handler):
        """Old errors outside the time window are not counted."""
        err = PantherException("t", ErrorSeverity.MEDIUM, ErrorCategory.TIMEOUT)
        old_time = datetime.now() - timedelta(
            seconds=real_fast_fail_handler.cascade_time_window + 60
        )
        # Add 3 old errors (outside window)
        for _ in range(3):
            real_fast_fail_handler.error_history.append((old_time, err))
        # 3 old TIMEOUT errors, but they are outside time window
        result = real_fast_fail_handler.detect_cascade(err)
        assert result is None

    def test_cascade_upgrades_severity_in_handle_error(self, real_fast_fail_handler):
        """When a cascade is detected, handle_error upgrades the error severity."""
        err = PantherException("timeout", ErrorSeverity.MEDIUM, ErrorCategory.TIMEOUT)
        # Add enough errors to trigger cascade (threshold for TIMEOUT = 3)
        for _ in range(3):
            real_fast_fail_handler.handle_error(err)
        # The 4th error should trigger cascade detection during handle_error
        # The cascade creates an ErrorCascadeException (HIGH severity)
        # So handle_error should return False (HIGH => stop)
        result = real_fast_fail_handler.handle_error(err, raise_on_critical=False)
        assert result is False

    def test_set_cascade_threshold(self, real_fast_fail_handler):
        """Custom cascade thresholds are respected."""
        real_fast_fail_handler.set_cascade_threshold(ErrorCategory.TIMEOUT, 1)
        err = PantherException("t", ErrorSeverity.MEDIUM, ErrorCategory.TIMEOUT)
        real_fast_fail_handler.error_history.append((datetime.now(), err))
        result = real_fast_fail_handler.detect_cascade(err)
        assert result is not None

    def test_default_threshold_for_unconfigured_category(self, real_fast_fail_handler):
        """Categories without explicit thresholds use default of 5."""
        err = PantherException("cfg", ErrorSeverity.MEDIUM, ErrorCategory.CONFIGURATION)
        # CONFIGURATION is not in default cascade_thresholds => default is 5
        for _ in range(4):
            real_fast_fail_handler.error_history.append((datetime.now(), err))
        assert real_fast_fail_handler.detect_cascade(err) is None
        real_fast_fail_handler.error_history.append((datetime.now(), err))
        assert real_fast_fail_handler.detect_cascade(err) is not None


class TestGetCascadeRisk:
    """Test get_cascade_risk() risk scoring."""

    def test_zero_risk_no_errors(self, real_fast_fail_handler):
        """Risk is 0.0 when there are no errors for a category."""
        risk = real_fast_fail_handler.get_cascade_risk(ErrorCategory.TIMEOUT)
        assert risk == 0.0

    def test_partial_risk(self, real_fast_fail_handler):
        """Risk is proportional to error count vs threshold."""
        err = PantherException("t", ErrorSeverity.MEDIUM, ErrorCategory.TIMEOUT)
        # TIMEOUT threshold=3, add 1 error => risk = 1/3
        real_fast_fail_handler.error_history.append((datetime.now(), err))
        risk = real_fast_fail_handler.get_cascade_risk(ErrorCategory.TIMEOUT)
        assert abs(risk - 1.0 / 3.0) < 0.01

    def test_full_risk_capped_at_one(self, real_fast_fail_handler):
        """Risk is capped at 1.0 even if errors exceed threshold."""
        err = PantherException("t", ErrorSeverity.MEDIUM, ErrorCategory.TIMEOUT)
        for _ in range(10):
            real_fast_fail_handler.error_history.append((datetime.now(), err))
        risk = real_fast_fail_handler.get_cascade_risk(ErrorCategory.TIMEOUT)
        assert risk == 1.0


class TestGetErrorPatterns:
    """Test get_error_patterns() analysis."""

    def test_empty_history_returns_empty(self, real_fast_fail_handler):
        """No patterns when history is empty."""
        patterns = real_fast_fail_handler.get_error_patterns()
        assert patterns == {}

    def test_single_category_single_window(self, real_fast_fail_handler):
        """Errors within 60s grouped into a single window."""
        err = PantherException("t", ErrorSeverity.MEDIUM, ErrorCategory.TIMEOUT)
        now = datetime.now()
        for _ in range(3):
            real_fast_fail_handler.error_history.append((now, err))
        patterns = real_fast_fail_handler.get_error_patterns()
        assert ErrorCategory.TIMEOUT in patterns
        windows = patterns[ErrorCategory.TIMEOUT]
        assert len(windows) == 1
        assert windows[0][1] == 3  # count

    def test_multiple_categories(self, real_fast_fail_handler):
        """Patterns are grouped per category."""
        now = datetime.now()
        t_err = PantherException("t", ErrorSeverity.MEDIUM, ErrorCategory.TIMEOUT)
        d_err = PantherException(
            "d", ErrorSeverity.MEDIUM, ErrorCategory.DOCKER_RUNTIME
        )
        real_fast_fail_handler.error_history.extend(
            [
                (now, t_err),
                (now, t_err),
                (now, d_err),
            ]
        )
        patterns = real_fast_fail_handler.get_error_patterns()
        assert ErrorCategory.TIMEOUT in patterns
        assert ErrorCategory.DOCKER_RUNTIME in patterns
        assert patterns[ErrorCategory.TIMEOUT][0][1] == 2
        assert patterns[ErrorCategory.DOCKER_RUNTIME][0][1] == 1


class TestGetErrorSummary:
    """Test get_error_summary() output structure."""

    def test_empty_summary(self, real_fast_fail_handler):
        """Summary on fresh handler has zeros and empty lists."""
        summary = real_fast_fail_handler.get_error_summary()
        assert summary["total_errors"] == 0
        assert summary["critical_error"] is None
        assert summary["errors_by_category"] == {}
        assert summary["errors_by_severity"] == {}
        assert summary["recent_errors"] == []
        assert summary["cascades_detected"] == []

    def test_summary_after_errors(self, real_fast_fail_handler):
        """Summary reflects errors that were handled."""
        err_low = PantherException(
            "lo", ErrorSeverity.LOW, ErrorCategory.COMMAND_EXECUTION
        )
        err_med = PantherException("med", ErrorSeverity.MEDIUM, ErrorCategory.TIMEOUT)
        real_fast_fail_handler.handle_error(err_low)
        real_fast_fail_handler.handle_error(err_med)

        summary = real_fast_fail_handler.get_error_summary()
        assert summary["total_errors"] == 2
        assert summary["errors_by_category"]["command_execution"] == 1
        assert summary["errors_by_category"]["timeout"] == 1
        assert summary["errors_by_severity"]["LOW"] == 1
        assert summary["errors_by_severity"]["MEDIUM"] == 1
        assert len(summary["recent_errors"]) == 2

    def test_summary_critical_error_field(self, real_fast_fail_handler):
        """Summary includes critical error string when present."""
        err = PantherException("fatal", ErrorSeverity.CRITICAL, ErrorCategory.RESOURCE)
        real_fast_fail_handler.handle_error(err, raise_on_critical=False)
        summary = real_fast_fail_handler.get_error_summary()
        assert summary["critical_error"] == "fatal"

    def test_summary_recent_errors_capped_at_10(self, real_fast_fail_handler):
        """Recent errors list shows at most 10 entries."""
        for i in range(15):
            err = PantherException(
                f"e{i}", ErrorSeverity.LOW, ErrorCategory.COMMAND_EXECUTION
            )
            real_fast_fail_handler.handle_error(err)
        summary = real_fast_fail_handler.get_error_summary()
        assert len(summary["recent_errors"]) == 10

    def test_summary_cascade_detection(self, real_fast_fail_handler):
        """Summary detects cascades in the error history."""
        err = PantherException("t", ErrorSeverity.MEDIUM, ErrorCategory.TIMEOUT)
        # TIMEOUT threshold=3, add 3+ errors => cascade detected in summary
        for _ in range(4):
            real_fast_fail_handler.handle_error(err)
        summary = real_fast_fail_handler.get_error_summary()
        assert len(summary["cascades_detected"]) >= 1
        cascade = summary["cascades_detected"][0]
        assert cascade["category"] == "timeout"


class TestCheckCritical:
    """Test check_critical() behavior."""

    def test_no_critical_does_nothing(self, real_fast_fail_handler):
        """check_critical does not raise when no critical error exists."""
        real_fast_fail_handler.check_critical()  # should not raise

    def test_raises_stored_critical(self, real_fast_fail_handler):
        """check_critical raises the stored critical error."""
        err = PantherException("fatal", ErrorSeverity.CRITICAL, ErrorCategory.RESOURCE)
        real_fast_fail_handler.handle_error(err, raise_on_critical=False)
        with pytest.raises(PantherException, match="fatal"):
            real_fast_fail_handler.check_critical()

    def test_disabled_handler_check_critical_does_not_raise(self):
        """check_critical does not raise when handler is disabled."""
        handler = FastFailHandler(enabled=False)
        err = PantherException("fatal", ErrorSeverity.CRITICAL, ErrorCategory.RESOURCE)
        handler.handle_error(err, raise_on_critical=False)
        # critical_error is set, but handler is disabled => no raise
        handler.check_critical()  # should not raise


class TestClearHistory:
    """Test clear_history() reset behavior."""

    def test_clear_resets_all_counters(self, real_fast_fail_handler):
        """clear_history resets error count, history, and critical error."""
        err = PantherException("e", ErrorSeverity.MEDIUM, ErrorCategory.TIMEOUT)
        crit = PantherException("fatal", ErrorSeverity.CRITICAL, ErrorCategory.RESOURCE)
        real_fast_fail_handler.handle_error(err)
        real_fast_fail_handler.handle_error(crit, raise_on_critical=False)

        assert real_fast_fail_handler.error_count == 2
        assert real_fast_fail_handler.critical_error is not None
        assert len(real_fast_fail_handler.error_history) == 2

        real_fast_fail_handler.clear_history()

        assert real_fast_fail_handler.error_count == 0
        assert real_fast_fail_handler.critical_error is None
        assert real_fast_fail_handler.error_history == []

    def test_clear_allows_check_critical_to_pass(self, real_fast_fail_handler):
        """After clearing, check_critical does not raise."""
        crit = PantherException("fatal", ErrorSeverity.CRITICAL, ErrorCategory.RESOURCE)
        real_fast_fail_handler.handle_error(crit, raise_on_critical=False)
        real_fast_fail_handler.clear_history()
        real_fast_fail_handler.check_critical()  # should not raise


class TestFormatError:
    """Test _format_error() output format."""

    def test_format_includes_category_severity_message(self, real_fast_fail_handler):
        """Formatted string includes category, severity, and message."""
        err = PantherException(
            "disk full",
            ErrorSeverity.CRITICAL,
            ErrorCategory.RESOURCE,
            context={"disk": "/dev/sda1"},
        )
        formatted = real_fast_fail_handler._format_error(err)
        assert "RESOURCE" in formatted
        assert "CRITICAL" in formatted
        assert "disk full" in formatted
        assert "disk=/dev/sda1" in formatted

    def test_format_empty_context(self, real_fast_fail_handler):
        """Formatting works with empty context."""
        err = PantherException("err", ErrorSeverity.LOW, ErrorCategory.TIMEOUT)
        formatted = real_fast_fail_handler._format_error(err)
        assert "TIMEOUT" in formatted
        assert "err" in formatted


# ---------------------------------------------------------------------------
# Integration-style scenarios
# ---------------------------------------------------------------------------


class TestFastFailIntegration:
    """End-to-end scenarios combining multiple FastFailHandler features."""

    def test_mixed_errors_with_cascade_and_summary(self, real_fast_fail_handler):
        """Simulate a realistic error sequence and verify summary."""
        h = real_fast_fail_handler
        # Several timeouts
        for _ in range(4):
            err = PantherException(
                "timeout", ErrorSeverity.MEDIUM, ErrorCategory.TIMEOUT
            )
            h.handle_error(err)
        # A docker error
        docker_err = PantherException(
            "docker", ErrorSeverity.HIGH, ErrorCategory.DOCKER_RUNTIME
        )
        h.handle_error(docker_err, raise_on_critical=False)

        summary = h.get_error_summary()
        assert summary["total_errors"] == 5
        assert summary["errors_by_category"]["timeout"] == 4
        assert summary["errors_by_category"]["docker_runtime"] == 1

    def test_cascade_then_clear_then_new_errors(self, real_fast_fail_handler):
        """Cascade triggers, history cleared, new errors start fresh."""
        h = real_fast_fail_handler
        err = PantherException("t", ErrorSeverity.MEDIUM, ErrorCategory.TIMEOUT)
        for _ in range(4):
            h.handle_error(err)
        # Cascade should be detectable
        assert h.detect_cascade(err) is not None

        h.clear_history()

        # After clear, no cascade
        assert h.detect_cascade(err) is None
        assert h.error_count == 0

    def test_docker_build_failure_triggers_immediate_stop(self, real_fast_fail_handler):
        """A DockerBuildException immediately raises."""
        err = DockerBuildException("build fail", "myimg", "Dockerfile")
        with pytest.raises(DockerBuildException, match="build fail"):
            real_fast_fail_handler.handle_error(err)
        assert real_fast_fail_handler.critical_error is err

    def test_error_severity_ordering(self):
        """Verify ErrorSeverity enum values are ordered correctly."""
        assert ErrorSeverity.LOW.value < ErrorSeverity.MEDIUM.value
        assert ErrorSeverity.MEDIUM.value < ErrorSeverity.HIGH.value
        assert ErrorSeverity.HIGH.value < ErrorSeverity.CRITICAL.value


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
