"""Unit tests for test execution display helpers in experiment_manager.

Tests the ``format_test_header``, ``format_test_result``, and
``format_experiment_summary`` module-level functions that produce
structured click.echo() output during test runs.
"""

import pytest

from panther.core.experiment_manager import (
    format_experiment_summary,
    format_test_header,
    format_test_result,
)

pytestmark = [pytest.mark.unit, pytest.mark.experiment_manager]


# ---------------------------------------------------------------------------
# format_test_header
# ---------------------------------------------------------------------------


class TestFormatTestHeader:
    """Tests for the ``format_test_header`` display helper."""

    def test_contains_test_number(self):
        """Test that header includes 1-based test number and total."""
        result = format_test_header(0, 3, "QUIC Handshake")
        assert "Test 1/3" in result

    def test_contains_test_name(self):
        """Test that header includes the test name."""
        result = format_test_header(2, 5, "Stream Migration")
        assert "Stream Migration" in result

    def test_starts_with_newline(self):
        """Test that header starts with a newline for visual separation."""
        result = format_test_header(0, 1, "Test")
        assert result.startswith("\n")

    def test_uses_box_drawing_dashes(self):
        """Test that header uses box-drawing horizontal lines."""
        result = format_test_header(0, 1, "Test")
        assert "\u2500" in result  # BOX DRAWINGS LIGHT HORIZONTAL

    def test_padding_at_least_two_dashes(self):
        """Test that even very long names get at least 2 trailing dashes."""
        long_name = "A" * 200
        result = format_test_header(0, 1, long_name)
        # The result should end with at least 2 dash characters
        assert result.endswith("\u2500\u2500")

    def test_last_index(self):
        """Test that the last test in a batch shows correct numbering."""
        result = format_test_header(9, 10, "Final Test")
        assert "Test 10/10" in result


# ---------------------------------------------------------------------------
# format_test_result
# ---------------------------------------------------------------------------


class TestFormatTestResult:
    """Tests for the ``format_test_result`` display helper."""

    def test_passed_with_emojis(self):
        """Test passing result includes checkmark emoji and duration."""
        result = format_test_result(passed=True, elapsed=26.42, use_emojis=True)
        assert "PASSED" in result
        assert "(26.4s)" in result
        assert "\u2705" in result

    def test_passed_without_emojis(self):
        """Test passing result without emojis omits the icon."""
        result = format_test_result(passed=True, elapsed=1.0, use_emojis=False)
        assert "PASSED" in result
        assert "\u2705" not in result

    def test_failed_with_error_message(self):
        """Test failing result includes error message and log hint."""
        result = format_test_result(
            passed=False,
            elapsed=3.14,
            use_emojis=True,
            error_message="Docker build failed for picoquic:rfc9000",
        )
        assert "FAILED" in result
        assert "(3.1s)" in result
        assert "Docker build failed" in result
        assert "Check logs for details" in result
        assert "\u274c" in result

    def test_failed_without_error_message(self):
        """Test failing result without error message omits the hint."""
        result = format_test_result(passed=False, elapsed=0.5, use_emojis=True)
        assert "FAILED" in result
        assert "Check logs" not in result

    def test_failed_without_emojis(self):
        """Test failing result without emojis omits the icon."""
        result = format_test_result(
            passed=False,
            elapsed=2.0,
            use_emojis=False,
            error_message="timeout",
        )
        assert "FAILED" in result
        assert "\u274c" not in result

    def test_result_indented(self):
        """Test that result lines are indented with two spaces."""
        passed = format_test_result(passed=True, elapsed=1.0, use_emojis=False)
        failed = format_test_result(passed=False, elapsed=1.0, use_emojis=False)
        assert passed.startswith("  ")
        assert failed.startswith("  ")

    def test_elapsed_formatting_precision(self):
        """Test that elapsed time is formatted to one decimal place."""
        result = format_test_result(passed=True, elapsed=0.123456, use_emojis=False)
        assert "(0.1s)" in result

    def test_zero_elapsed(self):
        """Test that zero elapsed time is displayed correctly."""
        result = format_test_result(passed=True, elapsed=0.0, use_emojis=False)
        assert "(0.0s)" in result


# ---------------------------------------------------------------------------
# format_experiment_summary
# ---------------------------------------------------------------------------


class TestFormatExperimentSummary:
    """Tests for the ``format_experiment_summary`` display helper."""

    def _make_summary(self, **overrides):
        """Create a summary with sensible defaults, overridden by kwargs."""
        defaults = dict(
            successful_tests=3,
            failed_tests=1,
            total_tests=4,
            elapsed_seconds=312.0,
            output_dir="outputs/2026-03-16_14-30/quic_test",
            failed_test_names=[("QUIC Stream Test", "Docker build failed")],
            use_emojis=True,
        )
        defaults.update(overrides)
        return format_experiment_summary(**defaults)

    def test_contains_experiment_complete_title(self):
        """Test that summary includes the 'Experiment Complete' title."""
        result = self._make_summary()
        assert "Experiment Complete" in result

    def test_contains_double_line_separators(self):
        """Test that summary is wrapped in double-line box characters."""
        result = self._make_summary()
        assert "\u2550" in result  # BOX DRAWINGS DOUBLE HORIZONTAL

    def test_contains_single_line_separator(self):
        """Test that summary has a single-line separator under the title."""
        result = self._make_summary()
        assert "\u2500" in result  # BOX DRAWINGS LIGHT HORIZONTAL

    def test_shows_pass_fail_counts(self):
        """Test that summary displays passed and failed test counts."""
        result = self._make_summary(successful_tests=3, failed_tests=1, total_tests=4)
        assert "3 passed" in result
        assert "1 failed" in result

    def test_shows_percentage(self):
        """Test that summary displays success percentage."""
        result = self._make_summary(successful_tests=3, failed_tests=1, total_tests=4)
        assert "75.0%" in result

    def test_percentage_all_passed(self):
        """Test 100% success rate when all tests pass."""
        result = self._make_summary(
            successful_tests=5,
            failed_tests=0,
            total_tests=5,
            failed_test_names=[],
        )
        assert "100.0%" in result

    def test_percentage_all_failed(self):
        """Test 0% success rate when all tests fail."""
        result = self._make_summary(
            successful_tests=0,
            failed_tests=2,
            total_tests=2,
            failed_test_names=[("A", "err1"), ("B", "err2")],
        )
        assert "0.0%" in result

    def test_percentage_zero_total(self):
        """Test that zero total tests does not cause division by zero."""
        result = self._make_summary(
            successful_tests=0,
            failed_tests=0,
            total_tests=0,
            failed_test_names=[],
        )
        assert "0.0%" in result

    def test_duration_minutes_and_seconds(self):
        """Test duration formatting for >= 60 seconds."""
        result = self._make_summary(elapsed_seconds=312.0)
        assert "5m 12s" in result

    def test_duration_seconds_only(self):
        """Test duration formatting for < 60 seconds."""
        result = self._make_summary(elapsed_seconds=45.0)
        assert "45s" in result

    def test_duration_exactly_60_seconds(self):
        """Test duration formatting for exactly 60 seconds."""
        result = self._make_summary(elapsed_seconds=60.0)
        assert "1m 0s" in result

    def test_duration_zero_seconds(self):
        """Test duration formatting for zero elapsed time."""
        result = self._make_summary(elapsed_seconds=0.0)
        assert "0s" in result

    def test_shows_output_dir(self):
        """Test that summary displays the output directory path."""
        result = self._make_summary(output_dir="outputs/my_experiment")
        assert "outputs/my_experiment" in result

    def test_shows_failed_tests_with_emojis(self):
        """Test that failed test list uses emoji when enabled."""
        result = self._make_summary(
            failed_test_names=[("QUIC Stream", "Docker build failed")],
            use_emojis=True,
        )
        assert "\u274c" in result
        assert "QUIC Stream" in result
        assert "Docker build failed" in result

    def test_shows_failed_tests_without_emojis(self):
        """Test that failed test list uses 'X' when emojis disabled."""
        result = self._make_summary(
            failed_test_names=[("QUIC Stream", "Docker build failed")],
            use_emojis=False,
        )
        assert "\u274c" not in result
        assert "X " in result
        assert "QUIC Stream" in result
        assert "Docker build failed" in result

    def test_failed_test_without_reason(self):
        """Test that failed test with empty reason omits the dash separator."""
        result = self._make_summary(
            failed_test_names=[("Some Test", "")],
        )
        assert "Some Test" in result
        # Should not have a dangling em dash
        assert "Some Test \u2014" not in result

    def test_multiple_failed_tests(self):
        """Test that multiple failed tests are listed."""
        failures = [
            ("QUIC Stream Test", "Docker build failed"),
            ("TLS Resumption", "Timeout after 60s"),
        ]
        result = self._make_summary(failed_tests=2, failed_test_names=failures)
        assert "QUIC Stream Test" in result
        assert "TLS Resumption" in result
        assert "Docker build failed" in result
        assert "Timeout after 60s" in result

    def test_no_failed_tests_section_when_all_pass(self):
        """Test that 'Failed tests:' section is omitted when none failed."""
        result = self._make_summary(
            successful_tests=3,
            failed_tests=0,
            total_tests=3,
            failed_test_names=[],
        )
        assert "Failed tests:" not in result

    def test_shows_next_steps(self):
        """Test that next steps with CLI commands are shown."""
        result = self._make_summary(output_dir="outputs/test123")
        assert "Next steps:" in result
        assert "panther report diagnose outputs/test123" in result
        assert "panther logs errors outputs/test123" in result

    def test_output_is_string(self):
        """Test that the function returns a string."""
        result = self._make_summary()
        assert isinstance(result, str)

    def test_starts_with_empty_line(self):
        """Test that the summary starts with an empty line for visual separation."""
        result = self._make_summary()
        assert result.startswith("\n")
