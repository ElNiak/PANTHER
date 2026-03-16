"""Report Command.

Manage experiment reports with generation, viewing, and listing capabilities.
Wraps the reporting subsystem (ExperimentReporter, StatusCollector) for CLI use.
"""

from datetime import datetime
from pathlib import Path
from typing import List, Tuple

import click
from termcolor import colored

from panther.cli.core.base import (
    error_message,
    featured_example,
    handle_errors,
    pass_context_and_setup_logging,
    warning_message,
)


def _info(msg: str) -> None:
    """Print an info message."""
    click.echo(colored(f"  {msg}", "blue"))


def _success(msg: str) -> None:
    """Print a success message."""
    click.echo(colored(f"  {msg}", "green"))


# -- list helpers --


def _find_experiment_dirs(output_dir: str) -> List[Tuple[Path, datetime, float]]:
    """Walk output directory for experiment directories.

    Looks for subdirectories inside dated parent directories (e.g.
    outputs/2024-01-01/exp1). Returns list of (path, mtime, size_mb).
    """
    root = Path(output_dir)
    if not root.exists():
        return []

    experiments: List[Tuple[Path, datetime, float]] = []
    try:
        for date_dir in sorted(root.iterdir()):
            if not date_dir.is_dir():
                continue
            for exp_dir in sorted(date_dir.iterdir()):
                if not exp_dir.is_dir():
                    continue
                try:
                    mtime = datetime.fromtimestamp(exp_dir.stat().st_mtime)
                    size = sum(
                        f.stat().st_size for f in exp_dir.rglob("*") if f.is_file()
                    )
                    experiments.append((exp_dir, mtime, size / (1024 * 1024)))
                except OSError:
                    continue
    except OSError:
        pass

    return experiments


def _display_experiment_list(experiments: List[Tuple[Path, datetime, float]]) -> None:
    """Display a table of experiment directories."""
    click.echo(colored("  Experiment Directories:", "cyan", attrs=["bold"]))
    click.echo()
    click.echo(f"    {'Directory':<50} {'Modified':<20} {'Size':>10}")
    click.echo(f"    {'-' * 50} {'-' * 20} {'-' * 10}")
    for exp_path, mtime, size_mb in experiments:
        rel = str(exp_path)
        date_str = mtime.strftime("%Y-%m-%d %H:%M")
        click.echo(f"    {rel:<50} {date_str:<20} {size_mb:>8.1f} MB")


# -- show helpers --


def _display_test_results(summary) -> None:
    """Display test results section."""
    click.echo(colored("  Test Results:", "cyan", attrs=["bold"]))
    click.echo(f"    Total:       {summary.total_tests}")
    click.echo(colored(f"    Passed:      {summary.passed_tests}", "green"))
    if summary.failed_tests:
        click.echo(colored(f"    Failed:      {summary.failed_tests}", "red"))
    else:
        click.echo(f"    Failed:      {summary.failed_tests}")
    click.echo(f"    Skipped:     {summary.skipped_tests}")
    click.echo(f"    Timeout:     {summary.timeout_tests}")
    click.echo(f"    Interrupted: {summary.interrupted_tests}")
    click.echo(f"    Unknown:     {summary.unknown_tests}")
    click.echo(f"    Success Rate: {summary.success_rate:.1f}%")
    click.echo()


def _display_service_health(summary) -> None:
    """Display service health section."""
    if not summary.services:
        return
    click.echo(colored("  Service Health:", "cyan", attrs=["bold"]))
    for svc in summary.services:
        status_color = "green" if svc.status == "healthy" else "red"
        comp = "OK" if svc.compilation_succeeded else "FAIL"
        ec = str(svc.exit_code) if svc.exit_code is not None else "N/A"
        line = f"    {svc.service_name} ({svc.service_type}): {svc.status}  compile={comp}  exit={ec}"
        click.echo(colored(line, status_color))
        if svc.error_summary:
            click.echo(colored(f"      Error: {svc.error_summary}", "red"))
    click.echo()


def _display_fast_fail(summary) -> None:
    """Display fast-fail analysis section."""
    ff = summary.fast_fail
    click.echo(colored("  Fast-Fail:", "cyan", attrs=["bold"]))
    click.echo(f"    Enabled:     {ff.enabled}")
    click.echo(f"    Test-Level:  {ff.test_level}")
    if ff.triggered:
        click.echo(colored(f"    Triggered:   Yes", "red"))
        if ff.reason:
            click.echo(colored(f"    Reason:      {ff.reason}", "red"))
        if ff.error_category:
            click.echo(f"    Category:    {ff.error_category}")
    else:
        click.echo(f"    Triggered:   No")
    click.echo()


def _display_resources(summary) -> None:
    """Display resource usage section."""
    res = summary.resources
    has_data = any(
        [
            res.peak_memory_mb,
            res.disk_usage_mb,
            res.docker_images_created,
            res.total_log_size_mb,
        ]
    )
    if not has_data:
        return
    click.echo(colored("  Resource Usage:", "cyan", attrs=["bold"]))
    if res.peak_memory_mb:
        click.echo(f"    Peak Memory:    {res.peak_memory_mb:.1f} MB")
    if res.disk_usage_mb:
        click.echo(f"    Disk Usage:     {res.disk_usage_mb:.1f} MB")
    if res.docker_images_created:
        click.echo(f"    Docker Images:  {res.docker_images_created}")
    if res.total_log_size_mb:
        click.echo(f"    Total Log Size: {res.total_log_size_mb:.1f} MB")
    click.echo()


# ========== Commands ==========


@featured_example("panther report list")
@click.group()
def report():
    r"""Manage experiment reports.

    Generate, view, and list experiment reports from output directories.

    \b
    Examples:
      panther report list                       # List experiments
      panther report show outputs/2024-01-01/exp1   # Show detailed summary
      panther report generate outputs/2024-01-01/exp1  # Generate reports
      panther report summary outputs/2024-01-01/exp1   # Quick summary
    """


@report.command("generate")
@click.argument("experiment_dir", type=click.Path(exists=True))
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["json", "markdown", "text", "all"]),
    default="all",
    help="Report format to generate (default: all)",
)
@handle_errors
@pass_context_and_setup_logging
def generate(_ctx, experiment_dir, fmt):
    r"""Generate reports from an experiment output directory.

    \b
    Examples:
      panther report generate outputs/2024-01-01/exp1
      panther report generate outputs/2024-01-01/exp1 --format json
    """
    from panther.core.reporting.experiment_reporter import ExperimentReporter

    exp_path = Path(experiment_dir)
    reporter = ExperimentReporter(exp_path, exp_path.name)

    _info(f"Generating {fmt} report(s) for: {exp_path.name}")
    results = reporter.generate_reports()

    for report_type, success in results.items():
        if success:
            _success(f"{report_type}: generated")
        else:
            warning_message(f"{report_type}: failed")

    succeeded = sum(1 for v in results.values() if v)
    if succeeded:
        _success(f"Generated {succeeded} report(s) in {exp_path}")
    else:
        error_message("No reports were generated successfully")


@report.command("summary")
@click.argument("experiment_dir", type=click.Path(exists=True))
@handle_errors
@pass_context_and_setup_logging
def summary(_ctx, experiment_dir):
    r"""Quick one-line experiment summary.

    \b
    Examples:
      panther report summary outputs/2024-01-01/exp1
    """
    from panther.core.reporting.experiment_reporter import ExperimentReporter

    exp_path = Path(experiment_dir)
    reporter = ExperimentReporter(exp_path)
    result = reporter.generate_quick_summary()

    if result:
        click.echo(result)
    else:
        warning_message("Could not generate summary for this experiment")


@report.command("list")
@click.option(
    "--output-dir",
    type=click.Path(),
    default="outputs",
    help="Root output directory (default: outputs)",
)
@handle_errors
@pass_context_and_setup_logging
def list_experiments(_ctx, output_dir):
    r"""List experiment output directories.

    \b
    Examples:
      panther report list
      panther report list --output-dir /path/to/outputs
    """
    experiments = _find_experiment_dirs(output_dir)

    if not experiments:
        warning_message(f"No experiment directories found in {output_dir}/")
        _info("Run experiments first, then check this listing.")
        return

    _display_experiment_list(experiments)
    click.echo()
    _success(f"Found {len(experiments)} experiment(s)")


@report.command("show")
@click.argument("experiment_dir", type=click.Path(exists=True))
@handle_errors
@pass_context_and_setup_logging
def show(_ctx, experiment_dir):
    r"""Detailed experiment summary.

    Shows test results (passed/failed/skipped), service health,
    fast-fail status, and resource usage.

    \b
    Examples:
      panther report show outputs/2024-01-01/exp1
    """
    from panther.core.reporting.status_collector import StatusCollector

    exp_path = Path(experiment_dir)
    collector = StatusCollector(exp_path)
    exp_summary = collector.collect_experiment_summary()

    click.echo(colored("Experiment Report", "blue", attrs=["bold"]))
    click.echo(colored("=" * 60, "blue"))
    click.echo(colored(f"  ID:     {exp_summary.experiment_id}", "blue"))
    click.echo(colored(f"  Status: {exp_summary.status.value.upper()}", "blue"))
    if exp_summary.start_time:
        click.echo(f"  Start:  {exp_summary.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
    if exp_summary.end_time:
        click.echo(f"  End:    {exp_summary.end_time.strftime('%Y-%m-%d %H:%M:%S')}")
    if exp_summary.configuration_file:
        click.echo(f"  Config: {exp_summary.configuration_file}")
    click.echo()

    _display_test_results(exp_summary)
    _display_service_health(exp_summary)
    _display_fast_fail(exp_summary)
    _display_resources(exp_summary)

    _success("Report displayed")


if __name__ == "__main__":
    report()
