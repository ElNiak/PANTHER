from pathlib import Path
from typing import Optional

from panther.config.core.models import ServiceConfig
from panther.core.docker_builder.service_manager_docker_mixin import (
    ServiceManagerDockerMixin,
)
from panther.core.exceptions.error_handler_mixin import ErrorHandlerMixin
from panther.core.observer.management.event_manager import EventManager
from panther.core.utils import ServiceTemplateRenderer
from panther.config.core.models import ProtocolConfig
from panther.plugins.services.testers.tester_interface import ITesterManager
from panther.plugins.services.testers.tester_service_manager_mixin import (
    TesterServiceManagerMixin,
)


class StandardTesterManager(
    TesterServiceManagerMixin,
    ServiceManagerDockerMixin,
    ErrorHandlerMixin,
    ITesterManager,
):
    """
    Standard implementation manager for Tester services that provides common initialization.

    This class encapsulates the common patterns found in all tester service implementations:
    - Standardized initialization sequence
    - Template renderer setup with protocol support
    - Docker configuration setup
    - Tester-specific attribute setup

    Concrete tester implementations should inherit from this class and only override specific methods
    or add implementation-specific attributes.
    """

    def __init__(
        self,
        service_config_to_test: ServiceConfig,
        service_type: str,
        protocol: ProtocolConfig,
        implementation_name: str,
        event_manager: Optional[EventManager] = None,
        docker_image_name: str = None,
        plugin_dir: Path = None,
        include_protocol_in_template: bool = True,
    ):
        super().__init__(
            service_config_to_test,
            service_type,
            protocol,
            implementation_name,
            event_manager,
        )

        # Use standardized initialization from mixin
        self.standardized_initialization(
            service_config_to_test,
            service_type,
            protocol,
            implementation_name,
            event_manager,
        )

        # Set up tester-specific attributes
        self.setup_tester_specific_attributes(service_config_to_test)

        # Initialize template renderer
        if plugin_dir is None:
            plugin_dir = Path(__file__).parent

        if include_protocol_in_template:
            self.template_renderer = ServiceTemplateRenderer(plugin_dir, protocol.name)
        else:
            self.template_renderer = ServiceTemplateRenderer(plugin_dir)

        # Set Docker attributes for ServiceManagerDockerMixin
        if docker_image_name is None:
            docker_image_name = f"{implementation_name}:latest"

        self.docker_image_name = docker_image_name
        self.docker_file_path = plugin_dir / "Dockerfile"
