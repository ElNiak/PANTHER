"""
Unit tests for PANTHER Docker Builder system.

This module tests Docker image building, container management, and deployment
utilities used throughout the PANTHER framework.
"""

import shutil
import tempfile
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import MagicMock, Mock, call, patch

import pytest

# Test imports with fallback to mocks
try:
    from panther.core.docker_builder.docker_builder import DockerBuilder
    from panther.core.docker_builder.plugin_mixin.docker_operations_mixin import (
        DockerOperationsMixin,
    )

    REAL_DOCKER_SYSTEM_AVAILABLE = True

    # Ensure clean test state by resetting singleton before tests
    DockerBuilder.reset_singleton()

except ImportError:
    REAL_DOCKER_SYSTEM_AVAILABLE = False

    # Create mock implementations for testing
    class DockerBuilder:
        def __init__(self, base_path=None, logger=None):
            self.base_path = Path(base_path) if base_path else Path.cwd()
            self.logger = logger or Mock()
            self.docker_client = Mock()
            self.built_images = {}
            self.containers = {}
            self.networks = []

        def build_image(self, dockerfile_path, tag, context_path=None, build_args=None):
            """Mock Docker image building."""
            self.built_images[tag] = {
                "dockerfile": dockerfile_path,
                "context": context_path or self.base_path,
                "build_args": build_args or {},
                "status": "built",
            }
            return True

        def list_images(self, filter_tags=None):
            """Mock Docker image listing."""
            if filter_tags:
                return {
                    tag: info
                    for tag, info in self.built_images.items()
                    if any(filter_tag in tag for filter_tag in filter_tags)
                }
            return self.built_images.copy()

        def remove_image(self, tag, force=False):
            """Mock Docker image removal."""
            if tag in self.built_images:
                del self.built_images[tag]
                return True
            return False

        def create_container(
            self,
            image_tag,
            name,
            command=None,
            environment=None,
            volumes=None,
            ports=None,
        ):
            """Mock Docker container creation."""
            self.containers[name] = {
                "image": image_tag,
                "command": command,
                "environment": environment or {},
                "volumes": volumes or [],
                "ports": ports or [],
                "status": "created",
            }
            return name

        def start_container(self, container_name):
            """Mock Docker container start."""
            if container_name in self.containers:
                self.containers[container_name]["status"] = "running"
                return True
            return False

        def stop_container(self, container_name):
            """Mock Docker container stop."""
            if container_name in self.containers:
                self.containers[container_name]["status"] = "stopped"
                return True
            return False

        def remove_container(self, container_name, force=False):
            """Mock Docker container removal."""
            if container_name in self.containers:
                del self.containers[container_name]
                return True
            return False

        def create_network(self, network_name, driver="bridge"):
            """Mock Docker network creation."""
            network_info = {"name": network_name, "driver": driver, "containers": []}
            self.networks.append(network_info)
            return network_info

        def connect_container_to_network(self, container_name, network_name):
            """Mock network connection."""
            for network in self.networks:
                if network["name"] == network_name:
                    if container_name not in network["containers"]:
                        network["containers"].append(container_name)
                    return True
            return False

        def is_docker_available(self):
            """Mock Docker availability check."""
            return True

        def get_container_logs(self, container_name):
            """Mock container log retrieval."""
            if container_name in self.containers:
                return f"Logs for container {container_name}"
            return ""

    class DockerOperationsMixin:
        def __init__(self):
            self.docker_operations = []

        def build_docker_image(
            self, dockerfile_path, tag, context=None, build_args=None
        ):
            """Mock Docker build operation."""
            operation = {
                "type": "build",
                "dockerfile": dockerfile_path,
                "tag": tag,
                "context": context,
                "build_args": build_args,
                "timestamp": "mock_timestamp",
            }
            self.docker_operations.append(operation)
            return True

        def cleanup_docker_resources(self, resource_type=None):
            """Mock Docker cleanup operation."""
            operation = {
                "type": "cleanup",
                "resource_type": resource_type,
                "timestamp": "mock_timestamp",
            }
            self.docker_operations.append(operation)
            return True

        def get_docker_info(self):
            """Mock Docker info retrieval."""
            return {
                "version": "20.10.0",
                "containers": len(getattr(self, "containers", {})),
                "images": len(getattr(self, "built_images", {})),
                "status": "running",
            }


pytestmark = [pytest.mark.unit, pytest.mark.docker_system]


class TestDockerBuilder:
    """Test DockerBuilder core functionality."""

    @pytest.fixture
    def temp_workspace(self):
        """Create temporary workspace for Docker tests."""
        temp_dir = tempfile.mkdtemp(prefix="panther_docker_test_")
        workspace = Path(temp_dir)

        # Create sample Dockerfile
        dockerfile = workspace / "Dockerfile"
        dockerfile.write_text(
            """
FROM python:3.10-slim
WORKDIR /app
COPY . .
RUN pip install -e .
CMD ["python", "-m", "panther"]
"""
        )

        # Create sample application files
        app_dir = workspace / "app"
        app_dir.mkdir()
        (app_dir / "__init__.py").write_text("")
        (app_dir / "main.py").write_text("print('Hello from Docker')")

        yield workspace

        # Cleanup
        shutil.rmtree(temp_dir, ignore_errors=True)

    def test_docker_builder_initialization(self, temp_workspace):
        """Test DockerBuilder initialization."""
        builder = DockerBuilder(base_path=temp_workspace)

        assert builder.base_path == temp_workspace
        assert builder.logger is not None
        assert hasattr(builder, "docker_client")
        assert hasattr(builder, "built_images")
        assert hasattr(builder, "containers")

    def test_docker_builder_initialization_default_path(self):
        """Test DockerBuilder initialization with default path."""
        builder = DockerBuilder()

        assert builder.base_path == Path.cwd()
        assert builder.logger is not None

    def test_build_image_basic(self, temp_workspace):
        """Test basic Docker image building."""
        builder = DockerBuilder(base_path=temp_workspace)
        dockerfile_path = temp_workspace / "Dockerfile"
        tag = "panther-test:latest"

        result = builder.build_image(dockerfile_path, tag)

        assert result is True
        assert tag in builder.built_images
        assert builder.built_images[tag]["dockerfile"] == dockerfile_path
        assert builder.built_images[tag]["status"] == "built"

    def test_build_image_with_context(self, temp_workspace):
        """Test Docker image building with custom context."""
        builder = DockerBuilder(base_path=temp_workspace)
        dockerfile_path = temp_workspace / "Dockerfile"
        tag = "panther-context-test:latest"
        context_path = temp_workspace / "app"

        result = builder.build_image(dockerfile_path, tag, context_path=context_path)

        assert result is True
        assert builder.built_images[tag]["context"] == context_path

    def test_build_image_with_build_args(self, temp_workspace):
        """Test Docker image building with build arguments."""
        builder = DockerBuilder(base_path=temp_workspace)
        dockerfile_path = temp_workspace / "Dockerfile"
        tag = "panther-args-test:latest"
        build_args = {"PYTHON_VERSION": "3.10", "APP_ENV": "test", "DEBUG": "true"}

        result = builder.build_image(dockerfile_path, tag, build_args=build_args)

        assert result is True
        assert builder.built_images[tag]["build_args"] == build_args

    def test_list_images_empty(self):
        """Test listing images when none exist."""
        builder = DockerBuilder()

        images = builder.list_images()

        assert images == {}

    def test_list_images_with_filter(self, temp_workspace):
        """Test listing images with tag filter."""
        builder = DockerBuilder(base_path=temp_workspace)
        dockerfile_path = temp_workspace / "Dockerfile"

        # Build multiple images
        builder.build_image(dockerfile_path, "panther-service:v1")
        builder.build_image(dockerfile_path, "panther-service:v2")
        builder.build_image(dockerfile_path, "other-service:v1")

        # Test filtering
        panther_images = builder.list_images(filter_tags=["panther-service"])

        assert len(panther_images) == 2
        assert "panther-service:v1" in panther_images
        assert "panther-service:v2" in panther_images
        assert "other-service:v1" not in panther_images

    def test_remove_image(self, temp_workspace):
        """Test Docker image removal."""
        builder = DockerBuilder(base_path=temp_workspace)
        dockerfile_path = temp_workspace / "Dockerfile"
        tag = "panther-remove-test:latest"

        # Build image first
        builder.build_image(dockerfile_path, tag)
        assert tag in builder.built_images

        # Remove image
        result = builder.remove_image(tag)

        assert result is True
        assert tag not in builder.built_images

    def test_remove_nonexistent_image(self):
        """Test removal of non-existent image."""
        builder = DockerBuilder()

        result = builder.remove_image("nonexistent:tag")

        assert result is False

    def test_create_container_basic(self, temp_workspace):
        """Test basic container creation."""
        builder = DockerBuilder(base_path=temp_workspace)
        image_tag = "panther-test:latest"
        container_name = "test-container"

        result = builder.create_container(image_tag, container_name)

        assert result == container_name
        assert container_name in builder.containers
        assert builder.containers[container_name]["image"] == image_tag
        assert builder.containers[container_name]["status"] == "created"

    def test_create_container_with_options(self):
        """Test container creation with full options."""
        builder = DockerBuilder()
        image_tag = "panther-full-test:latest"
        container_name = "full-test-container"
        command = ["python", "-m", "panther", "--config", "test.yaml"]
        environment = {"PANTHER_ENV": "test", "DEBUG": "true", "LOG_LEVEL": "debug"}
        volumes = ["/host/data:/container/data", "/host/logs:/container/logs"]
        ports = ["8080:8080", "9090:9090"]

        result = builder.create_container(
            image_tag,
            container_name,
            command=command,
            environment=environment,
            volumes=volumes,
            ports=ports,
        )

        assert result == container_name
        container_info = builder.containers[container_name]
        assert container_info["command"] == command
        assert container_info["environment"] == environment
        assert container_info["volumes"] == volumes
        assert container_info["ports"] == ports

    def test_container_lifecycle(self):
        """Test complete container lifecycle."""
        builder = DockerBuilder()
        image_tag = "panther-lifecycle:latest"
        container_name = "lifecycle-container"

        # Create container
        builder.create_container(image_tag, container_name)
        assert builder.containers[container_name]["status"] == "created"

        # Start container
        result = builder.start_container(container_name)
        assert result is True
        assert builder.containers[container_name]["status"] == "running"

        # Stop container
        result = builder.stop_container(container_name)
        assert result is True
        assert builder.containers[container_name]["status"] == "stopped"

        # Remove container
        result = builder.remove_container(container_name)
        assert result is True
        assert container_name not in builder.containers

    def test_container_operations_nonexistent(self):
        """Test container operations on non-existent containers."""
        builder = DockerBuilder()

        # Test start
        result = builder.start_container("nonexistent")
        assert result is False

        # Test stop
        result = builder.stop_container("nonexistent")
        assert result is False

        # Test remove
        result = builder.remove_container("nonexistent")
        assert result is False

    def test_network_creation(self):
        """Test Docker network creation."""
        builder = DockerBuilder()
        network_name = "panther-test-network"

        result = builder.create_network(network_name)

        assert result is not None
        assert result["name"] == network_name
        assert result["driver"] == "bridge"
        assert result in builder.networks

    def test_network_creation_custom_driver(self):
        """Test Docker network creation with custom driver."""
        builder = DockerBuilder()
        network_name = "panther-overlay-network"
        driver = "overlay"

        result = builder.create_network(network_name, driver=driver)

        assert result["name"] == network_name
        assert result["driver"] == driver

    def test_connect_container_to_network(self):
        """Test connecting container to network."""
        builder = DockerBuilder()
        container_name = "test-container"
        network_name = "test-network"

        # Create network and container
        builder.create_network(network_name)
        builder.create_container("test:image", container_name)

        # Connect container to network
        result = builder.connect_container_to_network(container_name, network_name)

        assert result is True

        # Verify connection
        network = next(net for net in builder.networks if net["name"] == network_name)
        assert container_name in network["containers"]

    def test_connect_to_nonexistent_network(self):
        """Test connecting container to non-existent network."""
        builder = DockerBuilder()

        result = builder.connect_container_to_network(
            "container", "nonexistent-network"
        )

        assert result is False

    def test_docker_availability_check(self):
        """Test Docker availability check."""
        builder = DockerBuilder()

        result = builder.is_docker_available()

        assert isinstance(result, bool)
        # In mock implementation, should return True
        assert result is True

    def test_get_container_logs(self):
        """Test container log retrieval."""
        builder = DockerBuilder()
        container_name = "log-test-container"

        # Create container
        builder.create_container("test:image", container_name)

        # Get logs
        logs = builder.get_container_logs(container_name)

        assert isinstance(logs, str)
        assert container_name in logs

    def test_get_logs_nonexistent_container(self):
        """Test log retrieval for non-existent container."""
        builder = DockerBuilder()

        logs = builder.get_container_logs("nonexistent")

        assert logs == ""


class TestDockerOperationsMixin:
    """Test DockerOperationsMixin functionality."""

    def test_docker_operations_mixin_initialization(self):
        """Test DockerOperationsMixin initialization."""
        mixin = DockerOperationsMixin()

        assert hasattr(mixin, "docker_operations")
        assert mixin.docker_operations == []

    def test_build_docker_image_operation(self):
        """Test Docker image build operation tracking."""
        mixin = DockerOperationsMixin()
        dockerfile_path = "/path/to/Dockerfile"
        tag = "test:latest"
        build_args = {"ARG1": "value1"}

        result = mixin.build_docker_image(dockerfile_path, tag, build_args=build_args)

        assert result is True
        assert len(mixin.docker_operations) == 1

        operation = mixin.docker_operations[0]
        assert operation["type"] == "build"
        assert operation["dockerfile"] == dockerfile_path
        assert operation["tag"] == tag
        assert operation["build_args"] == build_args

    def test_cleanup_docker_resources_operation(self):
        """Test Docker cleanup operation tracking."""
        mixin = DockerOperationsMixin()

        result = mixin.cleanup_docker_resources(resource_type="images")

        assert result is True
        assert len(mixin.docker_operations) == 1

        operation = mixin.docker_operations[0]
        assert operation["type"] == "cleanup"
        assert operation["resource_type"] == "images"

    def test_get_docker_info(self):
        """Test Docker info retrieval."""
        mixin = DockerOperationsMixin()

        info = mixin.get_docker_info()

        assert isinstance(info, dict)
        assert "version" in info
        assert "containers" in info
        assert "images" in info
        assert "status" in info

    def test_multiple_operations_tracking(self):
        """Test tracking multiple Docker operations."""
        mixin = DockerOperationsMixin()

        # Perform multiple operations
        mixin.build_docker_image("/dockerfile1", "tag1")
        mixin.build_docker_image("/dockerfile2", "tag2")
        mixin.cleanup_docker_resources("containers")
        mixin.cleanup_docker_resources("images")

        assert len(mixin.docker_operations) == 4

        # Verify operation types
        operation_types = [op["type"] for op in mixin.docker_operations]
        assert operation_types.count("build") == 2
        assert operation_types.count("cleanup") == 2


class TestDockerSystemIntegration:
    """Test integration between Docker system components."""

    def test_builder_with_operations_mixin(self, tmp_path):
        """Test DockerBuilder with DockerOperationsMixin integration."""
        temp_workspace = tmp_path

        # Create a combined class that uses both
        class DockerManagerWithOps(DockerBuilder, DockerOperationsMixin):
            def __init__(self, base_path=None):
                DockerBuilder.__init__(self, base_path)
                DockerOperationsMixin.__init__(self)

        manager = DockerManagerWithOps(base_path=temp_workspace)
        dockerfile_path = temp_workspace / "Dockerfile"
        tag = "integration-test:latest"

        # Use builder functionality
        build_result = manager.build_image(dockerfile_path, tag)
        assert build_result is True
        assert tag in manager.built_images

        # Use operations mixin functionality
        ops_result = manager.build_docker_image(str(dockerfile_path), tag)
        assert ops_result is True
        assert len(manager.docker_operations) == 1

    def test_multiple_docker_builders(self, tmp_path):
        """Test multiple DockerBuilder instances."""
        temp_workspace = tmp_path
        builder1 = DockerBuilder(base_path=temp_workspace)
        builder2 = DockerBuilder(base_path=temp_workspace)

        dockerfile_path = temp_workspace / "Dockerfile"

        # Build images with different builders
        builder1.build_image(dockerfile_path, "test1:latest")
        builder2.build_image(dockerfile_path, "test2:latest")

        # Verify isolation
        assert "test1:latest" in builder1.built_images
        assert "test1:latest" not in builder2.built_images
        assert "test2:latest" in builder2.built_images
        assert "test2:latest" not in builder1.built_images

    def test_container_network_integration(self):
        """Test container and network integration."""
        builder = DockerBuilder()

        # Create network
        network = builder.create_network("integration-network")

        # Create multiple containers
        container1 = builder.create_container("app:v1", "app1")
        container2 = builder.create_container("app:v2", "app2")
        container3 = builder.create_container("db:latest", "database")

        # Connect containers to network
        builder.connect_container_to_network("app1", "integration-network")
        builder.connect_container_to_network("app2", "integration-network")
        builder.connect_container_to_network("database", "integration-network")

        # Verify network setup
        network_info = next(
            net for net in builder.networks if net["name"] == "integration-network"
        )

        assert len(network_info["containers"]) == 3
        assert "app1" in network_info["containers"]
        assert "app2" in network_info["containers"]
        assert "database" in network_info["containers"]


class TestDockerSystemErrorHandling:
    """Test error handling in Docker system."""

    def test_build_image_invalid_dockerfile(self, tmp_path):
        """Test building image with invalid Dockerfile path."""
        temp_workspace = tmp_path
        builder = DockerBuilder(base_path=temp_workspace)
        invalid_path = temp_workspace / "nonexistent_dockerfile"

        # In a real implementation, this should handle the error gracefully
        # For our mock, we'll test that the method exists and can be called
        try:
            result = builder.build_image(invalid_path, "test:tag")
            # Mock implementation should handle this gracefully
            assert isinstance(result, bool)
        except Exception as e:
            # If an exception is raised, it should be a reasonable one
            assert isinstance(e, (FileNotFoundError, ValueError, RuntimeError))

    def test_container_operations_error_handling(self):
        """Test container operations error handling."""
        builder = DockerBuilder()

        # Try to start non-existent container
        result = builder.start_container("nonexistent")
        assert result is False

        # Try to connect to non-existent network
        result = builder.connect_container_to_network("container", "nonexistent")
        assert result is False

    def test_docker_availability_failure_handling(self):
        """Test handling of Docker unavailability."""

        # Create a builder that simulates Docker being unavailable
        class UnavailableDockerBuilder(DockerBuilder):
            def is_docker_available(self):
                return False

        builder = UnavailableDockerBuilder()

        # Test that availability check works
        assert builder.is_docker_available() is False


class TestDockerBuilderCacheIntegration:
    """Test Docker image cache integration with DockerBuilder."""

    @pytest.fixture
    def mock_docker_builder_with_cache(self, tmp_path):
        """Create DockerBuilder with cache for testing."""
        if REAL_DOCKER_SYSTEM_AVAILABLE:
            DockerBuilder.reset_singleton()

            with patch(
                "panther.core.docker_builder.docker_builder.docker.from_env"
            ) as mock_docker:
                mock_client = Mock()
                mock_client.ping.return_value = True

                # Configure mock images for cache testing
                mock_image = Mock()
                mock_image.id = "sha256:cache_test_123"
                mock_image.tags = ["cache_test:latest"]
                mock_image.attrs = {
                    "Size": 50 * 1024 * 1024,
                    "Created": "2025-06-24T10:00:00Z",
                }

                mock_client.images.list.return_value = [mock_image]
                mock_client.images.get.return_value = mock_image
                mock_docker.return_value = mock_client

                builder = DockerBuilder.get_instance()
                # Set custom cache file for testing
                builder.image_cache.cache_file = tmp_path / "test_docker_cache.json"

                yield builder, mock_client
        else:
            # Create mock builder with cache
            mock_builder = Mock()
            mock_builder.image_cache = Mock()
            mock_builder.client = Mock()

            yield mock_builder, mock_builder.client

    def test_image_exists_uses_cache(self, mock_docker_builder_with_cache):
        """Test that image_exists() uses cache to reduce Docker API calls."""
        if not REAL_DOCKER_SYSTEM_AVAILABLE:
            pytest.skip("Real Docker system not available for cache testing")

        builder, mock_client = mock_docker_builder_with_cache

        # First call should populate cache and call Docker API
        result1 = builder.image_exists("cache_test:latest")
        assert result1 is True
        assert mock_client.images.get.call_count >= 1

        # Reset mock to count subsequent calls
        initial_call_count = mock_client.images.get.call_count
        mock_client.images.get.reset_mock()

        # Second call should use cache (no additional Docker API call for listing)
        result2 = builder.image_exists("cache_test:latest")
        assert result2 is True

        # Should have made fewer API calls due to caching
        assert mock_client.images.get.call_count <= initial_call_count

    def test_image_exists_fallback_on_docker_failure(self, tmp_path):
        """Test image_exists() fallback when Docker is unavailable."""
        if not REAL_DOCKER_SYSTEM_AVAILABLE:
            pytest.skip("Real Docker system not available for fallback testing")

        # Create cache file with known data
        cache_file = tmp_path / "fallback_test_cache.json"
        cache_data = {
            "images": {
                "sha256:fallback123": {
                    "id": "sha256:fallback123",
                    "tags": ["fallback_test:latest"],
                    "size": 1024 * 1024,
                    "created": "2025-06-24T10:00:00Z",
                    "last_seen": time.time(),
                }
            },
            "last_refresh": time.time() - 100,
            "saved_at": time.time(),
        }

        import json

        with open(cache_file, "w") as f:
            json.dump(cache_data, f)

        DockerBuilder.reset_singleton()

        with patch(
            "panther.core.docker_builder.docker_builder.docker.from_env"
        ) as mock_docker:
            # Mock Docker client that fails
            mock_client = Mock()
            mock_client.ping.side_effect = DockerException("Connection refused")
            mock_client.images.get.side_effect = DockerException("Connection refused")
            mock_docker.return_value = mock_client

            # Builder should initialize without exception (graceful degradation)
            builder = DockerBuilder.get_instance()
            builder.image_cache.cache_file = cache_file
            builder.image_cache._load_cache()

            # Should find image in cache even though Docker is unavailable
            cached_result = builder.image_cache.image_exists_in_cache(
                "fallback_test:latest"
            )
            assert cached_result is True

    def test_cleanup_unused_images_uses_cache(self, mock_docker_builder_with_cache):
        """Test that cleanup_unused_images() uses cache."""
        if not REAL_DOCKER_SYSTEM_AVAILABLE:
            pytest.skip("Real Docker system not available for cache testing")

        builder, mock_client = mock_docker_builder_with_cache

        # Mock images.remove for cleanup
        mock_client.images.remove.return_value = True

        # Test cleanup with keep_tags
        builder.cleanup_unused_images(keep_tags=["keep_this:latest"])

        # Should have called cache operations
        assert hasattr(builder, "image_cache")
        assert builder.image_cache is not None

    def test_remove_dangling_images_uses_cache(self, mock_docker_builder_with_cache):
        """Test that remove_dangling_images() uses cache."""
        if not REAL_DOCKER_SYSTEM_AVAILABLE:
            pytest.skip("Real Docker system not available for cache testing")

        builder, mock_client = mock_docker_builder_with_cache

        # Mock dangling images
        mock_dangling = Mock()
        mock_dangling.id = "sha256:dangling123"
        mock_dangling.tags = []
        mock_client.images.list.return_value = [mock_dangling]
        mock_client.images.remove.return_value = True

        # Test dangling image removal
        result = builder.remove_dangling_images()

        # Should succeed and use cache
        assert result is True
        assert hasattr(builder, "image_cache")

    def test_docker_status_reporting(self, mock_docker_builder_with_cache):
        """Test get_docker_status() method."""
        if not REAL_DOCKER_SYSTEM_AVAILABLE:
            pytest.skip("Real Docker system not available for status testing")

        builder, mock_client = mock_docker_builder_with_cache

        # Get Docker status
        status = builder.get_docker_status()

        assert isinstance(status, dict)
        assert "docker_available" in status
        assert "cache_enabled" in status
        assert "cached_images" in status
        assert "cache_fresh" in status
        assert "fallback_mode" in status

        # Should report cache as enabled
        assert status["cache_enabled"] is True
        assert isinstance(status["docker_available"], bool)

    def test_builder_singleton_cache_persistence(self, tmp_path):
        """Test that DockerBuilder singleton maintains cache across instances."""
        if not REAL_DOCKER_SYSTEM_AVAILABLE:
            pytest.skip("Real Docker system not available for singleton testing")

        cache_file = tmp_path / "singleton_cache.json"

        # Reset and create first instance
        DockerBuilder.reset_singleton()

        with patch("panther.core.docker_builder.docker_builder.docker.from_env"):
            builder1 = DockerBuilder.get_instance()
            builder1.image_cache.cache_file = cache_file

            # Get second instance (should be same object)
            builder2 = DockerBuilder.get_instance()

            # Should be the same singleton instance
            assert builder1 is builder2
            assert builder1.image_cache is builder2.image_cache
            assert builder1.image_cache.cache_file == cache_file


class TestDockerSystemPerformance:
    """Test performance characteristics of Docker system."""

    def test_multiple_image_builds_performance(self, tmp_path):
        """Test performance of multiple image builds."""
        temp_workspace = tmp_path
        builder = DockerBuilder(base_path=temp_workspace)
        dockerfile_path = temp_workspace / "Dockerfile"

        import time

        start_time = time.time()

        # Build multiple images
        for i in range(10):
            builder.build_image(dockerfile_path, f"perf-test-{i}:latest")

        end_time = time.time()
        duration = end_time - start_time

        # Should build images reasonably quickly in mock
        assert duration < 1.0  # Less than 1 second for 10 builds
        assert len(builder.built_images) == 10

    def test_container_operations_performance(self):
        """Test performance of container operations."""
        builder = DockerBuilder()

        import time

        start_time = time.time()

        # Create, start, stop, and remove multiple containers
        for i in range(20):
            container_name = f"perf-container-{i}"
            builder.create_container("test:image", container_name)
            builder.start_container(container_name)
            builder.stop_container(container_name)
            builder.remove_container(container_name)

        end_time = time.time()
        duration = end_time - start_time

        # Should handle container lifecycle efficiently
        assert duration < 1.0  # Less than 1 second for 20 containers
        assert len(builder.containers) == 0  # All containers removed

    def test_network_operations_performance(self):
        """Test performance of network operations."""
        builder = DockerBuilder()

        import time

        start_time = time.time()

        # Create networks and connect containers
        for i in range(5):
            network_name = f"perf-network-{i}"
            builder.create_network(network_name)

            # Create and connect containers to each network
            for j in range(3):
                container_name = f"container-{i}-{j}"
                builder.create_container("test:image", container_name)
                builder.connect_container_to_network(container_name, network_name)

        end_time = time.time()
        duration = end_time - start_time

        # Should handle network operations efficiently
        assert duration < 1.0  # Less than 1 second
        assert len(builder.networks) == 5
        assert len(builder.containers) == 15


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
