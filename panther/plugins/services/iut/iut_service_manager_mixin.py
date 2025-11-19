import inspect
from typing import Any, Optional

from panther.plugins.services.iut.implementation_interface import IImplementationManager
from panther.plugins.services.service_manager_mixin import ServiceManagerMixin


class IUTServiceManagerMixin(ServiceManagerMixin, IImplementationManager):
    """
    Specialized mixin for IUT (Implementation Under Test) service managers.
    Provides IUT-specific patterns and utilities.
    """

    def __init__(self, *args, global_config=None, **kwargs):
        super().__init__(*args, **kwargs)

        # Store global configuration
        self.global_config = global_config
        self._role = None
        self._protocol_version = None

    def setup_iut_specific_attributes(
        self, protocol: Any, service_config_to_test: Any
    ) -> None:
        """
        Set up IUT-specific attributes.

        Args:
            protocol: Protocol configuration
            service_config_to_test: Service configuration
        """
        # Set role from protocol configuration
        if hasattr(service_config_to_test, "protocol") and hasattr(
            service_config_to_test.protocol, "role"
        ):
            self._role = service_config_to_test.protocol.role
        elif hasattr(protocol, "role"):
            self._role = protocol.role
        else:
            self._role = "client"  # Default role

        # Set protocol version
        if hasattr(service_config_to_test, "protocol") and hasattr(
            service_config_to_test.protocol, "version"
        ):
            self._protocol_version = service_config_to_test.protocol.version
        elif hasattr(protocol, "version"):
            self._protocol_version = protocol.version
        else:
            self._protocol_version = "default"

    @property
    def role(self) -> str:
        """Get the service role (client/server)."""
        return self._role

    @role.setter
    def role(self, value) -> None:
        """Set the service role."""
        self._role = value

    @property
    def protocol_version(self) -> str:
        """Get the protocol version."""
        return self._protocol_version or "default"

    def is_client(self) -> bool:
        """Check if this service is a client."""
        return self.role.lower() == "client"

    def is_server(self) -> bool:
        """Check if this service is a server."""
        return self.role.lower() == "server"

    def get_target_service(self) -> Optional[str]:
        """Get the target service name for client connections."""
        return getattr(self, "service_targets", None)

    def standard_iut_initialization(
        self,
        service_config_to_test: Any = None,
        service_type: str = None,
        protocol: Any = None,
        implementation_name: str = None,
        event_manager: Any = None,
        plugin_dir: Any = None,
    ) -> None:
        """
        Template method for standard IUT service initialization.

        This method encapsulates the common 6-line initialization pattern used by all IUT services:
        1. Call standardized_initialization from ServiceManagerMixin
        2. Set up IUT-specific attributes
        3. Initialize template renderer
        4. Set up Docker attributes

        Services can override the hook methods to customize specific steps.

        Args:
            service_config_to_test: Service configuration (defaults to self.service_config_to_test)
            service_type: Service type (defaults to self.service_type)
            protocol: Protocol config (defaults to self.service_protocol)
            implementation_name: Implementation name (defaults to self.implementation_name)
            event_manager: Event manager (defaults to self.event_manager)
            plugin_dir: Plugin directory path (required for template setup)
        """
        # Use provided parameters or fall back to instance attributes
        service_config_to_test = service_config_to_test or getattr(
            self, "service_config_to_test", None
        )
        service_type = service_type or getattr(self, "service_type", None)
        protocol = protocol or getattr(self, "service_protocol", None)
        implementation_name = implementation_name or getattr(
            self, "implementation_name", None
        )
        event_manager = event_manager or getattr(self, "event_manager", None)

        # Store plugin_dir for hook methods
        self._plugin_dir = plugin_dir

        # Step 1: Standardized initialization from ServiceManagerMixin
        self.standardized_initialization(
            service_config_to_test,
            service_type,
            protocol,
            implementation_name,
            event_manager,
        )

        # Step 2: Set up IUT-specific attributes
        self.setup_iut_specific_attributes(protocol, service_config_to_test)

        # Step 3: Initialize template renderer (hook method for customization)
        self._setup_template_renderer()

        # Step 4: Set up Docker attributes (hook method for customization)
        self._setup_docker_attributes()

    def _get_plugin_dir(self):
        """
        Hook method: Get the plugin directory.

        Override this method to customize plugin directory detection.
        Default implementation gets the directory of the calling file.

        Returns:
            Path: Plugin directory path
        """
        import inspect
        from pathlib import Path

        # Get the directory of the calling class (the actual service implementation)
        frame = inspect.currentframe()
        try:
            # Go up the stack to find the service class file
            caller_frame = (
                frame.f_back.f_back
            )  # Skip standard_iut_initialization and __init__
            if caller_frame and caller_frame.f_code.co_filename:
                return Path(caller_frame.f_code.co_filename).parent
        finally:
            del frame

        # Fallback to current file parent (not ideal but safe)
        return Path(__file__).parent

    def _get_docker_image_name(self, implementation_name: str = None) -> str:
        """
        Hook method: Get the Docker image name.

        Override this method to customize Docker image naming.
        Default implementation uses implementation_name:latest format.

        Args:
            implementation_name: Name of the implementation

        Returns:
            str: Docker image name
        """
        implementation_name = implementation_name or getattr(
            self, "implementation_name", "unknown"
        )
        return f"{implementation_name}:latest"

    def _setup_template_renderer(self) -> None:
        """
        Hook method: Set up the template renderer.

        Override this method to customize template renderer setup.
        Default implementation creates a ServiceTemplateRenderer with plugin directory.
        """
        from panther.core.template.template_renderer import ServiceTemplateRenderer

        plugin_dir = self._plugin_dir or self._get_plugin_dir()
        self.template_renderer = ServiceTemplateRenderer(plugin_dir)

    def _setup_docker_attributes(self) -> None:
        """
        Hook method: Set up Docker-related attributes.

        Override this method to customize Docker configuration.
        Default implementation sets docker_image_name and docker_file_path.
        """
        self.docker_image_name = self._get_docker_image_name()
        plugin_dir = self._plugin_dir or self._get_plugin_dir()
        self.docker_file_path = plugin_dir / "Dockerfile"
