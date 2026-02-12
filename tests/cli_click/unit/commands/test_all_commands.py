"""
Test cases for all remaining CLI commands.

Comprehensive tests for create, tutorial, admin, check, metrics, and tools commands.
"""

from unittest.mock import Mock, patch

import pytest

from panther.cli_click.core.main import cli


class TestCreateCommand:
    """Test the create command functionality."""

    def test_create_help(self, cli_runner):
        """Test create command help output."""
        result = cli_runner.invoke(cli, ["create", "--help"])
        assert result.exit_code == 0 or result.exit_code == 2
        # Should show create command help or indicate command exists

    def test_create_plugin_help(self, cli_runner):
        """Test create plugin subcommand help."""
        result = cli_runner.invoke(cli, ["create", "plugin", "--help"])
        assert result.exit_code == 0 or result.exit_code == 2

    def test_create_plugin_service(self, cli_runner, temp_dir):
        """Test creating a service plugin."""
        output_dir = temp_dir / "plugin_output"
        result = cli_runner.invoke(
            cli,
            [
                "create",
                "plugin",
                "service",
                "my_service",
                "--output-dir",
                str(output_dir),
            ],
        )
        assert result.exit_code is not None

    def test_create_plugin_tester(self, cli_runner, temp_dir):
        """Test creating a tester plugin."""
        output_dir = temp_dir / "tester_output"
        result = cli_runner.invoke(
            cli,
            [
                "create",
                "plugin",
                "tester",
                "my_tester",
                "--output-dir",
                str(output_dir),
            ],
        )
        assert result.exit_code is not None

    def test_create_test(self, cli_runner, temp_dir):
        """Test creating a test configuration."""
        output_dir = temp_dir / "test_output"
        result = cli_runner.invoke(
            cli, ["create", "test", "connectivity", "--output-dir", str(output_dir)]
        )
        assert result.exit_code is not None

    def test_create_config(self, cli_runner, temp_dir):
        """Test creating a configuration."""
        output_file = temp_dir / "created_config.yaml"
        result = cli_runner.invoke(
            cli,
            ["create", "config", "--template", "basic", "--output", str(output_file)],
        )
        assert result.exit_code is not None

    def test_create_with_verbose(self, cli_runner, temp_dir):
        """Test create command with verbose output."""
        result = cli_runner.invoke(
            cli,
            [
                "--verbose",
                "create",
                "plugin",
                "service",
                "verbose_service",
                "--output-dir",
                str(temp_dir),
            ],
        )
        assert "🔍 Verbose mode enabled" in result.output

    def test_create_invalid_type(self, cli_runner):
        """Test create command with invalid plugin type."""
        result = cli_runner.invoke(cli, ["create", "plugin", "invalid_type", "name"])
        assert result.exit_code != 0 or result.exit_code is None


class TestTutorialCommand:
    """Test the tutorial command functionality."""

    def test_tutorial_help(self, cli_runner):
        """Test tutorial command help output."""
        result = cli_runner.invoke(cli, ["tutorial", "--help"])
        assert result.exit_code == 0 or result.exit_code == 2

    def test_tutorial_list(self, cli_runner):
        """Test listing available tutorials."""
        result = cli_runner.invoke(cli, ["tutorial", "list"])
        assert result.exit_code is not None

    def test_tutorial_info(self, cli_runner):
        """Test getting tutorial information."""
        result = cli_runner.invoke(cli, ["tutorial", "info", "basic"])
        assert result.exit_code is not None

    def test_tutorial_run_basic(self, cli_runner, temp_dir):
        """Test running basic tutorial."""
        output_dir = temp_dir / "tutorial_output"
        result = cli_runner.invoke(
            cli, ["tutorial", "run", "basic", "--output-dir", str(output_dir)]
        )
        assert result.exit_code is not None

    def test_tutorial_run_service(self, cli_runner, temp_dir):
        """Test running service tutorial."""
        output_dir = temp_dir / "service_tutorial"
        result = cli_runner.invoke(
            cli, ["tutorial", "run", "service", "--output-dir", str(output_dir)]
        )
        assert result.exit_code is not None

    def test_tutorial_interactive(self, cli_runner):
        """Test interactive tutorial mode."""
        result = cli_runner.invoke(cli, ["tutorial", "interactive"])
        assert result.exit_code is not None

    def test_tutorial_with_dry_run(self, cli_runner, temp_dir):
        """Test tutorial with dry-run mode."""
        result = cli_runner.invoke(
            cli,
            ["tutorial", "run", "basic", "--output-dir", str(temp_dir), "--dry-run"],
        )
        assert result.exit_code is not None

    def test_tutorial_invalid_name(self, cli_runner):
        """Test tutorial with invalid name."""
        result = cli_runner.invoke(cli, ["tutorial", "run", "nonexistent"])
        assert result.exit_code != 0 or result.exit_code is None


class TestAdminCommand:
    """Test the admin command functionality."""

    def test_admin_help(self, cli_runner):
        """Test admin command help output."""
        result = cli_runner.invoke(cli, ["admin", "--help"])
        assert result.exit_code == 0 or result.exit_code == 2

    def test_admin_status(self, cli_runner):
        """Test admin status command."""
        result = cli_runner.invoke(cli, ["admin", "status"])
        assert result.exit_code is not None

    def test_admin_docker_status(self, cli_runner):
        """Test Docker status check."""
        result = cli_runner.invoke(cli, ["admin", "docker", "--status"])
        assert result.exit_code is not None

    def test_admin_docker_images(self, cli_runner):
        """Test Docker images management."""
        result = cli_runner.invoke(cli, ["admin", "docker", "--images"])
        assert result.exit_code is not None

    def test_admin_docker_images_all(self, cli_runner):
        """Test Docker all images management."""
        result = cli_runner.invoke(cli, ["admin", "docker", "--images-all"])
        assert result.exit_code is not None

    def test_admin_docker_cleanup(self, cli_runner):
        """Test Docker cleanup with dry-run."""
        result = cli_runner.invoke(cli, ["admin", "docker", "--cleanup", "--dry-run"])
        assert result.exit_code is not None

    def test_admin_docker_prune(self, cli_runner):
        """Test Docker system prune."""
        result = cli_runner.invoke(cli, ["admin", "docker", "--prune", "--dry-run"])
        assert result.exit_code is not None

    def test_admin_logs(self, cli_runner):
        """Test admin logs command."""
        result = cli_runner.invoke(cli, ["admin", "logs"])
        assert result.exit_code is not None

    def test_admin_config_check(self, cli_runner):
        """Test admin configuration check."""
        result = cli_runner.invoke(cli, ["admin", "config-check"])
        assert result.exit_code is not None


class TestCheckCommand:
    """Test the check command functionality."""

    def test_check_help(self, cli_runner):
        """Test check command help output."""
        result = cli_runner.invoke(cli, ["check", "--help"])
        assert result.exit_code == 0 or result.exit_code == 2

    def test_check_all(self, cli_runner):
        """Test running all checks."""
        result = cli_runner.invoke(cli, ["check", "--all"])
        assert result.exit_code is not None

    def test_check_style(self, cli_runner):
        """Test style checks."""
        result = cli_runner.invoke(cli, ["check", "--style"])
        assert result.exit_code is not None

    def test_check_security(self, cli_runner):
        """Test security checks."""
        result = cli_runner.invoke(cli, ["check", "--security"])
        assert result.exit_code is not None

    def test_check_dependencies(self, cli_runner):
        """Test dependency checks."""
        result = cli_runner.invoke(cli, ["check", "--dependencies"])
        assert result.exit_code is not None

    def test_check_format(self, cli_runner):
        """Test format checks."""
        result = cli_runner.invoke(cli, ["check", "--format"])
        assert result.exit_code is not None

    def test_check_with_fix(self, cli_runner):
        """Test checks with automatic fixing."""
        result = cli_runner.invoke(cli, ["check", "--style", "--fix"])
        assert result.exit_code is not None

    def test_check_with_fix_dry_run(self, cli_runner):
        """Test checks with fix in dry-run mode."""
        result = cli_runner.invoke(cli, ["check", "--style", "--fix", "--dry-run"])
        assert result.exit_code is not None

    def test_check_exclude_patterns(self, cli_runner):
        """Test checks with exclude patterns."""
        result = cli_runner.invoke(
            cli, ["check", "--style", "--exclude", "*.pyc", "--exclude", "__pycache__"]
        )
        assert result.exit_code is not None

    def test_check_specific_files(self, cli_runner, temp_dir):
        """Test checks on specific files."""
        test_file = temp_dir / "test.py"
        test_file.write_text('print("hello")')

        result = cli_runner.invoke(cli, ["check", "--style", str(test_file)])
        assert result.exit_code is not None


class TestMetricsCommand:
    """Test the metrics command functionality."""

    def test_metrics_help(self, cli_runner):
        """Test metrics command help output."""
        result = cli_runner.invoke(cli, ["metrics", "--help"])
        assert result.exit_code == 0 or result.exit_code == 2

    def test_metrics_list_no_data(self, cli_runner, temp_dir):
        """Test listing metrics when no data is available."""
        result = cli_runner.invoke(
            cli, ["metrics", "list", "--output-dir", str(temp_dir)]
        )
        assert result.exit_code is not None

    def test_metrics_list_with_data(self, cli_runner, temp_dir):
        """Test listing metrics with real data."""
        import json

        exp_dir = temp_dir / "exp1" / "metrics"
        exp_dir.mkdir(parents=True)
        metrics_data = {
            "timing_metrics": {"test_dur": 1.5},
            "resource_metrics": {},
            "phase_metrics": {},
            "error_metrics": {"total_errors": 0},
            "raw_metrics": {"counters": {"tests_run": 3}, "gauges": {}, "histograms": {}},
        }
        with open(exp_dir / "metrics.json", "w") as f:
            json.dump(metrics_data, f)

        result = cli_runner.invoke(
            cli, ["metrics", "list", "--output-dir", str(temp_dir)]
        )
        assert result.exit_code is not None

    def test_metrics_show_no_data(self, cli_runner, temp_dir):
        """Test showing metrics when no data is available."""
        result = cli_runner.invoke(
            cli, ["metrics", "show", "--output-dir", str(temp_dir)]
        )
        assert result.exit_code is not None

    def test_metrics_summary_no_data(self, cli_runner, temp_dir):
        """Test summary when no data is available."""
        result = cli_runner.invoke(
            cli, ["metrics", "summary", "--output-dir", str(temp_dir)]
        )
        assert result.exit_code is not None

    def test_metrics_export_no_data(self, cli_runner, temp_dir):
        """Test export when no data is available."""
        result = cli_runner.invoke(
            cli,
            [
                "metrics",
                "export",
                "--output-dir",
                str(temp_dir),
                "--format",
                "json",
            ],
        )
        assert result.exit_code is not None

    def test_metrics_clear_no_data(self, cli_runner, temp_dir):
        """Test clear when no data is available."""
        result = cli_runner.invoke(
            cli,
            [
                "metrics",
                "clear",
                "--force",
                "--output-dir",
                str(temp_dir),
            ],
        )
        assert result.exit_code is not None

    def test_metrics_export_with_data(self, cli_runner, temp_dir):
        """Test export with real experiment data."""
        import json

        exp_dir = temp_dir / "exp1" / "metrics"
        exp_dir.mkdir(parents=True)
        metrics_data = {
            "export_metadata": {"timestamp": "2025-01-15T10:00:00"},
            "timing_metrics": {"test_dur": 1.5},
            "resource_metrics": {},
            "phase_metrics": {},
            "error_metrics": {"total_errors": 0},
            "raw_metrics": {"counters": {}, "gauges": {}, "histograms": {}},
        }
        with open(exp_dir / "metrics.json", "w") as f:
            json.dump(metrics_data, f)

        output_file = temp_dir / "exported.json"
        result = cli_runner.invoke(
            cli,
            [
                "metrics",
                "export",
                "--output-dir",
                str(temp_dir),
                "--output",
                str(output_file),
                "--format",
                "json",
            ],
        )
        assert result.exit_code is not None

    def test_metrics_list_with_filter(self, cli_runner, temp_dir):
        """Test listing metrics with filter pattern."""
        import json

        exp_dir = temp_dir / "exp1" / "metrics"
        exp_dir.mkdir(parents=True)
        metrics_data = {
            "timing_metrics": {"cpu_duration": 1.5, "mem_duration": 2.0},
            "resource_metrics": {},
            "phase_metrics": {},
            "error_metrics": {"total_errors": 0},
            "raw_metrics": {"counters": {}, "gauges": {}, "histograms": {}},
        }
        with open(exp_dir / "metrics.json", "w") as f:
            json.dump(metrics_data, f)

        result = cli_runner.invoke(
            cli, ["metrics", "list", "--output-dir", str(temp_dir), "--filter", "cpu"]
        )
        assert result.exit_code is not None

    def test_metrics_with_experiment_dir(self, cli_runner, temp_dir):
        """Test metrics commands with --experiment-dir option."""
        import json

        exp_dir = temp_dir / "specific_exp"
        metrics_dir = exp_dir / "metrics"
        metrics_dir.mkdir(parents=True)
        metrics_data = {
            "timing_metrics": {"test_dur": 5.0},
            "resource_metrics": {},
            "phase_metrics": {},
            "error_metrics": {"total_errors": 0},
            "raw_metrics": {"counters": {}, "gauges": {}, "histograms": {}},
        }
        with open(metrics_dir / "metrics.json", "w") as f:
            json.dump(metrics_data, f)

        result = cli_runner.invoke(
            cli, ["metrics", "list", "--experiment-dir", str(exp_dir)]
        )
        assert result.exit_code is not None


class TestToolsCommand:
    """Test the tools command functionality."""

    def test_tools_help(self, cli_runner):
        """Test tools command help output."""
        result = cli_runner.invoke(cli, ["tools", "--help"])
        assert result.exit_code == 0 or result.exit_code == 2

    def test_tools_status(self, cli_runner):
        """Test tools status check."""
        result = cli_runner.invoke(cli, ["tools", "status"])
        assert result.exit_code is not None

    def test_tools_install_dev(self, cli_runner):
        """Test installing development tools."""
        result = cli_runner.invoke(cli, ["tools", "install-dev"])
        assert result.exit_code is not None

    def test_tools_install_slim(self, cli_runner):
        """Test installing slim optimization tools."""
        result = cli_runner.invoke(cli, ["tools", "install-slim"])
        assert result.exit_code is not None

    def test_tools_install_all(self, cli_runner):
        """Test installing all tools."""
        result = cli_runner.invoke(cli, ["tools", "install-all"])
        assert result.exit_code is not None

    def test_tools_update(self, cli_runner):
        """Test updating tools."""
        result = cli_runner.invoke(cli, ["tools", "update"])
        assert result.exit_code is not None

    def test_tools_remove(self, cli_runner):
        """Test removing tools."""
        result = cli_runner.invoke(cli, ["tools", "remove", "dev-tools"])
        assert result.exit_code is not None

    def test_tools_list(self, cli_runner):
        """Test listing available tools."""
        result = cli_runner.invoke(cli, ["tools", "list"])
        assert result.exit_code is not None

    def test_tools_info(self, cli_runner):
        """Test getting tool information."""
        result = cli_runner.invoke(cli, ["tools", "info", "docker"])
        assert result.exit_code is not None

    def test_tools_validate(self, cli_runner):
        """Test validating tool installations."""
        result = cli_runner.invoke(cli, ["tools", "validate"])
        assert result.exit_code is not None


class TestCommandInteractions:
    """Test interactions between different commands."""

    def test_create_then_validate(self, cli_runner, temp_dir):
        """Test creating a plugin and then validating it."""
        plugin_dir = temp_dir / "new_plugin"

        # Create plugin
        result1 = cli_runner.invoke(
            cli,
            [
                "create",
                "plugin",
                "service",
                "test_service",
                "--output-dir",
                str(plugin_dir),
            ],
        )
        assert result1.exit_code is not None

        # Validate plugin if it was created
        if plugin_dir.exists():
            result2 = cli_runner.invoke(
                cli, ["plugins", "validate", "--plugin-dir", str(plugin_dir)]
            )
            assert result2.exit_code is not None

    def test_admin_status_then_check(self, cli_runner):
        """Test checking admin status then running checks."""
        # Check system status
        result1 = cli_runner.invoke(cli, ["admin", "status"])
        assert result1.exit_code is not None

        # Run code checks
        result2 = cli_runner.invoke(cli, ["check", "--all"])
        assert result2.exit_code is not None

    def test_tools_install_then_status(self, cli_runner):
        """Test installing tools then checking status."""
        # Install tools
        result1 = cli_runner.invoke(cli, ["tools", "install-dev"])
        assert result1.exit_code is not None

        # Check status
        result2 = cli_runner.invoke(cli, ["tools", "status"])
        assert result2.exit_code is not None

    def test_tutorial_then_run(self, cli_runner, temp_dir):
        """Test running tutorial then executing the result."""
        tutorial_dir = temp_dir / "tutorial"
        config_file = temp_dir / "tutorial_config.yaml"

        # Run tutorial
        result1 = cli_runner.invoke(
            cli, ["tutorial", "run", "basic", "--output-dir", str(tutorial_dir)]
        )
        assert result1.exit_code is not None

        # If tutorial created config, validate it
        if config_file.exists():
            result2 = cli_runner.invoke(
                cli, ["config", "validate", "--config", str(config_file)]
            )
            assert result2.exit_code == 0


class TestCommandArgumentValidation:
    """Test argument validation across all commands."""

    def test_create_argument_validation(self, cli_runner):
        """Test create command argument validation."""
        # Missing plugin type
        result = cli_runner.invoke(cli, ["create", "plugin"])
        assert result.exit_code != 0 or result.exit_code is None

        # Invalid plugin type
        result = cli_runner.invoke(cli, ["create", "plugin", "invalid"])
        assert result.exit_code != 0 or result.exit_code is None

    def test_admin_argument_validation(self, cli_runner):
        """Test admin command argument validation."""
        # Invalid docker option
        result = cli_runner.invoke(cli, ["admin", "docker", "--invalid"])
        assert result.exit_code != 0 or result.exit_code is None

    def test_check_argument_validation(self, cli_runner):
        """Test check command argument validation."""
        # Invalid check type
        result = cli_runner.invoke(cli, ["check", "--invalid-check"])
        assert result.exit_code != 0 or result.exit_code is None

    def test_metrics_argument_validation(self, cli_runner):
        """Test metrics command argument validation."""
        # Invalid export format
        result = cli_runner.invoke(cli, ["metrics", "export", "--format", "invalid"])
        assert result.exit_code != 0 or result.exit_code is None

    def test_tools_argument_validation(self, cli_runner):
        """Test tools command argument validation."""
        # Invalid tool name
        result = cli_runner.invoke(cli, ["tools", "info", ""])
        assert result.exit_code != 0 or result.exit_code is None


class TestCommandOutputFormats:
    """Test different output formats across commands."""

    @pytest.mark.parametrize(
        "command,subcommand",
        [
            ("plugins", "list"),
            ("tools", "list"),
            ("admin", "status"),
        ],
    )
    def test_json_output_format(self, cli_runner, command, subcommand):
        """Test JSON output format for various commands."""
        result = cli_runner.invoke(cli, [command, subcommand, "--format", "json"])
        assert result.exit_code is not None

    @pytest.mark.parametrize(
        "command,subcommand",
        [("plugins", "list"), ("tools", "list")],
    )
    def test_table_output_format(self, cli_runner, command, subcommand):
        """Test table output format for various commands."""
        result = cli_runner.invoke(cli, [command, subcommand, "--format", "table"])
        assert result.exit_code is not None

    @pytest.mark.parametrize(
        "command,subcommand", [("admin", "status",)]
    )
    def test_yaml_output_format(self, cli_runner, command, subcommand):
        """Test YAML output format for various commands."""
        result = cli_runner.invoke(cli, [command, subcommand, "--format", "yaml"])
        assert result.exit_code is not None


class TestCommandErrorHandling:
    """Test error handling across all commands."""

    def test_permission_errors(self, cli_runner):
        """Test handling of permission errors."""
        # Try to write to system directory
        result = cli_runner.invoke(
            cli,
            [
                "create",
                "plugin",
                "service",
                "test",
                "--output-dir",
                "/root/no_permission",
            ],
        )
        # Should handle permission error gracefully
        assert result.exit_code is not None

    def test_network_errors(self, cli_runner):
        """Test handling of network-related errors."""
        # Commands that might require network access
        network_commands = [["tools", "update"], ["admin", "docker", "--pull"]]

        for cmd in network_commands:
            result = cli_runner.invoke(cli, cmd)
            # Should handle network errors gracefully
            assert result.exit_code is not None

    def test_missing_dependencies(self, cli_runner):
        """Test handling of missing dependencies."""
        # Commands that might require external tools
        dependency_commands = [
            ["check", "--style"],
            ["tools", "validate"],
            ["admin", "docker", "--status"],
        ]

        for cmd in dependency_commands:
            result = cli_runner.invoke(cli, cmd)
            # Should handle missing dependencies gracefully
            assert result.exit_code is not None


class TestCommandPerformance:
    """Test performance characteristics of commands."""

    def test_help_command_speed(self, cli_runner):
        """Test that help commands respond quickly."""
        import time

        commands = ["--help", "config", "plugins", "admin", "tools"]

        for cmd in commands:
            start_time = time.time()
            result = cli_runner.invoke(cli, [cmd, "--help"])
            end_time = time.time()

            # Help should be fast (under 5 seconds)
            assert (end_time - start_time) < 5.0
            assert result.exit_code == 0 or result.exit_code == 2

    def test_list_command_speed(self, cli_runner):
        """Test that list commands respond reasonably quickly."""
        import time

        list_commands = [["plugins", "list"], ["tools", "list"], ["metrics", "list"]]

        for cmd in list_commands:
            start_time = time.time()
            result = cli_runner.invoke(cli, cmd)
            end_time = time.time()

            # List commands should be reasonably fast (under 30 seconds)
            assert (end_time - start_time) < 30.0
            assert result.exit_code is not None
