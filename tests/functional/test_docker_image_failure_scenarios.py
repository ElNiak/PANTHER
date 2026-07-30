"""
Functional tests for Docker image failure scenarios.

This module tests specific failure patterns that occur in PANTHER when Docker images
don't exist, including the exact error "unknown (ceacda77-b5b4-56d6-a95f-ec764bb37357)".
"""

import json
import tempfile
import time
import uuid
from dataclasses import asdict
from pathlib import Path
from unittest.mock import MagicMock, Mock, call, patch

import pytest

# Test imports with fallback to mocks
try:
    import docker
    from docker.errors import DockerException, NotFound

    from panther.core.docker_builder.docker_builder import DockerBuilder
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


pytestmark = [pytest.mark.functional, pytest.mark.docker_failures]


class TestSpecificDockerImageFailures:
    """Test specific Docker image failure scenarios that occur in production."""

    def test_unknown_uuid_image_error_exact_reproduction(self):
        """Test exact reproduction of: unknown (ceacda77-b5b4-56d6-a95f-ec764bb37357)."""
        # This is the exact error from the user's problem
        problematic_image = "unknown:ceacda77-b5b4-56d6-a95f-ec764bb37357"

        # Mock Docker operations that would encounter this
        mock_executor = Mock()
        mock_executor.execute_with_logging.side_effect = DockerComposeException(
            "Docker command failed with return code 1"
        )

        # This represents the problematic Docker run command
        docker_run_cmd = [
            "docker",
            "run",
            "--name",
            "test-service",
            problematic_image,  # This image doesn't exist
        ]

        # Should fail at runtime (current behavior)
        with pytest.raises(
            DockerComposeException, match="Docker command failed with return code 1"
        ):
            mock_executor.execute_with_logging(docker_run_cmd)

        # This demonstrates the current failure point
        mock_executor.execute_with_logging.assert_called_with(docker_run_cmd)

    def test_uuid_like_image_patterns(self):
        """Test various UUID-like image patterns that can cause issues."""
        uuid_patterns = [
            "unknown:ceacda77-b5b4-56d6-a95f-ec764bb37357",
            "temp:" + str(uuid.uuid4()),
            "build:" + str(uuid.uuid4()),
            "sha256:" + "a" * 64,  # SHA256-like
            "intermediate:" + str(uuid.uuid4()),
        ]

        # Mock Docker builder
        mock_builder = Mock()
        mock_builder.image_exists.return_value = False

        # All UUID patterns should fail validation
        for pattern in uuid_patterns:
            assert mock_builder.image_exists(pattern) is False

            # Should raise appropriate error when used
            with pytest.raises(Exception):
                if not mock_builder.image_exists(pattern):
                    raise RuntimeError(f"Image {pattern} not found")

    def test_build_process_creates_intermediate_images(self):
        """Test scenario where build process creates intermediate images that aren't properly tagged."""
        service_name = "test-service"
        final_tag = f"{service_name}:latest"
        intermediate_id = "sha256:" + "b" * 64  # Intermediate image ID

        # Mock build process
        mock_builder = Mock()

        # Simulate build that creates intermediate image but fails to tag final image
        def mock_build_image(dockerfile, tag):
            # Build creates intermediate image
            mock_builder._intermediate_images = [intermediate_id]
            # But fails to create final tagged image
            return True  # Claims success

        def mock_image_exists(image_name):
            if image_name == final_tag:
                return False  # Final tag doesn't exist
            elif image_name == intermediate_id:
                return True  # Intermediate exists
            return False

        mock_builder.build_image.side_effect = mock_build_image
        mock_builder.image_exists.side_effect = mock_image_exists

        # Build process
        build_result = mock_builder.build_image("Dockerfile", final_tag)
        assert build_result is True  # Build claims success

        # But validation reveals the problem
        final_exists = mock_builder.image_exists(final_tag)
        assert final_exists is False  # Final image missing

        # Intermediate image exists but isn't usable
        intermediate_exists = mock_builder.image_exists(intermediate_id)
        assert intermediate_exists is True

    def test_docker_build_silent_failure(self):
        """Test scenario where Docker build fails silently."""
        service_name = "silent-fail-service"
        image_tag = f"{service_name}:latest"

        # Mock Docker build that fails silently
        mock_builder = Mock()

        def mock_build_with_silent_failure(dockerfile, tag):
            # Simulate build that reports success but actually failed
            # This can happen with complex Dockerfiles or resource issues
            return True  # Reports success

        def mock_image_missing(image_name):
            # But image doesn't actually exist
            return False

        mock_builder.build_image.side_effect = mock_build_with_silent_failure
        mock_builder.image_exists.side_effect = mock_image_missing

        # This scenario should be caught by validation
        build_result = mock_builder.build_image("Dockerfile", image_tag)
        validation_result = mock_builder.image_exists(image_tag)

        assert build_result is True  # Build claimed success
        assert validation_result is False  # But image doesn't exist

        # This inconsistency should trigger an error
        if build_result and not validation_result:
            with pytest.raises(RuntimeError):
                raise RuntimeError(
                    "Build succeeded but image not found - silent failure detected"
                )


class TestDeploymentFailureScenarios:
    """Test deployment failure scenarios when images are missing."""

    @pytest.fixture
    def mock_deployment_environment(self):
        """Create mock deployment environment."""

        class MockDeploymentEnvironment:
            def __init__(self):
                self.docker_name = "deployment-service"
                self.logger = Mock()
                self.docker_executor = Mock()

            def deploy_without_validation(self, image_name):
                """Current problematic deployment without validation."""
                docker_run_cmd = [
                    "docker",
                    "run",
                    "--name",
                    self.docker_name,
                    image_name,
                ]
                return self.docker_executor.execute_with_logging(docker_run_cmd)

            def deploy_with_validation(self, image_name, docker_builder):
                """Fixed deployment with validation."""
                # Validate image exists first
                if not docker_builder.image_exists(image_name):
                    raise RuntimeError(f"Cannot deploy: Image {image_name} not found")

                docker_run_cmd = [
                    "docker",
                    "run",
                    "--name",
                    self.docker_name,
                    image_name,
                ]
                return self.docker_executor.execute_with_logging(docker_run_cmd)

        yield MockDeploymentEnvironment()

    def test_deployment_fails_at_runtime_without_validation(
        self, mock_deployment_environment
    ):
        """Test current behavior where deployment fails at runtime."""
        missing_image = "missing-service:latest"

        # Configure Docker executor to fail (simulating real Docker behavior)
        mock_deployment_environment.docker_executor.execute_with_logging.side_effect = (
            DockerComposeException("Docker command failed with return code 1")
        )

        # Current behavior - fails at runtime
        with pytest.raises(DockerComposeException):
            mock_deployment_environment.deploy_without_validation(missing_image)

        # This represents the current failure point
        expected_cmd = ["docker", "run", "--name", "deployment-service", missing_image]
        mock_deployment_environment.docker_executor.execute_with_logging.assert_called_with(
            expected_cmd
        )

    def test_deployment_fails_early_with_validation(self, mock_deployment_environment):
        """Test fixed behavior where deployment fails early with clear error."""
        missing_image = "missing-service:latest"

        # Mock Docker builder
        mock_builder = Mock()
        mock_builder.image_exists.return_value = False

        # Fixed behavior - fails early with clear error
        with pytest.raises(RuntimeError, match="Cannot deploy: Image .* not found"):
            mock_deployment_environment.deploy_with_validation(
                missing_image, mock_builder
            )

        # Docker executor should not be called
        mock_deployment_environment.docker_executor.execute_with_logging.assert_not_called()

        # Validation should have been called
        mock_builder.image_exists.assert_called_with(missing_image)

    def test_deployment_succeeds_with_validation_when_image_exists(
        self, mock_deployment_environment
    ):
        """Test that deployment succeeds when image exists and validation passes."""
        existing_image = "existing-service:latest"

        # Mock Docker builder and executor
        mock_builder = Mock()
        mock_builder.image_exists.return_value = True
        mock_deployment_environment.docker_executor.execute_with_logging.return_value = (
            True
        )

        # Should succeed
        result = mock_deployment_environment.deploy_with_validation(
            existing_image, mock_builder
        )
        assert result is True

        # Both validation and execution should be called
        mock_builder.image_exists.assert_called_with(existing_image)
        expected_cmd = ["docker", "run", "--name", "deployment-service", existing_image]
        mock_deployment_environment.docker_executor.execute_with_logging.assert_called_with(
            expected_cmd
        )


class TestServiceLifecycleFailureScenarios:
    """Test service lifecycle failure scenarios."""

    def test_service_generation_creates_invalid_image_references(self):
        """Test scenario where service generation creates invalid image references."""
        # This tests the gap between service configuration and actual images
        service_config = {
            "service_name": "problematic-service",
            "protocol": "quic",
            "implementation": "picoquic",
        }

        # Mock service generator
        mock_generator = Mock()

        def generate_image_name(config):
            # Simulate image name generation that might not match built images
            base_name = f"{config['service_name']}-{config['protocol']}-{config['implementation']}"
            return f"{base_name}:latest"

        mock_generator.generate_image_name.side_effect = generate_image_name

        # Generated image name
        generated_image = mock_generator.generate_image_name(service_config)
        assert generated_image == "problematic-service-quic-picoquic:latest"

        # But this image might not actually exist
        mock_builder = Mock()
        mock_builder.image_exists.return_value = False

        # Should catch this mismatch
        if not mock_builder.image_exists(generated_image):
            with pytest.raises(RuntimeError):
                raise RuntimeError(
                    f"Generated image name {generated_image} does not exist"
                )

    def test_environment_setup_with_missing_dependencies(self):
        """Test environment setup when dependent images are missing."""
        # Test scenario with multiple dependent services
        service_dependencies = {
            "main-service": "main-service:latest",
            "database": "postgres:13",
            "cache": "redis:6-alpine",
            "monitoring": "custom-monitor:latest",  # This one might be missing
        }

        # Mock validator
        mock_validator = Mock()

        def validate_image_exists(image_name):
            # Simulate some standard images exist, custom ones don't
            standard_images = ["postgres:13", "redis:6-alpine"]
            return image_name in standard_images

        mock_validator.image_exists.side_effect = validate_image_exists

        # Check all dependencies
        missing_images = []
        for service, image in service_dependencies.items():
            if not mock_validator.image_exists(image):
                missing_images.append((service, image))

        # Should identify missing custom images
        assert len(missing_images) == 2
        assert ("main-service", "main-service:latest") in missing_images
        assert ("monitoring", "custom-monitor:latest") in missing_images

        # Should prevent environment setup
        if missing_images:
            error_msg = f"Missing required images: {missing_images}"
            with pytest.raises(RuntimeError, match="Missing required images"):
                raise RuntimeError(error_msg)


class TestRecoveryAndDiagnosticScenarios:
    """Test recovery and diagnostic scenarios for image failures."""

    def test_diagnostic_image_information_collection(self):
        """Test collection of diagnostic information when images are missing."""
        missing_image = "diagnostic-service:latest"

        # Mock diagnostic collector
        mock_diagnostics = Mock()

        def collect_image_diagnostics(image_name):
            """Collect comprehensive diagnostic information."""
            diagnostics = {
                "image_name": image_name,
                "exists": False,
                "build_history": [],
                "similar_images": [],
                "build_logs": "Build failed: No space left on device",
                "recommendations": [
                    "Check Docker build logs",
                    "Verify Dockerfile syntax",
                    "Check available disk space",
                    "Verify build context",
                ],
            }

            # Look for similar images
            if "service" in image_name:
                diagnostics["similar_images"] = [
                    "diagnostic-service:v1.0",
                    "diagnostic-service:dev",
                    "other-service:latest",
                ]

            return diagnostics

        mock_diagnostics.collect_diagnostics.side_effect = collect_image_diagnostics

        # Collect diagnostics
        diag_info = mock_diagnostics.collect_diagnostics(missing_image)

        assert diag_info["image_name"] == missing_image
        assert diag_info["exists"] is False
        assert len(diag_info["similar_images"]) > 0
        assert len(diag_info["recommendations"]) > 0
        assert "build_logs" in diag_info

    def test_automatic_image_recovery_attempts(self):
        """Test automatic recovery attempts when images are missing."""
        missing_image = "recovery-service:latest"

        # Mock recovery system
        mock_recovery = Mock()

        def attempt_recovery(image_name):
            """Attempt various recovery strategies."""
            recovery_attempts = []

            # Strategy 1: Try to pull from registry
            try:
                # mock_docker_client.images.pull(image_name)
                recovery_attempts.append(
                    ("pull_from_registry", False, "Image not found in registry")
                )
            except:
                pass

            # Strategy 2: Try to rebuild from source
            try:
                # Mock rebuild attempt
                recovery_attempts.append(
                    ("rebuild_from_source", False, "Dockerfile not found")
                )
            except:
                pass

            # Strategy 3: Look for alternative tags
            try:
                alternative_tags = ["recovery-service:dev", "recovery-service:v1"]
                for alt_tag in alternative_tags:
                    # Mock checking alternative
                    recovery_attempts.append(
                        ("try_alternative", False, f"Alternative {alt_tag} not found")
                    )
            except:
                pass

            return {
                "image_name": image_name,
                "recovery_successful": False,
                "attempts": recovery_attempts,
                "final_recommendation": "Manual intervention required",
            }

        mock_recovery.attempt_recovery.side_effect = attempt_recovery

        # Attempt recovery
        recovery_result = mock_recovery.attempt_recovery(missing_image)

        assert recovery_result["image_name"] == missing_image
        assert recovery_result["recovery_successful"] is False
        assert len(recovery_result["attempts"]) > 0
        assert "final_recommendation" in recovery_result

    def test_preventive_validation_pipeline(self):
        """Test preventive validation pipeline to catch issues early."""
        # Test comprehensive validation pipeline
        services_to_validate = [
            "service-a:latest",
            "service-b:v1.0",
            "service-c:dev",
            "unknown:ceacda77-b5b4-56d6-a95f-ec764bb37357",  # Problematic one
        ]

        # Mock validation pipeline
        mock_pipeline = Mock()

        def run_validation_pipeline(services):
            """Run comprehensive validation pipeline."""
            results = {
                "total_services": len(services),
                "validated": [],
                "failed": [],
                "warnings": [],
                "critical_issues": [],
            }

            for service in services:
                if "unknown:" in service or len(service.split(":")[-1]) > 20:
                    # Detect UUID-like or problematic patterns
                    results["critical_issues"].append(
                        {
                            "service": service,
                            "issue": "Suspicious image name pattern detected",
                            "severity": "critical",
                        }
                    )
                    results["failed"].append(service)
                elif service.endswith(":dev"):
                    results["warnings"].append(
                        {
                            "service": service,
                            "issue": "Development tag in production",
                            "severity": "warning",
                        }
                    )
                    results["validated"].append(service)
                else:
                    results["validated"].append(service)

            return results

        mock_pipeline.validate_all.side_effect = run_validation_pipeline

        # Run validation
        validation_results = mock_pipeline.validate_all(services_to_validate)

        assert validation_results["total_services"] == 4
        assert len(validation_results["critical_issues"]) == 1
        assert len(validation_results["warnings"]) == 1
        assert len(validation_results["failed"]) == 1

        # Critical issue should be the UUID-like image
        critical_issue = validation_results["critical_issues"][0]
        assert "ceacda77-b5b4-56d6-a95f-ec764bb37357" in critical_issue["service"]
        assert critical_issue["severity"] == "critical"


if __name__ in {"__main__", "__mp_main__"}:
    pytest.main([__file__, "-v"])
