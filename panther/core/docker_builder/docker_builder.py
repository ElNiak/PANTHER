"""DockerBuilder - Singleton Docker Management System.

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

import logging
import os
import threading
from typing import Optional, Set

import docker
from docker.errors import DockerException

from panther.core.docker_builder.utils.context_helper import _ensure_docker_host
from panther.core.docker_builder.utils.docker_output_parser import DockerOutputParser
from panther.core.exceptions.error_handler_mixin import ErrorHandlerMixin
from panther.core.utils.logging_mixin import LoggerMixin

from .buildx_operations import BuildxOperationsMixin
from .caching.docker_build_cache_mixin import DockerBuildCacheMixin
from .caching.docker_image_cache import DockerImageCache
from .image_operations import ImageOperationsMixin
from .platform_detection import PlatformDetectionMixin


class DockerBuilder(
    PlatformDetectionMixin,
    BuildxOperationsMixin,
    ImageOperationsMixin,
    DockerBuildCacheMixin,
    LoggerMixin,
    ErrorHandlerMixin,
):
    """Manage Docker operations with singleton pattern and advanced caching.

    A singleton Docker management system that provides comprehensive Docker operations
    including image building, container management, and network configuration. Implements
    intelligent caching, cross-platform builds, and resilient fallback mechanisms.

    The singleton pattern ensures single Docker client connection per application,
    shared Docker build cache across components, and consistent configuration.

    Attributes:
        _instance: Singleton instance holder
        _initialized: Singleton initialization flag
        MAX_TAG_LENGTH: Maximum Docker tag length (100 chars)
        client: Docker client connection
        image_cache: Docker image cache manager
        docker_logger: Docker output parser for build logs
    """

    _instance = None
    _initialized = False
    MAX_TAG_LENGTH = 100  # Maximum Docker tag length (leave room for registry prefix)
    _session_built_tags: Set[str] = set()
    _session_built_tags_lock = threading.Lock()

    def __new__(cls, *args, **kwargs):
        """Create or return the singleton instance."""
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
        """Initialize DockerBuilder singleton with configuration options.

        Args:
            build_log_file: Enable Docker build log file creation.
            enable_cache: Enable Docker build caching for faster rebuilds.
            global_config: Global configuration object containing Docker settings.
            experiment_context: Experiment context for organizing build logs.

        Raises:
            DockerException: If Docker daemon connection fails (graceful fallback enabled)
        """
        # Allow parameter updates even for existing instances
        if getattr(self.__class__, "_initialized", False):
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
        self.__init_logger__("docker_operations")
        self.__class__._initialized = True
        with DockerBuilder._session_built_tags_lock:
            DockerBuilder._session_built_tags = set()
        self.logger.info("Initializing DockerBuilder singleton instance")

        self.plugins_dir = None
        self.build_log_file = build_log_file
        self.client = None
        self.global_config = global_config
        self.experiment_context = experiment_context

        # Platform detection cache (populated lazily on first access)
        self._cached_host_platform: Optional[str] = None
        self._cached_target_platform: Optional[str] = None
        self._cached_buildx_available: Optional[bool] = None
        self._platform_detection_logged: bool = False

        # Initialize Docker image cache with platform-aware caching
        target_platform = self.get_target_platform()
        self.image_cache = DockerImageCache(
            cache_ttl=300,
            retry_count=2,
            retry_delay=1.0,
            target_platform=target_platform,
        )

        self.docker_logger = DockerOutputParser()

        if self.global_config and (
            self.global_config.docker.force_build_docker_image
            or getattr(self.global_config.docker, "no_docker_cache", False)
        ):
            enable_cache = False
            self.logger.warning("Force build enabled, disabling Docker build cache.")

        self.enable_cache(enable_cache)
        self._cache_enabled = enable_cache
        self.logger.info(
            f"Docker build cache: {'enabled' if enable_cache else 'disabled'}"
        )
        try:
            os.environ["DOCKER_BUILDKIT"] = "1"
            os.environ["COMPOSE_DOCKER_CLI_BUILD"] = "1"
            os.environ["DOCKER_PY_VERBOSE"] = "1"
            logging.getLogger("docker").setLevel(logging.DEBUG)
            logging.getLogger("requests").setLevel(logging.DEBUG)
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
            self.logger.debug("Detected host platform: %s", self._get_host_platform())

            if self.client and enable_cache:
                self.image_cache.set_docker_client(self.client)

                if hasattr(self, "get_cache_stats"):
                    stats = self.get_cache_stats()
                    self.logger.info(
                        f"Docker registry loaded with {stats['registry_stats']['total_resources']} resources"
                    )

                cache_stats = self.image_cache.get_cache_stats()
                self.logger.info(
                    f"Docker image cache initialized: {cache_stats['total_images']} images, "
                    f"fresh={cache_stats['cache_fresh']}"
                )
        except DockerException as e:
            self.logger.error(
                "Failed to connect to Docker daemon: %s, check your DOCKER_HOST", e
            )
            self.logger.warning("Docker daemon unavailable, running in cache-only mode")

    def update_parameters(
        self, build_log_file, global_config, experiment_context, updated_params
    ):
        """Update singleton configuration parameters if they have changed."""
        if hasattr(self, "build_log_file") and self.build_log_file != build_log_file:
            self.build_log_file = build_log_file
            updated_params.append(f"build_log_file={build_log_file}")
        enable_cache = True
        if global_config and getattr(self, "global_config", None) != global_config:
            self.global_config = global_config
            self._cached_target_platform = None
            self._platform_detection_logged = False
            updated_params.append("global_config=<updated>")

            if hasattr(global_config, "docker") and (
                getattr(global_config.docker, "force_build_docker_image", False)
                or getattr(global_config.docker, "no_docker_cache", False)
            ):
                enable_cache = False
                self.logger.warning(
                    "Force build enabled via updated config, disabling Docker build cache."
                )
        elif self.global_config and (
            self.global_config.docker.force_build_docker_image
            or getattr(self.global_config.docker, "no_docker_cache", False)
        ):
            enable_cache = False
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
        """Check if Docker daemon is available and responsive."""
        if self.client is None:
            return False
        try:
            self.client.ping()
            return True
        except DockerException:
            return False

    def _get_build_log_path(self, image_tag: str) -> str:
        """Generate appropriate log path for Docker build logs.

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
            base_dir = self.experiment_context.experiment_dir

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
                base_dir = (
                    self.experiment_context.experiment_dir
                    / self.experiment_context.test_name
                )
                self.logger.debug("Creating test-specific directory: %s", base_dir)

            docker_logs_dir = base_dir / "docker_builds"
            docker_logs_dir.mkdir(parents=True, exist_ok=True)
            log_path = str(docker_logs_dir / log_filename)
            self.logger.debug(
                "Docker build log will be written to test-specific output: %s", log_path
            )
            return log_path
        else:
            self.logger.debug(
                "No experiment context available, using current directory for build log: %s",
                log_filename,
            )
            return log_filename

    def set_experiment_context(self, experiment_context):
        """Set the experiment context for DockerBuilder."""
        self.experiment_context = experiment_context
        self.logger.debug("Experiment context set for DockerBuilder.")

    @classmethod
    def reset_singleton(cls):
        """Reset the singleton instance (testing only)."""
        cls._instance = None
        cls._initialized = False
        with cls._session_built_tags_lock:
            cls._session_built_tags = set()

    @classmethod
    def mark_session_built(cls, image_tag: str) -> None:
        """Record that an image was freshly built in this session (thread-safe)."""
        with cls._session_built_tags_lock:
            cls._session_built_tags.add(image_tag)

    @classmethod
    def was_built_this_session(cls, image_tag: str) -> bool:
        """Check if an image was already freshly built in this session (thread-safe)."""
        with cls._session_built_tags_lock:
            return image_tag in cls._session_built_tags

    @classmethod
    def get_instance(
        cls,
        build_log_file: bool = True,
        enable_cache: bool = True,
        global_config=None,
        experiment_context=None,
    ) -> "DockerBuilder":
        """Get the singleton instance of DockerBuilder."""
        return cls(
            build_log_file=build_log_file,
            enable_cache=enable_cache,
            global_config=global_config,
            experiment_context=experiment_context,
        )
