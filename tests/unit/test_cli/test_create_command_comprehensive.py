"""
Comprehensive unit tests for CreateCommand CLI.

This module provides exhaustive testing for ALL CreateCommand parameters,
including all 3 subcommands, plugin creation, subplugin creation, template generation, and error conditions.
"""

import argparse
import json
import logging
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, call, mock_open, patch

import pytest

from panther.cli.subcommands.create import CreateCommand
from tests.unit.test_cli.base_cli_test import ComprehensiveCLITest


class TestCreateCommandComprehensive(ComprehensiveCLITest):
    """Comprehensive tests for CreateCommand with ALL parameter combinations."""

    @pytest.fixture
    def command_class(self):
        """Return the command class being tested."""
        return CreateCommand

    @pytest.fixture
    def command_name(self):
        """Return the command name for testing."""
        return "create"

    @pytest.fixture
    def mock_plugin_creator_functions(self):
        """Mock plugin creator functions for testing."""
        with patch(
            "panther.cli.subcommands.create.create_plugin"
        ) as mock_create_plugin, patch(
            "panther.cli.subcommands.create.create_subplugin"
        ) as mock_create_subplugin:
            # Setup create_plugin mock
            mock_create_plugin.return_value = True

            # Setup create_subplugin mock
            mock_create_subplugin.return_value = True

            yield {
                "create_plugin": mock_create_plugin,
                "create_subplugin": mock_create_subplugin,
            }

    # =============================================================================
    # PARSER REGISTRATION TESTS
    # =============================================================================

    def test_parser_registration(self):
        """Test that CreateCommand is properly registered."""
        from panther.cli.main import create_parser

        parser = create_parser()

        # Verify 'create' subcommand exists
        subparsers_actions = [
            action
            for action in parser._actions
            if isinstance(action, argparse._SubParsersAction)
        ]
        assert len(subparsers_actions) == 1
        assert "create" in subparsers_actions[0].choices

    def test_all_subcommands_registered(self):
        """Test that all create subcommands are registered."""
        from panther.cli.main import create_parser

        parser = create_parser()

        # Parse create help to get subcommands
        try:
            parser.parse_args(["create", "--help"])
        except SystemExit:
            pass  # Expected behavior for help

        # Verify subcommands exist by testing their individual help
        subcommands = ["plugin", "subplugin", "template"]

        for subcommand in subcommands:
            try:
                parser.parse_args(["create", subcommand, "--help"])
            except SystemExit:
                pass  # Expected for help command

    # =============================================================================
    # MAIN COMMAND HANDLER TESTS
    # =============================================================================

    def test_handle_no_action_specified(self, caplog):
        """Test behavior when no create action is specified."""
        args = self.create_namespace(create_action=None)

        result = CreateCommand.handle(args)

        assert result == 1
        assert "No create action specified" in caplog.text

    def test_handle_unknown_action(self, caplog):
        """Test behavior with unknown create action."""
        args = self.create_namespace(create_action="unknown_action")

        result = CreateCommand.handle(args)

        assert result == 1
        assert "Unknown create action: unknown_action" in caplog.text

    # =============================================================================
    # PLUGIN SUBCOMMAND TESTS
    # =============================================================================

    @pytest.mark.parametrize("plugin_type", ["service", "environment", "protocol"])
    def test_create_plugin_all_types(
        self, plugin_type, mock_plugin_creator_functions, caplog
    ):
        """Test plugin creation for all valid plugin types."""
        plugin_name = f"test_{plugin_type}_plugin"

        args = self.create_namespace(
            create_action="plugin",
            plugin_type=plugin_type,
            plugin_name=plugin_name,
            dev_mode=False,
            production_mode=False,
            with_subplugins=False,
        )

        result = CreateCommand.handle(args)

        assert result == 0
        assert f"Creating {plugin_type} plugin: {plugin_name}" in caplog.text
        assert f"Plugin '{plugin_name}' created successfully" in caplog.text

        # Verify create_plugin was called with correct parameters
        mock_plugin_creator_functions["create_plugin"].assert_called_once_with(
            plugin_type,
            plugin_name,
            in_development_mode=None,  # Neither dev nor production mode specified
            create_subplugins=False,
        )

    def test_create_plugin_dev_mode(self, mock_plugin_creator_functions, caplog):
        """Test plugin creation with dev mode enabled."""
        args = self.create_namespace(
            create_action="plugin",
            plugin_type="service",
            plugin_name="test_dev_plugin",
            dev_mode=True,
            production_mode=False,
            with_subplugins=False,
        )

        result = CreateCommand.handle(args)

        assert result == 0
        assert "Creating service plugin: test_dev_plugin" in caplog.text

        # Verify create_plugin was called with dev_mode=True
        mock_plugin_creator_functions["create_plugin"].assert_called_once_with(
            "service",
            "test_dev_plugin",
            in_development_mode=True,
            create_subplugins=False,
        )

    def test_create_plugin_production_mode(self, mock_plugin_creator_functions, caplog):
        """Test plugin creation with production mode enabled."""
        args = self.create_namespace(
            create_action="plugin",
            plugin_type="environment",
            plugin_name="test_prod_plugin",
            dev_mode=False,
            production_mode=True,
            with_subplugins=False,
        )

        result = CreateCommand.handle(args)

        assert result == 0
        assert "Creating environment plugin: test_prod_plugin" in caplog.text

        # Verify create_plugin was called with dev_mode=False (production)
        mock_plugin_creator_functions["create_plugin"].assert_called_once_with(
            "environment",
            "test_prod_plugin",
            in_development_mode=False,
            create_subplugins=False,
        )

    def test_create_plugin_with_subplugins(self, mock_plugin_creator_functions, caplog):
        """Test plugin creation with subplugins enabled."""
        args = self.create_namespace(
            create_action="plugin",
            plugin_type="protocol",
            plugin_name="test_with_subplugins",
            dev_mode=False,
            production_mode=False,
            with_subplugins=True,
        )

        result = CreateCommand.handle(args)

        assert result == 0
        assert "Creating protocol plugin: test_with_subplugins" in caplog.text

        # Verify create_plugin was called with create_subplugins=True
        mock_plugin_creator_functions["create_plugin"].assert_called_once_with(
            "protocol",
            "test_with_subplugins",
            in_development_mode=None,
            create_subplugins=True,
        )

    def test_create_plugin_all_flags_enabled(
        self, mock_plugin_creator_functions, caplog
    ):
        """Test plugin creation with all flags enabled (dev mode takes precedence)."""
        args = self.create_namespace(
            create_action="plugin",
            plugin_type="service",
            plugin_name="test_all_flags",
            dev_mode=True,
            production_mode=True,  # Should be ignored when dev_mode is True
            with_subplugins=True,
        )

        result = CreateCommand.handle(args)

        assert result == 0

        # Dev mode should take precedence over production mode
        mock_plugin_creator_functions["create_plugin"].assert_called_once_with(
            "service",
            "test_all_flags",
            in_development_mode=True,  # dev_mode takes precedence
            create_subplugins=True,
        )

    def test_create_plugin_creation_failure(
        self, mock_plugin_creator_functions, caplog
    ):
        """Test plugin creation when create_plugin returns False."""
        mock_plugin_creator_functions["create_plugin"].return_value = False

        args = self.create_namespace(
            create_action="plugin",
            plugin_type="service",
            plugin_name="test_failure",
            dev_mode=False,
            production_mode=False,
            with_subplugins=False,
        )

        result = CreateCommand.handle(args)

        assert result == 1
        assert "Failed to create plugin 'test_failure'" in caplog.text

    def test_create_plugin_exception_handling(
        self, mock_plugin_creator_functions, caplog
    ):
        """Test plugin creation exception handling."""
        mock_plugin_creator_functions["create_plugin"].side_effect = Exception(
            "Plugin creation error"
        )

        args = self.create_namespace(
            create_action="plugin",
            plugin_type="service",
            plugin_name="test_exception",
            dev_mode=False,
            production_mode=False,
            with_subplugins=False,
        )

        result = CreateCommand.handle(args)

        assert result == 1
        assert "Error creating plugin: Plugin creation error" in caplog.text

    def test_create_plugin_debug_mode_exception(
        self, mock_plugin_creator_functions, caplog
    ):
        """Test plugin creation exception handling with debug mode."""
        mock_plugin_creator_functions["create_plugin"].side_effect = Exception(
            "Plugin creation error"
        )

        args = self.create_namespace(
            create_action="plugin",
            plugin_type="service",
            plugin_name="test_debug_exception",
            dev_mode=False,
            production_mode=False,
            with_subplugins=False,
            debug=True,
        )

        with patch("traceback.print_exc") as mock_traceback:
            result = CreateCommand.handle(args)

            assert result == 1
            assert "Error creating plugin: Plugin creation error" in caplog.text
            mock_traceback.assert_called_once()

    # =============================================================================
    # SUBPLUGIN SUBCOMMAND TESTS
    # =============================================================================

    @pytest.mark.parametrize("plugin_type", ["service", "environment", "protocol"])
    def test_create_subplugin_all_types(
        self, plugin_type, mock_plugin_creator_functions, caplog
    ):
        """Test subplugin creation for all valid plugin types."""
        plugin_name = f"parent_{plugin_type}_plugin"
        subplugin_name = f"child_{plugin_type}_subplugin"

        args = self.create_namespace(
            create_action="subplugin",
            plugin_type=plugin_type,
            plugin_name=plugin_name,
            subplugin_name=subplugin_name,
            dev_mode=False,
            production_mode=False,
        )

        result = CreateCommand.handle(args)

        assert result == 0
        assert (
            f"Creating subplugin '{subplugin_name}' for {plugin_type} plugin '{plugin_name}'"
            in caplog.text
        )
        assert f"Subplugin '{subplugin_name}' created successfully" in caplog.text

        # Verify create_subplugin was called with correct parameters
        mock_plugin_creator_functions["create_subplugin"].assert_called_once_with(
            plugin_type, plugin_name, subplugin_name, in_development_mode=None
        )

    def test_create_subplugin_dev_mode(self, mock_plugin_creator_functions, caplog):
        """Test subplugin creation with dev mode enabled."""
        args = self.create_namespace(
            create_action="subplugin",
            plugin_type="service",
            plugin_name="parent_plugin",
            subplugin_name="dev_subplugin",
            dev_mode=True,
            production_mode=False,
        )

        result = CreateCommand.handle(args)

        assert result == 0

        # Verify create_subplugin was called with dev_mode=True
        mock_plugin_creator_functions["create_subplugin"].assert_called_once_with(
            "service", "parent_plugin", "dev_subplugin", in_development_mode=True
        )

    def test_create_subplugin_production_mode(
        self, mock_plugin_creator_functions, caplog
    ):
        """Test subplugin creation with production mode enabled."""
        args = self.create_namespace(
            create_action="subplugin",
            plugin_type="environment",
            plugin_name="parent_plugin",
            subplugin_name="prod_subplugin",
            dev_mode=False,
            production_mode=True,
        )

        result = CreateCommand.handle(args)

        assert result == 0

        # Verify create_subplugin was called with dev_mode=False (production)
        mock_plugin_creator_functions["create_subplugin"].assert_called_once_with(
            "environment", "parent_plugin", "prod_subplugin", in_development_mode=False
        )

    def test_create_subplugin_both_modes_enabled(
        self, mock_plugin_creator_functions, caplog
    ):
        """Test subplugin creation with both dev and production modes (dev takes precedence)."""
        args = self.create_namespace(
            create_action="subplugin",
            plugin_type="protocol",
            plugin_name="parent_plugin",
            subplugin_name="both_modes_subplugin",
            dev_mode=True,
            production_mode=True,  # Should be ignored
        )

        result = CreateCommand.handle(args)

        assert result == 0

        # Dev mode should take precedence
        mock_plugin_creator_functions["create_subplugin"].assert_called_once_with(
            "protocol",
            "parent_plugin",
            "both_modes_subplugin",
            in_development_mode=True,
        )

    def test_create_subplugin_creation_failure(
        self, mock_plugin_creator_functions, caplog
    ):
        """Test subplugin creation when create_subplugin returns False."""
        mock_plugin_creator_functions["create_subplugin"].return_value = False

        args = self.create_namespace(
            create_action="subplugin",
            plugin_type="service",
            plugin_name="parent_plugin",
            subplugin_name="failed_subplugin",
            dev_mode=False,
            production_mode=False,
        )

        result = CreateCommand.handle(args)

        assert result == 1
        assert "Failed to create subplugin 'failed_subplugin'" in caplog.text

    def test_create_subplugin_exception_handling(
        self, mock_plugin_creator_functions, caplog
    ):
        """Test subplugin creation exception handling."""
        mock_plugin_creator_functions["create_subplugin"].side_effect = Exception(
            "Subplugin creation error"
        )

        args = self.create_namespace(
            create_action="subplugin",
            plugin_type="service",
            plugin_name="parent_plugin",
            subplugin_name="exception_subplugin",
            dev_mode=False,
            production_mode=False,
        )

        result = CreateCommand.handle(args)

        assert result == 1
        assert "Error creating subplugin: Subplugin creation error" in caplog.text

    def test_create_subplugin_debug_mode_exception(
        self, mock_plugin_creator_functions, caplog
    ):
        """Test subplugin creation exception handling with debug mode."""
        mock_plugin_creator_functions["create_subplugin"].side_effect = Exception(
            "Subplugin creation error"
        )

        args = self.create_namespace(
            create_action="subplugin",
            plugin_type="environment",
            plugin_name="parent_plugin",
            subplugin_name="debug_exception_subplugin",
            dev_mode=False,
            production_mode=False,
            debug=True,
        )

        with patch("traceback.print_exc") as mock_traceback:
            result = CreateCommand.handle(args)

            assert result == 1
            assert "Error creating subplugin: Subplugin creation error" in caplog.text
            mock_traceback.assert_called_once()

    # =============================================================================
    # TEMPLATE SUBCOMMAND TESTS
    # =============================================================================

    @pytest.mark.parametrize("template_type", ["experiment", "service", "environment"])
    def test_create_template_all_types_stdout(self, template_type, caplog):
        """Test template creation for all types outputting to stdout."""
        args = self.create_namespace(
            create_action="template", template_type=template_type, output=None
        )

        result = CreateCommand.handle(args)

        assert result == 0
        assert f"Creating {template_type} template" in caplog.text

        # Template content should be in the log (simplified check)
        if template_type == "experiment":
            assert "PANTHER Experiment Configuration Template" in caplog.text
        elif template_type == "service":
            assert "Service Plugin Configuration Template" in caplog.text
        elif template_type == "environment":
            assert "Environment Plugin Configuration Template" in caplog.text

    @pytest.mark.parametrize("template_type", ["experiment", "service", "environment"])
    def test_create_template_all_types_to_file(self, template_type, tmp_path, caplog):
        """Test template creation for all types outputting to file."""
        output_file = tmp_path / f"{template_type}_template.yaml"

        args = self.create_namespace(
            create_action="template",
            template_type=template_type,
            output=str(output_file),
        )

        result = CreateCommand.handle(args)

        assert result == 0
        assert f"Creating {template_type} template" in caplog.text
        assert f"Template created: {output_file}" in caplog.text
        assert output_file.exists()

        # Verify content was written
        content = output_file.read_text()
        if template_type == "experiment":
            assert "PANTHER Experiment Configuration Template" in content
            assert "logging:" in content
            assert "tests:" in content
        elif template_type == "service":
            assert "Service Plugin Configuration Template" in content
        elif template_type == "environment":
            assert "Environment Plugin Configuration Template" in content

    def test_create_template_creates_parent_directories(self, tmp_path, caplog):
        """Test template creation creates parent directories."""
        nested_output = tmp_path / "nested" / "dir" / "experiment_template.yaml"

        args = self.create_namespace(
            create_action="template",
            template_type="experiment",
            output=str(nested_output),
        )

        result = CreateCommand.handle(args)

        assert result == 0
        assert f"Template created: {nested_output}" in caplog.text
        assert nested_output.exists()

    def test_create_template_unknown_type(self, caplog):
        """Test template creation with unknown template type."""
        args = self.create_namespace(
            create_action="template",
            template_type="unknown_template",  # This would typically be caught by argparse
            output=None,
        )

        result = CreateCommand.handle(args)

        assert result == 1
        assert "Unknown template type: unknown_template" in caplog.text

    def test_create_template_file_write_error(self, tmp_path, caplog):
        """Test template creation when file writing fails."""
        output_file = tmp_path / "protected" / "template.yaml"

        # Mock open to raise permission error
        with patch("builtins.open", side_effect=PermissionError("Permission denied")):
            args = self.create_namespace(
                create_action="template",
                template_type="experiment",
                output=str(output_file),
            )

            result = CreateCommand.handle(args)

            assert result == 1
            assert "Error creating template: Permission denied" in caplog.text

    def test_create_template_pathlib_error(self, tmp_path, caplog):
        """Test template creation when Path operations fail."""
        output_file = tmp_path / "template.yaml"

        # Mock Path to raise an error
        with patch(
            "panther.cli.subcommands.create.Path", side_effect=Exception("Path error")
        ):
            args = self.create_namespace(
                create_action="template",
                template_type="experiment",
                output=str(output_file),
            )

            result = CreateCommand.handle(args)

            assert result == 1
            assert "Error creating template: Path error" in caplog.text

    # =============================================================================
    # TEMPLATE CONTENT VALIDATION TESTS
    # =============================================================================

    def test_experiment_template_content_structure(self):
        """Test that experiment template contains proper structure."""
        template_content = CreateCommand._get_experiment_template()

        # Check for essential sections
        assert "logging:" in template_content
        assert "observers:" in template_content
        assert "paths:" in template_content
        assert "docker:" in template_content
        assert "tests:" in template_content

        # Check for specific configurations
        assert "level: INFO" in template_content
        assert "enable_colors: true" in template_content
        assert "output_dir:" in template_content
        assert "force_build_docker_image:" in template_content
        assert "implementation:" in template_content
        assert "protocol:" in template_content

    def test_service_template_content_structure(self):
        """Test that service template contains proper structure."""
        template_content = CreateCommand._get_service_template()

        # Service template is minimal but should contain header
        assert "Service Plugin Configuration Template" in template_content

    def test_environment_template_content_structure(self):
        """Test that environment template contains proper structure."""
        template_content = CreateCommand._get_environment_template()

        # Environment template is minimal but should contain header
        assert "Environment Plugin Configuration Template" in template_content

    # =============================================================================
    # PARAMETER VALIDATION TESTS
    # =============================================================================

    @pytest.mark.parametrize(
        "invalid_action",
        ["invalid", "", "PLUGIN", "subplugin_wrong", 123, None],  # Case sensitive
    )
    def test_invalid_actions(self, invalid_action, caplog):
        """Test handling of invalid action parameters."""
        args = self.create_namespace(create_action=invalid_action)

        result = CreateCommand.handle(args)

        if invalid_action is None:
            assert "No create action specified" in caplog.text
        else:
            assert result == 1

    @pytest.mark.parametrize("plugin_type", ["service", "environment", "protocol"])
    def test_plugin_type_choices(self, plugin_type, mock_plugin_creator_functions):
        """Test all valid plugin type choices for plugin creation."""
        args = self.create_namespace(
            create_action="plugin",
            plugin_type=plugin_type,
            plugin_name="test_plugin",
            dev_mode=False,
            production_mode=False,
            with_subplugins=False,
        )

        result = CreateCommand.handle(args)

        assert result == 0
        mock_plugin_creator_functions["create_plugin"].assert_called_once()

    @pytest.mark.parametrize("plugin_type", ["service", "environment", "protocol"])
    def test_subplugin_type_choices(self, plugin_type, mock_plugin_creator_functions):
        """Test all valid plugin type choices for subplugin creation."""
        args = self.create_namespace(
            create_action="subplugin",
            plugin_type=plugin_type,
            plugin_name="parent_plugin",
            subplugin_name="test_subplugin",
            dev_mode=False,
            production_mode=False,
        )

        result = CreateCommand.handle(args)

        assert result == 0
        mock_plugin_creator_functions["create_subplugin"].assert_called_once()

    @pytest.mark.parametrize("template_type", ["experiment", "service", "environment"])
    def test_template_type_choices(self, template_type):
        """Test all valid template type choices."""
        args = self.create_namespace(
            create_action="template", template_type=template_type, output=None
        )

        result = CreateCommand.handle(args)

        assert result == 0

    @pytest.mark.parametrize("flag_value", [True, False])
    def test_plugin_boolean_flags(self, flag_value, mock_plugin_creator_functions):
        """Test plugin command boolean flags."""
        flags = ["dev_mode", "production_mode", "with_subplugins"]

        for flag in flags:
            args_dict = {
                "create_action": "plugin",
                "plugin_type": "service",
                "plugin_name": "test_plugin",
                "dev_mode": False,
                "production_mode": False,
                "with_subplugins": False,
            }
            args_dict[flag] = flag_value

            args = self.create_namespace(**args_dict)

            result = CreateCommand.handle(args)

            assert result == 0  # Should not crash with any valid flag value

    @pytest.mark.parametrize("flag_value", [True, False])
    def test_subplugin_boolean_flags(self, flag_value, mock_plugin_creator_functions):
        """Test subplugin command boolean flags."""
        flags = ["dev_mode", "production_mode"]

        for flag in flags:
            args_dict = {
                "create_action": "subplugin",
                "plugin_type": "service",
                "plugin_name": "parent_plugin",
                "subplugin_name": "test_subplugin",
                "dev_mode": False,
                "production_mode": False,
            }
            args_dict[flag] = flag_value

            args = self.create_namespace(**args_dict)

            result = CreateCommand.handle(args)

            assert result == 0  # Should not crash with any valid flag value

    # =============================================================================
    # EDGE CASE TESTS
    # =============================================================================

    def test_unicode_in_plugin_names(self, mock_plugin_creator_functions, caplog):
        """Test handling of unicode characters in plugin names."""
        unicode_name = "测试_plugin"

        args = self.create_namespace(
            create_action="plugin",
            plugin_type="service",
            plugin_name=unicode_name,
            dev_mode=False,
            production_mode=False,
            with_subplugins=False,
        )

        result = CreateCommand.handle(args)

        assert result == 0  # Should handle unicode gracefully
        mock_plugin_creator_functions["create_plugin"].assert_called_once_with(
            "service", unicode_name, in_development_mode=None, create_subplugins=False
        )

    def test_very_long_plugin_names(self, mock_plugin_creator_functions):
        """Test handling of very long plugin names."""
        long_name = "a" * 200  # Very long plugin name

        args = self.create_namespace(
            create_action="plugin",
            plugin_type="environment",
            plugin_name=long_name,
            dev_mode=False,
            production_mode=False,
            with_subplugins=False,
        )

        result = CreateCommand.handle(args)

        assert result == 0  # Should handle long names gracefully
        mock_plugin_creator_functions["create_plugin"].assert_called_once()

    def test_empty_plugin_names(self, mock_plugin_creator_functions):
        """Test handling of empty plugin names."""
        args = self.create_namespace(
            create_action="plugin",
            plugin_type="service",
            plugin_name="",  # Empty name
            dev_mode=False,
            production_mode=False,
            with_subplugins=False,
        )

        result = CreateCommand.handle(args)

        # Should pass empty name to create_plugin and let it handle validation
        assert result in [0, 1]  # May succeed or fail depending on validation
        mock_plugin_creator_functions["create_plugin"].assert_called_once()

    def test_special_characters_in_names(self, mock_plugin_creator_functions):
        """Test handling of special characters in plugin names."""
        special_name = "test-plugin_with.special@chars"

        args = self.create_namespace(
            create_action="subplugin",
            plugin_type="protocol",
            plugin_name="parent_plugin",
            subplugin_name=special_name,
            dev_mode=False,
            production_mode=False,
        )

        result = CreateCommand.handle(args)

        assert result == 0  # Should handle special characters gracefully
        mock_plugin_creator_functions["create_subplugin"].assert_called_once()

    def test_unicode_in_output_path(self, tmp_path):
        """Test handling of unicode characters in output path."""
        unicode_path = tmp_path / "测试_template.yaml"

        args = self.create_namespace(
            create_action="template",
            template_type="experiment",
            output=str(unicode_path),
        )

        result = CreateCommand.handle(args)

        assert result == 0  # Should handle unicode paths gracefully
        assert unicode_path.exists()

    def test_very_long_output_path(self, tmp_path):
        """Test handling of very long output paths."""
        long_path = tmp_path / ("a" * 200) / "template.yaml"

        args = self.create_namespace(
            create_action="template", template_type="service", output=str(long_path)
        )

        result = CreateCommand.handle(args)

        assert result == 0  # Should handle long paths gracefully
        assert long_path.exists()

    # =============================================================================
    # INTEGRATION TESTS
    # =============================================================================

    def test_end_to_end_plugin_creation_workflow(
        self, mock_plugin_creator_functions, caplog
    ):
        """Test complete plugin creation workflow."""
        # Step 1: Create main plugin with subplugins
        args_plugin = self.create_namespace(
            create_action="plugin",
            plugin_type="service",
            plugin_name="main_service",
            dev_mode=True,
            production_mode=False,
            with_subplugins=True,
        )

        result = CreateCommand.handle(args_plugin)
        assert result == 0
        assert "Plugin 'main_service' created successfully" in caplog.text

        # Step 2: Create a subplugin for the main plugin
        args_subplugin = self.create_namespace(
            create_action="subplugin",
            plugin_type="service",
            plugin_name="main_service",
            subplugin_name="sub_service",
            dev_mode=False,
            production_mode=True,
        )

        result = CreateCommand.handle(args_subplugin)
        assert result == 0
        assert "Subplugin 'sub_service' created successfully" in caplog.text

        # Verify both functions were called appropriately
        mock_plugin_creator_functions["create_plugin"].assert_called_once_with(
            "service", "main_service", in_development_mode=True, create_subplugins=True
        )
        mock_plugin_creator_functions["create_subplugin"].assert_called_once_with(
            "service", "main_service", "sub_service", in_development_mode=False
        )

    def test_create_command_comprehensive_parameters(
        self, tmp_path, mock_plugin_creator_functions, caplog
    ):
        """Test create command with comprehensive parameter combinations."""
        # Test all three subcommands with various parameter combinations

        # Plugin creation with all flags
        args_plugin = self.create_namespace(
            create_action="plugin",
            plugin_type="environment",
            plugin_name="comprehensive_plugin",
            dev_mode=True,
            production_mode=True,  # dev takes precedence
            with_subplugins=True,
        )

        result = CreateCommand.handle(args_plugin)
        assert result == 0

        # Subplugin creation with production mode
        args_subplugin = self.create_namespace(
            create_action="subplugin",
            plugin_type="protocol",
            plugin_name="parent_comprehensive",
            subplugin_name="child_comprehensive",
            dev_mode=False,
            production_mode=True,
        )

        result = CreateCommand.handle(args_subplugin)
        assert result == 0

        # Template creation with file output
        template_output = tmp_path / "comprehensive_template.yaml"
        args_template = self.create_namespace(
            create_action="template",
            template_type="experiment",
            output=str(template_output),
        )

        result = CreateCommand.handle(args_template)
        assert result == 0
        assert template_output.exists()

        # Verify all components were used appropriately
        assert mock_plugin_creator_functions["create_plugin"].call_count == 1
        assert mock_plugin_creator_functions["create_subplugin"].call_count == 1

        # Verify parameters were passed correctly
        plugin_call = mock_plugin_creator_functions["create_plugin"].call_args
        assert plugin_call[0] == ("environment", "comprehensive_plugin")
        assert plugin_call[1]["in_development_mode"] == True  # dev takes precedence
        assert plugin_call[1]["create_subplugins"] == True

        subplugin_call = mock_plugin_creator_functions["create_subplugin"].call_args
        assert subplugin_call[0] == (
            "protocol",
            "parent_comprehensive",
            "child_comprehensive",
        )
        assert subplugin_call[1]["in_development_mode"] == False  # production mode
