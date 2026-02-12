"""
Metrics Command - Click Implementation

Manage experiment and build metrics with enhanced user experience.
Reads real metrics data from experiment output directories.
"""

import csv
import json
import logging
import shutil
from datetime import datetime
from pathlib import Path

import click
from termcolor import colored

from panther.cli_click.core.base import (
    error_message,
    handle_errors,
    info_message,
    pass_context_and_setup_logging,
    success_message,
    warning_message,
)
from panther.core.metrics import MetricsDataLoader


def _shared_options(func):
    """Add shared --experiment-dir and --output-dir options."""
    func = click.option(
        "--output-dir",
        type=click.Path(),
        default="outputs",
        help="Root output directory (default: outputs)",
    )(func)
    func = click.option(
        "--experiment-dir",
        type=click.Path(exists=True),
        default=None,
        help="Specific experiment directory to read metrics from",
    )(func)
    return func


def _load_or_fail(experiment_dir, output_dir):
    """Load metrics data, returning (data, exp_path) or printing error and returning None."""
    loader = MetricsDataLoader(output_dir=Path(output_dir))
    exp_path = Path(experiment_dir) if experiment_dir else None
    data, exp_path = loader.load_metrics(experiment_dir=exp_path)

    if data is None:
        if exp_path is None:
            warning_message(
                f"No experiment directories with metrics found in {output_dir}/"
            )
            info_message("Run experiments with --enable-metrics to collect data.")
        else:
            warning_message(f"No metrics data found in {exp_path}/metrics/")
            info_message("Run experiments with --enable-metrics to collect data.")
        return None, None
    return data, exp_path


@click.group()
def metrics():
    """
    Manage and analyze PANTHER metrics data.

    Reads real metrics collected during experiment execution.

    \b
    Examples:
      panther metrics list                    # List available metrics
      panther metrics show --metric cpu       # Show specific metric
      panther metrics export --format csv     # Export to CSV
      panther metrics summary                 # Generate summary
    """
    pass


@metrics.command("list")
@click.option(
    "--filter", "filter_pattern", type=str, help="Filter metrics by name pattern (regex supported)"
)
@_shared_options
@handle_errors
@pass_context_and_setup_logging
def list_metrics(ctx, filter_pattern, experiment_dir, output_dir):
    """
    List all available metrics collected during experiments.

    Shows metrics organized by category with optional filtering.

    \b
    Examples:
      panther metrics list                     # List all metrics
      panther metrics list --filter cpu       # Filter by 'cpu'
      panther metrics list --filter "mem.*"   # Regex filter for memory metrics
    """
    data, exp_path = _load_or_fail(experiment_dir, output_dir)
    if data is None:
        return

    loader = MetricsDataLoader(output_dir=Path(output_dir))
    available = loader.get_available_metrics(data)

    if filter_pattern:
        import re

        available = [m for m in available if re.search(filter_pattern, m["name"])]

    if not available:
        if filter_pattern:
            warning_message(f"No metrics found matching filter: {filter_pattern}")
        else:
            warning_message("No metrics data in this experiment.")
        return

    click.echo(
        colored(f"Metrics from: {exp_path.name}", "blue", attrs=["bold"])
    )
    click.echo()

    # Group by category
    categories = {}
    for metric in available:
        cat = metric["category"]
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(metric)

    for category, cat_metrics in categories.items():
        click.echo(colored(f"  {category.title()} Metrics:", "cyan"))
        for metric in cat_metrics:
            samples_info = f" ({metric['count']} samples)" if metric["count"] > 0 else ""
            click.echo(f"    {metric['name']}{samples_info}")
        click.echo()

    success_message(f"Found {len(available)} metric(s) across {len(categories)} category(ies)")


@metrics.command()
@click.option("--metric", type=str, help="Specific metric name to show")
@click.option(
    "--limit",
    type=int,
    default=10,
    help="Limit number of values shown per metric (default: 10)",
)
@_shared_options
@handle_errors
@pass_context_and_setup_logging
def show(ctx, metric, limit, experiment_dir, output_dir):
    """
    Display detailed metrics data with values and timestamps.

    \b
    Examples:
      panther metrics show                        # Show all metrics
      panther metrics show --metric cpu_usage    # Show specific metric
      panther metrics show --limit 5             # Limit to 5 values per metric
    """
    data, exp_path = _load_or_fail(experiment_dir, output_dir)
    if data is None:
        return

    loader = MetricsDataLoader(output_dir=Path(output_dir))

    if metric:
        metrics_to_show = [metric]
    else:
        available = loader.get_available_metrics(data)
        metrics_to_show = [m["name"] for m in available]

    if not metrics_to_show:
        warning_message("No metrics available to show.")
        return

    click.echo(
        colored(f"Metrics from: {exp_path.name}", "blue", attrs=["bold"])
    )
    click.echo()

    for metric_name in metrics_to_show:
        values = loader.get_metric_values(data, metric_name, limit=limit)
        if not values:
            click.echo(colored(f"  {metric_name}:", "cyan", attrs=["bold"]))
            click.echo("    No data points found")
            click.echo()
            continue

        click.echo(colored(f"  {metric_name}:", "cyan", attrs=["bold"]))
        for entry in values:
            ts = entry.get("timestamp")
            val = entry.get("value")
            entry_type = entry.get("type", "")
            ts_str = ""
            if ts and isinstance(ts, (int, float)):
                ts_str = f"{datetime.fromtimestamp(ts).strftime('%H:%M:%S')} "

            if isinstance(val, float):
                click.echo(f"    {ts_str}{val:.4f}  [{entry_type}]")
            else:
                click.echo(f"    {ts_str}{val}  [{entry_type}]")
        click.echo()

    success_message("Metrics data displayed")


@metrics.command()
@click.option(
    "--output",
    type=click.Path(),
    help="Output file path (default: metrics_export_<timestamp>.<format>)",
)
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["json", "csv", "txt"]),
    default="json",
    help="Export format (default: json)",
)
@_shared_options
@handle_errors
@pass_context_and_setup_logging
def export(ctx, output, fmt, experiment_dir, output_dir):
    """
    Export collected metrics data to various file formats.

    \b
    Supported Formats:
    * json: Structured JSON format (default)
    * csv: Comma-separated values for spreadsheets
    * txt: Human-readable text format

    \b
    Examples:
      panther metrics export                          # Export to JSON with auto-name
      panther metrics export --format csv            # Export to CSV
      panther metrics export --output metrics.json   # Custom output file
    """
    data, exp_path = _load_or_fail(experiment_dir, output_dir)
    if data is None:
        return

    if not output:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output = f"metrics_export_{timestamp}.{fmt}"

    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    info_message(f"Exporting metrics to {fmt.upper()} format...")

    if fmt == "json":
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    elif fmt == "csv":
        # Flatten timing metrics + raw counters/gauges into rows
        rows = []
        for name, value in data.get("timing_metrics", {}).items():
            rows.append({"metric": name, "value": value, "type": "timing"})
        raw = data.get("raw_metrics", {})
        if isinstance(raw, dict):
            for section in ("counters", "gauges"):
                for name, value in raw.get(section, {}).items():
                    rows.append({"metric": name, "value": value, "type": section})
        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["metric", "value", "type"])
            writer.writeheader()
            writer.writerows(rows)
    else:  # txt
        loader = MetricsDataLoader(output_dir=Path(output_dir))
        summary = loader.get_summary(data)
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("PANTHER Metrics Export\n")
            f.write("=" * 40 + "\n")
            f.write(f"Source: {exp_path.name}\n\n")
            for key, value in summary.items():
                f.write(f"{key}: {value}\n")

    success_message(f"Metrics exported to: {output_path.absolute()}")
    size_kb = output_path.stat().st_size / 1024
    info_message(f"File size: {size_kb:.1f} KB")


@metrics.command()
@click.option("--force", is_flag=True, help="Clear without confirmation prompt")
@_shared_options
@handle_errors
@pass_context_and_setup_logging
def clear(ctx, force, experiment_dir, output_dir):
    """
    Clear stored metrics data from experiment directories.

    \b
    Examples:
      panther metrics clear           # Interactive clear with confirmation
      panther metrics clear --force   # Force clear without prompts
    """
    loader = MetricsDataLoader(output_dir=Path(output_dir))

    if experiment_dir:
        targets = [Path(experiment_dir) / "metrics"]
    else:
        experiments = loader.find_experiments_with_metrics()
        targets = [exp / "metrics" for exp in experiments]

    if not targets:
        warning_message("No metrics data found to clear.")
        return

    click.echo(f"Found metrics in {len(targets)} experiment(s):")
    for t in targets:
        click.echo(f"  {t}")

    if not force:
        if not click.confirm(
            colored(
                f"Delete metrics from {len(targets)} experiment(s)?", "yellow"
            )
        ):
            info_message("Clear operation cancelled")
            return

    deleted_count = 0
    for metrics_dir in targets:
        if metrics_dir.exists() and metrics_dir.is_dir():
            shutil.rmtree(metrics_dir)
            deleted_count += 1

    success_message(f"Cleared metrics from {deleted_count} experiment(s)")


@metrics.command()
@_shared_options
@handle_errors
@pass_context_and_setup_logging
def summary(ctx, experiment_dir, output_dir):
    """
    Generate and display comprehensive metrics summary.

    \b
    Examples:
      panther metrics summary    # Show complete metrics summary
    """
    data, exp_path = _load_or_fail(experiment_dir, output_dir)
    if data is None:
        return

    loader = MetricsDataLoader(output_dir=Path(output_dir))
    summary_data = loader.get_summary(data)

    click.echo(colored("Metrics Summary Report", "blue", attrs=["bold"]))
    click.echo(colored("=" * 60, "blue"))
    click.echo(colored(f"Experiment: {exp_path.name}", "blue"))
    click.echo()

    # Export info
    if "export_timestamp" in summary_data:
        click.echo(colored("  Export Info:", "cyan", attrs=["bold"]))
        click.echo(f"    Exported at: {summary_data['export_timestamp']}")
        click.echo()

    # Experiment overview
    has_overview = any(
        k in summary_data
        for k in ("total_experiments", "total_test_cases", "error_count")
    )
    if has_overview:
        click.echo(colored("  Overview:", "cyan", attrs=["bold"]))
        if "total_experiments" in summary_data:
            click.echo(f"    Total experiments: {summary_data['total_experiments']}")
        if "successful_experiments" in summary_data:
            click.echo(f"    Successful: {summary_data['successful_experiments']}")
        if "failed_experiments" in summary_data:
            click.echo(f"    Failed: {summary_data['failed_experiments']}")
        if "total_test_cases" in summary_data:
            click.echo(f"    Test cases: {summary_data['total_test_cases']}")
        if "total_execution_time" in summary_data:
            click.echo(
                f"    Total execution time: {summary_data['total_execution_time']}"
            )
        if "error_count" in summary_data:
            click.echo(f"    Error count: {summary_data['error_count']}")
        click.echo()

    # Timing stats
    if "timing_metric_count" in summary_data:
        click.echo(colored("  Timing:", "cyan", attrs=["bold"]))
        click.echo(f"    Metric count: {summary_data['timing_metric_count']}")
        click.echo(f"    Total: {summary_data.get('total_timing', 'N/A')}")
        click.echo()

    # Resource stats
    has_resource = any(k in summary_data for k in ("avg_cpu", "avg_memory"))
    if has_resource:
        click.echo(colored("  Resources:", "cyan", attrs=["bold"]))
        if "avg_cpu" in summary_data:
            click.echo(f"    Avg CPU: {summary_data['avg_cpu']}")
            click.echo(f"    Peak CPU: {summary_data.get('peak_cpu', 'N/A')}")
        if "avg_memory" in summary_data:
            click.echo(f"    Avg Memory: {summary_data['avg_memory']}")
            click.echo(
                f"    Peak Memory: {summary_data.get('peak_memory', 'N/A')}"
            )
        if "resource_samples" in summary_data:
            click.echo(f"    Samples: {summary_data['resource_samples']}")
        click.echo()

    # Error stats
    if summary_data.get("total_errors", 0) > 0:
        click.echo(colored("  Errors:", "cyan", attrs=["bold"]))
        click.echo(f"    Total: {summary_data['total_errors']}")
        categories = summary_data.get("error_categories", {})
        if categories:
            for cat, count in categories.items():
                click.echo(f"    {cat}: {count}")
        click.echo()

    success_message("Summary generated")


@metrics.command("quick")
@_shared_options
@handle_errors
@pass_context_and_setup_logging
def quick_overview(ctx, experiment_dir, output_dir):
    """
    Quick metrics overview (list + summary).

    Convenience command that shows both available metrics
    and a summary in one operation.
    """
    ctx.invoke(list_metrics, experiment_dir=experiment_dir, output_dir=output_dir)
    click.echo()
    ctx.invoke(summary, experiment_dir=experiment_dir, output_dir=output_dir)


@metrics.command("backup")
@click.option(
    "--output",
    type=click.Path(),
    help="Backup file path (default: metrics_backup_<timestamp>.json)",
)
@_shared_options
@handle_errors
@pass_context_and_setup_logging
def backup(ctx, output, experiment_dir, output_dir):
    """
    Create a backup of all metrics data.

    Exports all metrics to a timestamped backup file for safekeeping.
    """
    if not output:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output = f"metrics_backup_{timestamp}.json"

    info_message(f"Creating metrics backup: {output}")
    ctx.invoke(
        export,
        output=output,
        fmt="json",
        experiment_dir=experiment_dir,
        output_dir=output_dir,
    )
    success_message(f"Backup created: {output}")


if __name__ == "__main__":
    metrics()
