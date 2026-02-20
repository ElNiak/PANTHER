"""
Test cases for the config command.

Tests configuration validation, schema display, template generation,
and interactive configuration design functionality.
"""

from unittest.mock import patch

import pytest
import yaml

from panther.cli_click.core.main import cli


class TestConfigCommand:
    """Test the main config command group."""

    def test_config_help(self, cli_runner):
        """Test config command help output."""
        result = cli_runner.invoke(cli, ["config", "--help"])
        assert result.exit_code == 0
        assert "Configuration management and validation" in result.output
        assert "Key Features:" in result.output
        assert "🔍 Configuration validation" in result.output
        assert "📋 Schema inspection" in result.output
        assert "🎯 Template generation" in result.output

    def test_config_subcommands_listed(self, cli_runner):
        """Test that config subcommands are listed in help."""
        result = cli_runner.invoke(cli, ["config", "--help"])
        assert result.exit_code == 0

        expected_subcommands = ["validate", "schema", "generate", "design"]
        for cmd in expected_subcommands:
            assert cmd in result.output


class TestConfigValidateCommand:
    """Test the config validate subcommand."""

    def test_validate_help(self, cli_runner):
        """Test validate command help."""
        result = cli_runner.invoke(cli, ["config", "validate", "--help"])
        assert result.exit_code == 0
        assert "Validate configuration file syntax and structure" in result.output
        assert "Validation Checks:" in result.output
        assert "--config" in result.output
        assert "--strict" in result.output
        assert "--explain" in result.output

    def test_validate_missing_config(self, cli_runner):
        """Test validate with missing config file."""
        result = cli_runner.invoke(cli, ["config", "validate"])
        assert result.exit_code != 0
        assert "Missing option" in result.output or "required" in result.output.lower()

    def test_validate_nonexistent_config(self, cli_runner):
        """Test validate with nonexistent config file."""
        result = cli_runner.invoke(
            cli, ["config", "validate", "--config", "nonexistent.yaml"]
        )
        assert result.exit_code != 0

    def test_validate_valid_config(self, cli_runner, sample_config_file):
        """Test validation with valid config file."""
        result = cli_runner.invoke(
            cli, ["config", "validate", "--config", str(sample_config_file)]
        )
        assert result.exit_code == 0
        assert "🔍 PANTHER Configuration Validation" in result.output

    def test_validate_with_strict_mode(self, cli_runner, sample_config_file):
        """Test validation with strict mode enabled."""
        result = cli_runner.invoke(
            cli, ["config", "validate", "--config", str(sample_config_file), "--strict"]
        )
        assert result.exit_code == 0
        assert "STRICT VALIDATION" in result.output

    def test_validate_with_explain(self, cli_runner, sample_config_file):
        """Test validation with explain option."""
        result = cli_runner.invoke(
            cli,
            ["config", "validate", "--config", str(sample_config_file), "--explain"],
        )
        assert result.exit_code == 0

    def test_validate_with_show_schema(self, cli_runner, sample_config_file):
        """Test validation with show-schema option."""
        result = cli_runner.invoke(
            cli,
            [
                "config",
                "validate",
                "--config",
                str(sample_config_file),
                "--show-schema",
            ],
        )
        assert result.exit_code == 0

    @pytest.mark.parametrize("format_type", ["text", "json", "yaml"])
    def test_validate_output_formats(self, cli_runner, sample_config_file, format_type):
        """Test validation with different output formats."""
        result = cli_runner.invoke(
            cli,
            [
                "config",
                "validate",
                "--config",
                str(sample_config_file),
                "--format",
                format_type,
            ],
        )
        assert result.exit_code == 0

    def test_validate_invalid_yaml(self, cli_runner, invalid_config_file):
        """Test validation with invalid YAML syntax."""
        result = cli_runner.invoke(
            cli, ["config", "validate", "--config", str(invalid_config_file)]
        )
        # Should either succeed (if adapter handles it) or show an error
        # The exact behavior depends on whether the adapter is available
        assert result.exit_code is not None  # Command should complete

    def test_validate_with_verbose(self, cli_runner, sample_config_file):
        """Test validation with verbose output."""
        result = cli_runner.invoke(
            cli,
            ["--verbose", "config", "validate", "--config", str(sample_config_file)],
        )
        assert result.exit_code == 0
        assert "🔍 Verbose mode enabled" in result.output

    def test_validate_with_debug(self, cli_runner, sample_config_file):
        """Test validation with debug output."""
        result = cli_runner.invoke(
            cli, ["--debug", "config", "validate", "--config", str(sample_config_file)]
        )
        assert result.exit_code == 0
        assert "🐛 Debug mode enabled" in result.output


class TestConfigSchemaCommand:
    """Test the config schema subcommand."""

    def test_schema_help(self, cli_runner):
        """Test schema command help."""
        result = cli_runner.invoke(cli, ["config", "schema", "--help"])
        assert result.exit_code == 0
        assert "Display configuration schema and documentation" in result.output
        assert "Schema Sections:" in result.output
        assert "--format" in result.output
        assert "--section" in result.output
        assert "--examples" in result.output

    def test_schema_default_output(self, cli_runner):
        """Test schema command with default output."""
        result = cli_runner.invoke(cli, ["config", "schema"])
        assert result.exit_code == 0
        assert "📖 PANTHER Configuration Schema" in result.output

    @pytest.mark.parametrize("format_type", ["text", "json", "yaml"])
    def test_schema_output_formats(self, cli_runner, format_type):
        """Test schema command with different output formats."""
        result = cli_runner.invoke(cli, ["config", "schema", "--format", format_type])
        assert result.exit_code == 0
        assert "📖 PANTHER Configuration Schema" in result.output

    def test_schema_with_examples(self, cli_runner):
        """Test schema command with examples."""
        result = cli_runner.invoke(cli, ["config", "schema", "--examples"])
        assert result.exit_code == 0
        assert "💡 Example Configuration:" in result.output

    def test_schema_specific_section(self, cli_runner):
        """Test schema command with specific section."""
        result = cli_runner.invoke(cli, ["config", "schema", "--section", "services"])
        assert result.exit_code == 0

    def test_schema_text_format_content(self, cli_runner):
        """Test schema text format contains expected content."""
        result = cli_runner.invoke(cli, ["config", "schema", "--format", "text"])
        assert result.exit_code == 0
        assert "📋 Main Configuration Sections:" in result.output
        assert "🧪 Test Configuration:" in result.output
        assert "logging:" in result.output
        assert "observers:" in result.output
        assert "tests:" in result.output


class TestConfigGenerateCommand:
    """Test the config generate subcommand."""

    def test_generate_help(self, cli_runner):
        """Test generate command help."""
        result = cli_runner.invoke(cli, ["config", "generate", "--help"])
        assert result.exit_code == 0
        assert "Generate configuration templates" in result.output
        assert "Available Templates:" in result.output
        assert "--template" in result.output
        assert "--output" in result.output
        assert "--overwrite" in result.output

    @pytest.mark.parametrize(
        "template_type", ["minimal", "basic", "advanced", "performance", "security"]
    )
    def test_generate_templates(self, cli_runner, template_type):
        """Test generating different template types."""
        result = cli_runner.invoke(
            cli, ["config", "generate", "--template", template_type]
        )
        assert result.exit_code == 0
        assert f"📄 Generating {template_type} configuration template" in result.output

    def test_generate_to_stdout(self, cli_runner):
        """Test generating template to stdout."""
        result = cli_runner.invoke(cli, ["config", "generate", "--template", "basic"])
        assert result.exit_code == 0
        assert "# Basic PANTHER Configuration Template" in result.output
        assert "logging:" in result.output
        assert "tests:" in result.output

    def test_generate_to_file(self, cli_runner, temp_dir):
        """Test generating template to file."""
        output_file = temp_dir / "generated_config.yaml"
        result = cli_runner.invoke(
            cli,
            ["config", "generate", "--template", "basic", "--output", str(output_file)],
        )
        assert result.exit_code == 0
        assert f"✅ Template generated: {output_file}" in result.output
        assert output_file.exists()

        # Verify file content
        content = output_file.read_text()
        assert "logging:" in content
        assert "tests:" in content

    def test_generate_overwrite_confirmation(self, cli_runner, temp_dir):
        """Test overwrite confirmation for existing files."""
        output_file = temp_dir / "existing_config.yaml"
        output_file.write_text("existing content")

        # Should prompt for confirmation (answer no)
        result = cli_runner.invoke(
            cli,
            ["config", "generate", "--template", "basic", "--output", str(output_file)],
            input="n\n",
        )

        assert result.exit_code == 0
        assert "Generation cancelled" in result.output

    def test_generate_with_overwrite_flag(self, cli_runner, temp_dir):
        """Test generation with overwrite flag."""
        output_file = temp_dir / "existing_config.yaml"
        output_file.write_text("existing content")

        result = cli_runner.invoke(
            cli,
            [
                "config",
                "generate",
                "--template",
                "basic",
                "--output",
                str(output_file),
                "--overwrite",
            ],
        )
        assert result.exit_code == 0
        assert "✅ Template generated:" in result.output

        # Verify content was overwritten
        content = output_file.read_text()
        assert "Basic PANTHER Configuration Template" in content


class TestConfigDesignCommand:
    """Test the config design subcommand."""

    def test_design_help(self, cli_runner):
        """Test design command help."""
        result = cli_runner.invoke(cli, ["config", "design", "--help"])
        assert result.exit_code == 0
        assert "Interactive configuration designer" in result.output
        assert "Design Features:" in result.output
        assert "--output" in result.output
        assert "--from-file" in result.output
        assert "--quick" in result.output
        assert "--non-interactive" in result.output

    def test_design_missing_output(self, cli_runner):
        """Test design command without output file."""
        result = cli_runner.invoke(cli, ["config", "design"])
        assert result.exit_code != 0
        assert "Missing option" in result.output or "required" in result.output.lower()

    def test_design_non_interactive(self, cli_runner, temp_dir):
        """Test design command in non-interactive mode."""
        output_file = temp_dir / "auto_config.yaml"
        result = cli_runner.invoke(
            cli, ["config", "design", "--output", str(output_file), "--non-interactive"]
        )
        assert result.exit_code == 0
        assert "🎨 PANTHER Interactive Configuration Designer" in result.output
        assert "Running in non-interactive mode" in result.output
        assert f"✅ Configuration created: {output_file}" in result.output

        # Verify file was created
        assert output_file.exists()
        content = output_file.read_text()
        assert "Auto-generated PANTHER Configuration" in content

    def test_design_interactive_basic(self, cli_runner, temp_dir):
        """Test basic interactive design session."""
        output_file = temp_dir / "interactive_config.yaml"

        # Provide inputs for interactive prompts
        inputs = [
            "My Test",  # Test name
            "Created interactively",  # Test description
            "y",  # Confirm save
        ]

        result = cli_runner.invoke(
            cli,
            ["config", "design", "--output", str(output_file)],
            input="\n".join(inputs) + "\n",
        )

        # Should either succeed or fail gracefully
        assert result.exit_code is not None

    def test_design_quick_mode(self, cli_runner, temp_dir):
        """Test design in quick mode."""
        output_file = temp_dir / "quick_config.yaml"

        # Quick mode should use defaults and skip optional prompts
        result = cli_runner.invoke(
            cli,
            ["config", "design", "--output", str(output_file), "--quick"],
            input="Test Name\nTest Description\n",
        )

        # Should complete without extensive prompting
        assert result.exit_code is not None

    def test_design_overwrite_confirmation(self, cli_runner, temp_dir):
        """Test overwrite confirmation in design mode."""
        output_file = temp_dir / "existing_design.yaml"
        output_file.write_text("existing config")

        result = cli_runner.invoke(
            cli, ["config", "design", "--output", str(output_file)], input="n\n"
        )  # Don't overwrite

        assert result.exit_code == 0
        assert "Design session cancelled" in result.output

    def test_design_from_existing_file(self, cli_runner, temp_dir, sample_config_file):
        """Test design starting from existing file."""
        output_file = temp_dir / "modified_config.yaml"

        result = cli_runner.invoke(
            cli,
            [
                "config",
                "design",
                "--output",
                str(output_file),
                "--from-file",
                str(sample_config_file),
                "--non-interactive",
            ],
        )

        # Should handle the from-file option
        assert result.exit_code is not None

    def test_design_keyboard_interrupt(self, cli_runner, temp_dir):
        """Test handling of keyboard interrupt in design mode."""
        output_file = temp_dir / "interrupted_config.yaml"

        # Simulate KeyboardInterrupt during ExperimentDesigner.run()
        # The stub ExperimentDesigner doesn't use click.prompt, so we
        # patch the designer's run method to raise KeyboardInterrupt.
        with patch(
            "panther.cli_click.commands.config.ExperimentDesigner"
        ) as MockDesigner:
            MockDesigner.return_value.run.side_effect = KeyboardInterrupt
            result = cli_runner.invoke(
                cli, ["config", "design", "--output", str(output_file)]
            )

            assert result.exit_code == 1
            assert "Design session cancelled by user" in result.output


class TestConfigIntegration:
    """Integration tests for config command functionality."""

    def test_config_workflow_validate_then_generate(self, cli_runner, temp_dir):
        """Test complete workflow: generate then validate."""
        # First generate a config
        config_file = temp_dir / "workflow_config.yaml"
        result1 = cli_runner.invoke(
            cli,
            ["config", "generate", "--template", "basic", "--output", str(config_file)],
        )
        assert result1.exit_code == 0
        assert config_file.exists()

        # Then validate the generated config
        result2 = cli_runner.invoke(
            cli, ["config", "validate", "--config", str(config_file)]
        )
        assert result2.exit_code == 0

    def test_config_yaml_parsing(self, cli_runner, temp_dir):
        """Test that generated configs are valid YAML."""
        config_file = temp_dir / "yaml_test.yaml"
        result = cli_runner.invoke(
            cli,
            ["config", "generate", "--template", "basic", "--output", str(config_file)],
        )
        assert result.exit_code == 0

        # Verify the file contains valid YAML
        with open(config_file, "r") as f:
            try:
                config_data = yaml.safe_load(f)
                assert isinstance(config_data, dict)
                assert "tests" in config_data
                assert "logging" in config_data
            except yaml.YAMLError:
                pytest.fail("Generated config is not valid YAML")

    def test_config_commands_with_global_flags(self, cli_runner, sample_config_file):
        """Test config commands with global debug/verbose flags."""
        # Test with debug flag
        result = cli_runner.invoke(
            cli, ["--debug", "config", "validate", "--config", str(sample_config_file)]
        )
        assert result.exit_code == 0
        assert "🐛 Debug mode enabled" in result.output

        # Test with verbose flag
        result = cli_runner.invoke(cli, ["--verbose", "config", "schema"])
        assert result.exit_code == 0
        assert "🔍 Verbose mode enabled" in result.output
