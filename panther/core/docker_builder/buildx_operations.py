"""Docker Buildx operations for cross-platform builds.

Provides the BuildxOperationsMixin with methods for managing Buildx builders,
context configuration, and cross-platform image building.
"""

import json
import os
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, Optional

import click

from panther.core.exceptions.fast_fail import (
    DockerBuildException,
    ErrorCategory,
    ErrorSeverity,
)


class BuildxOperationsMixin:
    """Mixin providing Docker Buildx operations for cross-platform builds.

    Expects the host class to provide:
        - self.logger
        - self.global_config (optional)
        - self.client (Docker client)
        - self.build_log_file
        - self.docker_logger
        - self.image_cache
        - Platform detection methods from PlatformDetectionMixin
        - Cache methods from DockerBuildCacheMixin
        - Error handling from ErrorHandlerMixin
    """

    def _ensure_buildx_context(self, builder_name: str = "default") -> bool:
        """Ensure Docker context is properly configured for Buildx operations.

        Args:
            builder_name: The builder name to test compatibility with

        Returns:
            bool: True if context is ready, False otherwise
        """
        try:
            # Check current context
            result = subprocess.run(
                ["docker", "context", "show"],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode == 0:
                current_context = result.stdout.strip()
                self.logger.debug(f"Current Docker context: {current_context}")

                # Test if the specific builder works with current context
                test_result = subprocess.run(
                    ["docker", "buildx", "inspect", builder_name],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )

                if test_result.returncode == 0:
                    self.logger.debug(
                        f"Builder '{builder_name}' is compatible with context '{current_context}'"
                    )
                    return True
                else:
                    self.logger.warning(
                        f"Builder '{builder_name}' not compatible with context '{current_context}': {test_result.stderr}"
                    )

                    # Try to switch to default context and test again
                    self.logger.info(
                        "Attempting to switch to default context for Buildx compatibility"
                    )
                    switch_result = subprocess.run(
                        ["docker", "context", "use", "default"],
                        capture_output=True,
                        text=True,
                        timeout=10,
                    )

                    if switch_result.returncode == 0:
                        self.logger.info("Successfully switched to default context")

                        # Test builder again with default context
                        retest_result = subprocess.run(
                            ["docker", "buildx", "inspect", builder_name],
                            capture_output=True,
                            text=True,
                            timeout=10,
                        )

                        if retest_result.returncode == 0:
                            self.logger.info(
                                f"Builder '{builder_name}' is now compatible with default context"
                            )
                            return True
                        else:
                            self.logger.error(
                                f"Builder '{builder_name}' still not compatible with default context: {retest_result.stderr}"
                            )
                            return False
                    else:
                        self.logger.error(
                            f"Failed to switch to default context: {switch_result.stderr}"
                        )
                        return False
            else:
                self.logger.warning(
                    f"Failed to get current Docker context: {result.stderr}"
                )
                return False

        except (
            subprocess.TimeoutExpired,
            subprocess.CalledProcessError,
            FileNotFoundError,
        ) as e:
            self.logger.warning(f"Error ensuring Buildx context: {e}")
            return False

    def _setup_buildx_builder(self, builder_name: str) -> bool:
        """Setup and ensure the buildx builder instance is ready.

        Args:
            builder_name: Name of the buildx builder instance

        Returns:
            bool: True if builder is ready, False otherwise
        """
        try:
            # Check if builder already exists
            result = subprocess.run(
                ["docker", "buildx", "inspect", builder_name],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode == 0:
                self.logger.debug("Buildx builder '%s' already exists", builder_name)
                return True

            # Create new builder if it doesn't exist
            self.logger.info("Creating buildx builder: %s", builder_name)
            result = subprocess.run(
                ["docker", "buildx", "create", "--name", builder_name, "--use"],
                capture_output=True,
                text=True,
                timeout=30,
            )

            if result.returncode == 0:
                self.logger.info(
                    "Successfully created buildx builder: %s", builder_name
                )
                return True
            else:
                self.logger.error("Failed to create buildx builder: %s", result.stderr)
                return False

        except (
            subprocess.TimeoutExpired,
            subprocess.CalledProcessError,
            FileNotFoundError,
        ) as e:
            self.logger.error(
                "Error setting up buildx builder '%s': %s", builder_name, e
            )
            return False

    def _should_use_buildx(self) -> bool:
        """Determine if Docker Buildx should be used for the build.

        Returns:
            bool: True if buildx should be used, False otherwise
        """
        # Use buildx for cross-platform builds (when host != target platform)
        host_platform = self._get_host_platform()
        is_cross_platform = host_platform != self.get_target_platform()

        # Check if buildx is available on system first
        if not self._check_buildx_available():
            self.logger.info(
                "Buildx not available on system, falling back to regular Docker build"
            )
            if is_cross_platform:
                self.logger.warning(
                    "Cross-platform build requested but buildx is unavailable; build may fail."
                )
            return False

        # Check if Dockerfile requires BuildKit features (HIGHEST PRIORITY)
        dockerfile_path = getattr(self, "_current_dockerfile_path", None)
        if dockerfile_path and self._dockerfile_requires_buildkit(dockerfile_path):
            self.logger.info(
                "Dockerfile contains BuildKit-specific features, forcing buildx usage"
            )
            return True

        # Check if buildx is explicitly disabled in configuration
        if (
            hasattr(self, "global_config")
            and self.global_config
            and hasattr(self.global_config, "docker")
            and not self.global_config.docker.use_buildx
        ):
            if is_cross_platform:
                self.logger.warning(
                    "Buildx disabled via config but cross-platform build detected (%s -> %s). "
                    "Build may fail without QEMU/emulation support. "
                    "Set use_buildx: true to enable buildx for cross-platform builds.",
                    host_platform,
                    self.get_target_platform(),
                )
            self.logger.debug(
                "Buildx disabled in configuration, using regular Docker build"
            )
            return False

        # If multi-platform builds are enabled, always use buildx
        if (
            hasattr(self, "global_config")
            and self.global_config
            and hasattr(self.global_config, "docker")
            and self.global_config.docker.multi_platform
        ):
            self.logger.debug("Multi-platform builds enabled, using buildx")
            return True

        if is_cross_platform:
            self.logger.info(
                "Cross-platform build detected (%s -> %s), using buildx (required)",
                host_platform,
                self.get_target_platform(),
            )
            return True

        # For same-platform builds, default to regular Docker build
        self.logger.debug(
            "Same-platform build (%s), using regular Docker build for compatibility",
            self.get_target_platform(),
        )
        return False

    def _build_with_buildx(
        self,
        impl_name: str,
        dockerfile_path: Path,
        context_path: Path,
        build_args: Dict[str, Any],
        config: Dict[str, Any],
        version: str,
        tag_version: str = "latest",
        experiment_id: Optional[str] = None,
        image_tag: Optional[str] = None,
    ) -> Optional[str]:
        """Build a Docker image using Docker Buildx for cross-platform builds.

        Args:
            impl_name: The name of the implementation
            version: The version of the implementation
            dockerfile_path: The path to the Dockerfile
            context_path: The path to the build context
            build_args: Build arguments to pass to docker build
            config: Configuration dictionary containing build parameters
            tag_version: The tag version for the Docker image. Defaults to "latest"
            experiment_id: Optional experiment ID for tracking
            image_tag: Optional pre-computed image tag

        Returns:
            Optional[str]: The tag of the built Docker image, or None if build failed

        Raises:
            DockerBuildException: If the buildx build fails
        """
        try:
            # Check if Docker client is available
            if self.client is None:
                self.logger.error(
                    "Docker client is not available. Cannot build Docker image with buildx."
                )
                raise DockerBuildException(
                    message="Docker client is not available. Please check Docker daemon is running.",
                    image_name=impl_name,
                    dockerfile=str(dockerfile_path),
                    build_error="Docker client not initialized",
                )

            # Resolve which buildx builder to use
            builder_name = "default"
            if (
                hasattr(self, "global_config")
                and self.global_config
                and hasattr(self.global_config, "docker")
                and hasattr(self.global_config.docker, "buildx_builder")
            ):
                builder_name = self.global_config.docker.buildx_builder

            # Ensure Docker context is properly configured
            if not self._ensure_buildx_context(builder_name):
                self.logger.error(
                    f"Failed to ensure proper Docker context for Buildx builder '{builder_name}'"
                )
                raise DockerBuildException(
                    message=f"Failed to configure Docker context for Buildx builder '{builder_name}'",
                    image_name=impl_name,
                    dockerfile=str(dockerfile_path),
                    build_error="Docker context configuration failed",
                )

            # For "default" builder, skip custom setup
            if builder_name != "default":
                if not self._setup_buildx_builder(builder_name):
                    raise DockerBuildException(
                        message=f"Failed to setup buildx builder: {builder_name}",
                        image_name=impl_name,
                        dockerfile=str(dockerfile_path),
                        build_error="Buildx builder setup failed",
                    )

            # Extract build and runtime modes from config
            build_mode = config.get("build_mode", "")
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
            self.logger.info(
                "Building Docker image '%s' with buildx for platform '%s'",
                image_tag,
                self.get_effective_build_platform(),
            )
            click.echo(f"  Building image: {image_tag} (buildx)")
            # Prepare build arguments
            dependencies = config.get("dependencies", {})
            dependencies_json = json.dumps(dependencies) if dependencies else "[]"

            target_platform = self.get_target_platform()
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
                    "Using per-service resolved Docker configuration for buildx build arguments"
                )

            # Framework args take precedence over user-supplied build_args
            framework_build_args = {
                "VERSION": config.get("commit", "master"),
                "DEPENDENCIES": dependencies_json,
                "BUILD_MODE": build_mode,
                "RUNTIME_MODE": config.get("runtime_mode", "minimal"),
                "Z3_SOURCE": z3_source or "local",
                "BASE_IMAGE": self.generate_image_tag(
                    impl_name="panther_base_service",
                    version="",
                    tag_version="latest",
                    build_mode="",
                    runtime_mode=runtime_mode,
                    target_platform=target_platform,
                ),
                "TARGETPLATFORM": target_platform,
                "BUILDPLATFORM": build_platform,
                "TARGETARCH": target_arch,
                "TARGETOS": target_os,
                "BUILDARCH": build_arch,
                "BUILDOS": build_os,
            }
            # Merge: framework build_args override user-supplied build_args
            build_args = {**user_build_args, **framework_build_args}

            # Calculate relative path from context to dockerfile
            buildkit_candidates = [
                Path(dockerfile_path).parent / "Dockerfile.buildkit",
                dockerfile_path,  # fallback to original
            ]

            selected_dockerfile = None
            for candidate in buildkit_candidates:
                if candidate.exists():
                    selected_dockerfile = candidate
                    self.logger.info(
                        "Selected Dockerfile for buildx: %s", selected_dockerfile
                    )
                    break

            if selected_dockerfile is None:
                raise DockerBuildException(
                    message="No suitable Dockerfile found for buildx build",
                    image_name=impl_name,
                    dockerfile=str(dockerfile_path),
                    build_error="Dockerfile not found",
                )

            relative_dockerfile_path = selected_dockerfile.relative_to(context_path)

            # Construct buildx command
            buildx_cmd = [
                "docker",
                "buildx",
                "build",
                "--platform",
                self.get_target_platform(),
                "--file",
                str(relative_dockerfile_path),
                "--tag",
                image_tag,
                "--debug",
                "--load",  # Load the image into local Docker daemon
            ]

            # For base service images, also create platform-agnostic tags
            if "base_service" in impl_name.lower():
                base_tag_parts = image_tag.split(":")
                if len(base_tag_parts) == 2:
                    base_name, tag_with_platform = base_tag_parts
                    platform_str = self.get_target_platform().replace("/", "-")
                    platform_suffix = f"-{platform_str}"
                    if tag_with_platform.endswith(platform_suffix):
                        platform_agnostic_tag = (
                            f"{base_name}:{tag_with_platform[:-len(platform_suffix)]}"
                        )
                        buildx_cmd.extend(["--tag", platform_agnostic_tag])
                        self.logger.info(
                            "Adding platform-agnostic tag for base service: %s",
                            platform_agnostic_tag,
                        )

            buildx_cmd.append(str(context_path))

            # Add build arguments
            for key, value in build_args.items():
                buildx_cmd.extend(["--build-arg", f"{key}={value}"])

            # Add network mode
            buildx_cmd.extend(["--network", "host"])

            # Resolve force_build and no_cache
            if resolved_docker is not None:
                no_cache = bool(resolved_docker.get("no_docker_cache", False))
            elif (
                hasattr(self, "global_config")
                and self.global_config
                and hasattr(self.global_config, "docker")
            ):
                no_cache = bool(
                    getattr(self.global_config.docker, "no_docker_cache", False)
                )
            else:
                no_cache = False

            # Import here to avoid circular dependency at module level
            from panther.core.docker_builder.docker_builder import DockerBuilder

            if no_cache and not DockerBuilder.was_built_this_session(image_tag):
                buildx_cmd.append("--no-cache")
                self.logger.info(
                    "no_docker_cache: passing --no-cache for first build of %s",
                    image_tag,
                )

            self.logger.debug("Executing buildx command: %s", " ".join(buildx_cmd))

            # Track build start time
            build_start_time = time.time()

            # Ensure context is set right before executing the BuildX command
            original_context = None
            try:
                context_result = subprocess.run(
                    ["docker", "context", "show"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if context_result.returncode == 0:
                    original_context = context_result.stdout.strip()

                if original_context != "default":
                    self.logger.debug(
                        "Switching to default context for BuildX command execution"
                    )
                    switch_result = subprocess.run(
                        ["docker", "context", "use", "default"],
                        capture_output=True,
                        text=True,
                        timeout=5,
                    )
                    if switch_result.returncode != 0:
                        self.logger.warning(
                            f"Failed to switch to default context: {switch_result.stderr}"
                        )

                # Execute buildx build
                result = subprocess.run(
                    buildx_cmd,
                    cwd=str(context_path),
                    capture_output=True,
                    text=True,
                    timeout=1800,
                )

            finally:
                # Restore original context if we switched it
                if original_context and original_context != "default":
                    self.logger.debug(f"Restoring original context: {original_context}")
                    restore_result = subprocess.run(
                        ["docker", "context", "use", original_context],
                        capture_output=True,
                        text=True,
                        timeout=5,
                    )
                    if restore_result.returncode != 0:
                        self.logger.warning(
                            f"Failed to restore original context: {restore_result.stderr}"
                        )

            # Log build output
            build_logs = []

            if result.stdout:
                build_logs.extend(
                    {"stream": line + "\n"} for line in result.stdout.splitlines()
                )
            if result.stderr:
                build_logs.extend(
                    {"stream": line + "\n"} for line in result.stderr.splitlines()
                )

            build_logs = iter(build_logs)

            # Use existing docker logger for consistency
            log_f = None
            try:
                if self.build_log_file:
                    buildx_tag = (
                        image_tag.replace(":", "_").replace("/", "_") + "_buildx"
                    )
                    log_filename = self._get_build_log_path(buildx_tag)
                    self.logger.debug("Opening buildx log file at: %s", log_filename)
                    self.logger.debug("Current working directory: %s", os.getcwd())
                    log_f = open(log_filename, "w")

                self.docker_logger.log_docker_output(
                    build_logs,
                    f"Building Docker image '{image_tag}' with buildx",
                    log_f,
                )
            finally:
                if log_f:
                    log_f.close()

            # Check if build succeeded
            if result.returncode != 0:
                error_msg = result.stderr or "Unknown buildx build error"
                self.logger.error(
                    "Buildx build failed for '%s': %s", image_tag, error_msg
                )
                raise DockerBuildException(
                    message=f"Buildx build failed: {error_msg}",
                    image_name=impl_name,
                    dockerfile=str(dockerfile_path),
                    build_error=error_msg,
                )

            # Register the build in cache
            build_time = time.time() - build_start_time

            try:
                image = self.client.images.get(image_tag)
            except Exception as e:
                self.logger.warning(
                    "Could not get image ID for cache registration: %s", e
                )
                raise DockerBuildException(
                    message=f"Failed to retrieve image ID for '{image_tag}'",
                    image_name=impl_name,
                    dockerfile=str(dockerfile_path),
                    build_error="Image ID retrieval failed",
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

            click.echo(f"  \u2713 Image built: {image_tag} ({build_time:.1f}s)")
            self.logger.info(
                "Successfully built Docker image '%s' with buildx for platform '%s'",
                image_tag,
                self.get_target_platform(),
            )

            return image_tag

        except subprocess.TimeoutExpired:
            error_msg = f"Buildx build timeout after 30 minutes for {image_tag}"
            self.logger.error(error_msg)
            raise DockerBuildException(
                message=error_msg,
                image_name=impl_name,
                dockerfile=str(dockerfile_path),
                build_error="Build timeout",
            )
        except Exception as e:
            self.logger.error("Buildx build failed for '%s': %s", impl_name, e)
            self.handle_error(
                error=e,
                operation=f"buildx build Docker image '{impl_name}'",
                severity=ErrorSeverity.CRITICAL,
                category=ErrorCategory.DOCKER_BUILD,
                additional_context={
                    "impl_name": impl_name,
                    "dockerfile_path": str(dockerfile_path),
                    "context_path": str(context_path),
                    "target_platform": self.get_target_platform(),
                },
            )
            raise
