"""
Metrics Command - Manage experiment and build metrics
"""

import logging
from argparse import ArgumentParser, _SubParsersAction
from datetime import datetime
from pathlib import Path
from typing import Any

from panther.cli.base import BaseCommand


class MetricsCommand(BaseCommand):
    """Handle metrics collection and analysis."""

    @classmethod
    def register_parser(cls, subparsers: _SubParsersAction) -> ArgumentParser:
        """Register the metrics subcommand parser."""
        parser = subparsers.add_parser(
            "metrics",
            help="Manage and analyze metrics",
            description="View, export, and analyze PANTHER metrics data",
        )

        subcommands = parser.add_subparsers(
            dest="metrics_action", help="Metrics actions", metavar="ACTION"
        )

        # List metrics
        list_parser = subcommands.add_parser(
            "list",
            help="List available metrics",
            description="Show all available metrics collected during operations",
        )
        list_parser.add_argument(
            "--filter", type=str, help="Filter metrics by name pattern"
        )

        # Show metrics
        show_parser = subcommands.add_parser(
            "show",
            help="Display metrics data",
            description="Show detailed metrics data with values",
        )
        show_parser.add_argument(
            "--metric", type=str, help="Specific metric name to show"
        )
        show_parser.add_argument(
            "--limit",
            type=int,
            default=10,
            help="Limit number of values shown per metric (default: 10)",
        )

        # Export metrics
        export_parser = subcommands.add_parser(
            "export",
            help="Export metrics to file",
            description="Export collected metrics data to various formats",
        )
        export_parser.add_argument(
            "--output",
            type=str,
            help="Output file path (default: metrics_export_<timestamp>.json)",
        )
        export_parser.add_argument(
            "--format",
            choices=["json", "csv", "txt"],
            default="json",
            help="Export format (default: json)",
        )

        # Clear metrics
        clear_parser = subcommands.add_parser(
            "clear",
            help="Clear stored metrics",
            description="Remove all stored metrics data",
        )
        clear_parser.add_argument(
            "--force", action="store_true", help="Clear without confirmation"
        )

        # Summary
        summary_parser = subcommands.add_parser(
            "summary",
            help="Show metrics summary",
            description="Display a summary of collected metrics",
        )

        return parser

    @classmethod
    def handle(cls, args: Any) -> int:
        """Handle the metrics command execution."""
        if not hasattr(args, "metrics_action") or args.metrics_action is None:
            logging.info(
                "❌ No metrics action specified. Use 'panther metrics --help' for options."
            )
            return 1

        # Check if metrics system is available
        try:
            from panther.core.metrics.metrics_collector import MetricsCollector
            from panther.core.metrics.metrics_exporter import MetricsExporter
        except ImportError:
            logging.info("❌ Metrics system is not available.")
            logging.info(
                "   Make sure PANTHER is properly installed with metrics support."
            )
            return 1

        if args.metrics_action == "list":
            return cls._list_metrics(args)
        elif args.metrics_action == "show":
            return cls._show_metrics(args)
        elif args.metrics_action == "export":
            return cls._export_metrics(args)
        elif args.metrics_action == "clear":
            return cls._clear_metrics(args)
        elif args.metrics_action == "summary":
            return cls._summary_metrics(args)
        else:
            logging.info(f"❌ Unknown metrics action: {args.metrics_action}")
            return 1

    @classmethod
    def _get_experiment_context(cls) -> tuple[str, Path]:
        """Get or create experiment context for CLI metrics operations.

        Creates a CLI-specific experiment directory structure that follows
        the same pattern as RunCommand: outputs/<experiment_name>/metrics/

        Returns:
            tuple[str, Path]: (experiment_name, output_dir) for metrics operations
        """
        experiment_name = "cli_metrics_session"
        base_output_dir = Path("outputs")
        experiment_dir = base_output_dir / experiment_name
        metrics_output_dir = experiment_dir / "metrics"

        # Create directories following the experiment pattern
        metrics_output_dir.mkdir(parents=True, exist_ok=True)

        return experiment_name, metrics_output_dir

    @classmethod
    def _list_metrics(cls, args: Any) -> int:
        """List available metrics."""
        logging.info("📊 Listing available metrics...")

        try:
            from panther.core.metrics.metrics_collector import MetricsCollector

            # Get experiment context for proper MetricsCollector initialization
            experiment_name, output_dir = cls._get_experiment_context()
            collector = MetricsCollector(
                experiment_name=experiment_name, output_dir=output_dir
            )

            # Get all metrics using the correct method
            all_metrics = collector.get_metrics()

            if not all_metrics:
                logging.info("ℹ️  No metrics have been collected yet.")
                return 0

            # Extract metric names for display
            metric_names = [metric.name for metric in all_metrics]

            # Apply filter if provided
            if args.filter:
                import re

                pattern = re.compile(args.filter, re.IGNORECASE)
                metric_names = [m for m in metric_names if pattern.search(m)]

            if not metric_names:
                logging.info(f"ℹ️  No metrics match the filter: {args.filter}")
                return 0

            logging.info(f"Found {len(metric_names)} metric(s):")
            logging.info("-" * 60)

            # Group metrics by category
            categories = {}
            for metric in metric_names:
                category = metric.split(".")[0] if "." in metric else "general"
                if category not in categories:
                    categories[category] = []
                categories[category].append(metric)

            for category, cat_metrics in sorted(categories.items()):
                logging.info(f"\n{category.upper()}:")
                for metric in sorted(cat_metrics):
                    logging.info(f"  - {metric}")

            return 0

        except Exception as e:
            logging.info(f"❌ Error listing metrics: {e}")
            return 1

    @classmethod
    def _show_metrics(cls, args: Any) -> int:
        """Display metrics data."""
        logging.info("📈 Showing metrics data...")

        try:
            from panther.core.metrics.metrics_collector import MetricsCollector

            # Get experiment context for proper MetricsCollector initialization
            experiment_name, output_dir = cls._get_experiment_context()
            collector = MetricsCollector(
                experiment_name=experiment_name, output_dir=output_dir
            )

            # Get all metrics using the correct method
            all_metrics = collector.get_metrics()

            if args.metric:
                # Show specific metric by name
                matching_metrics = [m for m in all_metrics if m.name == args.metric]
                if not matching_metrics:
                    logging.info(f"❌ Metric not found: {args.metric}")
                    return 1

                metrics_data = {args.metric: matching_metrics}
            else:
                # Show all metrics grouped by name
                metrics_data = {}
                for metric in all_metrics:
                    if metric.name not in metrics_data:
                        metrics_data[metric.name] = []
                    metrics_data[metric.name].append(metric)

            if not metrics_data:
                logging.info("ℹ️  No metrics data available.")
                return 0

            logging.info(f"Metrics data ({len(metrics_data)} metric type(s)):")
            logging.info("-" * 60)

            for name, metrics_list in sorted(metrics_data.items()):
                logging.info(f"\n📊 {name}:")
                logging.info(f"   Count: {len(metrics_list)}")

                # Show sample values
                logging.info(f"   Values (showing up to {args.limit}):")
                for i, metric in enumerate(metrics_list[: args.limit], 1):
                    timestamp_str = (
                        metric.timestamp if hasattr(metric, "timestamp") else "N/A"
                    )
                    value_str = metric.value if hasattr(metric, "value") else "N/A"
                    logging.info(f"     {i}: {value_str} (timestamp: {timestamp_str})")

                if len(metrics_list) > args.limit:
                    logging.info(
                        f"     ... and {len(metrics_list) - args.limit} more values"
                    )

            return 0

        except Exception as e:
            logging.info(f"❌ Error showing metrics: {e}")
            return 1

    @classmethod
    def _export_metrics(cls, args: Any) -> int:
        """Export metrics to file."""
        logging.info("💾 Exporting metrics data...")

        try:
            from panther.core.metrics.metrics_collector import MetricsCollector
            from panther.core.metrics.metrics_exporter import MetricsExporter

            # Get experiment context for proper MetricsCollector initialization
            experiment_name, output_dir = cls._get_experiment_context()
            collector = MetricsCollector(
                experiment_name=experiment_name, output_dir=output_dir
            )

            # Determine output file
            if args.output:
                output_file = Path(args.output)
            else:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                output_file = Path(f"metrics_export_{timestamp}.{args.format}")

            # Initialize MetricsExporter with the collector instance
            exporter = MetricsExporter(metrics_collector=collector)

            if args.format == "json":
                success = exporter.export_to_json(str(output_file))
            elif args.format == "csv":
                success = exporter.export_to_csv(str(output_file))
            elif args.format == "txt":
                # For txt format, use JSON as fallback since export_to_text doesn't exist
                success = exporter.export_to_json(str(output_file))
            else:
                logging.info(f"❌ Unsupported format: {args.format}")
                return 1

            if success:
                logging.info(f"✅ Metrics exported successfully to: {output_file}")

                # Show file size
                size_kb = output_file.stat().st_size / 1024
                logging.info(f"   File size: {size_kb:.1f} KB")

                return 0
            else:
                logging.info("❌ No metrics data available to export.")
                return 1

        except Exception as e:
            logging.info(f"❌ Error exporting metrics: {e}")
            return 1

    @classmethod
    def _clear_metrics(cls, args: Any) -> int:
        """Clear stored metrics."""
        logging.info("🗑️  Clearing metrics data...")

        if not args.force:
            response = input("This will delete all stored metrics. Continue? (y/N): ")
            if response.lower() not in ["y", "yes"]:
                logging.info("❌ Clear operation cancelled")
                return 0

        try:
            from panther.core.metrics.metrics_collector import MetricsCollector

            # Get experiment context for proper MetricsCollector initialization
            experiment_name, output_dir = cls._get_experiment_context()
            collector = MetricsCollector(
                experiment_name=experiment_name, output_dir=output_dir
            )

            # Clear metrics by resetting the metrics list
            # Note: The MetricsCollector doesn't have a clear_all_metrics method
            # Instead we can work with the available data
            metrics_before = len(collector.get_metrics())
            logging.info(f"📊 Found {metrics_before} metrics in the system")

            # Clear the metrics directory if it exists
            if output_dir.exists():
                import shutil

                shutil.rmtree(output_dir)
                output_dir.mkdir(parents=True, exist_ok=True)
                logging.info("✅ Metrics directory has been cleared")
            else:
                logging.info("ℹ️  No metrics directory found to clear")

            return 0

        except Exception as e:
            logging.info(f"❌ Error clearing metrics: {e}")
            return 1

    @classmethod
    def _summary_metrics(cls, args: Any) -> int:
        """Show metrics summary."""
        logging.info("📊 Metrics Summary")
        logging.info("=" * 60)

        try:
            from panther.core.metrics.metrics_collector import MetricsCollector
            from panther.core.metrics.metrics_reporter import MetricsReporter

            # Get experiment context for proper MetricsCollector initialization
            experiment_name, output_dir = cls._get_experiment_context()
            collector = MetricsCollector(
                experiment_name=experiment_name, output_dir=output_dir
            )
            reporter = MetricsReporter(collector)

            summary = reporter.generate_summary()

            if not summary:
                logging.info("ℹ️  No metrics data available for summary.")
                return 0

            # Display summary sections
            if "overview" in summary:
                logging.info("\n📋 Overview:")
                for key, value in summary["overview"].items():
                    logging.info(f"   {key}: {value}")

            if "categories" in summary:
                logging.info("\n📂 Categories:")
                for category, count in summary["categories"].items():
                    logging.info(f"   {category}: {count} metric(s)")

            if "recent_activity" in summary:
                logging.info("\n🕐 Recent Activity:")
                for activity in summary["recent_activity"][:5]:
                    logging.info(f"   - {activity}")

            if "performance" in summary:
                logging.info("\n⚡ Performance Metrics:")
                perf = summary["performance"]
                for key, value in perf.items():
                    logging.info(f"   {key}: {value}")

            if "resource_usage" in summary:
                logging.info("\n💾 Resource Usage:")
                resources = summary["resource_usage"]
                for key, value in resources.items():
                    logging.info(f"   {key}: {value}")

            return 0

        except Exception as e:
            logging.info(f"❌ Error generating summary: {e}")
            return 1
