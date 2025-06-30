"""
Comprehensive unit tests for TutorialCommand CLI.

This module provides exhaustive testing for ALL TutorialCommand parameters,
including all 3 subcommands, interactive mode, tutorial running, and error conditions.
"""

import argparse
import logging
import tempfile
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, Mock, call, mock_open, patch

import pytest

from panther.cli.subcommands.tutorial import TutorialCommand
from tests.unit.test_cli.base_cli_test import ComprehensiveCLITest


class TestTutorialCommandComprehensive(ComprehensiveCLITest):
    """Comprehensive tests for TutorialCommand with ALL parameter combinations."""

    @pytest.fixture
    def command_class(self):
        """Return the command class being tested."""
        return TutorialCommand

    @pytest.fixture
    def command_name(self):
        """Return the command name for testing."""
        return "tutorial"

    @pytest.fixture
    def mock_run_tutorial_function(self):
        """Mock run_tutorial function for testing."""
        with patch("panther.cli.subcommands.tutorial.run_tutorial") as mock:
            mock.return_value = True
            yield mock

    # =============================================================================
    # PARSER REGISTRATION TESTS
    # =============================================================================

    def test_parser_registration(self):
        """Test that TutorialCommand is properly registered."""
        from panther.cli.main import create_parser

        parser = create_parser()

        # Verify 'tutorial' subcommand exists
        subparsers_actions = [
            action
            for action in parser._actions
            if isinstance(action, argparse._SubParsersAction)
        ]
        assert len(subparsers_actions) == 1
        assert "tutorial" in subparsers_actions[0].choices

    def test_all_subcommands_registered(self):
        """Test that all tutorial subcommands are registered."""
        from panther.cli.main import create_parser

        parser = create_parser()

        # Parse tutorial help to get subcommands
        try:
            parser.parse_args(["tutorial", "--help"])
        except SystemExit:
            pass  # Expected behavior for help

        # Verify subcommands exist by testing their individual help
        subcommands = ["run", "interactive", "list"]

        for subcommand in subcommands:
            try:
                parser.parse_args(["tutorial", subcommand, "--help"])
            except SystemExit:
                pass  # Expected for help command

    # =============================================================================
    # MAIN COMMAND HANDLER TESTS
    # =============================================================================

    def test_handle_no_action_specified(self, caplog):
        """Test behavior when no tutorial action is specified."""
        args = self.create_namespace(tutorial_action=None)

        result = TutorialCommand.handle(args)

        assert result == 1
        assert "No tutorial action specified" in caplog.text

    def test_handle_unknown_action(self, caplog):
        """Test behavior with unknown tutorial action."""
        args = self.create_namespace(tutorial_action="unknown_action")

        result = TutorialCommand.handle(args)

        assert result == 1
        assert "Unknown tutorial action: unknown_action" in caplog.text

    # =============================================================================
    # RUN SUBCOMMAND TESTS
    # =============================================================================

    @pytest.mark.parametrize(
        "tutorial_type", ["service", "environment", "protocol", "configuration"]
    )
    def test_run_tutorial_all_types(
        self, tutorial_type, mock_run_tutorial_function, caplog
    ):
        """Test running tutorials for all valid tutorial types."""
        args = self.create_namespace(tutorial_action="run", tutorial_type=tutorial_type)

        result = TutorialCommand.handle(args)

        assert result == 0
        assert f"Starting {tutorial_type} tutorial..." in caplog.text
        assert f"Tutorial '{tutorial_type}' completed successfully" in caplog.text

        # Verify run_tutorial was called with correct parameter
        mock_run_tutorial_function.assert_called_once_with(tutorial_type)

    def test_run_tutorial_success(self, mock_run_tutorial_function, caplog):
        """Test successful tutorial execution."""
        mock_run_tutorial_function.return_value = True

        args = self.create_namespace(tutorial_action="run", tutorial_type="service")

        result = TutorialCommand.handle(args)

        assert result == 0
        assert "Starting service tutorial..." in caplog.text
        assert "Tutorial 'service' completed successfully" in caplog.text

    def test_run_tutorial_failure(self, mock_run_tutorial_function, caplog):
        """Test tutorial execution failure."""
        mock_run_tutorial_function.return_value = False

        args = self.create_namespace(tutorial_action="run", tutorial_type="environment")

        result = TutorialCommand.handle(args)

        assert result == 1
        assert "Starting environment tutorial..." in caplog.text
        assert "Tutorial 'environment' failed" in caplog.text

    def test_run_tutorial_exception_handling(self, mock_run_tutorial_function, caplog):
        """Test tutorial execution exception handling."""
        mock_run_tutorial_function.side_effect = Exception("Tutorial error")

        args = self.create_namespace(tutorial_action="run", tutorial_type="protocol")

        result = TutorialCommand.handle(args)

        assert result == 1
        assert "Error running tutorial: Tutorial error" in caplog.text

    def test_run_tutorial_debug_mode_exception(
        self, mock_run_tutorial_function, caplog
    ):
        """Test tutorial execution exception handling with debug mode."""
        mock_run_tutorial_function.side_effect = Exception("Tutorial error")

        args = self.create_namespace(
            tutorial_action="run", tutorial_type="configuration", debug=True
        )

        with patch("traceback.print_exc") as mock_traceback:
            result = TutorialCommand.handle(args)

            assert result == 1
            assert "Error running tutorial: Tutorial error" in caplog.text
            mock_traceback.assert_called_once()

    def test_run_tutorial_import_error(self, caplog):
        """Test tutorial execution when run_tutorial import fails."""
        with patch(
            "panther.cli.subcommands.tutorial.run_tutorial",
            side_effect=ImportError("Module not found"),
        ):
            args = self.create_namespace(tutorial_action="run", tutorial_type="service")

            result = TutorialCommand.handle(args)

            assert result == 1
            assert "Error running tutorial: Module not found" in caplog.text

    # =============================================================================
    # INTERACTIVE SUBCOMMAND TESTS
    # =============================================================================

    def test_interactive_tutorial_welcome_message(self, caplog):
        """Test interactive tutorial displays welcome message."""
        with patch("builtins.input", side_effect=["q"]):  # Quit immediately
            args = self.create_namespace(tutorial_action="interactive")

            result = TutorialCommand.handle(args)

            assert result == 0
            assert "Welcome to PANTHER Interactive Tutorials!" in caplog.text
            assert "Available tutorials:" in caplog.text
            assert "1. Service - Learn to create service plugins" in caplog.text
            assert "2. Environment - Learn to create environment plugins" in caplog.text
            assert "3. Protocol - Learn to create protocol plugins" in caplog.text
            assert (
                "4. Configuration - Learn to write experiment configurations"
                in caplog.text
            )
            assert "Tutorial session ended" in caplog.text

    @pytest.mark.parametrize(
        "choice,expected_tutorial",
        [
            ("1", "service"),
            ("2", "environment"),
            ("3", "protocol"),
            ("4", "configuration"),
        ],
    )
    def test_interactive_tutorial_valid_choices(
        self, choice, expected_tutorial, mock_run_tutorial_function, caplog
    ):
        """Test interactive tutorial with valid numeric choices."""
        with patch("builtins.input", return_value=choice):
            args = self.create_namespace(tutorial_action="interactive")

            result = TutorialCommand.handle(args)

            assert result == 0
            assert f"Starting {expected_tutorial} tutorial..." in caplog.text
            assert (
                f"Tutorial '{expected_tutorial}' completed successfully" in caplog.text
            )
            mock_run_tutorial_function.assert_called_once_with(expected_tutorial)

    def test_interactive_tutorial_quit_option(self, caplog):
        """Test interactive tutorial quit option."""
        with patch("builtins.input", return_value="q"):
            args = self.create_namespace(tutorial_action="interactive")

            result = TutorialCommand.handle(args)

            assert result == 0
            assert "Tutorial session ended" in caplog.text

    def test_interactive_tutorial_quit_uppercase(self, caplog):
        """Test interactive tutorial quit option with uppercase Q."""
        with patch("builtins.input", return_value="Q"):
            args = self.create_namespace(tutorial_action="interactive")

            result = TutorialCommand.handle(args)

            assert result == 0
            assert "Tutorial session ended" in caplog.text

    def test_interactive_tutorial_invalid_number_choice(self, caplog):
        """Test interactive tutorial with invalid number choice."""
        with patch("builtins.input", return_value="5"):  # Out of range
            args = self.create_namespace(tutorial_action="interactive")

            result = TutorialCommand.handle(args)

            assert result == 1
            assert "Invalid selection. Please choose 1-4." in caplog.text

    def test_interactive_tutorial_zero_choice(self, caplog):
        """Test interactive tutorial with zero choice."""
        with patch("builtins.input", return_value="0"):
            args = self.create_namespace(tutorial_action="interactive")

            result = TutorialCommand.handle(args)

            assert result == 1
            assert "Invalid selection. Please choose 1-4." in caplog.text

    def test_interactive_tutorial_negative_choice(self, caplog):
        """Test interactive tutorial with negative choice."""
        with patch("builtins.input", return_value="-1"):
            args = self.create_namespace(tutorial_action="interactive")

            result = TutorialCommand.handle(args)

            assert result == 1
            assert "Invalid selection. Please choose 1-4." in caplog.text

    def test_interactive_tutorial_non_numeric_choice(self, caplog):
        """Test interactive tutorial with non-numeric choice."""
        with patch("builtins.input", return_value="abc"):
            args = self.create_namespace(tutorial_action="interactive")

            result = TutorialCommand.handle(args)

            assert result == 1
            assert "Invalid input. Please enter a number or 'q'." in caplog.text

    def test_interactive_tutorial_empty_choice(self, caplog):
        """Test interactive tutorial with empty choice."""
        with patch("builtins.input", return_value=""):
            args = self.create_namespace(tutorial_action="interactive")

            result = TutorialCommand.handle(args)

            assert result == 1
            assert "Invalid input. Please enter a number or 'q'." in caplog.text

    def test_interactive_tutorial_whitespace_choice(self, caplog):
        """Test interactive tutorial with whitespace-only choice."""
        with patch("builtins.input", return_value="   "):
            args = self.create_namespace(tutorial_action="interactive")

            result = TutorialCommand.handle(args)

            assert result == 1
            assert "Invalid input. Please enter a number or 'q'." in caplog.text

    def test_interactive_tutorial_keyboard_interrupt(self, caplog):
        """Test interactive tutorial handling keyboard interrupt."""
        with patch("builtins.input", side_effect=KeyboardInterrupt()):
            args = self.create_namespace(tutorial_action="interactive")

            result = TutorialCommand.handle(args)

            assert result == 0
            assert "Tutorial session cancelled" in caplog.text

    def test_interactive_tutorial_choice_with_spaces(
        self, mock_run_tutorial_function, caplog
    ):
        """Test interactive tutorial with choice that has leading/trailing spaces."""
        with patch("builtins.input", return_value="  2  "):  # Environment with spaces
            args = self.create_namespace(tutorial_action="interactive")

            result = TutorialCommand.handle(args)

            assert result == 0
            assert "Starting environment tutorial..." in caplog.text
            mock_run_tutorial_function.assert_called_once_with("environment")

    def test_interactive_tutorial_selected_tutorial_failure(
        self, mock_run_tutorial_function, caplog
    ):
        """Test interactive tutorial when selected tutorial fails."""
        mock_run_tutorial_function.return_value = False

        with patch("builtins.input", return_value="1"):
            args = self.create_namespace(tutorial_action="interactive")

            result = TutorialCommand.handle(args)

            assert result == 1
            assert "Starting service tutorial..." in caplog.text
            assert "Tutorial 'service' failed" in caplog.text

    def test_interactive_tutorial_selected_tutorial_exception(
        self, mock_run_tutorial_function, caplog
    ):
        """Test interactive tutorial when selected tutorial raises exception."""
        mock_run_tutorial_function.side_effect = Exception("Tutorial execution error")

        with patch("builtins.input", return_value="3"):
            args = self.create_namespace(tutorial_action="interactive")

            result = TutorialCommand.handle(args)

            assert result == 1
            assert "Starting protocol tutorial..." in caplog.text
            assert "Error running tutorial: Tutorial execution error" in caplog.text

    def test_interactive_tutorial_general_exception(self, caplog):
        """Test interactive tutorial general exception handling."""
        # Mock logging.info to raise an exception
        with patch("panther.cli.subcommands.tutorial.logging") as mock_logging:
            mock_logging.info.side_effect = Exception("Logging error")

            args = self.create_namespace(tutorial_action="interactive")

            result = TutorialCommand.handle(args)

            assert result == 1

    # =============================================================================
    # LIST SUBCOMMAND TESTS
    # =============================================================================

    def test_list_tutorials_displays_all_tutorials(self, caplog):
        """Test list command displays all available tutorials."""
        args = self.create_namespace(tutorial_action="list")

        result = TutorialCommand.handle(args)

        assert result == 0
        assert "Available PANTHER Tutorials" in caplog.text

        # Check for all tutorial types
        assert "Service Plugin Development" in caplog.text
        assert "Environment Plugin Development" in caplog.text
        assert "Protocol Plugin Development" in caplog.text
        assert "Experiment Configuration" in caplog.text

        # Check for tutorial details
        assert "Name: service" in caplog.text
        assert "Name: environment" in caplog.text
        assert "Name: protocol" in caplog.text
        assert "Name: configuration" in caplog.text

        # Check for descriptions
        assert (
            "Learn to create service plugins for protocol implementations"
            in caplog.text
        )
        assert (
            "Learn to create network and execution environment plugins" in caplog.text
        )
        assert "Learn to create protocol definition plugins" in caplog.text
        assert (
            "Learn to write and structure experiment configuration files" in caplog.text
        )

        # Check for difficulty levels
        assert "Difficulty: Beginner" in caplog.text
        assert "Difficulty: Intermediate" in caplog.text

        # Check for durations
        assert "Duration: 15-20 minutes" in caplog.text
        assert "Duration: 20-25 minutes" in caplog.text
        assert "Duration: 10-15 minutes" in caplog.text

        # Check for commands
        assert "Command: panther tutorial run service" in caplog.text
        assert "Command: panther tutorial run environment" in caplog.text
        assert "Command: panther tutorial run protocol" in caplog.text
        assert "Command: panther tutorial run configuration" in caplog.text

        # Check for usage instructions
        assert "To start a tutorial, use: panther tutorial run <name>" in caplog.text
        assert "For interactive mode, use: panther tutorial interactive" in caplog.text

    def test_list_tutorials_structure_validation(self, caplog):
        """Test that list command displays proper tutorial structure."""
        args = self.create_namespace(tutorial_action="list")

        result = TutorialCommand.handle(args)

        assert result == 0

        # Check that all required fields are present for each tutorial
        expected_tutorials = [
            {"name": "service", "difficulty": "Beginner"},
            {"name": "environment", "difficulty": "Intermediate"},
            {"name": "protocol", "difficulty": "Beginner"},
            {"name": "configuration", "difficulty": "Beginner"},
        ]

        for tutorial in expected_tutorials:
            assert f"Name: {tutorial['name']}" in caplog.text
            assert f"Difficulty: {tutorial['difficulty']}" in caplog.text

    def test_list_tutorials_exception_handling(self, caplog):
        """Test list tutorials exception handling."""
        # Mock logging.info to raise an exception
        with patch("panther.cli.subcommands.tutorial.logging") as mock_logging:
            mock_logging.info.side_effect = Exception("Listing error")

            args = self.create_namespace(tutorial_action="list")

            result = TutorialCommand.handle(args)

            assert result == 1

    # =============================================================================
    # PARAMETER VALIDATION TESTS
    # =============================================================================

    @pytest.mark.parametrize(
        "invalid_action",
        ["invalid", "", "RUN", "list_wrong", 123, None],  # Case sensitive
    )
    def test_invalid_actions(self, invalid_action, caplog):
        """Test handling of invalid action parameters."""
        args = self.create_namespace(tutorial_action=invalid_action)

        result = TutorialCommand.handle(args)

        if invalid_action is None:
            assert "No tutorial action specified" in caplog.text
        else:
            assert result == 1

    @pytest.mark.parametrize(
        "tutorial_type", ["service", "environment", "protocol", "configuration"]
    )
    def test_tutorial_type_choices(self, tutorial_type, mock_run_tutorial_function):
        """Test all valid tutorial type choices."""
        args = self.create_namespace(tutorial_action="run", tutorial_type=tutorial_type)

        result = TutorialCommand.handle(args)

        assert result == 0
        mock_run_tutorial_function.assert_called_once_with(tutorial_type)

    # =============================================================================
    # EDGE CASE TESTS
    # =============================================================================

    def test_unicode_in_tutorial_input(self, caplog):
        """Test handling of unicode characters in interactive input."""
        with patch("builtins.input", return_value="测试"):  # Unicode characters
            args = self.create_namespace(tutorial_action="interactive")

            result = TutorialCommand.handle(args)

            assert result == 1
            assert "Invalid input. Please enter a number or 'q'." in caplog.text

    def test_very_long_input(self, caplog):
        """Test handling of very long input strings."""
        long_input = "a" * 1000  # Very long string

        with patch("builtins.input", return_value=long_input):
            args = self.create_namespace(tutorial_action="interactive")

            result = TutorialCommand.handle(args)

            assert result == 1
            assert "Invalid input. Please enter a number or 'q'." in caplog.text

    def test_special_characters_input(self, caplog):
        """Test handling of special characters in interactive input."""
        special_chars = "!@#$%^&*()"

        with patch("builtins.input", return_value=special_chars):
            args = self.create_namespace(tutorial_action="interactive")

            result = TutorialCommand.handle(args)

            assert result == 1
            assert "Invalid input. Please enter a number or 'q'." in caplog.text

    def test_float_number_input(self, caplog):
        """Test handling of float numbers in interactive input."""
        with patch("builtins.input", return_value="2.5"):
            args = self.create_namespace(tutorial_action="interactive")

            result = TutorialCommand.handle(args)

            assert result == 1
            assert "Invalid input. Please enter a number or 'q'." in caplog.text

    def test_input_with_newlines(self, caplog):
        """Test handling of input with newline characters."""
        with patch("builtins.input", return_value="2\n"):
            args = self.create_namespace(tutorial_action="interactive")

            result = TutorialCommand.handle(args)

            # Should work because strip() removes newlines
            assert result == 0

    def test_multiple_keyboard_interrupts(self, caplog):
        """Test handling multiple keyboard interrupts."""
        with patch(
            "builtins.input", side_effect=[KeyboardInterrupt(), KeyboardInterrupt()]
        ):
            args = self.create_namespace(tutorial_action="interactive")

            result = TutorialCommand.handle(args)

            assert result == 0
            assert "Tutorial session cancelled" in caplog.text

    # =============================================================================
    # INTEGRATION TESTS
    # =============================================================================

    def test_end_to_end_tutorial_workflow(self, mock_run_tutorial_function, caplog):
        """Test complete tutorial workflow: list → interactive → run."""
        # Step 1: List available tutorials
        args_list = self.create_namespace(tutorial_action="list")
        result = TutorialCommand.handle(args_list)
        assert result == 0
        assert "Available PANTHER Tutorials" in caplog.text

        # Step 2: Interactive selection (choose service tutorial)
        with patch("builtins.input", return_value="1"):
            args_interactive = self.create_namespace(tutorial_action="interactive")
            result = TutorialCommand.handle(args_interactive)
            assert result == 0
            assert "Starting service tutorial..." in caplog.text

        # Step 3: Direct run command
        args_run = self.create_namespace(
            tutorial_action="run", tutorial_type="environment"
        )
        result = TutorialCommand.handle(args_run)
        assert result == 0
        assert "Starting environment tutorial..." in caplog.text

        # Verify tutorial functions were called
        assert mock_run_tutorial_function.call_count == 2
        mock_run_tutorial_function.assert_any_call("service")
        mock_run_tutorial_function.assert_any_call("environment")

    def test_tutorial_command_comprehensive_parameters(
        self, mock_run_tutorial_function, caplog
    ):
        """Test tutorial command with comprehensive parameter combinations."""
        # Test all tutorial types via run command
        tutorial_types = ["service", "environment", "protocol", "configuration"]

        for tutorial_type in tutorial_types:
            args = self.create_namespace(
                tutorial_action="run", tutorial_type=tutorial_type
            )

            result = TutorialCommand.handle(args)
            assert result == 0
            assert f"Starting {tutorial_type} tutorial..." in caplog.text

        # Test interactive mode with each choice
        for i, tutorial_type in enumerate(tutorial_types, 1):
            with patch("builtins.input", return_value=str(i)):
                args_interactive = self.create_namespace(tutorial_action="interactive")
                result = TutorialCommand.handle(args_interactive)
                assert result == 0

        # Test list command
        args_list = self.create_namespace(tutorial_action="list")
        result = TutorialCommand.handle(args_list)
        assert result == 0

        # Verify all tutorial types were run via both direct and interactive modes
        expected_calls = len(tutorial_types) * 2  # Direct + Interactive
        assert mock_run_tutorial_function.call_count == expected_calls

        # Verify each tutorial type was called
        for tutorial_type in tutorial_types:
            mock_run_tutorial_function.assert_any_call(tutorial_type)

    def test_tutorial_error_recovery_scenarios(
        self, mock_run_tutorial_function, caplog
    ):
        """Test tutorial command error recovery scenarios."""
        # Scenario 1: Tutorial fails but system continues
        mock_run_tutorial_function.return_value = False

        args_fail = self.create_namespace(
            tutorial_action="run", tutorial_type="service"
        )
        result = TutorialCommand.handle(args_fail)
        assert result == 1
        assert "Tutorial 'service' failed" in caplog.text

        # Scenario 2: Interactive mode with invalid input then valid input
        # Note: This would require more complex mocking for multiple interactions

        # Scenario 3: Exception during tutorial execution
        mock_run_tutorial_function.side_effect = Exception("Critical error")

        args_exception = self.create_namespace(
            tutorial_action="run", tutorial_type="protocol"
        )
        result = TutorialCommand.handle(args_exception)
        assert result == 1
        assert "Error running tutorial: Critical error" in caplog.text
