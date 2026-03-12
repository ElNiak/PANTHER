"""Tests for panther.core.reporting.experiment_reporter."""

import pytest

from panther.core.reporting.experiment_reporter import ExperimentReporter

pytestmark = [pytest.mark.unit]


def _make_minimal_experiment_dir(tmp_path):
    """Create a minimal experiment directory that produces a report."""
    exp_dir = tmp_path / "2026-01-01_00-00-00"
    exp_dir.mkdir()
    (exp_dir / "experiment.log").write_text(
        "2026-01-01 00:00:00 [INFO] - test - Experiment started\n"
        "2026-01-01 00:01:00 [INFO] - test - Experiment completed\n"
    )
    test_dir = exp_dir / "0_Test"
    test_dir.mkdir()
    (test_dir / "test.log").write_text(
        "2026-01-01 00:00:01 [INFO] - test completed successfully\n"
    )
    return exp_dir


class TestMarkdownReportEscaping:
    """Verify Markdown reports don't have HTML entity escaping."""

    def test_markdown_report_no_html_escaping(self, tmp_path):
        """Markdown reports should not have HTML entity escaping."""
        exp_dir = tmp_path / "2026-01-01_00-00-00"
        exp_dir.mkdir()
        (exp_dir / "experiment.log").write_text(
            '2026-01-01 00:00:00 [INFO] - test - Error: "something failed"\n'
            "2026-01-01 00:01:00 [INFO] - test - Done\n"
        )
        test_dir = exp_dir / "0_Test"
        test_dir.mkdir()
        (test_dir / "test.log").write_text(
            '2026-01-01 00:00:00 [ERROR] - test - Failed: "assertion error"\n'
        )

        reporter = ExperimentReporter(exp_dir, "2026-01-01_00-00-00")
        reporter.generate_reports()

        report_path = exp_dir / "EXPERIMENT_REPORT.md"
        if report_path.exists():
            content = report_path.read_text()
            assert (
                "&#34;" not in content
            ), "Markdown report should not contain HTML entities"
            assert (
                "&amp;" not in content
            ), "Markdown report should not contain HTML entities"


class TestMarkdownNewlines:
    """Verify Markdown sections are properly separated by newlines."""

    def test_markdown_sections_separated_by_newlines(self, tmp_path):
        """Markdown sections should not be concatenated on single lines."""
        exp_dir = _make_minimal_experiment_dir(tmp_path)

        reporter = ExperimentReporter(exp_dir, "2026-01-01_00-00-00")
        reporter.generate_reports()

        report_path = exp_dir / "EXPERIMENT_REPORT.md"
        assert report_path.exists(), "Report should be generated"
        content = report_path.read_text()

        # No two markdown list items should be concatenated on the same line
        assert "0- " not in content, "Skipped and Success Rate concatenated"

    def test_markdown_list_items_on_separate_lines(self, tmp_path):
        """Each markdown list item should be on its own line."""
        exp_dir = _make_minimal_experiment_dir(tmp_path)

        reporter = ExperimentReporter(exp_dir, "2026-01-01_00-00-00")
        reporter.generate_reports()

        report_path = exp_dir / "EXPERIMENT_REPORT.md"
        content = report_path.read_text()

        # Find all lines that start with "- **" (markdown list items)
        lines = content.split("\n")
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith("- **"):
                # Should not contain another "- **" on the same line
                rest = stripped[4:]
                assert (
                    "- **" not in rest
                ), f"Multiple list items on line {i + 1}: {stripped}"
