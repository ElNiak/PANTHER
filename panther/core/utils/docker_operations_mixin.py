"""
Docker Operations Mixin

This module provides a mixin class for Docker operations commonly used by service managers,
eliminating duplication of Docker image preparation and management logic.
"""

from typing import Optional, Any, TYPE_CHECKING
from pathlib import Path
import os

from panther.core.utils.logging_mixin import LoggerMixin
from panther.core.utils.docker_utils import DockerUtils, DockerOperationError
from panther.core.command_processor.command_event_mixin import CommandEventMixin

if TYPE_CHECKING:
    from panther.plugins.plugin_manager import PluginManager


class DockerOperationsMixin(LoggerMixin):
    """
    Mixin that provides common Docker operations for service managers.

    This mixin reduces duplication by providing standard implementations of:
    - Docker image preparation
    - Image existence checking
    - Build context management
    - Container lifecycle operations
    """

    def prepare_docker_image(
        self,
        image_name: str | None = None,
        dockerfile_path: str | Path | None = None,
        build_context: str | Path | None = None,
        build_args: dict[str, str] | None = None,
        force_rebuild: bool = False,
        no_cache: bool = False,
    ) -> bool:
        """
        Prepare a Docker image by building it if it doesn't exist.

        This method provides the standard prepare() functionality used by most
        service managers, with additional flexibility.

        Now emits Docker build events for proper tracking and monitoring.

        Args:
            image_name: Docker image name (defaults to self.docker_image_name)
            dockerfile_path: Path to Dockerfile (defaults to self.docker_file_path)
            build_context: Build context directory (defaults to dockerfile directory)
            build_args: Build arguments to pass to Docker
            force_rebuild: Force rebuild even if image exists
            no_cache: Disable Docker build cache

        Returns:
            bool: True if image is ready (built or already exists)

        Raises:
            DockerOperationError: If Docker operations fail
            AttributeError: If required attributes are missing
        """
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

        # Check if image already exists
        if not force_rebuild and DockerUtils.image_exists(image_name):
            self.logger.info(f"Docker image '{image_name}' already exists")
            return True

        # Emit Docker build started event
        self.emit_docker_build_started(str(dockerfile_path), image_name)

        # Build the image
        self.logger.info(f"Building Docker image '{image_name}'")
        try:
            success = DockerUtils.build_image(
                dockerfile_path=dockerfile_path,
                image_name=image_name,
                build_context=build_context,
                build_args=build_args,
                no_cache=no_cache,
            )

            if success:
                self.logger.info(f"Successfully built Docker image '{image_name}'")
                # Emit Docker build completed event with success
                self.emit_docker_build_completed(image_name, True)
            else:
                self.logger.error(f"Failed to build Docker image '{image_name}'")
                # Emit Docker build completed event with failure
                self.emit_docker_build_completed(image_name, False, "Docker build failed")

            return success

        except DockerOperationError as e:
            self.logger.error(f"Docker operation failed: {e}")
            # Emit Docker build completed event with failure
            self.emit_docker_build_completed(image_name, False, str(e))
            raise

    def prepare(self) -> None:
        """
        Standard prepare method that builds Docker image if needed.

        This is the most common implementation across service managers.
        Override this method if you need custom preparation logic.
        """
        self.prepare_docker_image()

    def ensure_docker_available(self) -> None:
        """
        Ensure Docker is available and running.

        Raises:
            DockerOperationError: If Docker is not available
        """
        if not DockerUtils.is_docker_available():
            raise DockerOperationError(
                "Docker is not available. Please ensure Docker is installed and running."
            )

    def remove_docker_image(self, image_name: str | None = None, force: bool = False) -> bool:
        """
        Remove a Docker image.

        Args:
            image_name: Image name (defaults to self.docker_image_name)
            force: Force removal even if container is using it

        Returns:
            bool: True if removal succeeded
        """
        if image_name is None:
            if not hasattr(self, "docker_image_name"):
                self.logger.warning("No docker_image_name attribute found")
                return False
            image_name = self.docker_image_name

        return DockerUtils.remove_image(image_name, force=force)

    def get_docker_image_tag(self) -> str:
        """
        Get the Docker image tag for this service.

        Returns:
            str: Docker image tag

        Raises:
            AttributeError: If docker_image_name is not set
        """
        if not hasattr(self, "docker_image_name"):
            raise AttributeError(
                f"{self.__class__.__name__} must have 'docker_image_name' attribute"
            )
        return self.docker_image_name

    def set_docker_build_args(self, build_args: dict[str, str]) -> None:
        """
        Set Docker build arguments for future builds.

        Args:
            build_args: Dictionary of build arguments
        """
        if not hasattr(self, "_docker_build_args"):
            self._docker_build_args = {}
        self._docker_build_args.update(build_args)

    def get_docker_build_args(self) -> dict[str, str]:
        """
        Get Docker build arguments.

        Returns:
            dict: Build arguments
        """
        return getattr(self, "_docker_build_args", {})


class DockerComposeOperationsMixin(DockerOperationsMixin):
    """
    Extended mixin for Docker Compose operations.

    Provides additional functionality specific to Docker Compose environments.
    """

    def prepare_for_compose(
        self, compose_project_name: str | None = None, network_name: str | None = None
    ) -> None:
        """
        Prepare service for Docker Compose deployment.

        Args:
            compose_project_name: Docker Compose project name
            network_name: Docker network name to use
        """
        # First ensure the image is built
        self.prepare()

        # Set compose-specific attributes if provided
        if compose_project_name:
            self.compose_project_name = compose_project_name

        if network_name:
            self.network_name = network_name

        # Add compose labels to build args
        build_args = self.get_docker_build_args()
        build_args.update(
            {
                "COMPOSE_PROJECT": compose_project_name or "panther",
                "SERVICE_NAME": getattr(self, "service_name", self.__class__.__name__),
            }
        )
        self.set_docker_build_args(build_args)

    def get_compose_service_definition(self) -> dict[str, Any]:
        """
        Get the Docker Compose service definition for this service.

        Returns:
            dict: Service definition for docker-compose.yml
        """
        if not hasattr(self, "docker_image_name"):
            raise AttributeError("docker_image_name must be set")

        service_def = {
            "image": self.docker_image_name,
            "container_name": getattr(self, "service_name", self.__class__.__name__.lower()),
            "networks": [getattr(self, "network_name", "default")],
        }

        # Add volumes if defined
        if hasattr(self, "volumes") and self.volumes:
            service_def["volumes"] = self.volumes

        # Add ports if defined
        if hasattr(self, "ports") and self.ports:
            service_def["ports"] = self.ports

        # Add environment if defined
        if hasattr(self, "environments") and self.environments:
            service_def["environment"] = self.environments

        return service_def


class ServiceManagerDockerMixin(DockerComposeOperationsMixin, CommandEventMixin):
    """
    Complete Docker mixin for service managers.

    Combines all Docker-related functionality and integrates with
    the service manager patterns in PANTHER.

    Now includes event emission capabilities for Docker build operations
    and unified build system to eliminate duplication.
    """

    # Class-level tracking for base image to ensure it's built only once per experiment
    _base_image_built = False
    _base_image_lock = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Initialize Docker-related attributes
        self._docker_prepared = False
        # Initialize CommandEventMixin
        CommandEventMixin.__init__(self)

        # Initialize lock if not done yet
        if ServiceManagerDockerMixin._base_image_lock is None:
            import threading

            ServiceManagerDockerMixin._base_image_lock = threading.Lock()

    def prepare(self, plugin_manager: Optional["PluginManager"] = None) -> None:
        """
        Enhanced prepare method with unified Docker building.

        This method unifies the two Docker build paths (PluginManager vs DockerUtils)
        and ensures the base image is built only once per experiment.

        Args:
            plugin_manager: Optional plugin manager for Docker operations
        """
        if self._docker_prepared:
            self.logger.debug(f"Docker image already prepared for {self.__class__.__name__}")
            return

        # Emit preparation started event
        self.notify_service_event("preparation_started", {"operation": "docker_build"})

        try:
            # Ensure Docker is available
            self.ensure_docker_available()

            # Use plugin_manager if available, otherwise fall back to DockerUtils
            if plugin_manager:
                # Build base image only once per experiment
                self._ensure_base_image_built(plugin_manager)
                # Build service-specific image
                self._build_service_image_unified(plugin_manager)
            else:
                # Fallback to DockerUtils
                self._build_with_docker_utils()

            # Mark as prepared
            self._docker_prepared = True

            # Initialize commands after Docker build if needed
            if hasattr(self, "initialize_commands"):
                self.initialize_commands()

            # Emit preparation completed event
            self.notify_service_event("preparation_completed", {"operation": "docker_build"})

        except Exception as e:
            self.notify_service_event(
                "preparation_failed", {"operation": "docker_build", "error": str(e)}
            )
            raise

    def _ensure_base_image_built(self, plugin_manager: "PluginManager") -> None:
        """
        Build base image only once per experiment session.

        Args:
            plugin_manager: Plugin manager for Docker operations
        """
        with self._base_image_lock:
            if not self._base_image_built:
                self.logger.info("Building base Docker image (once per experiment)")
                self.emit_docker_build_started(
                    "panther/plugins/services/Dockerfile", "panther_base"
                )

                base_dockerfile = Path(
                    os.path.join(os.getcwd(), "panther", "plugins", "services", "Dockerfile")
                )

                try:
                    plugin_manager.build_docker_image_from_path(
                        base_dockerfile, "panther_base", "service"
                    )
                    self._base_image_built = True
                    self.emit_docker_build_completed("panther_base", True)
                    self.logger.info("Base Docker image built successfully")
                except Exception as e:
                    self.emit_docker_build_completed("panther_base", False, str(e))
                    raise

    def _build_service_image_unified(self, plugin_manager: "PluginManager") -> None:
        """
        Build service-specific image with unified event emission.

        Args:
            plugin_manager: Plugin manager for Docker operations
        """
        if not hasattr(self, "implementation_name"):
            self.logger.warning("No implementation_name attribute, skipping service image build")
            return

        image_name = f"{self.implementation_name}:latest"
        dockerfile_path = getattr(self, "docker_file_path", "Unknown")

        self.logger.info(f"Building service Docker image: {image_name}")
        self.emit_docker_build_started(str(dockerfile_path), image_name)

        try:
            # Get simple version string from service config (not the complex object)
            version_obj = getattr(self.service_config_to_test.implementation, "version", "latest")

            # Extract simple version string from complex version object
            if hasattr(version_obj, "version"):
                version = version_obj.version
            elif hasattr(version_obj, "name"):
                version = version_obj.name
            elif isinstance(version_obj, str):
                version = version_obj
            else:
                version = "latest"

            plugin_manager.build_docker_image(self.implementation_name, version)
            self.emit_docker_build_completed(image_name, True)
            self.logger.info(f"Service Docker image {image_name} built successfully")
        except Exception as e:
            self.emit_docker_build_completed(image_name, False, str(e))
            raise

    def _build_with_docker_utils(self) -> None:
        """
        Fallback build using DockerUtils (already emits events via prepare_docker_image).
        """
        self.logger.info("Building Docker image using DockerUtils fallback")
        self.prepare_docker_image()

    @classmethod
    def reset_base_image_flag(cls) -> None:
        """
        Reset base image flag for new experiment.

        This should be called at the start of each experiment to ensure
        the base image is built once for the new experiment.
        """
        cls._base_image_built = False

    def is_docker_prepared(self) -> bool:
        """
        Check if Docker preparation has been completed.

        Returns:
            bool: True if prepared
        """
        return self._docker_prepared

    def reset_docker_preparation(self) -> None:
        """
        Reset the Docker preparation state.

        Useful for forcing rebuild on next prepare() call.
        """
        self._docker_prepared = False

    def get_docker_run_command(
        self,
        command: str | None = None,
        volumes: list[str] | None = None,
        environment: dict[str, str] | None = None,
        ports: list[str] | None = None,
        network: str | None = None,
        name: str | None = None,
        detach: bool = True,
        remove: bool = True,
    ) -> list[str]:
        """
        Generate a docker run command for this service.

        Args:
            command: Command to run in container
            volumes: Volume mappings
            environment: Environment variables
            ports: Port mappings
            network: Network to connect to
            name: Container name
            detach: Run in background
            remove: Remove container after exit

        Returns:
            list: Docker run command as list of arguments
        """
        if not hasattr(self, "docker_image_name"):
            raise AttributeError("docker_image_name must be set")

        cmd = ["docker", "run"]

        if detach:
            cmd.append("-d")
        if remove:
            cmd.append("--rm")

        if name:
            cmd.extend(["--name", name])
        elif hasattr(self, "service_name"):
            cmd.extend(["--name", self.service_name])

        if network:
            cmd.extend(["--network", network])

        # Add volumes
        for volume in volumes or getattr(self, "volumes", []):
            cmd.extend(["-v", volume])

        # Add environment variables
        env_vars = environment or getattr(self, "environments", {})
        for key, value in env_vars.items():
            cmd.extend(["-e", f"{key}={value}"])

        # Add ports
        for port in ports or getattr(self, "ports", []):
            cmd.extend(["-p", port])

        # Add image
        cmd.append(self.docker_image_name)

        # Add command if provided
        if command:
            cmd.extend(command.split() if isinstance(command, str) else command)

        return cmd
