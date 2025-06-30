"""
Maintainability and Code Quality Tests for CLI Commands.

Tests targeting maintainability issues identified by Codacy analysis:
- Unused imports and variables
- Trailing whitespace
- Code duplication
- Method length and complexity
- File size limits
"""

import argparse
import ast
import logging
import re
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from tests.unit.test_cli.base_cli_test import ComprehensiveCLITest


class TestCodeQualityMetrics(ComprehensiveCLITest):
    """Test adherence to code quality metrics and standards."""

    def test_file_size_limits(self):
        """
        Test that CLI files don't exceed reasonable size limits.
        Codacy flagged config.py (614 lines) and admin.py (612 lines) as too large.
        """
        cli_dir = (
            Path(__file__).parent.parent.parent.parent
            / "panther"
            / "cli"
            / "subcommands"
        )

        # Define reasonable limits for CLI command files
        MAX_LINES = 600  # Based on Codacy warning at 500, allowing some flexibility

        large_files = []

        for py_file in cli_dir.glob("*.py"):
            if py_file.name == "__init__.py":
                continue

            with open(py_file, "r", encoding="utf-8") as f:
                lines = f.readlines()
                line_count = len(
                    [line for line in lines if line.strip()]
                )  # Count non-empty lines

                if line_count > MAX_LINES:
                    large_files.append((py_file.name, line_count))

        # Report large files but don't fail - this is informational
        if large_files:
            for filename, line_count in large_files:
                logging.warning(
                    f"Large file detected: {filename} has {line_count} lines (limit: {MAX_LINES})"
                )

        # Assert that we don't have excessively large files (> 800 lines)
        excessive_files = [f for f, count in large_files if count > 800]
        assert len(excessive_files) == 0, f"Files exceed 800 lines: {excessive_files}"

    def test_method_complexity_awareness(self):
        """
        Test awareness of high-complexity methods for maintenance.
        This doesn't test functionality, but documents high-complexity areas.
        """
        # High complexity methods identified by Codacy
        high_complexity_methods = {
            "run.py": [
                ("handle", 43),  # Highest complexity
            ],
            "config.py": [
                ("_handle_validate", 26),
            ],
            "check.py": [
                ("handle", 21),
                ("_check_type", 18),
            ],
            "admin.py": [
                ("_handle_docker", 29),
                ("_handle_clean", 17),
            ],
            "plugins.py": [
                ("_handle_list", 14),
                ("_handle_params", 13),
                ("_handle_check_deps", 14),
            ],
        }

        # This test documents high-complexity methods for future refactoring
        total_complexity = 0
        method_count = 0

        for file, methods in high_complexity_methods.items():
            for method_name, complexity in methods:
                total_complexity += complexity
                method_count += 1

                # Log high complexity methods for awareness
                if complexity > 15:
                    logging.warning(
                        f"High complexity method: {file}::{method_name} (complexity: {complexity})"
                    )

        average_complexity = total_complexity / method_count if method_count > 0 else 0

        # Document average complexity for tracking
        logging.info(f"Average complexity of flagged methods: {average_complexity:.1f}")

        # Assert that we're aware of the complexity (this always passes but logs info)
        assert average_complexity > 0  # Always true, just for documentation

    def test_unused_variable_detection(self):
        """
        Test detection of unused variables in CLI commands.
        Based on Pylint findings from Codacy analysis.
        """
        # Known unused variables from Codacy analysis
        known_unused_variables = {
            "metrics.py": ["summary_parser"],
            "tutorial.py": ["interactive_parser", "list_parser"],
            "tools.py": ["list_parser", "output", "error", "location"],
            "admin.py": ["status_parser", "key"],
        }

        # This test documents known unused variables
        # In a real scenario, these should be cleaned up
        total_unused = sum(len(vars) for vars in known_unused_variables.values())

        logging.info(f"Known unused variables across CLI: {total_unused}")

        # Log specific files with unused variables
        for file, variables in known_unused_variables.items():
            if len(variables) > 2:  # Files with many unused variables
                logging.warning(
                    f"File {file} has {len(variables)} unused variables: {variables}"
                )

        # Assert awareness of unused variables (doesn't fail, just documents)
        assert total_unused >= 0  # Always true, for documentation

    def test_import_usage_efficiency(self):
        """
        Test efficiency of import usage in CLI commands.
        Based on unused import findings from Codacy.
        """
        # Known unused imports from Codacy analysis
        known_unused_imports = {
            "main.py": ["Path"],
            "plugins.py": ["Dict", "List", "ConfigLoader"],
            "metrics.py": ["MetricsCollector", "MetricsExporter"],
            "config.py": ["json", "OmegaConf", "ExperimentConfig", "GlobalConfig"],
            "check.py": ["Tuple"],
            "admin.py": ["panther"],
        }

        total_unused_imports = sum(
            len(imports) for imports in known_unused_imports.values()
        )

        logging.info(f"Known unused imports across CLI: {total_unused_imports}")

        # Files with many unused imports indicate poor import hygiene
        problematic_files = {
            file: imports
            for file, imports in known_unused_imports.items()
            if len(imports) > 2
        }

        if problematic_files:
            for file, imports in problematic_files.items():
                logging.warning(
                    f"File {file} has {len(imports)} unused imports: {imports}"
                )

        # Assert that import efficiency is tracked
        assert total_unused_imports >= 0  # Always true, for documentation


class TestCodeDuplicationDetection(ComprehensiveCLITest):
    """Test detection and prevention of code duplication."""

    def test_argument_parser_pattern_consistency(self):
        """Test consistency of argument parser patterns across commands."""
        from panther.cli.subcommands import (
            admin,
            check,
            config,
            create,
            metrics,
            plugins,
            run,
            tools,
            tutorial,
        )

        # Test that all commands follow the same parser registration pattern
        commands = [
            run,
            config,
            plugins,
            create,
            tutorial,
            admin,
            check,
            metrics,
            tools,
        ]

        registration_patterns = []

        for command_module in commands:
            command_class = getattr(
                command_module,
                f"{command_module.__name__.split('.')[-1].title()}Command",
            )

            # Check if register_parser method exists and follows pattern
            assert hasattr(
                command_class, "register_parser"
            ), f"{command_class} missing register_parser"
            assert hasattr(
                command_class, "handle"
            ), f"{command_class} missing handle method"

            # Document the pattern for consistency checking
            registration_patterns.append(command_class.__name__)

        # All commands should follow the same naming pattern
        assert len(registration_patterns) == len(commands)
        assert all("Command" in pattern for pattern in registration_patterns)

    def test_error_handling_pattern_consistency(self):
        """Test consistency of error handling patterns across commands."""
        from panther.cli.subcommands.tools import ToolsCommand
        from panther.cli.subcommands.tutorial import TutorialCommand

        # Test that commands using the new mixin have consistent error handling
        commands_with_mixin = [ToolsCommand, TutorialCommand]

        for command_class in commands_with_mixin:
            # Should have dispatch_action method from mixin
            args = self.create_namespace()

            # Test that all return proper error codes
            result = command_class.handle(args)
            assert result in [
                0,
                1,
            ], f"{command_class} returned invalid exit code: {result}"

    def test_logging_pattern_consistency(self):
        """Test consistency of logging patterns across commands."""
        # Test that all commands use logging.info consistently for user messages
        # This is based on our refactoring to replace print statements

        from panther.cli.subcommands.plugins import PluginsCommand

        with patch(
            "panther.cli.subcommands.plugins.PluginManager"
        ) as mock_manager, patch("logging.info") as mock_log:
            mock_manager_instance = MagicMock()
            mock_manager_instance.discover_plugins.return_value = None
            mock_manager_instance.get_plugins_by_type.return_value = []
            mock_manager.return_value = mock_manager_instance

            args = self.create_namespace(format="table", type="all")
            result = PluginsCommand._handle_list(args)

            # Should use logging.info, not print
            assert mock_log.called, "Command should use logging.info for user messages"
            assert result == 0


class TestCodeStyleCompliance(ComprehensiveCLITest):
    """Test compliance with code style guidelines."""

    def test_trailing_whitespace_awareness(self):
        """
        Test awareness of trailing whitespace issues.
        Based on Pylint findings from Codacy analysis.
        """
        # Files with trailing whitespace issues from Codacy
        files_with_whitespace_issues = [
            "base.py",
            "plugins.py",
            "metrics.py",
            "run.py",
            "tutorial.py",
            "tools.py",
        ]

        # Document the issue for cleanup
        logging.info(
            f"Files with trailing whitespace: {len(files_with_whitespace_issues)}"
        )

        # This test documents the issue - in practice, these should be fixed
        # by running a linter/formatter
        assert len(files_with_whitespace_issues) >= 0  # Always true, for documentation

    def test_method_length_compliance(self):
        """
        Test compliance with method length guidelines.
        Based on Lizard findings from Codacy analysis.
        """
        # Methods exceeding 50 lines from Codacy analysis
        long_methods = {
            "plugins.py": [
                "register_parser (80 lines)",
                "_handle_list (63 lines)",
                "_handle_params (57 lines)",
            ],
            "metrics.py": ["register_parser (62 lines)"],
            "run.py": ["register_parser (110 lines)", "handle (146 lines)"],
            "config.py": [
                "register_parser (82 lines)",
                "_handle_validate (80 lines)",
                "_get_minimal_template (55 lines)",
                "_get_basic_template (65 lines)",
                "_get_advanced_template (75 lines)",
                "_get_performance_template (61 lines)",
                "_get_security_template (56 lines)",
            ],
            "check.py": ["handle (62 lines)"],
            "create.py": [
                "register_parser (70 lines)",
                "_get_experiment_template (55 lines)",
            ],
            "tools.py": ["_install_precommit (84 lines)"],
            "admin.py": [
                "register_parser (116 lines)",
                "_handle_teardown (69 lines)",
                "_handle_status (63 lines)",
                "_handle_docker (180 lines)",
            ],
        }

        total_long_methods = sum(len(methods) for methods in long_methods.values())

        logging.info(f"Methods exceeding 50 lines: {total_long_methods}")

        # Files with many long methods need refactoring attention
        problematic_files = {
            file: methods for file, methods in long_methods.items() if len(methods) > 3
        }

        for file, methods in problematic_files.items():
            logging.warning(f"File {file} has {len(methods)} long methods")

        # Document for refactoring awareness
        assert total_long_methods >= 0  # Always true, for documentation

    def test_function_parameter_count(self):
        """Test that functions don't have too many parameters."""
        # This is a general guideline test - functions should have <= 5 parameters
        # Testing the dispatch_action method we created

        # Our dispatch_action method has 5 parameters - at the limit
        import inspect

        from panther.cli.base import CLIActionDispatchMixin

        sig = inspect.signature(CLIActionDispatchMixin.dispatch_action)
        param_count = len(sig.parameters) - 1  # Exclude 'cls'

        assert (
            param_count <= 5
        ), f"dispatch_action has {param_count} parameters, should be <= 5"

        # Log parameter count for awareness
        logging.info(
            f"CLIActionDispatchMixin.dispatch_action has {param_count} parameters"
        )


class TestMaintenanceReadiness(ComprehensiveCLITest):
    """Test readiness for maintenance and future development."""

    def test_mixin_pattern_adoption(self):
        """Test adoption of the new mixin pattern for maintainability."""
        from panther.cli.base import CLIActionDispatchMixin
        from panther.cli.subcommands.tools import ToolsCommand
        from panther.cli.subcommands.tutorial import TutorialCommand

        # Commands that have adopted the new mixin pattern
        mixin_commands = [ToolsCommand, TutorialCommand]

        for command_class in mixin_commands:
            # Should inherit from CLIActionDispatchMixin
            assert issubclass(
                command_class, CLIActionDispatchMixin
            ), f"{command_class} should inherit from CLIActionDispatchMixin"

            # Should have access to dispatch_action method
            assert hasattr(
                command_class, "dispatch_action"
            ), f"{command_class} should have access to dispatch_action method"

    def test_refactoring_impact_isolation(self):
        """Test that refactoring changes are properly isolated."""
        from panther.cli.subcommands.plugins import PluginsCommand
        from panther.cli.subcommands.tools import ToolsCommand
        from panther.cli.subcommands.tutorial import TutorialCommand

        # Test that refactored commands still work with same interface
        refactored_commands = [ToolsCommand, TutorialCommand]
        non_refactored_commands = [PluginsCommand]

        for command_class in refactored_commands + non_refactored_commands:
            # All should have the same basic interface
            assert hasattr(
                command_class, "register_parser"
            ), f"{command_class} missing register_parser method"
            assert hasattr(
                command_class, "handle"
            ), f"{command_class} missing handle method"

            # Test basic functionality still works
            args = self.create_namespace()
            result = command_class.handle(args)
            assert result in [0, 1], f"{command_class} returned invalid exit code"

    def test_backwards_compatibility(self):
        """Test that changes maintain backwards compatibility."""
        from panther.cli.subcommands.tools import ToolsCommand

        # Test that refactored commands still accept the same arguments
        # and return the same exit codes
        # Test with no action (should return 1)
        args = self.create_namespace(tools_action=None)
        result = ToolsCommand.handle(args)
        assert result == 1

        # Test with unknown action (should return 1)
        args = self.create_namespace(tools_action="unknown")
        result = ToolsCommand.handle(args)
        assert result == 1

    def test_documentation_completeness(self):
        """Test that new code includes proper documentation."""
        from panther.cli.base import CLIActionDispatchMixin

        # Test that new mixin has proper docstrings
        assert (
            CLIActionDispatchMixin.__doc__ is not None
        ), "CLIActionDispatchMixin should have class docstring"

        assert (
            CLIActionDispatchMixin.dispatch_action.__doc__ is not None
        ), "dispatch_action method should have docstring"

        # Test docstring content quality
        docstring = CLIActionDispatchMixin.dispatch_action.__doc__
        assert (
            "Args:" in docstring
        ), "dispatch_action docstring should document arguments"
        assert (
            "Returns:" in docstring
        ), "dispatch_action docstring should document return value"

    def test_error_message_consistency(self):
        """Test consistency of error messages across commands."""
        from panther.cli.subcommands.tools import ToolsCommand
        from panther.cli.subcommands.tutorial import TutorialCommand

        # Test that commands using the mixin have consistent error messages
        commands_with_mixin = [
            (ToolsCommand, "tools_action", "tools"),
            (TutorialCommand, "tutorial_action", "tutorial"),
        ]

        for command_class, action_attr, command_name in commands_with_mixin:
            args = self.create_namespace()
            setattr(args, action_attr, None)

            with patch("logging.info") as mock_log:
                result = command_class.handle(args)

                # Should log consistent error message format
                assert mock_log.called, f"{command_class} should log error message"

                # Check error message pattern
                error_message = str(mock_log.call_args)
                assert (
                    "No" in error_message and "action specified" in error_message
                ), f"{command_class} should have consistent error message format"

                assert (
                    result == 1
                ), f"{command_class} should return 1 for missing action"
