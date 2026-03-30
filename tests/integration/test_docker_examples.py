"""Docker Integration Examples using pytest-docker.

This file demonstrates how to use pytest-docker for PANTHER testing.
Includes examples of common Docker testing patterns.
"""

import logging
import time
from pathlib import Path

import docker
import pytest


# Example 1: Basic Docker Client Usage
@pytest.fixture(scope="session")
def docker_client():
    """Basic Docker client fixture."""
    try:
        client = docker.from_env()
        client.ping()
        return client
    except Exception as e:
        pytest.skip(f"Docker not available: {e}")


# Example 2: Docker Compose Integration
@pytest.fixture(scope="session")
def docker_compose_file(pytestconfig):
    """Docker Compose file for integration testing."""
    # Look for compose file in project root
    possible_files = ["docker-compose.yml", "docker-compose.yaml", "compose.yml"]

    for filename in possible_files:
        compose_path = Path(filename)
        if compose_path.exists():
            return compose_path

    # Return None if no compose file found
    return None


@pytest.fixture(scope="session")
def docker_compose_project_name():
    """Project name for Docker Compose testing."""
    return "panther_pytest_test"


# Example 3: Test Container Management
class TestDockerBasicOperations:
    """Basic Docker operations for testing."""

    pytestmark = [pytest.mark.requires_docker, pytest.mark.docker_integration]

    def test_docker_connectivity(self, docker_client):
        """Test basic Docker connectivity."""
        assert docker_client.ping() is True

        info = docker_client.info()
        logging.info(f"Docker Engine Version: {info.get('ServerVersion', 'unknown')}")

        # Basic health checks
        assert "ServerVersion" in info
        assert info.get("Containers", 0) >= 0

    def test_docker_image_operations(self, docker_client):
        """Test Docker image operations."""
        # List images
        images = docker_client.images.list()
        logging.info(f"Available images: {len(images)}")

        # Try to pull a lightweight test image
        try:
            image = docker_client.images.pull("alpine:latest")
            assert image is not None
            logging.info("Successfully pulled alpine:latest for testing")
        except Exception as e:
            logging.warning(f"Could not pull alpine image: {e}")

    @pytest.mark.slow
    def test_container_lifecycle(self, docker_client):
        """Test complete container lifecycle."""
        container = None

        try:
            # Create container
            container = docker_client.containers.create(
                "alpine:latest",
                command='echo "PANTHER test container"',
                name="panther_lifecycle_test",
                remove=True,  # Auto-remove when stopped
            )

            # Start container
            container.start()

            # Wait for completion
            result = container.wait(timeout=10)

            # Check exit code
            assert result["StatusCode"] == 0

            # Get logs
            logs = container.logs().decode("utf-8")
            assert "PANTHER test container" in logs

            logging.info("Container lifecycle test completed successfully")

        except Exception as e:
            pytest.fail(f"Container lifecycle test failed: {e}")
        finally:
            # Cleanup (container should auto-remove due to remove=True)
            if container:
                try:
                    container.reload()
                    if container.status != "exited":
                        container.stop()
                except Exception as e:
                    logging.warning(f"Container cleanup warning: {e}")


# Example 4: Docker Compose Integration
class TestDockerComposeIntegration:
    """Docker Compose integration examples."""

    pytestmark = [pytest.mark.requires_docker, pytest.mark.docker_integration]

    def test_compose_file_validation(self, docker_compose_file):
        """Test Docker Compose file validation."""
        if docker_compose_file is None:
            pytest.skip("No Docker Compose file found")

        # Test file is readable
        content = docker_compose_file.read_text()
        assert len(content) > 0

        # Basic structure validation
        assert "services:" in content
        logging.info(f"Validated Docker Compose file: {docker_compose_file}")

    def test_compose_service_validation(self, docker_compose_file):
        """Test Docker Compose service configuration."""
        if docker_compose_file is None:
            pytest.skip("No Docker Compose file found")

        try:
            import yaml

            with open(docker_compose_file, "r") as f:
                compose_data = yaml.safe_load(f)

            # Validate services structure
            assert "services" in compose_data
            services = compose_data["services"]
            assert isinstance(services, dict)

            # Log service information
            service_names = list(services.keys())
            logging.info(f"Docker Compose services: {service_names}")

            # Basic service validation
            for service_name, service_config in services.items():
                assert isinstance(
                    service_config, dict
                ), f"Service {service_name} should have dict config"
                logging.info(f"Service {service_name}: {list(service_config.keys())}")

        except ImportError:
            pytest.skip("PyYAML not available for compose validation")
        except Exception as e:
            pytest.fail(f"Compose service validation failed: {e}")


# Example 5: Network and Volume Testing
class TestDockerResourceManagement:
    """Test Docker resource management."""

    pytestmark = [pytest.mark.requires_docker, pytest.mark.docker_integration]

    def test_network_operations(self, docker_client):
        """Test Docker network operations."""
        # List networks
        networks = docker_client.networks.list()
        network_names = [net.name for net in networks]

        logging.info(f"Available networks: {network_names}")

        # Verify default networks exist
        assert "bridge" in network_names

        # Test network creation and cleanup
        test_network = None
        try:
            test_network = docker_client.networks.create(
                "panther_test_network", driver="bridge"
            )
            assert test_network is not None
            logging.info("Successfully created test network")

        finally:
            if test_network:
                try:
                    test_network.remove()
                    logging.info("Cleaned up test network")
                except Exception as e:
                    logging.warning(f"Network cleanup failed: {e}")

    def test_volume_operations(self, docker_client):
        """Test Docker volume operations."""
        # List volumes
        volumes = docker_client.volumes.list()
        logging.info(f"Available volumes: {len(volumes)}")

        # Test volume creation and cleanup
        test_volume = None
        try:
            test_volume = docker_client.volumes.create(
                name="panther_test_volume", driver="local"
            )
            assert test_volume is not None
            logging.info("Successfully created test volume")

            # Verify volume appears in list
            updated_volumes = docker_client.volumes.list()
            volume_names = [vol.name for vol in updated_volumes]
            assert "panther_test_volume" in volume_names

        finally:
            if test_volume:
                try:
                    test_volume.remove()
                    logging.info("Cleaned up test volume")
                except Exception as e:
                    logging.warning(f"Volume cleanup failed: {e}")


# Example 6: Performance and Resource Testing
class TestDockerPerformanceIntegration:
    """Test Docker performance characteristics."""

    pytestmark = [
        pytest.mark.requires_docker,
        pytest.mark.docker_integration,
        pytest.mark.slow,
    ]

    def test_container_startup_performance(self, docker_client):
        """Test container startup performance."""
        start_time = time.time()

        container = None
        try:
            # Create and start container
            container = docker_client.containers.create(
                "alpine:latest",
                command="echo 'performance test'",
                name="panther_perf_test",
            )

            creation_time = time.time()
            container.start()
            start_complete_time = time.time()

            # Wait for completion
            result = container.wait(timeout=5)
            completion_time = time.time()

            # Calculate timing metrics
            creation_duration = creation_time - start_time
            startup_duration = start_complete_time - creation_time
            total_duration = completion_time - start_time

            logging.info(f"Container performance metrics:")
            logging.info(f"  Creation: {creation_duration:.3f}s")
            logging.info(f"  Startup: {startup_duration:.3f}s")
            logging.info(f"  Total: {total_duration:.3f}s")

            # Performance assertions
            assert creation_duration < 5.0, "Container creation should be fast"
            assert startup_duration < 3.0, "Container startup should be fast"
            assert total_duration < 10.0, "Total execution should be reasonable"
            assert result["StatusCode"] == 0, "Container should execute successfully"

        finally:
            if container:
                try:
                    container.remove(force=True)
                except Exception as e:
                    logging.warning(f"Performance test cleanup failed: {e}")

    def test_resource_monitoring(self, docker_client):
        """Test Docker resource monitoring."""
        container = None
        try:
            # Create container with resource limits
            container = docker_client.containers.create(
                "alpine:latest",
                command="sleep 2",
                name="panther_resource_test",
                mem_limit="50m",  # 50MB limit
                cpu_period=100000,
                cpu_quota=50000,  # 50% CPU limit
            )

            container.start()

            # Wait a moment for container to be running
            time.sleep(0.5)

            # Get resource stats
            stats = container.stats(stream=False)

            # Verify stats structure
            assert "memory" in stats
            assert "cpu" in stats

            # Check memory stats
            memory_stats = stats["memory"]
            assert "usage" in memory_stats
            assert "limit" in memory_stats

            logging.info(
                f"Memory usage: {memory_stats.get('usage', 0) / 1024 / 1024:.1f}MB"
            )
            logging.info(
                f"Memory limit: {memory_stats.get('limit', 0) / 1024 / 1024:.1f}MB"
            )

            # Wait for container to complete
            result = container.wait(timeout=5)
            assert result["StatusCode"] == 0

        finally:
            if container:
                try:
                    container.remove(force=True)
                except Exception as e:
                    logging.warning(f"Resource test cleanup failed: {e}")


# Usage Examples in Documentation
"""
To run these Docker integration tests:

1. All Docker tests:
   pytest tests/integration/test_docker_examples.py -m requires_docker

2. Just basic operations:
   pytest tests/integration/test_docker_examples.py::TestDockerBasicOperations

3. Skip slow tests:
   pytest tests/integration/test_docker_examples.py -m "requires_docker and not slow"

4. With verbose Docker output:
   pytest tests/integration/test_docker_examples.py -v -s

5. Run only if Docker is available:
   pytest tests/integration/test_docker_examples.py -m docker_integration
"""
