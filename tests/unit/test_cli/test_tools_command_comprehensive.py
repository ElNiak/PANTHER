"""
Comprehensive unit tests for ToolsCommand CLI.

This module provides exhaustive testing for ALL ToolsCommand parameters,
including all 3 subcommands, tool installation, version checking, and error conditions.
"""

import argparse
import logging
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, call, mock_open, patch

import pytest

from panther.cli.subcommands.tools import ToolsCommand
from tests.unit.test_cli.base_cli_test import ComprehensiveCLITest


class TestToolsCommandComprehensive(ComprehensiveCLITest):
    """Comprehensive tests for ToolsCommand with ALL parameter combinations."""

    @pytest.fixture
    def command_class(self):
        """Return the command class being tested."""
        return ToolsCommand

    @pytest.fixture
    def command_name(self):
        """Return the command name for testing."""
        return "tools"

    @pytest.fixture
    def mock_subprocess(self):
        """Mock subprocess for command execution testing."""
        with patch("panther.cli.subcommands.tools.subprocess") as mock:
            # Default successful subprocess results
            mock.run.return_value = MagicMock(returncode=0, stdout=b"", stderr=b"")
            mock.Popen.return_value = MagicMock()
            yield mock

    @pytest.fixture
    def mock_sys(self):
        """Mock sys module for executable path."""
        with patch("panther.cli.subcommands.tools.sys") as mock:
            mock.executable = "/usr/bin/python"
            yield mock

    @pytest.fixture
    def mock_path_operations(self):
        """Mock Path operations for file system testing."""
        with patch("panther.cli.subcommands.tools.Path") as mock_path_class:
            mock_path_instance = MagicMock()
            mock_path_instance.exists.return_value = True
            mock_path_instance.is_dir.return_value = True
            mock_path_class.return_value = mock_path_instance

            # Mock Path.cwd() for precommit installation
            mock_path_class.cwd.return_value = mock_path_instance

            # Mock parent navigation for git repo detection
            mock_parent = MagicMock()
            mock_path_instance.parent = mock_parent
            mock_parent.parent = mock_parent  # Avoid infinite recursion

            yield mock_path_class, mock_path_instance

    # =============================================================================
    # PARSER REGISTRATION TESTS
    # =============================================================================

    def test_parser_registration(self):
        """Test that ToolsCommand is properly registered."""
        from panther.cli.main import create_parser

        parser = create_parser()

        # Verify 'tools' subcommand exists
        subparsers_actions = [
            action
            for action in parser._actions
            if isinstance(action, argparse._SubParsersAction)
        ]
        assert len(subparsers_actions) == 1
        assert "tools" in subparsers_actions[0].choices

    def test_all_subcommands_registered(self):
        """Test that all tool subcommands are registered."""
        from panther.cli.main import create_parser

        parser = create_parser()

        # Parse tools help to get subcommands
        try:
            parser.parse_args(["tools", "--help"])
        except SystemExit:
            pass  # Expected behavior for help

        # Verify subcommands exist by testing their individual help
        subcommands = ["install-slim", "install-precommit", "list"]

        for subcommand in subcommands:
            try:
                parser.parse_args(["tools", subcommand, "--help"])
            except SystemExit:
                pass  # Expected for help command

    def test_tool_options_registered(self):
        """Test that all tool options are registered in parsers."""
        from panther.cli.main import create_parser

        parser = create_parser()

        # Test install-slim options
        try:
            parser.parse_args(["tools", "install-slim", "--force"])
        except SystemExit:
            pass  # May exit depending on implementation

        # Test install-precommit options
        try:
            parser.parse_args(["tools", "install-precommit", "--update"])
        except SystemExit:
            pass  # May exit depending on implementation

    # =============================================================================
    # MAIN COMMAND HANDLER TESTS
    # =============================================================================

    def test_handle_no_action_specified(self, caplog):
        """Test behavior when no tools action is specified."""
        args = self.create_namespace(tools_action=None)

        result = ToolsCommand.handle(args)

        assert result == 1
        assert "No tools action specified" in caplog.text

    def test_handle_unknown_action(self, caplog):
        """Test behavior with unknown tools action."""
        args = self.create_namespace(tools_action="unknown_action")

        result = ToolsCommand.handle(args)

        assert result == 1
        assert "Unknown tools action: unknown_action" in caplog.text

    # =============================================================================
    # INSTALL-SLIM SUBCOMMAND TESTS
    # =============================================================================

    def test_install_slim_already_installed_no_force(self, mock_subprocess, caplog):
        """Test install-slim when slim is already installed without force flag."""
        # Mock 'which slim' to return success (already installed)
        mock_subprocess.run.return_value = MagicMock(
            returncode=0, stdout=b"/usr/local/bin/slim\n", stderr=b""
        )

        args = self.create_namespace(tools_action="install-slim", force=False)

        result = ToolsCommand.handle(args)

        assert result == 0
        assert "slim is already installed at: /usr/local/bin/slim" in caplog.text

        # Verify 'which slim' was called
        mock_subprocess.run.assert_called_once_with(
            ["which", "slim"], capture_output=True
        )

    def test_install_slim_not_installed(self, mock_subprocess, caplog):
        """Test install-slim when slim is not installed."""
        # Mock 'which slim' to return failure (not installed)
        mock_subprocess.run.side_effect = [
            MagicMock(returncode=1, stdout=b"", stderr=b""),  # which slim fails
            MagicMock(
                returncode=0, stdout=b"/usr/local/bin/slim\n", stderr=b""
            ),  # verification succeeds
        ]

        # Mock Popen for installation pipeline
        mock_curl_proc = MagicMock()
        mock_bash_proc = MagicMock()
        mock_bash_proc.communicate.return_value = (b"Installation output", b"")
        mock_subprocess.Popen.side_effect = [mock_curl_proc, mock_bash_proc]

        args = self.create_namespace(tools_action="install-slim", force=False)

        result = ToolsCommand.handle(args)

        assert result == 0
        assert "Downloading and installing slim..." in caplog.text
        assert "slim installed successfully at: /usr/local/bin/slim" in caplog.text

        # Verify subprocess calls
        assert mock_subprocess.run.call_count == 2  # which check + verification
        assert mock_subprocess.Popen.call_count == 2  # curl + bash

    def test_install_slim_force_reinstall(self, mock_subprocess, caplog):
        """Test install-slim with force flag to reinstall."""
        # Mock verification to succeed
        mock_subprocess.run.return_value = MagicMock(
            returncode=0, stdout=b"/usr/local/bin/slim\n", stderr=b""
        )

        # Mock Popen for installation pipeline
        mock_curl_proc = MagicMock()
        mock_bash_proc = MagicMock()
        mock_bash_proc.communicate.return_value = (b"Installation output", b"")
        mock_subprocess.Popen.side_effect = [mock_curl_proc, mock_bash_proc]

        args = self.create_namespace(tools_action="install-slim", force=True)

        result = ToolsCommand.handle(args)

        assert result == 0
        assert "Downloading and installing slim..." in caplog.text
        assert "slim installed successfully at: /usr/local/bin/slim" in caplog.text

        # Verify that 'which slim' check was skipped due to force=True
        # Only verification call should be made
        mock_subprocess.run.assert_called_once_with(
            ["which", "slim"], capture_output=True
        )

    def test_install_slim_installation_failed(self, mock_subprocess, caplog):
        """Test install-slim when installation process fails."""
        # Mock 'which slim' to return failure (not installed) for both initial check and verification
        mock_subprocess.run.side_effect = [
            MagicMock(
                returncode=1, stdout=b"", stderr=b""
            ),  # which slim fails initially
            MagicMock(returncode=1, stdout=b"", stderr=b""),  # verification also fails
        ]

        # Mock Popen for installation pipeline
        mock_curl_proc = MagicMock()
        mock_bash_proc = MagicMock()
        mock_bash_proc.communicate.return_value = (b"Installation output", b"")
        mock_subprocess.Popen.side_effect = [mock_curl_proc, mock_bash_proc]

        args = self.create_namespace(tools_action="install-slim", force=False)

        result = ToolsCommand.handle(args)

        assert result == 1
        assert "Downloading and installing slim..." in caplog.text
        assert "slim installation failed. Could not find slim in PATH." in caplog.text

    def test_install_slim_subprocess_exception(self, mock_subprocess, caplog):
        """Test install-slim when subprocess raises CalledProcessError."""
        # Mock 'which slim' to return failure (not installed)
        mock_subprocess.run.side_effect = [
            MagicMock(returncode=1, stdout=b"", stderr=b""),  # which slim fails
        ]

        # Mock Popen to raise exception
        mock_subprocess.Popen.side_effect = subprocess.CalledProcessError(1, "curl")

        args = self.create_namespace(tools_action="install-slim", force=False)

        result = ToolsCommand.handle(args)

        assert result == 1
        assert "Error installing slim:" in caplog.text

    def test_install_slim_unexpected_exception(self, mock_subprocess, caplog):
        """Test install-slim when unexpected exception occurs."""
        # Mock 'which slim' to return failure (not installed)
        mock_subprocess.run.side_effect = [
            MagicMock(returncode=1, stdout=b"", stderr=b""),  # which slim fails
        ]

        # Mock Popen to raise unexpected exception
        mock_subprocess.Popen.side_effect = Exception("Unexpected error")

        args = self.create_namespace(tools_action="install-slim", force=False)

        result = ToolsCommand.handle(args)

        assert result == 1
        assert "Unexpected error during slim installation:" in caplog.text

    # =============================================================================
    # INSTALL-PRECOMMIT SUBCOMMAND TESTS
    # =============================================================================

    def test_install_precommit_success(
        self, mock_subprocess, mock_path_operations, caplog
    ):
        """Test successful precommit installation."""
        mock_path_class, mock_path_instance = mock_path_operations

        # Mock successful pip install
        mock_subprocess.run.side_effect = [
            MagicMock(returncode=0, stdout=b"", stderr=b""),  # pip install
            MagicMock(returncode=0, stdout=b"", stderr=b""),  # pre-commit install
        ]

        # Mock git repo detection
        git_dir = MagicMock()
        git_dir.exists.return_value = True
        mock_path_instance.__truediv__.return_value = git_dir

        # Mock precommit config file
        config_file = MagicMock()
        config_file.exists.return_value = True

        with patch("builtins.open", mock_open()) as mock_file:
            args = self.create_namespace(tools_action="install-precommit", update=False)

            result = ToolsCommand.handle(args)

        assert result == 0
        assert "Installing and configuring pre-commit hooks..." in caplog.text
        assert "Installing pre-commit package..." in caplog.text
        assert "Installing pre-commit hooks into .git/hooks/..." in caplog.text
        assert "Pre-commit hooks installed and configured successfully!" in caplog.text

    def test_install_precommit_with_update(
        self, mock_subprocess, mock_path_operations, caplog
    ):
        """Test precommit installation with update flag."""
        mock_path_class, mock_path_instance = mock_path_operations

        # Mock successful operations
        mock_subprocess.run.side_effect = [
            MagicMock(returncode=0, stdout=b"", stderr=b""),  # pip install
            MagicMock(returncode=0, stdout=b"", stderr=b""),  # pre-commit install
            MagicMock(returncode=0, stdout=b"", stderr=b""),  # pre-commit autoupdate
        ]

        # Mock git repo detection
        git_dir = MagicMock()
        git_dir.exists.return_value = True
        mock_path_instance.__truediv__.return_value = git_dir

        # Mock precommit config file exists
        config_file = MagicMock()
        config_file.exists.return_value = True

        args = self.create_namespace(tools_action="install-precommit", update=True)

        result = ToolsCommand.handle(args)

        assert result == 0
        assert "Updating pre-commit hooks to latest versions..." in caplog.text

        # Verify autoupdate was called
        update_call = call(
            ["pre-commit", "autoupdate"], cwd=mock_path_instance, capture_output=True
        )
        assert update_call in mock_subprocess.run.call_args_list

    def test_install_precommit_pip_install_fails(
        self, mock_subprocess, mock_path_operations, caplog
    ):
        """Test precommit installation when pip install fails."""
        mock_path_class, mock_path_instance = mock_path_operations

        # Mock failed pip install
        mock_subprocess.run.return_value = MagicMock(
            returncode=1, stdout=b"", stderr=b"Package not found"
        )

        args = self.create_namespace(tools_action="install-precommit", update=False)

        result = ToolsCommand.handle(args)

        assert result == 1
        assert "Failed to install pre-commit package" in caplog.text

    def test_install_precommit_not_in_git_repo(
        self, mock_subprocess, mock_path_operations, caplog
    ):
        """Test precommit installation when not in git repository."""
        mock_path_class, mock_path_instance = mock_path_operations

        # Mock successful pip install
        mock_subprocess.run.return_value = MagicMock(
            returncode=0, stdout=b"", stderr=b""
        )

        # Mock no git repo detection - make .git directory not exist
        git_dir = MagicMock()
        git_dir.exists.return_value = False
        mock_path_instance.__truediv__.return_value = git_dir

        # Mock path traversal to reach root without finding .git
        mock_path_instance.parent = (
            mock_path_instance  # Same as parent to trigger exit condition
        )

        args = self.create_namespace(tools_action="install-precommit", update=False)

        result = ToolsCommand.handle(args)

        assert result == 1
        assert "Not in a git repository" in caplog.text

    def test_install_precommit_creates_config_file(
        self, mock_subprocess, mock_path_operations, caplog
    ):
        """Test precommit installation creates config file when missing."""
        mock_path_class, mock_path_instance = mock_path_operations

        # Mock successful operations
        mock_subprocess.run.side_effect = [
            MagicMock(returncode=0, stdout=b"", stderr=b""),  # pip install
            MagicMock(returncode=0, stdout=b"", stderr=b""),  # pre-commit install
        ]

        # Mock git repo detection
        git_dir = MagicMock()
        git_dir.exists.return_value = True
        mock_path_instance.__truediv__.return_value = git_dir

        # Mock precommit config file doesn't exist
        config_file = MagicMock()
        config_file.exists.return_value = False

        with patch("builtins.open", mock_open()) as mock_file:
            args = self.create_namespace(tools_action="install-precommit", update=False)

            result = ToolsCommand.handle(args)

        assert result == 0
        assert (
            "No .pre-commit-config.yaml found in root. Creating one..." in caplog.text
        )
        assert "Created basic .pre-commit-config.yaml" in caplog.text

        # Verify file was written with config content
        mock_file.assert_called_once()
        written_content = mock_file().write.call_args[0][0]
        assert "repos:" in written_content
        assert "pre-commit-hooks" in written_content
        assert "black" in written_content
        assert "isort" in written_content
        assert "flake8" in written_content

    def test_install_precommit_hooks_install_fails(
        self, mock_subprocess, mock_path_operations, caplog
    ):
        """Test precommit installation when pre-commit install fails."""
        mock_path_class, mock_path_instance = mock_path_operations

        # Mock pip install success, pre-commit install failure
        mock_subprocess.run.side_effect = [
            MagicMock(returncode=0, stdout=b"", stderr=b""),  # pip install success
            MagicMock(
                returncode=1, stdout=b"", stderr=b"Hook installation failed"
            ),  # pre-commit install fails
        ]

        # Mock git repo detection
        git_dir = MagicMock()
        git_dir.exists.return_value = True
        mock_path_instance.__truediv__.return_value = git_dir

        # Mock precommit config file exists
        config_file = MagicMock()
        config_file.exists.return_value = True

        args = self.create_namespace(tools_action="install-precommit", update=False)

        result = ToolsCommand.handle(args)

        assert result == 1
        assert "Failed to install pre-commit hooks" in caplog.text

    def test_install_precommit_update_fails_warning(
        self, mock_subprocess, mock_path_operations, caplog
    ):
        """Test precommit installation when update fails but installation succeeds."""
        mock_path_class, mock_path_instance = mock_path_operations

        # Mock operations: pip success, install success, update fails
        mock_subprocess.run.side_effect = [
            MagicMock(returncode=0, stdout=b"", stderr=b""),  # pip install
            MagicMock(returncode=0, stdout=b"", stderr=b""),  # pre-commit install
            MagicMock(
                returncode=1, stdout=b"", stderr=b"Update failed"
            ),  # autoupdate fails
        ]

        # Mock git repo detection
        git_dir = MagicMock()
        git_dir.exists.return_value = True
        mock_path_instance.__truediv__.return_value = git_dir

        # Mock precommit config file exists
        config_file = MagicMock()
        config_file.exists.return_value = True

        args = self.create_namespace(tools_action="install-precommit", update=True)

        result = ToolsCommand.handle(args)

        assert result == 0  # Should still succeed
        assert (
            "Warning: Failed to update pre-commit hooks, but installation was successful"
            in caplog.text
        )
        assert "Pre-commit hooks installed and configured successfully!" in caplog.text

    # =============================================================================
    # LIST SUBCOMMAND TESTS
    # =============================================================================

    def test_list_tools_all_installed(self, mock_subprocess, caplog):
        """Test list command when all tools are installed."""
        # Mock 'which' commands to succeed for all tools
        mock_subprocess.run.side_effect = [
            # which commands (all succeed)
            MagicMock(returncode=0, stdout="slim\n", stderr=""),
            MagicMock(returncode=0, stdout="pre-commit\n", stderr=""),
            MagicMock(returncode=0, stdout="docker\n", stderr=""),
            MagicMock(returncode=0, stdout="mkdocs\n", stderr=""),
            MagicMock(returncode=0, stdout="pytest\n", stderr=""),
            MagicMock(returncode=0, stdout="black\n", stderr=""),
            MagicMock(returncode=0, stdout="isort\n", stderr=""),
            MagicMock(returncode=0, stdout="flake8\n", stderr=""),
            MagicMock(returncode=0, stdout="mypy\n", stderr=""),
            # version commands (some succeed)
            MagicMock(returncode=0, stdout="slim version 1.40.11\n", stderr=""),
            MagicMock(returncode=0, stdout="pre-commit 3.5.0\n", stderr=""),
            MagicMock(returncode=0, stdout="Docker version 24.0.6\n", stderr=""),
            MagicMock(returncode=0, stdout="mkdocs, version 1.5.3\n", stderr=""),
            MagicMock(returncode=0, stdout="pytest 7.4.3\n", stderr=""),
            MagicMock(returncode=0, stdout="black, 23.7.0\n", stderr=""),
            MagicMock(returncode=0, stdout="isort 5.12.0\n", stderr=""),
            MagicMock(returncode=0, stdout="flake8 6.1.0\n", stderr=""),
            MagicMock(returncode=0, stdout="mypy 1.5.1\n", stderr=""),
        ]

        args = self.create_namespace(tools_action="list")

        result = ToolsCommand.handle(args)

        assert result == 0
        assert "PANTHER Tools Status" in caplog.text
        assert "✅ slim" in caplog.text
        assert "✅ pre-commit" in caplog.text
        assert "✅ docker" in caplog.text
        assert "✅ mkdocs" in caplog.text
        assert "✅ pytest" in caplog.text
        assert "✅ black" in caplog.text
        assert "✅ isort" in caplog.text
        assert "✅ flake8" in caplog.text
        assert "✅ mypy" in caplog.text

        # Check descriptions are included
        assert "Docker image optimizer" in caplog.text
        assert "Git hooks framework" in caplog.text
        assert "Container platform" in caplog.text
        assert "Documentation generator" in caplog.text
        assert "Testing framework" in caplog.text
        assert "Code formatter" in caplog.text
        assert "Import sorter" in caplog.text
        assert "Code linter" in caplog.text
        assert "Type checker" in caplog.text

    def test_list_tools_some_missing(self, mock_subprocess, caplog):
        """Test list command when some tools are missing."""
        # Mock some tools missing, some installed
        mock_subprocess.run.side_effect = [
            # which commands - mixed results
            MagicMock(returncode=1, stdout="", stderr=""),  # slim not found
            MagicMock(
                returncode=0, stdout="pre-commit\n", stderr=""
            ),  # pre-commit found
            MagicMock(returncode=1, stdout="", stderr=""),  # docker not found
            MagicMock(returncode=0, stdout="mkdocs\n", stderr=""),  # mkdocs found
            MagicMock(returncode=1, stdout="", stderr=""),  # pytest not found
            MagicMock(returncode=0, stdout="black\n", stderr=""),  # black found
            MagicMock(returncode=1, stdout="", stderr=""),  # isort not found
            MagicMock(returncode=0, stdout="flake8\n", stderr=""),  # flake8 found
            MagicMock(returncode=1, stdout="", stderr=""),  # mypy not found
            # version commands for found tools
            MagicMock(returncode=0, stdout="pre-commit 3.5.0\n", stderr=""),
            MagicMock(returncode=0, stdout="mkdocs, version 1.5.3\n", stderr=""),
            MagicMock(returncode=0, stdout="black, 23.7.0\n", stderr=""),
            MagicMock(returncode=0, stdout="flake8 6.1.0\n", stderr=""),
        ]

        args = self.create_namespace(tools_action="list")

        result = ToolsCommand.handle(args)

        assert result == 0
        assert "PANTHER Tools Status" in caplog.text

        # Check missing tools
        assert "❌ slim" in caplog.text
        assert "❌ docker" in caplog.text
        assert "❌ pytest" in caplog.text
        assert "❌ isort" in caplog.text
        assert "❌ mypy" in caplog.text

        # Check found tools
        assert "✅ pre-commit" in caplog.text
        assert "✅ mkdocs" in caplog.text
        assert "✅ black" in caplog.text
        assert "✅ flake8" in caplog.text

        # Check "not found" status
        assert "not found" in caplog.text

    def test_list_tools_version_extraction(self, mock_subprocess, caplog):
        """Test list command version extraction from various output formats."""
        # Mock tools with different version output formats
        mock_subprocess.run.side_effect = [
            # which commands (all succeed)
            MagicMock(returncode=0, stdout="slim\n", stderr=""),
            MagicMock(returncode=0, stdout="pre-commit\n", stderr=""),
            MagicMock(returncode=0, stdout="docker\n", stderr=""),
            MagicMock(returncode=0, stdout="mkdocs\n", stderr=""),
            MagicMock(returncode=0, stdout="pytest\n", stderr=""),
            MagicMock(returncode=0, stdout="black\n", stderr=""),
            MagicMock(returncode=0, stdout="isort\n", stderr=""),
            MagicMock(returncode=0, stdout="flake8\n", stderr=""),
            MagicMock(returncode=0, stdout="mypy\n", stderr=""),
            # version commands with different formats
            MagicMock(
                returncode=0, stdout="version 1.40.11\n", stderr=""
            ),  # simple version
            MagicMock(
                returncode=0, stdout="pre-commit 3.5.0 from /usr/local\n", stderr=""
            ),  # version with path
            MagicMock(
                returncode=0, stdout="Docker version 24.0.6, build ed223bc\n", stderr=""
            ),  # Docker format
            MagicMock(
                returncode=0,
                stdout="mkdocs, version 1.5.3 from /usr/local (Python 3.11)\n",
                stderr="",
            ),  # complex format
            MagicMock(returncode=1, stdout="", stderr=""),  # version command fails
            MagicMock(
                returncode=0, stdout="black, 23.7.0 (compiled: yes)\n", stderr=""
            ),  # black format
            MagicMock(
                returncode=0, stdout="                         5.12.0\n", stderr=""
            ),  # isort format
            MagicMock(
                returncode=0,
                stdout="flake8 6.1.0 (mccabe: 0.7.0, pycodestyle: 2.11.0)\n",
                stderr="",
            ),  # detailed format
            MagicMock(
                returncode=0, stdout="mypy 1.5.1 (compiled: yes)\n", stderr=""
            ),  # mypy format
        ]

        args = self.create_namespace(tools_action="list")

        result = ToolsCommand.handle(args)

        assert result == 0

        # Check that version numbers are extracted correctly
        assert "1.40.11" in caplog.text  # slim
        assert "3.5.0" in caplog.text  # pre-commit
        assert "24.0.6" in caplog.text  # docker
        assert "1.5.3" in caplog.text  # mkdocs
        assert "unknown" in caplog.text  # pytest (version command failed)
        assert "23.7.0" in caplog.text  # black
        assert "5.12.0" in caplog.text  # isort
        assert "6.1.0" in caplog.text  # flake8
        assert "1.5.1" in caplog.text  # mypy

    def test_list_tools_version_exception_handling(self, mock_subprocess, caplog):
        """Test list command handles version extraction exceptions gracefully."""
        # Mock 'which' to succeed but version commands to raise exceptions
        mock_subprocess.run.side_effect = [
            # which commands succeed
            MagicMock(returncode=0, stdout="slim\n", stderr=""),
            MagicMock(returncode=0, stdout="pre-commit\n", stderr=""),
            MagicMock(returncode=0, stdout="docker\n", stderr=""),
            MagicMock(returncode=0, stdout="mkdocs\n", stderr=""),
            MagicMock(returncode=0, stdout="pytest\n", stderr=""),
            MagicMock(returncode=0, stdout="black\n", stderr=""),
            MagicMock(returncode=0, stdout="isort\n", stderr=""),
            MagicMock(returncode=0, stdout="flake8\n", stderr=""),
            MagicMock(returncode=0, stdout="mypy\n", stderr=""),
        ] + [
            Exception("Version command failed")
        ] * 9  # All version commands raise exceptions

        args = self.create_namespace(tools_action="list")

        result = ToolsCommand.handle(args)

        assert result == 0

        # All tools should show as installed but with unknown versions
        assert "✅ slim" in caplog.text
        assert "unknown" in caplog.text  # Should appear multiple times for each tool

    # =============================================================================
    # PARAMETER VALIDATION TESTS
    # =============================================================================

    @pytest.mark.parametrize(
        "invalid_action",
        ["invalid", "", "INSTALL-SLIM", "list_wrong", 123, None],  # Case sensitive
    )
    def test_invalid_actions(self, invalid_action, caplog):
        """Test handling of invalid action parameters."""
        args = self.create_namespace(tools_action=invalid_action)

        result = ToolsCommand.handle(args)

        if invalid_action is None:
            assert "No tools action specified" in caplog.text
        else:
            assert result == 1

    @pytest.mark.parametrize("force_flag", [True, False])
    def test_install_slim_force_parameter(self, force_flag, mock_subprocess, caplog):
        """Test install-slim with different force parameter values."""
        # Mock 'which slim' based on force flag behavior
        if force_flag:
            # With force, should skip initial check and go straight to installation
            mock_subprocess.run.return_value = MagicMock(
                returncode=0, stdout=b"/usr/local/bin/slim\n", stderr=b""
            )
        else:
            # Without force, check first, then skip installation if found
            mock_subprocess.run.return_value = MagicMock(
                returncode=0, stdout=b"/usr/local/bin/slim\n", stderr=b""
            )

        # Mock Popen for installation pipeline (only used with force or when not found)
        mock_curl_proc = MagicMock()
        mock_bash_proc = MagicMock()
        mock_bash_proc.communicate.return_value = (b"Installation output", b"")
        mock_subprocess.Popen.side_effect = [mock_curl_proc, mock_bash_proc]

        args = self.create_namespace(tools_action="install-slim", force=force_flag)

        result = ToolsCommand.handle(args)

        assert result == 0

        if force_flag:
            assert "Downloading and installing slim..." in caplog.text
        else:
            assert "slim is already installed at:" in caplog.text

    @pytest.mark.parametrize("update_flag", [True, False])
    def test_install_precommit_update_parameter(
        self, update_flag, mock_subprocess, mock_path_operations, caplog
    ):
        """Test install-precommit with different update parameter values."""
        mock_path_class, mock_path_instance = mock_path_operations

        # Mock successful operations
        base_calls = [
            MagicMock(returncode=0, stdout=b"", stderr=b""),  # pip install
            MagicMock(returncode=0, stdout=b"", stderr=b""),  # pre-commit install
        ]

        if update_flag:
            base_calls.append(
                MagicMock(returncode=0, stdout=b"", stderr=b"")
            )  # autoupdate

        mock_subprocess.run.side_effect = base_calls

        # Mock git repo detection
        git_dir = MagicMock()
        git_dir.exists.return_value = True
        mock_path_instance.__truediv__.return_value = git_dir

        # Mock precommit config file exists
        config_file = MagicMock()
        config_file.exists.return_value = True

        args = self.create_namespace(
            tools_action="install-precommit", update=update_flag
        )

        result = ToolsCommand.handle(args)

        assert result == 0
        assert "Pre-commit hooks installed and configured successfully!" in caplog.text

        if update_flag:
            assert "Updating pre-commit hooks to latest versions..." in caplog.text
        else:
            assert "Updating pre-commit hooks to latest versions..." not in caplog.text

    # =============================================================================
    # EDGE CASE TESTS
    # =============================================================================

    def test_tools_command_with_empty_subprocess_output(self, mock_subprocess, caplog):
        """Test tools command handling of empty subprocess outputs."""
        # Mock empty outputs for various commands
        mock_subprocess.run.return_value = MagicMock(
            returncode=0, stdout="", stderr=""  # Empty output
        )

        args = self.create_namespace(tools_action="list")

        result = ToolsCommand.handle(args)

        assert result == 0
        # Should handle empty outputs gracefully
        assert "PANTHER Tools Status" in caplog.text

    def test_install_slim_with_malformed_subprocess_output(
        self, mock_subprocess, caplog
    ):
        """Test install-slim with malformed subprocess outputs."""
        # Mock malformed outputs
        mock_subprocess.run.side_effect = [
            MagicMock(returncode=1, stdout=b"", stderr=b""),  # which slim fails
            MagicMock(
                returncode=0, stdout=b"weird\noutput\nformat\n", stderr=b""
            ),  # verification with strange output
        ]

        # Mock Popen for installation pipeline
        mock_curl_proc = MagicMock()
        mock_bash_proc = MagicMock()
        mock_bash_proc.communicate.return_value = (b"Strange output", b"")
        mock_subprocess.Popen.side_effect = [mock_curl_proc, mock_bash_proc]

        args = self.create_namespace(tools_action="install-slim", force=False)

        result = ToolsCommand.handle(args)

        assert result == 0
        assert (
            "slim installed successfully at: weird" in caplog.text
        )  # Should handle first line of output

    def test_unicode_handling_in_subprocess_output(self, mock_subprocess, caplog):
        """Test handling of unicode characters in subprocess output."""
        # Mock unicode outputs
        mock_subprocess.run.side_effect = [
            MagicMock(
                returncode=0, stdout="tëst-tööl\n", stderr=""
            ),  # unicode in tool path
            MagicMock(
                returncode=0, stdout="vërsiön 1.2.3 with spëcial chars\n", stderr=""
            ),  # unicode in version
        ] * 9  # For all tools in list

        args = self.create_namespace(tools_action="list")

        result = ToolsCommand.handle(args)

        assert result == 0
        # Should handle unicode gracefully
        assert "PANTHER Tools Status" in caplog.text

    def test_very_long_subprocess_output(self, mock_subprocess, caplog):
        """Test handling of very long subprocess outputs."""
        # Mock very long outputs
        long_output = "a" * 10000 + " version 1.2.3 " + "b" * 10000
        mock_subprocess.run.side_effect = [
            MagicMock(returncode=0, stdout="tool\n", stderr=""),
            MagicMock(returncode=0, stdout=long_output, stderr=""),
        ] * 9  # For all tools in list

        args = self.create_namespace(tools_action="list")

        result = ToolsCommand.handle(args)

        assert result == 0
        # Should extract version correctly even from long output
        assert "1.2.3" in caplog.text

    # =============================================================================
    # INTEGRATION TESTS
    # =============================================================================

    def test_end_to_end_tools_workflow(
        self, mock_subprocess, mock_path_operations, caplog
    ):
        """Test complete tools workflow: list → install-slim → install-precommit → list."""
        mock_path_class, mock_path_instance = mock_path_operations

        # Setup subprocess mocks for the complete workflow
        mock_subprocess.run.side_effect = [
            # First list command - slim and pre-commit not found
            MagicMock(returncode=1, stdout="", stderr=""),  # slim not found
            MagicMock(returncode=1, stdout="", stderr=""),  # pre-commit not found
            MagicMock(returncode=0, stdout="docker\n", stderr=""),  # docker found
            MagicMock(returncode=0, stdout="mkdocs\n", stderr=""),  # mkdocs found
            MagicMock(returncode=0, stdout="pytest\n", stderr=""),  # pytest found
            MagicMock(returncode=0, stdout="black\n", stderr=""),  # black found
            MagicMock(returncode=0, stdout="isort\n", stderr=""),  # isort found
            MagicMock(returncode=0, stdout="flake8\n", stderr=""),  # flake8 found
            MagicMock(returncode=0, stdout="mypy\n", stderr=""),  # mypy found
            # Version calls for found tools
            MagicMock(returncode=0, stdout="Docker version 24.0.6\n", stderr=""),
            MagicMock(returncode=0, stdout="mkdocs 1.5.3\n", stderr=""),
            MagicMock(returncode=0, stdout="pytest 7.4.3\n", stderr=""),
            MagicMock(returncode=0, stdout="black 23.7.0\n", stderr=""),
            MagicMock(returncode=0, stdout="isort 5.12.0\n", stderr=""),
            MagicMock(returncode=0, stdout="flake8 6.1.0\n", stderr=""),
            MagicMock(returncode=0, stdout="mypy 1.5.1\n", stderr=""),
            # Install slim workflow
            MagicMock(returncode=1, stdout=b"", stderr=b""),  # which slim (not found)
            MagicMock(
                returncode=0, stdout=b"/usr/local/bin/slim\n", stderr=b""
            ),  # verification after install
            # Install precommit workflow
            MagicMock(returncode=0, stdout=b"", stderr=b""),  # pip install pre-commit
            MagicMock(returncode=0, stdout=b"", stderr=b""),  # pre-commit install
            # Final list command - now with slim and pre-commit installed
            MagicMock(returncode=0, stdout="slim\n", stderr=""),  # slim now found
            MagicMock(
                returncode=0, stdout="pre-commit\n", stderr=""
            ),  # pre-commit now found
            MagicMock(returncode=0, stdout="docker\n", stderr=""),  # docker still found
            MagicMock(returncode=0, stdout="mkdocs\n", stderr=""),  # mkdocs still found
            MagicMock(returncode=0, stdout="pytest\n", stderr=""),  # pytest still found
            MagicMock(returncode=0, stdout="black\n", stderr=""),  # black still found
            MagicMock(returncode=0, stdout="isort\n", stderr=""),  # isort still found
            MagicMock(returncode=0, stdout="flake8\n", stderr=""),  # flake8 still found
            MagicMock(returncode=0, stdout="mypy\n", stderr=""),  # mypy still found
            # Version calls for all tools
            MagicMock(returncode=0, stdout="slim 1.40.11\n", stderr=""),
            MagicMock(returncode=0, stdout="pre-commit 3.5.0\n", stderr=""),
            MagicMock(returncode=0, stdout="Docker version 24.0.6\n", stderr=""),
            MagicMock(returncode=0, stdout="mkdocs 1.5.3\n", stderr=""),
            MagicMock(returncode=0, stdout="pytest 7.4.3\n", stderr=""),
            MagicMock(returncode=0, stdout="black 23.7.0\n", stderr=""),
            MagicMock(returncode=0, stdout="isort 5.12.0\n", stderr=""),
            MagicMock(returncode=0, stdout="flake8 6.1.0\n", stderr=""),
            MagicMock(returncode=0, stdout="mypy 1.5.1\n", stderr=""),
        ]

        # Mock Popen for slim installation
        mock_curl_proc = MagicMock()
        mock_bash_proc = MagicMock()
        mock_bash_proc.communicate.return_value = (b"Installation output", b"")
        mock_subprocess.Popen.side_effect = [mock_curl_proc, mock_bash_proc]

        # Mock git repo detection for precommit
        git_dir = MagicMock()
        git_dir.exists.return_value = True
        mock_path_instance.__truediv__.return_value = git_dir

        # Mock precommit config file exists
        config_file = MagicMock()
        config_file.exists.return_value = True

        # Step 1: List tools (before installation)
        args_list1 = self.create_namespace(tools_action="list")
        result = ToolsCommand.handle(args_list1)
        assert result == 0
        assert "❌ slim" in caplog.text
        assert "❌ pre-commit" in caplog.text

        # Step 2: Install slim
        args_slim = self.create_namespace(tools_action="install-slim", force=False)
        result = ToolsCommand.handle(args_slim)
        assert result == 0
        assert "slim installed successfully" in caplog.text

        # Step 3: Install precommit
        args_precommit = self.create_namespace(
            tools_action="install-precommit", update=False
        )
        result = ToolsCommand.handle(args_precommit)
        assert result == 0
        assert "Pre-commit hooks installed and configured successfully!" in caplog.text

        # Step 4: List tools again (after installation)
        args_list2 = self.create_namespace(tools_action="list")
        result = ToolsCommand.handle(args_list2)
        assert result == 0
        assert "✅ slim" in caplog.text
        assert "✅ pre-commit" in caplog.text

    def test_tools_command_comprehensive_parameters(
        self, mock_subprocess, mock_path_operations, caplog
    ):
        """Test tools command with comprehensive parameter combinations."""
        mock_path_class, mock_path_instance = mock_path_operations

        # Test all actions and parameter combinations
        test_cases = [
            # List command
            {"tools_action": "list"},
            # Install-slim variations
            {"tools_action": "install-slim", "force": False},
            {"tools_action": "install-slim", "force": True},
            # Install-precommit variations
            {"tools_action": "install-precommit", "update": False},
            {"tools_action": "install-precommit", "update": True},
        ]

        # Setup mocks for all test cases
        mock_subprocess.run.side_effect = [
            # Mock responses for each test case
            # List command
            MagicMock(returncode=0, stdout="tool\n", stderr=""),  # Tool check
            MagicMock(
                returncode=0, stdout="version 1.0.0\n", stderr=""
            ),  # Version check
        ] * 9 + [  # 9 tools in list
            # Install-slim (force=False) - already installed
            MagicMock(returncode=0, stdout=b"/usr/local/bin/slim\n", stderr=b""),
            # Install-slim (force=True) - reinstall
            MagicMock(
                returncode=0, stdout=b"/usr/local/bin/slim\n", stderr=b""
            ),  # verification
            # Install-precommit (update=False)
            MagicMock(returncode=0, stdout=b"", stderr=b""),  # pip install
            MagicMock(returncode=0, stdout=b"", stderr=b""),  # pre-commit install
            # Install-precommit (update=True)
            MagicMock(returncode=0, stdout=b"", stderr=b""),  # pip install
            MagicMock(returncode=0, stdout=b"", stderr=b""),  # pre-commit install
            MagicMock(returncode=0, stdout=b"", stderr=b""),  # autoupdate
        ]

        # Mock Popen for slim installations
        mock_curl_proc = MagicMock()
        mock_bash_proc = MagicMock()
        mock_bash_proc.communicate.return_value = (b"Installation output", b"")
        mock_subprocess.Popen.side_effect = [mock_curl_proc, mock_bash_proc]

        # Mock git repo detection
        git_dir = MagicMock()
        git_dir.exists.return_value = True
        mock_path_instance.__truediv__.return_value = git_dir

        # Mock precommit config file exists
        config_file = MagicMock()
        config_file.exists.return_value = True

        # Test each case
        for test_case in test_cases:
            args = self.create_namespace(**test_case)
            result = ToolsCommand.handle(args)
            assert result == 0

        # Verify expected log messages
        assert "PANTHER Tools Status" in caplog.text  # List command
        assert "slim is already installed" in caplog.text  # Install-slim without force
        assert (
            "Downloading and installing slim..." in caplog.text
        )  # Install-slim with force
        assert (
            "Pre-commit hooks installed and configured successfully!" in caplog.text
        )  # Install-precommit
        assert (
            "Updating pre-commit hooks to latest versions..." in caplog.text
        )  # Install-precommit with update

    def test_tools_error_recovery_scenarios(
        self, mock_subprocess, mock_path_operations, caplog
    ):
        """Test tools command error recovery scenarios."""
        mock_path_class, mock_path_instance = mock_path_operations

        # Scenario 1: Install slim fails but system continues
        mock_subprocess.run.side_effect = [
            MagicMock(returncode=1, stdout=b"", stderr=b""),  # which slim fails
            MagicMock(returncode=1, stdout=b"", stderr=b""),  # verification also fails
        ]

        # Mock Popen for installation pipeline
        mock_curl_proc = MagicMock()
        mock_bash_proc = MagicMock()
        mock_bash_proc.communicate.return_value = (b"Installation output", b"")
        mock_subprocess.Popen.side_effect = [mock_curl_proc, mock_bash_proc]

        args_fail = self.create_namespace(tools_action="install-slim", force=False)
        result = ToolsCommand.handle(args_fail)
        assert result == 1
        assert "slim installation failed" in caplog.text

        # Scenario 2: Precommit pip install fails but gracefully handled
        mock_subprocess.run.side_effect = [
            MagicMock(
                returncode=1, stdout=b"", stderr=b"Package not found"
            )  # pip install fails
        ]

        args_pip_fail = self.create_namespace(
            tools_action="install-precommit", update=False
        )
        result = ToolsCommand.handle(args_pip_fail)
        assert result == 1
        assert "Failed to install pre-commit package" in caplog.text

        # Scenario 3: List command with all tools missing
        mock_subprocess.run.side_effect = [
            MagicMock(returncode=1, stdout="", stderr="")  # All tools not found
        ] * 9

        args_all_missing = self.create_namespace(tools_action="list")
        result = ToolsCommand.handle(args_all_missing)
        assert result == 0  # Should still succeed
        assert "❌" in caplog.text  # Should show missing tools
        assert "not found" in caplog.text
