"""Docker image build and management operations.

Provides the ImageOperationsMixin with methods for building images,
validating prerequisites, and managing image lifecycle.
"""

import json
import time
from pathlib import Path
from typing import Any, Dict, Optional

from docker.errors import BuildError

from panther.core.exceptions.fast_fail import (
    DockerBuildException,
    ErrorCategory,
    ErrorSeverity,
    PantherException,
)

from .tag_generator import generate_image_tag as _generate_image_tag
from .tag_generator import sanitize_docker_tag as _sanitize_docker_tag


class ImageOperationsMixin:
    """Mixin providing Docker image build and management operations.

    Expects the host class to provide:
        - self.logger
        - self.global_config (optional)
        - self.client (Docker client)
        - self.build_log_file
        - self.docker_logger
        - self.image_cache
        - Platform detection methods from PlatformDetectionMixin
        - Buildx methods from BuildxOperationsMixin
        - Cache methods from DockerBuildCacheMixin
        - Error handling from ErrorHandlerMixin
    """

    def build_image(
        self,
        impl_name: str,
        version: str,
        dockerfile_path: Path,
        context_path: Path,
        config: Dict[str, Any],
        tag_version: str = "latest",
        remove_dangling: bool = False,
        experiment_id: Optional[str] = None,
    ) -> Optional[str]:
        """Build Docker image with intelligent caching and cross-platform support.

        Args:
            impl_name: Implementation name for image tagging
            version: Version string for image tagging
            dockerfile_path: Absolute path to Dockerfile
            context_path: Absolute path to build context directory
            config: Build configuration dict
            tag_version: Docker tag version suffix (default: 'latest')
            remove_dangling: Remove dangling images after build (default: False)
            experiment_id: Optional experiment identifier for tracking

        Returns:
            Generated Docker image tag on success, None if build failed or skipped

        Raises:
            DockerBuildException: Build operation failed
            PantherException: Validation error or Docker daemon unavailable
        """
        try:
            # Fast-fail validation before expensive build operation
            self._validate_build_prerequisites(
                impl_name, dockerfile_path, context_path, config
            )

            if self.client is None:
                self.logger.error(
                    "Docker client is not available. Cannot build Docker image."
                )
                raise DockerBuildException(
                    message="Docker client is not available. Please check Docker daemon is running.",
                    image_name=impl_name,
                    dockerfile=str(dockerfile_path),
                    build_error="Docker client not initialized",
                )

            # Extract build and runtime modes from config
            build_mode = self.validate_build_mode_for_architecture(
                config.get("build_mode", "")
            )
            runtime_mode = config.get("runtime_mode", "minimal")
            z3_source = config.get("z3_source", "")
            _valid_z3_sources = {"local", "pip", ""}
            if z3_source and z3_source not in _valid_z3_sources:
                self.logger.warning(
                    "Unknown z3_source value '%s', falling back to 'local'. "
                    "Valid values: local, pip",
                    z3_source,
                )
                z3_source = "local"

            # Construct image tag with mode information
            image_tag = self.generate_image_tag(
                impl_name=impl_name,
                version=version,
                tag_version=tag_version,
                build_mode=build_mode,
                runtime_mode=runtime_mode,
                target_platform=self.get_effective_build_platform(),
                z3_source=z3_source,
            )

            # Check build cache first
            dependencies = config.get("dependencies", {})
            target_platform = self.get_effective_build_platform()
            build_platform = self._get_host_platform()

            # Extract architecture from platform strings
            target_arch = (
                target_platform.split("/")[-1]
                if "/" in target_platform
                else target_platform
            )
            target_os = (
                target_platform.split("/")[0] if "/" in target_platform else "linux"
            )
            build_arch = (
                build_platform.split("/")[-1]
                if "/" in build_platform
                else build_platform
            )
            build_os = (
                build_platform.split("/")[0] if "/" in build_platform else "linux"
            )

            # Start with per-service user build_args (lowest priority)
            resolved_docker = config.get("resolved_docker", None)
            user_build_args = {}
            if resolved_docker is not None:
                user_build_args = resolved_docker.get("build_args", {})
                self.logger.debug(
                    "Using per-service resolved Docker configuration for build arguments"
                )

            # Framework args take precedence over user-supplied build_args
            framework_build_args = {
                "VERSION": config.get("commit", "production"),
                "DEPENDENCIES": json.dumps(dependencies) if dependencies else "[]",
                "BUILD_MODE": build_mode,
                "RUNTIME_MODE": config.get("runtime_mode", "minimal"),
                "Z3_SOURCE": z3_source or "local",
                "TARGETPLATFORM": target_platform,
                "BASE_IMAGE": self.generate_image_tag(
                    impl_name="panther_base_service",
                    version="",
                    tag_version="latest",
                    build_mode="",
                    runtime_mode=runtime_mode,
                    target_platform=target_platform,
                ),
                "BUILDPLATFORM": build_platform,
                "TARGETARCH": target_arch,
                "TARGETOS": target_os,
                "BUILDARCH": build_arch,
                "BUILDOS": build_os,
            }
            # Merge: user args first, then framework args override
            build_args = {**user_build_args, **framework_build_args}

            self.logger.debug(
                "Receiving configuration (%s) for building Docker image with tag='%s' with version='%s' from Dockerfile='%s' in context='%s' with arguments=%s for target architecture='%s' on host platform='%s'",
                config,
                image_tag,
                version,
                dockerfile_path,
                context_path,
                build_args,
                self.get_target_platform(),
                self._get_host_platform(),
            )

            # Resolve force_build and no_cache from per-service overrides or global config
            if resolved_docker is not None:
                force_build = bool(
                    resolved_docker.get("force_build_docker_image", False)
                    or resolved_docker.get("no_docker_cache", False)
                )
                no_cache = bool(resolved_docker.get("no_docker_cache", False))
            elif (
                hasattr(self, "global_config")
                and self.global_config
                and hasattr(self.global_config, "docker")
            ):
                force_build = bool(
                    getattr(
                        self.global_config.docker, "force_build_docker_image", False
                    )
                    or getattr(self.global_config.docker, "no_docker_cache", False)
                )
                no_cache = bool(
                    getattr(self.global_config.docker, "no_docker_cache", False)
                )
            else:
                force_build = True
                no_cache = False

            if not force_build:
                self.logger.debug(
                    "Checking Docker build cache for image '%s' with args: %s",
                    image_tag,
                    build_args,
                )
                if cached_result := self.should_use_cached_build(
                    dockerfile_path=dockerfile_path,
                    context_path=context_path,
                    build_args=build_args,
                    image_tag=image_tag,
                    force_build=force_build,
                ):
                    self.logger.info(
                        "Using cached Docker image '%s' for implementation '%s'",
                        image_tag,
                        impl_name,
                    )
                    self.logger.info("Image cached: %s (skipped)", image_tag)
                    return cached_result

            log_f = None

            # Calculate relative path from context to dockerfile
            if resolved_docker is not None:
                use_buildx_config = resolved_docker.get("use_buildx", True)
            else:
                use_buildx_config = (
                    hasattr(self, "global_config")
                    and self.global_config
                    and hasattr(self.global_config, "docker")
                    and self.global_config.docker.use_buildx
                )

            if use_buildx_config:
                buildkit_candidates = [
                    Path(dockerfile_path).parent / "Dockerfile.buildkit",
                    dockerfile_path,  # fallback to original
                ]
            else:
                buildkit_candidates = [dockerfile_path]

            selected_dockerfile = None
            for candidate in buildkit_candidates:
                if candidate.exists():
                    selected_dockerfile = candidate
                    self.logger.debug(
                        "Selected Dockerfile (use_buildx=%s): %s",
                        use_buildx_config,
                        selected_dockerfile,
                    )
                    break

            if selected_dockerfile is None:
                raise DockerBuildException(
                    message="No suitable Dockerfile found for regular build",
                    image_name=impl_name,
                    dockerfile=str(dockerfile_path),
                    build_error="Dockerfile not found",
                )

            relative_dockerfile_path = selected_dockerfile.relative_to(context_path)

            # Track build start time for cache
            _build_start_time = time.time()

            # Set the current dockerfile path for BuildKit detection
            self._current_dockerfile_path = selected_dockerfile

            # Check if we should use buildx for this build
            if self._should_use_buildx():
                return self._build_with_buildx(
                    impl_name=impl_name,
                    dockerfile_path=dockerfile_path,
                    context_path=context_path,
                    build_args=build_args,
                    config=config,
                    version=version,
                    tag_version=tag_version,
                    experiment_id=experiment_id,
                    image_tag=image_tag,
                )

            # Use regular Docker build for same-platform builds
            effective_platform = self.get_effective_build_platform()
            self.logger.info(
                "Building Docker image '%s' using standard Docker build for platform '%s'",
                image_tag,
                effective_platform,
            )
            self.logger.info("Building image: %s", image_tag)

            # Import here to avoid circular dependency at module level
            from panther.core.docker_builder.docker_builder import DockerBuilder

            # Open the build log file if specified
            if self.build_log_file:
                log_filename = self._get_build_log_path(image_tag)
                log_f = open(log_filename, "w")

            try:
                image, build_logs = self.client.images.build(
                    path=str(context_path),
                    dockerfile=str(relative_dockerfile_path),
                    tag=image_tag,
                    network_mode="host",
                    buildargs=build_args,
                    platform=effective_platform,
                    nocache=no_cache
                    and not DockerBuilder.was_built_this_session(image_tag),
                )

                self.docker_logger.log_docker_output(
                    build_logs, f"Building Docker image '{image_tag}'", log_f
                )
            finally:
                if log_f:
                    log_f.close()

            # Register the build in cache
            build_time = (
                time.time() - _build_start_time
                if "_build_start_time" in locals()
                else 0
            )

            self.register_build(
                image_id=image.id,
                image_tag=image_tag,
                dockerfile_path=dockerfile_path,
                context_path=context_path,
                build_args=build_args,
                build_time_seconds=build_time,
                experiment_id=experiment_id,
            )
            DockerBuilder.mark_session_built(image_tag)

            self.logger.info("Image built: %s (%.1fs)", image_tag, build_time)
            self.logger.info(
                "Successfully built Docker image '%s' with context '%s' and build args '%s'",
                image_tag,
                context_path,
                build_args,
            )

            # Clean up any dangling images
            if remove_dangling:
                self.logger.info("Removing dangling images after build.")
                self.remove_dangling_images()

            return image_tag
        except PantherException:
            raise
        except BuildError as e:
            tag_for_error = locals().get("image_tag", f"{impl_name}_unknown")
            log_file = locals().get("log_f")
            self.logger.error(
                "Failed to build Docker image '%s' : %s", tag_for_error, e
            )
            self.docker_logger.log_and_raise_build_exception(
                impl_name, dockerfile_path, tag_for_error, e, log_file
            )
        except Exception as e:
            tag_for_error = locals().get("image_tag", f"{impl_name}_unknown")
            log_file = locals().get("log_f")
            self.handle_error(
                error=e,
                operation=f"build Docker image '{impl_name}'",
                severity=ErrorSeverity.CRITICAL,
                category=ErrorCategory.DOCKER_BUILD,
                additional_context={
                    "impl_name": impl_name,
                    "dockerfile_path": str(dockerfile_path),
                    "context_path": str(context_path),
                },
            )
            self.docker_logger.log_and_raise_build_exception(
                impl_name, dockerfile_path, tag_for_error, e, log_file
            )

    def generate_image_tag(
        self,
        impl_name,
        version,
        tag_version,
        build_mode="",
        runtime_mode="minimal",
        target_platform="",
        z3_source="",
    ):
        """Generate Docker image tag. Delegates to ``tag_generator`` module."""
        return _generate_image_tag(
            impl_name=impl_name,
            version=version,
            tag_version=tag_version,
            build_mode=build_mode,
            runtime_mode=runtime_mode,
            target_platform=target_platform,
            z3_source=z3_source,
        )

    def _sanitize_docker_tag(self, tag: str) -> str:
        """Sanitize Docker tag. Delegates to ``tag_generator`` module."""
        return _sanitize_docker_tag(tag)

    def _validate_build_prerequisites(
        self,
        impl_name: str,
        dockerfile_path: Path,
        context_path: Path,
        config: Dict[str, Any],
    ) -> None:
        """Validate all prerequisites before starting Docker build operation.

        Args:
            impl_name: The name of the implementation
            dockerfile_path: Path to the Dockerfile
            context_path: Path to the build context
            config: Configuration dictionary

        Raises:
            PantherException: If any validation fails
        """
        if not impl_name or not isinstance(impl_name, str):
            raise PantherException(
                message=f"Invalid implementation name: {impl_name}",
                severity=ErrorSeverity.CRITICAL,
                category=ErrorCategory.DOCKER_BUILD,
                context={"impl_name": impl_name},
            )

        if not dockerfile_path.exists():
            raise PantherException(
                message=f"Dockerfile not found: {dockerfile_path}",
                severity=ErrorSeverity.CRITICAL,
                category=ErrorCategory.DOCKER_BUILD,
                context={"dockerfile_path": str(dockerfile_path)},
            )

        if not dockerfile_path.is_file():
            raise PantherException(
                message=f"Dockerfile path is not a file: {dockerfile_path}",
                severity=ErrorSeverity.CRITICAL,
                category=ErrorCategory.DOCKER_BUILD,
                context={"dockerfile_path": str(dockerfile_path)},
            )

        if not context_path.exists():
            raise PantherException(
                message=f"Build context path not found: {context_path}",
                severity=ErrorSeverity.CRITICAL,
                category=ErrorCategory.DOCKER_BUILD,
                context={"context_path": str(context_path)},
            )

        if not context_path.is_dir():
            raise PantherException(
                message=f"Build context must be a directory: {context_path}",
                severity=ErrorSeverity.CRITICAL,
                category=ErrorCategory.DOCKER_BUILD,
                context={"context_path": str(context_path)},
            )

        if not self.is_docker_available():
            raise PantherException(
                message="Docker daemon is not available",
                severity=ErrorSeverity.CRITICAL,
                category=ErrorCategory.DOCKER_RUNTIME,
                context={"impl_name": impl_name},
            )

        if not isinstance(config, dict):
            raise PantherException(
                message=f"Configuration must be a dictionary, got {type(config).__name__}",
                severity=ErrorSeverity.HIGH,
                category=ErrorCategory.CONFIGURATION,
                context={"config_type": type(config).__name__},
            )

        self.logger.debug(
            "Build prerequisites validated for '%s': Dockerfile=%s, Context=%s",
            impl_name,
            dockerfile_path,
            context_path,
        )

    def image_exists(self, image_tag: str) -> bool:
        """Check if a Docker image with the given tag exists locally.

        Args:
            image_tag: Tag of the Docker image.

        Returns:
            True if exists, else False.
        """
        return self.image_cache.image_exists(image_tag, self.client)

    def remove_dangling_images(self):
        """Remove dangling Docker images (images with <none>:<none> tag).

        Returns:
            bool: True if successful, False if an error occurred.
        """
        return self.image_cache.remove_dangling_images(self.client)
