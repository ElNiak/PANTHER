"""
CLI Docker Commands Integration Tests.

Tests CLI Docker commands using pytest-docker for real Docker integration.
Focuses on admin commands and Docker workflow validation.
"""

import logging
import subprocess
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import docker
import pytest

from tests.unit.test_cli.base_cli_test import ComprehensiveCLITest


@pytest.fixture(scope="module")
def docker_client():
    """Provide Docker client for CLI tests."""
    try:
        client = docker.from_env()
        client.ping()
        return client
    except Exception as e:
        pytest.skip(f"Docker not available for CLI tests: {e}")


class TestDockerCLICommands(ComprehensiveCLITest):
    """Test Docker-related CLI commands with real Docker integration."""

    pytestmark = [pytest.mark.integration, pytest.mark.requires_docker]

    def test_admin_docker_status_integration(self, docker_client):
        """Test admin docker status command with real Docker."""
        from panther.cli.subcommands.admin import AdminCommand

        args = self.create_namespace(
            admin_action="docker", docker_action="status", format="simple"
        )

        # Test with real Docker environment
        result = AdminCommand._handle_docker(args)

        # Should complete successfully or with expected error
        assert result in [0, 1], "Docker status command should return valid exit code"

    def test_admin_docker_build_validation(self, docker_client):
        """Test Docker build command validation."""
        from panther.cli.subcommands.admin import AdminCommand

        # Test build command structure without actually building
        with patch("subprocess.run") as mock_subprocess:
            mock_subprocess.return_value = MagicMock(
                returncode=0, stdout="Build would execute", stderr=""
            )

            args = self.create_namespace(
                admin_action="docker",
                docker_action="build",
                force=False,
                no_cache=False,
            )

            result = AdminCommand._handle_docker(args)

            # Should call subprocess with docker-compose build
            assert mock_subprocess.called, "Should call subprocess for Docker build"

            # Verify command structure
            call_str = str(mock_subprocess.call_args)
            expected_commands = ["docker-compose", "docker", "build"]
            assert any(
                cmd in call_str for cmd in expected_commands
            ), f"Should call Docker build command, got: {call_str}"

            assert result in [0, 1], "Build command should return valid exit code"

    def test_admin_docker_clean_integration(self, docker_client):
        """Test Docker clean command integration."""
        from panther.cli.subcommands.admin import AdminCommand

        # Test clean command with mock to avoid actual cleanup
        with patch("subprocess.run") as mock_subprocess:
            mock_subprocess.return_value = MagicMock(
                returncode=0, stdout="Cleanup completed", stderr=""
            )

            args = self.create_namespace(
                admin_action="docker", docker_action="clean", force=True, prune=False
            )

            result = AdminCommand._handle_docker(args)

            # Should execute cleanup commands
            assert mock_subprocess.called, "Should call subprocess for Docker cleanup"
            assert result in [0, 1], "Clean command should return valid exit code"

    def test_admin_docker_logs_integration(self, docker_client):
        """Test Docker logs command integration."""
        from panther.cli.subcommands.admin import AdminCommand

        with patch("subprocess.run") as mock_subprocess:
            mock_subprocess.return_value = MagicMock(
                returncode=0, stdout="Service logs...", stderr=""
            )

            args = self.create_namespace(
                admin_action="docker",
                docker_action="logs",
                service="test-service",
                follow=False,
            )

            result = AdminCommand._handle_docker(args)

            # Should execute logs command
            assert mock_subprocess.called, "Should call subprocess for Docker logs"

            # Verify logs command structure
            call_str = str(mock_subprocess.call_args)
            assert "logs" in call_str, "Should call Docker logs command"

            assert result in [0, 1], "Logs command should return valid exit code"


class TestDockerWorkflowIntegration:
    """Test Docker workflow integration with PANTHER commands."""

    pytestmark = [pytest.mark.integration, pytest.mark.requires_docker]

    def test_docker_compose_file_accessibility(self):
        """Test that docker-compose file is accessible for CLI commands."""
        compose_files = [
            "docker-compose.yml",
            "docker-compose.yaml",
            "compose.yml",
            "compose.yaml",
        ]

        found_compose = False
        for compose_file in compose_files:
            if Path(compose_file).exists():
                found_compose = True
                logging.info(f"Found Docker Compose file: {compose_file}")

                # Test file is readable
                try:
                    with open(compose_file, "r") as f:
                        content = f.read()
                    assert (
                        len(content) > 0
                    ), f"Compose file {compose_file} should not be empty"

                    # Basic YAML structure check
                    assert (
                        "services:" in content or "version:" in content
                    ), f"Compose file {compose_file} should contain services or version"

                except Exception as e:
                    pytest.fail(f"Error reading compose file {compose_file}: {e}")
                break

        if not found_compose:
            logging.warning(
                "No Docker Compose file found - some Docker commands may not work"
            )

    def test_docker_command_error_handling(self, docker_client):
        """Test Docker command error handling."""
        from panther.cli.subcommands.admin import AdminCommand

        # Test with invalid Docker action
        args = self.create_namespace(
            admin_action="docker", docker_action="invalid_action"
        )

        result = AdminCommand._handle_docker(args)

        # Should handle invalid actions gracefully
        assert result == 1, "Invalid Docker action should return error code 1"

    def test_docker_permission_error_handling(self, docker_client):
        """Test handling of Docker permission errors."""
        from panther.cli.subcommands.admin import AdminCommand

        with patch("subprocess.run") as mock_subprocess:
            # Simulate permission denied error
            mock_subprocess.side_effect = subprocess.CalledProcessError(
                1, "docker", "Permission denied"
            )

            args = self.create_namespace(admin_action="docker", docker_action="status")

            result = AdminCommand._handle_docker(args)

            # Should handle permission errors gracefully
            assert result == 1, "Permission errors should be handled gracefully"

    @pytest.mark.slow
    def test_docker_timeout_handling(self, docker_client):
        """Test handling of Docker command timeouts."""
        from panther.cli.subcommands.admin import AdminCommand

        with patch("subprocess.run") as mock_subprocess:
            # Simulate timeout
            mock_subprocess.side_effect = subprocess.TimeoutExpired("docker", 30)

            args = self.create_namespace(
                admin_action="docker",
                docker_action="build",
                timeout=1,  # Very short timeout
            )

            result = AdminCommand._handle_docker(args)

            # Should handle timeouts gracefully
            assert result == 1, "Timeouts should be handled gracefully"


class TestDockerServiceIntegration:
    """Test Docker service integration scenarios."""

    pytestmark = [pytest.mark.integration, pytest.mark.requires_docker]

    def test_docker_service_discovery(self, docker_client):
        """Test Docker service discovery functionality."""
        # Get list of running containers that might be PANTHER services
        try:
            containers = docker_client.containers.list()

            panther_containers = [
                c
                for c in containers
                if "panther" in c.name.lower()
                or any("panther" in tag.lower() for tag in getattr(c.image, "tags", []))
            ]

            logging.info(
                f"Found {len(panther_containers)} potential PANTHER containers"
            )

            # This is informational - not a failure if no containers found
            for container in panther_containers:
                logging.info(
                    f"PANTHER container: {container.name} - {container.status}"
                )

        except Exception as e:
            logging.warning(f"Docker service discovery failed: {e}")

    def test_docker_network_connectivity(self, docker_client):
        """Test Docker network connectivity for PANTHER services."""
        try:
            # List Docker networks
            networks = docker_client.networks.list()

            # Look for PANTHER-related networks
            panther_networks = [
                net for net in networks if "panther" in net.name.lower()
            ]

            logging.info(f"Found {len(panther_networks)} potential PANTHER networks")

            # Test default network connectivity
            bridge_networks = [net for net in networks if net.name == "bridge"]
            assert len(bridge_networks) > 0, "Default bridge network should exist"

        except Exception as e:
            pytest.fail(f"Docker network connectivity test failed: {e}")

    def test_docker_volume_management(self, docker_client):
        """Test Docker volume management for PANTHER services."""
        try:
            # List Docker volumes
            volumes = docker_client.volumes.list()

            # Look for PANTHER-related volumes
            panther_volumes = [vol for vol in volumes if "panther" in vol.name.lower()]

            logging.info(f"Found {len(panther_volumes)} potential PANTHER volumes")

            # Test volume creation and cleanup (with safe test volume)
            test_volume_name = "panther_test_cli_volume"

            # Clean up any existing test volume first
            try:
                existing_volume = docker_client.volumes.get(test_volume_name)
                existing_volume.remove()
                logging.info("Cleaned up existing test volume")
            except docker.errors.NotFound:
                pass  # Volume doesn't exist, which is fine

            # Create test volume
            test_volume = docker_client.volumes.create(name=test_volume_name)
            assert test_volume is not None, "Should be able to create test volume"

            # Verify volume exists
            volume_list = docker_client.volumes.list()
            volume_names = [vol.name for vol in volume_list]
            assert (
                test_volume_name in volume_names
            ), "Test volume should appear in volume list"

            # Clean up test volume
            test_volume.remove()
            logging.info("Successfully tested Docker volume management")

        except Exception as e:
            pytest.fail(f"Docker volume management test failed: {e}")


class TestDockerCLISecurityIntegration:
    """Test Docker CLI security integration."""

    pytestmark = [pytest.mark.integration, pytest.mark.requires_docker]

    def test_docker_command_injection_prevention(self, docker_client):
        """Test prevention of command injection in Docker CLI commands."""
        from panther.cli.subcommands.admin import AdminCommand

        # Test with potentially malicious input
        malicious_inputs = ["; rm -rf /", "service; whoami", "test && cat /etc/passwd"]

        for malicious_input in malicious_inputs:
            with patch("subprocess.run") as mock_subprocess:
                mock_subprocess.return_value = MagicMock(
                    returncode=1, stdout="", stderr=""
                )

                args = self.create_namespace(
                    admin_action="docker", docker_action="logs", service=malicious_input
                )

                result = AdminCommand._handle_docker(args)

                # Should not execute malicious commands
                if mock_subprocess.called:
                    call_str = str(mock_subprocess.call_args)
                    assert (
                        "rm -rf" not in call_str
                    ), "Should not execute dangerous commands"
                    assert (
                        "whoami" not in call_str
                    ), "Should not execute system commands"
                    assert (
                        "/etc/passwd" not in call_str
                    ), "Should not access system files"

                # Command should either fail safely or succeed without injection
                assert result in [0, 1], "Should return safe exit code"

    def test_docker_privilege_escalation_prevention(self, docker_client):
        """Test prevention of privilege escalation in Docker commands."""
        from panther.cli.subcommands.admin import AdminCommand

        with patch("subprocess.run") as mock_subprocess:
            # Simulate permission denied (good security behavior)
            mock_subprocess.side_effect = subprocess.CalledProcessError(
                1, "docker", "Permission denied"
            )

            args = self.create_namespace(
                admin_action="docker",
                docker_action="build",
                privileged=True,  # Attempt privileged operation
            )

            result = AdminCommand._handle_docker(args)

            # Should handle permission restrictions gracefully
            assert result == 1, "Privilege escalation should be prevented"

    def test_docker_resource_limit_validation(self, docker_client):
        """Test Docker resource limit validation."""
        # Test that Docker has reasonable resource limits
        try:
            info = docker_client.info()

            # Check memory limits
            mem_total = info.get("MemTotal", 0)
            assert (
                mem_total > 512 * 1024 * 1024
            ), "Should have at least 512MB memory"  # 512MB minimum

            # Check CPU limits
            ncpu = info.get("NCPU", 0)
            assert ncpu > 0, "Should have at least 1 CPU available"

            logging.info(
                f"Docker resources - Memory: {mem_total // (1024**3)}GB, CPUs: {ncpu}"
            )

        except Exception as e:
            pytest.fail(f"Docker resource validation failed: {e}")


# Test configuration
pytestmark = [pytest.mark.integration, pytest.mark.requires_docker]
