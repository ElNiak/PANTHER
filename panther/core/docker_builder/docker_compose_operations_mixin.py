from typing import Any, Dict, Optional

from panther.core.docker_builder.docker_operations_mixin import DockerOperationsMixin


class DockerComposeOperationsMixin(DockerOperationsMixin):
    """
    Extended mixin for Docker Compose operations.

    Provides additional functionality specific to Docker Compose environments.
    """

    def prepare_for_compose(
        self,
        compose_project_name: Optional[str] = None,
        network_name: Optional[str] = None,
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

    def get_compose_service_definition(self) -> Dict[str, Any]:
        """
        Get the Docker Compose service definition for this service.

        Returns:
            dict: Service definition for docker-compose.yml
        """
        if not hasattr(self, "docker_image_name"):
            raise AttributeError("docker_image_name must be set")

        service_def = {
            "image": self.docker_image_name,
            "container_name": getattr(
                self, "service_name", self.__class__.__name__.lower()
            ),
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
