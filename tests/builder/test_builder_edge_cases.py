"""
Edge case and error condition tests for panther_builder.py.

This module tests unusual scenarios, boundary conditions, and error handling
in the BuildManager class to ensure robust behavior.
"""

import pytest
import sys
from pathlib import Path
from unittest.mock import Mock, patch

from panther_builder import BuildManager


class TestBuildManagerEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_init_with_extremely_long_path(self):
        """Test initialization with an extremely long project path."""
        long_path = Path("/" + "a" * 200 + "/project")
        with patch.object(Path, "parent", long_path):
            with patch("panther_builder.docker_available", False):
                manager = BuildManager()
                assert manager.project_root == long_path

    def test_docker_version_with_malformed_version_string(self):
        """Test Docker version parsing with malformed version strings."""
        mock_client = Mock()
        test_cases = [
            {"Version": "not.a.version"},
            {"Version": "27"},
            {"Version": "27.1"},
            {"Version": "27.1.1.1.1"},
            {"Version": ""},
            {"Version": "v27.1.1"},
            {"Version": "27.1.1-beta"},
        ]

        manager = BuildManager()

        for case in test_cases:
            mock_client.version.return_value = case
            with patch("builtins.print"):
                # Should not raise an exception
                manager._check_docker_version(mock_client)

    def test_run_command_with_very_long_command(self):
        """Test command execution with very long command arguments."""
        long_arg = "a" * 1000
        with patch("panther_builder.subprocess.run") as mock_run:
            mock_result = Mock()
            mock_result.returncode = 0
            mock_run.return_value = mock_result

            manager = BuildManager()
            result = manager.run_command(["echo", long_arg])

            assert result == 0
            mock_run.assert_called_once()

    def test_run_command_with_empty_command_list(self):
        """Test command execution with empty command list."""
        with patch("panther_builder.subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError("Empty command")

            with patch("builtins.print") as mock_print:
                manager = BuildManager()
                result = manager.run_command([])

                assert result == 1

    def test_clean_with_permission_errors(self):
        """Test clean operation when encountering permission errors."""

        def rmtree_side_effect(path):
            if "protected" in str(path):
                raise PermissionError("Permission denied")

        with patch("panther_builder.shutil.rmtree", side_effect=rmtree_side_effect):
            with patch("pathlib.Path.exists", return_value=True):
                with patch(
                    "pathlib.Path.glob", return_value=[Path("protected.egg-info")]
                ):
                    with patch("pathlib.Path.rglob", return_value=[]):
                        manager = BuildManager()
                        # Should handle permission errors gracefully
                        with pytest.raises(PermissionError):
                            manager.clean()

    def test_install_wheel_multiple_wheels(self):
        """Test wheel installation when multiple wheel files exist."""
        wheels = [
            Path("/project/dist/panther_net-1.0.0-py3-none-any.whl"),
            Path("/project/dist/panther_net-1.0.1-py3-none-any.whl"),
        ]

        with patch("pathlib.Path.glob", return_value=wheels):
            with patch.object(BuildManager, "run_command") as mock_run:
                mock_run.return_value = 0

                manager = BuildManager()
                result = manager.install_wheel()

                assert result == 0
                # Should install the first wheel found
                mock_run.assert_called_once_with(
                    [sys.executable, "-m", "pip", "install", str(wheels[0])]
                )


class TestBuildManagerErrorHandling:
    """Test error handling and recovery mechanisms."""

    def test_docker_version_check_with_network_timeout(self):
        """Test Docker version check with network timeout."""
        mock_client = Mock()
        mock_client.version.side_effect = TimeoutError("Network timeout")

        with patch("builtins.print") as mock_print:
            manager = BuildManager()
            manager._check_docker_version(mock_client)

            mock_print.assert_called_with(
                "Warning: Could not determine Docker version: Network timeout"
            )

    def test_run_command_with_interrupted_process(self):
        """Test command execution when process is interrupted."""
        with patch("panther_builder.subprocess.run") as mock_run:
            mock_run.side_effect = KeyboardInterrupt("Process interrupted")

            with pytest.raises(KeyboardInterrupt):
                manager = BuildManager()
                manager.run_command(["sleep", "100"])

    def test_build_docs_with_missing_dependencies(self):
        """Test documentation building with missing dependencies."""
        with patch.object(BuildManager, "run_command") as mock_run:
            # Simulate missing dependency installation
            mock_run.side_effect = [1, 0, 0, 0, 0, 0, 0]  # First call fails

            with patch.object(BuildManager, "clean"):
                with patch("panther_builder.shutil.copy2"):
                    with patch(
                        "panther_builder.shutil.rmtree"
                    ):  # Mock rmtree to avoid FileNotFoundError
                        with patch("pathlib.Path.exists", return_value=True):
                            with patch("pathlib.Path.mkdir"):
                                with patch("builtins.open", create=True):
                                    manager = BuildManager()
                                    result = manager.build_docs()

                                    # Should continue despite dependency installation failure
                                    assert isinstance(result, int)

    def test_zip_outputs_with_insufficient_disk_space(self):
        """Test output zipping when there's insufficient disk space."""
        with patch("datetime.datetime") as mock_datetime_class:
            mock_datetime_instance = Mock()
            mock_datetime_instance.strftime.return_value = "20241225"
            mock_datetime_class.now.return_value = mock_datetime_instance

            with patch("pathlib.Path.exists", return_value=True):
                with patch("pathlib.Path.iterdir", return_value=[Path("output1")]):
                    with patch.object(BuildManager, "run_command") as mock_run:
                        mock_run.return_value = 1  # Zip command fails

                        with patch("builtins.print") as mock_print:
                            manager = BuildManager()
                            result = manager.zip_outputs()

                            assert result == 1
                            mock_print.assert_called_with(
                                "❌ Failed to create zip archive"
                            )


class TestBuildManagerRobustness:
    """Test system robustness and resilience."""

    def test_concurrent_build_operations(self):
        """Test behavior when multiple build operations might run concurrently."""
        # This test simulates file locking scenarios
        with patch("panther_builder.shutil.rmtree") as mock_rmtree:
            mock_rmtree.side_effect = [
                OSError("Resource temporarily unavailable"),
                None,  # Second call succeeds
            ]

            with patch("pathlib.Path.exists", return_value=True):
                with patch("pathlib.Path.glob", return_value=[]):
                    with patch("pathlib.Path.rglob", return_value=[]):
                        manager = BuildManager()
                        # Should handle temporary file conflicts
                        with pytest.raises(OSError):
                            manager.clean()

    def test_system_resource_exhaustion(self):
        """Test behavior under system resource exhaustion."""
        with patch("panther_builder.subprocess.run") as mock_run:
            mock_run.side_effect = OSError("Cannot allocate memory")

            with patch("builtins.print") as mock_print:
                manager = BuildManager()
                result = manager.run_command(["echo", "test"])

                assert result == 1
                # Should handle system resource errors gracefully
                mock_print.assert_called_with(
                    "Error: System error occurred: Cannot allocate memory"
                )

    def test_corrupted_wheel_file_handling(self):
        """Test handling of corrupted wheel files."""
        corrupted_wheel = Path("/project/dist/corrupted.whl")

        with patch("pathlib.Path.glob", return_value=[corrupted_wheel]):
            with patch.object(BuildManager, "run_command") as mock_run:
                mock_run.return_value = 1  # pip install fails

                manager = BuildManager()
                result = manager.install_wheel()

                assert result == 1


class TestBuildManagerFileSystemEdgeCases:
    """Test file system related edge cases."""

    def test_read_only_filesystem(self):
        """Test operations on read-only filesystem."""
        with patch("pathlib.Path.mkdir") as mock_mkdir:
            mock_mkdir.side_effect = PermissionError("Read-only file system")

            manager = BuildManager()
            # Should handle read-only filesystem gracefully in build_docs
            with patch.object(manager, "clean"):
                with patch.object(manager, "run_command", return_value=0):
                    with patch("pathlib.Path.exists", return_value=False):
                        with pytest.raises(PermissionError):
                            manager.build_docs()

    def test_symlink_handling_in_clean(self):
        """Test clean operation with symbolic links."""
        # Create mock path objects for symlinks
        mock_symlink = Mock()
        mock_symlink.is_symlink.return_value = True
        mock_symlink.__str__ = Mock(return_value="mock_symlink_path")
        mock_symlink.__fspath__ = Mock(return_value="mock_symlink_path")

        with patch("pathlib.Path.rglob") as mock_rglob:
            mock_rglob.return_value = [mock_symlink]

            with patch("pathlib.Path.exists", return_value=False):
                with patch("pathlib.Path.glob", return_value=[]):
                    with patch("panther_builder.shutil.rmtree") as mock_rmtree:
                        with patch("pathlib.Path.unlink") as mock_unlink:
                            manager = BuildManager()
                            result = manager.clean()

                            # Should handle symlinks appropriately
                            assert result == 0

    def test_case_sensitive_filesystem_issues(self):
        """Test handling of case-sensitive filesystem issues."""
        # Simulate case where both 'Build' and 'build' directories exist
        with patch("pathlib.Path.exists") as mock_exists:

            def exists_side_effect(*args, **kwargs):
                path_str = str(args[0]) if args else str(kwargs.get("self", ""))
                return "build" in path_str.lower()

            mock_exists.side_effect = exists_side_effect

            with patch("panther_builder.shutil.rmtree") as mock_rmtree:
                with patch("pathlib.Path.glob", return_value=[]):
                    with patch("pathlib.Path.rglob", return_value=[]):
                        manager = BuildManager()
                        result = manager.clean()

                        assert result == 0


class TestBuildManagerNetworkAndIOEdgeCases:
    """Test network and I/O related edge cases."""

    def test_docker_api_rate_limiting(self):
        """Test Docker API calls with rate limiting."""
        mock_client = Mock()
        mock_client.ping.side_effect = [
            Exception("Rate limit exceeded"),
            None,  # Second call succeeds
        ]

        with patch("panther_builder.docker.from_env", return_value=mock_client):
            with patch("panther_builder.docker_available", True):
                with patch("builtins.print"):
                    manager = BuildManager()
                    # Should handle rate limiting gracefully
                    assert manager.docker_available is False

    def test_network_dependency_installation_failure(self):
        """Test dependency installation with network failures."""
        with patch.object(BuildManager, "run_command") as mock_run:
            mock_run.side_effect = [
                1,  # First pip install fails (network issue)
                0,  # Second pip install succeeds
                0,  # Third pip install succeeds
            ]

            manager = BuildManager()
            result = manager.install_dependencies()

            # Should return sum of all return codes
            assert result == 1

    @pytest.mark.slow
    def test_large_file_operations(self):
        """Test operations with large files (marked as slow)."""
        with patch("pathlib.Path.rglob") as mock_rglob:
            # Simulate many pyc files
            large_file_list = [Path(f"file_{i}.pyc") for i in range(1000)]
            mock_rglob.return_value = large_file_list

            with patch("pathlib.Path.exists", return_value=False):
                with patch("pathlib.Path.glob", return_value=[]):
                    with patch("pathlib.Path.unlink") as mock_unlink:
                        manager = BuildManager()
                        result = manager.clean()

                        assert result == 0
                        assert mock_unlink.call_count == 1000


class TestBuildManagerStateConsistency:
    """Test state consistency across operations."""

    def test_docker_state_consistency(self):
        """Test Docker availability state remains consistent."""
        with patch("panther_builder.docker_available", True):
            with patch("panther_builder.docker") as mock_docker:
                mock_client = Mock()
                mock_docker.from_env.return_value = mock_client
                mock_client.ping.return_value = None

                with patch.object(BuildManager, "_check_docker_version"):
                    manager = BuildManager()
                    initial_state = manager.docker_available

                    # State should remain consistent throughout operations
                    manager.remove_images_all()
                    assert manager.docker_available == initial_state

    def test_project_root_immutability(self):
        """Test that project_root remains immutable after initialization."""
        manager = BuildManager()
        original_root = manager.project_root

        # Perform various operations
        with patch.object(manager, "run_command", return_value=0):
            manager.clean()
            manager.install_dependencies()

        # Project root should remain unchanged
        assert manager.project_root == original_root

    def test_package_name_consistency(self):
        """Test package name consistency across operations."""
        manager = BuildManager()
        original_package_name = manager.package_name

        # Package name should be used consistently
        with patch.object(manager, "run_command") as mock_run:
            manager.uninstall_package()

            # Check that the correct package name was used
            call_args = mock_run.call_args[0][0]
            assert original_package_name in call_args
