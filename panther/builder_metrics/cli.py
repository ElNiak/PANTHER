"""Command-line interface for PANTHER metrics."""

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

from .storage import JSONLinesStorage


def format_timestamp(timestamp: str) -> str:
    """Format ISO timestamp for display."""
    try:
        dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except ValueError:
        return timestamp


def format_duration(seconds: float) -> str:
    """Format duration for display."""
    if seconds < 60:
        return f"{seconds:.1f}s"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.1f}m"
    else:
        hours = seconds / 3600
        return f"{hours:.1f}h"


def format_size(mb: float) -> str:
    """Format size in MB for display."""
    if mb < 1024:
        return f"{mb:.1f} MB"
    else:
        gb = mb / 1024
        return f"{gb:.1f} GB"


def get_storage() -> JSONLinesStorage:
    """Get the metrics storage instance."""
    project_root = Path.cwd()
    storage_path = project_root / ".panther-metrics"
    return JSONLinesStorage(storage_path)


def cmd_list(args: argparse.Namespace) -> int:
    """List recent metrics records.

    Lists metrics records from storage in a tabular format, showing run ID, record type,
    timestamp, and key metrics for each record. Supports both builder and test metrics.

    Args:
        args: Namespace containing command arguments.
            - limit: Maximum number of records to display

    Returns:
        int: Exit code (0 for success, 1 for error)

    Output Format:
        Displays a table with columns:
        - Run ID: Unique identifier for the metrics run (truncated to 35 chars)
        - Type: Record type ('builder' or 'tests')
        - Timestamp: Formatted timestamp of the record
        - Key Metrics: Summary of important metrics based on record type
            - For builder: build time, image size, dist size
            - For tests: duration, test count, pass/fail counts, coverage percentage

    Error Handling:
        - Returns 1 and prints error message to stderr if storage read fails
        - Returns 0 with informative message if no records found
    """
    """List recent metrics records."""
    storage = get_storage()

    try:
        records = storage.read_records(limit=args.limit)
    except Exception as e:
        print(f"Error reading metrics: {e}", file=sys.stderr)
        return 1

    if not records:
        print("No metrics records found.")
        return 0

    # Print header
    print(f"{'Run ID':<36} {'Type':<8} {'Timestamp':<19} {'Key Metrics'}")
    print("-" * 80)

    # Print records
    for record in records:
        run_id = record.get("run_id", "unknown")[:35]
        record_type = record.get("type", "unknown")
        timestamp = format_timestamp(record.get("timestamp", ""))

        # Extract key metrics based on type
        metrics = record.get("metrics", {})
        key_metrics = []

        if record_type == "builder":
            if "container.build_seconds" in metrics:
                duration = format_duration(metrics["container.build_seconds"])
                key_metrics.append(f"build: {duration}")
            if "container.image_mb" in metrics:
                size = format_size(metrics["container.image_mb"])
                key_metrics.append(f"image: {size}")
            if "artifact.dist_mb" in metrics:
                size = format_size(metrics["artifact.dist_mb"])
                key_metrics.append(f"dist: {size}")

        elif record_type == "tests":
            if "pytest.total_seconds" in metrics:
                duration = format_duration(metrics["pytest.total_seconds"])
                key_metrics.append(f"duration: {duration}")
            if "pytest.item_count" in metrics:
                count = int(metrics["pytest.item_count"])
                key_metrics.append(f"tests: {count}")
            if "pytest.failed" in metrics and "pytest.passed" in metrics:
                failed = int(metrics["pytest.failed"])
                passed = int(metrics["pytest.passed"])
                key_metrics.append(f"passed: {passed}, failed: {failed}")
            if "pytest.coverage_pct" in metrics:
                coverage = metrics["pytest.coverage_pct"]
                key_metrics.append(f"coverage: {coverage:.1f}%")

        key_metrics_str = ", ".join(key_metrics) if key_metrics else "no metrics"
        print(f"{run_id:<36} {record_type:<8} {timestamp:<19} {key_metrics_str}")

    return 0


def cmd_show(args: argparse.Namespace) -> int:
    """Show detailed information about a specific metrics record."""
    storage = get_storage()

    try:
        record = storage.get_record_by_id(args.run_id)
    except Exception as e:
        print(f"Error reading metrics: {e}", file=sys.stderr)
        return 1

    if not record:
        print(f"No record found with run ID: {args.run_id}")
        return 1

    # Print basic information
    print(f"Run ID: {record.get('run_id', 'unknown')}")
    print(f"Type: {record.get('type', 'unknown')}")
    print(f"Timestamp: {format_timestamp(record.get('timestamp', ''))}")
    print(f"Git Commit: {record.get('git_commit', 'unknown')}")

    # Print configuration hash if available
    if "config_hash" in record:
        print(f"Config Hash: {record['config_hash']}")

    print()

    # Print metrics
    metrics = record.get("metrics", {})
    if metrics:
        print("Metrics:")
        for name, value in sorted(metrics.items()):
            if name.endswith("_seconds"):
                formatted_value = format_duration(value)
            elif name.endswith("_mb"):
                formatted_value = format_size(value)
            elif name.endswith("_pct"):
                formatted_value = f"{value:.1f}%"
            elif isinstance(value, float):
                formatted_value = f"{value:.2f}"
            else:
                formatted_value = str(value)

            print(f"  {name}: {formatted_value}")
        print()

    # Print tags if available
    tags = record.get("tags", {})
    if tags:
        print("Tags:")
        for metric_name, metric_tags in sorted(tags.items()):
            print(f"  {metric_name}: {metric_tags}")
        print()

    # Print additional data
    extra_keys = set(record.keys()) - {
        "run_id",
        "type",
        "timestamp",
        "git_commit",
        "metrics",
        "tags",
    }
    if extra_keys:
        print("Additional Data:")
        for key in sorted(extra_keys):
            value = record[key]
            if isinstance(value, (dict, list)):
                print(f"  {key}:")
                print("   ", json.dumps(value, indent=2).replace("\n", "\n    "))
            else:
                print(f"  {key}: {value}")

    return 0


def cmd_export(args: argparse.Namespace) -> int:
    """Export metrics records to JSON."""
    storage = get_storage()

    try:
        records = storage.read_records(date=args.date, limit=args.limit)
    except Exception as e:
        print(f"Error reading metrics: {e}", file=sys.stderr)
        return 1

    if args.output:
        try:
            with open(args.output, "w") as f:
                json.dump(records, f, indent=2)
            print(f"Exported {len(records)} records to {args.output}")
        except Exception as e:
            print(f"Error writing to {args.output}: {e}", file=sys.stderr)
            return 1
    else:
        json.dump(records, sys.stdout, indent=2)

    return 0


def main() -> int:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="panther-metrics", description="PANTHER metrics management CLI"
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # List command
    list_parser = subparsers.add_parser(
        "ls", aliases=["list"], help="List recent metrics records"
    )
    list_parser.add_argument(
        "--limit",
        "-n",
        type=int,
        default=20,
        help="Maximum number of records to show (default: 20)",
    )

    # Show command
    show_parser = subparsers.add_parser(
        "show", help="Show detailed information about a specific record"
    )
    show_parser.add_argument("run_id", help="Run ID to show details for")

    # Export command
    export_parser = subparsers.add_parser(
        "export", help="Export metrics records to JSON"
    )
    export_parser.add_argument("--output", "-o", help="Output file (default: stdout)")
    export_parser.add_argument(
        "--date", "-d", help="Filter by date (YYYY-MM-DD format)"
    )
    export_parser.add_argument(
        "--limit", "-n", type=int, help="Maximum number of records to export"
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    # Route to appropriate command handler
    if args.command in ("ls", "list"):
        return cmd_list(args)
    elif args.command == "show":
        return cmd_show(args)
    elif args.command == "export":
        return cmd_export(args)
    else:
        print(f"Unknown command: {args.command}", file=sys.stderr)
        return 1


if __name__ in {"__main__", "__mp_main__"}:
    sys.exit(main())
