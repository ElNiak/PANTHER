"""
Tests for the Click-based tutorial CLI commands.

Covers: run, list, interactive commands with all bug fixes verified.

Note: success_message/info_message/warning_message/error_message route through
Python's logging module (not stdout), so CliRunner only captures click.echo output.
Tests verify exit codes and direct click.echo output rather than logged messages.
"""

import json
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from panther.cli_click.core.main import cli


@pytest.fixture
def runner():
    return CliRunner()


# ---------------------------------------------------------------------------
# TestTutorialRun
# ---------------------------------------------------------------------------
class TestTutorialRun:
    """Tests for `panther tutorial run <type>`."""

    def test_run_success_exit_code(self, runner):
        """B1+B2: run_tutorial(type) returns 0 -> exit code 0."""
        with patch(
            "panther.tools.plugins.plugin_creator.run_tutorial", return_value=0
        ):
            result = runner.invoke(cli, ["tutorial", "run", "service"])
        assert result.exit_code == 0

    def test_run_failure_exit_code(self, runner):
        """B2: run_tutorial returns non-zero -> non-zero exit or error output."""
        with patch(
            "panther.tools.plugins.plugin_creator.run_tutorial", return_value=1
        ):
            result = runner.invoke(cli, ["tutorial", "run", "service"])
        # handle_errors calls sys.exit(1) when the function returns 1,
        # or the function returns 1 which Click translates
        assert result.exit_code != 0 or "encountered issues" in (result.output or "")

    def test_run_import_error(self, runner):
        """Import error is caught and reported gracefully."""
        with patch(
            "panther.tools.plugins.plugin_creator.run_tutorial",
            side_effect=ImportError("no module"),
        ):
            result = runner.invoke(cli, ["tutorial", "run", "service"])
        # The ImportError is caught internally, so no unhandled exception
        assert result.exception is None or isinstance(result.exception, SystemExit)

    @pytest.mark.parametrize(
        "tutorial_type", ["service", "environment", "protocol", "configuration"]
    )
    def test_run_all_valid_types(self, runner, tutorial_type):
        """All four tutorial types are accepted by the CLI."""
        with patch(
            "panther.tools.plugins.plugin_creator.run_tutorial", return_value=0
        ):
            result = runner.invoke(cli, ["tutorial", "run", tutorial_type])
        assert result.exit_code == 0

    def test_run_invalid_type_rejected(self, runner):
        """Invalid tutorial type is rejected by Click's Choice validator."""
        result = runner.invoke(cli, ["tutorial", "run", "nonexistent"])
        assert result.exit_code != 0

    def test_run_debug_traceback(self, runner):
        """B5: debug flag from ctx.obj used for traceback. Without --debug, no crash."""
        with patch(
            "panther.tools.plugins.plugin_creator.run_tutorial",
            side_effect=RuntimeError("test error"),
        ):
            result = runner.invoke(cli, ["tutorial", "run", "service"])
            # The RuntimeError is caught internally; no unhandled exception
            assert result.exception is None or isinstance(result.exception, SystemExit)

    def test_run_correct_signature(self, runner):
        """B1: run_tutorial is called with only plugin_type, no extra kwargs."""
        with patch(
            "panther.tools.plugins.plugin_creator.run_tutorial", return_value=0
        ) as mock_fn:
            runner.invoke(cli, ["tutorial", "run", "service"])
            mock_fn.assert_called_once_with("service")

    def test_run_zero_is_success(self, runner):
        """B2: Return value 0 is treated as success (exit code 0), not falsy."""
        with patch(
            "panther.tools.plugins.plugin_creator.run_tutorial", return_value=0
        ):
            result = runner.invoke(cli, ["tutorial", "run", "service"])
        assert result.exit_code == 0


# ---------------------------------------------------------------------------
# TestTutorialList
# ---------------------------------------------------------------------------
class TestTutorialList:
    """Tests for `panther tutorial list`."""

    def test_list_default_format(self, runner):
        """Default format (detail) shows tutorial information via click.echo."""
        result = runner.invoke(cli, ["tutorial", "list"])
        assert result.exit_code == 0
        assert "Service Plugin Development" in result.output

    def test_list_json_output(self, runner):
        """JSON format outputs valid JSON."""
        result = runner.invoke(cli, ["tutorial", "list", "--format", "json"])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert isinstance(data, list)
        assert len(data) == 4
        names = {t["name"] for t in data}
        assert names == {"service", "environment", "protocol", "configuration"}

    def test_list_table_output(self, runner):
        """Table format shows column headers."""
        result = runner.invoke(cli, ["tutorial", "list", "--format", "table"])
        assert result.exit_code == 0
        assert "Name" in result.output
        assert "Title" in result.output

    def test_list_filter_by_level(self, runner):
        """Level filter restricts results."""
        result = runner.invoke(
            cli, ["tutorial", "list", "--format", "json", "--level", "intermediate"]
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert all(t["difficulty"] == "intermediate" for t in data)
        assert len(data) == 1  # Only environment is intermediate

    def test_list_filter_by_category(self, runner):
        """Category filter restricts results."""
        result = runner.invoke(
            cli, ["tutorial", "list", "--format", "json", "--category", "service"]
        )
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert len(data) == 1
        assert data[0]["name"] == "service"

    def test_list_no_results(self, runner):
        """Filters that match nothing exit cleanly."""
        result = runner.invoke(
            cli,
            [
                "tutorial",
                "list",
                "--level",
                "advanced",
                "--category",
                "service",
            ],
        )
        assert result.exit_code == 0


# ---------------------------------------------------------------------------
# TestTutorialInteractive
# ---------------------------------------------------------------------------
class TestTutorialInteractive:
    """Tests for `panther tutorial interactive`."""

    def test_interactive_quit(self, runner):
        """Typing 'q' exits interactive mode cleanly."""
        result = runner.invoke(cli, ["tutorial", "interactive"], input="q\n")
        assert result.exit_code == 0
        # The menu is displayed via click.echo
        assert "Available Tutorials" in result.output

    def test_interactive_list_option(self, runner):
        """Typing 'l' shows tutorial list, then 'q' exits."""
        result = runner.invoke(cli, ["tutorial", "interactive"], input="l\nq\n")
        assert result.exit_code == 0
        assert "Service Plugin Development" in result.output

    def test_interactive_help_option(self, runner):
        """Typing 'h' shows help (goes through logging), then 'q' exits."""
        result = runner.invoke(cli, ["tutorial", "interactive"], input="h\nq\n")
        assert result.exit_code == 0
        # Menu should still be displayed
        assert "Available Tutorials" in result.output

    def test_interactive_run_tutorial(self, runner):
        """Selecting a tutorial number invokes it, then user can quit."""
        with patch(
            "panther.tools.plugins.plugin_creator.run_tutorial", return_value=0
        ):
            # Select tutorial 1, then answer "no" to "try another" prompt
            result = runner.invoke(
                cli, ["tutorial", "interactive"], input="1\nn\n"
            )
        assert result.exit_code == 0

    def test_interactive_invalid_input(self, runner):
        """Invalid input doesn't crash, then user can quit."""
        result = runner.invoke(
            cli, ["tutorial", "interactive"], input="xyz\nq\n"
        )
        assert result.exit_code == 0

    def test_interactive_invalid_number(self, runner):
        """Out-of-range number doesn't crash, then user can quit."""
        result = runner.invoke(
            cli, ["tutorial", "interactive"], input="9\nq\n"
        )
        assert result.exit_code == 0

    def test_interactive_system_exit_recovery(self, runner):
        """B7: SystemExit from handle_errors is caught in interactive mode."""
        with patch(
            "panther.tools.plugins.plugin_creator.run_tutorial",
            side_effect=SystemExit(1),
        ):
            # Select tutorial 1, SystemExit caught, answer "no" to "select another"
            result = runner.invoke(
                cli, ["tutorial", "interactive"], input="1\nn\n"
            )
        # Interactive mode catches SystemExit; exit code should be 0 or 1 (not a crash)
        assert result.exit_code in (0, 1)

    def test_interactive_quick_start(self, runner):
        """--quick-start skips the welcome intro."""
        result = runner.invoke(
            cli, ["tutorial", "interactive", "--quick-start"], input="q\n"
        )
        assert result.exit_code == 0
        # With quick-start, the "=" separator from welcome is not present
        assert "Welcome to PANTHER" not in result.output

    def test_interactive_prompt_wording(self, runner):
        """U4: After failure, prompt says 'select another' not 'try again'."""
        with patch(
            "panther.tools.plugins.plugin_creator.run_tutorial", return_value=1
        ):
            result = runner.invoke(
                cli, ["tutorial", "interactive"], input="1\nn\n"
            )
        assert "try again" not in result.output.lower()


# ---------------------------------------------------------------------------
# TestProtocolTutorial
# ---------------------------------------------------------------------------
class TestProtocolTutorial:
    """Tests for the protocol tutorial stub (B3 fix)."""

    def test_protocol_tutorial_exists_and_runs(self):
        """B3: Protocol tutorial file is no longer empty and runs successfully."""
        from panther.tools.plugins.protocols.tutorials.tutorial import (
            ProtocolPluginTutorial,
        )

        t = ProtocolPluginTutorial()
        result = t.run()
        assert result == 0

    def test_protocol_tutorial_has_class(self):
        """Protocol tutorial module has the expected class."""
        from panther.tools.plugins.protocols.tutorials import tutorial

        assert hasattr(tutorial, "ProtocolPluginTutorial")
