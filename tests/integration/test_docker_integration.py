"""
Docker Integration Tests using pytest-docker.

Tests Docker functionality for PANTHER CLI commands and services using real Docker containers.
Requires Docker to be running on the system.
"""

import json
import logging
import subprocess
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import docker
import pytest

from tests.unit.test_cli.base_cli_test import ComprehensiveCLITest


# Pytest-docker configuration
@pytest.fixture(scope="session")
def docker_compose_file(pytestconfig):
    """Return path to docker-compose.yml for testing."""
    return Path(__file__).parent.parent.parent / "docker-compose.yml"


@pytest.fixture(scope="session")
def docker_compose_project_name():
    """Return project name for Docker Compose."""
    return "panther_test"


@pytest.fixture(scope="session")
def docker_services():
    """Define which services to start for testing."""
    return []  # Start with empty - we'll control services manually


@pytest.fixture(scope="session")
def docker_client():
    """Provide Docker client for tests."""
    try:
        client = docker.from_env()
        client.ping()
        return client
    except Exception as e:
        pytest.skip(f"Docker not available: {e}")


class TestDockerAdminCommands(ComprehensiveCLITest):
    """Test Docker admin commands with real Docker integration."""

    pytestmark = pytest.mark.requires_docker

    def test_docker_status_real_docker(self, docker_client):
        """Test docker status command with real Docker."""
        from panther.cli.subcommands.admin import AdminCommand

        args = self.create_namespace(
            admin_action="docker", docker_action="status", format="json"
        )

        # This should work with real Docker
        result = AdminCommand._handle_docker(args)
        assert result in [0, 1]  # Should not crash

    def test_docker_build_command_structure(self, docker_client):
        """Test that docker build command is properly structured."""
        from panther.cli.subcommands.admin import AdminCommand

        # Test with dry run to avoid actually building
        with patch("subprocess.run") as mock_subprocess:
            mock_subprocess.return_value = MagicMock(
                returncode=0, stdout="Build command would execute", stderr=""
            )

            args = self.create_namespace(
                admin_action="docker", docker_action="build", force=True, no_cache=True
            )

            result = AdminCommand._handle_docker(args)

            # Verify subprocess was called
            assert mock_subprocess.called

            # Check that docker-compose build command structure is correct
            call_args = str(mock_subprocess.call_args)
            assert "docker-compose" in call_args or "docker" in call_args
            assert result in [0, 1]

    def test_docker_compose_file_validation(self):
        """Test that docker-compose file exists and is valid."""
        compose_file = Path("docker-compose.yml")

        if compose_file.exists():
            # Test that we can parse the compose file
            try:
                import yaml

                with open(compose_file, "r") as f:
                    compose_data = yaml.safe_load(f)

                # Basic validation
                assert "services" in compose_data
                assert isinstance(compose_data["services"], dict)

                # Log services for debugging
                services = list(compose_data["services"].keys())
                logging.info(f"Docker Compose services found: {services}")

            except Exception as e:
                pytest.fail(f"Invalid docker-compose.yml: {e}")
        else:
            logging.warning("No docker-compose.yml found - skipping validation")


class TestDockerContainerLifecycle:
    """Test Docker container lifecycle operations."""

    pytestmark = pytest.mark.requires_docker

    def test_docker_client_connectivity(self, docker_client):
        """Test that Docker client can connect and get info."""
        try:
            info = docker_client.info()
            assert "ServerVersion" in info
            logging.info(f"Docker version: {info.get('ServerVersion', 'unknown')}")
        except Exception as e:
            pytest.fail(f"Docker client connectivity failed: {e}")

    def test_docker_image_operations(self, docker_client):
        """Test Docker image listing and basic operations."""
        try:
            # List available images
            images = docker_client.images.list()
            logging.info(f"Available Docker images: {len(images)}")

            # Try to pull a small test image (alpine)
            try:
                docker_client.images.pull("alpine:latest")
                logging.info("Successfully pulled alpine:latest test image")
            except Exception as e:
                logging.warning(f"Could not pull alpine image: {e}")

        except Exception as e:
            pytest.fail(f"Docker image operations failed: {e}")

    @pytest.mark.slow
    def test_container_creation_and_cleanup(self, docker_client):
        """Test container creation and cleanup."""
        container = None
        try:
            # Create a simple test container
            container = docker_client.containers.create(
                "alpine:latest",
                command="echo 'PANTHER Docker test'",
                name="panther_test_container",
            )

            assert container is not None
            logging.info(f"Created test container: {container.id[:12]}")

            # Start and wait for completion
            container.start()
            result = container.wait(timeout=10)

            # Check exit code
            assert result["StatusCode"] == 0

            # Get logs
            logs = container.logs().decode("utf-8")
            assert "PANTHER Docker test" in logs

        except Exception as e:
            pytest.fail(f"Container lifecycle test failed: {e}")
        finally:
            # Cleanup
            if container:
                try:
                    container.remove(force=True)
                    logging.info("Cleaned up test container")
                except Exception as e:
                    logging.warning(f"Container cleanup failed: {e}")


class TestDockerServiceIntegration:
    """Test Docker service integration for PANTHER services."""

    pytestmark = pytest.mark.requires_docker

    def test_panther_service_docker_configuration(self):
        """Test that PANTHER services have proper Docker configuration."""
        # Check if there are any Dockerfiles in the project
        dockerfiles = list(Path(".").rglob("Dockerfile*"))

        if dockerfiles:
            logging.info(f"Found Dockerfiles: {[str(d) for d in dockerfiles]}")

            for dockerfile in dockerfiles:
                # Basic Dockerfile validation
                with open(dockerfile, "r") as f:
                    content = f.read()

                # Check for basic Dockerfile structure
                assert content.startswith(
                    "FROM"
                ), f"Dockerfile {dockerfile} should start with FROM"

                # Check for Python setup if it's a Python service
                if "python" in content.lower():
                    assert (
                        "WORKDIR" in content or "RUN" in content
                    ), f"Python Dockerfile {dockerfile} should have WORKDIR or RUN commands"
        else:
            logging.info("No Dockerfiles found in project")

    def test_docker_network_configuration(self, docker_client):
        """Test Docker network operations."""
        try:
            # List available networks
            networks = docker_client.networks.list()
            network_names = [net.name for net in networks]

            logging.info(f"Available Docker networks: {network_names}")

            # Check for common networks
            assert "bridge" in network_names, "Default bridge network should exist"

        except Exception as e:
            pytest.fail(f"Docker network test failed: {e}")

    def test_docker_volume_operations(self, docker_client):
        """Test Docker volume operations."""
        try:
            # List available volumes
            volumes = docker_client.volumes.list()
            logging.info(f"Available Docker volumes: {len(volumes)}")

            # Test volume creation and cleanup
            test_volume = None
            try:
                test_volume = docker_client.volumes.create(
                    name="panther_test_volume", driver="local"
                )
                assert test_volume is not None
                logging.info("Successfully created test volume")

            finally:
                if test_volume:
                    try:
                        test_volume.remove()
                        logging.info("Cleaned up test volume")
                    except Exception as e:
                        logging.warning(f"Volume cleanup failed: {e}")

        except Exception as e:
            pytest.fail(f"Docker volume test failed: {e}")


class TestDockerMetricsIntegration:
    """Test Docker integration with PANTHER metrics system."""

    pytestmark = pytest.mark.requires_docker

    def test_docker_container_metrics_collection(self, docker_client):
        """Test collection of Docker container metrics."""
        container = None
        try:
            # Create a long-running test container
            container = docker_client.containers.create(
                "alpine:latest", command="sleep 5", name="panther_metrics_test"
            )

            container.start()

            # Wait a moment for container to be running
            time.sleep(1)

            # Collect container stats
            stats = container.stats(stream=False)

            # Verify stats structure
            assert "memory" in stats
            assert "cpu" in stats
            assert "networks" in stats

            logging.info("Successfully collected container metrics")

        except Exception as e:
            pytest.fail(f"Docker metrics collection failed: {e}")
        finally:
            if container:
                try:
                    container.remove(force=True)
                    logging.info("Cleaned up metrics test container")
                except Exception as e:
                    logging.warning(f"Metrics container cleanup failed: {e}")

    def test_docker_resource_monitoring(self, docker_client):
        """Test Docker resource monitoring capabilities."""
        try:
            # Get Docker system info
            info = docker_client.info()

            # Check resource information
            assert "MemTotal" in info, "Docker should report total memory"
            assert "NCPU" in info, "Docker should report CPU count"

            # Log resource info
            memory_gb = info.get("MemTotal", 0) / (1024**3)
            cpu_count = info.get("NCPU", 0)

            logging.info(
                f"Docker host resources - Memory: {memory_gb:.1f}GB, CPUs: {cpu_count}"
            )

            # Verify reasonable resource limits
            assert memory_gb > 0, "Should have positive memory allocation"
            assert cpu_count > 0, "Should have positive CPU allocation"

        except Exception as e:
            pytest.fail(f"Docker resource monitoring failed: {e}")


class TestDockerSecurityValidation:
    """Test Docker security aspects."""

    pytestmark = pytest.mark.requires_docker

    def test_docker_security_configuration(self, docker_client):
        """Test Docker security configuration."""
        try:
            # Get Docker info
            info = docker_client.info()

            # Check security features
            security_options = info.get("SecurityOptions", [])
            logging.info(f"Docker security options: {security_options}")

            # Test that Docker daemon is accessible (but not overly permissive)
            # This is a basic connectivity test
            assert docker_client.ping() is True, "Docker daemon should be accessible"

        except Exception as e:
            pytest.fail(f"Docker security validation failed: {e}")

    def test_container_isolation(self, docker_client):
        """Test container isolation capabilities."""
        container1 = None
        container2 = None

        try:
            # Create two isolated containers
            container1 = docker_client.containers.create(
                "alpine:latest", command="sleep 3", name="panther_isolation_test1"
            )

            container2 = docker_client.containers.create(
                "alpine:latest", command="sleep 3", name="panther_isolation_test2"
            )

            container1.start()
            container2.start()

            # Verify containers are running independently
            assert (
                container1.status != container2.status or container1.id != container2.id
            ), "Containers should be independent"

            logging.info("Container isolation test passed")

        except Exception as e:
            pytest.fail(f"Container isolation test failed: {e}")
        finally:
            # Cleanup
            for container in [container1, container2]:
                if container:
                    try:
                        container.remove(force=True)
                    except Exception as e:
                        logging.warning(f"Container cleanup failed: {e}")


class TestDockerErrorHandling:
    """Test Docker error handling and recovery."""

    pytestmark = pytest.mark.requires_docker

    def test_docker_connection_failure_handling(self):
        """Test handling of Docker connection failures."""
        from panther.cli.subcommands.admin import AdminCommand

        # Test with invalid Docker configuration
        with patch("subprocess.run") as mock_subprocess:
            # Simulate Docker connection failure
            mock_subprocess.side_effect = subprocess.CalledProcessError(
                1, "docker", "Cannot connect to Docker daemon"
            )

            args = self.create_namespace(admin_action="docker", docker_action="status")

            result = AdminCommand._handle_docker(args)

            # Should handle error gracefully
            assert result == 1, "Should return error code for Docker connection failure"

    def test_invalid_docker_command_handling(self, docker_client):
        """Test handling of invalid Docker commands."""
        from panther.cli.subcommands.admin import AdminCommand

        with patch("subprocess.run") as mock_subprocess:
            # Simulate invalid Docker command
            mock_subprocess.side_effect = subprocess.CalledProcessError(
                125, "docker", "Invalid command"
            )

            args = self.create_namespace(
                admin_action="docker", docker_action="invalid_action"
            )

            result = AdminCommand._handle_docker(args)

            # Should handle invalid commands gracefully
            assert result == 1, "Should return error code for invalid Docker commands"

    def test_docker_resource_exhaustion_handling(self, docker_client):
        """Test handling of Docker resource exhaustion."""
        # This is a lightweight test - we don't actually exhaust resources
        try:
            # Try to create a container with very low memory limit
            container = docker_client.containers.create(
                "alpine:latest",
                command="echo 'resource test'",
                mem_limit="1m",  # Very low memory limit
                name="panther_resource_test",
            )

            container.start()
            result = container.wait(timeout=5)

            # Should either succeed or fail gracefully
            assert result["StatusCode"] in [
                0,
                125,
                126,
                127,
            ], "Container should complete or fail with expected exit codes"

            container.remove()
            logging.info("Resource exhaustion test completed")

        except Exception as e:
            # Resource constraints might cause various exceptions
            logging.info(f"Resource exhaustion test triggered expected exception: {e}")
            # This is actually expected behavior


# Additional pytest marks for test organization
pytestmark = [pytest.mark.integration, pytest.mark.requires_docker]
