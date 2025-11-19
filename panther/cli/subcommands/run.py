"""
Run Command - Execute PANTHER experiments
"""

import logging
from argparse import ArgumentParser, _SubParsersAction
from pathlib import Path
from typing import Any

from panther.cli.base import BaseCommand
from panther.config import ConfigurationManager
from panther.core.experiment_manager import ExperimentManager


class RunCommand(BaseCommand):
    """Handle experiment execution commands."""

    @classmethod
    def register_parser(cls, subparsers: _SubParsersAction) -> ArgumentParser:
        """Register the run subcommand parser."""
        parser = subparsers.add_parser(
            "run",
            help="Execute PANTHER experiments",
            description="Run experiments using configuration files",
        )

        parser.add_argument(
            "--config",
            type=str,
            required=True,
            help="Path to experiment configuration file",
        )

        parser.add_argument(
            "--output-dir",
            type=str,
            default="outputs",
            help="Output directory for experiment results (default: outputs)",
        )

        parser.add_argument(
            "--experiment-name", type=str, help="Override experiment name"
        )

        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what commands would be executed without running them",
        )

        # Plugin directories
        plugin_group = parser.add_argument_group("Plugin Directories")
        plugin_group.add_argument(
            "--exec-env-dir",
            type=str,
            default="",
            help="Custom execution environment plugin directory",
        )
        plugin_group.add_argument(
            "--net-env-dir",
            type=str,
            default="",
            help="Custom network environment plugin directory",
        )
        plugin_group.add_argument(
            "--iut-dir", type=str, default="", help="Custom IUT plugin directory"
        )
        plugin_group.add_argument(
            "--tester-dir", type=str, default="", help="Custom tester plugin directory"
        )

        # Metrics options
        metrics_group = parser.add_argument_group("Metrics Options")
        metrics_group.add_argument(
            "--enable-metrics",
            action="store_true",
            help="Enable metrics collection during experiment",
        )

        # Docker user mapping options
        docker_group = parser.add_argument_group("Docker User Mapping")
        docker_group.add_argument(
            "--docker-run-as-host",
            action="store_true",
            help="Run containers with host user ID for volume mount compatibility",
        )
        docker_group.add_argument(
            "--docker-user-id", type=int, help="Custom user ID to use in containers"
        )
        docker_group.add_argument(
            "--docker-group-id", type=int, help="Custom group ID to use in containers"
        )
        docker_group.add_argument(
            "--docker-user-name",
            type=str,
            default="panther",
            help="Username for custom user creation (default: panther)",
        )
        metrics_group.add_argument(
            "--disable-metrics",
            action="store_true",
            help="Explicitly disable metrics collection",
        )
        metrics_group.add_argument(
            "--metrics-output-dir",
            type=str,
            default="metrics",
            help="Metrics output directory (default: metrics)",
        )
        metrics_group.add_argument(
            "--metrics-format",
            type=str,
            choices=["json", "csv", "txt"],
            default="json",
            help="Metrics export format (default: json)",
        )
        metrics_group.add_argument(
            "--metrics-interval",
            type=float,
            default=3.0,
            help="Resource monitoring interval in seconds (default: 3.0)",
        )
        metrics_group.add_argument(
            "--metrics-disable-resource-monitoring",
            action="store_true",
            help="Disable resource monitoring",
        )
        metrics_group.add_argument(
            "--metrics-generate-report",
            action="store_true",
            help="Generate metrics report after experiment",
        )
        metrics_group.add_argument(
            "--metrics-quiet",
            action="store_true",
            help="Suppress metrics collection output",
        )

        return parser

    @classmethod
    def handle(cls, args: Any) -> int:
        """Handle the run command execution."""
        try:
            # Import metrics components
            from panther.core.metrics import (
                MetricsCollector,
                MetricsExporter,
                MetricsReporter,
                ResourceMonitor,
            )
            from panther.core.utils.logger_factory import LoggerFactory

            # Validate config file exists
            config_path = Path(args.config)
            if not config_path.exists():
                cls.get_instance().logger.error(f"❌ Configuration file not found: {config_path}")
                cls.get_instance().logger.error(
                    f"   Please ensure the experiment config file exists at the specified path."
                )
                cls.get_instance().logger.error(f"   Current working directory: {Path.cwd()}")
                if config_path.is_absolute():
                    cls.get_instance().logger.error(f"   Absolute path provided: {config_path}")
                else:
                    cls.get_instance().logger.error(
                        f"   Relative path resolved to: {config_path.resolve()}"
                    )
                return 1

            cls.get_instance().logger.info(f"🚀 Starting PANTHER experiment with config: {config_path}")

            # Check for dry-run mode
            if args.dry_run:
                cls.get_instance().logger.info(
                    "🔍 DRY-RUN MODE: Analyzing experiment configuration without execution"
                )

            # Load configuration to get logging settings
            config_loader = ConfigurationManager(
                experiment_file=str(config_path),
                debug_override=args.debug if hasattr(args, "debug") else False,
            )

            cls.get_instance().logger.info("📂 Loading global configuration...")
            # Load global config for logging settings
            global_config = config_loader.load_and_validate_global_config()

            # Override Docker user mapping settings from CLI arguments
            if global_config and hasattr(global_config, "docker"):
                if args.docker_run_as_host:
                    global_config.docker.user_mapping.run_as_host_user = True
                if args.docker_user_id is not None:
                    global_config.docker.user_mapping.custom_uid = args.docker_user_id
                if args.docker_group_id is not None:
                    global_config.docker.user_mapping.custom_gid = args.docker_group_id
                if (
                    args.docker_user_name != "panther"
                ):  # Only override if explicitly set
                    global_config.docker.user_mapping.user_name = args.docker_user_name

            # Initialize LoggerFactory with configuration
            if global_config and hasattr(global_config, "logging"):
                logging_config = {
                    "level": (
                        global_config.logging.level.name
                        if hasattr(global_config.logging.level, "name")
                        else str(global_config.logging.level)
                    ),
                    "format": global_config.logging.format,
                    "enable_colors": getattr(
                        global_config.logging, "enable_colors", True
                    ),
                }

                # Include feature_levels if available
                if hasattr(global_config.logging, "feature_levels"):
                    logging_config[
                        "feature_levels"
                    ] = global_config.logging.feature_levels

                LoggerFactory.initialize(logging_config)

            # Initialize metrics if enabled
            metrics_collector = None
            resource_monitor = None
            metrics_reporter = None
            metrics_exporter = None

            if args.enable_metrics and not args.disable_metrics:
                try:
                    experiment_name = args.experiment_name or "experiment"
                    metrics_output_dir = Path(args.metrics_output_dir)
                    metrics_output_dir.parent.mkdir(parents=True, exist_ok=True)

                    metrics_collector = MetricsCollector(
                        experiment_name=experiment_name, output_dir=metrics_output_dir
                    )

                    if not args.metrics_disable_resource_monitoring:
                        resource_monitor = ResourceMonitor(
                            metrics_collector=metrics_collector,
                            interval=args.metrics_interval,
                        )

                    if args.metrics_generate_report:
                        metrics_reporter = MetricsReporter(
                            metrics_collector=metrics_collector
                        )

                    metrics_exporter = MetricsExporter(
                        metrics_collector=metrics_collector
                    )

                    if not args.metrics_quiet:
                        cls.get_instance().logger.info(
                            f"📊 Metrics collection enabled for: {experiment_name}"
                        )

                except Exception as e:
                    cls.get_instance().logger.info(f"⚠️  Warning: Failed to initialize metrics: {e}")

            # Update config_loader with additional parameters
            config_loader.output_dir = args.output_dir
            config_loader.exec_env_dir = args.exec_env_dir
            config_loader.net_env_dir = args.net_env_dir
            config_loader.iut_dir = args.iut_dir
            config_loader.testers_dir = args.tester_dir
            config_loader.metrics_collector = metrics_collector

            # Load experiment configuration
            cls.get_instance().logger.info("📋 Loading experiment configuration...")
            try:
                experiment_config = config_loader.load_and_validate_experiment_config()
            except FileNotFoundError as e:
                cls.get_instance().logger.error(f"❌ Configuration file error: {e}")
                return 1
            except ValueError as e:
                cls.get_instance().logger.error(f"❌ Configuration validation error: {e}")
                return 1
            except PermissionError as e:
                cls.get_instance().logger.error(f"❌ Configuration file access error: {e}")
                return 1
            except Exception as e:
                cls.get_instance().logger.error(f"❌ Unexpected configuration error: {e}")
                if hasattr(args, "debug") and args.debug:
                    import traceback

                    traceback.print_exc()
                return 1

            # Create experiment manager with global config
            experiment_manager = ExperimentManager(
                global_config=global_config,
                experiment_name=args.experiment_name,
                metrics_collector=metrics_collector,
                dry_run=args.dry_run,
            )

            # Initialize experiments with experiment config
            cls.get_instance().logger.info("🔧 Initializing experiment...")
            experiment_manager.initialize_experiments(experiment_config)

            # Start resource monitoring if enabled
            if resource_monitor:
                try:
                    resource_monitor.start()
                except Exception as e:
                    cls.get_instance().logger.info(
                        f"⚠️  Warning: Failed to start resource monitoring: {e}"
                    )

            # Run the tests
            cls.get_instance().logger.info("🚀 Running tests...")
            success = experiment_manager.run_tests()

            # Stop resource monitoring
            if resource_monitor:
                try:
                    resource_monitor.stop()
                except Exception as e:
                    cls.get_instance().logger.info(
                        f"⚠️  Warning: Failed to stop resource monitoring: {e}"
                    )

            # Generate metrics report
            if metrics_reporter and args.metrics_generate_report:
                try:
                    report_path = metrics_output_dir / "metrics_report.txt"
                    success = metrics_reporter.generate_report(str(report_path))
                    if success and not args.metrics_quiet:
                        cls.get_instance().logger.info("📈 Metrics report generated")
                    elif not success:
                        cls.get_instance().logger.info("⚠️  Warning: Failed to generate metrics report")
                except Exception as e:
                    cls.get_instance().logger.info(f"⚠️  Warning: Failed to generate metrics report: {e}")

            # Export metrics
            if metrics_exporter:
                try:
                    # Determine output path based on format
                    output_path = metrics_output_dir / f"metrics.{args.metrics_format}"

                    # Export using appropriate method based on format
                    if args.metrics_format == "json":
                        success = metrics_exporter.export_to_json(output_path)
                    elif args.metrics_format == "csv":
                        success = metrics_exporter.export_to_csv(output_path)
                    else:  # txt format - fallback to JSON
                        success = metrics_exporter.export_to_json(output_path)

                    if success and not args.metrics_quiet:
                        cls.get_instance().logger.info(
                            f"💾 Metrics exported to {args.metrics_format} format"
                        )
                    elif not success:
                        cls.get_instance().logger.info(
                            f"⚠️  Warning: Failed to export metrics to {args.metrics_format} format"
                        )
                except Exception as e:
                    cls.get_instance().logger.info(f"⚠️  Warning: Failed to export metrics: {e}")

            if success:
                cls.get_instance().logger.info("✅ Experiment completed successfully")
                return 0
            else:
                cls.get_instance().logger.info("❌ Experiment failed")
                return 1

        except KeyboardInterrupt:
            cls.get_instance().logger.info("\n⚠️  Experiment interrupted by user")
            return 130
        except Exception as e:
            cls.get_instance().logger.info(f"❌ Error running experiment: {e}")
            if hasattr(args, "debug") and args.debug:
                import traceback

                traceback.print_exc()
            return 1
