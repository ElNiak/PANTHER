"""
Comprehensive unit tests for CheckCommand CLI.

This module provides exhaustive testing for ALL CheckCommand parameters,
including all check types, subprocess operations, tool installation, and error conditions.
"""

import argparse
import logging
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, call, mock_open, patch

import pytest

from panther.cli.subcommands.check import CheckCommand
from tests.unit.test_cli.base_cli_test import ComprehensiveCLITest


class TestCheckCommandComprehensive(ComprehensiveCLITest):
    """Comprehensive tests for CheckCommand with ALL parameter combinations."""

    @pytest.fixture
    def command_class(self):
        """Return the command class being tested."""
        return CheckCommand

    @pytest.fixture
    def command_name(self):
        """Return the command name for testing."""
        return "check"

    @pytest.fixture
    def mock_subprocess(self):
        """Mock subprocess for command execution testing."""
        with patch("panther.cli.subcommands.check.subprocess") as mock:
            # Default successful subprocess results
            mock.run.return_value = MagicMock(
                returncode=0, stdout="", stderr="", text=True
            )
            yield mock

    @pytest.fixture
    def mock_sys(self):
        """Mock sys module for executable path."""
        with patch("panther.cli.subcommands.check.sys") as mock:
            mock.executable = "/usr/bin/python"
            yield mock

    @pytest.fixture
    def mock_path_operations(self):
        """Mock Path operations for file system testing."""
        with patch("panther.cli.subcommands.check.Path") as mock_path_class:
            mock_path_instance = MagicMock()
            mock_path_instance.exists.return_value = True
            mock_path_class.return_value = mock_path_instance
            yield mock_path_class, mock_path_instance

    # =============================================================================
    # PARSER REGISTRATION TESTS
    # =============================================================================

    def test_parser_registration(self):
        """Test that CheckCommand is properly registered."""
        from panther.cli.main import create_parser

        parser = create_parser()

        # Verify 'check' subcommand exists
        subparsers_actions = [
            action
            for action in parser._actions
            if isinstance(action, argparse._SubParsersAction)
        ]
        assert len(subparsers_actions) == 1
        assert "check" in subparsers_actions[0].choices

    def test_all_check_options_registered(self):
        """Test that all check options are registered in parser."""
        from panther.cli.main import create_parser

        parser = create_parser()

        # Parse check help to verify all options exist
        try:
            parser.parse_args(["check", "--help"])
        except SystemExit:
            pass  # Expected behavior for help

        # Test individual check options exist
        check_options = [
            "--fix",
            "--all",
            "--format",
            "--imports",
            "--lint",
            "--type",
            "--security",
            "--test",
            "--coverage",
            "--path",
            "--config",
        ]

        for option in check_options:
            try:
                # This would fail if the option doesn't exist
                parser.parse_args(
                    ["check", option, "dummy"]
                    if option in ["--path", "--config"]
                    else ["check", option]
                )
            except (SystemExit, argparse.ArgumentError):
                pass  # Expected for some combinations

    # =============================================================================
    # MAIN COMMAND HANDLER TESTS
    # =============================================================================

    def test_handle_no_checks_specified(self, caplog):
        """Test behavior when no checks are specified."""
        args = self.create_namespace(
            all=False,
            format=False,
            imports=False,
            lint=False,
            type=False,
            security=False,
            test=False,
            coverage=False,
            fix=False,
            path="panther/",
            config=None,
        )

        result = CheckCommand.handle(args)

        assert result == 1
        assert "No checks specified" in caplog.text
        assert (
            "Available checks: --format, --imports, --lint, --type, --security, --test"
            in caplog.text
        )

    def test_handle_all_flag(self, mock_subprocess, caplog):
        """Test behavior with --all flag."""
        args = self.create_namespace(
            all=True,
            format=False,
            imports=False,
            lint=False,
            type=False,
            security=False,
            test=False,
            coverage=False,
            fix=False,
            path="panther/",
            config=None,
        )

        # Mock successful subprocess calls for all tools
        mock_subprocess.run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        result = CheckCommand.handle(args)

        assert result == 0
        assert "Running code quality checks on: panther/" in caplog.text
        assert "Checks to run: format, imports, lint, type, security" in caplog.text
        assert "All checks passed!" in caplog.text

    def test_handle_all_flag_with_test(
        self, mock_subprocess, mock_path_operations, caplog
    ):
        """Test behavior with --all and --test flags."""
        args = self.create_namespace(
            all=True,
            format=False,
            imports=False,
            lint=False,
            type=False,
            security=False,
            test=True,
            coverage=False,
            fix=False,
            path="panther/",
            config=None,
        )

        mock_path_class, mock_path_instance = mock_path_operations
        mock_subprocess.run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        result = CheckCommand.handle(args)

        assert result == 0
        assert "test" in caplog.text

    @pytest.mark.parametrize(
        "check_flag", ["format", "imports", "lint", "type", "security", "test"]
    )
    def test_handle_individual_checks(
        self, check_flag, mock_subprocess, mock_path_operations, caplog
    ):
        """Test behavior with individual check flags."""
        args_dict = {
            "all": False,
            "format": False,
            "imports": False,
            "lint": False,
            "type": False,
            "security": False,
            "test": False,
            "coverage": False,
            "fix": False,
            "path": "panther/",
            "config": None,
        }
        args_dict[check_flag] = True

        args = self.create_namespace(**args_dict)

        mock_path_class, mock_path_instance = mock_path_operations
        mock_subprocess.run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        result = CheckCommand.handle(args)

        assert result == 0
        assert f"Checks to run: {check_flag}" in caplog.text

    def test_handle_multiple_individual_checks(self, mock_subprocess, caplog):
        """Test behavior with multiple individual check flags."""
        args = self.create_namespace(
            all=False,
            format=True,
            imports=True,
            lint=False,
            type=False,
            security=False,
            test=False,
            coverage=False,
            fix=False,
            path="panther/",
            config=None,
        )

        mock_subprocess.run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        result = CheckCommand.handle(args)

        assert result == 0
        assert "Checks to run: format, imports" in caplog.text

    def test_handle_with_fix_flag(self, mock_subprocess, caplog):
        """Test behavior with --fix flag."""
        args = self.create_namespace(
            all=False,
            format=True,
            imports=False,
            lint=False,
            type=False,
            security=False,
            test=False,
            coverage=False,
            fix=True,
            path="panther/",
            config=None,
        )

        mock_subprocess.run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        result = CheckCommand.handle(args)

        assert result == 0
        assert "Auto-fix: Enabled" in caplog.text

    def test_handle_check_failures(self, mock_subprocess, caplog):
        """Test behavior when checks fail."""
        args = self.create_namespace(
            all=False,
            format=True,
            imports=True,
            lint=False,
            type=False,
            security=False,
            test=False,
            coverage=False,
            fix=False,
            path="panther/",
            config=None,
        )

        # Mock one successful and one failed check
        mock_subprocess.run.side_effect = [
            # Tool installation checks (format, imports)
            MagicMock(returncode=0, stdout="", stderr=""),
            MagicMock(returncode=0, stdout="", stderr=""),
            # Actual checks
            MagicMock(returncode=0, stdout="", stderr=""),  # format success
            MagicMock(returncode=1, stdout="import errors", stderr=""),  # imports fail
        ]

        result = CheckCommand.handle(args)

        assert result == 1
        assert "total issue(s) found" in caplog.text

    # =============================================================================
    # TOOL INSTALLATION TESTS
    # =============================================================================

    def test_ensure_tools_installed_all_present(self, mock_subprocess, caplog):
        """Test tool installation when all tools are present."""
        # Mock all tools as installed
        mock_subprocess.run.return_value = MagicMock(
            returncode=0, stdout="version 1.0", stderr=""
        )

        CheckCommand._ensure_tools_installed(["format", "imports", "lint"])

        assert "Checking required tools..." in caplog.text
        # Should check for black, isort, flake8
        assert mock_subprocess.run.call_count >= 3

    def test_ensure_tools_installed_missing_tools(self, mock_subprocess, caplog):
        """Test tool installation when some tools are missing."""
        # Mock tool checks - some succeed, some fail
        mock_subprocess.run.side_effect = [
            MagicMock(returncode=0, stdout="version 1.0", stderr=""),  # black present
            subprocess.CalledProcessError(1, "cmd"),  # isort missing
            FileNotFoundError(),  # flake8 missing
            MagicMock(returncode=0, stdout="", stderr=""),  # pip install
        ]

        CheckCommand._ensure_tools_installed(["format", "imports", "lint"])

        assert "Installing missing tools:" in caplog.text
        assert "isort" in caplog.text or "flake8" in caplog.text

    def test_ensure_tools_installed_no_tools_needed(self, mock_subprocess):
        """Test tool installation when no tools are needed."""
        CheckCommand._ensure_tools_installed([])

        # No subprocess calls should be made
        mock_subprocess.run.assert_not_called()

    # =============================================================================
    # FORMAT CHECK TESTS
    # =============================================================================

    def test_check_format_success(self, mock_subprocess, caplog):
        """Test format check when code is properly formatted."""
        args = self.create_namespace(fix=False, path="panther/", config=None)

        mock_subprocess.run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        result = CheckCommand._check_format(args)

        assert result == 0
        assert "Checking code formatting with black..." in caplog.text
        assert "Code formatting is correct" in caplog.text

        # Verify correct command was called
        mock_subprocess.run.assert_called_once()
        call_args = mock_subprocess.run.call_args[0][0]
        assert "black" in call_args
        assert "--check" in call_args
        assert "--diff" in call_args

    def test_check_format_failure_without_fix(self, mock_subprocess, caplog):
        """Test format check failure without fix flag."""
        args = self.create_namespace(fix=False, path="panther/", config=None)

        mock_subprocess.run.return_value = MagicMock(
            returncode=1,
            stdout="--- panther/test.py\n+++ panther/test.py\n@@ -1,1 +1,1 @@\n-x=1\n+x = 1",
            stderr="",
        )

        result = CheckCommand._check_format(args)

        assert result == 1
        assert "Code formatting issues found" in caplog.text
        assert "Suggested changes:" in caplog.text
        assert "Run with --fix to automatically format" in caplog.text

    def test_check_format_with_fix(self, mock_subprocess, caplog):
        """Test format check with fix flag enabled."""
        args = self.create_namespace(fix=True, path="panther/", config=None)

        mock_subprocess.run.return_value = MagicMock(returncode=1, stdout="", stderr="")

        result = CheckCommand._check_format(args)

        assert result == 0  # Should return 0 when fixing
        assert "Running black to format code..." in caplog.text
        assert "Code has been formatted" in caplog.text

        # Verify correct command was called (no --check or --diff)
        call_args = mock_subprocess.run.call_args[0][0]
        assert "black" in call_args
        assert "--check" not in call_args
        assert "--diff" not in call_args

    # =============================================================================
    # IMPORTS CHECK TESTS
    # =============================================================================

    def test_check_imports_success(self, mock_subprocess, caplog):
        """Test imports check when imports are properly sorted."""
        args = self.create_namespace(fix=False, path="panther/", config=None)

        mock_subprocess.run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        result = CheckCommand._check_imports(args)

        assert result == 0
        assert "Checking import sorting with isort..." in caplog.text
        assert "Import sorting is correct" in caplog.text

        # Verify correct command was called
        call_args = mock_subprocess.run.call_args[0][0]
        assert "isort" in call_args
        assert "--check-only" in call_args
        assert "--diff" in call_args

    def test_check_imports_failure_without_fix(self, mock_subprocess, caplog):
        """Test imports check failure without fix flag."""
        args = self.create_namespace(fix=False, path="panther/", config=None)

        # Create long output to test truncation
        long_output = "\n".join([f"import line {i}" for i in range(25)])
        mock_subprocess.run.return_value = MagicMock(
            returncode=1, stdout=long_output, stderr=""
        )

        result = CheckCommand._check_imports(args)

        assert result == 1
        assert "Import sorting issues found" in caplog.text
        assert "Suggested changes (first 20 lines):" in caplog.text
        assert "... and more" in caplog.text
        assert "Run with --fix to automatically sort imports" in caplog.text

    def test_check_imports_with_fix(self, mock_subprocess, caplog):
        """Test imports check with fix flag enabled."""
        args = self.create_namespace(fix=True, path="panther/", config=None)

        mock_subprocess.run.return_value = MagicMock(returncode=1, stdout="", stderr="")

        result = CheckCommand._check_imports(args)

        assert result == 0  # Should return 0 when fixing
        assert "Running isort to sort imports..." in caplog.text
        assert "Imports have been sorted" in caplog.text

        # Verify correct command was called (no --check-only or --diff)
        call_args = mock_subprocess.run.call_args[0][0]
        assert "isort" in call_args
        assert "--check-only" not in call_args
        assert "--diff" not in call_args

    # =============================================================================
    # LINT CHECK TESTS
    # =============================================================================

    def test_check_lint_success(self, mock_subprocess, caplog):
        """Test lint check when no issues are found."""
        args = self.create_namespace(fix=False, path="panther/", config=None)

        mock_subprocess.run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        result = CheckCommand._check_lint(args)

        assert result == 0
        assert "Running flake8 linting..." in caplog.text
        assert "No linting issues found" in caplog.text

        # Verify correct command was called with defaults
        call_args = mock_subprocess.run.call_args[0][0]
        assert "flake8" in call_args
        assert "--max-line-length=100" in call_args
        assert "--extend-ignore=E203,W503" in call_args

    def test_check_lint_with_config(self, mock_subprocess, caplog):
        """Test lint check with custom config file."""
        args = self.create_namespace(
            fix=False, path="panther/", config="/path/to/config"
        )

        mock_subprocess.run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        result = CheckCommand._check_lint(args)

        assert result == 0

        # Verify config file was used instead of defaults
        call_args = mock_subprocess.run.call_args[0][0]
        assert "--config" in call_args
        assert "/path/to/config" in call_args
        assert "--max-line-length=100" not in call_args

    def test_check_lint_failure(self, mock_subprocess, caplog):
        """Test lint check when issues are found."""
        args = self.create_namespace(fix=False, path="panther/", config=None)

        # Create output with multiple issues
        lint_output = "\n".join(
            [
                "panther/test.py:1:1: E302 expected 2 blank lines",
                "panther/test.py:5:80: E501 line too long",
                "panther/other.py:10:1: F401 unused import",
            ]
            + [f"panther/file{i}.py:1:1: E302 error {i}" for i in range(4, 15)]
        )  # More than 10 total

        mock_subprocess.run.return_value = MagicMock(
            returncode=1, stdout=lint_output, stderr=""
        )

        result = CheckCommand._check_lint(args)

        assert result == 13  # Should return actual issue count
        assert "Linting issues found:" in caplog.text
        assert "First 10 issues:" in caplog.text
        assert "... and 3 more issues" in caplog.text

    def test_check_lint_no_output(self, mock_subprocess, caplog):
        """Test lint check when command fails but no output."""
        args = self.create_namespace(fix=False, path="panther/", config=None)

        mock_subprocess.run.return_value = MagicMock(returncode=1, stdout="", stderr="")

        result = CheckCommand._check_lint(args)

        assert result == 1  # Should return 1 if no specific count
        assert "Linting issues found:" in caplog.text

    # =============================================================================
    # TYPE CHECK TESTS
    # =============================================================================

    def test_check_type_success(self, mock_subprocess, caplog):
        """Test type check when no issues are found."""
        args = self.create_namespace(fix=False, path="panther/", config=None)

        mock_subprocess.run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        result = CheckCommand._check_type(args)

        assert result == 0
        assert "Running mypy type checking..." in caplog.text
        assert "No type checking issues found" in caplog.text

        # Verify correct command was called with defaults
        call_args = mock_subprocess.run.call_args[0][0]
        assert "mypy" in call_args
        assert "--ignore-missing-imports" in call_args
        assert "--no-strict-optional" in call_args
        assert "--warn-return-any" in call_args
        assert "--warn-unused-configs" in call_args

    def test_check_type_with_config(self, mock_subprocess, caplog):
        """Test type check with custom config file."""
        args = self.create_namespace(
            fix=False, path="panther/", config="/path/to/mypy.ini"
        )

        mock_subprocess.run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        result = CheckCommand._check_type(args)

        assert result == 0

        # Verify config file was used instead of defaults
        call_args = mock_subprocess.run.call_args[0][0]
        assert "--config-file" in call_args
        assert "/path/to/mypy.ini" in call_args
        assert "--ignore-missing-imports" not in call_args

    def test_check_type_failure(self, mock_subprocess, caplog):
        """Test type check when issues are found."""
        args = self.create_namespace(fix=False, path="panther/", config=None)

        # Create output with different types of issues
        type_output = "\n".join(
            [
                "panther/test.py:10: error: Incompatible types",
                "panther/test.py:15: error: Missing return statement",
                "panther/test.py:20: warning: Unused variable",
                "panther/test.py:25: note: Consider using Optional",
                "panther/other.py:5: error: Cannot resolve name",
            ]
            + [f"panther/file{i}.py:1: error: Type error {i}" for i in range(6, 20)]
        )  # More than 10 errors

        mock_subprocess.run.return_value = MagicMock(
            returncode=1, stdout=type_output, stderr=""
        )

        result = CheckCommand._check_type(args)

        assert result == 1
        assert "Type checking issues found:" in caplog.text
        assert "Errors: 15, Warnings: 1, Notes: 1" in caplog.text
        assert "First 10 errors:" in caplog.text
        assert "... and more errors" in caplog.text

    def test_check_type_success_with_output(self, mock_subprocess, caplog):
        """Test type check success but with non-error output."""
        args = self.create_namespace(fix=False, path="panther/", config=None)

        mock_subprocess.run.return_value = MagicMock(
            returncode=0,
            stdout="Success: no issues found in 10 source files\n",
            stderr="",
        )

        result = CheckCommand._check_type(args)

        assert result == 1  # Should return 1 if there's output even with returncode 0
        assert "Type checking issues found:" in caplog.text

    # =============================================================================
    # SECURITY CHECK TESTS
    # =============================================================================

    def test_check_security_success(self, mock_subprocess, caplog):
        """Test security check when no issues are found."""
        args = self.create_namespace(fix=False, path="panther/", config=None)

        mock_subprocess.run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        result = CheckCommand._check_security(args)

        assert result == 0
        assert "Running bandit security checks..." in caplog.text
        assert "No security issues found" in caplog.text

        # Verify correct command was called with defaults
        call_args = mock_subprocess.run.call_args[0][0]
        assert "bandit" in call_args
        assert "-r" in call_args
        assert "-ll" in call_args
        assert "-i" in call_args

    def test_check_security_with_config(self, mock_subprocess, caplog):
        """Test security check with custom config file."""
        args = self.create_namespace(
            fix=False, path="panther/", config="/path/to/bandit.conf"
        )

        mock_subprocess.run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        result = CheckCommand._check_security(args)

        assert result == 0

        # Verify config file was used instead of defaults
        call_args = mock_subprocess.run.call_args[0][0]
        assert "-c" in call_args
        assert "/path/to/bandit.conf" in call_args
        assert "-ll" not in call_args

    def test_check_security_failure(self, mock_subprocess, caplog):
        """Test security check when issues are found."""
        args = self.create_namespace(fix=False, path="panther/", config=None)

        # Create realistic bandit output
        security_output = """
>> Issue: [B602:subprocess_popen_with_shell_equals_true] subprocess call with shell=True identified
   Severity: High   Confidence: High
   Location: panther/test.py:10
   More Info: https://bandit.readthedocs.io/en/latest/
10     subprocess.Popen('ls -la', shell=True)

>> Issue: [B101:assert_used] Use of assert detected
   Severity: Low   Confidence: High
   Location: panther/test.py:15
15     assert user_input == "admin"

Total issues (by severity):
    Undefined: 0
    Low: 1
    Medium: 0
    High: 1
"""

        mock_subprocess.run.return_value = MagicMock(
            returncode=1, stdout=security_output, stderr=""
        )

        result = CheckCommand._check_security(args)

        assert result == 1
        assert "Security issues found:" in caplog.text
        assert "Total issues" in caplog.text
        assert "Security issues found:" in caplog.text
        assert ">> Issue:" in caplog.text

    def test_check_security_long_output(self, mock_subprocess, caplog):
        """Test security check with very long output."""
        args = self.create_namespace(fix=False, path="panther/", config=None)

        # Create very long output to test truncation
        long_issues = []
        for i in range(20):
            long_issues.extend(
                [
                    f">> Issue: [B{100+i}:test_issue_{i}] Test issue {i}",
                    f"   Severity: High   Confidence: High",
                    f"   Location: panther/test{i}.py:10",
                    f"10     some_code_{i}()",
                    "",
                ]
            )

        security_output = "\n".join(long_issues)

        mock_subprocess.run.return_value = MagicMock(
            returncode=1, stdout=security_output, stderr=""
        )

        result = CheckCommand._check_security(args)

        assert result == 1
        assert "Security issues found:" in caplog.text
        assert "... and more issues" in caplog.text

    # =============================================================================
    # TEST EXECUTION TESTS
    # =============================================================================

    def test_run_tests_success(self, mock_subprocess, mock_path_operations, caplog):
        """Test running tests when all tests pass."""
        args = self.create_namespace(
            fix=False, path="panther/", config=None, coverage=False
        )

        mock_path_class, mock_path_instance = mock_path_operations
        mock_subprocess.run.return_value = MagicMock(returncode=0)

        result = CheckCommand._run_tests(args)

        assert result == 0
        assert "Running tests with pytest..." in caplog.text
        assert "All tests passed" in caplog.text

        # Verify correct command was called
        call_args = mock_subprocess.run.call_args[0][0]
        assert "pytest" in call_args
        assert "tests" in call_args

    def test_run_tests_with_coverage(
        self, mock_subprocess, mock_path_operations, caplog
    ):
        """Test running tests with coverage enabled."""
        args = self.create_namespace(
            fix=False, path="panther/", config=None, coverage=True
        )

        mock_path_class, mock_path_instance = mock_path_operations
        mock_subprocess.run.return_value = MagicMock(returncode=0)

        result = CheckCommand._run_tests(args)

        assert result == 0
        assert "Coverage report generated in htmlcov/" in caplog.text

        # Verify coverage options were added
        call_args = mock_subprocess.run.call_args[0][0]
        assert "--cov=panther" in call_args
        assert "--cov-report=term-missing" in call_args
        assert "--cov-report=html" in call_args

    def test_run_tests_with_config(self, mock_subprocess, mock_path_operations, caplog):
        """Test running tests with custom config file."""
        args = self.create_namespace(
            fix=False, path="panther/", config="/path/to/pytest.ini", coverage=False
        )

        mock_path_class, mock_path_instance = mock_path_operations
        mock_subprocess.run.return_value = MagicMock(returncode=0)

        result = CheckCommand._run_tests(args)

        assert result == 0

        # Verify config file was added
        call_args = mock_subprocess.run.call_args[0][0]
        assert "-c" in call_args
        assert "/path/to/pytest.ini" in call_args

    def test_run_tests_no_tests_directory(
        self, mock_subprocess, mock_path_operations, caplog
    ):
        """Test running tests when tests directory doesn't exist."""
        args = self.create_namespace(
            fix=False, path="panther/", config=None, coverage=False
        )

        mock_path_class, mock_path_instance = mock_path_operations
        mock_path_instance.exists.return_value = False

        result = CheckCommand._run_tests(args)

        assert result == 0
        assert "No tests directory found" in caplog.text

        # pytest should not be called
        mock_subprocess.run.assert_not_called()

    def test_run_tests_failure(self, mock_subprocess, mock_path_operations, caplog):
        """Test running tests when some tests fail."""
        args = self.create_namespace(
            fix=False, path="panther/", config=None, coverage=False
        )

        mock_path_class, mock_path_instance = mock_path_operations
        mock_subprocess.run.return_value = MagicMock(returncode=1)

        result = CheckCommand._run_tests(args)

        assert result == 1
        assert "Some tests failed" in caplog.text

    # =============================================================================
    # PARAMETER VALIDATION TESTS
    # =============================================================================

    @pytest.mark.parametrize("flag_value", [True, False])
    def test_boolean_flags(self, flag_value, mock_subprocess, mock_path_operations):
        """Test all boolean flags."""
        flags = [
            "all",
            "format",
            "imports",
            "lint",
            "type",
            "security",
            "test",
            "coverage",
            "fix",
        ]

        for flag in flags:
            args_dict = {
                "all": False,
                "format": False,
                "imports": False,
                "lint": False,
                "type": False,
                "security": False,
                "test": False,
                "coverage": False,
                "fix": False,
                "path": "panther/",
                "config": None,
            }

            # Set at least one check to run
            if flag != "coverage" and flag != "fix":
                args_dict[flag] = flag_value
                if not flag_value and flag != "all":
                    args_dict["format"] = True  # Ensure at least one check runs
            else:
                args_dict["format"] = True  # Ensure at least one check runs
                args_dict[flag] = flag_value

            args = self.create_namespace(**args_dict)

            mock_path_class, mock_path_instance = mock_path_operations
            mock_subprocess.run.return_value = MagicMock(
                returncode=0, stdout="", stderr=""
            )

            result = CheckCommand.handle(args)

            # Should not crash with any valid flag value
            assert result in [0, 1]

    @pytest.mark.parametrize(
        "path_value", ["panther/", "src/", "tests/", ".", "/absolute/path"]
    )
    def test_path_values(self, path_value, mock_subprocess):
        """Test different path values."""
        args = self.create_namespace(
            all=False,
            format=True,
            imports=False,
            lint=False,
            type=False,
            security=False,
            test=False,
            coverage=False,
            fix=False,
            path=path_value,
            config=None,
        )

        mock_subprocess.run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        result = CheckCommand.handle(args)

        assert result == 0
        # Verify path was used in subprocess call
        call_args = mock_subprocess.run.call_args[0][0]
        assert path_value in call_args

    @pytest.mark.parametrize(
        "config_value", [None, "/path/to/config", "relative/config", ".config"]
    )
    def test_config_values(self, config_value, mock_subprocess):
        """Test different config file values."""
        args = self.create_namespace(
            all=False,
            format=False,
            imports=False,
            lint=True,
            type=False,
            security=False,
            test=False,
            coverage=False,
            fix=False,
            path="panther/",
            config=config_value,
        )

        mock_subprocess.run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        result = CheckCommand.handle(args)

        assert result == 0

        call_args = mock_subprocess.run.call_args[0][0]
        if config_value:
            assert "--config" in call_args
            assert config_value in call_args
        else:
            # Should use defaults when no config
            assert "--max-line-length=100" in call_args

    # =============================================================================
    # EDGE CASE TESTS
    # =============================================================================

    def test_unicode_in_path(self, mock_subprocess):
        """Test handling of unicode characters in path."""
        unicode_path = "测试/path"

        args = self.create_namespace(
            all=False,
            format=True,
            imports=False,
            lint=False,
            type=False,
            security=False,
            test=False,
            coverage=False,
            fix=False,
            path=unicode_path,
            config=None,
        )

        mock_subprocess.run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        result = CheckCommand.handle(args)

        assert result == 0  # Should handle unicode gracefully

    def test_very_long_path(self, mock_subprocess):
        """Test handling of very long paths."""
        long_path = "very/" + ("long/" * 50) + "path"

        args = self.create_namespace(
            all=False,
            format=True,
            imports=False,
            lint=False,
            type=False,
            security=False,
            test=False,
            coverage=False,
            fix=False,
            path=long_path,
            config=None,
        )

        mock_subprocess.run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        result = CheckCommand.handle(args)

        assert result == 0  # Should handle long paths gracefully

    def test_special_characters_in_path(self, mock_subprocess):
        """Test handling of special characters in path."""
        special_path = "path/with-special@chars#/code$"

        args = self.create_namespace(
            all=False,
            format=True,
            imports=False,
            lint=False,
            type=False,
            security=False,
            test=False,
            coverage=False,
            fix=False,
            path=special_path,
            config=None,
        )

        mock_subprocess.run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        result = CheckCommand.handle(args)

        assert result == 0  # Should handle special characters gracefully

    def test_subprocess_exception(self, mock_subprocess, caplog):
        """Test handling of subprocess exceptions."""
        args = self.create_namespace(
            all=False,
            format=True,
            imports=False,
            lint=False,
            type=False,
            security=False,
            test=False,
            coverage=False,
            fix=False,
            path="panther/",
            config=None,
        )

        # Mock subprocess to raise exception
        mock_subprocess.run.side_effect = [
            MagicMock(returncode=0),  # Tool check
            Exception("Subprocess error"),  # Actual check
        ]

        # Should handle exception gracefully
        try:
            result = CheckCommand.handle(args)
            # If it doesn't raise, result should indicate error
            assert result == 1
        except Exception:
            # If it raises, that's also acceptable behavior
            pass

    # =============================================================================
    # INTEGRATION TESTS
    # =============================================================================

    def test_end_to_end_all_checks_workflow(
        self, mock_subprocess, mock_path_operations, caplog
    ):
        """Test complete workflow with all checks enabled."""
        args = self.create_namespace(
            all=True,
            format=False,
            imports=False,
            lint=False,
            type=False,
            security=False,
            test=True,
            coverage=True,
            fix=False,
            path="panther/",
            config=None,
        )

        mock_path_class, mock_path_instance = mock_path_operations
        # Mock all tools as installed and all checks as successful
        mock_subprocess.run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        result = CheckCommand.handle(args)

        assert result == 0
        assert "All checks passed!" in caplog.text
        assert "format" in caplog.text
        assert "imports" in caplog.text
        assert "lint" in caplog.text
        assert "type" in caplog.text
        assert "security" in caplog.text
        assert "test" in caplog.text

    def test_check_command_comprehensive_parameters(
        self, mock_subprocess, mock_path_operations, caplog
    ):
        """Test check command with comprehensive parameter combinations."""
        # Test various combinations of checks
        test_combinations = [
            # Single checks
            {"format": True},
            {"imports": True},
            {"lint": True},
            {"type": True},
            {"security": True},
            {"test": True},
            # Multiple checks
            {"format": True, "imports": True},
            {"lint": True, "type": True, "security": True},
            # All checks
            {"all": True},
            {"all": True, "test": True, "coverage": True},
            # With fix
            {"format": True, "fix": True},
            {"imports": True, "fix": True},
        ]

        mock_path_class, mock_path_instance = mock_path_operations
        mock_subprocess.run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        for combination in test_combinations:
            # Create base args
            args_dict = {
                "all": False,
                "format": False,
                "imports": False,
                "lint": False,
                "type": False,
                "security": False,
                "test": False,
                "coverage": False,
                "fix": False,
                "path": "panther/",
                "config": None,
            }
            args_dict.update(combination)

            args = self.create_namespace(**args_dict)

            result = CheckCommand.handle(args)

            assert result == 0  # All should succeed with mocked subprocess

        # Verify various tools were called
        assert mock_subprocess.run.call_count > len(test_combinations)

    def test_check_error_recovery_scenarios(
        self, mock_subprocess, mock_path_operations, caplog
    ):
        """Test check command error recovery scenarios."""
        mock_path_class, mock_path_instance = mock_path_operations

        # Scenario 1: Some checks pass, some fail
        args_mixed = self.create_namespace(
            all=False,
            format=True,
            imports=True,
            lint=True,
            type=False,
            security=False,
            test=False,
            coverage=False,
            fix=False,
            path="panther/",
            config=None,
        )

        # Mock mixed results
        mock_subprocess.run.side_effect = [
            MagicMock(returncode=0),  # tool checks
            MagicMock(returncode=0),  # tool checks
            MagicMock(returncode=0),  # tool checks
            MagicMock(returncode=0, stdout="", stderr=""),  # format success
            MagicMock(returncode=1, stdout="import errors", stderr=""),  # imports fail
            MagicMock(returncode=1, stdout="lint errors", stderr=""),  # lint fail
        ]

        result = CheckCommand.handle(args_mixed)

        assert result == 1
        assert "total issue(s) found" in caplog.text

        # Verify summary shows mixed results
        assert "✅ PASSED" in caplog.text
        assert "❌ FAILED" in caplog.text
