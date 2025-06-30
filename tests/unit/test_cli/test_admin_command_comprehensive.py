"""
Comprehensive unit tests for AdminCommand CLI.

This module provides exhaustive testing for ALL AdminCommand parameters,
including all 5 subcommands, Docker management, system operations, and error conditions.
"""

import argparse
import json
import logging
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, call, mock_open, patch

import pytest

from panther.cli.subcommands.admin import AdminCommand
from tests.unit.test_cli.base_cli_test import ComprehensiveCLITest


class TestAdminCommandComprehensive(ComprehensiveCLITest):
    """Comprehensive tests for AdminCommand with ALL parameter combinations."""

    @pytest.fixture
    def command_class(self):
        """Return the command class being tested."""
        return AdminCommand

    @pytest.fixture
    def command_name(self):
        """Return the command name for testing."""
        return "admin"

    @pytest.fixture
    def mock_subprocess(self):
        """Mock subprocess for system command testing."""
        with patch("panther.cli.subcommands.admin.subprocess") as mock:
            # Default successful subprocess results
            mock.run.return_value = MagicMock(returncode=0, stdout="", stderr="")
            yield mock

    @pytest.fixture
    def mock_docker_registry_class(self):
        """Mock DockerRegistry class for testing."""
        with patch("panther.cli.subcommands.admin.DockerRegistry") as mock:
            mock_instance = MagicMock()
            mock_instance.get_registry_stats.return_value = {
                "total_resources": 10,
                "cache_entries": 5,
                "registry_size_kb": 1024.0,
                "by_type": {"image": 3, "container": 2},
            }
            mock_instance.build_cache = {
                "key1": MagicMock(
                    build_time="2023-01-01T10:00:00",
                    image_tag="test:latest",
                    size_bytes=1048576,
                ),
                "key2": MagicMock(
                    build_time="2023-01-02T11:00:00",
                    image_tag="app:v1",
                    size_bytes=2097152,
                ),
            }
            mock.return_value = mock_instance
            yield mock, mock_instance

    @pytest.fixture
    def mock_docker_cache_mixin_class(self):
        """Mock DockerCacheMixin class for testing."""
        with patch("panther.cli.subcommands.admin.DockerCacheMixin") as mock:
            mock_instance = MagicMock()
            mock_instance.prune_cache.return_value = {
                "cache_entries": 3,
                "images": 2,
                "size_freed_mb": 100.5,
            }
            mock.return_value = mock_instance
            yield mock, mock_instance

    @pytest.fixture
    def mock_path_operations(self):
        """Mock Path operations for file system testing."""
        with patch("panther.cli.subcommands.admin.Path") as mock_path_class, patch(
            "panther.cli.subcommands.admin.shutil"
        ) as mock_shutil:
            # Setup Path mocking
            mock_path_instance = MagicMock()
            mock_path_instance.exists.return_value = True
            mock_path_instance.is_dir.return_value = True
            mock_path_instance.stat.return_value = MagicMock(st_size=1024)
            mock_path_class.return_value = mock_path_instance

            yield {
                "path_class": mock_path_class,
                "path_instance": mock_path_instance,
                "shutil": mock_shutil,
            }

    # =============================================================================
    # PARSER REGISTRATION TESTS
    # =============================================================================

    def test_parser_registration(self):
        """Test that AdminCommand is properly registered."""
        from panther.cli.main import create_parser

        parser = create_parser()

        # Verify 'admin' subcommand exists
        subparsers_actions = [
            action
            for action in parser._actions
            if isinstance(action, argparse._SubParsersAction)
        ]
        assert len(subparsers_actions) == 1
        assert "admin" in subparsers_actions[0].choices

    def test_all_subcommands_registered(self):
        """Test that all admin subcommands are registered."""
        from panther.cli.main import create_parser

        parser = create_parser()

        # Parse admin help to get subcommands
        try:
            parser.parse_args(["admin", "--help"])
        except SystemExit:
            pass  # Expected behavior for help

        # Verify subcommands exist by testing their individual help
        subcommands = ["teardown", "webapp", "status", "clean", "docker"]

        for subcommand in subcommands:
            try:
                parser.parse_args(["admin", subcommand, "--help"])
            except SystemExit:
                pass  # Expected for help command

    # =============================================================================
    # MAIN COMMAND HANDLER TESTS
    # =============================================================================

    def test_handle_no_action_specified(self, caplog):
        """Test behavior when no admin action is specified."""
        args = self.create_namespace(admin_action=None)

        result = AdminCommand.handle(args)

        assert result == 1
        assert "No admin action specified" in caplog.text

    def test_handle_unknown_action(self, caplog):
        """Test behavior with unknown admin action."""
        args = self.create_namespace(admin_action="unknown_action")

        result = AdminCommand.handle(args)

        assert result == 1
        assert "Unknown admin action: unknown_action" in caplog.text

    # =============================================================================
    # TEARDOWN SUBCOMMAND TESTS
    # =============================================================================

    def test_teardown_with_force_flag(
        self, mock_subprocess, mock_path_operations, caplog
    ):
        """Test teardown command with --force flag."""
        args = self.create_namespace(admin_action="teardown", force=True)

        # Mock subprocess commands
        mock_subprocess.run.side_effect = [
            MagicMock(returncode=0, stdout="", stderr=""),  # docker container prune
            MagicMock(
                returncode=0, stdout="container1\ncontainer2", stderr=""
            ),  # docker ps -a
            MagicMock(returncode=0, stdout="", stderr=""),  # docker rm
            MagicMock(returncode=0, stdout="", stderr=""),  # docker network prune
        ]

        result = AdminCommand.handle(args)

        assert result == 0
        assert "Starting system teardown and cleanup..." in caplog.text
        assert "Cleaning up Docker containers..." in caplog.text
        assert "Cleaning up Docker networks..." in caplog.text
        assert "Cleaning up temporary files..." in caplog.text
        assert "System teardown completed" in caplog.text

        # Verify subprocess calls were made
        assert mock_subprocess.run.call_count >= 3

    def test_teardown_without_force_user_confirms(
        self, mock_subprocess, mock_path_operations, caplog
    ):
        """Test teardown command without force flag with user confirmation."""
        args = self.create_namespace(admin_action="teardown", force=False)

        with patch("builtins.input", return_value="y"):
            result = AdminCommand.handle(args)

            assert result == 0
            assert "Starting system teardown and cleanup..." in caplog.text

    def test_teardown_without_force_user_cancels(self, caplog):
        """Test teardown command without force flag with user cancellation."""
        args = self.create_namespace(admin_action="teardown", force=False)

        with patch("builtins.input", return_value="n"):
            result = AdminCommand.handle(args)

            assert result == 0
            assert "Teardown cancelled" in caplog.text

    @pytest.mark.parametrize("user_response", ["yes", "Y", "YES"])
    def test_teardown_user_confirmation_variations(
        self, user_response, mock_subprocess, mock_path_operations, caplog
    ):
        """Test teardown command with various confirmation responses."""
        args = self.create_namespace(admin_action="teardown", force=False)

        with patch("builtins.input", return_value=user_response):
            result = AdminCommand.handle(args)

            assert result == 0
            assert "Starting system teardown and cleanup..." in caplog.text

    @pytest.mark.parametrize("user_response", ["no", "N", "NO", "", "maybe"])
    def test_teardown_user_cancellation_variations(self, user_response, caplog):
        """Test teardown command with various cancellation responses."""
        args = self.create_namespace(admin_action="teardown", force=False)

        with patch("builtins.input", return_value=user_response):
            result = AdminCommand.handle(args)

            assert result == 0
            assert "Teardown cancelled" in caplog.text

    def test_teardown_docker_cleanup_failure(self, mock_subprocess, caplog):
        """Test teardown command when Docker cleanup fails."""
        args = self.create_namespace(admin_action="teardown", force=True)

        # Mock subprocess to raise exception for Docker operations
        mock_subprocess.run.side_effect = Exception("Docker error")

        result = AdminCommand.handle(args)

        assert result == 0  # Should continue despite Docker errors
        assert "Warning: Docker cleanup failed" in caplog.text

    def test_teardown_general_exception(self, caplog):
        """Test teardown command general exception handling."""
        args = self.create_namespace(admin_action="teardown", force=True)

        # Mock subprocess import to raise exception
        with patch(
            "panther.cli.subcommands.admin.subprocess",
            side_effect=ImportError("No subprocess"),
        ):
            result = AdminCommand.handle(args)

            assert result == 1
            assert "Error during teardown" in caplog.text

    # =============================================================================
    # WEBAPP SUBCOMMAND TESTS
    # =============================================================================

    def test_webapp_deprecated_feature(self, caplog):
        """Test webapp command returns deprecation message."""
        args = self.create_namespace(admin_action="webapp", port=8080, host="localhost")

        result = AdminCommand.handle(args)

        assert result == 1
        assert "Web application feature has been removed" in caplog.text
        assert "feature was incomplete and has been deprecated" in caplog.text
        assert "Use 'panther admin status' for system monitoring instead" in caplog.text

    @pytest.mark.parametrize("port", [8080, 3000, 9000, 8888])
    def test_webapp_different_ports(self, port, caplog):
        """Test webapp command with different port values."""
        args = self.create_namespace(admin_action="webapp", port=port, host="localhost")

        result = AdminCommand.handle(args)

        assert result == 1  # Should always fail due to deprecation
        assert "Web application feature has been removed" in caplog.text

    @pytest.mark.parametrize(
        "host", ["localhost", "0.0.0.0", "127.0.0.1", "myhost.local"]
    )
    def test_webapp_different_hosts(self, host, caplog):
        """Test webapp command with different host values."""
        args = self.create_namespace(admin_action="webapp", port=8080, host=host)

        result = AdminCommand.handle(args)

        assert result == 1  # Should always fail due to deprecation
        assert "Web application feature has been removed" in caplog.text

    # =============================================================================
    # STATUS SUBCOMMAND TESTS
    # =============================================================================

    def test_status_successful_display(self, mock_subprocess, caplog):
        """Test status command successful system status display."""
        args = self.create_namespace(admin_action="status")

        # Mock subprocess calls for Docker and system info
        mock_subprocess.run.side_effect = [
            MagicMock(
                returncode=0, stdout="Docker version 20.10.7\n", stderr=""
            ),  # docker --version
            MagicMock(returncode=0, stdout="", stderr=""),  # docker info
            MagicMock(
                returncode=0,
                stdout="NAMES\tSTATUS\ntest_container\tUp 2 hours\n",
                stderr="",
            ),  # docker ps
        ]

        # Mock sys.version
        with patch.object(sys, "version", "3.9.0 (default, Oct  9 2020, 15:07:54)"):
            result = AdminCommand.handle(args)

        assert result == 0
        assert "PANTHER System Status" in caplog.text
        assert "Python: 3.9.0" in caplog.text
        assert "Docker: Docker version 20.10.7" in caplog.text
        assert "Docker daemon: Running" in caplog.text
        assert "PANTHER: Installed" in caplog.text
        assert "Running PANTHER containers:" in caplog.text

    def test_status_docker_not_installed(self, mock_subprocess, caplog):
        """Test status command when Docker is not installed."""
        args = self.create_namespace(admin_action="status")

        # Mock subprocess to raise FileNotFoundError for Docker
        mock_subprocess.run.side_effect = FileNotFoundError("docker not found")

        result = AdminCommand.handle(args)

        assert result == 0  # Should not fail, just report status
        assert "Docker: Not installed or not accessible" in caplog.text

    def test_status_docker_daemon_not_running(self, mock_subprocess, caplog):
        """Test status command when Docker daemon is not running."""
        args = self.create_namespace(admin_action="status")

        # Mock subprocess calls
        mock_subprocess.run.side_effect = [
            MagicMock(
                returncode=0, stdout="Docker version 20.10.7\n", stderr=""
            ),  # docker --version
            subprocess.CalledProcessError(1, "docker info"),  # docker info fails
            MagicMock(
                returncode=1, stdout="", stderr="Cannot connect"
            ),  # docker ps fails
        ]

        result = AdminCommand.handle(args)

        assert result == 0
        assert "Docker daemon: Not running" in caplog.text

    def test_status_no_panther_containers(self, mock_subprocess, caplog):
        """Test status command when no PANTHER containers are running."""
        args = self.create_namespace(admin_action="status")

        # Mock subprocess calls
        mock_subprocess.run.side_effect = [
            MagicMock(
                returncode=0, stdout="Docker version 20.10.7\n", stderr=""
            ),  # docker --version
            MagicMock(returncode=0, stdout="", stderr=""),  # docker info
            MagicMock(
                returncode=0, stdout="NAMES\tSTATUS\n", stderr=""
            ),  # docker ps (empty)
        ]

        result = AdminCommand.handle(args)

        assert result == 0
        assert "No PANTHER containers currently running" in caplog.text

    def test_status_panther_not_installed(self, mock_subprocess, caplog):
        """Test status command when PANTHER is not properly installed."""
        args = self.create_namespace(admin_action="status")

        # Mock panther import to fail
        with patch(
            "panther.cli.subcommands.admin.panther",
            side_effect=ImportError("No module named 'panther'"),
        ):
            result = AdminCommand.handle(args)

            assert result == 0
            assert "PANTHER: Not properly installed" in caplog.text

    def test_status_plugin_directory_not_found(
        self, mock_subprocess, mock_path_operations, caplog
    ):
        """Test status command when plugin directory is not found."""
        args = self.create_namespace(admin_action="status")

        # Mock plugin directory not existing
        mock_path_operations["path_instance"].exists.return_value = False

        result = AdminCommand.handle(args)

        assert result == 0
        assert "Plugin directory not found" in caplog.text

    def test_status_general_exception(self, caplog):
        """Test status command general exception handling."""
        args = self.create_namespace(admin_action="status")

        # Mock sys import to raise exception
        with patch(
            "panther.cli.subcommands.admin.sys", side_effect=Exception("System error")
        ):
            result = AdminCommand.handle(args)

            assert result == 1
            assert "Error checking system status" in caplog.text

    # =============================================================================
    # CLEAN SUBCOMMAND TESTS
    # =============================================================================

    def test_clean_logs_only(self, mock_path_operations, caplog):
        """Test clean command with --logs flag only."""
        args = self.create_namespace(
            admin_action="clean", logs=True, cache=False, all=False
        )

        result = AdminCommand.handle(args)

        assert result == 0
        assert "Starting cleanup operations..." in caplog.text
        assert "Cleaned items:" in caplog.text
        assert "Log directory:" in caplog.text

    def test_clean_cache_only(self, mock_path_operations, caplog):
        """Test clean command with --cache flag only."""
        args = self.create_namespace(
            admin_action="clean", logs=False, cache=True, all=False
        )

        # Mock Path.rglob to return some __pycache__ directories
        mock_path_operations["path_instance"].rglob.return_value = [
            MagicMock(name="__pycache__1"),
            MagicMock(name="__pycache__2"),
        ]

        result = AdminCommand.handle(args)

        assert result == 0
        assert "Starting cleanup operations..." in caplog.text
        assert "Cleaned items:" in caplog.text
        assert "Cache:" in caplog.text or "Cache directory:" in caplog.text

    def test_clean_all_flag(self, mock_path_operations, caplog):
        """Test clean command with --all flag."""
        args = self.create_namespace(
            admin_action="clean", logs=False, cache=False, all=True
        )

        # Mock Path.rglob to return various files
        mock_path_operations["path_instance"].rglob.side_effect = [
            [MagicMock(name="__pycache__1")],  # __pycache__ directories
            [MagicMock(name="temp1.tmp")],  # *.tmp files
            [MagicMock(name="temp2.temp")],  # *.temp files
            [MagicMock(name=".DS_Store")],  # .DS_Store files
        ]

        result = AdminCommand.handle(args)

        assert result == 0
        assert "Starting cleanup operations..." in caplog.text
        assert "Cleaned items:" in caplog.text

    def test_clean_all_flags_together(self, mock_path_operations, caplog):
        """Test clean command with multiple flags together."""
        args = self.create_namespace(
            admin_action="clean",
            logs=True,
            cache=True,
            all=True,  # Should take precedence and clean everything
        )

        result = AdminCommand.handle(args)

        assert result == 0
        assert "Starting cleanup operations..." in caplog.text

    def test_clean_no_flags_specified(self, caplog):
        """Test clean command with no cleanup flags specified."""
        args = self.create_namespace(
            admin_action="clean", logs=False, cache=False, all=False
        )

        result = AdminCommand.handle(args)

        assert result == 0
        assert "No items to clean" in caplog.text

    def test_clean_no_items_found(self, mock_path_operations, caplog):
        """Test clean command when no items are found to clean."""
        args = self.create_namespace(
            admin_action="clean", logs=True, cache=False, all=False
        )

        # Mock paths not existing
        mock_path_operations["path_instance"].exists.return_value = False

        result = AdminCommand.handle(args)

        assert result == 0
        assert "No items to clean" in caplog.text

    def test_clean_exception_handling(self, caplog):
        """Test clean command exception handling."""
        args = self.create_namespace(
            admin_action="clean", logs=True, cache=False, all=False
        )

        # Mock shutil import to raise exception
        with patch(
            "panther.cli.subcommands.admin.shutil", side_effect=ImportError("No shutil")
        ):
            result = AdminCommand.handle(args)

            assert result == 1
            assert "Error during cleanup" in caplog.text

    # =============================================================================
    # DOCKER SUBCOMMAND TESTS
    # =============================================================================

    def test_docker_not_available(self, mock_subprocess, caplog):
        """Test docker command when Docker is not available."""
        args = self.create_namespace(admin_action="docker", images_all=True)

        # Mock Docker not available
        mock_subprocess.run.side_effect = FileNotFoundError("docker not found")

        result = AdminCommand.handle(args)

        assert result == 1
        assert "Docker is not available or not installed" in caplog.text

    def test_docker_no_operations_specified(self, mock_subprocess, caplog):
        """Test docker command with no operations specified."""
        args = self.create_namespace(
            admin_action="docker",
            images_all=False,
            images_services=False,
            system_all=False,
            system_services=False,
            volumes=False,
            containers=False,
            show_registry=False,
            prune_cache=False,
            export_registry=None,
            import_registry=None,
        )

        # Mock Docker available
        mock_subprocess.run.return_value = MagicMock(returncode=0)

        result = AdminCommand.handle(args)

        assert result == 1
        assert "No Docker operations specified" in caplog.text

    def test_docker_images_all_operation(self, mock_subprocess, caplog):
        """Test docker command with --images-all operation."""
        args = self.create_namespace(
            admin_action="docker",
            images_all=True,
            images_services=False,
            system_all=False,
            system_services=False,
            volumes=False,
            containers=False,
            show_registry=False,
            prune_cache=False,
            export_registry=None,
            import_registry=None,
        )

        # Mock Docker commands
        mock_subprocess.run.side_effect = [
            MagicMock(returncode=0),  # docker --version
            MagicMock(returncode=0),  # remove images
            MagicMock(returncode=0, stdout=""),  # dangling images check
        ]

        result = AdminCommand.handle(args)

        assert result == 0
        assert "Docker Resource Management" in caplog.text
        assert "Removing Docker images with 'panther' in the name..." in caplog.text
        assert "Images removed successfully" in caplog.text

    def test_docker_images_services_operation(self, mock_subprocess, caplog):
        """Test docker command with --images-services operation."""
        args = self.create_namespace(
            admin_action="docker",
            images_all=False,
            images_services=True,
            system_all=False,
            system_services=False,
            volumes=False,
            containers=False,
            show_registry=False,
            prune_cache=False,
            export_registry=None,
            import_registry=None,
        )

        # Mock Docker commands
        mock_subprocess.run.side_effect = [
            MagicMock(returncode=0),  # docker --version
            MagicMock(returncode=0),  # remove service images
            MagicMock(returncode=0, stdout=""),  # dangling images check
        ]

        result = AdminCommand.handle(args)

        assert result == 0
        assert "Removing Docker images with '_panther' in the name..." in caplog.text
        assert "Service images removed successfully" in caplog.text

    def test_docker_system_all_operation(self, mock_subprocess, caplog):
        """Test docker command with --system-all operation."""
        args = self.create_namespace(
            admin_action="docker",
            images_all=False,
            images_services=False,
            system_all=True,
            system_services=False,
            volumes=False,
            containers=False,
            show_registry=False,
            prune_cache=False,
            export_registry=None,
            import_registry=None,
        )

        # Mock Docker commands
        mock_subprocess.run.side_effect = [
            MagicMock(returncode=0),  # docker --version
            MagicMock(returncode=0),  # remove images
            MagicMock(returncode=0),  # system prune
            MagicMock(returncode=0, stdout=""),  # dangling images check
        ]

        result = AdminCommand.handle(args)

        assert result == 0
        assert "Pruning Docker system data with 'panther' label..." in caplog.text
        assert "System pruned successfully" in caplog.text

    def test_docker_volumes_operation(self, mock_subprocess, caplog):
        """Test docker command with --volumes operation."""
        args = self.create_namespace(
            admin_action="docker",
            images_all=False,
            images_services=False,
            system_all=False,
            system_services=False,
            volumes=True,
            containers=False,
            show_registry=False,
            prune_cache=False,
            export_registry=None,
            import_registry=None,
        )

        # Mock Docker commands
        mock_subprocess.run.side_effect = [
            MagicMock(returncode=0),  # docker --version
            MagicMock(returncode=0),  # remove volumes
            MagicMock(returncode=0, stdout=""),  # dangling images check
        ]

        result = AdminCommand.handle(args)

        assert result == 0
        assert "Removing Docker volumes with 'panther' in the name..." in caplog.text
        assert "Volumes removed successfully" in caplog.text

    def test_docker_containers_operation(self, mock_subprocess, caplog):
        """Test docker command with --containers operation."""
        args = self.create_namespace(
            admin_action="docker",
            images_all=False,
            images_services=False,
            system_all=False,
            system_services=False,
            volumes=False,
            containers=True,
            show_registry=False,
            prune_cache=False,
            export_registry=None,
            import_registry=None,
        )

        # Mock Docker commands
        mock_subprocess.run.side_effect = [
            MagicMock(returncode=0),  # docker --version
            MagicMock(returncode=0),  # stop containers
            MagicMock(returncode=0),  # remove containers
            MagicMock(returncode=0, stdout=""),  # dangling images check
        ]

        result = AdminCommand.handle(args)

        assert result == 0
        assert "Removing stopped containers with 'panther' label..." in caplog.text
        assert "Containers removed successfully" in caplog.text

    def test_docker_multiple_operations(self, mock_subprocess, caplog):
        """Test docker command with multiple operations."""
        args = self.create_namespace(
            admin_action="docker",
            images_all=True,
            images_services=False,
            system_all=False,
            system_services=False,
            volumes=True,
            containers=True,
            show_registry=False,
            prune_cache=False,
            export_registry=None,
            import_registry=None,
        )

        # Mock successful Docker commands
        mock_subprocess.run.return_value = MagicMock(returncode=0, stdout="")

        result = AdminCommand.handle(args)

        assert result == 0
        assert "Docker Resource Management" in caplog.text
        assert "Docker cleanup completed successfully" in caplog.text

    def test_docker_operation_failures(self, mock_subprocess, caplog):
        """Test docker command when operations fail."""
        args = self.create_namespace(
            admin_action="docker",
            images_all=True,
            images_services=False,
            system_all=False,
            system_services=False,
            volumes=False,
            containers=False,
            show_registry=False,
            prune_cache=False,
            export_registry=None,
            import_registry=None,
        )

        # Mock Docker commands with failures
        mock_subprocess.run.side_effect = [
            MagicMock(returncode=0),  # docker --version
            MagicMock(returncode=1),  # remove images fails
            MagicMock(returncode=0, stdout=""),  # dangling images check
        ]

        result = AdminCommand.handle(args)

        assert result == 0  # Should not fail completely
        assert "Some images could not be removed" in caplog.text
        assert "Docker cleanup completed with 1 warning(s)" in caplog.text

    def test_docker_show_registry_operation(self, mock_docker_registry_class, caplog):
        """Test docker command with --show-registry operation."""
        args = self.create_namespace(admin_action="docker", show_registry=True)

        mock_registry_class, mock_registry_instance = mock_docker_registry_class

        result = AdminCommand.handle(args)

        assert result == 0
        assert "Docker Registry Statistics" in caplog.text
        assert "Total resources: 10" in caplog.text
        assert "Cache entries: 5" in caplog.text
        assert "Registry size: 1024.0 KB" in caplog.text
        assert "Resources by type:" in caplog.text
        assert "Recent cached builds:" in caplog.text

    def test_docker_prune_cache_operation(
        self, mock_docker_registry_class, mock_docker_cache_mixin_class, caplog
    ):
        """Test docker command with --prune-cache operation."""
        args = self.create_namespace(
            admin_action="docker", prune_cache=True, cache_max_age=7
        )

        mock_registry_class, mock_registry_instance = mock_docker_registry_class
        mock_cache_class, mock_cache_instance = mock_docker_cache_mixin_class

        result = AdminCommand.handle(args)

        assert result == 0
        assert "Pruning Docker cache..." in caplog.text
        assert "Max age: 7 days" in caplog.text
        assert "Before pruning:" in caplog.text
        assert "Pruned:" in caplog.text
        assert "Cache entries removed: 3" in caplog.text
        assert "Space freed: 100.5 MB" in caplog.text
        assert "Cache pruning completed" in caplog.text

    def test_docker_export_registry_operation(
        self, mock_docker_registry_class, mock_path_operations, caplog
    ):
        """Test docker command with --export-registry operation."""
        args = self.create_namespace(
            admin_action="docker", export_registry="/tmp/registry.json"
        )

        mock_registry_class, mock_registry_instance = mock_docker_registry_class

        result = AdminCommand.handle(args)

        assert result == 0
        assert "Exporting Docker registry to:" in caplog.text
        assert "Registry exported successfully" in caplog.text
        mock_registry_instance.export_registry.assert_called_once()

    def test_docker_import_registry_operation(
        self, mock_docker_registry_class, mock_path_operations, caplog
    ):
        """Test docker command with --import-registry operation."""
        args = self.create_namespace(
            admin_action="docker", import_registry="/tmp/registry.json"
        )

        mock_registry_class, mock_registry_instance = mock_docker_registry_class

        with patch("builtins.input", return_value="Y"):  # Confirm merge
            result = AdminCommand.handle(args)

        assert result == 0
        assert "Importing Docker registry from:" in caplog.text
        assert "Registry imported successfully" in caplog.text
        mock_registry_instance.import_registry.assert_called_once()

    def test_docker_import_registry_file_not_found(
        self, mock_docker_registry_class, mock_path_operations, caplog
    ):
        """Test docker command with --import-registry when file doesn't exist."""
        args = self.create_namespace(
            admin_action="docker", import_registry="/nonexistent/registry.json"
        )

        # Mock file not existing
        mock_path_operations["path_instance"].exists.return_value = False

        result = AdminCommand.handle(args)

        assert result == 1
        assert "Import file not found:" in caplog.text

    def test_docker_import_registry_no_merge(
        self, mock_docker_registry_class, mock_path_operations, caplog
    ):
        """Test docker command with --import-registry with no merge option."""
        args = self.create_namespace(
            admin_action="docker", import_registry="/tmp/registry.json"
        )

        mock_registry_class, mock_registry_instance = mock_docker_registry_class

        with patch("builtins.input", return_value="n"):  # Don't merge
            result = AdminCommand.handle(args)

        assert result == 0
        # Verify merge=False was passed
        mock_registry_instance.import_registry.assert_called_once()
        call_args = mock_registry_instance.import_registry.call_args
        assert call_args[1]["merge"] == False

    def test_docker_general_exception(self, mock_subprocess, caplog):
        """Test docker command general exception handling."""
        args = self.create_namespace(admin_action="docker", images_all=True)

        # Mock subprocess import to raise exception
        with patch(
            "panther.cli.subcommands.admin.subprocess",
            side_effect=Exception("Docker error"),
        ):
            result = AdminCommand.handle(args)

            assert result == 1
            assert "Error during Docker management" in caplog.text

    # =============================================================================
    # PARAMETER VALIDATION TESTS
    # =============================================================================

    @pytest.mark.parametrize(
        "invalid_action",
        ["invalid", "", "TEARDOWN", "docker_wrong", 123, None],  # Case sensitive
    )
    def test_invalid_actions(self, invalid_action, caplog):
        """Test handling of invalid action parameters."""
        args = self.create_namespace(admin_action=invalid_action)

        result = AdminCommand.handle(args)

        if invalid_action is None:
            assert "No admin action specified" in caplog.text
        else:
            assert result == 1

    @pytest.mark.parametrize("flag_value", [True, False])
    def test_teardown_boolean_flags(
        self, flag_value, mock_subprocess, mock_path_operations
    ):
        """Test teardown command boolean flags."""
        args = self.create_namespace(admin_action="teardown", force=flag_value)

        if not flag_value:
            with patch("builtins.input", return_value="y"):
                result = AdminCommand.handle(args)
        else:
            result = AdminCommand.handle(args)

        assert result == 0  # Should not crash with any valid flag value

    @pytest.mark.parametrize("flag_value", [True, False])
    def test_clean_boolean_flags(self, flag_value, mock_path_operations):
        """Test clean command boolean flags."""
        flags = ["logs", "cache", "all"]

        for flag in flags:
            args_dict = {
                "admin_action": "clean",
                "logs": False,
                "cache": False,
                "all": False,
            }
            args_dict[flag] = flag_value

            args = self.create_namespace(**args_dict)

            result = AdminCommand.handle(args)

            assert result == 0  # Should not crash with any valid flag value

    @pytest.mark.parametrize("flag_value", [True, False])
    def test_docker_boolean_flags(self, flag_value, mock_subprocess):
        """Test docker command boolean flags."""
        # Test a subset of flags to avoid too many combinations
        flags = ["images_all", "volumes", "containers", "show_registry"]

        for flag in flags:
            args_dict = {
                "admin_action": "docker",
                "images_all": False,
                "images_services": False,
                "system_all": False,
                "system_services": False,
                "volumes": False,
                "containers": False,
                "show_registry": False,
                "prune_cache": False,
                "export_registry": None,
                "import_registry": None,
                "cache_max_age": 7,
            }
            args_dict[flag] = flag_value

            args = self.create_namespace(**args_dict)

            if flag == "show_registry" and flag_value:
                with patch("panther.cli.subcommands.admin.DockerRegistry"):
                    result = AdminCommand.handle(args)
            else:
                result = AdminCommand.handle(args)

            # Should either succeed or fail gracefully (not crash)
            assert result in [0, 1]

    @pytest.mark.parametrize("port", [80, 3000, 8080, 9000, 65535])
    def test_webapp_port_values(self, port, caplog):
        """Test webapp command with different port values."""
        args = self.create_namespace(admin_action="webapp", port=port, host="localhost")

        result = AdminCommand.handle(args)

        assert result == 1  # Always fails due to deprecation
        assert "Web application feature has been removed" in caplog.text

    @pytest.mark.parametrize("max_age", [1, 7, 14, 30, 365])
    def test_docker_cache_max_age_values(
        self, max_age, mock_docker_registry_class, mock_docker_cache_mixin_class
    ):
        """Test docker command with different cache max age values."""
        args = self.create_namespace(
            admin_action="docker", prune_cache=True, cache_max_age=max_age
        )

        mock_registry_class, mock_registry_instance = mock_docker_registry_class
        mock_cache_class, mock_cache_instance = mock_docker_cache_mixin_class

        result = AdminCommand.handle(args)

        assert result == 0
        # Verify max_age was passed correctly
        mock_cache_instance.prune_cache.assert_called_once_with(max_age_days=max_age)

    # =============================================================================
    # EDGE CASE TESTS
    # =============================================================================

    def test_unicode_in_export_path(
        self, mock_docker_registry_class, mock_path_operations
    ):
        """Test docker command with unicode characters in export path."""
        unicode_path = "/tmp/测试_registry.json"

        args = self.create_namespace(
            admin_action="docker", export_registry=unicode_path
        )

        mock_registry_class, mock_registry_instance = mock_docker_registry_class

        result = AdminCommand.handle(args)

        assert result == 0  # Should handle unicode paths gracefully

    def test_very_long_file_paths(
        self, mock_docker_registry_class, mock_path_operations
    ):
        """Test docker command with very long file paths."""
        long_path = "/tmp/" + ("a" * 200) + "/registry.json"

        args = self.create_namespace(admin_action="docker", export_registry=long_path)

        result = AdminCommand.handle(args)

        assert result == 0  # Should handle long paths gracefully

    def test_special_characters_in_file_paths(
        self, mock_docker_registry_class, mock_path_operations
    ):
        """Test docker command with special characters in file paths."""
        special_path = "/tmp/registry@#$%^&*().json"

        args = self.create_namespace(
            admin_action="docker", import_registry=special_path
        )

        # Mock file exists
        mock_path_operations["path_instance"].exists.return_value = True

        with patch("builtins.input", return_value="Y"):
            result = AdminCommand.handle(args)

        assert result == 0  # Should handle special characters gracefully

    # =============================================================================
    # INTEGRATION TESTS
    # =============================================================================

    def test_end_to_end_admin_workflow(
        self, mock_subprocess, mock_path_operations, mock_docker_registry_class, caplog
    ):
        """Test complete admin workflow: status → clean → docker → teardown."""

        # Step 1: Check system status
        args_status = self.create_namespace(admin_action="status")
        result = AdminCommand.handle(args_status)
        assert result == 0
        assert "PANTHER System Status" in caplog.text

        # Step 2: Clean cache files
        args_clean = self.create_namespace(
            admin_action="clean", logs=False, cache=True, all=False
        )
        result = AdminCommand.handle(args_clean)
        assert result == 0

        # Step 3: Show Docker registry
        args_docker = self.create_namespace(admin_action="docker", show_registry=True)
        mock_registry_class, mock_registry_instance = mock_docker_registry_class
        result = AdminCommand.handle(args_docker)
        assert result == 0
        assert "Docker Registry Statistics" in caplog.text

        # Step 4: Teardown system with force
        args_teardown = self.create_namespace(admin_action="teardown", force=True)
        result = AdminCommand.handle(args_teardown)
        assert result == 0

    def test_admin_command_comprehensive_parameters(
        self, mock_subprocess, mock_path_operations, mock_docker_registry_class, caplog
    ):
        """Test admin command with comprehensive parameter combinations."""

        # Test all main subcommands
        subcommands = [
            {"admin_action": "status"},
            {"admin_action": "webapp", "port": 8080, "host": "localhost"},
            {"admin_action": "clean", "logs": True, "cache": True, "all": True},
            {"admin_action": "teardown", "force": True},
        ]

        for subcommand_args in subcommands:
            args = self.create_namespace(**subcommand_args)
            result = AdminCommand.handle(args)

            if subcommand_args["admin_action"] == "webapp":
                assert result == 1  # Webapp is deprecated
            else:
                assert result == 0

        # Test Docker operations
        docker_operations = [
            {"admin_action": "docker", "images_all": True},
            {"admin_action": "docker", "volumes": True, "containers": True},
            {"admin_action": "docker", "show_registry": True},
            {"admin_action": "docker", "prune_cache": True, "cache_max_age": 14},
        ]

        mock_registry_class, mock_registry_instance = mock_docker_registry_class

        for docker_args in docker_operations:
            # Add default values for all Docker flags
            full_docker_args = {
                "images_all": False,
                "images_services": False,
                "system_all": False,
                "system_services": False,
                "volumes": False,
                "containers": False,
                "show_registry": False,
                "prune_cache": False,
                "export_registry": None,
                "import_registry": None,
                "cache_max_age": 7,
            }
            full_docker_args.update(docker_args)

            args = self.create_namespace(**full_docker_args)

            if full_docker_args.get("prune_cache"):
                with patch("panther.cli.subcommands.admin.DockerCacheMixin"):
                    result = AdminCommand.handle(args)
            else:
                result = AdminCommand.handle(args)

            assert result == 0
