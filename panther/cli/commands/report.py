"""Report Command.

Manage experiment reports with generation, viewing, and listing capabilities.
Wraps the reporting subsystem (ExperimentReporter, StatusCollector) for CLI use.
Includes timeline and artifact browsing subcommands.
"""

import json
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


# -- timeline helpers --


def _parse_time(value: str) -> datetime:
    """Parse a time string into a datetime.

    Accepts ISO-8601 format (e.g. ``2025-01-15T10:00:00+00:00``) as well
    as a bare time like ``10:00:00`` (interpreted as today, UTC).

    Args:
        value: Time string to parse.

    Returns:
        Parsed datetime.

    Raises:
        click.BadParameter: If the string cannot be parsed.
    """
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        pass
    try:
        from datetime import timezone

        t = datetime.strptime(value, "%H:%M:%S").time()
        return datetime.combine(
            datetime.now(timezone.utc).date(), t, tzinfo=timezone.utc
        )
    except ValueError:
        raise click.BadParameter(f"Cannot parse time: {value!r}")


@report.command("timeline")
@click.argument("experiment_dir", type=click.Path(exists=True))
@click.option("--test", "test_id", default=None, help="Filter by test_id")
@click.option("--service", "service_id", default=None, help="Filter by service_id")
@click.option(
    "--after",
    "after_str",
    default=None,
    help="Include entries at or after this time (ISO-8601)",
)
@click.option(
    "--before",
    "before_str",
    default=None,
    help="Include entries strictly before this time (ISO-8601)",
)
@click.option(
    "--limit",
    default=50,
    type=int,
    show_default=True,
    help="Maximum entries to display",
)
@click.option(
    "--json",
    "output_json",
    is_flag=True,
    default=False,
    help="Output as JSON (default)",
)
@click.option(
    "--human",
    "output_human",
    is_flag=True,
    default=False,
    help="Output as human-readable swimlane",
)
@handle_errors
@pass_context_and_setup_logging
def timeline(
    _ctx,
    experiment_dir,
    test_id,
    service_id,
    after_str,
    before_str,
    limit,
    output_json,
    output_human,
):
    r"""Display a chronological timeline of log entries.

    Reads structured.jsonl files from the experiment directory, sorts
    entries by timestamp, and groups them by service for swimlane display.

    \b
    Examples:
      panther report timeline outputs/2024-01-01/exp1
      panther report timeline outputs/2024-01-01/exp1 --human --service picoquic
      panther report timeline outputs/2024-01-01/exp1 --after 10:00:00 --limit 20
    """
    from panther.core.reporting.timeline_renderer import TimelineRenderer

    after = _parse_time(after_str) if after_str else None
    before = _parse_time(before_str) if before_str else None

    renderer = TimelineRenderer(Path(experiment_dir))

    if output_human:
        text = renderer.render_human(
            test=test_id,
            service=service_id,
            after=after,
            before=before,
            limit=limit,
        )
        click.echo(text)
    else:
        entries = renderer.render_json(
            test=test_id,
            service=service_id,
            after=after,
            before=before,
            limit=limit,
        )
        click.echo(json.dumps(entries, indent=2, default=str))


# -- artifacts helpers --


def _format_artifacts_human(artifacts: List[dict]) -> str:
    """Format artifact list as a human-readable table.

    Args:
        artifacts: List of artifact metadata dicts.

    Returns:
        Formatted table string.
    """
    if not artifacts:
        return "(no matching artifacts)"

    # Compute column widths
    max_path = max(len(a.get("path", "")) for a in artifacts)
    max_path = min(max_path, 60)  # Cap path width
    max_type = max(len(a.get("type", "")) for a in artifacts)

    lines = []
    header = (
        f"  {'Path':<{max_path}}  {'Type':<{max_type}}  {'Format':<8}  {'Size':>10}"
    )
    lines.append(header)
    lines.append(f"  {'-' * max_path}  {'-' * max_type}  {'-' * 8}  {'-' * 10}")

    for a in artifacts:
        path = a.get("path", "")
        if len(path) > max_path:
            path = "..." + path[-(max_path - 3) :]
        size = a.get("size_bytes", 0)
        if size >= 1024 * 1024:
            size_str = f"{size / (1024 * 1024):.1f} MB"
        elif size >= 1024:
            size_str = f"{size / 1024:.1f} KB"
        else:
            size_str = f"{size} B"
        lines.append(
            f"  {path:<{max_path}}  "
            f"{a.get('type', ''):<{max_type}}  "
            f"{a.get('format', ''):<8}  "
            f"{size_str:>10}"
        )

    return "\n".join(lines)


@report.command("artifacts")
@click.argument("experiment_dir", type=click.Path(exists=True))
@click.option("--test", "test_id", default=None, help="Filter by test_id")
@click.option("--service", "service_id", default=None, help="Filter by service_id")
@click.option(
    "--type",
    "artifact_type",
    default=None,
    help="Filter by artifact type (pcap, qlog, log, etc.)",
)
@click.option("--phase", default=None, help="Filter by execution phase")
@click.option(
    "--json",
    "output_json",
    is_flag=True,
    default=False,
    help="Output as JSON (default)",
)
@click.option(
    "--human",
    "output_human",
    is_flag=True,
    default=False,
    help="Output as human-readable table",
)
@handle_errors
@pass_context_and_setup_logging
def artifacts(
    _ctx,
    experiment_dir,
    test_id,
    service_id,
    artifact_type,
    phase,
    output_json,
    output_human,
):
    r"""Browse artifacts from an experiment output directory.

    Lists output files (logs, pcaps, qlogs, reports, etc.) from the
    experiment directory. Reads output_index.json when available, falls
    back to directory walking otherwise.

    \b
    Examples:
      panther report artifacts outputs/2024-01-01/exp1
      panther report artifacts outputs/2024-01-01/exp1 --human
      panther report artifacts outputs/2024-01-01/exp1 --type artifact --service picoquic
    """
    from panther.core.reporting.artifact_browser import ArtifactBrowser

    browser = ArtifactBrowser(Path(experiment_dir))
    results = browser.list_artifacts(
        test_id=test_id,
        service_id=service_id,
        artifact_type=artifact_type,
        phase=phase,
    )

    if output_human:
        click.echo(_format_artifacts_human(results))
        click.echo()
        _success(f"Found {len(results)} artifact(s)")
    else:
        click.echo(json.dumps(results, indent=2, default=str))


@report.command("diagnose")
@click.argument("experiment_dir", type=click.Path(exists=True))
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["human", "json"]),
    default="human",
    help="Output format (default: human)",
)
@handle_errors
@pass_context_and_setup_logging
def diagnose(_ctx, experiment_dir, fmt):
    r"""Root cause analysis for a failed experiment.

    Scans structured.jsonl for errors, matches against known failure
    patterns, and reports ranked root causes with log excerpts and
    actionable suggestions.

    \b
    Examples:
      panther report diagnose outputs/2024-01-01/exp1
      panther report diagnose outputs/2024-01-01/exp1 --format json
    """
    from panther.core.reporting.root_cause_analyzer import RootCauseAnalyzer

    exp_path = Path(experiment_dir)
    analyzer = RootCauseAnalyzer(exp_path)
    causes = analyzer.analyze()

    if not causes:
        _info("No errors found -- nothing to diagnose.")
        return

    if fmt == "json":
        output = json.dumps([c.to_dict() for c in causes], indent=2, ensure_ascii=False)
        click.echo(output)
        return

    # Human-readable output
    click.echo(colored("Root Cause Analysis", "blue", attrs=["bold"]))
    click.echo(colored("=" * 60, "blue"))
    click.echo()

    for cause in causes:
        # Rank header
        conf_pct = f"{cause.confidence:.0%}"
        click.echo(
            colored(
                f"  #{cause.rank}  {cause.pattern_name}  (confidence: {conf_pct})",
                "yellow",
                attrs=["bold"],
            )
        )
        click.echo(f"    Category:   {cause.category}")

        msg = cause.event.get("message", "")
        if msg:
            click.echo(f"    Trigger:    {msg}")

        svc = cause.event.get("service_id", "")
        if svc:
            click.echo(f"    Service:    {svc}")

        if cause.suggestion:
            click.echo(colored(f"    Suggestion: {cause.suggestion}", "green"))

        if cause.log_excerpt:
            click.echo(colored("    Log excerpt:", "cyan"))
            for line in cause.log_excerpt:
                click.echo(f"      {line}")

        click.echo()

    _success(f"Found {len(causes)} root cause(s)")


if __name__ == "__main__":
    report()
