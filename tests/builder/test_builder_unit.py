"""
Unit tests for panther_builder.py BuildManager class.

This module provides comprehensive white-box unit tests for the BuildManager class,
covering all public methods with mocked dependencies to ensure deterministic behavior.
"""

import pytest
import sys
import subprocess
from pathlib import Path
from unittest.mock import Mock, patch, call

from panther_builder import BuildManager


class TestBuildManagerInit:
    """Test BuildManager initialization and environment checks."""

    def test_init_creates_required_attributes(self):
        """Test that BuildManager.__init__ sets up all required attributes."""
        with patch("panther_builder.docker", create=True):
            with patch("panther_builder.docker_available", True):
                with patch.object(Path, "parent", Path("/fake/project")):
                    manager = BuildManager()

                    assert manager.project_root == Path("/fake/project")
                    assert manager.build_dirs == ["build", "dist"]
                    assert manager.docs_dir == ["docs", "site"]
                    assert manager.tests_gen_dir == ["htmlcov"]
                    assert manager.package_name == "panther_net"
                    assert manager.min_python_version == (3, 10)

    def test_init_python_version_check_passes(self):
        """Test that initialization succeeds with supported Python version."""
        with patch("panther_builder.sys.version_info", (3, 11, 0)):
            with patch("panther_builder.docker_available", False):
                manager = BuildManager()
                assert manager is not None

    def test_init_python_version_check_fails(self):
        """Test that initialization fails with unsupported Python version."""
        with patch("panther_builder.sys.version_info", (3, 9, 0)):
            with patch("panther_builder.sys.exit") as mock_exit:
                with patch("builtins.print"):
                    BuildManager()
                    mock_exit.assert_called_once_with(1)

    def test_init_detects_virtual_environment_real_prefix(self):
        """Test virtual environment detection using real_prefix."""
        with patch("panther_builder.sys") as mock_sys:
            mock_sys.version_info = (3, 8, 5)  # Valid version
            mock_sys.real_prefix = "/usr"

            with patch("panther_builder.docker_available", False):
                manager = BuildManager()
                assert manager.is_venv is True

    def test_init_detects_virtual_environment_base_prefix(self):
        """Test virtual environment detection using base_prefix."""
        with patch("panther_builder.sys") as mock_sys:
            mock_sys.base_prefix = "/usr"
            mock_sys.prefix = "/venv"
            (
                delattr(mock_sys, "real_prefix")
                if hasattr(mock_sys, "real_prefix")
                else None
            )
            mock_sys.version_info = (3, 11, 0)
            with patch("panther_builder.docker_available", False):
                manager = BuildManager()
                assert manager.is_venv is True

    def test_init_detects_no_virtual_environment(self):
        """Test detection when not in virtual environment."""
        with patch("panther_builder.sys") as mock_sys:
            mock_sys.base_prefix = "/usr"
            mock_sys.prefix = "/usr"
            (
                delattr(mock_sys, "real_prefix")
                if hasattr(mock_sys, "real_prefix")
                else None
            )
            mock_sys.version_info = (3, 11, 0)
            with patch("panther_builder.docker_available", False):
                with patch("builtins.print") as mock_print:
                    manager = BuildManager()
                    assert manager.is_venv is False
                    mock_print.assert_called_with(
                        "Warning: It is recommended to run this script in a Python virtual environment."
                    )

    @patch("panther_builder.docker_available", True)
    @patch("panther_builder.docker")
    def test_init_docker_available_and_running(self, mock_docker):
        """Test Docker initialization when Docker is available and running."""
        mock_client = Mock()
        mock_docker.from_env.return_value = mock_client
        mock_client.ping.return_value = None

        with patch.object(BuildManager, "_check_docker_version") as mock_check:
            with patch("builtins.print") as mock_print:
                manager = BuildManager()

                assert manager.docker_available is True
                mock_docker.from_env.assert_called_once()
                mock_client.ping.assert_called_once()
                mock_check.assert_called_once_with(mock_client)
                mock_print.assert_any_call("Docker is available and running.")

    @patch("panther_builder.docker_available", True)
    @patch("panther_builder.docker")
    def test_init_docker_import_error(self, mock_docker):
        """Test Docker initialization when Docker package is not installed."""
        mock_docker.from_env.side_effect = ImportError("No module named docker")

        with patch("builtins.print") as mock_print:
            manager = BuildManager()

            assert manager.docker_available is False
            mock_print.assert_any_call(
                "Warning: Docker Python package not installed. Docker-dependent features will not work."
            )

    @patch("panther_builder.docker_available", True)
    @patch("panther_builder.docker")
    def test_init_docker_daemon_not_running(self, mock_docker):
        """Test Docker initialization when Docker daemon is not running."""
        mock_client = Mock()
        mock_docker.from_env.return_value = mock_client
        mock_client.ping.side_effect = Exception("Docker daemon not reachable")

        with patch("builtins.print") as mock_print:
            manager = BuildManager()

            assert manager.docker_available is False
            mock_print.assert_any_call(
                "Warning: Docker daemon is not running or not accessible. Docker-dependent features will not work."
            )

    @patch("panther_builder.docker_available", False)
    def test_init_docker_not_available(self):
        """Test initialization when Docker is not available."""
        manager = BuildManager()
        assert (
            not hasattr(manager, "docker_available")
            or manager.docker_available is False
        )


class TestBuildManagerDockerVersion:
    """Test Docker version checking functionality."""

    def test_check_docker_version_meets_requirements(self):
        """Test Docker version check when version meets requirements."""
        mock_client = Mock()
        mock_client.version.return_value = {"Version": "27.1.1"}

        with patch("builtins.print") as mock_print:
            manager = BuildManager()
            manager._check_docker_version(mock_client)

            mock_print.assert_called_with(
                "Docker version 27.1.1 meets requirements (≥27.0.0)"
            )

    def test_check_docker_version_below_minimum(self):
        """Test Docker version check when version is below minimum."""
        mock_client = Mock()
        mock_client.version.return_value = {"Version": "26.9.0"}

        with patch("builtins.print") as mock_print:
            manager = BuildManager()
            manager._check_docker_version(mock_client)

            mock_print.assert_any_call(
                "Warning: Docker version 26.9.0 is below recommended minimum 27.0.0"
            )

    def test_check_docker_version_exception(self):
        """Test Docker version check when an exception occurs."""
        mock_client = Mock()
        mock_client.version.side_effect = Exception("API error")

        with patch("builtins.print") as mock_print:
            manager = BuildManager()
            manager._check_docker_version(mock_client)

            mock_print.assert_called_with(
                "Warning: Could not determine Docker version: API error"
            )

    def test_check_docker_version_missing_version_key(self):
        """Test Docker version check when version key is missing."""
        mock_client = Mock()
        mock_client.version.return_value = {}

        with patch("builtins.print") as mock_print:
            manager = BuildManager()
            manager._check_docker_version(mock_client)

            # Should default to "0.0.0" and warn about older version
            mock_print.assert_any_call(
                "Warning: Docker version 0.0.0 is below recommended minimum 27.0.0"
            )


class TestBuildManagerRunCommand:
    """Test command execution functionality."""

    def test_run_command_success(self):
        """Test successful command execution."""
        with patch("panther_builder.subprocess.run") as mock_run:
            mock_result = Mock()
            mock_result.returncode = 0
            mock_run.return_value = mock_result

            manager = BuildManager()
            result = manager.run_command(["echo", "test"])

            assert result == 0
            mock_run.assert_called_once_with(
                ["echo", "test"],
                cwd=manager.project_root,
                check=True,
                capture_output=False,
            )

    def test_run_command_with_custom_cwd(self):
        """Test command execution with custom working directory."""
        with patch("panther_builder.subprocess.run") as mock_run:
            mock_result = Mock()
            mock_result.returncode = 0
            mock_run.return_value = mock_result

            manager = BuildManager()
            custom_cwd = Path("/custom/path")
            result = manager.run_command(["echo", "test"], cwd=custom_cwd)

            assert result == 0
            mock_run.assert_called_once_with(
                ["echo", "test"], cwd=custom_cwd, check=True, capture_output=False
            )

    def test_run_command_called_process_error(self):
        """Test command execution when subprocess fails."""
        with patch("panther_builder.subprocess.run") as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(1, ["false"])

            with patch("builtins.print") as mock_print:
                manager = BuildManager()
                result = manager.run_command(["false"])

                assert result == 1
                mock_print.assert_called_with("Error: Command failed with exit code 1")

    def test_run_command_file_not_found(self):
        """Test command execution when command is not found."""
        with patch("panther_builder.subprocess.run") as mock_run:
            mock_run.side_effect = FileNotFoundError("Command not found")

            with patch("builtins.print") as mock_print:
                manager = BuildManager()
                result = manager.run_command(["nonexistent-command"])

                assert result == 1
                mock_print.assert_called_with(
                    "Error: Command not found: nonexistent-command"
                )


class TestBuildManagerClean:
    """Test build artifact cleaning functionality."""

    @patch("panther_builder.shutil.rmtree")
    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.glob")
    @patch("pathlib.Path.rglob")
    @patch("pathlib.Path.unlink")
    def test_clean_removes_all_artifacts(
        self, mock_unlink, mock_rglob, mock_glob, mock_exists, mock_rmtree
    ):
        """Test that clean removes all build artifacts."""
        # Setup mock file system
        mock_exists.return_value = True
        mock_glob.return_value = [Path("test.egg-info")]
        mock_rglob.side_effect = [
            [Path("__pycache__")],  # First call for __pycache__
            [Path("test.pyc")],  # Second call for *.pyc
        ]

        with patch("builtins.print"):
            manager = BuildManager()
            result = manager.clean()

            assert result == 0
            # Should remove docs, tests_gen, build dirs, egg-info, __pycache__, and .pyc files
            assert (
                mock_rmtree.call_count >= 3
            )  # At minimum: docs, tests_gen, build dirs
            mock_unlink.assert_called()  # Should unlink .pyc files

    def test_clean_non_existent_directories(self):
        """Test clean when directories don't exist."""
        with patch("pathlib.Path.exists", return_value=False):
            with patch("pathlib.Path.glob", return_value=[]):
                with patch("pathlib.Path.rglob", return_value=[]):
                    with patch("builtins.print") as mock_print:
                        manager = BuildManager()
                        result = manager.clean()

                        assert result == 0
                        mock_print.assert_called_with("Clean completed.")


class TestBuildManagerInstallDependencies:
    """Test dependency installation functionality."""

    def test_install_dependencies_success(self):
        """Test successful dependency installation."""
        with patch.object(BuildManager, "run_command") as mock_run:
            mock_run.return_value = 0

            manager = BuildManager()
            result = manager.install_dependencies()

            assert result == 0
            expected_calls = [
                call(
                    [
                        sys.executable,
                        "-m",
                        "pip",
                        "install",
                        "build",
                        "wheel",
                        "setuptools",
                    ]
                ),
                call([sys.executable, "-m", "pip", "install", "--upgrade", "pip"]),
                call([sys.executable, "-m", "pip", "install", "."]),
            ]
            mock_run.assert_has_calls(expected_calls)

    def test_install_dependencies_partial_failure(self):
        """Test dependency installation with partial failures."""
        with patch.object(BuildManager, "run_command") as mock_run:
            mock_run.side_effect = [1, 0, 0]  # First command fails

            manager = BuildManager()
            result = manager.install_dependencies()

            assert result == 1  # 1 + 0 + 0


class TestBuildManagerPackageOperations:
    """Test package build and installation operations."""

    def test_uninstall_package_success(self):
        """Test successful package uninstallation."""
        with patch.object(BuildManager, "run_command") as mock_run:
            mock_run.return_value = 0

            manager = BuildManager()
            result = manager.uninstall_package()

            assert result == 0
            mock_run.assert_called_once_with(
                [sys.executable, "-m", "pip", "uninstall", "--yes", "panther_net"]
            )

    def test_build_wheel_success(self):
        """Test successful wheel building."""
        with patch.object(BuildManager, "run_command") as mock_run:
            mock_run.return_value = 0

            manager = BuildManager()
            result = manager.build_wheel()

            assert result == 0
            mock_run.assert_called_once_with(
                [sys.executable, "-m", "build", "--wheel", "--no-isolation"]
            )

    @patch("pathlib.Path.glob")
    def test_install_wheel_success(self, mock_glob):
        """Test successful wheel installation."""
        mock_wheel = Path("/project/dist/panther_net-1.0.0-py3-none-any.whl")
        mock_glob.return_value = [mock_wheel]

        with patch.object(BuildManager, "run_command") as mock_run:
            mock_run.return_value = 0

            manager = BuildManager()
            result = manager.install_wheel()

            assert result == 0
            mock_run.assert_called_once_with(
                [sys.executable, "-m", "pip", "install", str(mock_wheel)]
            )

    @patch("pathlib.Path.glob")
    def test_install_wheel_no_wheel_found(self, mock_glob):
        """Test wheel installation when no wheel file is found."""
        mock_glob.return_value = []

        with patch("builtins.print") as mock_print:
            manager = BuildManager()
            result = manager.install_wheel()

            assert result == 1
            mock_print.assert_called_with("Error: No wheel file found in dist/")

    def test_install_editable_success(self):
        """Test successful editable installation."""
        with patch.object(BuildManager, "run_command") as mock_run:
            mock_run.return_value = 0

            manager = BuildManager()
            result = manager.install_editable()

            assert result == 0
            mock_run.assert_called_once_with(
                [
                    sys.executable,
                    "-m",
                    "pip",
                    "install",
                    "--force-reinstall",
                    "--editable",
                    ".",
                ]
            )


class TestBuildManagerTestOperations:
    """Test testing-related operations."""

    def test_run_tests_success(self):
        """Test successful test execution."""
        with patch.object(BuildManager, "run_command") as mock_run:
            mock_run.return_value = 0

            manager = BuildManager()
            result = manager.run_tests()

            assert result == 0
            expected_calls = [
                call([sys.executable, "-m", "pip", "install", ".[tests]"]),
                call([sys.executable, "-m", "pytest", "tests/"]),
            ]
            mock_run.assert_has_calls(expected_calls)

    def test_run_tests_dependency_installation_fails(self):
        """Test test execution when dependency installation fails."""
        with patch.object(BuildManager, "run_command") as mock_run:
            mock_run.side_effect = [1, 0]  # Dependency install fails

            manager = BuildManager()
            result = manager.run_tests()

            assert result == 1
            # Should only call dependency installation, not pytest
            mock_run.assert_called_once_with(
                [sys.executable, "-m", "pip", "install", ".[tests]"]
            )


class TestBuildManagerQualityChecks:
    """Test code quality checking functionality."""

    def test_check_code_quality_all_pass(self):
        """Test code quality checks when all checks pass."""
        with patch.object(BuildManager, "run_command") as mock_run:
            mock_run.return_value = 0

            manager = BuildManager()
            result = manager.check_code_quality()

            assert result == 0
            assert mock_run.call_count >= 4  # Install + 3 checks minimum

    def test_check_code_quality_some_fail(self):
        """Test code quality checks when some checks fail."""
        with patch.object(BuildManager, "run_command") as mock_run:
            # Install succeeds, black fails, isort succeeds, flake8 fails
            mock_run.side_effect = [0, 1, 0, 1]

            with patch("builtins.print"):
                manager = BuildManager()
                result = manager.check_code_quality()

                assert result == 2  # Two failed checks

    def test_check_code_quality_install_fails(self):
        """Test code quality checks when tool installation fails."""
        with patch.object(BuildManager, "run_command") as mock_run:
            mock_run.side_effect = [1, 0, 0, 0]  # Install fails

            with patch("builtins.print") as mock_print:
                manager = BuildManager()
                result = manager.check_code_quality()

                # Should still run checks even if install fails
                assert result == 0
                mock_print.assert_any_call(
                    "Warning: Could not install quality check tools"
                )


@pytest.mark.slow
class TestBuildManagerDockerOperations:
    """Test Docker-related operations (marked as slow)."""

    def test_remove_images_all_docker_available(self):
        """Test removing all panther-related Docker images."""
        with patch.object(BuildManager, "run_command") as mock_run:
            mock_run.return_value = 0

            manager = BuildManager()
            manager.docker_available = True
            result = manager.remove_images_all()

            assert result == 0
            assert mock_run.call_count == 2  # Two docker commands

    def test_remove_images_all_docker_not_available(self):
        """Test removing Docker images when Docker is not available."""
        with patch("builtins.print") as mock_print:
            manager = BuildManager()
            manager.docker_available = False
            result = manager.remove_images_all()

            assert result == 1
            mock_print.assert_called_with(
                "❌ Docker is not available. Cannot remove Docker images."
            )

    def test_remove_images_services_success(self):
        """Test removing service-related Docker images."""
        with patch.object(BuildManager, "run_command") as mock_run:
            mock_run.return_value = 0

            manager = BuildManager()
            manager.docker_available = True
            result = manager.remove_images_services()

            assert result == 0
            assert mock_run.call_count == 2


class TestBuildManagerUtilityOperations:
    """Test utility operations like zip creation."""

    @patch("datetime.datetime")
    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.iterdir")
    def test_zip_outputs_success(self, mock_iterdir, mock_exists, mock_datetime):
        """Test successful outputs zipping."""
        mock_datetime.now.return_value.strftime.return_value = "20241225"
        mock_exists.return_value = True
        mock_iterdir.return_value = [Path("output1"), Path("output2")]

        with patch.object(BuildManager, "run_command") as mock_run:
            mock_run.return_value = 0
            with patch("panther_builder.shutil.rmtree") as mock_rmtree:
                with patch("pathlib.Path.mkdir") as mock_mkdir:
                    manager = BuildManager()
                    result = manager.zip_outputs()

                    assert result == 0
                    mock_run.assert_called_once()
                    mock_rmtree.assert_called_once()
                    mock_mkdir.assert_called_once()

    @patch("pathlib.Path.exists")
    def test_zip_outputs_no_outputs_directory(self, mock_exists):
        """Test zipping when outputs directory doesn't exist."""
        mock_exists.return_value = False

        with patch("builtins.print") as mock_print:
            manager = BuildManager()
            result = manager.zip_outputs()

            assert result == 0
            mock_print.assert_called_with(
                "No outputs directory found or it's empty. Nothing to zip."
            )

    @patch("pathlib.Path.exists")
    @patch("pathlib.Path.iterdir")
    def test_zip_outputs_empty_directory(self, mock_iterdir, mock_exists):
        """Test zipping when outputs directory is empty."""
        mock_exists.return_value = True
        mock_iterdir.return_value = []

        with patch("builtins.print") as mock_print:
            manager = BuildManager()
            result = manager.zip_outputs()

            assert result == 0
            mock_print.assert_called_with(
                "No outputs directory found or it's empty. Nothing to zip."
            )
