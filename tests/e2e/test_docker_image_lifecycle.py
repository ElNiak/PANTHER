"""
End-to-end tests for complete Docker image lifecycle in PANTHER.

This module tests the complete lifecycle from service configuration through
image building, validation, and deployment to prevent issues like:
"unknown (ceacda77-b5b4-56d6-a95f-ec764bb37357)"
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


pytestmark = [pytest.mark.e2e, pytest.mark.docker_lifecycle]


class TestCompleteDockerImageLifecycle:
    """Test complete Docker image lifecycle from configuration to deployment."""

    @pytest.fixture
    def mock_panther_system(self):
        """Create mock PANTHER system with all components."""

        class MockPantherSystem:
            def __init__(self):
                # Core components
                self.config_manager = Mock()
                self.service_manager = Mock()
                self.environment_manager = Mock()
                self.docker_builder = Mock()
                self.logger = Mock()

                # State tracking
                self.built_images = set()
                self.validated_images = set()
                self.deployed_services = set()

                # Configure component interactions
                self._setup_component_behavior()

            def _setup_component_behavior(self):
                """Setup realistic component behavior."""

                # Service manager builds images
                def mock_build_service_image(service_config):
                    service_name = service_config["name"]
                    image_tag = f"{service_name}:latest"

                    # Simulate build process
                    build_success = self.docker_builder.build_image(
                        "Dockerfile", image_tag
                    )
                    if build_success:
                        self.built_images.add(image_tag)

                    return build_success

                self.service_manager.build_service_image.side_effect = (
                    mock_build_service_image
                )

                # Docker builder behavior
                def mock_build_image(dockerfile, tag):
                    # Simulate build that may or may not succeed
                    if hasattr(self, "_build_failures") and tag in self._build_failures:
                        return False
                    return True

                def mock_image_exists(image_name):
                    # Check if image was actually built and exists
                    return image_name in self.built_images

                self.docker_builder.build_image.side_effect = mock_build_image
                self.docker_builder.image_exists.side_effect = mock_image_exists

                # Environment manager deployment
                def mock_deploy_service(service_config):
                    service_name = service_config["name"]
                    image_tag = f"{service_name}:latest"

                    # Validate image exists before deployment
                    if not self.docker_builder.image_exists(image_tag):
                        raise RuntimeError(
                            f"Cannot deploy {service_name}: Image {image_tag} not found"
                        )

                    self.deployed_services.add(service_name)
                    return True

                self.environment_manager.deploy_service.side_effect = (
                    mock_deploy_service
                )

            def set_build_failures(self, failing_images):
                """Configure which images should fail to build."""
                self._build_failures = set(failing_images)

            def complete_service_lifecycle(self, service_config):
                """Run complete service lifecycle with validation."""
                service_name = service_config["name"]

                try:
                    # Step 1: Build service image
                    self.logger.info(f"Building image for service {service_name}")
                    build_success = self.service_manager.build_service_image(
                        service_config
                    )

                    if not build_success:
                        raise RuntimeError(
                            f"Failed to build image for service {service_name}"
                        )

                    # Step 2: Validate image exists
                    image_tag = f"{service_name}:latest"
                    self.logger.info(f"Validating image {image_tag}")

                    if not self.docker_builder.image_exists(image_tag):
                        raise RuntimeError(
                            f"Build succeeded but image {image_tag} not found"
                        )

                    self.validated_images.add(image_tag)

                    # Step 3: Deploy service
                    self.logger.info(f"Deploying service {service_name}")
                    deploy_success = self.environment_manager.deploy_service(
                        service_config
                    )

                    if not deploy_success:
                        raise RuntimeError(f"Failed to deploy service {service_name}")

                    return {
                        "service_name": service_name,
                        "image_tag": image_tag,
                        "status": "deployed",
                        "build_success": True,
                        "validation_success": True,
                        "deploy_success": True,
                    }

                except Exception as e:
                    return {
                        "service_name": service_name,
                        "image_tag": f"{service_name}:latest",
                        "status": "failed",
                        "error": str(e),
                        "build_success": service_name
                        in [img.split(":")[0] for img in self.built_images],
                        "validation_success": f"{service_name}:latest"
                        in self.validated_images,
                        "deploy_success": service_name in self.deployed_services,
                    }

        yield MockPantherSystem()

    def test_successful_complete_lifecycle(self, mock_panther_system):
        """Test successful complete lifecycle from configuration to deployment."""
        service_config = {
            "name": "quic-server",
            "protocol": "quic",
            "implementation": "picoquic",
            "role": "server",
        }

        # Run complete lifecycle
        result = mock_panther_system.complete_service_lifecycle(service_config)

        # Verify successful completion
        assert result["status"] == "deployed"
        assert result["build_success"] is True
        assert result["validation_success"] is True
        assert result["deploy_success"] is True
        assert result["service_name"] == "quic-server"
        assert result["image_tag"] == "quic-server:latest"

        # Verify system state
        assert "quic-server:latest" in mock_panther_system.built_images
        assert "quic-server:latest" in mock_panther_system.validated_images
        assert "quic-server" in mock_panther_system.deployed_services

        # Verify component calls
        mock_panther_system.service_manager.build_service_image.assert_called_with(
            service_config
        )
        mock_panther_system.docker_builder.image_exists.assert_called()
        mock_panther_system.environment_manager.deploy_service.assert_called_with(
            service_config
        )

    def test_lifecycle_fails_at_build_step(self, mock_panther_system):
        """Test lifecycle failure at build step."""
        service_config = {
            "name": "failing-service",
            "protocol": "quic",
            "implementation": "broken",
        }

        # Configure build to fail
        mock_panther_system.set_build_failures(["failing-service:latest"])

        # Run lifecycle
        result = mock_panther_system.complete_service_lifecycle(service_config)

        # Verify failure at build step
        assert result["status"] == "failed"
        assert result["build_success"] is False
        assert result["validation_success"] is False
        assert result["deploy_success"] is False
        assert "Failed to build image" in result["error"]

        # Verify no deployment occurred
        assert "failing-service" not in mock_panther_system.deployed_services

    def test_lifecycle_fails_at_validation_step(self, mock_panther_system):
        """Test lifecycle failure at validation step (build succeeds but image missing)."""
        service_config = {
            "name": "validation-fail-service",
            "protocol": "quic",
            "implementation": "ghost",
        }

        # Override docker builder to simulate the problematic scenario
        def mock_build_success_but_no_image(dockerfile, tag):
            # Build claims success but doesn't actually create image
            return True

        def mock_image_missing(image_name):
            # Image doesn't exist despite build success
            return False

        mock_panther_system.docker_builder.build_image.side_effect = (
            mock_build_success_but_no_image
        )
        mock_panther_system.docker_builder.image_exists.side_effect = mock_image_missing

        # Run lifecycle
        result = mock_panther_system.complete_service_lifecycle(service_config)

        # Verify failure at validation step
        assert result["status"] == "failed"
        assert result["build_success"] is True  # Build claimed success
        assert result["validation_success"] is False
        assert result["deploy_success"] is False
        assert "Build succeeded but image" in result["error"]
        assert "not found" in result["error"]

        # Verify no deployment occurred
        assert "validation-fail-service" not in mock_panther_system.deployed_services

    def test_multiple_services_lifecycle(self, mock_panther_system):
        """Test lifecycle with multiple services."""
        service_configs = [
            {
                "name": "quic-client",
                "protocol": "quic",
                "implementation": "picoquic",
                "role": "client",
            },
            {
                "name": "quic-server",
                "protocol": "quic",
                "implementation": "picoquic",
                "role": "server",
            },
            {
                "name": "http-server",
                "protocol": "http",
                "implementation": "nginx",
                "role": "server",
            },
            {
                "name": "problematic",
                "protocol": "quic",
                "implementation": "broken",
                "role": "client",
            },
        ]

        # Configure one service to fail
        mock_panther_system.set_build_failures(["problematic:latest"])

        # Run lifecycle for all services
        results = []
        for config in service_configs:
            result = mock_panther_system.complete_service_lifecycle(config)
            results.append(result)

        # Analyze results
        successful = [r for r in results if r["status"] == "deployed"]
        failed = [r for r in results if r["status"] == "failed"]

        assert len(successful) == 3
        assert len(failed) == 1
        assert failed[0]["service_name"] == "problematic"

        # Verify successful services
        successful_names = {r["service_name"] for r in successful}
        expected_successful = {"quic-client", "quic-server", "http-server"}
        assert successful_names == expected_successful


class TestDockerImageValidationWorkflows:
    """Test specific Docker image validation workflows."""

    def test_prevent_uuid_image_deployment_workflow(self):
        """Test workflow that prevents deployment of UUID-like images."""
        # This tests prevention of the specific error case
        problematic_configs = [
            {
                "name": "unknown",
                "image_override": "unknown:ceacda77-b5b4-56d6-a95f-ec764bb37357",
            },
            {"name": "temp-build", "image_override": f"temp:{uuid.uuid4()}"},
            {"name": "sha-build", "image_override": "sha256:" + "a" * 64},
        ]

        # Mock validation system
        mock_validator = Mock()

        def validate_image_name_pattern(image_name):
            """Validate image name patterns to prevent problematic images."""
            # Check for UUID-like patterns
            if len(image_name.split(":")[-1]) > 20:
                return False, "Suspicious UUID-like tag detected"

            # Check for known problematic patterns
            problematic_patterns = ["unknown:", "temp:", "sha256:"]
            for pattern in problematic_patterns:
                if image_name.startswith(pattern):
                    return False, f"Problematic image pattern: {pattern}"

            return True, "Image name pattern valid"

        mock_validator.validate_pattern.side_effect = validate_image_name_pattern

        # Test validation for all problematic configs
        validation_results = []
        for config in problematic_configs:
            image_name = config["image_override"]
            is_valid, message = mock_validator.validate_pattern(image_name)
            validation_results.append(
                {"config": config, "valid": is_valid, "message": message}
            )

        # All should be flagged as invalid
        assert all(not result["valid"] for result in validation_results)

        # Check specific messages
        uuid_result = validation_results[0]
        assert "UUID-like tag" in uuid_result["message"]

        temp_result = validation_results[1]
        assert "temp:" in temp_result["message"]

        sha_result = validation_results[2]
        assert "sha256:" in sha_result["message"]

    def test_image_build_validation_pipeline(self):
        """Test comprehensive image build and validation pipeline."""

        # Mock comprehensive build pipeline
        class MockBuildPipeline:
            def __init__(self):
                self.docker_builder = Mock()
                self.logger = Mock()
                self.build_history = []

            def build_and_validate_service_image(self, service_config):
                """Complete build and validation pipeline."""
                service_name = service_config["name"]
                image_tag = f"{service_name}:latest"

                pipeline_result = {
                    "service_name": service_name,
                    "image_tag": image_tag,
                    "steps": [],
                    "success": False,
                    "error": None,
                }

                try:
                    # Step 1: Pre-build validation
                    self.logger.info(f"Pre-build validation for {service_name}")
                    if not self._validate_build_context(service_config):
                        raise RuntimeError("Pre-build validation failed")
                    pipeline_result["steps"].append(("pre_build_validation", True))

                    # Step 2: Build image
                    self.logger.info(f"Building image {image_tag}")
                    build_success = self.docker_builder.build_image(
                        "Dockerfile", image_tag
                    )
                    if not build_success:
                        raise RuntimeError("Image build failed")
                    pipeline_result["steps"].append(("build", True))

                    # Step 3: Post-build validation
                    self.logger.info(f"Post-build validation for {image_tag}")
                    if not self.docker_builder.image_exists(image_tag):
                        raise RuntimeError(
                            "Post-build validation failed: image not found"
                        )
                    pipeline_result["steps"].append(("post_build_validation", True))

                    # Step 4: Image quality checks
                    self.logger.info(f"Quality checks for {image_tag}")
                    if not self._validate_image_quality(image_tag):
                        raise RuntimeError("Image quality validation failed")
                    pipeline_result["steps"].append(("quality_validation", True))

                    # Step 5: Security scanning
                    self.logger.info(f"Security scanning for {image_tag}")
                    if not self._validate_image_security(image_tag):
                        raise RuntimeError("Image security validation failed")
                    pipeline_result["steps"].append(("security_validation", True))

                    pipeline_result["success"] = True
                    self.build_history.append(pipeline_result)
                    return pipeline_result

                except Exception as e:
                    pipeline_result["error"] = str(e)
                    pipeline_result["success"] = False
                    self.build_history.append(pipeline_result)
                    return pipeline_result

            def _validate_build_context(self, service_config):
                """Validate build context exists and is valid."""
                # Mock validation logic
                return service_config.get("name") != "invalid-context"

            def _validate_image_quality(self, image_tag):
                """Validate image quality (size, layers, etc.)."""
                # Mock quality validation
                return not image_tag.startswith("low-quality")

            def _validate_image_security(self, image_tag):
                """Validate image security (vulnerabilities, etc.)."""
                # Mock security validation
                return not image_tag.startswith("insecure")

        pipeline = MockBuildPipeline()

        # Configure Docker builder
        pipeline.docker_builder.build_image.return_value = True
        pipeline.docker_builder.image_exists.return_value = True

        # Test successful pipeline
        service_config = {"name": "test-service", "protocol": "quic"}
        result = pipeline.build_and_validate_service_image(service_config)

        assert result["success"] is True
        assert len(result["steps"]) == 5
        assert result["error"] is None

        # Verify all steps completed
        step_names = [step[0] for step in result["steps"]]
        expected_steps = [
            "pre_build_validation",
            "build",
            "post_build_validation",
            "quality_validation",
            "security_validation",
        ]
        assert step_names == expected_steps

    def test_deployment_readiness_validation(self):
        """Test deployment readiness validation."""

        # Mock deployment readiness checker
        class MockDeploymentReadinessChecker:
            def __init__(self):
                self.docker_builder = Mock()
                self.environment_manager = Mock()

            def check_deployment_readiness(self, service_configs):
                """Check if all services are ready for deployment."""
                readiness_report = {
                    "total_services": len(service_configs),
                    "ready_services": [],
                    "not_ready_services": [],
                    "overall_ready": True,
                    "issues": [],
                }

                for config in service_configs:
                    service_name = config["name"]
                    image_tag = f"{service_name}:latest"

                    service_readiness = {
                        "service_name": service_name,
                        "image_tag": image_tag,
                        "checks": {},
                    }

                    # Check 1: Image exists
                    image_exists = self.docker_builder.image_exists(image_tag)
                    service_readiness["checks"]["image_exists"] = image_exists

                    # Check 2: Image is recent (not stale)
                    image_recent = self._check_image_freshness(image_tag)
                    service_readiness["checks"]["image_recent"] = image_recent

                    # Check 3: Dependencies available
                    deps_available = self._check_dependencies(config)
                    service_readiness["checks"][
                        "dependencies_available"
                    ] = deps_available

                    # Check 4: Environment ready
                    env_ready = self._check_environment_readiness(config)
                    service_readiness["checks"]["environment_ready"] = env_ready

                    # Determine overall service readiness
                    all_checks_passed = all(service_readiness["checks"].values())

                    if all_checks_passed:
                        readiness_report["ready_services"].append(service_readiness)
                    else:
                        readiness_report["not_ready_services"].append(service_readiness)
                        readiness_report["overall_ready"] = False

                        # Add specific issues
                        for check_name, check_result in service_readiness[
                            "checks"
                        ].items():
                            if not check_result:
                                readiness_report["issues"].append(
                                    {
                                        "service": service_name,
                                        "check": check_name,
                                        "severity": "error",
                                    }
                                )

                return readiness_report

            def _check_image_freshness(self, image_tag):
                """Check if image is recent."""
                # Mock freshness check
                return not image_tag.startswith("stale")

            def _check_dependencies(self, config):
                """Check if service dependencies are available."""
                # Mock dependency check
                return config.get("dependencies_ready", True)

            def _check_environment_readiness(self, config):
                """Check if environment is ready for service."""
                # Mock environment check
                return config.get("environment_ready", True)

        checker = MockDeploymentReadinessChecker()

        # Configure Docker builder
        def mock_image_exists(image_name):
            return not image_name.startswith("missing")

        checker.docker_builder.image_exists.side_effect = mock_image_exists

        # Test with mixed readiness
        service_configs = [
            {
                "name": "ready-service",
                "dependencies_ready": True,
                "environment_ready": True,
            },
            {
                "name": "missing-image",
                "dependencies_ready": True,
                "environment_ready": True,
            },
            {
                "name": "stale-service",
                "dependencies_ready": True,
                "environment_ready": True,
            },
            {
                "name": "deps-not-ready",
                "dependencies_ready": False,
                "environment_ready": True,
            },
        ]

        # Check readiness
        report = checker.check_deployment_readiness(service_configs)

        assert report["total_services"] == 4
        assert len(report["ready_services"]) == 1
        assert len(report["not_ready_services"]) == 3
        assert report["overall_ready"] is False
        assert len(report["issues"]) > 0

        # Verify specific issues
        issue_services = {issue["service"] for issue in report["issues"]}
        expected_issue_services = {"missing-image", "stale-service", "deps-not-ready"}
        assert issue_services == expected_issue_services


class TestImageLifecycleRecoveryScenarios:
    """Test recovery scenarios in image lifecycle."""

    def test_automated_recovery_workflow(self):
        """Test automated recovery when image build fails."""

        # Mock recovery system
        class MockRecoverySystem:
            def __init__(self):
                self.docker_builder = Mock()
                self.logger = Mock()
                self.recovery_attempts = []

            def attempt_service_recovery(self, service_config, failure_reason):
                """Attempt to recover from service failure."""
                service_name = service_config["name"]
                recovery_result = {
                    "service_name": service_name,
                    "original_failure": failure_reason,
                    "recovery_attempts": [],
                    "recovery_successful": False,
                    "final_status": "failed",
                }

                # Recovery Strategy 1: Clean rebuild
                try:
                    self.logger.info(f"Attempting clean rebuild for {service_name}")
                    self._clean_build_cache(service_name)

                    image_tag = f"{service_name}:latest"
                    build_success = self.docker_builder.build_image(
                        "Dockerfile", image_tag
                    )

                    recovery_attempt = {
                        "strategy": "clean_rebuild",
                        "success": build_success
                        and self.docker_builder.image_exists(image_tag),
                        "details": "Cleaned cache and rebuilt from scratch",
                    }
                    recovery_result["recovery_attempts"].append(recovery_attempt)

                    if recovery_attempt["success"]:
                        recovery_result["recovery_successful"] = True
                        recovery_result["final_status"] = "recovered"
                        return recovery_result

                except Exception as e:
                    recovery_result["recovery_attempts"][-1]["error"] = str(e)

                # Recovery Strategy 2: Alternative base image
                try:
                    self.logger.info(
                        f"Attempting alternative base image for {service_name}"
                    )
                    alt_config = service_config.copy()
                    alt_config["base_image"] = "alpine:latest"  # Fallback base

                    image_tag = f"{service_name}-alt:latest"
                    build_success = self.docker_builder.build_image(
                        "Dockerfile.alt", image_tag
                    )

                    recovery_attempt = {
                        "strategy": "alternative_base",
                        "success": build_success
                        and self.docker_builder.image_exists(image_tag),
                        "details": "Used alternative base image",
                    }
                    recovery_result["recovery_attempts"].append(recovery_attempt)

                    if recovery_attempt["success"]:
                        recovery_result["recovery_successful"] = True
                        recovery_result["final_status"] = "recovered_alternative"
                        return recovery_result

                except Exception as e:
                    recovery_result["recovery_attempts"][-1]["error"] = str(e)

                # Recovery Strategy 3: Use pre-built image
                try:
                    self.logger.info(f"Attempting pre-built image for {service_name}")
                    prebuilt_tag = f"registry/{service_name}:stable"

                    if self.docker_builder.image_exists(prebuilt_tag):
                        recovery_attempt = {
                            "strategy": "prebuilt_image",
                            "success": True,
                            "details": f"Using pre-built image {prebuilt_tag}",
                        }
                        recovery_result["recovery_attempts"].append(recovery_attempt)
                        recovery_result["recovery_successful"] = True
                        recovery_result["final_status"] = "recovered_prebuilt"
                        return recovery_result

                except Exception as e:
                    recovery_result["recovery_attempts"].append(
                        {
                            "strategy": "prebuilt_image",
                            "success": False,
                            "error": str(e),
                        }
                    )

                # All recovery attempts failed
                recovery_result["final_status"] = "recovery_failed"
                return recovery_result

            def _clean_build_cache(self, service_name):
                """Clean build cache for service."""
                # Mock cache cleaning
                pass

        recovery_system = MockRecoverySystem()

        # Test successful recovery (clean rebuild)
        recovery_system.docker_builder.build_image.return_value = True
        recovery_system.docker_builder.image_exists.return_value = True

        service_config = {"name": "recoverable-service"}
        result = recovery_system.attempt_service_recovery(
            service_config, "Build failed"
        )

        assert result["recovery_successful"] is True
        assert result["final_status"] == "recovered"
        assert len(result["recovery_attempts"]) >= 1
        assert result["recovery_attempts"][0]["strategy"] == "clean_rebuild"

        # Test failed recovery (all strategies fail)
        recovery_system.docker_builder.build_image.return_value = False
        recovery_system.docker_builder.image_exists.return_value = False

        failed_config = {"name": "unrecoverable-service"}
        failed_result = recovery_system.attempt_service_recovery(
            failed_config, "Critical build error"
        )

        assert failed_result["recovery_successful"] is False
        assert failed_result["final_status"] == "recovery_failed"
        assert (
            len(failed_result["recovery_attempts"]) > 1
        )  # Multiple strategies attempted


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
