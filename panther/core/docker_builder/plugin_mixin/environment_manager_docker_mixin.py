"""Docker mixin for environment managers (localhost, shadow)."""

import os
import threading
from pathlib import Path
from typing import TYPE_CHECKING, Dict, List, Optional

from panther.core.command_processor.mixins import CommandEventMixin
from panther.core.docker_builder.docker_builder import DockerBuilder
from panther.core.docker_builder.plugin_mixin.docker_operations_mixin import (
    DockerOperationsMixin,
)

if TYPE_CHECKING:
    from panther.plugins.plugin_manager import PluginManager
    from panther.plugins.services.services_interface import IServiceManager


class StagedDockerMixin(DockerOperationsMixin, CommandEventMixin):
    """Docker mixin specifically for environment managers (localhost, shadow).

    Handles:
    - Building base service images
    - Building environment-specific images from generated Dockerfiles
    - Managing multi-stage builds that reference service images
    - Orchestrating multiple service images rather than building a single service

    This is distinct from ServiceManagerDockerMixin which handles individual service images.
    """

    # Use different class variable to avoid conflicts with service mixin
    _env_base_service_image_built = False
    _env_base_service_lock = threading.Lock()

    def __init__(self, *args, **kwargs):
        """Initialize staged Docker mixin for environment managers."""
        super().__init__(*args, **kwargs)
        # Initialize Docker-related attributes
        self._docker_prepared = False
        # Initialize CommandEventMixin
        CommandEventMixin.__init__(self)

    def build_base_service_image(self, plugin_manager: "PluginManager") -> str:
        """Build the base service image from panther/plugins/services/Dockerfile.

        Returns:
            str: Image tag of built base image
        """
        with self._env_base_service_lock:
            if not self._env_base_service_image_built:
                self.logger.info("Building base service image (once per experiment)")

                # Use environment name for base image tag
                env_name = getattr(self, "env_name", "localhost_single_container")
                version = getattr(self, "docker_version", "v1")
                base_image_tag = f"{env_name}_{version}"

                self.emit_docker_build_started(
                    "panther/plugins/services/Dockerfile", base_image_tag
                )

                base_dockerfile = Path(
                    os.path.join(
                        os.getcwd(), "panther", "plugins", "services", "Dockerfile"
                    )
                )

                try:
                    docker_builder = DockerBuilder.get_instance(
                        global_config=getattr(self, "global_config", None),
                        experiment_context=getattr(self, "experiment_context", None),
                    )
                    docker_builder.build_image(
                        impl_name=env_name,
                        version=version,
                        dockerfile_path=base_dockerfile,
                        context_path=base_dockerfile.parent,
                        config={},
                    )
                    self._env_base_service_image_built = True
                    self.emit_docker_build_completed(base_image_tag, True)
                    self.logger.info(
                        f"Base service image built successfully: {base_image_tag}"
                    )
                    return base_image_tag
                except Exception as e:
                    self.emit_docker_build_completed(base_image_tag, False, str(e))
                    raise
            else:
                # Return the already built image tag
                env_name = getattr(self, "env_name", "localhost_single_container")
                version = getattr(self, "docker_version", "v1")
                return f"{env_name}_{version}"

    def ensure_service_images_available(
        self, services: List["IServiceManager"]
    ) -> Dict[str, str]:
        """Ensure all required service images are available.

        Returns:
            Dict[str, str]: Mapping of service_name to image_tag
        """
        service_images = {}
        for service in services:
            image_tag = getattr(service, "docker_image_tag", "")
            if not image_tag:
                service_name = getattr(service, "service_name", "unknown")
                self.logger.error(
                    "Service %s has no docker_image_tag set. "
                    "The experiment cannot proceed without all service images.",
                    service_name,
                )
                continue

            # Check if image exists
            check_cmd = ["docker", "images", "-q", image_tag]
            result = self.execute_command(check_cmd, timeout=10, check=False)

            if not result.stdout.strip():
                self.logger.warning(
                    f"Service image {image_tag} not found. It should have been built by the service manager."
                )
            else:
                self.logger.debug(f"Service image {image_tag} is available")

            service_images[service.service_name] = image_tag

        return service_images

    def build_environment_image(
        self,
        dockerfile_path: Path,
        image_name: str,
        context_path: Optional[Path] = None,
    ) -> None:
        """Build environment-specific Docker image from generated Dockerfile.

        Handles multi-stage builds properly.

        Args:
            dockerfile_path: Path to the generated Dockerfile
            image_name: Name for the resulting image
            context_path: Build context path (defaults to dockerfile directory)
        """
        self.logger.info(f"Building environment image: {image_name}")
        self.emit_docker_build_started(str(dockerfile_path), image_name)

        # Use dockerfile directory as context if not specified
        if context_path is None:
            context_path = dockerfile_path.parent

        build_cmd = [
            "docker",
            "build",
            "-t",
            image_name,
            "-f",
            str(dockerfile_path),
            str(context_path),
        ]

        try:
            # Execute build with proper timeout for multi-stage builds
            result = self.execute_command(
                build_cmd,
                timeout=600,  # 10 minutes for complex multi-stage builds
                check=True,
            )

            self.emit_docker_build_completed(image_name, True)
            self.logger.info(f"Environment image {image_name} built successfully")

        except Exception as e:
            self.emit_docker_build_completed(image_name, False, str(e))
            self.logger.error(f"Failed to build environment image: {e}")
            raise

    def verify_dockerfile_ready(self, dockerfile_path: Path) -> bool:
        """Verify that a Dockerfile has been generated and contains valid FROM instructions.

        Args:
            dockerfile_path: Path to the Dockerfile to verify

        Returns:
            bool: True if Dockerfile is valid, False otherwise
        """
        if not dockerfile_path.exists():
            self.logger.error(f"Dockerfile not found: {dockerfile_path}")
            return False

        try:
            with open(dockerfile_path, "r") as f:
                content = f.read()

            # Check for empty FROM instructions
            if "FROM " in content and "FROM  " in content:
                self.logger.error("Dockerfile contains empty FROM instructions")
                return False

            # Check that we have at least one valid FROM
            from_count = content.count("FROM ")
            if from_count == 0:
                self.logger.error("Dockerfile contains no FROM instructions")
                return False

            self.logger.debug(
                f"Dockerfile verified with {from_count} FROM instructions"
            )
            return True

        except Exception as e:
            self.logger.error(f"Error verifying Dockerfile: {e}")
            return False

    @classmethod
    def reset_base_image_flag(cls) -> None:
        """Reset base image flag for new experiment.

        This should be called at the start of each experiment to ensure
        the base image is built once for the new experiment.
        """
        cls._env_base_service_image_built = False

    def is_docker_prepared(self) -> bool:
        """Check if Docker preparation has been completed.

        Returns:
            bool: True if prepared
        """
        return self._docker_prepared

    def reset_docker_preparation(self) -> None:
        """Reset the Docker preparation state.

        Useful for forcing rebuild on next prepare() call.
        """
        self._docker_prepared = False

    def get_environment_docker_run_command(
        self,
        image_name: str,
        container_name: str,
        command: Optional[str] = None,
        volumes: Optional[List[str]] = None,
        environment: Optional[Dict[str, str]] = None,
        ports: Optional[List[str]] = None,
        network: Optional[str] = None,
        user: Optional[str] = None,
        detach: bool = True,
        remove: bool = False,  # Environments typically don't auto-remove
    ) -> List[str]:
        """Generate a docker run command for environment containers.

        Args:
            image_name: Docker image to run
            container_name: Name for the container
            command: Command to run in container
            volumes: Volume mappings
            environment: Environment variables
            ports: Port mappings
            network: Network to connect to
            user: User mapping (e.g., "1000:1000")
            detach: Run in background
            remove: Remove container after exit

        Returns:
            list: Docker run command as list of arguments
        """
        cmd = ["docker", "run"]

        if detach:
            cmd.append("-d")
        if remove:
            cmd.append("--rm")

        cmd.extend(["--name", container_name])

        if network:
            cmd.extend(["--network", network])

        if user:
            cmd.extend(["--user", user])

        # Add volumes
        for volume in volumes or []:
            cmd.extend(["-v", volume])

        # Add environment variables
        for key, value in (environment or {}).items():
            cmd.extend(["-e", f"{key}={value}"])

        # Add ports
        for port in ports or []:
            cmd.extend(["-p", port])

        # Add image
        cmd.append(image_name)

        # Add command if provided
        if command:
            cmd.extend(command.split() if isinstance(command, str) else command)

        return cmd
