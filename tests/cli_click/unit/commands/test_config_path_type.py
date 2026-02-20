"""
Tests for str vs Path type handling in CLI commands.

Verifies that click.Path() string return values are properly
converted to pathlib.Path before calling Path methods.
"""

import pytest

from panther.cli_click.core.main import cli


@pytest.mark.unit
class TestConfigDesignPathType:
    """Verify config design handles click.Path() str correctly."""

    def test_design_non_interactive_with_string_path(self, cli_runner, temp_dir):
        """click.Path() returns str; design() must not crash on .exists()/.parent."""
        output_file = temp_dir / "design_output.yaml"
        result = cli_runner.invoke(
            cli,
            [
                "config",
                "design",
                "--output",
                str(output_file),
                "--non-interactive",
            ],
        )
        assert result.exit_code == 0, f"Crashed: {result.output}"
        assert output_file.exists()

    def test_design_non_interactive_quick(self, cli_runner, temp_dir):
        """Reproduce the exact command from the bug report."""
        output_file = temp_dir / "quick_output.yaml"
        result = cli_runner.invoke(
            cli,
            [
                "config",
                "design",
                "--output",
                str(output_file),
                "--non-interactive",
                "--quick",
            ],
        )
        assert result.exit_code == 0, f"Crashed: {result.output}"
        assert output_file.exists()
        content = output_file.read_text()
        assert "Auto-generated PANTHER Configuration" in content

    def test_design_overwrite_prompt_with_string_path(self, cli_runner, temp_dir):
        """Existing file check must work with str path."""
        output_file = temp_dir / "existing.yaml"
        output_file.write_text("existing content")

        result = cli_runner.invoke(
            cli,
            ["config", "design", "--output", str(output_file)],
            input="n\n",
        )
        assert result.exit_code == 0
        # "Design session cancelled" goes through info_message -> logger,
        # not click.echo, so it won't appear in result.output.
        # Verify the overwrite prompt appeared and file was NOT overwritten.
        assert "already exists. Overwrite?" in result.output
        assert output_file.read_text() == "existing content"

    def test_design_creates_parent_directories(self, cli_runner, temp_dir):
        """parent.mkdir() must work when parent dir doesn't exist."""
        output_file = temp_dir / "nested" / "dir" / "config.yaml"
        result = cli_runner.invoke(
            cli,
            [
                "config",
                "design",
                "--output",
                str(output_file),
                "--non-interactive",
            ],
        )
        assert result.exit_code == 0, f"Crashed: {result.output}"
        assert output_file.exists()


@pytest.mark.unit
class TestTutorialPathType:
    """Verify tutorial.py has the Path conversion fix."""

    def test_tutorial_source_has_path_conversion(self):
        """Verify tutorial.py converts output_dir str to Path before .mkdir()."""
        from pathlib import Path

        import panther.cli_click.commands.tutorial as tutorial_mod

        source = Path(tutorial_mod.__file__).read_text()
        # Verify Path conversion appears before .mkdir() call
        conversion_pos = source.find("Path(output_dir)")
        mkdir_pos = source.find("output_dir.mkdir(")
        assert conversion_pos != -1, "Path(output_dir) conversion missing"
        assert mkdir_pos != -1, "output_dir.mkdir() call missing"
        assert conversion_pos < mkdir_pos, "Path conversion must come before .mkdir()"
