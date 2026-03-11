"""Docker Operations Mixin.

This module provides a mixin class for Docker operations commonly used by service managers,
eliminating duplication of Docker image preparation and management logic.

Unified to use only DockerBuilder, removing the previous duplication with DockerUtils.
"""

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Dict, Optional, Union

from docker.errors import DockerException

from panther.core.utils.logging_mixin import LoggerMixin

if TYPE_CHECKING:
    from panther.core.docker_builder import DockerBuilder


class DockerOperationError(Exception):
    """Exception raised when Docker operations fail."""

    pass


class DockerOperationsMixin(LoggerMixin):
    """Mixin that provides common Docker operations for service managers.

    This mixin reduces duplication by providing standard implementations of:
    - Docker image preparation
    - Image existence checking
    - Build context management
    - Container lifecycle operations

    Now unified to use DockerBuilder throughout for consistency.
    """

    def __init__(self, *args, **kwargs):
        """Initialize mixin and set up Docker builder reference."""
        super().__init__(*args, **kwargs)
        self._docker_builder = None
        self.global_config = getattr(self, "global_config", None)

    @property
    def docker_builder(self) -> "DockerBuilder":
        """Lazy initialization of DockerBuilder instance.

        Returns the singleton DockerBuilder instance, ensuring all Docker operations
        across the application share the same client connection and configuration.
        """
        if self._docker_builder is None:
            from panther.core.docker_builder.docker_builder import DockerBuilder

            self._docker_builder = DockerBuilder.get_instance(
                global_config=getattr(self, "global_config", None),
                experiment_context=getattr(self, "experiment_context", None),
            )
        return self._docker_builder

    def prepare_docker_image(
        self,
        image_name: Optional[str] = None,
        dockerfile_path: Optional[Union[str, Path]] = None,
        build_context: Optional[Union[str, Path]] = None,
        build_args: Optional[Dict[str, str]] = None,
        no_cache: bool = True,
    ) -> bool:
        """Prepare a Docker image by building it if it doesn't exist.

        This method provides the standard prepare() functionality used by most
        service managers, with additional flexibility.

        Now emits Docker build events for proper tracking and monitoring.

        Args:
            image_name: Docker image name (defaults to self.docker_image_name)
            dockerfile_path: Path to Dockerfile (defaults to self.docker_file_path)
            build_context: Build context directory (defaults to dockerfile directory)
            build_args: Build arguments to pass to Docker
            force_rebuild: Force rebuild even if image exists
            no_cache: Whether to disable Docker build cache

        Returns:
            bool: True if image is ready (built or already exists)

        Raises:
            DockerOperationError: If Docker operations fail
            AttributeError: If required attributes are missing
        """
        self.logger.debug(
            "Preparing Docker image: %s, dockerfile: %s, context: %s",
            image_name,
            dockerfile_path,
            build_context,
        )
        # Use instance attributes if not provided
        if image_name is None:
            if not hasattr(self, "docker_image_name"):
                raise AttributeError(
                    f"{self.__class__.__name__} must have 'docker_image_name' attribute"
                )
            image_name = self.docker_image_name

        if dockerfile_path is None:
            if not hasattr(self, "docker_file_path"):
                raise AttributeError(
                    f"{self.__class__.__name__} must have 'docker_file_path' attribute"
                )
            dockerfile_path = self.docker_file_path

        # Convert to Path object
        dockerfile_path = Path(dockerfile_path)

        # Default build context to dockerfile directory
        if build_context is None:
            build_context = dockerfile_path.parent

        # Check if we should build Docker images based on config
        # TODO: use same idea htan _check_and_add_existing_image
        force_build = (
            self.global_config.docker.force_build_docker_image
            if (
                self.global_config
                and hasattr(self.global_config, "docker")
                and hasattr(self.global_config.docker, "force_build_docker_image")
            )
            else True
        )

        # Check if image already exists
        image_exists = self.docker_builder.image_exists(image_name)

        # Skip build if image already exists and force_build is False
        if image_exists and not force_build:
            self.log_with_context(
                logging.INFO,
                "Docker image already exists, skipping build",
                image=image_name,
            )
            return True

        # Skip build if force_build is False but image doesn't exist - this is wrong logic!
        # We should always build if image doesn't exist, regardless of force_build setting
        if not image_exists:
            self.logger.debug(
                f"🔍 BUILD_TRIGGER: Image '{image_name}' does not exist, building it..."
            )
        elif force_build:
            self.logger.debug(
                f"🔍 BUILD_TRIGGER: Force build enabled, rebuilding '{image_name}'..."
            )

        # Continue with build...

        # Emit Docker build started event
        self.emit_docker_build_started(str(dockerfile_path), image_name)

        # Build the image using DockerBuilder
        self.log_operation_start(
            "Docker image build", image=image_name, context=str(build_context)
        )
        try:
            # Create a config dict compatible with DockerBuilder.build_image
            config = {
                "dependencies": build_args or {},
                "commit": "master",  # Default value
            }

            if success_tag := self.docker_builder.build_image(
                impl_name=image_name.split(":")[0],  # Extract name part
                version="",
                dockerfile_path=dockerfile_path,
                context_path=Path(build_context),
                config=config,
                tag_version="latest",
            ):
                self.log_operation_complete(
                    "Docker image build", image=image_name, tag=success_tag
                )
                # Emit Docker build completed event with success
                self.emit_docker_build_completed(image_name, True)
                return True
            else:
                self.log_operation_failed(
                    "Docker image build",
                    Exception("Build returned no success tag"),
                    image=image_name,
                )
                # Emit Docker build completed event with failure
                self.emit_docker_build_completed(
                    image_name, False, "Docker build failed"
                )
                return False

        except (DockerException, Exception) as e:
            self.logger.error(f"Docker operation failed: {e}")
            # Emit Docker build completed event with failure
            self.emit_docker_build_completed(image_name, False, str(e))
            raise DockerOperationError(f"Docker build failed: {e}")

    def prepare(self) -> None:
        """Standard prepare method that builds Docker image if needed.

        This is the most common implementation across service managers.
        Override this method if you need custom preparation logic.
        """
        self.prepare_docker_image()

    def ensure_docker_available(self) -> None:
        """Ensure Docker is available and running.

        Raises:
            DockerOperationError: If Docker is not available
        """
        try:
            # Test Docker connection by pinging
            self.docker_builder.is_docker_available()
            self.logger.info("Docker is available and running.")
        except DockerException as e:
            raise DockerOperationError(
                f"Docker is not available: {e}. Please ensure Docker is installed and running."
            )
