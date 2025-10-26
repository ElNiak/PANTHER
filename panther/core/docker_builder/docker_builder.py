"""
DockerBuilder - Singleton Docker Management System

This module provides a singleton DockerBuilder class that manages Docker operations
across the PANTHER framework. The singleton pattern ensures:

1. Single Docker client connection per application
2. Shared Docker build cache across all components
3. Consistent Docker configuration throughout the system
4. Reduced resource usage and connection overhead

Usage:
    # All of these return the same singleton instance
    builder1 = DockerBuilder()
    builder2 = DockerBuilder.get_instance()
    builder3 = SomeClass().docker_builder  # via DockerOperationsMixin

Note: Configuration parameters (build_log_file, enable_cache, global_config) can be
updated on subsequent calls, allowing dynamic configuration changes.
"""

import json
import logging
import os
import platform
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import docker
from docker.errors import BuildError, DockerException, NotFound

from panther.core.docker_builder.utils.context_helper import (
    _ensure_docker_host,
    ensure_builder_context,
)
from panther.core.docker_builder.utils.docker_output_parser import DockerOutputParser
from panther.core.exceptions import EnvironmentPluginNotFound, ServicePluginNotFound
from panther.core.exceptions.error_handler_mixin import ErrorHandlerMixin
from panther.core.exceptions.fast_fail import (
    DockerBuildException,
    ErrorCategory,
    ErrorSeverity,
    PantherException,
)
from panther.core.utils.logging_mixin import LoggerMixin

from .caching.docker_build_cache_mixin import DockerBuildCacheMixin
from .caching.docker_image_cache import DockerImageCache


class DockerBuilder(DockerBuildCacheMixin, LoggerMixin, ErrorHandlerMixin):
    """
    DockerBuilder is a utility class for managing Docker images and containers.

    Provides methods to build, push, and manage Docker images and containers,
    as well as manipulate the /etc/hosts file and Docker networks.

    This class implements the Singleton pattern to ensure only one instance
    exists across the application, preventing multiple Docker client connections.
    """

    _instance = None
    _initialized = False
    MAX_TAG_LENGTH = 100  # Maximum Docker tag length (leave room for registry prefix)

    def __new__(cls, *args, **kwargs):
        """
        Create or return the singleton instance.

        If an instance already exists, returns it regardless of parameters.
        Parameters are only used during first instantiation.
        """
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(
        self,
        build_log_file: bool = True,
        enable_cache: bool = True,
        global_config=None,
        experiment_context=None,
    ):
        """
        Initialize the DockerBuilder singleton.

        Args:
            build_log_file: Whether to create log files for Docker builds
            enable_cache: Whether to enable Docker build caching
            global_config: Global configuration object containing Docker settings
            experiment_context: Optional experiment context for organizing build logs

        Note: Configuration parameters can be updated on subsequent calls.
        """
        # Allow parameter updates even for existing instances
        if getattr(self.__class__, "_initialized", False):
            # Update parameters on existing instance
            updated_params = []

            self.update_parameters(
                build_log_file, global_config, experiment_context, updated_params
            )

            if updated_params:
                self.logger.debug(
                    f"Updated DockerBuilder parameters: {', '.join(updated_params)}"
                )
            else:
                self.logger.debug("DockerBuilder parameters unchanged.")
            return

        # First-time initialization
        super().__init__()
        # Initialize with docker_operations feature for specialized logging
        self.__init_logger__("docker_operations")
        self.__class__._initialized = True
        self.logger.info("Initializing DockerBuilder singleton instance")

        self.plugins_dir = None
        self.build_log_file = build_log_file
        self.client = None
        self.global_config = global_config
        self.experiment_context = experiment_context

        # Initialize Docker image cache for resilient operations (#TODO add parameters)
        self.image_cache = DockerImageCache(
            cache_ttl=300, retry_count=1, retry_delay=1.0  # 5 minutes TTL
        )

        self.docker_logger = DockerOutputParser()

        if self.global_config and self.global_config.docker.force_build_docker_image:
            enable_cache = False  # Force build overrides cache setting
            self.logger.warning("Force build enabled, disabling Docker build cache.")

        # Enable Docker build cache
        self.enable_cache(enable_cache)
        self._cache_enabled = enable_cache  # Store for comparison in re-init attempts
        self.logger.info(
            f"Docker build cache: {'enabled' if enable_cache else 'disabled'}"
        )
        try:
            os.environ["DOCKER_BUILDKIT"] = "1"
            os.environ["COMPOSE_DOCKER_CLI_BUILD"] = "1"
            os.environ[
                "DOCKER_PY_VERBOSE"
            ] = "1"  # Enable verbose logging for Docker SDK
            logging.getLogger("docker").setLevel(logging.DEBUG)
            logging.getLogger("requests").setLevel(
                logging.DEBUG
            )  # Reduce noise from requests library
            host_override = (
                getattr(self.global_config.docker, "docker_host_override", None)
                if hasattr(self, "global_config")
                and self.global_config
                and hasattr(self.global_config, "docker")
                else None
            )
            _ensure_docker_host(explicit=host_override)
            self.client = docker.from_env()
            self.client.ping()
            self.logger.info("Connected to Docker daemon successfully.")
            self.logger.debug("Using Docker platform: %s", self._get_host_platform())

            if self.client and enable_cache:
                # Set Docker client for image cache
                self.image_cache.set_docker_client(self.client)

                # Log cache statistics on initialization
                if hasattr(self, "get_cache_stats"):
                    stats = self.get_cache_stats()
                    self.logger.info(
                        f"Docker registry loaded with {stats['registry_stats']['total_resources']} resources"
                    )

                # Log image cache statistics
                cache_stats = self.image_cache.get_cache_stats()
                self.logger.info(
                    f"Docker image cache initialized: {cache_stats['total_images']} images, "
                    f"fresh={cache_stats['cache_fresh']}"
                )
        except DockerException as e:
            self.logger.error(
                "Failed to connect to Docker daemon: %s, check your DOCKER_HOST", e
            )
            # Still initialize image cache for resilient operations
            self.logger.warning("Docker daemon unavailable, running in cache-only mode")

    def update_parameters(
        self, build_log_file, global_config, experiment_context, updated_params
    ):
        if hasattr(self, "build_log_file") and self.build_log_file != build_log_file:
            self.build_log_file = build_log_file
            updated_params.append(f"build_log_file={build_log_file}")
        enable_cache = True  # Default to True unless overridden by global config
        if (
            global_config 
            and getattr(self, "global_config", None) != global_config
        ):
            self.global_config = global_config
            updated_params.append("global_config=<updated>")

            # Re-evaluate cache settings if global config changed
            if (
                hasattr(global_config, "docker")
                and hasattr(global_config.docker, "force_build_docker_image")
                and global_config.docker.force_build_docker_image
            ):
                enable_cache = False
                self.logger.warning(
                    "Force build enabled via updated config, disabling Docker build cache."
                )
        elif self.global_config and self.global_config.docker.force_build_docker_image:
            enable_cache = False  # Force build overrides cache setting
            self.logger.warning("Force build enabled, disabling Docker build cache.")
        if (
            experiment_context is not None
            and getattr(self, "experiment_context", None) != experiment_context
        ):
            self.experiment_context = experiment_context
            updated_params.append("experiment_context=<updated>")

        if hasattr(self, "_cache_enabled") and self._cache_enabled != enable_cache:
            self.enable_cache(enable_cache)
            self._cache_enabled = enable_cache
            updated_params.append(f"enable_cache={enable_cache}")

    def is_docker_available(self) -> bool:
        """
        Check if Docker daemon is available and responsive.

        Returns:
            bool: True if Docker is available, False otherwise
        """
        if self.client is None:
            return False

        try:
            self.client.ping()
            return True
        except DockerException:
            return False

    def get_docker_status(self) -> Dict[str, Union[bool, str, int]]:
        """
        Get comprehensive Docker status including cache information.

        Returns:
            Dictionary with Docker and cache status
        """
        docker_available = self.is_docker_available()
        cache_stats = self.image_cache.get_cache_stats()

        return {
            "docker_available": docker_available,
            "cache_enabled": True,
            "cached_images": cache_stats["total_images"],
            "cache_fresh": cache_stats["cache_fresh"],
            "cache_age_seconds": cache_stats["cache_age_seconds"],
            "fallback_mode": not docker_available and cache_stats["total_images"] > 0,
        }

    def _get_build_log_path(self, image_tag: str) -> str:
        """
        Generate appropriate log path for Docker build logs.

        When experiment context is available, logs are placed in test-specific directories:
        1. {test_experiment_dir}/docker_builds/{safe_image_tag}.log (preferred)
        2. {experiment_dir}/{test_name}/docker_builds/{safe_image_tag}.log
        3. {experiment_dir}/docker_builds/{safe_image_tag}.log (fallback)

        This ensures each test case has its own build logs, preventing overwrites.

        Args:
            image_tag: The Docker image tag to generate log path for

        Returns:
            str: Full path to the log file
        """
        safe_tag = image_tag.replace(":", "_").replace("/", "_")
        log_filename = f"{safe_tag}.log"

        if (
            self.experiment_context
            and hasattr(self.experiment_context, "experiment_dir")
            and self.experiment_context.experiment_dir
        ):
            # Determine base directory for logs
            base_dir = self.experiment_context.experiment_dir

            # Use test-specific directory if test context is available
            if (
                hasattr(self.experiment_context, "test_experiment_dir")
                and self.experiment_context.test_experiment_dir
            ):
                base_dir = self.experiment_context.test_experiment_dir
                self.logger.debug("Using test-specific directory for Docker logs")
            elif (
                hasattr(self.experiment_context, "test_name")
                and self.experiment_context.test_name
            ):
                # Create test-specific subdirectory if we have test name but not test_experiment_dir
                base_dir = (
                    self.experiment_context.experiment_dir
                    / self.experiment_context.test_name
                )
                self.logger.debug("Creating test-specific directory: %s", base_dir)

            # Create docker_builds subdirectory
            docker_logs_dir = base_dir / "docker_builds"
            docker_logs_dir.mkdir(parents=True, exist_ok=True)
            log_path = str(docker_logs_dir / log_filename)
            self.logger.debug(
                "Docker build log will be written to test-specific output: %s", log_path
            )
            return log_path
        else:
            # Fallback to current behavior (current working directory)
            self.logger.debug(
                "No experiment context available, using current directory for build log: %s",
                log_filename,
            )
            return log_filename

    def get_target_platform(self) -> str:
        """
        Detect the appropriate Docker platform based on the current architecture.

        Respects the target_platform configuration override if specified.

        Returns:
            str: Docker platform string (e.g., 'linux/amd64', 'linux/arm64')
        """
        # Check for configuration override first
        if (
            hasattr(self, "global_config")
            and self.global_config
            and hasattr(self.global_config, "docker")
            and self.global_config.docker.target_platform
        ):
            target_platform = self.global_config.docker.target_platform
            self.logger.debug(
                "Using configured target platform override: %s", target_platform
            )
            return target_platform

        # Detect host architecture and map to appropriate Docker platform
        machine = platform.machine().lower()
        if machine in ["arm64", "aarch64"]:
            # docker_platform = "linux/arm64"  # TODO some plugins are not supported on arm64
            self.logger.warning(
                "Detected ARM64 architecture '%s', defaulting to linux/amd64 for compatibility",
                machine,
            )
            docker_platform = "linux/amd64"  # Fallback to amd64 for compatibility
        elif machine in ["x86_64", "amd64"]:
            docker_platform = "linux/amd64"
        else:
            # Default to amd64 for unknown architectures
            docker_platform = "linux/amd64"
            self.logger.warning(
                "Unknown architecture '%s', defaulting to %s", machine, docker_platform
            )

        self.logger.debug(
            "Detected host architecture: %s -> Docker platform: %s",
            machine,
            docker_platform,
        )

        return docker_platform

    def _check_buildx_available(self) -> bool:
        """
        Check if Docker Buildx is available on the system.

        Returns:
            bool: True if buildx is available, False otherwise
        """
        try:
            result = subprocess.run(
                ["docker", "buildx", "version"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                self.logger.debug(
                    "Docker Buildx is available: %s", result.stdout.strip()
                )
                return True
            else:
                self.logger.warning("Docker Buildx not available: %s", result.stderr)
                return False
        except (
            subprocess.TimeoutExpired,
            subprocess.CalledProcessError,
            FileNotFoundError,
        ) as e:
            self.logger.warning("Failed to check Docker Buildx availability: %s", e)
            return False

    def _setup_buildx_builder(self, builder_name: str) -> bool:
        """
        Setup and ensure the buildx builder instance is ready.

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
        """
        Determine if Docker Buildx should be used for the build.

        Args:
            target_platform: Target platform for the build

        Returns:
            bool: True if buildx should be used, False otherwise
        """
        # Use buildx for cross-platform builds (when host != target platform)
        host_platform = self._get_host_platform()
        is_cross_platform = host_platform != self.get_target_platform()
        
        # Check if buildx is explicitly disabled in configuration
        if (
            hasattr(self, "global_config")
            and self.global_config
            and hasattr(self.global_config, "docker")
            and not self.global_config.docker.use_buildx
            and not is_cross_platform
        ):
            self.logger.debug(
                "Buildx disabled in configuration, using regular Docker build"
            )
            return False

        # Check if buildx is available on system
        if not self._check_buildx_available():
            self.logger.info(
                "Buildx not available on system, falling back to regular Docker build"
            )
            if is_cross_platform:
                self.logger.warning(
                    "Cross-platform build requested but buildx is unavailable; build may fail."
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

        # For same-platform builds, buildx can still be beneficial on some systems
        # But default to regular Docker build for maximum compatibility
        self.logger.debug(
            "Same-platform build (%s), using regular Docker build for compatibility",
            self.get_target_platform(),
        )
        return False

    def _get_host_platform(self) -> str:
        """
        Get the host platform without configuration overrides.

        Returns:
            str: Host platform string (e.g., 'linux/amd64', 'linux/arm64')
        """
        machine = platform.machine().lower()
        return "linux/arm64" if machine in ["arm64", "aarch64"] else "linux/amd64"

    def validate_build_mode_for_architecture(self, build_mode: str) -> str:
        """
        Validate BUILD_MODE compatibility with host architecture.

        Advanced build modes (rel-lto, debug-asan, release-static-pgo) require x86 architecture.
        Non-x86 architectures fall back to empty BUILD_MODE for compatibility.

        Args:
            build_mode: The requested build mode

        Returns:
            str: Validated build mode (empty string if incompatible with architecture)
        """
        if not build_mode:
            return build_mode

        self.logger.debug(
            "Validating BUILD_MODE='%s' for current architecture '%s'",
            build_mode,
            platform.machine(),
        )

        # Check if we're on x86 architecture
        machine = platform.machine().lower()
        is_x86 = machine in ["x86_64", "amd64", "x86", "i386", "i686"]

        advanced_modes = ["rel-lto", "debug-asan", "release-static-pgo"]

        if build_mode in advanced_modes and not is_x86:
            self.logger.warning(
                "BUILD_MODE='%s' requires x86 architecture but detected '%s'. "
                "Falling back to default build mode for compatibility.",
                build_mode,
                machine,
            )
            return ""  # Fall back to default/legacy build

        return build_mode

    def _build_with_buildx(
        self,
        impl_name: str,
        dockerfile_path: Path,
        context_path: Path,
        build_args: Dict[str, Any],
        experiment_id: Optional[str] = None,
        image_tag: Optional[str] = None,
    ) -> Optional[str]:
        """
        Build a Docker image using Docker Buildx for cross-platform builds.

        Args:
            impl_name: The name of the implementation
            version: The version of the implementation
            dockerfile_path: The path to the Dockerfile
            context_path: The path to the build context
            config: Configuration dictionary containing build parameters
            tag_version: The tag version for the Docker image. Defaults to "latest"
            target_platform: Target platform override. If None, uses detected platform
            experiment_id: Optional experiment ID for tracking

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

            # Get buildx configuration - use Docker's default builder instead of custom name
            # Resolve which buildx builder to use
            builder_name = "default"
            if (
                hasattr(self, "global_config")
                and self.global_config
                and hasattr(self.global_config, "docker")
                and hasattr(self.global_config.docker, "buildx_builder")
            ):
                builder_name = self.global_config.docker.buildx_builder
                # 🔄 NEW: ensure CLI context matches builder context
                try:
                    strategy = (
                        getattr(
                            self.global_config.docker,
                            "docker_context_strategy",
                            "switch-cli-context",
                        )
                        if hasattr(self, "global_config")
                        and self.global_config
                        and hasattr(self.global_config, "docker")
                        else "switch-cli-context"
                    )
                    self.logger.debug(
                        "Ensuring Docker CLI context matches buildx builder '%s' with strategy '%s'",
                        builder_name,
                        strategy,
                    )
                    ensure_builder_context(builder=builder_name, strategy=strategy)
                except subprocess.CalledProcessError as ctx_err:
                    # Non-fatal: continue but make it visible in logs
                    self.logger.warning(
                        "Docker context reconciliation for builder '%s' failed (%s); continuing with current context.",
                        builder_name,
                        ctx_err,
                    )

            # For non-default custom builders, make sure they exist
            if builder_name != "default" and not self._setup_buildx_builder(
                builder_name
            ):
                raise DockerBuildException(
                    message=f"Failed to setup buildx builder: {builder_name}",
                    image_name=impl_name,
                    dockerfile=str(dockerfile_path),
                    build_error="Buildx builder setup failed",
                )

            self.logger.info(
                "Building Docker image '%s' with buildx for platform '%s'",
                image_tag,
                self.get_target_platform(),
            )

            # Calculate relative path from context to dockerfile
            # For buildx, prefer Dockerfile.buildkit or multistage variants if they exist
            buildkit_candidates = [
                Path(dockerfile_path).parent / "Dockerfile.buildkit",
                Path(dockerfile_path).parent / "Dockerfile.multistage",
                dockerfile_path,  # fallback to original
            ]

            selected_dockerfile = None
            for candidate in buildkit_candidates:
                if candidate.exists():
                    selected_dockerfile = candidate
                    self.logger.debug(
                        "Selected Dockerfile for buildx: %s", selected_dockerfile
                    )
                    break

            if selected_dockerfile is None:
                # This should never happen since dockerfile_path is the fallback
                raise DockerBuildException(
                    message=f"No suitable Dockerfile found for buildx build",
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
                # "--builder",
                # builder_name,
                "--platform",
                self.get_target_platform(),
                "--file",
                str(relative_dockerfile_path),
                "--tag",
                image_tag,
                "--debug",
                "--load",  # Load the image into local Docker daemon
                str(context_path),
            ]

            # Add build arguments with proper shell escaping for JSON values
            for key, value in build_args.items():
                # For complex values like JSON, pass them as separate arguments to avoid shell parsing issues
                buildx_cmd.extend(["--build-arg", f"{key}={value}"])

            # Add network mode
            buildx_cmd.extend(["--network", "host"])

            # Force rebuild if configured
            # force_build = getattr(self.global_config.docker, 'force_build_docker_image', True) if hasattr(self, 'global_config') and self.global_config and hasattr(self.global_config, 'docker') else True
            # if force_build:
            #     buildx_cmd.append("--no-cache")

            self.logger.debug("Executing buildx command: %s", " ".join(buildx_cmd))

            # Track build start time
            build_start_time = time.time()

            # Execute buildx build
            result = subprocess.run(
                buildx_cmd, cwd=str(context_path), capture_output=True, text=True
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

            build_logs = iter(build_logs)  # Convert to iterator for logging

            # Use existing docker logger for consistency
            log_f = None
            if self.build_log_file:
                buildx_tag = image_tag.replace(":", "_").replace("/", "_") + "_buildx"
                log_filename = self._get_build_log_path(buildx_tag)
                self.logger.debug("Opening buildx log file at: %s", log_filename)
                self.logger.debug("Current working directory: %s", os.getcwd())
                log_f = open(log_filename, "w")

            self.docker_logger.log_docker_output(
                build_logs, f"Building Docker image '{image_tag}' with buildx", log_f
            )

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

            # Get image ID from local Docker daemon (buildx doesn't return image ID directly)
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
        """
        Build a Docker image for the specified implementation.
        Args:
            impl_name (str): The name of the implementation.
            version (str): The version of the implementation.
            dockerfile_path (Path): The path to the Dockerfile.
            context_path (Path): The path to the build context.
            config (Dict[str, Any]): Configuration dictionary containing build parameters.
            tag_version (str, optional): The tag version for the Docker image. Defaults to "latest".
            build_image_force (bool, optional): Force rebuild of the Docker image even if it already exists. Defaults to False.
        Returns:
            Optional[str]: The tag of the built Docker image, or None if the build was skipped.
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

            # Construct image tag with mode information
            image_tag = self.generate_image_tag(
                impl_name=impl_name,
                version=version,
                tag_version=tag_version,
                build_mode=build_mode,
                runtime_mode=runtime_mode,
                target_platform=self.get_target_platform(),
            )

            # Check build cache first
            dependencies = config.get("dependencies", {})
            build_args = {
                "VERSION": config.get("commit", "production"),
                "DEPENDENCIES": json.dumps(dependencies) if dependencies else "[]",
                "BUILD_MODE": build_mode,
                "RUNTIME_MODE": config.get("runtime_mode", "minimal"),
                "TARGETPLATFORM": self.get_target_platform(),
                "BASE_IMAGE": self.generate_image_tag(
                    impl_name="panther_base_service",
                    version="",
                    tag_version="latest",
                    build_mode="",
                    runtime_mode=runtime_mode,
                    target_platform=self.get_target_platform(),
                ),
            }

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

            # Check cache and handle cache logic
            force_build = (
                getattr(self.global_config.docker, "force_build_docker_image", True)
                if hasattr(self, "global_config")
                and self.global_config
                and hasattr(self.global_config, "docker")
                else True
            )

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
                    return cached_result

            log_f = None
            # Open the build log file if specified
            if self.build_log_file:
                log_filename = self._get_build_log_path(image_tag)
                log_f = open(log_filename, "w")

            # Calculate relative path from context to dockerfile for Docker API
            relative_dockerfile_path = Path(dockerfile_path).relative_to(context_path)

            # Track build start time for cache
            _build_start_time = time.time()

            # Check if we should use buildx for this build
            if self._should_use_buildx():
                # Use buildx for cross-platform builds
                return self._build_with_buildx(
                    impl_name=impl_name,
                    dockerfile_path=dockerfile_path,
                    context_path=context_path,
                    build_args=build_args,
                    experiment_id=experiment_id,
                    image_tag=image_tag,
                )

            # Use regular Docker build for same-platform builds
            self.logger.info(
                "Building Docker image '%s' using standard Docker build for platform '%s'",
                image_tag,
                self.get_target_platform(),
            )
            image, build_logs = self.client.images.build(
                path=str(context_path),
                dockerfile=str(relative_dockerfile_path),
                tag=image_tag,
                network_mode="host",
                buildargs=build_args,
                platform=self.get_target_platform(),  # Auto-detected platform
                nocache=force_build,  # Force build if specified
                # squash=True,  # Squash layers to reduce image size (experimental)
                # pull=True,  # Always pull latest base images
            )

            self.docker_logger.log_docker_output(
                build_logs, f"Building Docker image '{image_tag}'", log_f
            )
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

            self.logger.info(
                "Successfully built Docker image '%s' with context '%s' and build args '%s'",
                image_tag,
                context_path,
                build_args,
            )

            # Clean up any dangling images that were created during this build
            if remove_dangling:
                self.logger.info("Removing dangling images after build.")
                self.remove_dangling_images()

            return image_tag
        except PantherException:
            # Re-raise PantherExceptions (from fast-fail validation) without modification
            raise
        except BuildError as e:
            # Use impl_name if image_tag not yet defined
            tag_for_error = locals().get("image_tag", f"{impl_name}_unknown")
            log_file = locals().get("log_f")
            self.logger.error(
                "Failed to build Docker image '%s' : %s", tag_for_error, e
            )
            self.docker_logger.log_and_raise_build_exception(
                impl_name, dockerfile_path, tag_for_error, e, log_file
            )
        except Exception as e:
            # Handle unexpected errors with fast-fail handler
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
    ):
        """
        Generate Docker image tag with build and runtime mode differentiation.

        Args:
            impl_name: Implementation name (e.g., 'picoquic')
            version: Version string (e.g., 'v1.0' or 'latest')
            tag_version: Tag version (e.g., 'latest', 'stable')
            build_mode: Build mode ('', 'debug-asan', 'rel-lto', 'release-static-pgo')
            runtime_mode: Runtime mode ('minimal', 'debug', 'profile')

        Returns:
            str: Complete image tag

        Examples:
            - picoquic_v1.0_debug-asan_debug:latest (build_mode + runtime_mode)
            - picoquic_v1.0__minimal:latest (empty build_mode, minimal runtime)
            - picoquic_v1.0_rel-lto_profile:latest (both modes specified)
            - picoquic:latest (no version, minimal runtime)
        """

        # Build mode suffix (empty string results in no suffix)
        build_suffix = f"-{build_mode}" if build_mode else ""

        # Runtime mode suffix (minimal is default, so no suffix needed)
        runtime_suffix = (
            f"-{runtime_mode}" if runtime_mode and runtime_mode != "minimal" else ""
        )

        platform_suffix = f"-{target_platform}" if target_platform else ""

        # Construct base name with version
        base_name = f"{impl_name}-{version}" if version else impl_name
        # Combine all parts
        full_tag = (
            f"{base_name}:{tag_version}{build_suffix}{runtime_suffix}{platform_suffix}"
        )

        # Sanitize tag (Docker tags have character restrictions)
        return self._sanitize_docker_tag(full_tag)

    def _sanitize_docker_tag(self, tag: str) -> str:
        """
        Sanitize Docker tag to meet Docker naming requirements.

        Docker tag rules:
        - Lowercase letters, digits, underscores, periods, dashes
        - Cannot start with period or dash
        - Max 128 characters
        """
        import re

        # Convert to lowercase and replace invalid characters (allow colon for tag separator)
        sanitized = re.sub(r"[^a-z0-9._:-]", "-", tag.lower())

        # Ensure doesn't start with period or dash
        sanitized = re.sub(r"^[.-]+", "", sanitized)

        # Truncate if too long (leave room for registry prefix)
        if len(sanitized) > self.MAX_TAG_LENGTH:
            # Keep the tag version part intact
            parts = sanitized.split(":")
            if len(parts) == 2:
                name_part, tag_part = parts
                max_name_length = self.MAX_TAG_LENGTH - len(tag_part) - 1  # -1 for ':'
                if len(name_part) > max_name_length:
                    name_part = name_part[:max_name_length]
                sanitized = f"{name_part}:{tag_part}"
            else:
                sanitized = sanitized[: self.MAX_TAG_LENGTH]

        return sanitized

    def _validate_build_prerequisites(
        self,
        impl_name: str,
        dockerfile_path: Path,
        context_path: Path,
        config: Dict[str, Any],
    ) -> None:
        """
        Validate all prerequisites before starting Docker build operation.

        Args:
            impl_name: The name of the implementation
            dockerfile_path: Path to the Dockerfile
            context_path: Path to the build context
            config: Configuration dictionary containing build parameters

        Raises:
            PantherException: If any validation fails
        """
        # Validate implementation name
        if not impl_name or not isinstance(impl_name, str):
            raise PantherException(
                message=f"Invalid implementation name: {impl_name}",
                severity=ErrorSeverity.CRITICAL,
                category=ErrorCategory.DOCKER_BUILD,
                context={"impl_name": impl_name},
            )

        # Validate Dockerfile exists and is readable
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

        # Validate build context exists and is accessible
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

        # Validate Docker daemon is available
        if not self.is_docker_available():
            raise PantherException(
                message="Docker daemon is not available",
                severity=ErrorSeverity.CRITICAL,
                category=ErrorCategory.DOCKER_RUNTIME,
                context={"impl_name": impl_name},
            )

        # Validate configuration
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

    def push_image_to_registry(self, image_tag, registry_image_tag, registry_url, tag):
        # Tag the image for the registry
        image = self.client.images.get(image_tag)
        image.tag(registry_image_tag)
        self.logger.debug("Tagged image '%s' as '%s'", image_tag, registry_image_tag)

        # Push the image
        push_logs = self.client.images.push(
            registry_url, tag=tag, stream=True, decode=True
        )
        for chunk in push_logs:
            if "status" in chunk:
                self.logger.debug("Pushing: %s", chunk["status"])
            elif "error" in chunk:
                self.logger.error("Pushing Error: %s", chunk["error"])
                return False
        self.logger.info(
            "Successfully pushed image '%s' to registry.", registry_image_tag
        )
        return True

    def image_exists(self, image_tag: str) -> bool:
        """
        Checks if a Docker image with the given tag exists locally.
        Delegates to DockerImageCache for resilient image checking.

        :param image_tag: Tag of the Docker image.
        :return: True if exists, else False.
        """
        return self.image_cache.image_exists(image_tag, self.client)

    def container_exists(self, container_name: str) -> bool:
        """
        Check if a Docker container with the given name exists.
        Args:
            container_name (str): The name of the Docker container to check.
        Returns:
            bool: True if the container exists, False otherwise.
        Raises:
            DockerException: If there is an error while checking the container existence.
        """
        if self.client is None:
            self.logger.error(
                "Docker client is not available. Cannot check if container exists."
            )
            return False

        try:
            self.client.containers.get(container_name)
            self.logger.debug("Container '%s' exists.", container_name)
            return True
        except NotFound:
            self.logger.debug("Container '%s' does not exist.", container_name)
            return False
        except DockerException as e:
            self.logger.error(
                "Error checking container existence '%s': %s", container_name, e
            )
            return False

    def create_network(
        self,
        network_name: str,
        driver: str = "bridge",
        subnet: str = "172.27.1.0/24",
        gateway: str = "172.27.1.1",
    ) -> bool:
        """
        Creates a Docker network with the specified parameters.
        Args:
            network_name (str): The name of the network to create.
            driver (str, optional): The network driver to use. Defaults to "bridge".
            subnet (str, optional): The subnet for the network. Defaults to "172.27.1.0/24".
            gateway (str, optional): The gateway for the network. Defaults to "172.27.1.1".
        Returns:
            bool: True if the network was created successfully or already exists, False otherwise.
        Raises:
            DockerException: If there is an error creating the network.
            Exception: If there is an unexpected error.
        """
        if self.client is None:
            self.logger.error("Docker client is not available. Cannot create network.")
            return False

        try:
            if self.network_exists(network_name):
                self.logger.info("Network '%s' already exists.", network_name)
                return True

            self.client.networks.create(
                name=network_name,
                driver=driver,
                ipam=docker.service_types.IPAMConfig(
                    pool_configs=[
                        docker.service_types.IPAMPool(subnet=subnet, gateway=gateway)
                    ]
                ),
            )
            self.logger.info("Network '%s' created successfully.", network_name)
            return True
        except DockerException as e:
            self.logger.error("Failed to create network '%s': %s", network_name, e)
            return False
        except Exception as e:
            self.logger.error(
                "Unexpected error creating network '%s': %s", network_name, e
            )
            return False

    def network_exists(self, network_name: str) -> bool:
        """
        Check if a Docker network exists.
        Args:zdzd
            network_name (str): The name of the Docker network to check.
        Returns:
            bool: True if the network exists, False otherwise.
        Logs:
            Debug: Logs whether the network exists or not.
            Error: Logs any DockerException encountered during the check.
        """
        if self.client is None:
            self.logger.error(
                "Docker client is not available. Cannot check if network exists."
            )
            return False

        try:
            self.client.networks.get(network_name)
            self.logger.debug("Network '%s' exists.", network_name)
            return True
        except NotFound:
            self.logger.debug("Network '%s' does not exist.", network_name)
            return False
        except DockerException as e:
            self.logger.error(
                "Error checking network existence '%s': %s", network_name, e
            )
            return False

    def cleanup_unused_images(self, keep_tags: List[str]):
        """
        Removes Docker images that are not in the keep_tags list.
        Delegates to DockerImageCache for cache-aware cleanup.

        :param keep_tags: List of image tags to retain.
        """
        self.image_cache.cleanup_unused_images(keep_tags, self.client)

    def remove_dangling_images(self):
        """
        Removes dangling Docker images (images with <none>:<none> tag).
        Delegates to DockerImageCache for cache-aware dangling image removal.

        Returns:
            bool: True if successful, False if an error occurred
        """
        return self.image_cache.remove_dangling_images(self.client)

    def set_experiment_context(self, experiment_context):
        """
        Set the experiment context for DockerBuilder.

        This allows DockerBuilder to organize build logs and other outputs
        within the context of a specific experiment.

        Args:
            experiment_context: The experiment context object containing experiment metadata
        """
        self.experiment_context = experiment_context
        self.logger.debug("Experiment context set for DockerBuilder.")

    @classmethod
    def reset_singleton(cls):
        """
        Reset the singleton instance.

        This method should only be used in testing scenarios where
        a fresh instance is needed.
        """
        cls._instance = None
        cls._initialized = False

    @classmethod
    def get_instance(
        cls,
        build_log_file: bool = True,
        enable_cache: bool = True,
        global_config=None,
        experiment_context=None,
    ) -> "DockerBuilder":
        """
        Get the singleton instance of DockerBuilder.

        This method returns the singleton instance and allows updating
        configuration parameters even if the instance already exists.

        Args:
            build_log_file: Whether to create log files for Docker builds
            enable_cache: Whether to enable Docker build caching
            global_config: Global configuration object containing Docker settings
            experiment_context: Optional experiment context for organizing build logs

        Returns:
            The singleton DockerBuilder instance (with updated parameters if provided)
        """
        return cls(
            build_log_file=build_log_file,
            enable_cache=enable_cache,
            global_config=global_config,
            experiment_context=experiment_context,
        )
