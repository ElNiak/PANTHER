"""Run Command.

Execute PANTHER experiments with enhanced user experience and error handling.
"""

import datetime
import logging
import time
from pathlib import Path

import click
import yaml
from termcolor import colored

from panther.cli.core.base import (
    error_message,
    featured_example,
    handle_errors,
    info_message,
    pass_context_and_setup_logging,
    success_message,
)
from panther.core.utils.logger_factory import TRACE


@featured_example("panther run --config experiment.yaml")
@click.command()
@click.option(
    "--config",
    "-c",
    type=click.Path(exists=True),
    required=True,
    help="Path to experiment configuration file",
)
@click.option(
    "--output-dir",
    "-o",
    type=click.Path(),
    default="outputs",
    help="Output directory for experiment results (default: outputs)",
)
@click.option("--experiment-name", help="Override experiment name from configuration")
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what commands would be executed without running them",
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Enable verbose output (DEBUG level on console)",
)
@click.option(
    "--debug",
    is_flag=True,
    help="Enable TRACE-level console output (overrides --verbose)",
)
# Plugin directories group
@click.option(
    "--exec-env-dir",
    type=click.Path(exists=True, file_okay=False),
    help="Custom execution environment plugin directory",
)
@click.option(
    "--net-env-dir",
    type=click.Path(exists=True, file_okay=False),
    help="Custom network environment plugin directory",
)
@click.option(
    "--iut-dir",
    type=click.Path(exists=True, file_okay=False),
    help="Custom IUT plugin directory",
)
@click.option(
    "--tester-dir",
    type=click.Path(exists=True, file_okay=False),
    help="Custom tester plugin directory",
)
# Metrics options group
@click.option(
    "--enable-metrics/--disable-metrics",
    default=False,
    help="Enable/disable ALL metrics collection (CLI and observer-based) during experiment",
)
@click.option(
    "--metrics-output-dir",
    type=click.Path(),
    default="outputs",
    help="Base directory for metrics collector state. Note: final exported metrics are written to <experiment_dir>/metrics/ during cleanup (default: outputs)",
)
@click.option(
    "--metrics-interval",
    type=int,
    default=1,
    help="Metrics collection interval in seconds (default: 1)",
)
@click.option(
    "--metrics-disable-resource-monitoring",
    is_flag=True,
    help="Disable resource monitoring in metrics collection",
)
# Docker user mapping options
@click.option(
    "--docker-run-as-host",
    is_flag=True,
    help="Run containers with host user ID for volume mount compatibility",
)
@click.option("--docker-user-id", type=int, help="Custom user ID to use in containers")
@click.option(
    "--docker-group-id", type=int, help="Custom group ID to use in containers"
)
@click.option(
    "--docker-user-name",
    default="panther",
    help="Username for custom user creation (default: panther)",
)
@click.option(
    "--force-build/--no-force-build",
    default=None,
    help="Force rebuild Docker images without cache (overrides YAML force_build_docker_image)",
)
@click.option(
    "--no-docker-cache",
    is_flag=True,
    default=False,
    help="Force rebuild AND skip Docker layer cache entirely (implies --force-build)",
)
@handle_errors
@pass_context_and_setup_logging
def run(
    ctx,
    config,
    output_dir,
    experiment_name,
    dry_run,
    verbose,
    debug,
    exec_env_dir,
    net_env_dir,
    iut_dir,
    tester_dir,
    enable_metrics,
    metrics_output_dir,
    metrics_interval,
    metrics_disable_resource_monitoring,
    docker_run_as_host,
    docker_user_id,
    docker_group_id,
    docker_user_name,
    force_build,
    no_docker_cache,
):
    r"""Execute PANTHER experiments with specified configuration.

    Runs protocol analysis and testing experiments using Docker-based
    environments. Supports multiple network configurations, plugin
    systems, and comprehensive metrics collection.

    \b
    Key Features:
    🚀 Experiment execution with comprehensive logging
    🐋 Docker-based isolated testing environments
    📊 Optional metrics collection and reporting
    🔧 Plugin system for custom implementations
    ⚙️  Flexible configuration management

    \b
    Configuration:
    The experiment configuration file defines:
    • Network environment (localhost, docker-compose, shadow-ns)
    • Protocol implementations to test
    • Test scenarios and parameters
    • Plugin configurations
    • Output settings

    \b
    Examples:
      # Basic experiment execution
      panther run --config experiment.yaml

      # With custom output directory
      panther run --config tests/quic.yaml --output-dir results/

      # Dry run to validate configuration
      panther run --config experiment.yaml --dry-run

      # With metrics collection
      panther run --config experiment.yaml --enable-metrics

      # Custom Docker user mapping
      panther run --config experiment.yaml --docker-run-as-host

      # Override experiment name
      panther run --config experiment.yaml --experiment-name "custom-test"

    \b
    Plugin Directories:
    Use custom plugin directories to extend PANTHER functionality:
    • --exec-env-dir: Execution environment plugins
    • --net-env-dir: Network environment plugins
    • --iut-dir: Implementation Under Test plugins
    • --tester-dir: Protocol tester plugins

    \b
    Metrics Collection:
    When enabled, collects comprehensive metrics including:
    • Resource usage (CPU, memory, network)
    • Test execution timing
    • Protocol-specific measurements
    • Docker container statistics
    """
    # Enhanced logging setup -- merge top-level and per-command flags
    debug = debug or ctx.obj.get("debug", False)
    verbose = verbose or ctx.obj.get("verbose", False)

    # Determine console_level: --debug (TRACE=5) wins over --verbose (DEBUG)
    console_level = None
    if debug:
        console_level = TRACE
    elif verbose:
        console_level = logging.DEBUG

    if verbose or debug:
        info_message(f"Starting PANTHER experiment with config: {config}")

    # Validate output directory
    output_dir = Path(output_dir)
    if not output_dir.exists():
        output_dir.mkdir(parents=True, exist_ok=True)
        if verbose or debug:
            info_message(f"Created output directory: {output_dir}")

    # Show configuration summary
    if verbose or debug:
        click.echo(colored("📋 Experiment Configuration:", "blue", attrs=["bold"]))
        click.echo(f"   📄 Config file: {config}")
        click.echo(f"   📁 Output directory: {output_dir}")
        if experiment_name:
            click.echo(f"   🏷️  Experiment name: {experiment_name}")
        if dry_run:
            click.echo(f"   🔍 Mode: {colored('DRY RUN', 'yellow', attrs=['bold'])}")
        if enable_metrics:
            click.echo(f"   📊 Metrics: {colored('ENABLED', 'green', attrs=['bold'])}")
            click.echo(f"   📈 Metrics output: {Path(metrics_output_dir) / 'metrics'}")
        click.echo()

    # Dry run mode information
    if dry_run:
        info_message(
            "DRY-RUN MODE: Analyzing experiment configuration without execution"
        )
        click.echo()

    try:
        if dry_run:
            click.echo(colored("🔍 DRY RUN - Configuration Analysis:", "yellow"))

            # Validate configuration file
            try:
                with open(config, "r") as f:
                    config_data = yaml.safe_load(f)
                click.echo(f"   ✓ Config file: {config} (valid YAML)")

                # Validate configuration structure
                if "tests" in config_data:
                    test_count = len(config_data["tests"])
                    click.echo(f"   ✓ Found {test_count} test configuration(s)")

                    for i, test in enumerate(config_data["tests"]):
                        if "name" in test:
                            click.echo(f"   ✓ Test {i+1}: {test['name']}")
                        if "services" in test:
                            service_count = len(test["services"])
                            click.echo(f"      - {service_count} service(s) configured")
                else:
                    click.echo("   ⚠️  No tests found in configuration")

            except yaml.YAMLError as e:
                click.echo(f"   ❌ Config file: {config} (YAML error: {e})")
                raise click.Abort()

            click.echo(f"   ✓ Output directory: {output_dir}")
            if enable_metrics:
                click.echo(
                    f"   ✓ Metrics directory: {Path(metrics_output_dir) / 'metrics'}"
                )
            click.echo(f"   ✓ Experiment ready to execute")

            info_message("Dry run completed - configuration is valid")
            return

        else:
            click.echo(colored("🚀 Executing PANTHER experiment...", "green"))

            try:
                from panther.config import ConfigurationManager
                from panther.core.experiment_manager import ExperimentManager
                from panther.core.metrics import MetricsCollector

                info_message("Loading configuration...")

                # Build CLI overrides (CLI > YAML > Pydantic defaults)
                from panther.config.core.utils import extract_cli_overrides

                cli_overrides = extract_cli_overrides(ctx)

                manager = ConfigurationManager(
                    exec_env_dir=exec_env_dir or "",
                    net_env_dir=net_env_dir or "",
                    iut_dir=iut_dir or "",
                    testers_dir=tester_dir or "",
                )
                global_config, experiment_config = manager.load_full_config(
                    config, cli_overrides=cli_overrides
                )

                # Set up metrics if enabled
                metrics_collector = None
                if enable_metrics:
                    metrics_output_path = Path(metrics_output_dir)
                    metrics_output_path.mkdir(parents=True, exist_ok=True)
                    exp_name = experiment_name or Path(config).stem
                    metrics_collector = MetricsCollector(
                        experiment_name=exp_name,
                        output_dir=metrics_output_path,
                        collection_interval=float(metrics_interval),
                    )
                    if not metrics_disable_resource_monitoring:
                        metrics_collector.start_collection_thread(
                            interval=float(metrics_interval)
                        )

                info_message(f"Initializing experiment manager...")

                # Initialize experiment manager with context manager so
                # cleanup() (including metrics export) always runs.
                with ExperimentManager(
                    global_config=global_config,
                    experiment_name=experiment_name,
                    metrics_collector=metrics_collector,
                    dry_run=False,
                    console_level=console_level,
                ) as experiment_manager:
                    # Initialize experiments with experiment config
                    info_message("🔧 Initializing experiment...")
                    experiment_manager.initialize_experiments(experiment_config)

                    # Execute the experiment
                    info_message("🚀 Running tests...")
                    success = experiment_manager.run_tests()

                    if success:
                        success_message("All experiments completed successfully")
                    else:
                        error_message("Experiment execution encountered errors")
                        raise click.Abort()

            except ImportError as e:
                error_message(
                    f"PANTHER installation is incomplete: ExperimentManager could not "
                    f"be imported ({e}). Please run 'panther build dev' "
                    f"(or 'python panther_builder.py package-dev') to install all dependencies."
                )
                raise click.Abort()

    except Exception as e:
        error_message(f"Experiment execution failed: {e}")
        if ctx.obj.get("debug", False):
            import traceback

            click.echo(traceback.format_exc(), err=True)
        raise click.Abort()


# Make run the main command, not a group
# The main experiment execution command


# Separate status command (can be added to main CLI if needed)
@click.command("status")
@click.option("--experiment-name", help="Show status for specific experiment")
@click.option(
    "--output-dir",
    "-o",
    type=click.Path(exists=True),
    default="outputs",
    help="Output directory to check (default: outputs)",
)
@handle_errors
@pass_context_and_setup_logging
def status(ctx, experiment_name, output_dir):
    """Show status of running or completed experiments.

    Displays information about experiment execution status,
    progress, and results location.
    """
    output_dir = Path(output_dir)

    click.echo(colored("📊 Experiment Status", "blue", attrs=["bold"]))
    click.echo()

    if experiment_name:
        click.echo(f"🔍 Checking status for experiment: {experiment_name}")
    else:
        click.echo("🔍 Checking all experiments")

    # Check for experiment directories
    if output_dir.exists():
        experiment_dirs = [d for d in output_dir.iterdir() if d.is_dir()]

        if experiment_dirs:
            click.echo(
                f"📁 Found {len(experiment_dirs)} experiment(s) in {output_dir}:"
            )
            click.echo()

            for exp_dir in experiment_dirs:
                # Check for completion indicators
                log_file = exp_dir / "experiment.log"
                config_file = exp_dir / "experiment_config.yaml"

                if log_file.exists():
                    status_icon = "✅"
                    status_text = colored("Completed", "green")
                else:
                    status_icon = "🔄"
                    status_text = colored("In Progress", "yellow")

                click.echo(f"  {status_icon} {exp_dir.name}: {status_text}")

                if config_file.exists():
                    click.echo(f"     📄 Config: {config_file}")
                if log_file.exists():
                    click.echo(f"     📝 Log: {log_file}")
                click.echo()
        else:
            info_message(f"No experiments found in {output_dir}")
    else:
        error_message(f"Output directory not found: {output_dir}")


@click.command("list-experiments")
@click.option(
    "--output-dir",
    "-o",
    type=click.Path(),
    default="outputs",
    help="Output directory to list (default: outputs)",
)
@click.option("--verbose", "-v", is_flag=True, help="Show detailed information")
@handle_errors
def list_experiments(output_dir, verbose):
    """List all experiments in output directory.

    Shows comprehensive list of all experiment runs with
    timestamps, status, and result information.
    """
    output_dir = Path(output_dir)

    click.echo(colored("📋 Experiment History", "blue", attrs=["bold"]))
    click.echo()

    if not output_dir.exists():
        info_message(f"Output directory does not exist: {output_dir}")
        return

    experiment_dirs = sorted(
        [d for d in output_dir.iterdir() if d.is_dir()],
        key=lambda x: x.stat().st_mtime,
        reverse=True,
    )

    if not experiment_dirs:
        info_message(f"No experiments found in {output_dir}")
        return

    click.echo(f"📁 Found {len(experiment_dirs)} experiment(s):")
    click.echo()

    for exp_dir in experiment_dirs:
        # Get experiment info
        config_file = exp_dir / "experiment_config.yaml"
        log_file = exp_dir / "experiment.log"

        # Determine status
        if log_file.exists():
            status_icon = "✅"
            status_text = colored("Completed", "green")
        else:
            status_icon = "🔄"
            status_text = colored("In Progress", "yellow")

        # Get timestamp
        timestamp = exp_dir.stat().st_mtime
        dt = datetime.datetime.fromtimestamp(timestamp)
        time_str = dt.strftime("%Y-%m-%d %H:%M:%S")

        click.echo(f"{status_icon} {colored(exp_dir.name, 'cyan', attrs=['bold'])}")
        click.echo(f"   Status: {status_text}")
        click.echo(f"   Created: {time_str}")

        if verbose:
            if config_file.exists():
                click.echo(f"   Config: {config_file}")
            if log_file.exists():
                click.echo(f"   Log: {log_file}")

            # Show file count
            files = list(exp_dir.rglob("*"))
            file_count = len([f for f in files if f.is_file()])
            click.echo(f"   Files: {file_count}")

        click.echo()
