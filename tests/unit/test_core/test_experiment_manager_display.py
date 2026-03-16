"""Unit tests for test execution display helpers in experiment_manager.

Tests the ``format_test_header`` and ``format_test_result`` module-level
functions that produce structured click.echo() output during test runs.
"""

import pytest

from panther.core.experiment_manager import format_test_header, format_test_result

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
