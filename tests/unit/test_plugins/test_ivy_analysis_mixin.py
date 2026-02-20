"""Tests for IvyAnalysisMixin output organization and analysis."""
import logging
import pytest

from panther.plugins.services.testers.panther_ivy.ivy_analysis_mixin import (
    IvyAnalysisMixin,
)


class FakeService(IvyAnalysisMixin):
    """Minimal harness so the mixin's methods can run."""

    def __init__(self):
        self.logger = logging.getLogger("test.ivy_analysis")


@pytest.mark.unit
class TestOrganizeOutputsByService:
    """Verify that _organize_outputs_by_service concatenates phase outputs."""

    def _write_temp(self, tmp_path, name, content):
        p = tmp_path / name
        p.write_text(content)
        return str(p)

    def test_concatenates_multiple_phases_for_same_key(self, tmp_path):
        """compile_stderr + runtime_stderr + test_stderr → single 'stderr' with all content."""
        svc = FakeService()

        collected = {
            "compile_stderr_ivy_server": {
                "env0": self._write_temp(tmp_path, "compile_stderr.log", "starting runtime phase")
            },
            "runtime_stderr_ivy_server": {
                "env0": self._write_temp(tmp_path, "runtime_stderr.log", "call_generating cycles = 10")
            },
            "test_stderr_ivy_server": {
                "env0": self._write_temp(tmp_path, "test_stderr.log", "")
            },
        }

        result = svc._organize_outputs_by_service(collected)

        assert "ivy_server" in result
        stderr = result["ivy_server"]["stderr"]
        assert "starting runtime phase" in stderr
        assert "call_generating" in stderr

    def test_single_phase_no_duplicate(self, tmp_path):
        """A single file for a key should not get newline-prefixed."""
        svc = FakeService()

        collected = {
            "compile_stderr_ivy_server": {
                "env0": self._write_temp(tmp_path, "compile_stderr.log", "only content")
            },
        }

        result = svc._organize_outputs_by_service(collected)
        assert result["ivy_server"]["stderr"] == "only content"

    def test_stdout_phases_concatenated(self, tmp_path):
        """compile_stdout + test_stdout both preserved."""
        svc = FakeService()

        collected = {
            "compile_stdout_ivy_server": {
                "env0": self._write_temp(tmp_path, "compile_stdout.log", "Compilation succeeded")
            },
            "test_stdout_ivy_server": {
                "env0": self._write_temp(tmp_path, "test_stdout.log", "test complete")
            },
        }

        result = svc._organize_outputs_by_service(collected)
        stdout = result["ivy_server"]["stdout"]
        assert "Compilation succeeded" in stdout
        assert "test complete" in stdout


@pytest.mark.unit
class TestAnalysisWithConcatenatedOutputs:
    """End-to-end: compilation detection works when phases are concatenated."""

    def _write_temp(self, tmp_path, name, content):
        p = tmp_path / name
        p.write_text(content)
        return str(p)

    def test_compilation_detected_from_compile_stdout(self, tmp_path):
        """compile_stdout has 'Compilation succeeded' but test_stdout overwrote it before the fix."""
        svc = FakeService()

        collected = {
            "compile_stdout_ivy_server": {
                "env0": self._write_temp(tmp_path, "compile_stdout.log", "Compilation succeeded")
            },
            "test_stdout_ivy_server": {
                "env0": self._write_temp(tmp_path, "test_stdout.log", "test complete")
            },
            "compile_stderr_ivy_server": {
                "env0": self._write_temp(tmp_path, "compile_stderr.log", "starting runtime phase")
            },
            "runtime_stderr_ivy_server": {
                "env0": self._write_temp(tmp_path, "runtime_stderr.log", "call_generating cycles = 5")
            },
            "test_stderr_ivy_server": {
                "env0": self._write_temp(tmp_path, "test_stderr.log", "")
            },
        }

        result = svc.analyze_outputs_with_data(collected)

        assert result["passed"] is True
        ivy = result["detailed_results"]["ivy_server"]
        assert ivy["compilation_succeeded"] is True
        assert ivy["test_executed"] is True
        assert ivy["execution_successful"] is True
