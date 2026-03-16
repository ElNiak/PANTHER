"""Build Metrics Command.

View and export build/test metrics collected by the PANTHER builder.
"""

import json
import sys
from pathlib import Path

import click

from panther.builder_metrics.cli import format_duration, format_size, format_timestamp
from panther.builder_metrics.storage import JSONLinesStorage
from panther.cli.core.base import (
    featured_example,
    handle_errors,
    pass_context_and_setup_logging,
)


def _get_storage() -> JSONLinesStorage:
    project_root = Path.cwd()
    return JSONLinesStorage(project_root / ".panther-metrics")


@featured_example("panther build-metrics list")
@click.group("build-metrics")
def build_metrics():
    r"""View and export build/test metrics.

    Reads metrics collected during package builds and test runs
    from .panther-metrics/ JSONL storage.

    \b
    Examples:
      panther build-metrics list              # List recent records
      panther build-metrics show <run-id>     # Show record details
      panther build-metrics export            # Export to JSON
    """


@build_metrics.command("list")
@click.option(
    "--limit", "-n", type=int, default=20, help="Max records to show (default: 20)"
)
@handle_errors
@pass_context_and_setup_logging
def list_records(_ctx, limit):
    """List recent build/test metrics records."""
    storage = _get_storage()
    records = storage.read_records(limit=limit)

    if not records:
        click.echo("No metrics records found.")
        return

    click.echo(f"{'Run ID':<36} {'Type':<8} {'Timestamp':<19} {'Key Metrics'}")
    click.echo("-" * 80)

    for record in records:
        run_id = record.get("run_id", "unknown")[:35]
        record_type = record.get("type", "unknown")
        timestamp = format_timestamp(record.get("timestamp", ""))
        metrics = record.get("metrics", {})
        key_metrics = []

        if record_type == "builder":
            if "container.build_seconds" in metrics:
                key_metrics.append(
                    f"build: {format_duration(metrics['container.build_seconds'])}"
                )
            if "container.image_mb" in metrics:
                key_metrics.append(
                    f"image: {format_size(metrics['container.image_mb'])}"
                )
        elif record_type == "tests":
            if "pytest.total_seconds" in metrics:
                key_metrics.append(
                    f"duration: {format_duration(metrics['pytest.total_seconds'])}"
                )
            if "pytest.passed" in metrics and "pytest.failed" in metrics:
                key_metrics.append(
                    f"passed: {int(metrics['pytest.passed'])}, failed: {int(metrics['pytest.failed'])}"
                )

        click.echo(
            f"{run_id:<36} {record_type:<8} {timestamp:<19} {', '.join(key_metrics) or 'no metrics'}"
        )


@build_metrics.command("show")
@click.argument("run_id")
@handle_errors
@pass_context_and_setup_logging
def show_record(_ctx, run_id):
    """Show detailed information about a specific metrics record."""
    storage = _get_storage()
    record = storage.get_record_by_id(run_id)

    if not record:
        click.echo(f"No record found with run ID: {run_id}")
        return

    click.echo(f"Run ID: {record.get('run_id', 'unknown')}")
    click.echo(f"Type: {record.get('type', 'unknown')}")
    click.echo(f"Timestamp: {format_timestamp(record.get('timestamp', ''))}")
    click.echo(f"Git Commit: {record.get('git_commit', 'unknown')}")
    click.echo()

    metrics = record.get("metrics", {})
    if metrics:
        click.echo("Metrics:")
        for name, value in sorted(metrics.items()):
            if name.endswith("_seconds"):
                click.echo(f"  {name}: {format_duration(value)}")
            elif name.endswith("_mb"):
                click.echo(f"  {name}: {format_size(value)}")
            elif isinstance(value, float):
                click.echo(f"  {name}: {value:.2f}")
            else:
                click.echo(f"  {name}: {value}")


@build_metrics.command("export")
@click.option("--output", "-o", type=click.Path(), help="Output file (default: stdout)")
@click.option("--limit", "-n", type=int, help="Max records to export")
@handle_errors
@pass_context_and_setup_logging
def export_records(_ctx, output, limit):
    """Export metrics records to JSON."""
    storage = _get_storage()
    records = storage.read_records(limit=limit)

    if output:
        with open(output, "w") as f:
            json.dump(records, f, indent=2)
        click.echo(f"Exported {len(records)} records to {output}")
    else:
        json.dump(records, sys.stdout, indent=2)
