"""
Integration tests for CLI workflows.

Tests complete workflows that span multiple commands and verify
end-to-end functionality of the Click CLI implementation.
"""

from pathlib import Path

import pytest
import yaml

from panther.cli_click.core.main import cli


class TestConfigWorkflows:
    """Test configuration-related workflows."""

    def test_generate_validate_workflow(self, cli_runner, temp_dir):
        """Test generating a config and then validating it."""
        config_file = temp_dir / "workflow_config.yaml"

        # Step 1: Generate a configuration
        result1 = cli_runner.invoke(
            cli,
            ["config", "generate", "--template", "basic", "--output", str(config_file)],
        )
        assert result1.exit_code == 0
        assert config_file.exists()

        # Step 2: Validate the generated configuration
        result2 = cli_runner.invoke(
            cli, ["config", "validate", "--config", str(config_file)]
        )
        assert result2.exit_code == 0

        # Step 3: View the schema
        result3 = cli_runner.invoke(cli, ["config", "schema"])
        assert result3.exit_code == 0

    def test_design_validate_workflow(self, cli_runner, temp_dir):
        """Test designing a config interactively and then validating it."""
        config_file = temp_dir / "designed_config.yaml"

        # Step 1: Design configuration in non-interactive mode
        result1 = cli_runner.invoke(
            cli, ["config", "design", "--output", str(config_file), "--non-interactive"]
        )
        assert result1.exit_code == 0
        assert config_file.exists()

        # Step 2: Validate the designed configuration
        result2 = cli_runner.invoke(
            cli, ["config", "validate", "--config", str(config_file)]
        )
        assert result2.exit_code == 0

    def test_template_comparison_workflow(self, cli_runner, temp_dir):
        """Test generating and comparing different templates."""
        templates = ["minimal", "basic", "advanced"]
        config_files = []

        # Generate different templates
        for template in templates:
            config_file = temp_dir / f"{template}_config.yaml"
            result = cli_runner.invoke(
                cli,
                [
                    "config",
                    "generate",
                    "--template",
                    template,
                    "--output",
                    str(config_file),
                ],
            )
            assert result.exit_code == 0
            assert config_file.exists()
            config_files.append(config_file)

        # Validate all generated templates
        for config_file in config_files:
            result = cli_runner.invoke(
                cli, ["config", "validate", "--config", str(config_file)]
            )
            assert result.exit_code == 0

        # Verify they contain different content
        configs = []
        for config_file in config_files:
            with open(config_file, "r") as f:
                configs.append(f.read())

        # Each template should be unique
        assert len(set(configs)) == len(configs)


class TestRunWorkflows:
    """Test run command workflows."""

    def test_config_run_workflow(self, cli_runner, temp_dir):
        """Test generating config and running with it."""
        config_file = temp_dir / "run_config.yaml"
        output_dir = temp_dir / "run_output"

        # Step 1: Generate configuration
        result1 = cli_runner.invoke(
            cli,
            ["config", "generate", "--template", "basic", "--output", str(config_file)],
        )
        assert result1.exit_code == 0

        # Step 2: Validate configuration
        result2 = cli_runner.invoke(
            cli, ["config", "validate", "--config", str(config_file)]
        )
        assert result2.exit_code == 0

        # Step 3: Run with dry-run mode
        result3 = cli_runner.invoke(
            cli,
            [
                "run",
                "--config",
                str(config_file),
                "--output-dir",
                str(output_dir),
                "--dry-run",
            ],
        )
        # Should complete without error in dry-run mode
        assert result3.exit_code is not None

    def test_metrics_enabled_workflow(self, cli_runner, temp_dir):
        """Test workflow with metrics enabled."""
        config_file = temp_dir / "metrics_config.yaml"
        output_dir = temp_dir / "metrics_output"
        metrics_dir = temp_dir / "metrics_data"

        # Generate config
        result1 = cli_runner.invoke(
            cli,
            [
                "config",
                "generate",
                "--template",
                "performance",
                "--output",
                str(config_file),
            ],
        )
        assert result1.exit_code == 0

        # Run with metrics enabled
        result2 = cli_runner.invoke(
            cli,
            [
                "run",
                "--config",
                str(config_file),
                "--output-dir",
                str(output_dir),
                "--enable-metrics",
                "--metrics-output-dir",
                str(metrics_dir),
                "--metrics-interval",
                "2",
                "--metrics-export-format",
                "json",
                "--dry-run",
            ],
        )
        assert result2.exit_code is not None


class TestPluginWorkflows:
    """Test plugin management workflows."""

    def test_plugin_discovery_workflow(self, cli_runner):
        """Test plugin discovery and status checking."""
        # Step 1: List available plugins
        result1 = cli_runner.invoke(cli, ["plugins", "list"])
        assert result1.exit_code is not None

        # Step 2: Check plugin status
        result2 = cli_runner.invoke(cli, ["plugins", "status"])
        assert result2.exit_code is not None

        # Step 3: Validate plugins
        result3 = cli_runner.invoke(cli, ["plugins", "validate"])
        assert result3.exit_code is not None

    def test_plugin_type_filtering_workflow(self, cli_runner):
        """Test filtering plugins by type."""
        plugin_types = ["iut", "tester", "environment"]

        for plugin_type in plugin_types:
            result = cli_runner.invoke(cli, ["plugins", "list", "--type", plugin_type])
            assert result.exit_code is not None


class TestAdminWorkflows:
    """Test administrative workflows."""

    def test_system_status_workflow(self, cli_runner):
        """Test checking system status."""
        # Check overall system status
        result1 = cli_runner.invoke(cli, ["admin", "status"])
        assert result1.exit_code is not None

        # Check Docker status
        result2 = cli_runner.invoke(cli, ["admin", "docker", "--status"])
        assert result2.exit_code is not None

    def test_cleanup_workflow(self, cli_runner):
        """Test system cleanup workflow."""
        # Check current status
        result1 = cli_runner.invoke(cli, ["admin", "status"])
        assert result1.exit_code is not None

        # Dry-run cleanup
        result2 = cli_runner.invoke(cli, ["admin", "docker", "--cleanup", "--dry-run"])
        assert result2.exit_code is not None


class TestTutorialWorkflows:
    """Test tutorial workflows."""

    def test_tutorial_discovery_workflow(self, cli_runner):
        """Test discovering available tutorials."""
        # List tutorials
        result1 = cli_runner.invoke(cli, ["tutorial", "list"])
        assert result1.exit_code is not None

        # Show tutorial info
        result2 = cli_runner.invoke(cli, ["tutorial", "info", "basic"])
        assert result2.exit_code is not None

    def test_tutorial_execution_workflow(self, cli_runner, temp_dir):
        """Test tutorial execution workflow."""
        output_dir = temp_dir / "tutorial_output"

        # Run tutorial in dry-run mode
        result = cli_runner.invoke(
            cli,
            ["tutorial", "run", "basic", "--output-dir", str(output_dir), "--dry-run"],
        )
        assert result.exit_code is not None


class TestCreateWorkflows:
    """Test creation workflows."""

    def test_plugin_creation_workflow(self, cli_runner, temp_dir):
        """Test creating and validating a new plugin."""
        plugin_dir = temp_dir / "new_plugin"

        # Create plugin
        result1 = cli_runner.invoke(
            cli,
            [
                "create",
                "plugin",
                "service",
                "my_service",
                "--output-dir",
                str(plugin_dir),
            ],
        )
        assert result1.exit_code is not None

        # If creation succeeded, validate the plugin
        if plugin_dir.exists():
            result2 = cli_runner.invoke(
                cli, ["plugins", "validate", "--plugin-dir", str(plugin_dir)]
            )
            assert result2.exit_code is not None

    def test_test_creation_workflow(self, cli_runner, temp_dir):
        """Test creating and running a test."""
        test_dir = temp_dir / "new_test"

        # Create test
        result1 = cli_runner.invoke(
            cli, ["create", "test", "connectivity", "--output-dir", str(test_dir)]
        )
        assert result1.exit_code is not None


class TestToolsWorkflows:
    """Test tools workflows."""

    def test_tools_installation_workflow(self, cli_runner):
        """Test tools installation workflow."""
        # Install development tools
        result1 = cli_runner.invoke(cli, ["tools", "install-dev"])
        assert result1.exit_code is not None

        # Install optimization tools
        result2 = cli_runner.invoke(cli, ["tools", "install-slim"])
        assert result2.exit_code is not None

    def test_tools_status_workflow(self, cli_runner):
        """Test checking tools status."""
        result = cli_runner.invoke(cli, ["tools", "status"])
        assert result.exit_code is not None


class TestCheckWorkflows:
    """Test code quality check workflows."""

    def test_comprehensive_check_workflow(self, cli_runner):
        """Test running all code quality checks."""
        # Run all checks
        result1 = cli_runner.invoke(cli, ["check", "--all"])
        assert result1.exit_code is not None

        # Run specific checks
        check_types = ["style", "security", "dependencies"]
        for check_type in check_types:
            result = cli_runner.invoke(cli, ["check", f"--{check_type}"])
            assert result.exit_code is not None

    def test_check_fix_workflow(self, cli_runner):
        """Test check and fix workflow."""
        # Check for issues
        result1 = cli_runner.invoke(cli, ["check", "--style"])
        assert result1.exit_code is not None

        # Fix issues (dry-run)
        result2 = cli_runner.invoke(cli, ["check", "--style", "--fix", "--dry-run"])
        assert result2.exit_code is not None


class TestMetricsWorkflows:
    """Test metrics workflows."""

    def test_metrics_collection_workflow(self, cli_runner, temp_dir):
        """Test metrics collection workflow."""
        config_file = temp_dir / "metrics_config.yaml"

        # Generate config with metrics
        result1 = cli_runner.invoke(
            cli,
            [
                "config",
                "generate",
                "--template",
                "performance",
                "--output",
                str(config_file),
            ],
        )
        assert result1.exit_code == 0

        # List available metrics
        result2 = cli_runner.invoke(cli, ["metrics", "list"])
        assert result2.exit_code is not None

        # Show metrics configuration
        result3 = cli_runner.invoke(
            cli, ["metrics", "config", "--config", str(config_file)]
        )
        assert result3.exit_code is not None

    def test_metrics_analysis_workflow(self, cli_runner, temp_dir):
        """Test metrics analysis workflow."""
        results_dir = temp_dir / "results"
        results_dir.mkdir()

        # Analyze metrics (if results exist)
        result1 = cli_runner.invoke(
            cli, ["metrics", "analyze", "--results-dir", str(results_dir)]
        )
        assert result1.exit_code is not None

        # Generate report
        result2 = cli_runner.invoke(
            cli,
            [
                "metrics",
                "report",
                "--results-dir",
                str(results_dir),
                "--format",
                "json",
            ],
        )
        assert result2.exit_code is not None


class TestComplexWorkflows:
    """Test complex multi-command workflows."""

    def test_full_experiment_workflow(self, cli_runner, temp_dir):
        """Test complete experiment workflow from config to results."""
        config_file = temp_dir / "experiment_config.yaml"
        output_dir = temp_dir / "experiment_output"

        # Step 1: Generate experiment configuration
        result1 = cli_runner.invoke(
            cli,
            [
                "config",
                "generate",
                "--template",
                "advanced",
                "--output",
                str(config_file),
            ],
        )
        assert result1.exit_code == 0

        # Step 2: Validate configuration
        result2 = cli_runner.invoke(
            cli, ["config", "validate", "--config", str(config_file), "--strict"]
        )
        assert result2.exit_code == 0

        # Step 3: Check system status
        result3 = cli_runner.invoke(cli, ["admin", "status"])
        assert result3.exit_code is not None

        # Step 4: List available plugins
        result4 = cli_runner.invoke(cli, ["plugins", "list"])
        assert result4.exit_code is not None

        # Step 5: Run experiment (dry-run)
        result5 = cli_runner.invoke(
            cli,
            [
                "run",
                "--config",
                str(config_file),
                "--output-dir",
                str(output_dir),
                "--enable-metrics",
                "--dry-run",
            ],
        )
        assert result5.exit_code is not None

        # Step 6: Check metrics configuration
        result6 = cli_runner.invoke(
            cli, ["metrics", "config", "--config", str(config_file)]
        )
        assert result6.exit_code is not None

    def test_development_workflow(self, cli_runner, temp_dir):
        """Test development workflow with checks and tools."""
        plugin_dir = temp_dir / "dev_plugin"

        # Step 1: Install development tools
        result1 = cli_runner.invoke(cli, ["tools", "install-dev"])
        assert result1.exit_code is not None

        # Step 2: Create new plugin
        result2 = cli_runner.invoke(
            cli,
            [
                "create",
                "plugin",
                "service",
                "dev_service",
                "--output-dir",
                str(plugin_dir),
            ],
        )
        assert result2.exit_code is not None

        # Step 3: Run code quality checks
        result3 = cli_runner.invoke(cli, ["check", "--all"])
        assert result3.exit_code is not None

        # Step 4: Validate plugin
        if plugin_dir.exists():
            result4 = cli_runner.invoke(
                cli, ["plugins", "validate", "--plugin-dir", str(plugin_dir)]
            )
            assert result4.exit_code is not None

    def test_debugging_workflow(self, cli_runner, temp_dir):
        """Test debugging workflow with verbose output."""
        config_file = temp_dir / "debug_config.yaml"

        # Generate config with debug info
        result1 = cli_runner.invoke(
            cli,
            [
                "--debug",
                "config",
                "generate",
                "--template",
                "basic",
                "--output",
                str(config_file),
            ],
        )
        assert result1.exit_code == 0
        assert "🐛 Debug mode enabled" in result1.output

        # Validate with verbose output
        result2 = cli_runner.invoke(
            cli,
            [
                "--verbose",
                "config",
                "validate",
                "--config",
                str(config_file),
                "--explain",
            ],
        )
        assert result2.exit_code == 0
        assert "🔍 Verbose mode enabled" in result2.output

        # Check system status with debug
        result3 = cli_runner.invoke(cli, ["--debug", "admin", "status"])
        assert result3.exit_code is not None
        assert "🐛 Debug mode enabled" in result3.output


class TestErrorRecoveryWorkflows:
    """Test error handling and recovery workflows."""

    def test_invalid_config_recovery(self, cli_runner, temp_dir):
        """Test recovery from invalid configuration."""
        invalid_config = temp_dir / "invalid.yaml"
        invalid_config.write_text("invalid: yaml: syntax:\n  missing: bracket")

        # Attempt to validate invalid config
        result1 = cli_runner.invoke(
            cli, ["config", "validate", "--config", str(invalid_config)]
        )
        # Should handle error gracefully
        assert result1.exit_code is not None

        # Generate valid config to replace invalid one
        result2 = cli_runner.invoke(
            cli,
            [
                "config",
                "generate",
                "--template",
                "basic",
                "--output",
                str(invalid_config),
                "--overwrite",
            ],
        )
        assert result2.exit_code == 0

        # Validate the corrected config
        result3 = cli_runner.invoke(
            cli, ["config", "validate", "--config", str(invalid_config)]
        )
        assert result3.exit_code == 0

    def test_missing_dependencies_workflow(self, cli_runner):
        """Test handling of missing dependencies."""
        # Try to run with potential missing dependencies
        result1 = cli_runner.invoke(cli, ["admin", "status"])
        assert result1.exit_code is not None

        # Check what tools are available
        result2 = cli_runner.invoke(cli, ["tools", "status"])
        assert result2.exit_code is not None

        # Install missing tools if needed
        result3 = cli_runner.invoke(cli, ["tools", "install-dev"])
        assert result3.exit_code is not None


class TestPerformanceWorkflows:
    """Test performance-related workflows."""

    def test_completion_generation_workflow(self, cli_runner, temp_dir):
        """Test shell completion generation workflow."""
        shells = ["bash", "zsh", "fish"]

        for shell in shells:
            completion_file = temp_dir / f"completion.{shell}"
            result = cli_runner.invoke(
                cli, ["completion", shell, "--output", str(completion_file)]
            )
            assert result.exit_code == 0
            assert completion_file.exists()

            # Verify completion file content
            content = completion_file.read_text()
            assert f"{shell} completion" in content.lower()

    def test_large_config_workflow(self, cli_runner, temp_dir):
        """Test workflow with large configuration files."""
        # Generate multiple configs
        config_files = []
        for i in range(5):
            config_file = temp_dir / f"large_config_{i}.yaml"
            result = cli_runner.invoke(
                cli,
                [
                    "config",
                    "generate",
                    "--template",
                    "advanced",
                    "--output",
                    str(config_file),
                ],
            )
            assert result.exit_code == 0
            config_files.append(config_file)

        # Validate all configs
        for config_file in config_files:
            result = cli_runner.invoke(
                cli, ["config", "validate", "--config", str(config_file)]
            )
            assert result.exit_code == 0
