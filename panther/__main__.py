#!/usr/bin/env python3
"""
PANTHER CLI - Main entry point

This module provides the command-line interface for the PANTHER framework.
"""

import argparse
import argcomplete
import logging
import sys
from pathlib import Path

# Import metrics components
from panther.core.metrics import (
    MetricsCollector,
    ResourceMonitor,
    MetricsReporter,
    MetricsExporter,
)

# Import the plugin creation utility functions
try:
    from panther.plugins.plugin_creator import (
        is_development_mode,
        create_plugin,
        run_tutorial,
        launch_interactive_tutorials,
    )
except ImportError:
    # Fallback if the import fails (can happen during development)
    import importlib.util
    import sys

    # Try to load the module directly
    plugin_creator_path = Path(__file__).parent / "plugins" / "plugin_creator.py"
    if plugin_creator_path.exists():
        spec = importlib.util.spec_from_file_location("plugin_creator", plugin_creator_path)
        if spec is not None and spec.loader is not None:
            plugin_creator = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(plugin_creator)
            is_development_mode = plugin_creator.is_development_mode
            create_plugin = plugin_creator.create_plugin
            run_tutorial = plugin_creator.run_tutorial
            launch_interactive_tutorials = plugin_creator.launch_interactive_tutorials
        else:
            raise ImportError("Could not import plugin_creator module")
    else:
        raise ImportError("Could not find plugin_creator.py module")

from panther.core.experiment_manager import ExperimentManager
from panther.config.config_manager import ConfigLoader
from panther.plugins.plugin_params import list_plugin_parameters


def initialize_metrics(args):
    """
    Initialize metrics collection components based on command-line arguments.

    Args:
        args: Parsed command-line arguments

    Returns:
        tuple: (metrics_collector, resource_monitor, metrics_reporter, metrics_exporter)
    """
    # Check if metrics are explicitly disabled
    if hasattr(args, "disable_metrics") and args.disable_metrics:
        logging.info("Metrics collection is explicitly disabled.")
        return None, None, None, None

    # Check if metrics are enabled
    if not args.enable_metrics:
        logging.info("Metrics collection is disabled. Use --enable-metrics to enable.")
        return None, None, None, None

    try:
        from pathlib import Path

        # We'll defer creating the metrics directory until we know if an experiment directory is available.
        # For now, just store the path as specified in args if provided
        metrics_output_dir_path = args.metrics_output_dir

        # Get experiment name or use a default
        experiment_name = args.experiment_name or "unnamed_experiment"

        # Create the output directory path object
        metrics_output_dir = Path(args.metrics_output_dir)
        metrics_output_dir.parent.mkdir(parents=True, exist_ok=True)

        # Initialize metrics collector
        metrics_collector = MetricsCollector(
            experiment_name=experiment_name, output_dir=metrics_output_dir
        )

        # Ensure metrics collector has basic error handling
        if hasattr(metrics_collector, "initialize_error_handling"):
            metrics_collector.initialize_error_handling()

        logging.info(f"✅ Metrics collector initialized for experiment: {experiment_name}")
        logging.info(f"   Output directory: {metrics_output_dir}")

        # Initialize resource monitor if not disabled
        resource_monitor = None
        if not args.metrics_disable_resource_monitoring:
            try:
                resource_monitor = ResourceMonitor(
                    metrics_collector=metrics_collector,
                    interval=args.metrics_resource_interval,
                )
                # Add error handlers to resource monitor
                if hasattr(resource_monitor, "initialize_error_handling"):
                    resource_monitor.initialize_error_handling()
            except Exception as e:
                logging.warning(f"⚠️ Warning: Failed to initialize resource monitor: {e}")
                resource_monitor = None

        # Initialize reporter with error handling
        metrics_reporter = MetricsReporter(metrics_collector)
        if hasattr(metrics_reporter, "initialize_error_handling"):
            metrics_reporter.initialize_error_handling()

        # Initialize exporter with error handling
        metrics_exporter = MetricsExporter(metrics_collector)
        if hasattr(metrics_exporter, "initialize_error_handling"):
            metrics_exporter.initialize_error_handling()

        if not args.metrics_quiet:
            logging.info("✅ Metrics collection enabled")
            logging.info(f"   Output directory: {args.metrics_output_dir}")
            logging.info(f"   Export format: {args.metrics_export_format}")
            if resource_monitor:
                logging.info(f"   Resource monitoring interval: {args.metrics_resource_interval}s")

        return metrics_collector, resource_monitor, metrics_reporter, metrics_exporter

    except ImportError as e:
        logging.error(f"❌ Failed to import metrics components: {e}")
        return None, None, None, None
    except Exception as e:
        logging.error(f"❌ Failed to initialize metrics: {e}")
        return None, None, None, None


def finalize_metrics(
    args,
    metrics_collector,
    resource_monitor,
    metrics_reporter,
    metrics_exporter,
    execution_success,
    experiment_manager=None,
):
    """
    Finalize metrics collection and generate reports/exports.

    Args:
        args: Parsed command-line arguments
        metrics_collector: The metrics collector instance
        resource_monitor: The resource monitor instance
        metrics_reporter: The metrics reporter instance
        metrics_exporter: The metrics exporter instance
        execution_success: Whether the experiment execution was successful
        experiment_manager: The experiment manager instance (for getting experiment directory)
    """
    # First check if metrics are enabled and if we have a metrics collector
    if (
        not args
        or not getattr(args, "enable_metrics", False)
        or (hasattr(args, "disable_metrics") and args.disable_metrics)
    ):
        return

    if metrics_collector is None:
        # No metrics collector, nothing to finalize
        logging.info("ℹ️ No metrics to finalize (metrics collector not available)")
        return

    # Check if we have all the required metrics components
    if None in (metrics_collector, metrics_exporter, metrics_reporter):
        logging.info("ℹ️ Some metrics components not available, metrics may be limited")
        # Continue anyway to try to finalize what we have

    try:
        # Stop resource monitoring if available
        if resource_monitor is not None:
            try:
                resource_monitor.stop()
                if args and not getattr(args, "metrics_quiet", False):
                    logging.info("🔄 Stopped resource monitoring")
            except Exception as e:
                logging.warning(f"⚠️ Warning: Failed to stop resource monitor: {e}")

        # Record final status in metrics collector
        try:
            if execution_success:
                metrics_collector.increment_counter("experiments_successful")
                metrics_collector.record_gauge("experiment_final_status", 1)  # 1 = success
            else:
                metrics_collector.increment_counter("experiments_failed")
                metrics_collector.record_gauge("experiment_final_status", 0)  # 0 = failure
        except Exception as e:
            logging.warning(f"⚠️ Warning: Failed to record final experiment status: {e}")

        # Create output directory if it doesn't exist
        try:
            from pathlib import Path

            metrics_output_dir = (
                Path(args.metrics_output_dir)
                if args and hasattr(args, "metrics_output_dir") and args.metrics_output_dir
                else Path("metrics")
            )
            metrics_output_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            logging.error(f"❌ Failed to create metrics output directory: {e}")
            # Use current directory as fallback
            from pathlib import Path

            metrics_output_dir = Path(".")

        # Generate timestamp for files
        try:
            from datetime import datetime

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        except Exception:
            timestamp = "unknown_time"

        # Export metrics data if exporter is available
        export_success = False
        if metrics_exporter is not None:
            try:
                # Prepare all metrics data for export first
                metrics_exporter.prepare_metrics_data()

                # Get export format with fallback
                export_format = getattr(args, "metrics_export_format", "json") if args else "json"

                try:
                    if export_format == "json":
                        export_path = metrics_output_dir / f"metrics_{timestamp}.json"
                        # Make sure resource metrics are converted to serializable format
                        metrics_exporter.format_resource_metrics()
                        export_success = metrics_exporter.export_to_json(export_path)
                    elif export_format == "csv":
                        export_success = metrics_exporter.export_to_csv(metrics_output_dir)
                    elif export_format == "prometheus":
                        export_path = metrics_output_dir / f"metrics_{timestamp}.prom"
                        export_success = metrics_exporter.export_prometheus_format(export_path)
                    elif export_format == "dashboard":
                        export_path = metrics_output_dir / f"dashboard_{timestamp}.json"
                        # Make sure metrics are in dashboard-compatible format
                        metrics_exporter.prepare_dashboard_metrics()
                        export_success = metrics_exporter.export_dashboard_json(export_path)
                except Exception as e:
                    logging.error(f"❌ Failed to export metrics in {export_format} format: {e}")
                    export_success = False
            except Exception as e:
                logging.error(f"❌ Failed to prepare metrics data for export: {e}")
                export_success = False

        # Generate human-readable report if requested and reporter is available
        report_success = False
        if args and getattr(args, "metrics_generate_report", True) and metrics_reporter is not None:
            try:
                report_path = metrics_output_dir / f"metrics_report_{timestamp}.txt"
                report_success = metrics_reporter.generate_report(str(report_path))

                if not getattr(args, "metrics_quiet", False) and report_success:
                    logging.info(f"📊 Metrics report generated: {report_path}")
            except Exception as e:
                logging.error(f"❌ Failed to generate metrics report: {e}")

        # Print summary info if not in quiet mode
        if args and not getattr(args, "metrics_quiet", False):
            if export_success:
                logging.info(
                    f"📁 Metrics exported ({getattr(args, 'metrics_export_format', 'json')}): {metrics_output_dir}"
                )
            else:
                logging.warning("⚠️ Failed to export metrics or no exporter available")

            # Print summary, safely accessing metrics if available
            try:
                if metrics_collector:
                    total_experiments = metrics_collector.get_counter("experiments_total") or 0
                    successful_experiments = (
                        metrics_collector.get_counter("experiments_successful") or 0
                    )
                    failed_experiments = metrics_collector.get_counter("experiments_failed") or 0
                    total_execution_time = (
                        metrics_collector.get_timing_metric("total_execution_time") or 0
                    )

                    logging.info("\n📈 Metrics Summary:")
                    logging.info(f"   Total experiments: {total_experiments}")
                    logging.info(f"   Successful: {successful_experiments}")
                    logging.info(f"   Failed: {failed_experiments}")
                    logging.info(f"   Total execution time: {total_execution_time:.2f}s")
                else:
                    logging.warning("\n⚠️ No metrics collector available for summary")
            except Exception as e:
                logging.error(f"⚠️ Failed to show metrics summary: {e}")

    except Exception as e:
        logging.error(f"❌ Error in finalize_metrics: {e}")


def main():
    """Main entry point for the PANTHER CLI."""
    parser = argparse.ArgumentParser(description="Panther CLI")
    # TODO manage dir of the experiments configs
    parser.add_argument(
        "--experiment-config",
        type=str,
        default="experiment-config/experiment_config_example_minimal.yaml",
        help="Path to the configuration directory.",
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Override debug mode for detailed logging.",
    )
    parser.add_argument(
        "--validate-config",
        action="store_true",
        help="Flag to validate the configuration.",
    )
    parser.add_argument(
        "--list-plugin-params",
        type=str,
        metavar="PLUGIN_NAME",
        help="List available parameters for the specified plugin.",
    )
    parser.add_argument(
        "--plugin-type",
        type=str,
        choices=["iut", "tester", "network_environment", "execution_environment"],
        help="Type of plugin to show parameters for. Optional - will be auto-detected if not provided.",
    )
    parser.add_argument(
        "--protocol",
        type=str,
        help="Protocol for IUT/tester plugins (e.g., quic, http, minip). Optional - will be auto-detected if not provided.",
    )

    # Plugin creation and tutorial subcommands
    create_group = parser.add_argument_group("Plugin Creation and Tutorials")
    create_group.add_argument(
        "--create-plugin",
        nargs=2,
        metavar=("TYPE", "NAME"),
        help="Create a new plugin. TYPE can be service, environment, or protocol. NAME is the plugin name.",
    )
    create_group.add_argument(
        "--create-subplugin",
        nargs=3,
        metavar=("PLUGIN_TYPE", "PLUGIN_NAME", "SUBPLUGIN_TYPE"),
        help="Create a new subplugin within an existing plugin. PLUGIN_TYPE can be service, environment, or protocol. "
        "PLUGIN_NAME is the name of the existing plugin. SUBPLUGIN_TYPE is the type of subplugin to create "
        "(e.g., iut, tester, network_environment, execution_environment).",
    )
    create_group.add_argument(
        "--with-subplugins",
        action="store_true",
        help="Create default subplugins when creating a new plugin.",
    )
    create_group.add_argument(
        "--tutorial",
        type=str,
        choices=["service", "environment", "protocol"],
        help="Run an interactive tutorial for the specified plugin type.",
    )
    create_group.add_argument(
        "--interactive-tutorials",
        action="store_true",
        help="Launch the interactive tutorial menu.",
    )
    create_group.add_argument(
        "--dev-mode",
        action="store_true",
        help="Force development mode for plugin creation (put plugins in source tree).",
    )
    create_group.add_argument(
        "--production-mode",
        action="store_true",
        help="Force production mode for plugin creation (put plugins in user directory).",
    )

    parser.add_argument(
        "--exec-env-dir",
        type=str,
        help="Path to the execution plugin additional directory.",
    )
    parser.add_argument(
        "--net-env-dir",
        type=str,
        help="Path to the network plugin additional directory.",
    )
    parser.add_argument(
        "--iut-dir",
        type=str,
        help="Path to a new IUT plugin additional directory.",
    )
    parser.add_argument(
        "--tester-dir",
        type=str,
        help="Path to a new tester plugin additional directory.",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="outputs",
        help="Path to the output directory.",
    )
    parser.add_argument(
        "--experiment-name",
        type=str,
        default=None,
        help="Name of the experiment.",
    )
    parser.add_argument(
        "--teardown",
        action="store_true",
        help="Flag to teardown an existing experiment.",
    )
    parser.add_argument(
        "--webapp",
        action="store_true",
        help="Start the web app to configurate the experiments.",
    )

    # Metrics configuration
    metrics_group = parser.add_argument_group("Metrics Configuration")
    metrics_group.add_argument(
        "--enable-metrics",
        action="store_true",
        default=False,
        help="Enable comprehensive metrics collection during experiment execution. (default: enable)",
    )
    metrics_group.add_argument(
        "--disable-metrics",
        action="store_true",
        help="Explicitly disable metrics collection (overrides --enable-metrics).",
    )
    metrics_group.add_argument(
        "--metrics-output-dir",
        type=str,
        default="metrics",
        help="Directory to save metrics data and reports (default: experiment directory/metrics).",
    )
    metrics_group.add_argument(
        "--metrics-export-format",
        type=str,
        choices=["json", "csv", "prometheus", "dashboard"],
        default="json",
        help="Format for exporting metrics data (default: json).",
    )
    metrics_group.add_argument(
        "--metrics-resource-interval",
        type=float,
        default=3.0,
        help="Interval in seconds for resource monitoring (default: 3.0).",
    )
    metrics_group.add_argument(
        "--metrics-disable-resource-monitoring",
        action="store_true",
        help="Disable system resource monitoring to reduce overhead. (default: disabled).",
    )
    metrics_group.add_argument(
        "--metrics-generate-report",
        action="store_true",
        default=True,
        help="Generate a human-readable metrics report (default: enabled).",
    )
    metrics_group.add_argument(
        "--metrics-quiet",
        action="store_true",
        help="Suppress metrics-related output during execution.",
    )
    argcomplete.autocomplete(parser)
    args = parser.parse_args()

    # Handle plugin creation
    if args.create_plugin:
        plugin_type, plugin_name = args.create_plugin

        # Determine mode based on arguments or auto-detect
        dev_mode = None  # Auto-detect by default
        if args.dev_mode:
            dev_mode = True
        elif args.production_mode:
            dev_mode = False

        try:
            # Pass the with_subplugins flag
            success = create_plugin(
                plugin_type,
                plugin_name,
                in_development_mode=dev_mode,
                create_subplugins=args.with_subplugins,
            )
            return 0 if success else 1
        except Exception as e:
            logging.error(f"❌ Error creating plugin: {e}")
            return 1

    # Handle subplugin creation
    if args.create_subplugin:
        plugin_type, plugin_name, subplugin_type = args.create_subplugin

        # Determine mode based on arguments or auto-detect
        dev_mode = None  # Auto-detect by default
        if args.dev_mode:
            dev_mode = True
        elif args.production_mode:
            dev_mode = False

        try:
            # Import the subplugin creation function
            from panther.plugins.plugin_creator import create_subplugin

            success = create_subplugin(
                plugin_type, plugin_name, subplugin_type, in_development_mode=dev_mode
            )
            return 0 if success else 1
        except Exception as e:
            logging.error(f"❌ Error creating subplugin: {e}")
            return 1

    # Handle tutorial execution
    if args.tutorial:
        try:
            return run_tutorial(args.tutorial)
        except Exception as e:
            logging.error(f"❌ Error running tutorial: {e}")
            return 1

    # Handle interactive tutorial menu
    if args.interactive_tutorials:
        try:
            # Import the interactive tutorials function
            from panther.plugins.plugin_creator import launch_interactive_tutorials

            launch_interactive_tutorials()
            return 0
        except Exception as e:
            logging.error(f"❌ Error launching interactive tutorials: {e}")
            return 1

    if args.list_plugin_params:
        config_loader = ConfigLoader(
            args.experiment_config,
            args.output_dir,
            args.exec_env_dir,
            args.net_env_dir,
            args.iut_dir,
            args.tester_dir,
        )

        # Use the dedicated function for listing plugin parameters
        params = list_plugin_parameters(
            plugin_name=args.list_plugin_params,
            plugin_type=args.plugin_type,
            protocol=args.protocol,  # Pass the protocol parameter
        )

        if not params:
            return 1

        # Print parameters in a readable format
        logging.info(
            f"\n{'Parameter':<20} {'Type':<30} {'Default':<20} {'Required':<10} Description"
        )
        logging.info("-" * 100)
        for name, info in params.items():
            default = str(info["default"]) if info["default"] is not None else "None"
            required = "Yes" if info["required"] else "No"
            desc = info["description"]

            # Handle special version field with additional information
            if name == "version" and "value" in info:
                version_info = info["value"]
                if hasattr(version_info, "version") and version_info.version:
                    desc += f" (Version: {version_info.version})"
                if hasattr(version_info, "commit") and version_info.commit:
                    desc += f" (Commit: {version_info.commit})"
                if info.get("note"):
                    desc += f" - {info['note']}"

            logging.info(f"{name:<20} {info['type']:<30} {default:<20} {required:<10} {desc}")

            # If this is a version field with client/server details, show them
            if name == "version" and "value" in info:
                version_info = info["value"]
                if hasattr(version_info, "client") and version_info.client:
                    logging.info("  ├─ client: Configuration for client role")
                if hasattr(version_info, "server") and version_info.server:
                    logging.info("  └─ server: Configuration for server role")

        return 0
    elif args.teardown:
        experiment_dir = getattr(args, "experiment_dir", None)
        if not experiment_dir:
            logging.error(
                "Please provide the experiment directory to teardown using '--experiment-dir'."
            )
            return 1
        raise NotImplementedError("Teardown functionality is not implemented yet.")
    elif args.validate_config:
        logging.info("Validating the configuration.")
        config_loader = ConfigLoader(
            args.experiment_config,
            args.output_dir,
            args.exec_env_dir,
            args.net_env_dir,
            args.iut_dir,
            args.tester_dir,
        )
        # We get the global configurations
        global_config = config_loader.load_and_validate_global_config()
        # We create the experiment manager
        experiment_manager = ExperimentManager(
            global_config=global_config, experiment_name=args.experiment_name
        )
        config_loader.load_and_validate_experiment_config()
        return 0
    else:
        # Create ConfigLoader (without metrics collector for now)
        config_loader = ConfigLoader(
            args.experiment_config,
            args.output_dir,
            args.exec_env_dir,
            args.net_env_dir,
            args.iut_dir,
            args.tester_dir,
            metrics_collector=None,  # Fix: Set metrics_collector to None initially
            debug_override=args.debug,
        )

        # Load global configuration
        global_config = config_loader.load_and_validate_global_config()

        # Create the experiment manager to get the experiment directory
        experiment_manager = ExperimentManager(
            global_config=global_config,
            experiment_name=args.experiment_name,
            metrics_collector=None,  # We'll set this later if metrics are enabled
        )

        # Now determine the metrics output directory
        from pathlib import Path

        # Check if user explicitly specified metrics output directory with --metrics-output-dir
        if args.metrics_output_dir != "metrics":  # Not using the default
            metrics_dir = Path(args.metrics_output_dir)
            # Store original argument back for later use in output messages
            args.metrics_output_dir = str(metrics_dir)
        else:
            # Use experiment directory as the metrics output directory
            if hasattr(experiment_manager, "experiment_dir") and experiment_manager.experiment_dir:
                metrics_dir = experiment_manager.experiment_dir / "metrics"
                # Update the argument for display purposes
                args.metrics_output_dir = str(metrics_dir)
            else:
                # Fallback to default if no experiment dir is available
                metrics_dir = Path("metrics")

        # Initialize metrics collection if enabled
        metrics_collector, resource_monitor, metrics_reporter, metrics_exporter = (
            initialize_metrics(args)
        )

        # Update the experiment manager with metrics collector
        if metrics_collector:
            experiment_manager.metrics_collector = metrics_collector

        if args.webapp:
            raise NotImplementedError("WebApplication functionality is not fully implemented yet.")
            try:
                from panther.webapp.web_app import run

                run(config_loader, global_config, args)
                return 0
            except Exception as e:
                logging.error(e)
                return 1
            finally:
                sys.stdout.close()
                sys.stderr.close()
                sys.stdout = sys.__stdout__
                sys.stderr = sys.__stderr__
        else:
            execution_success = False

            try:
                # Start resource monitoring if enabled
                if resource_monitor:
                    resource_monitor.start()

                # Record overall execution timing
                if metrics_collector:
                    metrics_collector.increment_counter("experiments_total")
                    metrics_collector.start_timer("total_execution_time")

                # Note: We already created the experiment manager above when determining the metrics directory
                # We may need to update the ConfigLoader with metrics collector (if one was created)
                if metrics_collector:
                    config_loader.metrics_collector = metrics_collector

                # Load and validate experiment config with timing
                if metrics_collector:
                    with metrics_collector.timing_context("config_loading_and_validation"):
                        experiment_config = config_loader.load_and_validate_experiment_config()
                else:
                    experiment_config = config_loader.load_and_validate_experiment_config()

                # Initialize experiments with timing
                if metrics_collector:
                    with metrics_collector.timing_context("experiment_initialization"):
                        experiment_manager.initialize_experiments(experiment_config)
                else:
                    experiment_manager.initialize_experiments(experiment_config)

                # Start the experiment execution with timing
                if metrics_collector:
                    with metrics_collector.timing_context("test_execution"):
                        experiment_manager.run_tests()
                else:
                    experiment_manager.run_tests()

                # Complete overall timing
                if metrics_collector:
                    metrics_collector.stop_timer("total_execution_time")

                return 0

            except Exception as e:
                if metrics_collector:
                    try:
                        metrics_collector.increment_counter("experiments_failed")

                        # Get error type safely
                        error_type = "UnknownError"
                        try:
                            error_type = type(e).__name__
                        except Exception:
                            pass

                        # Get error message safely
                        error_message = "No details available"
                        try:
                            error_message = str(e)
                        except Exception:
                            pass

                        # Record error with robust error handling
                        try:
                            metrics_collector.record_error(
                                error_type=error_type,
                                error_message=error_message,
                                phase="experiment_execution",
                                component="main",
                                exception=e,
                            )
                        except Exception as err:
                            # If error recording fails, log it but don't raise
                            logging.error(f"Failed to record error in metrics: {err}")
                    except Exception as err:
                        # Don't let metrics issues stop execution
                        logging.error(f"Error during metrics error recording: {err}")

                logging.error(f"Experiment execution failed: {e}")
                return 1
            finally:
                config_loader.cleanup()


if __name__ == "__main__":
    sys.exit(main() or 0)
