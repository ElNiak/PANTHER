"""Unit tests for IvyAnalysisMixin verdict determination and output parsing."""

import logging
import os
import tempfile

import pytest

from panther.plugins.services.testers.panther_ivy.ivy_analysis_mixin import (
    IvyAnalysisMixin,
)


class ConcreteIvyAnalyzer(IvyAnalysisMixin):
    """Concrete test class that mixes in IvyAnalysisMixin."""

    def __init__(self):
        self.logger = logging.getLogger("test_ivy_analysis")
        self.collected_outputs = {}


@pytest.fixture
def analyzer():
    return ConcreteIvyAnalyzer()


# ---------------------------------------------------------------------------
# _parse_output_key
# ---------------------------------------------------------------------------


class TestParseOutputKey:
    """Tests for _parse_output_key handling all key formats."""

    def test_runtime_stdout_key(self, analyzer):
        service, otype = analyzer._parse_output_key("runtime_stdout_ivy_server")
        assert service == "ivy_server"
        assert otype == "stdout"

    def test_runtime_stderr_key(self, analyzer):
        service, otype = analyzer._parse_output_key("runtime_stderr_ivy_server")
        assert service == "ivy_server"
        assert otype == "stderr"

    def test_compilation_status_key(self, analyzer):
        """compilation_status_ivy_server must parse correctly (was broken)."""
        service, otype = analyzer._parse_output_key("compilation_status_ivy_server")
        assert service == "ivy_server"
        assert otype == "compile_status"

    def test_compile_status_key(self, analyzer):
        service, otype = analyzer._parse_output_key("compile_status_ivy_server")
        assert service == "ivy_server"
        assert otype == "compile_status"

    def test_infix_compile_status(self, analyzer):
        service, otype = analyzer._parse_output_key("ivy_compile_status_ivy_server")
        assert service == "ivy_server"
        assert otype == "compile_status"

    def test_infix_compilation_status(self, analyzer):
        service, otype = analyzer._parse_output_key(
            "ivy_compilation_status_ivy_server"
        )
        assert service == "ivy_server"
        assert otype == "compile_status"

    def test_test_results_key(self, analyzer):
        service, otype = analyzer._parse_output_key("runtime_test_results_ivy_server")
        assert service == "ivy_server"
        assert otype == "test_results"

    def test_unknown_key(self, analyzer):
        service, otype = analyzer._parse_output_key("random_garbage")
        assert service is None
        assert otype is None


# ---------------------------------------------------------------------------
# _determine_ivy_verdict
# ---------------------------------------------------------------------------


class TestDetermineIvyVerdict:
    """Tests for IVY-specific verdict determination."""

    def test_assumption_failed_returns_non_compliant(self, analyzer):
        stdout = 'assumption_failed("quic_packet.ivy: line 597")\n'
        result = analyzer._determine_ivy_verdict(stdout, "")
        assert result["verdict"] == "NON_COMPLIANT"
        assert len(result["assumption_failures"]) == 1
        assert "line 597" in result["assumption_failures"][0]

    def test_multiple_assumption_failures(self, analyzer):
        stdout = (
            'assumption_failed("quic_packet.ivy: line 597")\n'
            '> quic_packet\n'
            'assumption_failed("quic_packet.ivy: line 602")\n'
        )
        result = analyzer._determine_ivy_verdict(stdout, "")
        assert result["verdict"] == "NON_COMPLIANT"
        assert len(result["assumption_failures"]) == 2

    def test_test_completed_no_failures_returns_no_violation(self, analyzer):
        stdout = "> quic_connected\n< quic_packet\ntest_completed\n"
        result = analyzer._determine_ivy_verdict(stdout, "")
        assert result["verdict"] == "NO_VIOLATION_FOUND"
        assert result["assumption_failures"] == []

    def test_assumption_failed_overrides_test_completed(self, analyzer):
        """If both markers present, assumption_failed takes priority."""
        stdout = (
            'assumption_failed("quic_packet.ivy: line 100")\n' "test_completed\n"
        )
        result = analyzer._determine_ivy_verdict(stdout, "")
        assert result["verdict"] == "NON_COMPLIANT"

    def test_segfault_returns_tester_crash(self, analyzer):
        result = analyzer._determine_ivy_verdict("", "Segmentation fault (core dumped)")
        assert result["verdict"] == "TESTER_CRASH"

    def test_sigsegv_returns_tester_crash(self, analyzer):
        result = analyzer._determine_ivy_verdict("", "signal: SIGSEGV")
        assert result["verdict"] == "TESTER_CRASH"

    def test_connection_reset_returns_iut_crash(self, analyzer):
        result = analyzer._determine_ivy_verdict("", "connection reset by peer")
        assert result["verdict"] == "IUT_CRASH"

    def test_protocol_activity_no_markers_returns_no_violation(self, analyzer):
        """Protocol activity without assumption_failed or test_completed -> NO_VIOLATION_FOUND."""
        stdout = (
            "< show_socket_debug_event\n"
            "> frame.crypto.handle\n"
            "< prot.show_header\n"
        )
        result = analyzer._determine_ivy_verdict(stdout, "")
        assert result["verdict"] == "NO_VIOLATION_FOUND"
        assert result["assumption_failures"] == []
        assert any("Protocol activity" in d for d in result["details"])

    def test_protocol_activity_with_assumption_failed_returns_non_compliant(self, analyzer):
        """assumption_failed takes priority over protocol activity."""
        stdout = (
            "< show_socket_debug_event\n"
            "> frame.crypto.handle\n"
            'assumption_failed("quic_packet.ivy: line 200")\n'
            "< prot.show_header\n"
        )
        result = analyzer._determine_ivy_verdict(stdout, "")
        assert result["verdict"] == "NON_COMPLIANT"
        assert len(result["assumption_failures"]) == 1

    def test_no_output_returns_unknown(self, analyzer):
        result = analyzer._determine_ivy_verdict("", "")
        assert result["verdict"] == "UNKNOWN"

    def test_none_output_returns_unknown(self, analyzer):
        result = analyzer._determine_ivy_verdict("", "")
        assert result["verdict"] == "UNKNOWN"


# ---------------------------------------------------------------------------
# _check_compilation_status
# ---------------------------------------------------------------------------


class TestCheckCompilationStatus:
    """Tests for compilation status checking with both key variants."""

    def test_compile_status_key_succeeded(self, analyzer):
        outputs = {"compile_status": "Compilation succeeded"}
        assert analyzer._check_compilation_status(outputs) is True

    def test_compilation_status_key_succeeded(self, analyzer):
        """compilation_status key variant (from Docker Compose collector)."""
        outputs = {"compilation_status": "Compilation succeeded"}
        assert analyzer._check_compilation_status(outputs) is True

    def test_compilation_failed(self, analyzer):
        outputs = {"compile_status": "Compilation failed"}
        assert analyzer._check_compilation_status(outputs) is False

    def test_stderr_lifecycle_evidence(self, analyzer):
        outputs = {"stderr": "starting runtime phase\ncall_generating ..."}
        assert analyzer._check_compilation_status(outputs) is True

    def test_no_evidence(self, analyzer):
        outputs = {"stderr": "some random output"}
        assert analyzer._check_compilation_status(outputs) is False


# ---------------------------------------------------------------------------
# _verify_test_execution
# ---------------------------------------------------------------------------


class TestVerifyTestExecution:
    """Tests for IVY-specific test execution verification."""

    def test_protocol_event_markers(self, analyzer):
        outputs = {"stdout": "> quic_connected\n< quic_packet\n"}
        assert analyzer._verify_test_execution(outputs) is True

    def test_assumption_failed_proves_execution(self, analyzer):
        outputs = {"stdout": 'assumption_failed("quic_packet.ivy: line 597")'}
        assert analyzer._verify_test_execution(outputs) is True

    def test_test_completed_proves_execution(self, analyzer):
        outputs = {"stdout": "test_completed"}
        assert analyzer._verify_test_execution(outputs) is True

    def test_stderr_lifecycle_proves_execution(self, analyzer):
        outputs = {"stderr": "call_generating cycles = 100"}
        assert analyzer._verify_test_execution(outputs) is True

    def test_no_evidence(self, analyzer):
        outputs = {"stdout": "some random text", "stderr": "some random stderr"}
        assert analyzer._verify_test_execution(outputs) is False


# ---------------------------------------------------------------------------
# Integration: analyze_outputs_with_data
# ---------------------------------------------------------------------------


class TestAnalyzeOutputsIntegration:
    """Integration tests for the full analysis pipeline."""

    def _make_outputs_with_files(self, file_contents):
        """Helper: write content to temp files and return collected_outputs dict."""
        outputs = {}
        temp_files = []
        for key, content in file_contents.items():
            tf = tempfile.NamedTemporaryFile(
                mode="w", suffix=".txt", delete=False
            )
            tf.write(content)
            tf.close()
            temp_files.append(tf.name)
            outputs[key] = tf.name
        return outputs, temp_files

    def test_assumption_failed_gives_non_compliant_verdict(self, analyzer):
        file_contents = {
            "compilation_status_ivy_server": "Compilation succeeded\n",
            "runtime_stdout_ivy_server": (
                '> quic_connected\nassumption_failed("quic_packet.ivy: line 597")\n'
            ),
            "runtime_stderr_ivy_server": (
                "starting runtime phase\ncall_generating\ncycles = 100\n"
            ),
        }
        outputs, temp_files = self._make_outputs_with_files(file_contents)
        try:
            result = analyzer.analyze_outputs_with_data(outputs)
            assert result["passed"] is False
            ivy_result = result["detailed_results"]["ivy_server"]
            assert ivy_result["verdict"] == "NON_COMPLIANT"
            assert ivy_result["execution_successful"] is False
            assert ivy_result["compilation_succeeded"] is True
            assert ivy_result["test_executed"] is True
            assert any(
                "assumption_failed" in msg
                for msg in ivy_result["error_messages"]
            )
        finally:
            for f in temp_files:
                os.unlink(f)

    def test_test_completed_gives_no_violation_found(self, analyzer):
        file_contents = {
            "compilation_status_ivy_server": "Compilation succeeded\n",
            "runtime_stdout_ivy_server": (
                "> quic_connected\n< quic_packet\ntest_completed\n"
            ),
            "runtime_stderr_ivy_server": (
                "starting runtime phase\ncall_generating\ncycles = 100\n"
            ),
        }
        outputs, temp_files = self._make_outputs_with_files(file_contents)
        try:
            result = analyzer.analyze_outputs_with_data(outputs)
            assert result["passed"] is True
            ivy_result = result["detailed_results"]["ivy_server"]
            assert ivy_result["verdict"] == "NO_VIOLATION_FOUND"
            assert ivy_result["execution_successful"] is True
        finally:
            for f in temp_files:
                os.unlink(f)

    def test_protocol_activity_no_markers_gives_no_violation(self, analyzer):
        """Mimics the 17-15-18 test: protocol activity, no assumption_failed, no test_completed."""
        file_contents = {
            "compilation_status_ivy_server": "Compilation succeeded\n",
            "runtime_stdout_ivy_server": (
                "< show_socket_debug_event\n"
                "< prot.show_header\n"
                "> frame.crypto.handle\n"
                "< show_socket_debug_event\n"
                "> frame.ack.handle\n"
            ),
            "runtime_stderr_ivy_server": (
                "Starting RUNTIME phase\ncall_generating\ncycles = 50\n"
            ),
        }
        outputs, temp_files = self._make_outputs_with_files(file_contents)
        try:
            result = analyzer.analyze_outputs_with_data(outputs)
            assert result["passed"] is True
            ivy_result = result["detailed_results"]["ivy_server"]
            assert ivy_result["verdict"] == "NO_VIOLATION_FOUND"
            assert ivy_result["execution_successful"] is True
            assert ivy_result["compilation_succeeded"] is True
            assert ivy_result["test_executed"] is True
        finally:
            for f in temp_files:
                os.unlink(f)

    def test_tester_crash_gives_tester_crash_verdict(self, analyzer):
        file_contents = {
            "compilation_status_ivy_server": "Compilation succeeded\n",
            "runtime_stdout_ivy_server": "",
            "runtime_stderr_ivy_server": "Segmentation fault (core dumped)\n",
        }
        outputs, temp_files = self._make_outputs_with_files(file_contents)
        try:
            result = analyzer.analyze_outputs_with_data(outputs)
            assert result["passed"] is False
            ivy_result = result["detailed_results"]["ivy_server"]
            assert ivy_result["verdict"] == "TESTER_CRASH"
            assert ivy_result["execution_successful"] is False
        finally:
            for f in temp_files:
                os.unlink(f)

    def test_passed_requires_decisive_verdict(self, analyzer):
        """ivy has NO_VIOLATION_FOUND, picoquic has UNKNOWN -> passed: true
        (only when all compilations succeed)."""
        file_contents = {
            "compilation_status_ivy_server": "Compilation succeeded\n",
            "runtime_stdout_ivy_server": (
                "> quic_connected\n< quic_packet\ntest_completed\n"
            ),
            "runtime_stderr_ivy_server": (
                "starting runtime phase\ncall_generating\ncycles = 100\n"
            ),
            # picoquic has no IVY markers -> UNKNOWN verdict
            # but must have compilation evidence for passed=True
            "runtime_stdout_picoquic_server": "some picoquic output\n",
            "runtime_stderr_picoquic_server": "starting runtime phase\ncall_generating\n",
        }
        outputs, temp_files = self._make_outputs_with_files(file_contents)
        try:
            result = analyzer.analyze_outputs_with_data(outputs)
            assert result["passed"] is True
            ivy_result = result["detailed_results"]["ivy_server"]
            assert ivy_result["verdict"] == "NO_VIOLATION_FOUND"
        finally:
            for f in temp_files:
                os.unlink(f)

    def test_non_compliant_overrides_iut_success(self, analyzer):
        """ivy has NON_COMPLIANT, picoquic has execution_successful: true -> passed: false."""
        file_contents = {
            "compilation_status_ivy_server": "Compilation succeeded\n",
            "runtime_stdout_ivy_server": (
                '> quic_connected\nassumption_failed("quic_packet.ivy: line 200")\n'
            ),
            "runtime_stderr_ivy_server": (
                "starting runtime phase\ncall_generating\ncycles = 100\n"
            ),
            # picoquic ran fine (would have execution_successful=True with old logic)
            "runtime_stdout_picoquic_server": "some picoquic output\n",
            "runtime_stderr_picoquic_server": "picoquic running\n",
        }
        outputs, temp_files = self._make_outputs_with_files(file_contents)
        try:
            result = analyzer.analyze_outputs_with_data(outputs)
            # NON_COMPLIANT from ivy must override picoquic success
            assert result["passed"] is False
            ivy_result = result["detailed_results"]["ivy_server"]
            assert ivy_result["verdict"] == "NON_COMPLIANT"
        finally:
            for f in temp_files:
                os.unlink(f)

    def test_all_unknown_means_not_passed(self, analyzer):
        """Both services have UNKNOWN verdict -> passed: false."""
        file_contents = {
            "runtime_stdout_ivy_server": "some non-IVY output\n",
            "runtime_stderr_ivy_server": "some random stderr\n",
            "runtime_stdout_picoquic_server": "some picoquic output\n",
            "runtime_stderr_picoquic_server": "picoquic running\n",
        }
        outputs, temp_files = self._make_outputs_with_files(file_contents)
        try:
            result = analyzer.analyze_outputs_with_data(outputs)
            assert result["passed"] is False
        finally:
            for f in temp_files:
                os.unlink(f)

    def test_failures_not_discarded_when_passed(self, analyzer):
        """When passed is true, failures list should still contain any collected failures."""
        file_contents = {
            "compilation_status_ivy_server": "Compilation succeeded\n",
            "runtime_stdout_ivy_server": (
                "> quic_connected\n< quic_packet\ntest_completed\n"
            ),
            "runtime_stderr_ivy_server": (
                "starting runtime phase\ncall_generating\ncycles = 100\n"
            ),
        }
        outputs, temp_files = self._make_outputs_with_files(file_contents)
        try:
            result = analyzer.analyze_outputs_with_data(outputs)
            assert result["passed"] is True
            # failures key should exist and be a list (not suppressed)
            assert isinstance(result["failures"], list)
        finally:
            for f in temp_files:
                os.unlink(f)


# ---------------------------------------------------------------------------
# StatusCollector tests
# ---------------------------------------------------------------------------


class TestStatusCollector:
    """Tests for StatusCollector bug fixes (Bugs B and C)."""

    def test_status_from_analysis_results_json(self, tmp_path):
        """Mock test directory with analysis_results.json -> correct status."""
        from panther.core.reporting.status_collector import StatusCollector, TestStatus

        # Create experiment dir structure
        experiment_dir = tmp_path / "experiment"
        experiment_dir.mkdir()
        test_dir = experiment_dir / "test_0"
        test_dir.mkdir()
        analysis_dir = test_dir / "analysis"
        analysis_dir.mkdir()

        # Write analysis results indicating pass
        import json

        analysis_results = {
            "ivy_tester": {
                "results": {"passed": True, "verdict": "NO_VIOLATION_FOUND"}
            }
        }
        (analysis_dir / "analysis_results.json").write_text(
            json.dumps(analysis_results)
        )

        # Write a test.log that would falsely match old broad patterns
        (test_dir / "test.log").write_text(
            "2026-02-17 18:02:05 INFO Starting test\n"
            "wait timeout: 200\n"
            "error_handler configured\n"
            "2026-02-17 18:05:10 INFO Test complete\n"
        )

        collector = StatusCollector(experiment_dir)
        content = (test_dir / "test.log").read_text()
        status = collector._determine_test_status(content, test_dir)
        assert status == TestStatus.PASSED

    def test_status_from_analysis_results_failed(self, tmp_path):
        """analysis_results.json with passed=false -> FAILED status."""
        from panther.core.reporting.status_collector import StatusCollector, TestStatus

        experiment_dir = tmp_path / "experiment"
        experiment_dir.mkdir()
        test_dir = experiment_dir / "test_0"
        test_dir.mkdir()
        analysis_dir = test_dir / "analysis"
        analysis_dir.mkdir()

        import json

        analysis_results = {
            "ivy_tester": {
                "results": {"passed": False, "verdict": "NON_COMPLIANT"}
            }
        }
        (analysis_dir / "analysis_results.json").write_text(
            json.dumps(analysis_results)
        )

        (test_dir / "test.log").write_text(
            "2026-02-17 18:02:05 INFO Starting test\n"
        )

        collector = StatusCollector(experiment_dir)
        content = (test_dir / "test.log").read_text()
        status = collector._determine_test_status(content, test_dir)
        assert status == TestStatus.FAILED

    def test_bare_error_word_does_not_trigger_failure(self, tmp_path):
        """Log containing 'error' as part of config/names should NOT match."""
        from panther.core.reporting.status_collector import StatusCollector, TestStatus

        experiment_dir = tmp_path / "experiment"
        experiment_dir.mkdir()
        test_dir = experiment_dir / "test_0"
        test_dir.mkdir()

        (test_dir / "test.log").write_text(
            "2026-02-17 18:02:05 INFO error_handler configured\n"
            "wait timeout: 200\n"
            "error threshold set to 5\n"
        )

        collector = StatusCollector(experiment_dir)
        content = (test_dir / "test.log").read_text()
        status = collector._determine_test_status(content, test_dir)
        # Should NOT be TIMEOUT or FAILED — bare words no longer match
        assert status == TestStatus.UNKNOWN

    def test_fast_fail_not_triggered_by_generic_error(self, tmp_path):
        """Log containing 'error' and 'critical' separately should NOT trigger fast-fail."""
        from panther.core.reporting.status_collector import StatusCollector

        experiment_dir = tmp_path / "experiment"
        experiment_dir.mkdir()
        test_dir = experiment_dir / "test_0"
        test_dir.mkdir()

        # Log has "critical" and "error" as separate words, NOT "critical error"
        (test_dir / "test.log").write_text(
            "2026-02-17 18:02:05 INFO critical configuration loaded\n"
            "2026-02-17 18:02:06 INFO error_handler initialized\n"
            "2026-02-17 18:05:10 INFO Execution completed\n"
        )

        collector = StatusCollector(experiment_dir)
        result = collector._extract_test_result(test_dir)
        assert result is not None
        assert result.fast_fail_triggered is False

    def test_fast_fail_triggered_by_actual_event(self, tmp_path):
        """Log with actual fast-fail event SHOULD trigger."""
        from panther.core.reporting.status_collector import StatusCollector

        experiment_dir = tmp_path / "experiment"
        experiment_dir.mkdir()
        test_dir = experiment_dir / "test_0"
        test_dir.mkdir()

        (test_dir / "test.log").write_text(
            "2026-02-17 18:02:05 INFO Starting test\n"
            "2026-02-17 18:03:00 CRITICAL fast-fail triggered due to docker build failure\n"
            "2026-02-17 18:03:01 INFO Test stopped\n"
        )

        collector = StatusCollector(experiment_dir)
        result = collector._extract_test_result(test_dir)
        assert result is not None
        assert result.fast_fail_triggered is True


# ---------------------------------------------------------------------------
# Bug 3: passed=true despite compilation failure
# ---------------------------------------------------------------------------


class TestCompilationFailurePreventsPass:
    """Tests for Bug 3: passed logic must check compilation_succeeded."""

    def _make_outputs_with_files(self, file_contents):
        outputs = {}
        temp_files = []
        for key, content in file_contents.items():
            tf = tempfile.NamedTemporaryFile(
                mode="w", suffix=".txt", delete=False
            )
            tf.write(content)
            tf.close()
            temp_files.append(tf.name)
            outputs[key] = tf.name
        return outputs, temp_files

    def test_compilation_failed_overrides_no_violation(self, analyzer):
        """NO_VIOLATION_FOUND verdict but compilation failed -> passed=False."""
        file_contents = {
            "compilation_status_ivy_server": "Compilation failed\n",
            "runtime_stdout_ivy_server": (
                "> quic_connected\n< quic_packet\ntest_completed\n"
            ),
            "runtime_stderr_ivy_server": "some output\n",
        }
        outputs, temp_files = self._make_outputs_with_files(file_contents)
        try:
            result = analyzer.analyze_outputs_with_data(outputs)
            assert result["passed"] is False
        finally:
            for f in temp_files:
                os.unlink(f)

    def test_compilation_succeeded_allows_pass(self, analyzer):
        """NO_VIOLATION_FOUND + compilation succeeded -> passed=True."""
        file_contents = {
            "compilation_status_ivy_server": "Compilation succeeded\n",
            "runtime_stdout_ivy_server": (
                "> quic_connected\ntest_completed\n"
            ),
            "runtime_stderr_ivy_server": (
                "starting runtime phase\ncall_generating\n"
            ),
        }
        outputs, temp_files = self._make_outputs_with_files(file_contents)
        try:
            result = analyzer.analyze_outputs_with_data(outputs)
            assert result["passed"] is True
        finally:
            for f in temp_files:
                os.unlink(f)


# ---------------------------------------------------------------------------
# Bug 4: Flexible compilation status detection
# ---------------------------------------------------------------------------


class TestFlexibleCompilationStatus:
    """Tests for Bug 4: compilation status should accept multiple formats."""

    def test_status_succeeded(self, analyzer):
        outputs = {"compile_status": "succeeded"}
        assert analyzer._check_compilation_status(outputs) is True

    def test_status_success(self, analyzer):
        outputs = {"compile_status": "success"}
        assert analyzer._check_compilation_status(outputs) is True

    def test_status_ok(self, analyzer):
        outputs = {"compile_status": "ok"}
        assert analyzer._check_compilation_status(outputs) is True

    def test_status_failed(self, analyzer):
        outputs = {"compile_status": "failed"}
        assert analyzer._check_compilation_status(outputs) is False

    def test_status_error(self, analyzer):
        outputs = {"compile_status": "error during compilation"}
        assert analyzer._check_compilation_status(outputs) is False


# ---------------------------------------------------------------------------
# Bug 7: Duplicate failure deduplication
# ---------------------------------------------------------------------------


class TestFailureDeduplication:
    """Tests for Bug 7: duplicate failures should be removed."""

    def _make_outputs_with_files(self, file_contents):
        outputs = {}
        temp_files = []
        for key, content in file_contents.items():
            tf = tempfile.NamedTemporaryFile(
                mode="w", suffix=".txt", delete=False
            )
            tf.write(content)
            tf.close()
            temp_files.append(tf.name)
            outputs[key] = tf.name
        return outputs, temp_files

    def test_duplicate_errors_not_repeated(self, analyzer):
        """Same error from multiple services should appear only once."""
        file_contents = {
            "runtime_stdout_ivy_server": "some output\n",
            "runtime_stderr_ivy_server": "error: No such file or directory\n",
            "runtime_stdout_ivy_client": "some output\n",
            "runtime_stderr_ivy_client": "error: No such file or directory\n",
        }
        outputs, temp_files = self._make_outputs_with_files(file_contents)
        try:
            result = analyzer.analyze_outputs_with_data(outputs)
            # Check for no duplicates in failures
            assert len(result["failures"]) == len(set(result["failures"]))
        finally:
            for f in temp_files:
                os.unlink(f)


# ---------------------------------------------------------------------------
# Bug 5: TIMEOUT status counting
# ---------------------------------------------------------------------------


class TestStatusCounting:
    """Tests for Bug 5: ExperimentSummary status counters."""

    def test_timeout_tests_counted(self, tmp_path):
        """TIMEOUT tests should be counted separately."""
        from panther.core.reporting.status_collector import (
            ExperimentSummary,
            ExperimentStatus,
            FastFailInfo,
            ResourceUsage,
            TestResult,
            TestStatus,
        )

        summary = ExperimentSummary(
            experiment_id="test",
            status=ExperimentStatus.TIMEOUT,
            start_time=None,
            end_time=None,
            duration=None,
            configuration_file=None,
            tests=[
                TestResult(name="t1", status=TestStatus.PASSED, duration=1.0),
                TestResult(name="t2", status=TestStatus.TIMEOUT, duration=30.0),
                TestResult(name="t3", status=TestStatus.INTERRUPTED, duration=5.0),
                TestResult(name="t4", status=TestStatus.UNKNOWN, duration=0.0),
            ],
            fast_fail=FastFailInfo(enabled=False),
            resources=ResourceUsage(),
        )

        assert summary.total_tests == 4
        assert summary.passed_tests == 1
        assert summary.timeout_tests == 1
        assert summary.interrupted_tests == 1
        assert summary.unknown_tests == 1

    def test_to_dict_includes_all_counters(self):
        """to_dict() must include timeout, interrupted, unknown counts."""
        from panther.core.reporting.status_collector import (
            ExperimentSummary,
            ExperimentStatus,
            FastFailInfo,
            ResourceUsage,
            TestResult,
            TestStatus,
        )

        summary = ExperimentSummary(
            experiment_id="test",
            status=ExperimentStatus.COMPLETED,
            start_time=None,
            end_time=None,
            duration=None,
            configuration_file=None,
            tests=[
                TestResult(name="t1", status=TestStatus.PASSED, duration=1.0),
                TestResult(name="t2", status=TestStatus.TIMEOUT, duration=30.0),
            ],
            fast_fail=FastFailInfo(enabled=False),
            resources=ResourceUsage(),
        )

        d = summary.to_dict()
        assert "timeout" in d["tests"]
        assert "interrupted" in d["tests"]
        assert "unknown" in d["tests"]
        assert d["tests"]["timeout"] == 1


# ---------------------------------------------------------------------------
# Bug 11: Experiment status for plugin failures
# ---------------------------------------------------------------------------


class TestExperimentStatusPluginFailure:
    """Tests for Bug 11: empty test_results with plugin failure -> FAILED."""

    def test_empty_results_with_plugin_failure(self, tmp_path):
        """Empty test_results but log shows plugin validation failed -> FAILED."""
        from panther.core.reporting.status_collector import (
            ExperimentStatus,
            StatusCollector,
        )

        experiment_dir = tmp_path / "experiment"
        experiment_dir.mkdir()

        (experiment_dir / "experiment.log").write_text(
            "2026-02-17 18:00:00 INFO Starting experiment\n"
            "2026-02-17 18:00:05 ERROR Plugin Validation Failed: missing config\n"
            "2026-02-17 18:00:06 INFO Experiment terminated\n"
        )

        collector = StatusCollector(experiment_dir)
        summary = collector.collect_experiment_summary()
        assert summary.status == ExperimentStatus.FAILED

    def test_empty_results_no_failure_indicators(self, tmp_path):
        """Empty test_results and no failure indicators -> UNKNOWN."""
        from panther.core.reporting.status_collector import (
            ExperimentStatus,
            StatusCollector,
        )

        experiment_dir = tmp_path / "experiment"
        experiment_dir.mkdir()

        (experiment_dir / "experiment.log").write_text(
            "2026-02-17 18:00:00 INFO Starting experiment\n"
            "2026-02-17 18:00:01 INFO Configuration loaded\n"
        )

        collector = StatusCollector(experiment_dir)
        summary = collector.collect_experiment_summary()
        assert summary.status == ExperimentStatus.UNKNOWN
