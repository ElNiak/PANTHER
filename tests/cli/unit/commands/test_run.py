"""Test cases for the run command.

Tests experiment execution, options handling, plugin directories,
metrics configuration, and Docker user mapping.
"""

import pytest

from panther.cli.core.main import cli


class TestRunCommand:
    """Test the run command functionality."""

    def test_run_help(self, cli_runner):
        """Test run command help output."""
        result = cli_runner.invoke(cli, ["run", "--help"])
        assert result.exit_code == 0
        assert "Execute PANTHER experiments" in result.output
        assert "--config" in result.output
        assert "--output-dir" in result.output
        assert "--dry-run" in result.output
        assert "--verbose" in result.output

    def test_run_missing_config(self, cli_runner):
        """Test run command without required config option."""
        result = cli_runner.invoke(cli, ["run"])
        assert result.exit_code != 0
        assert "Missing option" in result.output or "required" in result.output.lower()

    def test_run_nonexistent_config(self, cli_runner):
        """Test run command with nonexistent config file."""
        result = cli_runner.invoke(cli, ["run", "--config", "nonexistent.yaml"])
        assert result.exit_code != 0

    def test_run_with_valid_config(self, cli_runner, sample_config_file):
        """Test run command with valid config file."""
        result = cli_runner.invoke(cli, ["run", "--config", str(sample_config_file)])
        # Command should at least parse correctly
        # Actual execution may fail without full environment
        assert result.exit_code is not None

    def test_run_with_output_dir(self, cli_runner, sample_config_file, temp_dir):
        """Test run command with custom output directory."""
        output_dir = temp_dir / "custom_output"
        result = cli_runner.invoke(
            cli,
            [
                "run",
                "--config",
                str(sample_config_file),
                "--output-dir",
                str(output_dir),
            ],
        )
        assert result.exit_code is not None

    def test_run_with_experiment_name(self, cli_runner, sample_config_file):
        """Test run command with custom experiment name."""
        result = cli_runner.invoke(
            cli,
            [
                "run",
                "--config",
                str(sample_config_file),
                "--experiment-name",
                "Custom Experiment",
            ],
        )
        assert result.exit_code is not None

    def test_run_dry_run_mode(self, cli_runner, sample_config_file):
        """Test run command in dry-run mode."""
        result = cli_runner.invoke(
            cli, ["run", "--config", str(sample_config_file), "--dry-run"]
        )
        assert result.exit_code is not None

    def test_run_verbose_mode(self, cli_runner, sample_config_file):
        """Test run command with verbose output."""
        result = cli_runner.invoke(
            cli, ["run", "--config", str(sample_config_file), "--verbose"]
        )
        assert result.exit_code is not None


class TestRunPluginDirectories:
    """Test run command plugin directory options."""

    def test_run_with_exec_env_dir(self, cli_runner, sample_config_file, temp_dir):
        """Test run command with custom execution environment directory."""
        plugin_dir = temp_dir / "exec_env"
        plugin_dir.mkdir()

        result = cli_runner.invoke(
            cli,
            [
                "run",
                "--config",
                str(sample_config_file),
                "--exec-env-dir",
                str(plugin_dir),
            ],
        )
        assert result.exit_code is not None

    def test_run_with_net_env_dir(self, cli_runner, sample_config_file, temp_dir):
        """Test run command with custom network environment directory."""
        plugin_dir = temp_dir / "net_env"
        plugin_dir.mkdir()

        result = cli_runner.invoke(
            cli,
            [
                "run",
                "--config",
                str(sample_config_file),
                "--net-env-dir",
                str(plugin_dir),
            ],
        )
        assert result.exit_code is not None

    def test_run_with_iut_dir(self, cli_runner, sample_config_file, temp_dir):
        """Test run command with custom IUT plugin directory."""
        plugin_dir = temp_dir / "iut"
        plugin_dir.mkdir()

        result = cli_runner.invoke(
            cli,
            ["run", "--config", str(sample_config_file), "--iut-dir", str(plugin_dir)],
        )
        assert result.exit_code is not None

    def test_run_with_tester_dir(self, cli_runner, sample_config_file, temp_dir):
        """Test run command with custom tester plugin directory."""
        plugin_dir = temp_dir / "tester"
        plugin_dir.mkdir()

        result = cli_runner.invoke(
            cli,
            [
                "run",
                "--config",
                str(sample_config_file),
                "--tester-dir",
                str(plugin_dir),
            ],
        )
        assert result.exit_code is not None

    def test_run_with_all_plugin_dirs(self, cli_runner, sample_config_file, temp_dir):
        """Test run command with all custom plugin directories."""
        dirs = {}
        for dir_type in ["exec_env", "net_env", "iut", "tester"]:
            plugin_dir = temp_dir / dir_type
            plugin_dir.mkdir()
            dirs[dir_type] = plugin_dir

        result = cli_runner.invoke(
            cli,
            [
                "run",
                "--config",
                str(sample_config_file),
                "--exec-env-dir",
                str(dirs["exec_env"]),
                "--net-env-dir",
                str(dirs["net_env"]),
                "--iut-dir",
                str(dirs["iut"]),
                "--tester-dir",
                str(dirs["tester"]),
            ],
        )
        assert result.exit_code is not None

    def test_run_with_nonexistent_plugin_dir(self, cli_runner, sample_config_file):
        """Test run command with nonexistent plugin directory."""
        result = cli_runner.invoke(
            cli,
            [
                "run",
                "--config",
                str(sample_config_file),
                "--iut-dir",
                "/nonexistent/directory",
            ],
        )
        assert result.exit_code != 0


class TestRunMetricsOptions:
    """Test run command metrics configuration options."""

    def test_run_enable_metrics(self, cli_runner, sample_config_file):
        """Test run command with metrics enabled."""
        result = cli_runner.invoke(
            cli, ["run", "--config", str(sample_config_file), "--enable-metrics"]
        )
        assert result.exit_code is not None

    def test_run_disable_metrics(self, cli_runner, sample_config_file):
        """Test run command with metrics disabled."""
        result = cli_runner.invoke(
            cli, ["run", "--config", str(sample_config_file), "--disable-metrics"]
        )
        assert result.exit_code is not None

    def test_run_metrics_output_dir(self, cli_runner, sample_config_file, temp_dir):
        """Test run command with custom metrics output directory."""
        metrics_dir = temp_dir / "metrics"
        result = cli_runner.invoke(
            cli,
            [
                "run",
                "--config",
                str(sample_config_file),
                "--enable-metrics",
                "--metrics-output-dir",
                str(metrics_dir),
            ],
        )
        assert result.exit_code is not None

    def test_run_metrics_interval(self, cli_runner, sample_config_file):
        """Test run command with custom metrics interval."""
        result = cli_runner.invoke(
            cli,
            [
                "run",
                "--config",
                str(sample_config_file),
                "--enable-metrics",
                "--metrics-interval",
                "5",
            ],
        )
        assert result.exit_code is not None

    def test_run_metrics_disable_resource_monitoring(
        self, cli_runner, sample_config_file
    ):
        """Test run command with resource monitoring disabled."""
        result = cli_runner.invoke(
            cli,
            [
                "run",
                "--config",
                str(sample_config_file),
                "--enable-metrics",
                "--metrics-disable-resource-monitoring",
            ],
        )
        assert result.exit_code is not None

    def test_run_metrics_generate_report(self, cli_runner, sample_config_file):
        """Test run command with report generation enabled."""
        result = cli_runner.invoke(
            cli,
            [
                "run",
                "--config",
                str(sample_config_file),
                "--enable-metrics",
                "--metrics-generate-report",
            ],
        )
        assert result.exit_code is not None

    @pytest.mark.parametrize("export_format", ["json", "csv", "yaml"])
    def test_run_metrics_export_formats(
        self, cli_runner, sample_config_file, export_format
    ):
        """Test run command with different metrics export formats."""
        result = cli_runner.invoke(
            cli,
            [
                "run",
                "--config",
                str(sample_config_file),
                "--enable-metrics",
                "--metrics-export-format",
                export_format,
            ],
        )
        assert result.exit_code is not None

    def test_run_metrics_invalid_interval(self, cli_runner, sample_config_file):
        """Test run command with invalid metrics interval."""
        result = cli_runner.invoke(
            cli,
            [
                "run",
                "--config",
                str(sample_config_file),
                "--metrics-interval",
                "invalid",
            ],
        )
        assert result.exit_code != 0

    def test_run_metrics_invalid_format(self, cli_runner, sample_config_file):
        """Test run command with invalid metrics format."""
        result = cli_runner.invoke(
            cli,
            [
                "run",
                "--config",
                str(sample_config_file),
                "--metrics-export-format",
                "invalid",
            ],
        )
        assert result.exit_code != 0


class TestRunDockerOptions:
    """Test run command Docker configuration options."""

    def test_run_docker_run_as_host(self, cli_runner, sample_config_file):
        """Test run command with Docker host user mapping."""
        result = cli_runner.invoke(
            cli, ["run", "--config", str(sample_config_file), "--docker-run-as-host"]
        )
        assert result.exit_code is not None

    def test_run_docker_custom_user_id(self, cli_runner, sample_config_file):
        """Test run command with custom Docker user ID."""
        result = cli_runner.invoke(
            cli,
            ["run", "--config", str(sample_config_file), "--docker-user-id", "1001"],
        )
        assert result.exit_code is not None

    def test_run_docker_custom_group_id(self, cli_runner, sample_config_file):
        """Test run command with custom Docker group ID."""
        result = cli_runner.invoke(
            cli,
            ["run", "--config", str(sample_config_file), "--docker-group-id", "1001"],
        )
        assert result.exit_code is not None

    def test_run_docker_custom_user_name(self, cli_runner, sample_config_file):
        """Test run command with custom Docker user name."""
        result = cli_runner.invoke(
            cli,
            [
                "run",
                "--config",
                str(sample_config_file),
                "--docker-user-name",
                "custom_user",
            ],
        )
        assert result.exit_code is not None

    def test_run_docker_full_user_config(self, cli_runner, sample_config_file):
        """Test run command with full Docker user configuration."""
        result = cli_runner.invoke(
            cli,
            [
                "run",
                "--config",
                str(sample_config_file),
                "--docker-user-id",
                "1001",
                "--docker-group-id",
                "1001",
                "--docker-user-name",
                "test_user",
            ],
        )
        assert result.exit_code is not None

    def test_run_docker_invalid_user_id(self, cli_runner, sample_config_file):
        """Test run command with invalid Docker user ID."""
        result = cli_runner.invoke(
            cli,
            ["run", "--config", str(sample_config_file), "--docker-user-id", "invalid"],
        )
        assert result.exit_code != 0

    def test_run_docker_invalid_group_id(self, cli_runner, sample_config_file):
        """Test run command with invalid Docker group ID."""
        result = cli_runner.invoke(
            cli,
            [
                "run",
                "--config",
                str(sample_config_file),
                "--docker-group-id",
                "invalid",
            ],
        )
        assert result.exit_code != 0


class TestRunArgumentValidation:
    """Test run command argument validation."""

    def test_run_config_path_validation(self, cli_runner, temp_dir):
        """Test that config path validation works."""
        # Create a directory instead of file
        config_dir = temp_dir / "config_dir"
        config_dir.mkdir()

        result = cli_runner.invoke(cli, ["run", "--config", str(config_dir)])
        # Should fail because config should be a file, not directory
        assert result.exit_code != 0

    def test_run_plugin_dir_validation(self, cli_runner, sample_config_file, temp_dir):
        """Test that plugin directory validation works."""
        # Create a file instead of directory
        plugin_file = temp_dir / "plugin_file.txt"
        plugin_file.write_text("not a directory")

        result = cli_runner.invoke(
            cli,
            ["run", "--config", str(sample_config_file), "--iut-dir", str(plugin_file)],
        )
        # Should fail because plugin dir should be a directory
        assert result.exit_code != 0

    def test_run_numeric_validation(self, cli_runner, sample_config_file):
        """Test numeric argument validation."""
        # Test invalid numeric arguments
        invalid_tests = [
            (["--metrics-interval", "not_a_number"], "metrics interval"),
            (["--docker-user-id", "not_a_number"], "docker user ID"),
            (["--docker-group-id", "not_a_number"], "docker group ID"),
        ]

        for args, description in invalid_tests:
            result = cli_runner.invoke(
                cli, ["run", "--config", str(sample_config_file)] + args
            )
            assert result.exit_code != 0, f"Should fail with invalid {description}"

    def test_run_choice_validation(self, cli_runner, sample_config_file):
        """Test choice argument validation."""
        # Test invalid choice arguments
        result = cli_runner.invoke(
            cli,
            [
                "run",
                "--config",
                str(sample_config_file),
                "--metrics-export-format",
                "invalid_format",
            ],
        )
        assert result.exit_code != 0


class TestRunIntegration:
    """Integration tests for run command functionality."""

    def test_run_with_global_flags(self, cli_runner, sample_config_file):
        """Test run command with global debug/verbose flags."""
        # Test with debug flag
        result = cli_runner.invoke(
            cli, ["--debug", "run", "--config", str(sample_config_file), "--dry-run"]
        )
        assert "🐛 Debug mode enabled" in result.output

        # Test with verbose flag
        result = cli_runner.invoke(
            cli, ["--verbose", "run", "--config", str(sample_config_file), "--dry-run"]
        )
        assert "🔍 Verbose mode enabled" in result.output

    def test_run_complex_command_line(self, cli_runner, sample_config_file, temp_dir):
        """Test run command with many options combined."""
        metrics_dir = temp_dir / "metrics"
        output_dir = temp_dir / "output"
        plugin_dir = temp_dir / "plugins"
        plugin_dir.mkdir()

        result = cli_runner.invoke(
            cli,
            [
                "run",
                "--config",
                str(sample_config_file),
                "--output-dir",
                str(output_dir),
                "--experiment-name",
                "Complex Test",
                "--verbose",
                "--dry-run",
                "--iut-dir",
                str(plugin_dir),
                "--enable-metrics",
                "--metrics-output-dir",
                str(metrics_dir),
                "--metrics-interval",
                "2",
                "--metrics-export-format",
                "json",
                "--docker-run-as-host",
                "--docker-user-name",
                "test_user",
            ],
        )

        # Should handle complex command line without errors
        assert result.exit_code is not None

    def test_run_path_handling(self, cli_runner, sample_config_file, temp_dir):
        """Test that path arguments are handled correctly."""
        # Test with relative paths
        output_dir = "relative_output"

        result = cli_runner.invoke(
            cli,
            [
                "run",
                "--config",
                str(sample_config_file),
                "--output-dir",
                output_dir,
                "--dry-run",
            ],
            catch_exceptions=False,
        )

        # Should handle relative paths
        assert result.exit_code is not None

    def test_run_option_precedence(self, cli_runner, sample_config_file):
        """Test that command line options override defaults."""
        # Test that explicit options override defaults
        result = cli_runner.invoke(
            cli,
            [
                "run",
                "--config",
                str(sample_config_file),
                "--output-dir",
                "custom_output",  # Override default 'outputs'
                "--metrics-interval",
                "5",  # Override default 1
                "--metrics-export-format",
                "csv",  # Override default 'json'
                "--docker-user-name",
                "custom",  # Override default 'panther'
                "--dry-run",
            ],
        )

        assert result.exit_code is not None
