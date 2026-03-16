"""Logs Command.

Post-hoc query and filtering of structured.jsonl files produced during
experiment runs. Supports level, service, test, phase, time-range,
correlation-id, regex, and source filters.
"""

import json
import re
from datetime import datetime
from pathlib import Path

import click
from termcolor import colored

from panther.cli.core.base import (
    featured_example,
    handle_errors,
    pass_context_and_setup_logging,
)


def _build_filter(
    level, service, test, phase, after, before, correlation_id, pattern, source
):
    """Build a LogFilter from CLI option values.

    Args:
        level: Comma-separated level names (e.g. "ERROR,WARNING").
        service: Service ID to filter by.
        test: Test ID to filter by.
        phase: Phase name to filter by.
        after: ISO-8601 timestamp for time-range start.
        before: ISO-8601 timestamp for time-range end.
        correlation_id: Correlation ID to follow.
        pattern: Regex pattern for message filtering.
        source: Record source ("logging" or "event").

    Returns:
        A LogFilter instance.
    """
    from panther.core.reporting.log_query_engine import LogFilter

    levels = {l.strip().upper() for l in level.split(",")} if level else None
    services = {service} if service else None
    tests = {test} if test else None
    phases = {phase} if phase else None
    sources = {source} if source else None

    try:
        after_dt = datetime.fromisoformat(after) if after else None
    except ValueError as exc:
        raise click.BadParameter(f"Invalid --after timestamp: {exc}") from exc
    try:
        before_dt = datetime.fromisoformat(before) if before else None
    except ValueError as exc:
        raise click.BadParameter(f"Invalid --before timestamp: {exc}") from exc
    try:
        msg_pattern = re.compile(pattern) if pattern else None
    except re.error as exc:
        raise click.BadParameter(f"Invalid --pattern regex: {exc}") from exc

    return LogFilter(
        levels=levels,
        services=services,
        tests=tests,
        phases=phases,
        after=after_dt,
        before=before_dt,
        correlation_id=correlation_id,
        message_pattern=msg_pattern,
        sources=sources,
    )


def _format_human(record):
    """Format a log record as a human-readable table row.

    Args:
        record: Parsed JSONL record dictionary.

    Returns:
        Formatted string for terminal output.
    """
    ts = record.get("ts", "")[:23]  # trim microseconds for display
    level = record.get("level", "?")
    service = record.get("service_id", "-")
    message = record.get("message", "")

    # Color by level
    level_colors = {
        "CRITICAL": "red",
        "ERROR": "red",
        "WARNING": "yellow",
        "INFO": "blue",
        "DEBUG": "white",
        "EVENT": "cyan",
    }
    color = level_colors.get(level, "white")
    level_str = colored(f"{level:<8}", color)

    return f"{ts:<23}  {level_str}  {service:<20}  {message}"


# ========== Commands ==========


@featured_example("panther logs query outputs/2024-01-01/exp1 --level ERROR")
@click.group()
def logs():
    r"""Query and filter structured experiment logs.

    Read structured.jsonl files from experiment output directories and
    filter by level, service, test, phase, time range, and more.

    \b
    Examples:
      panther logs query outputs/2024-01-01/exp1 --level ERROR
      panther logs errors outputs/2024-01-01/exp1
      panther logs query outputs/2024-01-01/exp1 --service picoquic --human
    """


@logs.command("query")
@click.argument("directory", type=click.Path(exists=True))
@click.option(
    "--level", default=None, help="Comma-separated log levels (e.g. ERROR,WARNING)"
)
@click.option("--service", default=None, help="Filter by service_id")
@click.option("--test", default=None, help="Filter by test_id")
@click.option("--phase", default=None, help="Filter by phase")
@click.option(
    "--after", default=None, help="Include records at or after this ISO timestamp"
)
@click.option(
    "--before", default=None, help="Include records before this ISO timestamp"
)
@click.option("--correlation-id", default=None, help="Follow a correlation chain")
@click.option(
    "--pattern", default=None, help="Regex pattern to match against message field"
)
@click.option("--source", default=None, help='Record source: "logging" or "event"')
@click.option("--limit", default=0, type=int, help="Max results (0 = unlimited)")
@click.option(
    "--json/--human",
    "output_json",
    default=True,
    help="Output format: --json (JSONL, default) or --human (table)",
)
@handle_errors
@pass_context_and_setup_logging
def query(
    _ctx,
    directory,
    level,
    service,
    test,
    phase,
    after,
    before,
    correlation_id,
    pattern,
    source,
    limit,
    output_json,
):
    r"""Query structured log records with filtering.

    Reads structured.jsonl files from DIRECTORY and prints matching
    records. By default output is JSONL (one JSON object per line);
    use --human for a formatted table.

    \b
    Examples:
      panther logs query outputs/2024-01-01/exp1 --level ERROR,WARNING
      panther logs query outputs/2024-01-01/exp1 --service picoquic --human
      panther logs query outputs/2024-01-01/exp1 --pattern "timeout" --limit 20
      panther logs query outputs/2024-01-01/exp1 --after 2024-01-01T12:00:00
    """
    from panther.core.reporting.log_query_engine import LogQueryEngine

    log_filter = _build_filter(
        level, service, test, phase, after, before, correlation_id, pattern, source
    )
    engine = LogQueryEngine(Path(directory))

    if not output_json:
        # Print header for human-readable table
        header = f"{'Timestamp':<23}  {'Level':<8}  {'Service':<20}  Message"
        click.echo(colored(header, "cyan", attrs=["bold"]))
        click.echo("-" * 90)

    count = 0
    for record in engine.query(log_filter, limit=limit):
        if output_json:
            click.echo(json.dumps(record, default=str))
        else:
            click.echo(_format_human(record))
        count += 1

    if not output_json:
        click.echo("-" * 90)
        click.echo(colored(f"  {count} record(s) matched", "green"))


@logs.command("errors")
@click.argument("directory", type=click.Path(exists=True))
@click.option("--service", default=None, help="Filter by service_id")
@click.option("--test", default=None, help="Filter by test_id")
@click.option("--limit", default=0, type=int, help="Max results (0 = unlimited)")
@click.option(
    "--json/--human",
    "output_json",
    default=True,
    help="Output format: --json (JSONL, default) or --human (table)",
)
@handle_errors
@pass_context_and_setup_logging
def errors(_ctx, directory, service, test, limit, output_json):
    r"""Show ERROR and CRITICAL log records.

    Shorthand for ``panther logs query <dir> --level ERROR,CRITICAL``.

    \b
    Examples:
      panther logs errors outputs/2024-01-01/exp1
      panther logs errors outputs/2024-01-01/exp1 --human
      panther logs errors outputs/2024-01-01/exp1 --service picoquic
    """
    from panther.core.reporting.log_query_engine import LogQueryEngine

    log_filter = _build_filter(
        level="ERROR,CRITICAL",
        service=service,
        test=test,
        phase=None,
        after=None,
        before=None,
        correlation_id=None,
        pattern=None,
        source=None,
    )
    engine = LogQueryEngine(Path(directory))

    if not output_json:
        header = f"{'Timestamp':<23}  {'Level':<8}  {'Service':<20}  Message"
        click.echo(colored(header, "cyan", attrs=["bold"]))
        click.echo("-" * 90)

    count = 0
    for record in engine.query(log_filter, limit=limit):
        if output_json:
            click.echo(json.dumps(record, default=str))
        else:
            click.echo(_format_human(record))
        count += 1

    if not output_json:
        click.echo("-" * 90)
        click.echo(colored(f"  {count} error(s) found", "green"))


def _format_metric_human(record):
    """Format a metric record as a human-readable line.

    Args:
        record: Parsed JSONL record dictionary with source="metrics".

    Returns:
        Formatted string for terminal output.
    """
    ts = record.get("ts", "")[:23]
    name = record.get("metric_name", "?")
    value = record.get("metric_value", "?")
    mtype = record.get("metric_type", "")
    phase = record.get("phase", "")
    phase_str = f" ({phase})" if phase else ""
    return f"{ts:<23}  {colored('METRIC', 'magenta'):<17}  {name} = {value}{phase_str}  [{mtype}]"


@logs.command("metrics")
@click.argument("directory", type=click.Path(exists=True))
@click.option("--name", default=None, help="Filter by metric_name")
@click.option(
    "--type",
    "metric_type",
    default=None,
    help="Filter by metric_type (timing/counter/gauge/histogram/status)",
)
@click.option("--limit", default=0, type=int, help="Max results (0 = unlimited)")
@click.option(
    "--json/--human",
    "output_json",
    default=True,
    help="Output format: --json (JSONL, default) or --human (table)",
)
@handle_errors
@pass_context_and_setup_logging
def metrics(_ctx, directory, name, metric_type, limit, output_json):
    r"""Show metric records from structured logs.

    Shorthand for ``panther logs query <dir> --source metrics``.

    \b
    Examples:
      panther logs metrics outputs/2024-01-01/exp1
      panther logs metrics outputs/2024-01-01/exp1 --type timing --human
      panther logs metrics outputs/2024-01-01/exp1 --name setup_services_duration
    """
    from panther.core.reporting.log_query_engine import LogFilter, LogQueryEngine

    metric_names = {name} if name else None
    metric_types = {metric_type} if metric_type else None

    log_filter = LogFilter(
        sources={"metrics"},
        metric_names=metric_names,
        metric_types=metric_types,
    )
    engine = LogQueryEngine(Path(directory))

    if not output_json:
        header = f"{'Timestamp':<23}  {'Level':<8}  {'Metric':<30}  Value"
        click.echo(colored(header, "cyan", attrs=["bold"]))
        click.echo("-" * 90)

    count = 0
    for record in engine.query(log_filter, limit=limit):
        if output_json:
            click.echo(json.dumps(record, default=str))
        else:
            click.echo(_format_metric_human(record))
        count += 1

    if not output_json:
        click.echo("-" * 90)
        click.echo(colored(f"  {count} metric(s) found", "green"))
