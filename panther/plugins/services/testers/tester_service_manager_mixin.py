from typing import Any, Dict, Optional

from panther.plugins.services.plugin_directory_mixin import PluginDirectoryMixin
from panther.plugins.services.service_manager_mixin import ServiceManagerMixin
from panther.plugins.services.testers.tester_interface import ITesterManager


class TesterServiceManagerMixin(
    PluginDirectoryMixin, ServiceManagerMixin, ITesterManager
):
    """
    Specialized mixin for tester service managers.

    Provides tester-specific patterns and utilities including test parameter
    management, formal verification support, and a strict template renderer
    setup that requires a protocol to be specified (raises ValueError if
    protocol is missing).

    Plugin directory detection, Docker image naming, and Docker attribute
    setup are inherited from PluginDirectoryMixin.

    MRO: TesterServiceManagerMixin -> PluginDirectoryMixin -> ServiceManagerMixin -> LoggerMixin -> ITesterManager
    """

    def __init__(self, *args, global_config=None, **kwargs):
        super().__init__(*args, **kwargs)

        # Store global configuration
        self.global_config = global_config
        self._test_parameters = {}
        self._role = None
        self._protocol_version = None

    def setup_tester_specific_attributes(
        self, protocol: Any, service_config_to_test: Any
    ) -> None:
        """
        Set up tester-specific attributes.

        Args:
            service_config_to_test: Service configuration
        """
        # Extract test parameters if available
        if hasattr(service_config_to_test, "protocol") and hasattr(
            service_config_to_test.protocol, "role"
        ):
            self._role = service_config_to_test.protocol.role
        elif hasattr(protocol, "role"):
            self._role = protocol.role
        else:
            self._role = "client"  # Default role

        if hasattr(service_config_to_test, "test_parameters"):
            self._test_parameters = service_config_to_test.test_parameters
        elif hasattr(service_config_to_test, "implementation"):
            # Check if the implementation is a dict with 'test' key
            if (
                isinstance(service_config_to_test.implementation, dict)
                and "test" in service_config_to_test.implementation
            ):
                self._test_parameters = {
                    "test": service_config_to_test.implementation["test"]
                }
            # Check if implementation has test attribute
            elif hasattr(service_config_to_test.implementation, "test"):
                self._test_parameters = {
                    "test": service_config_to_test.implementation.test
                }
            # Check if service_config has test attribute directly
            elif hasattr(service_config_to_test, "test"):
                self._test_parameters = {"test": service_config_to_test.test}

    @property
    def test_parameters(self) -> Dict[str, Any]:
        """Get the test parameters."""
        return self._test_parameters

    def get_test_name(self) -> Optional[str]:
        """Get the specific test name to run."""
        return self._test_parameters.get("test")

    def is_formal_verification_tester(self) -> bool:
        """Check if this is a formal verification tester (like Ivy)."""
        impl_name = getattr(self, "implementation_name", "").lower()
        return "ivy" in impl_name or "formal" in impl_name

    def standard_tester_initialization(
        self,
        service_config_to_test: Any = None,
        service_type: str = None,
        protocol: Any = None,
        implementation_name: str = None,
        event_manager: Any = None,
        include_protocol_in_template: bool = True,
        plugin_dir: Any = None,
    ) -> None:
        """
        Template method for standard tester service initialization.

        This method encapsulates the common initialization pattern used by all tester services:
        1. Call standardized_initialization from ServiceManagerMixin
        2. Set up tester-specific attributes
        3. Initialize template renderer (with optional protocol support)
        4. Set up Docker attributes

        Services can override the hook methods to customize specific steps.

        Args:
            service_config_to_test: Service configuration (defaults to self.service_config_to_test)
            service_type: Service type (defaults to self.service_type)
            protocol: Protocol config (defaults to self.service_protocol)
            implementation_name: Implementation name (defaults to self.implementation_name)
            event_manager: Event manager (defaults to self.event_manager)
            include_protocol_in_template: Whether to include protocol in template renderer
        """
        # Use provided parameters or fall back to instance attributes
        service_config_to_test = service_config_to_test or getattr(
            self, "service_config_to_test", None
        )
        service_type = service_type or getattr(self, "service_type", None)
        # TODO check if tester
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

        # Step 2: Set up tester-specific attributes
        self.setup_tester_specific_attributes(protocol, service_config_to_test)

        # Step 3: Initialize template renderer (hook method for customization)
        self._setup_template_renderer(include_protocol_in_template, protocol)

        # Step 4: Set up Docker attributes (hook method for customization)
        self._setup_docker_attributes()

    def _setup_template_renderer(
        self, include_protocol_in_template: bool = True, protocol: Any = None
    ) -> None:
        """
        Hook method: Set up the template renderer.

        Override this method to customize template renderer setup.
        Default implementation creates a ServiceTemplateRenderer with optional protocol support.

        Args:
            include_protocol_in_template: Whether to include protocol in template setup
            protocol: Protocol configuration
        """
        from panther.core.template.template_renderer import ServiceTemplateRenderer

        plugin_dir = self._plugin_dir or self._get_plugin_dir()

        self.logger.debug(
            "Setting up template renderer with plugin_dir: %s, include_protocol_in_template: %s, protocol: %s",
            plugin_dir,
            include_protocol_in_template,
            protocol,
        )

        if include_protocol_in_template and protocol:
            protocol_name = getattr(protocol, "name", None)
            if protocol_name:
                self.template_renderer = ServiceTemplateRenderer(
                    plugin_dir, protocol_name
                )
            else:
                raise ValueError(
                    "Protocol name not found in the provided protocol configuration."
                )
        else:
            self.template_renderer = ServiceTemplateRenderer(plugin_dir)
