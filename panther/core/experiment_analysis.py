"""
Experiment Analysis Mixin for PANTHER framework.

This module contains the ExperimentObserverMixin class which provides observer setup
and management functionality that can be mixed into the ExperimentManager.
"""

from typing import Any

from panther.core.utils.log_statistics_display import create_display
from panther.core.utils.log_statistics_reporter import LogStatisticsReporter
from panther.core.utils.logger_factory import LoggerFactory


class ExperimentAnalysisMixin:
    """
    Mixin class for managing experiment observers in the PANTHER framework.

    This class provides methods to create and manage observers for experiments,
    including logging and metrics collection.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)

    def _setup_log_statistics(self):
        """Setup log statistics collection if enabled in configuration."""
        try:
            stats_config = getattr(
                self.global_config.logging, "statistics", None
            )  # TODO add parameter to pass stats_config
            if not stats_config or not stats_config.enabled:
                return

            # Enable statistics in LoggerFactory
            stats_dict = {
                "enabled": stats_config.enabled,
                "buffer_size": stats_config.buffer_size,
                "track_performance": stats_config.track_performance,
                "handler_type": stats_config.handler_type,
                "handler_buffer_size": stats_config.handler_buffer_size,
                "flush_interval": stats_config.flush_interval,
            }
            LoggerFactory.enable_statistics(stats_dict)

            # Setup real-time display if enabled
            if stats_config.real_time_display and hasattr(
                LoggerFactory, "_statistics_collector"
            ):
                self.log_statistics_display = create_display(
                    collector=LoggerFactory._statistics_collector,
                    display_mode="detailed",  # Could be configurable
                    interval=stats_config.collection_interval,
                    auto_clear=True,
                )

                # Start display in background
                if self.log_statistics_display.start_display():
                    self.logger.info("Started real-time log statistics display")
                else:
                    self.logger.warning("Failed to start log statistics display")

            self.logger.debug("Log statistics collection enabled")

        except Exception as e:
            self.logger.warning("Failed to setup log statistics: %s", e)

    def _generate_final_log_report(self):
        """Generate final logging statistics report."""
        try:
            stats_config = getattr(self.global_config.logging, "statistics", None)
            if (
                not stats_config
                or not stats_config.enabled
                or not stats_config.generate_reports
            ):
                return

            if not hasattr(LoggerFactory, "_statistics_collector"):
                return

            collector = LoggerFactory._statistics_collector
            reporter = LogStatisticsReporter(collector)

            # Generate reports in requested formats
            report_dir = self.experiment_dir / "log_statistics"
            report_dir.mkdir(exist_ok=True)

            base_filename = f"log_statistics_{self.experiment_name}"

            for format_type in stats_config.export_formats:
                try:
                    if format_type.lower() == "json":
                        filepath = report_dir / f"{base_filename}.json"
                        if reporter.export_to_file(filepath, "json", pretty=True):
                            self.logger.info(
                                "Generated JSON log statistics report: %s", filepath
                            )

                    elif format_type.lower() == "text":
                        filepath = report_dir / f"{base_filename}.txt"
                        if reporter.export_to_file(filepath, "text"):
                            self.logger.info(
                                "Generated text log statistics report: %s", filepath
                            )

                    elif format_type.lower() == "csv":
                        filepath = report_dir / f"{base_filename}.csv"
                        if reporter.export_to_file(filepath, "csv"):
                            self.logger.info(
                                "Generated CSV log statistics report: %s", filepath
                            )

                except Exception as e:
                    self.logger.warning(
                        "Failed to generate %s log statistics report: %s",
                        format_type,
                        e,
                    )

            # Also save a real-time snapshot for comparison purposes
            try:
                snapshot_path = report_dir / f"{base_filename}_final_snapshot.json"
                if reporter.save_real_time_snapshot(snapshot_path):
                    self.logger.debug(
                        "Saved final log statistics snapshot: %s", snapshot_path
                    )
            except Exception as e:
                self.logger.debug("Failed to save final snapshot: %s", e)

            # Log summary statistics to console
            try:
                stats = collector.get_real_time_stats()
                session = stats["session_info"]
                errors = stats["error_statistics"]

                self.logger.info("📊 Final Logging Statistics Summary:")
                self.logger.info("   Total Messages: %d", session["total_messages"])
                self.logger.info(
                    "   Duration: %.1f seconds", session["duration_seconds"]
                )
                self.logger.info(
                    "   Average Rate: %.2f messages/second",
                    session["messages_per_second"],
                )
                self.logger.info(
                    "   Total Errors: %d (%.2f%%)",
                    errors["total_errors"],
                    errors["error_rate_percent"],
                )

                # Show top features if available
                top_features = stats["message_distribution"]["by_feature"]
                if top_features:
                    top_3 = list(top_features.items())[:3]
                    self.logger.info(
                        "   Top Features: %s",
                        ", ".join([f"{name}({count})" for name, count in top_3]),
                    )

            except Exception as e:
                self.logger.debug("Failed to log statistics summary: %s", e)

        except Exception as e:
            self.logger.warning("Failed to generate final log statistics report: %s", e)

    def _generate_experiment_report(self):
        """Generate comprehensive experiment status report."""
        try:
            from panther.core.reporting.experiment_reporter import ExperimentReporter

            reporter = ExperimentReporter(self.experiment_dir, self.experiment_name)

            if quick_summary := reporter.generate_quick_summary():
                self.logger.info("Experiment Summary: %s", quick_summary)

            # Generate all report formats
            results = reporter.generate_reports()

            # Log success/failure for each format
            if results.get("json"):
                self.logger.info(
                    "Generated machine-readable experiment summary: experiment_summary.json"
                )

            if results.get("markdown"):
                self.logger.info(
                    "Generated human-readable experiment report: EXPERIMENT_REPORT.md"
                )

            if results.get("text"):
                self.logger.info(
                    "Generated text experiment summary: experiment_summary.txt"
                )

            # Log if any reports failed
            failed_reports = [fmt for fmt, success in results.items() if not success]
            if failed_reports:
                self.logger.warning(
                    "Failed to generate reports: %s", ", ".join(failed_reports)
                )

        except Exception as e:
            self.logger.error(
                "Failed to generate experiment report: %s", e, exc_info=True
            )

    def _analyze_test_case_config(self, test_case):
        """Analyze test case configuration for dry-run mode."""
        # Basic configuration analysis
        config = test_case.test_config

        self.logger.info("    📝 Test Name: %s", config.name)

        if hasattr(config, "iut") and config.iut:
            self.logger.info("    🎯 IUT: %s", config.iut.name)

        if hasattr(config, "tester") and config.tester:
            self.logger.info("    🧪 Tester: %s", config.tester.name)

        if hasattr(config, "network_environment") and config.network_environment:
            self.logger.info(
                "    🌐 Network Environment: %s", config.network_environment.name
            )

        if hasattr(config, "execution_environment") and config.execution_environment:
            self.logger.info(
                "    ⚙️  Execution Environment: %s", config.execution_environment.name
            )
