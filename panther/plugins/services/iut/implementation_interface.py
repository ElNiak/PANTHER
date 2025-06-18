from abc import ABC
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
from panther.plugins.services.iut.iut_service_manager_mixin import (
    IUTServiceManagerMixin,
)
from panther.plugins.services.services_interface import IServiceManager


class IImplementationManager(IServiceManager, ABC):
    """
    IImplementationManager is an abstract base class that inherits from IServiceManager and ABC.

    Attributes:
        service_config_to_test (ServiceConfig): The configuration of the service to be tested.
        service_type (str): The type of the service.
        protocol (ProtocolConfig): The protocol configuration.
        implementation_name (str): The name of the implementation.
        event_manager (Optional[EventManager]): Manager for handling events.

    Methods:
        __init__(service_config_to_test, service_type, protocol, implementation_name, event_manager):
            Initializes the IImplementationManager with the given parameters.

        is_tester():
            Returns False indicating that this implementation is not a tester.
    """

    def __init__(
        self,
        service_config_to_test: ServiceConfig,
        service_type: str,
        protocol: ProtocolConfig,
        implementation_name: str,
        event_manager: Optional[EventManager] = None,
    ):
        super().__init__(
            service_config_to_test,
            service_type,
            protocol,
            implementation_name,
            event_manager,
        )

    def is_tester(self):
        return False


class StandardIUTImplementationManager(
    IUTServiceManagerMixin,
    ServiceManagerDockerMixin,
    ErrorHandlerMixin,
    IImplementationManager,
):
    """
    Standard implementation manager for IUT services that provides common initialization.

    This class encapsulates the common patterns found in all IUT service implementations:
    - Standardized initialization sequence
    - Template renderer setup
    - Docker configuration setup
    - IUT-specific attribute setup

    Concrete implementations should inherit from this class and only override specific methods
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

        # Set up IUT-specific attributes
        self.setup_iut_specific_attributes(protocol, service_config_to_test)

        # Initialize template renderer
        if plugin_dir is None:
            plugin_dir = Path(__file__).parent
        self.template_renderer = ServiceTemplateRenderer(plugin_dir)

        # Set Docker attributes for ServiceManagerDockerMixin
        if docker_image_name is None:
            docker_image_name = f"{implementation_name}:latest"

        self.docker_image_name = docker_image_name
        self.docker_file_path = plugin_dir / "Dockerfile"
