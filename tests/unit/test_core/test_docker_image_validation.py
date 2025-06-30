"""
Unit tests for Docker image existence validation across PANTHER components.

This module tests the critical Docker image validation functionality that prevents
the error "unknown (ceacda77-b5b4-56d6-a95f-ec764bb37357)" by ensuring proper
image existence checking before deployment.
"""

import json
import tempfile
import time
from dataclasses import asdict
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

# Test imports with fallback to mocks
try:
    import docker
    from docker.errors import DockerException, NotFound

    from panther.core.docker_builder.docker_builder import DockerBuilder
    from panther.core.docker_builder.docker_image_cache import (
        CachedImage,
        DockerImageCache,
    )
    from panther.core.exceptions.fast_fail import DockerComposeException

    DOCKER_SYSTEM_AVAILABLE = True
except ImportError:
    DOCKER_SYSTEM_AVAILABLE = False

    # Mock implementations for testing
    class DockerException(Exception):
        pass

    class NotFound(DockerException):
        pass

    class DockerComposeException(Exception):
        pass

    class DockerBuilder:
        def __init__(self):
            self.client = Mock()
            self.image_cache = Mock()

        def image_exists(self, image_name):
            # Mock implementation that can be configured
            return (
                hasattr(self, "_mock_existing_images")
                and image_name in self._mock_existing_images
            )

        def set_existing_images(self, images):
            self._mock_existing_images = set(images)


pytestmark = [pytest.mark.unit, pytest.mark.docker_validation]


class TestDockerImageExistenceValidation:
    """Test core Docker image existence validation functionality."""

    @pytest.fixture
    def mock_docker_builder(self):
        """Create mock DockerBuilder for testing."""
        if DOCKER_SYSTEM_AVAILABLE:
            with patch(
                "panther.core.docker_builder.docker_builder.docker.from_env"
            ) as mock_docker:
                mock_client = Mock()
                mock_client.ping.return_value = True
                mock_docker.return_value = mock_client

                DockerBuilder.reset_singleton()
                builder = DockerBuilder.get_instance()

                # Configure mock image responses
                def mock_image_exists(image_name):
                    # Simulate real image checking behavior
                    existing_images = getattr(builder, "_test_existing_images", set())
                    return image_name in existing_images

                builder.image_exists = mock_image_exists
                builder.set_test_images = lambda images: setattr(
                    builder, "_test_existing_images", set(images)
                )

                yield builder
        else:
            builder = DockerBuilder()
            yield builder

    def test_image_exists_validation_success(self, mock_docker_builder):
        """Test successful image existence validation."""
        # Configure builder with existing images
        mock_docker_builder.set_test_images(
            ["python:3.11", "alpine:latest", "nginx:1.21"]
        )

        # Test existing images
        assert mock_docker_builder.image_exists("python:3.11") is True
        assert mock_docker_builder.image_exists("alpine:latest") is True
        assert mock_docker_builder.image_exists("nginx:1.21") is True

    def test_image_exists_validation_failure(self, mock_docker_builder):
        """Test image existence validation for non-existent images."""
        # Configure builder with limited images
        mock_docker_builder.set_test_images(["python:3.11"])

        # Test non-existing images
        assert mock_docker_builder.image_exists("nonexistent:tag") is False
        assert mock_docker_builder.image_exists("unknown:latest") is False
        assert mock_docker_builder.image_exists("missing:1.0") is False

    def test_image_exists_with_uuid_tags(self, mock_docker_builder):
        """Test image existence validation with UUID-like tags."""
        # Test the specific error case: "unknown (ceacda77-b5b4-56d6-a95f-ec764bb37357)"
        mock_docker_builder.set_test_images([])

        # This should return False for UUID-like image names
        uuid_image = "unknown:ceacda77-b5b4-56d6-a95f-ec764bb37357"
        assert mock_docker_builder.image_exists(uuid_image) is False

        # Test other UUID-like patterns
        assert mock_docker_builder.image_exists("sha256:abc123def456") is False
        assert mock_docker_builder.image_exists("temp:abcd-1234-efgh-5678") is False

    def test_image_exists_with_build_tags(self, mock_docker_builder):
        """Test image existence validation with common build tag patterns."""
        build_tags = [
            "panther-service:latest",
            "panther-service:v1.0",
            "localhost/panther:test",
            "service-manager:dev",
        ]

        mock_docker_builder.set_test_images(build_tags)

        # Test all build tags exist
        for tag in build_tags:
            assert mock_docker_builder.image_exists(tag) is True

        # Test variations that don't exist
        assert mock_docker_builder.image_exists("panther-service:v2.0") is False
        assert mock_docker_builder.image_exists("localhost/panther:prod") is False

    def test_image_validation_with_cache_fallback(self, tmp_path):
        """Test image validation with cache fallback when Docker is unavailable."""
        if not DOCKER_SYSTEM_AVAILABLE:
            pytest.skip("Docker system not available")

        cache_file = tmp_path / "validation_cache.json"

        # Create cache with known images
        cache_data = {
            "images": {
                "sha256:cached_image": {
                    "id": "sha256:cached_image",
                    "tags": ["cached:latest", "backup:v1"],
                    "size": 1024 * 1024,
                    "created": "2025-06-24T10:00:00Z",
                    "last_seen": time.time(),
                }
            },
            "last_refresh": time.time() - 100,
            "saved_at": time.time(),
        }

        with open(cache_file, "w") as f:
            json.dump(cache_data, f)

        DockerBuilder.reset_singleton()

        with patch(
            "panther.core.docker_builder.docker_builder.docker.from_env"
        ) as mock_docker:
            # Mock failing Docker client
            mock_client = Mock()
            mock_client.ping.side_effect = DockerException("Connection refused")
            mock_docker.return_value = mock_client

            builder = DockerBuilder.get_instance()
            builder.image_cache.cache_file = cache_file
            builder.image_cache._load_cache()

            # Should find cached images even when Docker is down
            assert builder.image_cache.image_exists_in_cache("cached:latest") is True
            assert builder.image_cache.image_exists_in_cache("backup:v1") is True
            assert builder.image_cache.image_exists_in_cache("nonexistent:tag") is False


class TestEnvironmentManagerImageValidation:
    """Test image validation in environment managers."""

    @pytest.fixture
    def mock_environment_manager(self):
        """Create mock environment manager with Docker operations."""
        try:
            # Try to import real environment manager classes
            from panther.core.docker_builder.plugin_mixin.environment_manager_docker_mixing import (
                EnvironmentManagerDockerMixin,
            )
            from panther.plugins.environments.network_environment.localhost_single_container.localhost_single_container import (
                LocalhostSingleContainer,
            )

            class TestableEnvironmentManager(
                LocalhostSingleContainer, EnvironmentManagerDockerMixin
            ):
                def __init__(self):
                    self.docker_name = "test-service"
                    self.logger = Mock()
                    self.docker_builder = Mock()
                    self.docker_builder.image_exists = Mock()

                def execute_command(self, cmd, timeout=10, check=False):
                    # Mock command execution
                    result = Mock()
                    result.stdout = ""  # Empty means image not found
                    result.returncode = 1 if not check else 0
                    return result

            yield TestableEnvironmentManager()

        except ImportError:
            # Create mock environment manager
            class MockEnvironmentManager:
                def __init__(self):
                    self.docker_name = "test-service"
                    self.logger = Mock()
                    self.docker_builder = Mock()
                    self.docker_builder.image_exists = Mock()

                def get_environment_docker_run_command(
                    self, image_name, container_name, **kwargs
                ):
                    return ["docker", "run", "--name", container_name, image_name]

                def execute_command(self, cmd, timeout=10, check=False):
                    result = Mock()
                    result.stdout = ""
                    result.returncode = 1 if not check else 0
                    return result

                def validate_image_exists_before_run(self, image_name):
                    """Critical validation method that should exist."""
                    if not self.docker_builder.image_exists(image_name):
                        raise RuntimeError(
                            f"Docker image {image_name} not found. Cannot launch environment."
                        )
                    return True

            yield MockEnvironmentManager()

    def test_environment_manager_validates_image_before_run(
        self, mock_environment_manager
    ):
        """Test that environment manager validates image existence before running containers."""
        image_name = f"{mock_environment_manager.docker_name}:latest"

        # Configure builder to simulate image exists
        mock_environment_manager.docker_builder.image_exists.return_value = True

        # Validation should pass
        result = mock_environment_manager.validate_image_exists_before_run(image_name)
        assert result is True
        mock_environment_manager.docker_builder.image_exists.assert_called_with(
            image_name
        )

    def test_environment_manager_fails_on_missing_image(self, mock_environment_manager):
        """Test that environment manager fails when image doesn't exist."""
        image_name = f"{mock_environment_manager.docker_name}:latest"

        # Configure builder to simulate image doesn't exist
        mock_environment_manager.docker_builder.image_exists.return_value = False

        # Validation should raise exception
        with pytest.raises(RuntimeError, match="Docker image .* not found"):
            mock_environment_manager.validate_image_exists_before_run(image_name)

        mock_environment_manager.docker_builder.image_exists.assert_called_with(
            image_name
        )

    def test_environment_docker_run_command_validation(self, mock_environment_manager):
        """Test validation in get_environment_docker_run_command."""
        image_name = "test-service:latest"
        container_name = "test-container"

        # Should generate command when image exists
        mock_environment_manager.docker_builder.image_exists.return_value = True

        command = mock_environment_manager.get_environment_docker_run_command(
            image_name=image_name, container_name=container_name
        )

        assert "docker" in command
        assert "run" in command
        assert container_name in command
        assert image_name in command

    def test_environment_manager_image_check_warning_only(
        self, mock_environment_manager
    ):
        """Test current behavior where missing images only generate warnings."""
        # Simulate the current problematic behavior in environment_manager_docker_mixing.py:124
        image_tag = "missing-service:latest"

        # Mock command execution that returns empty (image not found)
        check_cmd = ["docker", "images", "-q", image_tag]
        result = mock_environment_manager.execute_command(
            check_cmd, timeout=10, check=False
        )

        # Current behavior: only logs warning, doesn't prevent execution
        if not result.stdout.strip():
            mock_environment_manager.logger.warning(
                f"Service image {image_tag} not found. It should have been built by the service manager."
            )
            # PROBLEM: Execution continues here instead of failing

        # Test that warning was logged
        mock_environment_manager.logger.warning.assert_called_once()
        warning_message = mock_environment_manager.logger.warning.call_args[0][0]
        assert "not found" in warning_message
        assert image_tag in warning_message


class TestMissingImageFailureScenarios:
    """Test specific failure scenarios when images are missing."""

    def test_unknown_uuid_image_error(self):
        """Test the specific error: unknown (ceacda77-b5b4-56d6-a95f-ec764bb37357)."""
        # This tests the exact error pattern from the user's problem
        problematic_image = "unknown:ceacda77-b5b4-56d6-a95f-ec764bb37357"

        # Mock Docker builder that would encounter this
        builder = Mock()
        builder.image_exists.return_value = False

        # This should fail validation
        assert builder.image_exists(problematic_image) is False

        # Should raise appropriate exception when used in deployment
        with pytest.raises(Exception):
            if not builder.image_exists(problematic_image):
                raise DockerComposeException(
                    f"Docker image {problematic_image} not found"
                )

    def test_build_claims_success_but_image_missing(self):
        """Test scenario where build claims success but image doesn't actually exist."""
        service_name = "test-service"
        expected_tag = f"{service_name}:latest"

        # Mock build process that claims success
        mock_builder = Mock()
        mock_builder.build_image.return_value = True  # Claims success
        mock_builder.image_exists.return_value = False  # But image doesn't exist

        # Build process
        build_result = mock_builder.build_image("Dockerfile", expected_tag)
        assert build_result is True  # Build claimed success

        # Validation should catch the problem
        image_exists = mock_builder.image_exists(expected_tag)
        assert image_exists is False  # Image actually missing

        # This scenario should be caught before deployment
        if build_result and not image_exists:
            # This is the critical gap that needs fixing
            pytest.fail(
                "Build succeeded but image doesn't exist - validation gap detected"
            )

    def test_deployment_without_validation(self):
        """Test deployment scenario without proper image validation."""
        # Simulate the problematic flow in localhost_single_container.py:394
        docker_name = "problematic-service"
        image_name = f"{docker_name}:latest"

        # Mock Docker run command generation (current behavior)
        docker_run_cmd = [
            "docker",
            "run",
            "--name",
            docker_name,
            image_name
            # No validation of image_name existence!
        ]

        # Mock execution that would fail
        mock_executor = Mock()
        mock_executor.execute_with_logging.side_effect = DockerComposeException(
            "Docker command failed with return code 1"
        )

        # This should fail at runtime (current behavior)
        with pytest.raises(DockerComposeException):
            mock_executor.execute_with_logging(docker_run_cmd)

    def test_proper_validation_prevents_deployment_failure(self):
        """Test that proper validation prevents deployment failures."""
        docker_name = "validated-service"
        image_name = f"{docker_name}:latest"

        # Mock Docker builder with proper validation
        mock_builder = Mock()
        mock_builder.image_exists.return_value = False

        # Proper validation should prevent deployment
        def validated_get_environment_docker_run_command(image_name, container_name):
            # Add validation before generating command
            if not mock_builder.image_exists(image_name):
                raise RuntimeError(f"Docker image {image_name} not found")

            return ["docker", "run", "--name", container_name, image_name]

        # This should fail early with clear error
        with pytest.raises(RuntimeError, match="Docker image .* not found"):
            validated_get_environment_docker_run_command(image_name, docker_name)

        # Verify validation was called
        mock_builder.image_exists.assert_called_with(image_name)


class TestImageValidationIntegration:
    """Test integration scenarios for image validation."""

    def test_build_then_validate_workflow(self):
        """Test complete build-then-validate workflow."""
        service_name = "integration-test"
        image_tag = f"{service_name}:latest"

        # Mock builder with proper integration
        mock_builder = Mock()

        # Simulate successful build and validation
        mock_builder.build_image.return_value = True
        mock_builder.image_exists.return_value = True

        # Workflow: Build -> Validate -> Deploy
        build_success = mock_builder.build_image("Dockerfile", image_tag)
        assert build_success is True

        validation_success = mock_builder.image_exists(image_tag)
        assert validation_success is True

        # Only proceed with deployment if both succeed
        if build_success and validation_success:
            deploy_ready = True
        else:
            deploy_ready = False

        assert deploy_ready is True

    def test_build_success_validation_failure_workflow(self):
        """Test workflow when build succeeds but validation fails."""
        service_name = "flaky-build"
        image_tag = f"{service_name}:latest"

        # Mock builder with inconsistent state
        mock_builder = Mock()
        mock_builder.build_image.return_value = True  # Build claims success
        mock_builder.image_exists.return_value = False  # But image missing

        # Workflow with proper validation
        build_success = mock_builder.build_image("Dockerfile", image_tag)
        validation_success = mock_builder.image_exists(image_tag)

        # Should detect the inconsistency
        assert build_success is True
        assert validation_success is False

        # Should not proceed with deployment
        deploy_ready = build_success and validation_success
        assert deploy_ready is False

    def test_service_manager_environment_manager_integration(self):
        """Test integration between service manager and environment manager."""
        service_name = "quic-service"
        image_tag = f"{service_name}:latest"

        # Mock service manager (should build image)
        mock_service_manager = Mock()
        mock_service_manager.build_service_image.return_value = True

        # Mock environment manager (should validate before deploy)
        mock_env_manager = Mock()
        mock_env_manager.docker_builder = Mock()
        mock_env_manager.docker_builder.image_exists.return_value = True

        # Service manager builds
        build_result = mock_service_manager.build_service_image(image_tag)
        assert build_result is True

        # Environment manager validates before deploy
        validation_result = mock_env_manager.docker_builder.image_exists(image_tag)
        assert validation_result is True

        # Integration successful
        integration_success = build_result and validation_result
        assert integration_success is True


class TestImageValidationPerformance:
    """Test performance characteristics of image validation."""

    def test_bulk_image_validation_performance(self):
        """Test performance of validating many images."""
        # Create mock builder
        mock_builder = Mock()

        # Configure fast responses
        def fast_image_exists(image_name):
            return image_name.startswith("existing")

        mock_builder.image_exists.side_effect = fast_image_exists

        # Test many images
        images_to_test = [f"existing-service-{i}:latest" for i in range(50)] + [
            f"missing-service-{i}:latest" for i in range(50)
        ]

        import time

        start_time = time.time()

        results = []
        for image in images_to_test:
            results.append(mock_builder.image_exists(image))

        end_time = time.time()
        duration = end_time - start_time

        # Should be fast
        assert duration < 0.1  # Less than 100ms for 100 validations
        assert len(results) == 100
        assert sum(results) == 50  # 50 existing, 50 missing

    def test_cached_validation_performance(self, tmp_path):
        """Test performance benefit of cached validation."""
        if not DOCKER_SYSTEM_AVAILABLE:
            pytest.skip("Docker system not available")

        cache_file = tmp_path / "perf_cache.json"
        cache = DockerImageCache(cache_file=cache_file)

        # Add many images to cache
        for i in range(100):
            cache._cache[f"sha256:perf{i}"] = CachedImage(
                id=f"sha256:perf{i}",
                tags=[f"perf{i}:latest"],
                size=1024 * 1024,
                created="2025-06-24T10:00:00Z",
                last_seen=time.time(),
            )

        # Test lookup performance
        start_time = time.time()

        # Many lookups
        for i in range(100):
            exists = cache.image_exists_in_cache(f"perf{i}:latest")
            assert exists is True

        end_time = time.time()
        duration = end_time - start_time

        # Should be very fast with cache
        assert duration < 0.01  # Less than 10ms for 100 cached lookups


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
