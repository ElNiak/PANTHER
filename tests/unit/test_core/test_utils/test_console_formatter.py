"""Tests for ConsoleFormatter."""

import logging

import pytest

pytestmark = pytest.mark.unit

from panther.core.utils.console_formatter import (
    ConsoleFormatter,
    _build_context_tag,
    _short_module,
)
from panther.core.utils.log_context import log_context

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


@pytest.fixture
def formatter():
    """Plain (no-color) ConsoleFormatter."""
    return ConsoleFormatter()


@pytest.fixture
def make_record():
    """Factory for LogRecord objects."""

    def _make(
        msg="test message",
        level=logging.INFO,
        name="test.logger",
        module="experiment_manager",
    ):
        record = logging.LogRecord(
            name=name,
            level=level,
            pathname="test.py",
            lineno=42,
            msg=msg,
            args=(),
            exc_info=None,
        )
        record.module = module
        return record

    return _make


# ---------------------------------------------------------------------------
# _short_module
# ---------------------------------------------------------------------------


class TestShortModule:
    """Tests for the _short_module helper."""

    def test_strips_panther_core_prefix(self):
        assert _short_module("panther.core.experiment_manager") == "experiment_manager"

    def test_strips_nested_prefix(self):
        assert (
            _short_module("panther.core.utils.logger_factory") == "utils.logger_factory"
        )

    def test_leaves_non_prefixed_unchanged(self):
        assert _short_module("some_other_module") == "some_other_module"

    def test_leaves_partial_prefix_unchanged(self):
        assert _short_module("panther.plugins.quic") == "panther.plugins.quic"


# ---------------------------------------------------------------------------
# _build_context_tag
# ---------------------------------------------------------------------------


class TestBuildContextTag:
    """Tests for the _build_context_tag helper."""

    def test_no_context(self):
        assert _build_context_tag() == ""

    def test_phase_only(self):
        with log_context(phase="initialization"):
            assert _build_context_tag() == "(initialization) "

    def test_phase_and_service(self):
        with log_context(phase="test_execution", service_id="picoquic"):
            tag = _build_context_tag()
            assert "test_execution" in tag
            assert "picoquic" in tag
            assert tag.startswith("(")
            assert tag.endswith(") ")

    def test_service_only(self):
        with log_context(service_id="aioquic"):
            assert _build_context_tag() == "(aioquic) "

    def test_nested_context_overrides(self):
        with log_context(phase="init"):
            with log_context(phase="plugin_loading"):
                assert _build_context_tag() == "(plugin_loading) "


# ---------------------------------------------------------------------------
# ConsoleFormatter.format
# ---------------------------------------------------------------------------


class TestConsoleFormatterFormat:
    """Tests for ConsoleFormatter.format()."""

    def test_basic_format_contains_level(self, formatter, make_record):
        record = make_record()
        output = formatter.format(record)
        assert "[INFO]" in output

    def test_basic_format_contains_message(self, formatter, make_record):
        record = make_record(msg="Loading plugins")
        output = formatter.format(record)
        assert "Loading plugins" in output

    def test_short_timestamp(self, formatter, make_record):
        record = make_record()
        output = formatter.format(record)
        # Should have HH:MM:SS format (no date)
        # Timestamp is at the start, e.g. "12:30:01"
        parts = output.split(" ")
        timestamp = parts[0]
        assert len(timestamp.split(":")) == 3  # HH:MM:SS
        # Should NOT contain a date (no dashes in the first token)
        assert "-" not in timestamp

    def test_context_injected_into_output(self, formatter, make_record):
        with log_context(phase="initialization"):
            record = make_record()
            output = formatter.format(record)
            assert "(initialization)" in output

    def test_no_context_no_parens(self, formatter, make_record):
        record = make_record()
        output = formatter.format(record)
        # Should not contain context parens when no context is set
        assert "() " not in output

    def test_module_name_in_output(self, formatter, make_record):
        record = make_record(module="experiment_manager")
        output = formatter.format(record)
        assert "experiment_manager" in output

    def test_phase_and_service_both_visible(self, formatter, make_record):
        with log_context(phase="test_execution", service_id="picoquic"):
            record = make_record()
            output = formatter.format(record)
            assert "test_execution" in output
            assert "picoquic" in output


# ---------------------------------------------------------------------------
# ConsoleFormatter with colors
# ---------------------------------------------------------------------------


class TestConsoleFormatterColor:
    """Tests for ConsoleFormatter with color support."""

    def test_color_formatter_creates_without_error(self):
        """Color formatter should not raise even if colorlog is missing."""
        log_colors = {
            "DEBUG": "cyan",
            "INFO": "green",
            "WARNING": "yellow",
            "ERROR": "red",
        }
        fmt = ConsoleFormatter(log_colors=log_colors)
        assert fmt is not None

    def test_no_colors_when_none(self):
        fmt = ConsoleFormatter(log_colors=None)
        assert not fmt._use_color


# ---------------------------------------------------------------------------
# ConsoleFormatter.banner
# ---------------------------------------------------------------------------


class TestBanner:
    """Tests for the static banner method."""

    def test_banner_outputs_text(self, capsys):
        ConsoleFormatter.banner("Initialization")
        captured = capsys.readouterr()
        assert "Initialization" in captured.out

    def test_banner_has_separators(self, capsys):
        ConsoleFormatter.banner("Test Phase")
        captured = capsys.readouterr()
        # Should contain the double-line separator character
        assert "\u2550" in captured.out

    def test_banner_custom_width(self, capsys):
        ConsoleFormatter.banner("Narrow", width=20)
        captured = capsys.readouterr()
        lines = [line for line in captured.out.split("\n") if "\u2550" in line]
        # Each separator line should be exactly 20 chars of the box char
        for line in lines:
            assert len(line.strip()) == 20

    def test_banner_default_width(self, capsys):
        ConsoleFormatter.banner("Default Width")
        captured = capsys.readouterr()
        lines = [line for line in captured.out.split("\n") if "\u2550" in line]
        for line in lines:
            assert len(line.strip()) == 50
