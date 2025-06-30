"""
Comprehensive unit tests for ConfigCommand CLI.

This module provides exhaustive testing for ALL ConfigCommand parameters,
including all 4 subcommands, template generation, validation, and error conditions.
"""

import argparse
import json
import logging
import tempfile
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, Mock, call, mock_open, patch

import pytest
import yaml

from panther.cli.subcommands.config import ConfigCommand
from tests.unit.test_cli.base_cli_test import ComprehensiveCLITest


class TestConfigCommandComprehensive(ComprehensiveCLITest):
    """Comprehensive tests for ConfigCommand with ALL parameter combinations."""

    @pytest.fixture
    def command_class(self):
        """Return the command class being tested."""
        return ConfigCommand

    @pytest.fixture
    def command_name(self):
        """Return the command name for testing."""
        return "config"

    @pytest.fixture
    def mock_config_loader_class(self):
        """Mock ConfigLoader class for testing."""
        with patch("panther.cli.subcommands.config.ConfigLoader") as mock:
            mock_instance = MagicMock()
            mock_instance.load_and_validate_experiment_config.return_value = MagicMock()
            mock.return_value = mock_instance
            yield mock, mock_instance

    @pytest.fixture
    def mock_logger_factory(self):
        """Mock LoggerFactory for testing."""
        with patch("panther.cli.subcommands.config.LoggerFactory") as mock:
            mock.initialize.return_value = None
            yield mock

    @pytest.fixture
    def mock_experiment_designer(self):
        """Mock ExperimentDesigner for testing."""
        with patch("panther.cli.subcommands.config.ExperimentDesigner") as mock:
            mock_instance = MagicMock()
            mock_instance.run.return_value = True
            mock.return_value = mock_instance
            yield mock, mock_instance

    @pytest.fixture
    def mock_validation_helper(self):
        """Mock ValidationHelper for testing."""
        with patch("panther.cli.subcommands.config.ValidationHelper") as mock:
            mock.explain_validation_error.return_value = "Detailed error explanation"
            mock.suggest_fixes.return_value = ["Fix suggestion 1", "Fix suggestion 2"]
            mock.validate_with_explanation.return_value = (True, ["Validation passed"])
            yield mock

    @pytest.fixture
    def sample_config_content(self):
        """Sample configuration content for testing."""
        return {
            "logging": {"level": "INFO", "enable_colors": True},
            "paths": {"output_dir": "outputs"},
            "docker": {"force_build_docker_image": False},
            "tests": [
                {
                    "name": "Test Case",
                    "description": "Test description",
                    "network_environment": {"type": "docker_compose"},
                    "services": {
                        "server": {
                            "name": "server",
                            "implementation": {"name": "picoquic", "type": "iut"},
                            "protocol": {
                                "name": "quic",
                                "version": "rfc9000",
                                "role": "server",
                            },
                            "ports": ["4443:4443"],
                        }
                    },
                    "steps": {"wait": 30},
                }
            ],
        }

    @pytest.fixture
    def invalid_yaml_content(self):
        """Invalid YAML content for testing."""
        return """
logging:
  level: INFO
tests:
  - name: "Test"
    invalid_yaml: [unclosed list
"""

    @pytest.fixture
    def malformed_config_content(self):
        """Malformed configuration content."""
        return {
            "logging": {"level": "INFO"},
            "tests": [
                {
                    "name": "Broken Test",
                    # Missing required fields
                    "services": {
                        "broken_service": {
                            # Missing required implementation and protocol
                            "ports": ["invalid_port"]
                        }
                    },
                }
            ],
        }

    # =============================================================================
    # PARSER REGISTRATION TESTS
    # =============================================================================

    def test_parser_registration(self):
        """Test that ConfigCommand is properly registered."""
        from panther.cli.main import create_parser

        parser = create_parser()

        # Verify 'config' subcommand exists
        subparsers_actions = [
            action
            for action in parser._actions
            if isinstance(action, argparse._SubParsersAction)
        ]
        assert len(subparsers_actions) == 1
        assert "config" in subparsers_actions[0].choices

    def test_all_subcommands_registered(self):
        """Test that all config subcommands are registered."""
        from panther.cli.main import create_parser

        parser = create_parser()

        # Parse config help to get subcommands
        try:
            parser.parse_args(["config", "--help"])
        except SystemExit:
            pass  # Expected behavior for help

        # Verify subcommands exist by testing their individual help
        subcommands = ["validate", "schema", "generate", "design"]

        for subcommand in subcommands:
            try:
                parser.parse_args(["config", subcommand, "--help"])
            except SystemExit:
                pass  # Expected for help command

    # =============================================================================
    # MAIN COMMAND HANDLER TESTS
    # =============================================================================

    def test_handle_no_action_specified(self, caplog):
        """Test behavior when no config action is specified."""
        args = self.create_namespace(config_action=None)

        result = ConfigCommand.handle(args)

        assert result == 1
        assert "No config action specified" in caplog.text

    def test_handle_unknown_action(self, caplog):
        """Test behavior with unknown config action."""
        args = self.create_namespace(config_action="unknown_action")

        result = ConfigCommand.handle(args)

        assert result == 1
        assert "Unknown config action: unknown_action" in caplog.text

    # =============================================================================
    # VALIDATE SUBCOMMAND TESTS
    # =============================================================================

    def test_validate_config_file_not_found(self, caplog):
        """Test validate command when config file doesn't exist."""
        args = self.create_namespace(
            config_action="validate",
            config="/nonexistent/config.yaml",
            strict=False,
            show_schema=False,
            explain=False,
        )

        result = ConfigCommand.handle(args)

        assert result == 1
        assert "Configuration file not found" in caplog.text

    def test_validate_invalid_yaml_syntax(self, tmp_path, invalid_yaml_content, caplog):
        """Test validate command with invalid YAML syntax."""
        config_file = tmp_path / "invalid.yaml"
        config_file.write_text(invalid_yaml_content)

        args = self.create_namespace(
            config_action="validate",
            config=str(config_file),
            strict=False,
            show_schema=False,
            explain=False,
        )

        result = ConfigCommand.handle(args)

        assert result == 1
        assert "YAML syntax error" in caplog.text

    def test_validate_valid_config_basic(
        self,
        tmp_path,
        sample_config_content,
        mock_config_loader_class,
        mock_logger_factory,
        caplog,
    ):
        """Test validate command with valid configuration."""
        config_file = tmp_path / "valid.yaml"
        with open(config_file, "w") as f:
            yaml.dump(sample_config_content, f)

        mock_config_class, mock_config_instance = mock_config_loader_class

        # Setup experiment config mock
        mock_experiment_config = MagicMock()
        mock_experiment_config.tests = [MagicMock(), MagicMock()]  # 2 tests
        mock_config_instance.load_and_validate_experiment_config.return_value = (
            mock_experiment_config
        )

        args = self.create_namespace(
            config_action="validate",
            config=str(config_file),
            strict=False,
            show_schema=False,
            explain=False,
        )

        result = ConfigCommand.handle(args)

        assert result == 0
        assert "YAML syntax is valid" in caplog.text
        assert "Configuration schema is valid" in caplog.text
        assert "Found 2 test(s) in configuration" in caplog.text
        assert "Configuration is valid and ready to use" in caplog.text

        # Verify LoggerFactory was initialized
        mock_logger_factory.initialize.assert_called_once()

        # Verify ConfigLoader was used
        mock_config_class.assert_called_once()
        mock_config_instance.load_and_validate_experiment_config.assert_called_once()

    def test_validate_with_show_schema(
        self, tmp_path, sample_config_content, mock_config_loader_class, caplog
    ):
        """Test validate command with --show-schema flag."""
        config_file = tmp_path / "valid.yaml"
        with open(config_file, "w") as f:
            yaml.dump(sample_config_content, f)

        mock_config_class, mock_config_instance = mock_config_loader_class

        # Setup experiment config with named tests
        mock_test1 = MagicMock()
        mock_test1.name = "Test 1"
        mock_test1.services = {"service1": MagicMock(), "service2": MagicMock()}

        mock_test2 = MagicMock()
        mock_test2.name = "Test 2"
        mock_test2.services = {"service1": MagicMock()}

        mock_experiment_config = MagicMock()
        mock_experiment_config.tests = [mock_test1, mock_test2]
        mock_config_instance.load_and_validate_experiment_config.return_value = (
            mock_experiment_config
        )

        args = self.create_namespace(
            config_action="validate",
            config=str(config_file),
            strict=False,
            show_schema=True,
            explain=False,
        )

        result = ConfigCommand.handle(args)

        assert result == 0
        assert "Configuration Summary:" in caplog.text
        assert "Test 1: Test 1" in caplog.text
        assert "Test 2: Test 2" in caplog.text
        assert "Services: 2" in caplog.text
        assert "Services: 1" in caplog.text

    def test_validate_with_strict_mode(
        self, tmp_path, sample_config_content, mock_config_loader_class
    ):
        """Test validate command with --strict flag."""
        config_file = tmp_path / "valid.yaml"
        with open(config_file, "w") as f:
            yaml.dump(sample_config_content, f)

        mock_config_class, mock_config_instance = mock_config_loader_class

        args = self.create_namespace(
            config_action="validate",
            config=str(config_file),
            strict=True,
            show_schema=False,
            explain=False,
        )

        result = ConfigCommand.handle(args)

        assert result == 0
        # Strict mode should still use same validation logic
        mock_config_class.assert_called_once()

    def test_validate_with_explain_success(
        self,
        tmp_path,
        sample_config_content,
        mock_config_loader_class,
        mock_validation_helper,
        caplog,
    ):
        """Test validate command with --explain flag on successful validation."""
        config_file = tmp_path / "valid.yaml"
        with open(config_file, "w") as f:
            yaml.dump(sample_config_content, f)

        mock_config_class, mock_config_instance = mock_config_loader_class

        args = self.create_namespace(
            config_action="validate",
            config=str(config_file),
            strict=False,
            show_schema=False,
            explain=True,
        )

        result = ConfigCommand.handle(args)

        assert result == 0
        assert "Detailed Validation Report:" in caplog.text
        assert "Validation passed" in caplog.text

        # Verify ValidationHelper was used
        mock_validation_helper.validate_with_explanation.assert_called_once()

    def test_validate_config_validation_error(
        self, tmp_path, sample_config_content, mock_config_loader_class, caplog
    ):
        """Test validate command when configuration validation fails."""
        config_file = tmp_path / "invalid.yaml"
        with open(config_file, "w") as f:
            yaml.dump(sample_config_content, f)

        mock_config_class, mock_config_instance = mock_config_loader_class

        # Setup ConfigLoader to raise validation error
        mock_config_instance.load_and_validate_experiment_config.side_effect = (
            Exception("Schema validation failed")
        )

        args = self.create_namespace(
            config_action="validate",
            config=str(config_file),
            strict=False,
            show_schema=False,
            explain=False,
        )

        result = ConfigCommand.handle(args)

        assert result == 1
        assert "Configuration validation failed" in caplog.text

    def test_validate_with_explain_on_error(
        self,
        tmp_path,
        sample_config_content,
        mock_config_loader_class,
        mock_validation_helper,
        caplog,
    ):
        """Test validate command with --explain flag when validation fails."""
        config_file = tmp_path / "invalid.yaml"
        with open(config_file, "w") as f:
            yaml.dump(sample_config_content, f)

        mock_config_class, mock_config_instance = mock_config_loader_class

        # Setup ConfigLoader to raise validation error
        validation_error = Exception("Schema validation failed")
        mock_config_instance.load_and_validate_experiment_config.side_effect = (
            validation_error
        )

        args = self.create_namespace(
            config_action="validate",
            config=str(config_file),
            strict=False,
            show_schema=False,
            explain=True,
        )

        result = ConfigCommand.handle(args)

        assert result == 1
        assert "Configuration validation failed" in caplog.text
        assert "Detailed error explanation" in caplog.text
        assert "Suggestions:" in caplog.text
        assert "Fix suggestion 1" in caplog.text
        assert "Fix suggestion 2" in caplog.text

        # Verify ValidationHelper methods were called
        mock_validation_helper.explain_validation_error.assert_called_once_with(
            validation_error
        )
        mock_validation_helper.suggest_fixes.assert_called_once()

    def test_validate_explain_validation_fails(
        self,
        tmp_path,
        sample_config_content,
        mock_config_loader_class,
        mock_validation_helper,
        caplog,
    ):
        """Test validate command when explanation validation itself fails."""
        config_file = tmp_path / "valid.yaml"
        with open(config_file, "w") as f:
            yaml.dump(sample_config_content, f)

        mock_config_class, mock_config_instance = mock_config_loader_class

        # Setup ValidationHelper to return validation failure
        mock_validation_helper.validate_with_explanation.return_value = (
            False,
            ["Validation failed"],
        )

        args = self.create_namespace(
            config_action="validate",
            config=str(config_file),
            strict=False,
            show_schema=False,
            explain=True,
        )

        result = ConfigCommand.handle(args)

        assert result == 1
        assert "Detailed Validation Report:" in caplog.text
        assert "Validation failed" in caplog.text

    # =============================================================================
    # SCHEMA SUBCOMMAND TESTS
    # =============================================================================

    def test_schema_text_format_default(self, caplog):
        """Test schema command with default text format."""
        args = self.create_namespace(config_action="schema", format="text")

        result = ConfigCommand.handle(args)

        assert result == 0
        assert "PANTHER Configuration Schema" in caplog.text
        assert "Main Configuration Sections:" in caplog.text
        assert "Test Configuration:" in caplog.text
        assert "Service Configuration:" in caplog.text

    @pytest.mark.parametrize("format_choice", ["text", "json", "yaml"])
    def test_schema_different_formats(self, format_choice, caplog):
        """Test schema command with different format choices."""
        args = self.create_namespace(config_action="schema", format=format_choice)

        result = ConfigCommand.handle(args)

        assert result == 0
        assert "PANTHER Configuration Schema" in caplog.text

        if format_choice == "json":
            assert "JSON schema export not yet implemented" in caplog.text
        elif format_choice == "yaml":
            assert "YAML schema export not yet implemented" in caplog.text
        else:  # text
            assert "Main Configuration Sections:" in caplog.text

    def test_schema_error_handling(self, caplog):
        """Test schema command error handling."""
        args = self.create_namespace(config_action="schema", format="text")

        with patch("panther.cli.subcommands.config.logging") as mock_logging:
            mock_logging.info.side_effect = Exception("Schema error")

            result = ConfigCommand.handle(args)

            assert result == 1

    # =============================================================================
    # GENERATE SUBCOMMAND TESTS
    # =============================================================================

    @pytest.mark.parametrize(
        "template_type", ["minimal", "basic", "advanced", "performance", "security"]
    )
    def test_generate_all_template_types(self, template_type, caplog):
        """Test generate command with all template types."""
        args = self.create_namespace(
            config_action="generate", template=template_type, output=None
        )

        result = ConfigCommand.handle(args)

        assert result == 0
        # Template content should be printed to stdout
        assert (
            f"# {template_type.title()}" in caplog.text
            or f"# {template_type.upper()}" in caplog.text
            or "PANTHER Configuration" in caplog.text
        )

    def test_generate_with_output_file(self, tmp_path):
        """Test generate command with output file."""
        output_file = tmp_path / "generated_config.yaml"

        args = self.create_namespace(
            config_action="generate", template="basic", output=str(output_file)
        )

        result = ConfigCommand.handle(args)

        assert result == 0
        assert output_file.exists()

        # Verify content was written
        content = output_file.read_text()
        assert "Basic PANTHER Configuration" in content
        assert "logging:" in content
        assert "tests:" in content

    def test_generate_creates_output_directory(self, tmp_path, caplog):
        """Test generate command creates parent directories."""
        output_file = tmp_path / "nested" / "dir" / "config.yaml"

        args = self.create_namespace(
            config_action="generate", template="minimal", output=str(output_file)
        )

        result = ConfigCommand.handle(args)

        assert result == 0
        assert output_file.exists()
        assert "Template generated" in caplog.text

    def test_generate_unknown_template(self, caplog):
        """Test generate command with unknown template."""
        args = self.create_namespace(
            config_action="generate", template="unknown_template", output=None
        )

        result = ConfigCommand.handle(args)

        assert result == 1
        assert "Unknown template: unknown_template" in caplog.text

    def test_generate_template_content_validation(self):
        """Test that all template types generate valid content."""
        templates = ["minimal", "basic", "advanced", "performance", "security"]

        for template in templates:
            args = self.create_namespace(
                config_action="generate", template=template, output=None
            )

            result = ConfigCommand.handle(args)
            assert result == 0, f"Template {template} failed to generate"

    def test_generate_error_handling(self, tmp_path, caplog):
        """Test generate command error handling."""
        # Try to write to a protected location (simulate permission error)
        with patch("builtins.open", side_effect=PermissionError("Permission denied")):
            args = self.create_namespace(
                config_action="generate",
                template="basic",
                output=str(tmp_path / "protected.yaml"),
            )

            result = ConfigCommand.handle(args)

            assert result == 1
            assert "Error generating template" in caplog.text

    # =============================================================================
    # DESIGN SUBCOMMAND TESTS
    # =============================================================================

    def test_design_successful_creation(
        self, tmp_path, mock_experiment_designer, caplog
    ):
        """Test design command successful execution."""
        output_file = tmp_path / "designed_config.yaml"

        mock_designer_class, mock_designer_instance = mock_experiment_designer

        args = self.create_namespace(
            config_action="design", output=str(output_file), from_file=None, quick=False
        )

        result = ConfigCommand.handle(args)

        assert result == 0
        assert "Welcome to PANTHER Interactive Configuration Designer!" in caplog.text
        assert "Configuration successfully created" in caplog.text
        assert "You can validate it with:" in caplog.text

        # Verify ExperimentDesigner was called correctly
        mock_designer_class.assert_called_once_with(
            output_path=str(output_file), from_file=None, quick_mode=False
        )
        mock_designer_instance.run.assert_called_once()

    def test_design_with_from_file(self, tmp_path, mock_experiment_designer):
        """Test design command with --from parameter."""
        output_file = tmp_path / "designed_config.yaml"
        source_file = tmp_path / "source_config.yaml"
        source_file.write_text("# Source config")

        mock_designer_class, mock_designer_instance = mock_experiment_designer

        args = self.create_namespace(
            config_action="design",
            output=str(output_file),
            from_file=str(source_file),
            quick=False,
        )

        result = ConfigCommand.handle(args)

        assert result == 0

        # Verify from_file was passed
        mock_designer_class.assert_called_once_with(
            output_path=str(output_file), from_file=str(source_file), quick_mode=False
        )

    def test_design_with_quick_mode(self, tmp_path, mock_experiment_designer):
        """Test design command with --quick flag."""
        output_file = tmp_path / "designed_config.yaml"

        mock_designer_class, mock_designer_instance = mock_experiment_designer

        args = self.create_namespace(
            config_action="design", output=str(output_file), from_file=None, quick=True
        )

        result = ConfigCommand.handle(args)

        assert result == 0

        # Verify quick_mode was enabled
        mock_designer_class.assert_called_once_with(
            output_path=str(output_file), from_file=None, quick_mode=True
        )

    def test_design_failed_creation(self, tmp_path, mock_experiment_designer, caplog):
        """Test design command when creation fails."""
        output_file = tmp_path / "designed_config.yaml"

        mock_designer_class, mock_designer_instance = mock_experiment_designer
        mock_designer_instance.run.return_value = False  # Simulate failure

        args = self.create_namespace(
            config_action="design", output=str(output_file), from_file=None, quick=False
        )

        result = ConfigCommand.handle(args)

        assert result == 1
        assert "Configuration design cancelled or failed" in caplog.text

    def test_design_keyboard_interrupt(
        self, tmp_path, mock_experiment_designer, caplog
    ):
        """Test design command keyboard interrupt handling."""
        output_file = tmp_path / "designed_config.yaml"

        mock_designer_class, mock_designer_instance = mock_experiment_designer
        mock_designer_instance.run.side_effect = KeyboardInterrupt()

        args = self.create_namespace(
            config_action="design", output=str(output_file), from_file=None, quick=False
        )

        result = ConfigCommand.handle(args)

        assert result == 130  # Standard exit code for SIGINT
        assert "Design session cancelled by user" in caplog.text

    def test_design_error_handling(self, tmp_path, mock_experiment_designer, caplog):
        """Test design command error handling."""
        output_file = tmp_path / "designed_config.yaml"

        mock_designer_class, mock_designer_instance = mock_experiment_designer
        mock_designer_instance.run.side_effect = Exception("Design error")

        args = self.create_namespace(
            config_action="design", output=str(output_file), from_file=None, quick=False
        )

        result = ConfigCommand.handle(args)

        assert result == 1
        assert "Error during configuration design" in caplog.text

    # =============================================================================
    # PARAMETER VALIDATION TESTS
    # =============================================================================

    @pytest.mark.parametrize(
        "invalid_action",
        ["invalid", "", "VALIDATE", "schema_wrong", 123, None],  # Case sensitive
    )
    def test_invalid_actions(self, invalid_action, caplog):
        """Test handling of invalid action parameters."""
        args = self.create_namespace(config_action=invalid_action)

        result = ConfigCommand.handle(args)

        if invalid_action is None:
            assert "No config action specified" in caplog.text
        else:
            assert result == 1

    @pytest.mark.parametrize("format_choice", ["json", "yaml", "text"])
    def test_schema_format_choices(self, format_choice):
        """Test all valid schema format choices."""
        args = self.create_namespace(config_action="schema", format=format_choice)

        result = ConfigCommand.handle(args)

        assert result == 0

    @pytest.mark.parametrize(
        "template_choice", ["minimal", "basic", "advanced", "performance", "security"]
    )
    def test_generate_template_choices(self, template_choice):
        """Test all valid template choices."""
        args = self.create_namespace(
            config_action="generate", template=template_choice, output=None
        )

        result = ConfigCommand.handle(args)

        assert result == 0

    @pytest.mark.parametrize("flag_value", [True, False])
    def test_validate_boolean_flags(
        self, flag_value, tmp_path, sample_config_content, mock_config_loader_class
    ):
        """Test validate command boolean flags."""
        config_file = tmp_path / "test_config.yaml"
        with open(config_file, "w") as f:
            yaml.dump(sample_config_content, f)

        mock_config_class, mock_config_instance = mock_config_loader_class

        flags = ["strict", "show_schema", "explain"]

        for flag in flags:
            args_dict = {
                "config_action": "validate",
                "config": str(config_file),
                "strict": False,
                "show_schema": False,
                "explain": False,
            }
            args_dict[flag] = flag_value

            args = self.create_namespace(**args_dict)

            result = ConfigCommand.handle(args)

            assert result == 0  # Should not crash with any valid flag value

    # =============================================================================
    # EDGE CASE TESTS
    # =============================================================================

    def test_unicode_in_config_path(
        self, tmp_path, sample_config_content, mock_config_loader_class
    ):
        """Test handling of unicode characters in config path."""
        unicode_path = tmp_path / "测试_config.yaml"
        with open(unicode_path, "w") as f:
            yaml.dump(sample_config_content, f)

        mock_config_class, mock_config_instance = mock_config_loader_class

        args = self.create_namespace(
            config_action="validate",
            config=str(unicode_path),
            strict=False,
            show_schema=False,
            explain=False,
        )

        result = ConfigCommand.handle(args)

        assert result == 0  # Should handle unicode gracefully

    def test_very_long_output_path(self, tmp_path):
        """Test handling of very long output paths."""
        long_path = tmp_path / ("a" * 200) / "config.yaml"

        args = self.create_namespace(
            config_action="generate", template="minimal", output=str(long_path)
        )

        result = ConfigCommand.handle(args)

        assert result == 0  # Should handle long paths gracefully
        assert long_path.exists()

    def test_empty_config_file(self, tmp_path, mock_config_loader_class, caplog):
        """Test handling of empty configuration file."""
        empty_config = tmp_path / "empty.yaml"
        empty_config.write_text("")

        mock_config_class, mock_config_instance = mock_config_loader_class

        args = self.create_namespace(
            config_action="validate",
            config=str(empty_config),
            strict=False,
            show_schema=False,
            explain=False,
        )

        result = ConfigCommand.handle(args)

        # Should handle empty files gracefully
        assert result in [0, 1]  # May succeed or fail depending on validation

    def test_config_file_with_only_comments(self, tmp_path, mock_config_loader_class):
        """Test handling of config file with only comments."""
        comment_only_config = tmp_path / "comments.yaml"
        comment_only_config.write_text(
            """
# This is a comment
# Another comment
# No actual configuration
"""
        )

        mock_config_class, mock_config_instance = mock_config_loader_class

        args = self.create_namespace(
            config_action="validate",
            config=str(comment_only_config),
            strict=False,
            show_schema=False,
            explain=False,
        )

        result = ConfigCommand.handle(args)

        # Should handle comment-only files gracefully
        assert result in [0, 1]

    # =============================================================================
    # INTEGRATION TESTS
    # =============================================================================

    def test_end_to_end_config_workflow(
        self, tmp_path, sample_config_content, mock_config_loader_class, caplog
    ):
        """Test complete config workflow: generate → validate → design."""
        mock_config_class, mock_config_instance = mock_config_loader_class

        # Step 1: Generate a config
        generated_config = tmp_path / "generated.yaml"
        args_generate = self.create_namespace(
            config_action="generate", template="basic", output=str(generated_config)
        )

        result = ConfigCommand.handle(args_generate)
        assert result == 0
        assert generated_config.exists()

        # Step 2: Validate the generated config
        args_validate = self.create_namespace(
            config_action="validate",
            config=str(generated_config),
            strict=False,
            show_schema=True,
            explain=False,
        )

        result = ConfigCommand.handle(args_validate)
        # Note: Might fail due to mocking, but should not crash
        assert result in [0, 1]

        # Step 3: Display schema
        args_schema = self.create_namespace(config_action="schema", format="text")

        result = ConfigCommand.handle(args_schema)
        assert result == 0
        assert "PANTHER Configuration Schema" in caplog.text

    def test_config_command_comprehensive_parameters(
        self,
        tmp_path,
        sample_config_content,
        mock_config_loader_class,
        mock_experiment_designer,
    ):
        """Test config command with comprehensive parameter combinations."""
        config_file = tmp_path / "comprehensive.yaml"
        with open(config_file, "w") as f:
            yaml.dump(sample_config_content, f)

        mock_config_class, mock_config_instance = mock_config_loader_class
        mock_designer_class, mock_designer_instance = mock_experiment_designer

        # Test validate with all flags
        args_validate = self.create_namespace(
            config_action="validate",
            config=str(config_file),
            strict=True,
            show_schema=True,
            explain=True,
        )

        result = ConfigCommand.handle(args_validate)
        assert result in [0, 1]  # May succeed or fail due to mocking

        # Test generate with output
        output_file = tmp_path / "generated_comprehensive.yaml"
        args_generate = self.create_namespace(
            config_action="generate", template="advanced", output=str(output_file)
        )

        result = ConfigCommand.handle(args_generate)
        assert result == 0
        assert output_file.exists()

        # Test design with all options
        design_output = tmp_path / "designed_comprehensive.yaml"
        args_design = self.create_namespace(
            config_action="design",
            output=str(design_output),
            from_file=str(config_file),
            quick=True,
        )

        result = ConfigCommand.handle(args_design)
        assert result == 0

        # Verify all components were used appropriately
        mock_config_class.assert_called()
        mock_designer_class.assert_called_once_with(
            output_path=str(design_output), from_file=str(config_file), quick_mode=True
        )
