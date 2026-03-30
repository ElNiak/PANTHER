"""Tests for DockerOutputParser verbose-aware output formatting.

Validates that the parser produces concise output by default and
detailed output when verbose mode is enabled.
"""

import logging
from unittest.mock import patch

import pytest

from panther.core.docker_builder.utils.docker_output_parser import DockerOutputParser

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def concise_parser():
    """Parser in concise (non-verbose) mode."""
    return DockerOutputParser(verbose=False)


@pytest.fixture
def verbose_parser():
    """Parser in verbose mode."""
    return DockerOutputParser(verbose=True)


@pytest.fixture
def auto_parser():
    """Parser that reads verbose from LoggerFactory._verbose."""
    return DockerOutputParser()


# ---------------------------------------------------------------------------
# verbose property
# ---------------------------------------------------------------------------


class TestVerboseProperty:
    """Tests for the ``verbose`` property and its auto-detection."""

    def test_explicit_verbose_true(self, verbose_parser):
        assert verbose_parser.verbose is True

    def test_explicit_verbose_false(self, concise_parser):
        assert concise_parser.verbose is False

    def test_auto_reads_logger_factory_verbose(self, auto_parser):
        from panther.core.utils.logger_factory import LoggerFactory

        original = LoggerFactory._verbose
        try:
            LoggerFactory._verbose = True
            assert auto_parser.verbose is True

            LoggerFactory._verbose = False
            assert auto_parser.verbose is False
        finally:
            LoggerFactory._verbose = original


# ---------------------------------------------------------------------------
# Step parsing -- concise mode
# ---------------------------------------------------------------------------


class TestConciseStepParsing:
    """In concise mode, step lines should be short one-liners."""

    def test_run_step_shows_label_only(self, concise_parser):
        line = "Step 5/12 : RUN apt-get update && apt-get install -y curl wget git build-essential cmake ninja-build"
        result = concise_parser.parse_line(line)
        assert result is not None
        message, progress, level = result
        assert message == "Step 5/12: Run"
        assert level == "INFO"
        assert 40 < progress < 43  # ~41.67%

    def test_from_step_shows_base_image(self, concise_parser):
        line = "Step 1/12 : FROM ubuntu:22.04 AS base"
        result = concise_parser.parse_line(line)
        assert result is not None
        message, _progress, _level = result
        assert message == "Step 1/12: Base image"

    def test_copy_step_shows_copy_files(self, concise_parser):
        line = "Step 8/12 : COPY --from=builder /opt/picoquic /opt/picoquic"
        result = concise_parser.parse_line(line)
        assert result is not None
        message, _progress, _level = result
        assert message == "Step 8/12: Copy files"

    def test_add_step_shows_add_files(self, concise_parser):
        line = "Step 3/12 : ADD . /src"
        result = concise_parser.parse_line(line)
        assert result is not None
        message, _progress, _level = result
        assert message == "Step 3/12: Add files"

    def test_env_step_shows_set_env(self, concise_parser):
        line = "Step 4/12 : ENV DEBIAN_FRONTEND=noninteractive"
        result = concise_parser.parse_line(line)
        assert result is not None
        message, _progress, _level = result
        assert message == "Step 4/12: Set env"

    def test_workdir_step_shows_set_workdir(self, concise_parser):
        line = "Step 6/12 : WORKDIR /opt/picoquic"
        result = concise_parser.parse_line(line)
        assert result is not None
        message, _progress, _level = result
        assert message == "Step 6/12: Set workdir"

    def test_arg_step_shows_build_arg(self, concise_parser):
        line = "Step 2/12 : ARG VERSION=production"
        result = concise_parser.parse_line(line)
        assert result is not None
        message, _progress, _level = result
        assert message == "Step 2/12: Build arg"


# ---------------------------------------------------------------------------
# Step parsing -- verbose mode
# ---------------------------------------------------------------------------


class TestVerboseStepParsing:
    """In verbose mode, step lines should show the full instruction."""

    def test_run_step_no_truncation(self, verbose_parser):
        long_run = "RUN apt-get update && apt-get install -y curl wget git build-essential cmake ninja-build libssl-dev pkg-config"
        line = f"Step 5/12 : {long_run}"
        result = verbose_parser.parse_line(line)
        assert result is not None
        message, _progress, _level = result
        assert message == f"Step 5/12: {long_run}"
        assert "..." not in message

    def test_from_step_full_detail(self, verbose_parser):
        line = "Step 1/12 : FROM ubuntu:22.04 AS base"
        result = verbose_parser.parse_line(line)
        assert result is not None
        message, _progress, _level = result
        assert message == "Step 1/12: FROM ubuntu:22.04 AS base"


# ---------------------------------------------------------------------------
# Download / extract suppression
# ---------------------------------------------------------------------------


class TestDownloadExtractHandling:
    """Download and extract lines are suppressed in concise mode."""

    # The regex expects [=>-]+ with no spaces inside the progress bar,
    # followed by size values like 50.5MB/100MB.
    DOWNLOAD_LINE = "Downloading [==========>---------] 50.5MB/100MB"
    EXTRACT_LINE = "Extracting [==========>---------] 50.5MB/100MB"

    def test_download_suppressed_in_concise(self, concise_parser):
        result = concise_parser.parse_line(self.DOWNLOAD_LINE)
        assert result is None

    def test_download_shown_in_verbose(self, verbose_parser):
        result = verbose_parser.parse_line(self.DOWNLOAD_LINE)
        assert result is not None
        message, _progress, level = result
        assert "Downloading" in message
        assert level == "DEBUG"

    def test_extract_suppressed_in_concise(self, concise_parser):
        result = concise_parser.parse_line(self.EXTRACT_LINE)
        assert result is None

    def test_extract_shown_in_verbose(self, verbose_parser):
        result = verbose_parser.parse_line(self.EXTRACT_LINE)
        assert result is not None
        message, _progress, level = result
        assert "Extracting" in message
        assert level == "DEBUG"


# ---------------------------------------------------------------------------
# Shared behavior (same in both modes)
# ---------------------------------------------------------------------------


class TestSharedBehavior:
    """Behavior that does not change between concise and verbose modes."""

    @pytest.mark.parametrize("verbose", [True, False])
    def test_error_lines_always_returned(self, verbose):
        parser = DockerOutputParser(verbose=verbose)
        line = "ERROR: failed to solve: process returned non-zero exit code"
        result = parser.parse_line(line)
        assert result is not None
        _message, _progress, level = result
        assert level == "ERROR"

    @pytest.mark.parametrize("verbose", [True, False])
    def test_warning_lines_always_returned(self, verbose):
        parser = DockerOutputParser(verbose=verbose)
        line = "WARNING: IPv4 forwarding is disabled"
        result = parser.parse_line(line)
        assert result is not None
        _message, _progress, level = result
        assert level == "WARNING"

    @pytest.mark.parametrize("verbose", [True, False])
    def test_build_context_always_returned(self, verbose):
        parser = DockerOutputParser(verbose=verbose)
        line = "Sending build context to Docker daemon  150.5MB"
        result = parser.parse_line(line)
        assert result is not None
        message, _progress, level = result
        assert "150.5MB" in message
        assert level == "INFO"

    @pytest.mark.parametrize("verbose", [True, False])
    def test_empty_line_skipped(self, verbose):
        parser = DockerOutputParser(verbose=verbose)
        assert parser.parse_line("") is None
        assert parser.parse_line("   ") is None

    @pytest.mark.parametrize("verbose", [True, False])
    def test_already_exists_skipped(self, verbose):
        parser = DockerOutputParser(verbose=verbose)
        assert parser.parse_line("Already exists") is None

    @pytest.mark.parametrize("verbose", [True, False])
    def test_pull_message_returned(self, verbose):
        parser = DockerOutputParser(verbose=verbose)
        result = parser.parse_line("Pulling from library/ubuntu")
        assert result is not None
        message, _progress, level = result
        assert "library/ubuntu" in message
        assert level == "INFO"

    @pytest.mark.parametrize("verbose", [True, False])
    def test_layer_ids_skipped(self, verbose):
        parser = DockerOutputParser(verbose=verbose)
        result = parser.parse_line(" ---> abc123def456")
        assert result is None

    @pytest.mark.parametrize("verbose", [True, False])
    def test_success_keywords_returned(self, verbose):
        parser = DockerOutputParser(verbose=verbose)
        result = parser.parse_line("Successfully tagged myimage:latest")
        assert result is not None
        _message, _progress, level = result
        assert level == "INFO"


# ---------------------------------------------------------------------------
# Progress tracking
# ---------------------------------------------------------------------------


class TestProgressTracking:
    """Verify that step/total counters update correctly."""

    def test_progress_updates_across_steps(self, concise_parser):
        concise_parser.parse_line("Step 1/10 : FROM ubuntu:22.04")
        assert concise_parser.current_step == 1
        assert concise_parser.total_steps == 10

        concise_parser.parse_line("Step 5/10 : RUN echo hello")
        assert concise_parser.current_step == 5
        assert concise_parser.total_steps == 10

    def test_get_summary_with_steps(self, concise_parser):
        concise_parser.parse_line("Step 10/10 : CMD echo done")
        summary = concise_parser.get_summary()
        assert "10/10" in summary

    def test_get_summary_no_steps(self, concise_parser):
        summary = concise_parser.get_summary()
        assert summary == "Docker build completed"


# ---------------------------------------------------------------------------
# LoggerFactory._verbose integration
# ---------------------------------------------------------------------------


class TestLoggerFactoryVerboseFlag:
    """Verify that LoggerFactory._verbose is set by set_console_level."""

    def test_set_console_level_debug_sets_verbose(self):
        from panther.core.utils.logger_factory import LoggerFactory

        # Save original state
        original = LoggerFactory._verbose

        try:
            LoggerFactory._verbose = False
            LoggerFactory._initialized = True
            LoggerFactory.set_console_level(logging.DEBUG)
            assert LoggerFactory._verbose is True
        finally:
            LoggerFactory._verbose = original

    def test_set_console_level_info_clears_verbose(self):
        from panther.core.utils.logger_factory import LoggerFactory

        original = LoggerFactory._verbose

        try:
            LoggerFactory._verbose = True
            LoggerFactory._initialized = True
            LoggerFactory.set_console_level(logging.INFO)
            assert LoggerFactory._verbose is False
        finally:
            LoggerFactory._verbose = original


# ---------------------------------------------------------------------------
# format_progress_bar (unchanged, but verify it still works)
# ---------------------------------------------------------------------------


class TestFormatProgressBar:
    """Progress bar formatting helper."""

    def test_zero_progress(self, concise_parser):
        bar = concise_parser.format_progress_bar(0)
        assert bar == "[--------------------] 0%"

    def test_full_progress(self, concise_parser):
        bar = concise_parser.format_progress_bar(100)
        assert bar == "[====================] 100%"

    def test_half_progress(self, concise_parser):
        bar = concise_parser.format_progress_bar(50)
        assert "==========----------" in bar


# ---------------------------------------------------------------------------
# _concise_step_label
# ---------------------------------------------------------------------------


class TestConciseStepLabel:
    """Verify the label mapping for Docker instructions."""

    def test_known_instructions(self, concise_parser):
        assert concise_parser._concise_step_label("RUN apt-get update") == "Run"
        assert concise_parser._concise_step_label("COPY . /app") == "Copy files"
        assert concise_parser._concise_step_label("FROM ubuntu") == "Base image"
        assert concise_parser._concise_step_label("ENV FOO=bar") == "Set env"
        assert concise_parser._concise_step_label("WORKDIR /opt") == "Set workdir"

    def test_unknown_instruction_capitalized(self, concise_parser):
        assert (
            concise_parser._concise_step_label("HEALTHCHECK --interval=30s CMD curl")
            == "Healthcheck"
        )

    def test_empty_string(self, concise_parser):
        assert concise_parser._concise_step_label("") == ""
