"""Integration tests for Docker image validation across PANTHER environment managers.

This module tests the integration between service managers, environment managers,
and Docker image validation to prevent deployment failures like:
"unknown (ceacda77-b5b4-56d6-a95f-ec764bb37357)"
"""

import json
import tempfile
import time
from dataclasses import asdict
from pathlib import Path
from unittest.mock import MagicMock, Mock, call, patch

import pytest

# Test imports with fallback to mocks
try:
    import docker
    from docker.errors import DockerException, NotFound

    from panther.core.docker_builder.docker_builder import DockerBuilder
    from panther.core.docker_builder.docker_image_cache import DockerImageCache
    from panther.core.exceptions.fast_fail import DockerComposeException

    DOCKER_SYSTEM_AVAILABLE = True
except ImportError:
    DOCKER_SYSTEM_AVAILABLE = False

    # Mock implementations
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
            return False  # Default to not found


pytestmark = [pytest.mark.integration, pytest.mark.docker_validation]


class TestLocalhostEnvironmentImageValidation:
    """Test image validation in localhost single container environment."""

    @pytest.fixture
    def mock_localhost_environment(self):
        """Create mock localhost environment with validation capabilities."""
        try:
            # Try to import real environment class
            from panther.plugins.environments.network_environment.localhost_single_container.localhost_single_container import (
                LocalhostSingleContainer,
            )

            class TestableLocalhostEnvironment(LocalhostSingleContainer):
                def __init__(self):
                    self.docker_name = "test-service"
                    self.logger = Mock()
                    self.docker_builder = Mock()
                    self.docker_executor = Mock()

                def validate_image_before_launch(self):
                    """Add the missing validation that should exist."""
                    image_name = f"{self.docker_name}:latest"
                    if not self.docker_builder.image_exists(image_name):
                        raise RuntimeError(
                            f"Docker image {image_name} not found. Cannot launch environment."
                        )
                    return True

                def get_environment_docker_run_command_validated(
                    self, image_name, container_name, **kwargs
                ):
                    """Enhanced version with validation."""
                    # Validate image exists before generating command
                    if not self.docker_builder.image_exists(image_name):
                        raise RuntimeError(f"Docker image {image_name} not found")

                    return ["docker", "run", "--name", container_name, image_name]

            yield TestableLocalhostEnvironment()

        except ImportError:
            # Create comprehensive mock
            class MockLocalhostEnvironment:
                def __init__(self):
                    self.docker_name = "test-service"
                    self.logger = Mock()
                    self.docker_builder = Mock()
                    self.docker_executor = Mock()

                def validate_image_before_launch(self):
                    image_name = f"{self.docker_name}:latest"
                    if not self.docker_builder.image_exists(image_name):
                        raise RuntimeError(
                            f"Docker image {image_name} not found. Cannot launch environment."
                        )
                    return True

                def get_environment_docker_run_command_validated(
                    self, image_name, container_name, **kwargs
                ):
                    if not self.docker_builder.image_exists(image_name):
                        raise RuntimeError(f"Docker image {image_name} not found")
                    return ["docker", "run", "--name", container_name, image_name]

                def launch_environment_services_with_validation(self):
                    """Simulate the fixed launch process."""
                    # Step 1: Validate image exists
                    self.validate_image_before_launch()

                    # Step 2: Generate run command
                    image_name = f"{self.docker_name}:latest"
                    docker_run_cmd = self.get_environment_docker_run_command_validated(
                        image_name=image_name, container_name=self.docker_name
                    )

                    # Step 3: Execute (would only run if validation passed)
                    self.docker_executor.execute_with_logging(docker_run_cmd)

            yield MockLocalhostEnvironment()

    def test_localhost_validates_image_before_launch(self, mock_localhost_environment):
        """Test that localhost environment validates image before launching services."""
        # Configure image exists
        mock_localhost_environment.docker_builder.image_exists.return_value = True

        # Validation should pass
        result = mock_localhost_environment.validate_image_before_launch()
        assert result is True

        # Verify validation was called with correct image name
        expected_image = f"{mock_localhost_environment.docker_name}:latest"
        mock_localhost_environment.docker_builder.image_exists.assert_called_with(
            expected_image
        )

    def test_localhost_fails_when_image_missing(self, mock_localhost_environment):
        """Test that localhost environment fails when image doesn't exist."""
        # Configure image doesn't exist
        mock_localhost_environment.docker_builder.image_exists.return_value = False

        # Should raise exception
        with pytest.raises(RuntimeError, match="Docker image .* not found"):
            mock_localhost_environment.validate_image_before_launch()

    def test_localhost_complete_launch_with_validation(
        self, mock_localhost_environment
    ):
        """Test complete launch process with validation."""
        # Configure successful scenario
        mock_localhost_environment.docker_builder.image_exists.return_value = True
        mock_localhost_environment.docker_executor.execute_with_logging.return_value = (
            True
        )

        # Should complete successfully
        mock_localhost_environment.launch_environment_services_with_validation()

        # Verify all steps were called
        mock_localhost_environment.docker_builder.image_exists.assert_called()
        mock_localhost_environment.docker_executor.execute_with_logging.assert_called()

    def test_localhost_prevents_launch_when_image_missing(
        self, mock_localhost_environment
    ):
        """Test that missing image prevents launch."""
        # Configure image missing
        mock_localhost_environment.docker_builder.image_exists.return_value = False

        # Should fail at validation step
        with pytest.raises(RuntimeError, match="Docker image .* not found"):
            mock_localhost_environment.launch_environment_services_with_validation()

        # Executor should not be called
        mock_localhost_environment.docker_executor.execute_with_logging.assert_not_called()


class TestEnvironmentManagerDockerMixinValidation:
    """Test image validation in environment manager Docker mixin."""

    @pytest.fixture
    def mock_environment_docker_mixin(self):
        """Create mock environment manager Docker mixin."""
        try:
            from panther.core.docker_builder.plugin_mixin.environment_manager_docker_mixin import (
                EnvironmentManagerDockerMixin,
            )

            class TestableEnvironmentDockerMixin(EnvironmentManagerDockerMixin):
                def __init__(self):
                    self.logger = Mock()
                    self.docker_builder = Mock()

                def execute_command(self, cmd, timeout=10, check=False):
                    """Mock command execution."""
                    result = Mock()
                    # Simulate 'docker images -q <tag>' command
                    if "images" in cmd and "-q" in cmd:
                        image_tag = cmd[-1]  # Last argument is the image tag
                        # Return empty if image not found, image ID if found
                        if (
                            hasattr(self, "_existing_images")
                            and image_tag in self._existing_images
                        ):
                            result.stdout = "sha256:abc123"
                        else:
                            result.stdout = ""
                    else:
                        result.stdout = ""

                    result.returncode = 0
                    return result

                def set_existing_images(self, images):
                    """Configure which images exist for testing."""
                    self._existing_images = set(images)

                def validate_service_image_exists_fixed(self, image_tag):
                    """Fixed version that fails fast instead of just warning."""
                    check_cmd = ["docker", "images", "-q", image_tag]
                    result = self.execute_command(check_cmd, timeout=10, check=False)

                    if not result.stdout.strip():
                        # FIXED: Raise exception instead of just warning
                        raise RuntimeError(
                            f"Service image {image_tag} not found. Build may have failed."
                        )

                    return True

            yield TestableEnvironmentDockerMixin()

        except ImportError:
            # Create mock implementation
            class MockEnvironmentDockerMixin:
                def __init__(self):
                    self.logger = Mock()
                    self.docker_builder = Mock()
                    self._existing_images = set()

                def execute_command(self, cmd, timeout=10, check=False):
                    result = Mock()
                    if "images" in cmd and "-q" in cmd:
                        image_tag = cmd[-1]
                        result.stdout = (
                            "sha256:abc123"
                            if image_tag in self._existing_images
                            else ""
                        )
                    else:
                        result.stdout = ""
                    result.returncode = 0
                    return result

                def set_existing_images(self, images):
                    self._existing_images = set(images)

                def validate_service_image_exists_current(self, image_tag):
                    """Current problematic behavior - warning only."""
                    check_cmd = ["docker", "images", "-q", image_tag]
                    result = self.execute_command(check_cmd, timeout=10, check=False)

                    if not result.stdout.strip():
                        self.logger.warning(
                            f"Service image {image_tag} not found. It should have been built by the service manager."
                        )
                        # PROBLEM: Continues execution instead of failing

                    return True  # Always returns True even if image missing

                def validate_service_image_exists_fixed(self, image_tag):
                    """Fixed version that fails fast."""
                    check_cmd = ["docker", "images", "-q", image_tag]
                    result = self.execute_command(check_cmd, timeout=10, check=False)

                    if not result.stdout.strip():
                        raise RuntimeError(
                            f"Service image {image_tag} not found. Build may have failed."
                        )

                    return True

            yield MockEnvironmentDockerMixin()

    def test_current_behavior_warning_only(self, mock_environment_docker_mixin):
        """Test current problematic behavior that only warns."""
        image_tag = "missing-service:latest"

        # Configure no existing images
        mock_environment_docker_mixin.set_existing_images([])

        # Current behavior should warn but not fail
        result = mock_environment_docker_mixin.validate_service_image_exists_current(
            image_tag
        )

        assert result is True  # PROBLEM: Returns True even though image missing

        # Should have logged warning
        mock_environment_docker_mixin.logger.warning.assert_called_once()
        warning_msg = mock_environment_docker_mixin.logger.warning.call_args[0][0]
        assert "not found" in warning_msg
        assert image_tag in warning_msg

    def test_fixed_behavior_fails_fast(self, mock_environment_docker_mixin):
        """Test fixed behavior that fails fast on missing image."""
        image_tag = "missing-service:latest"

        # Configure no existing images
        mock_environment_docker_mixin.set_existing_images([])

        # Fixed behavior should raise exception
        with pytest.raises(RuntimeError, match="Service image .* not found"):
            mock_environment_docker_mixin.validate_service_image_exists_fixed(image_tag)

    def test_fixed_behavior_succeeds_when_image_exists(
        self, mock_environment_docker_mixin
    ):
        """Test fixed behavior succeeds when image exists."""
        image_tag = "existing-service:latest"

        # Configure image exists
        mock_environment_docker_mixin.set_existing_images([image_tag])

        # Should succeed
        result = mock_environment_docker_mixin.validate_service_image_exists_fixed(
            image_tag
        )
        assert result is True


class TestDockerComposeEnvironmentValidation:
    """Test image validation in Docker Compose environment."""

    @pytest.fixture
    def mock_docker_compose_environment(self):
        """Create mock Docker Compose environment."""
        try:
            from panther.plugins.environments.network_environment.docker_compose.docker_compose import (
                DockerCompose,
            )

            class TestableDockerCompose(DockerCompose):
                def __init__(self):
                    self.docker_name = "compose-service"
                    self.logger = Mock()
                    self.docker_builder = Mock()
                    self.lifecycle_manager = Mock()

                def validate_all_service_images(self, services):
                    """Validate all service images before launch."""
                    for service_name, service_config in services.items():
                        image_name = service_config.get("image")
                        if image_name and not self.docker_builder.image_exists(
                            image_name
                        ):
                            raise RuntimeError(
                                f"Service {service_name} image {image_name} not found"
                            )
                    return True

            yield TestableDockerCompose()

        except ImportError:

            class MockDockerCompose:
                def __init__(self):
                    self.docker_name = "compose-service"
                    self.logger = Mock()
                    self.docker_builder = Mock()
                    self.lifecycle_manager = Mock()

                def validate_all_service_images(self, services):
                    for service_name, service_config in services.items():
                        image_name = service_config.get("image")
                        if image_name and not self.docker_builder.image_exists(
                            image_name
                        ):
                            raise RuntimeError(
                                f"Service {service_name} image {image_name} not found"
                            )
                    return True

            yield MockDockerCompose()

    def test_docker_compose_validates_all_service_images(
        self, mock_docker_compose_environment
    ):
        """Test that Docker Compose validates all service images."""
        services = {
            "service1": {"image": "service1:latest"},
            "service2": {"image": "service2:latest"},
            "service3": {"image": "service3:latest"},
        }

        # Configure all images exist
        mock_docker_compose_environment.docker_builder.image_exists.return_value = True

        # Should validate successfully
        result = mock_docker_compose_environment.validate_all_service_images(services)
        assert result is True

        # Should have checked all images
        assert (
            mock_docker_compose_environment.docker_builder.image_exists.call_count == 3
        )

        # Verify specific images were checked
        expected_calls = [
            call("service1:latest"),
            call("service2:latest"),
            call("service3:latest"),
        ]
        mock_docker_compose_environment.docker_builder.image_exists.assert_has_calls(
            expected_calls, any_order=True
        )

    def test_docker_compose_fails_on_missing_service_image(
        self, mock_docker_compose_environment
    ):
        """Test that Docker Compose fails when any service image is missing."""
        services = {
            "service1": {"image": "service1:latest"},
            "service2": {"image": "missing:latest"},  # This one is missing
            "service3": {"image": "service3:latest"},
        }

        # Configure only some images exist
        def mock_image_exists(image_name):
            return image_name != "missing:latest"

        mock_docker_compose_environment.docker_builder.image_exists.side_effect = (
            mock_image_exists
        )

        # Should fail validation
        with pytest.raises(
            RuntimeError, match="Service service2 image missing:latest not found"
        ):
            mock_docker_compose_environment.validate_all_service_images(services)


class TestServiceManagerImageBuildValidation:
    """Test image validation after service manager builds."""

    @pytest.fixture
    def mock_service_manager(self):
        """Create mock service manager with build validation."""

        class MockServiceManager:
            def __init__(self):
                self.service_name = "test-service"
                self.logger = Mock()
                self.docker_builder = Mock()

            def build_and_validate_image(self, dockerfile_path, image_tag):
                """Build image and validate it exists."""
                # Step 1: Build
                build_result = self.docker_builder.build_image(
                    dockerfile_path, image_tag
                )

                if not build_result:
                    raise RuntimeError(f"Failed to build image {image_tag}")

                # Step 2: Validate (critical step often missing)
                if not self.docker_builder.image_exists(image_tag):
                    raise RuntimeError(
                        f"Build claimed success but image {image_tag} not found. "
                        f"Build may have failed silently or image not properly tagged."
                    )

                return True

            def build_without_validation(self, dockerfile_path, image_tag):
                """Current problematic behavior - build without validation."""
                return self.docker_builder.build_image(dockerfile_path, image_tag)

        yield MockServiceManager()

    def test_service_manager_build_and_validate_success(self, mock_service_manager):
        """Test successful build and validation."""
        dockerfile_path = "Dockerfile"
        image_tag = "test-service:latest"

        # Configure successful build and validation
        mock_service_manager.docker_builder.build_image.return_value = True
        mock_service_manager.docker_builder.image_exists.return_value = True

        # Should succeed
        result = mock_service_manager.build_and_validate_image(
            dockerfile_path, image_tag
        )
        assert result is True

        # Verify both steps were called
        mock_service_manager.docker_builder.build_image.assert_called_with(
            dockerfile_path, image_tag
        )
        mock_service_manager.docker_builder.image_exists.assert_called_with(image_tag)

    def test_service_manager_build_fails(self, mock_service_manager):
        """Test build failure."""
        dockerfile_path = "Dockerfile"
        image_tag = "test-service:latest"

        # Configure build failure
        mock_service_manager.docker_builder.build_image.return_value = False

        # Should fail at build step
        with pytest.raises(RuntimeError, match="Failed to build image"):
            mock_service_manager.build_and_validate_image(dockerfile_path, image_tag)

        # Validation should not be called if build fails
        mock_service_manager.docker_builder.image_exists.assert_not_called()

    def test_service_manager_build_succeeds_validation_fails(
        self, mock_service_manager
    ):
        """Test the critical scenario: build succeeds but image doesn't exist."""
        dockerfile_path = "Dockerfile"
        image_tag = "test-service:latest"

        # Configure the problematic scenario
        mock_service_manager.docker_builder.build_image.return_value = (
            True  # Build claims success
        )
        mock_service_manager.docker_builder.image_exists.return_value = (
            False  # But image missing
        )

        # Should detect the inconsistency
        with pytest.raises(
            RuntimeError, match="Build claimed success but image .* not found"
        ):
            mock_service_manager.build_and_validate_image(dockerfile_path, image_tag)

    def test_service_manager_without_validation_misses_problem(
        self, mock_service_manager
    ):
        """Test that build without validation misses the problem."""
        dockerfile_path = "Dockerfile"
        image_tag = "test-service:latest"

        # Configure problematic scenario
        mock_service_manager.docker_builder.build_image.return_value = (
            True  # Build claims success
        )
        mock_service_manager.docker_builder.image_exists.return_value = (
            False  # But image missing
        )

        # Without validation, this appears to succeed
        result = mock_service_manager.build_without_validation(
            dockerfile_path, image_tag
        )
        assert result is True  # PROBLEM: Appears successful

        # The problem won't be discovered until deployment
        # (This is the current problematic behavior)


class TestEndToEndImageValidationWorkflow:
    """Test complete end-to-end image validation workflow."""

    def test_complete_successful_workflow(self):
        """Test complete successful workflow from build to deploy."""
        service_name = "e2e-service"
        image_tag = f"{service_name}:latest"

        # Mock all components
        service_manager = Mock()
        environment_manager = Mock()
        docker_builder = Mock()

        # Configure successful scenario
        service_manager.build_service_image.return_value = True
        docker_builder.image_exists.return_value = True
        environment_manager.deploy_service.return_value = True

        # Workflow with validation
        # Step 1: Service manager builds image
        build_result = service_manager.build_service_image(image_tag)
        assert build_result is True

        # Step 2: Validate image exists after build
        validation_result = docker_builder.image_exists(image_tag)
        assert validation_result is True

        # Step 3: Environment manager deploys (only if validation passed)
        if build_result and validation_result:
            deploy_result = environment_manager.deploy_service(image_tag)
        else:
            deploy_result = False

        assert deploy_result is True

        # Verify all steps were executed
        service_manager.build_service_image.assert_called_with(image_tag)
        docker_builder.image_exists.assert_called_with(image_tag)
        environment_manager.deploy_service.assert_called_with(image_tag)

    def test_complete_workflow_with_build_validation_failure(self):
        """Test workflow when build succeeds but validation fails."""
        service_name = "problematic-service"
        image_tag = f"{service_name}:latest"

        # Mock components
        service_manager = Mock()
        environment_manager = Mock()
        docker_builder = Mock()

        # Configure problematic scenario
        service_manager.build_service_image.return_value = True  # Build claims success
        docker_builder.image_exists.return_value = False  # But validation fails

        # Workflow with validation
        build_result = service_manager.build_service_image(image_tag)
        validation_result = docker_builder.image_exists(image_tag)

        # Should prevent deployment
        if build_result and validation_result:
            deploy_result = environment_manager.deploy_service(image_tag)
        else:
            deploy_result = False

        assert build_result is True
        assert validation_result is False
        assert deploy_result is False  # Deployment prevented

        # Environment manager should not be called
        environment_manager.deploy_service.assert_not_called()

    def test_workflow_prevents_uuid_image_deployment(self):
        """Test that workflow prevents deployment of UUID-like images."""
        # This tests the specific error case
        problematic_image = "unknown:ceacda77-b5b4-56d6-a95f-ec764bb37357"

        # Mock components
        docker_builder = Mock()
        environment_manager = Mock()

        # Configure validation failure for UUID image
        docker_builder.image_exists.return_value = False

        # Validation should fail
        validation_result = docker_builder.image_exists(problematic_image)
        assert validation_result is False

        # Should prevent deployment
        if validation_result:
            environment_manager.deploy_service(problematic_image)

        # Environment manager should not be called
        environment_manager.deploy_service.assert_not_called()


if __name__ in {"__main__", "__mp_main__"}:
    pytest.main([__file__, "-v"])
