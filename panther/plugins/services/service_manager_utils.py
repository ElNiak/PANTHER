"""
Service Manager Utilities

This module provides common utilities and mixins for service managers,
integrating with PANTHER's existing patterns and interfaces.
"""

import logging
from typing import Any

from panther.core.utils.logging_mixin import LoggerMixin
from panther.core.command_processor.command_utils import CommandUtils
from panther.core.command_processor.command import ShellCommand

logger = logging.getLogger(__name__)


class ServiceManagerUtilities:
    """Common utility methods for service managers."""

    @staticmethod
    def standardize_initialization_logging(
        logger: logging.Logger, implementation_name: str, service_config: Any
    ) -> None:
        """
        Standardize initialization logging across service managers.

        Args:
            logger: Logger instance
            implementation_name: Name of the implementation
            service_config: Service configuration object
        """
        logger.debug(
            "Initializing %s service manager for '%s'",
            logger.name or "Service",
            implementation_name,
        )
        logger.debug("Loaded %s configuration: %s", logger.name or "Service", service_config)

    @staticmethod
    def setup_service_attributes(
        service_manager: Any,
        service_config_to_test: Any,
        service_type: str,
        protocol: Any,
        implementation_name: str,
    ) -> None:
        """
        Set up standard service manager attributes.

        Args:
            service_manager: Service manager instance
            service_config_to_test: Service configuration
            service_type: Type of service
            protocol: Protocol configuration
            implementation_name: Implementation name
        """
        service_manager.service_config_to_test = service_config_to_test
        service_manager.implementation_name = implementation_name
        service_manager.service_name = getattr(service_config_to_test, "name", implementation_name)
        service_manager.service_protocol = protocol
        service_manager.service_type = service_type
        service_manager.service_targets = (
            getattr(service_config_to_test.protocol, "target", "")
            if hasattr(service_config_to_test, "protocol")
            else ""
        )
        service_manager.service_version = (
            getattr(service_config_to_test.protocol, "version", "")
            if hasattr(service_config_to_test, "protocol")
            else ""
        )


class ServiceManagerMixin(LoggerMixin):
    """
    Comprehensive mixin for service managers that provides common patterns
    and integrates with PANTHER's existing architecture.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._commands_initialized = False
        self._run_cmd = None

    def standardized_initialization(
        self,
        service_config_to_test: Any,
        service_type: str,
        protocol: Any,
        implementation_name: str,
        event_manager=None,
    ) -> None:
        """
        Perform standardized service manager initialization.

        This method sets up attributes and configuration but does NOT initialize commands.
        Commands should be initialized later in prepare() after Docker images are built.

        Args:
            service_config_to_test: Service configuration
            service_type: Type of service
            protocol: Protocol configuration
            implementation_name: Implementation name
            event_manager: Event manager instance
        """
        # Set up standard attributes
        ServiceManagerUtilities.setup_service_attributes(
            self, service_config_to_test, service_type, protocol, implementation_name
        )

        # Store event manager
        self.event_manager = event_manager

        # Standard logging
        ServiceManagerUtilities.standardize_initialization_logging(
            self.logger, implementation_name, service_config_to_test
        )

        # DO NOT initialize commands here - they should be initialized in prepare()
        # after Docker images are built and environment is ready

    def initialize_commands(self) -> None:
        """Initialize the command structure with defaults."""
        if not self._commands_initialized:
            # Create the nested structure expected by Docker Compose templates
            basic_commands = CommandUtils.generate_basic_service_commands()
            self._run_cmd = {
                "pre_compile_cmds": basic_commands.get("pre_compile_cmds", []),
                "compile_cmds": basic_commands.get("compile_cmds", []),
                "post_compile_cmds": basic_commands.get("post_compile_cmds", []),
                "pre_run_cmds": basic_commands.get("pre_run_cmds", []),
                "run_cmd": basic_commands.get(
                    "run_cmd",
                    {
                        "working_dir": "/app",
                        "command_binary": "echo",
                        "command_args": "No run command implemented",
                        "timeout": 60,
                        "environment": {},
                    },
                ),
                "post_run_cmds": basic_commands.get("post_run_cmds", []),
            }
            self._commands_initialized = True

    @property
    def run_cmd(self) -> dict[str, Any]:
        """Get the run command structure."""
        if self._run_cmd is None:
            self.initialize_commands()
        return self._run_cmd

    @run_cmd.setter
    def run_cmd(self, value: dict[str, Any]) -> None:
        """Set the run command structure."""
        self._run_cmd = value

    def generate_pre_compile_commands(self) -> list[str | ShellCommand]:
        """Generate pre-compile commands. Override in subclasses."""
        return []

    def generate_compile_commands(self) -> list[str | ShellCommand]:
        """Generate compile commands. Override in subclasses."""
        return []

    def generate_post_compile_commands(self) -> list[str | ShellCommand]:
        """Generate post-compile commands. Override in subclasses."""
        return []

    def generate_pre_run_commands(self) -> list[str | ShellCommand]:
        """Generate pre-run commands. Override in subclasses."""
        return []

    def generate_post_run_commands(self) -> list[str | ShellCommand]:
        """Generate post-run commands. Override in subclasses."""
        return []

    def generate_run_command(self) -> dict[str, Any]:
        """Generate the main run command. Must be implemented by subclasses."""
        return {
            "working_dir": "/app",
            "command_binary": "echo",
            "command_args": "No run command implemented",
            "timeout": 60,
            "environment": {},
        }

    def create_standard_shell_command(
        self,
        command: str,
        working_dir: str | None = None,
        environment: dict[str, str] | None = None,
        timeout: int | None = None,
    ) -> ShellCommand:
        """
        Create a ShellCommand with service-specific defaults.

        Args:
            command: Command string
            working_dir: Working directory (defaults to service working_dir)
            environment: Environment variables
            timeout: Command timeout

        Returns:
            ShellCommand: Configured command object
        """
        if working_dir is None:
            working_dir = getattr(self, "working_dir", "/app")

        return CommandUtils.create_shell_command(
            command=command, working_dir=working_dir, environment=environment, timeout=timeout
        )

    def add_environment_variable(self, key: str, value: str) -> None:
        """
        Add an environment variable to the run command.

        Args:
            key: Environment variable name
            value: Environment variable value
        """
        # Ensure commands are initialized
        if not self._commands_initialized:
            self.initialize_commands()

        # Ensure the run_cmd structure exists
        if "run_cmd" not in self.run_cmd:
            self.run_cmd["run_cmd"] = self.generate_run_command()

        if "environment" not in self.run_cmd["run_cmd"]:
            self.run_cmd["run_cmd"]["environment"] = {}

        self.run_cmd["run_cmd"]["environment"][key] = value

    def finalize_commands(self) -> dict[str, Any]:
        """
        Finalize and structure all commands for the service.
        Preserves any modifications made by execution environments.

        Returns:
            dict: Complete command structure
        """
        self.initialize_commands()

        # Log what we have before generating new commands
        if hasattr(self, "logger"):
            self.logger.debug(
                "finalize_commands called for %s", getattr(self, "service_name", "unknown")
            )
            self.logger.debug(
                "Existing pre_run_cmds before generation: %s", self.run_cmd.get("pre_run_cmds", [])
            )

        # Generate all command phases
        pre_compile = self.generate_pre_compile_commands()
        compile_cmds = self.generate_compile_commands()
        post_compile = self.generate_post_compile_commands()
        pre_run = self.generate_pre_run_commands()
        post_run = self.generate_post_run_commands()
        run_cmd = self.generate_run_command()

        # Preserve existing execution environment modifications by merging instead of overwriting
        existing_pre_compile = self.run_cmd.get("pre_compile_cmds", [])
        existing_compile = self.run_cmd.get("compile_cmds", [])
        existing_post_compile = self.run_cmd.get("post_compile_cmds", [])
        existing_pre_run = self.run_cmd.get("pre_run_cmds", [])
        existing_post_run = self.run_cmd.get("post_run_cmds", [])

        # Merge execution environment modifications with generated commands
        # Execution environment commands come first, then service-specific commands
        self.run_cmd.update(
            {
                "pre_compile_cmds": existing_pre_compile + pre_compile,
                "compile_cmds": existing_compile + compile_cmds,
                "post_compile_cmds": existing_post_compile + post_compile,
                "pre_run_cmds": existing_pre_run + pre_run,
                "post_run_cmds": existing_post_run + post_run,
                "run_cmd": run_cmd,
            }
        )

        # Log the final state
        if hasattr(self, "logger"):
            self.logger.debug(
                "Final pre_run_cmds after merge: %s", self.run_cmd.get("pre_run_cmds", [])
            )

        return self.run_cmd

    def get_service_name(self) -> str:
        """Get the service name."""
        return getattr(self, "service_name", self.__class__.__name__)

    def is_tester(self) -> bool:
        """Check if this is a tester service."""
        service_type = getattr(self, "service_type", "").upper()
        return service_type == "TESTERS"


class IUTServiceManagerMixin(ServiceManagerMixin):
    """
    Specialized mixin for IUT (Implementation Under Test) service managers.
    Provides IUT-specific patterns and utilities.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._role = None
        self._protocol_version = None

    def setup_iut_specific_attributes(self, protocol: Any, service_config_to_test: Any) -> None:
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
        return self._role or "client"

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

    def get_target_service(self) -> str | None:
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
        implementation_name = implementation_name or getattr(self, "implementation_name", None)
        event_manager = event_manager or getattr(self, "event_manager", None)

        # Store plugin_dir for hook methods
        self._plugin_dir = plugin_dir

        # Step 1: Standardized initialization from ServiceManagerMixin
        self.standardized_initialization(
            service_config_to_test, service_type, protocol, implementation_name, event_manager
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
        from pathlib import Path
        import inspect

        # Get the directory of the calling class (the actual service implementation)
        frame = inspect.currentframe()
        try:
            # Go up the stack to find the service class file
            caller_frame = frame.f_back.f_back  # Skip standard_iut_initialization and __init__
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
        implementation_name = implementation_name or getattr(self, "implementation_name", "unknown")
        return f"{implementation_name}:latest"

    def _setup_template_renderer(self) -> None:
        """
        Hook method: Set up the template renderer.

        Override this method to customize template renderer setup.
        Default implementation creates a ServiceTemplateRenderer with plugin directory.
        """
        from panther.core.utils import ServiceTemplateRenderer

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


class TesterServiceManagerMixin(ServiceManagerMixin):
    """
    Specialized mixin for tester service managers.
    Provides tester-specific patterns and utilities.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._test_parameters = {}

    def setup_tester_specific_attributes(self, service_config_to_test: Any) -> None:
        """
        Set up tester-specific attributes.

        Args:
            service_config_to_test: Service configuration
        """
        # Extract test parameters if available
        if hasattr(service_config_to_test, "test_parameters"):
            self._test_parameters = service_config_to_test.test_parameters
        elif hasattr(service_config_to_test, "implementation") and hasattr(
            service_config_to_test.implementation, "test"
        ):
            self._test_parameters = {"test": service_config_to_test.implementation.test}

    @property
    def test_parameters(self) -> dict[str, Any]:
        """Get the test parameters."""
        return self._test_parameters

    def get_test_name(self) -> str | None:
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
        protocol = protocol or getattr(self, "service_protocol", None)
        implementation_name = implementation_name or getattr(self, "implementation_name", None)
        event_manager = event_manager or getattr(self, "event_manager", None)

        # Store plugin_dir for hook methods
        self._plugin_dir = plugin_dir

        # Step 1: Standardized initialization from ServiceManagerMixin
        self.standardized_initialization(
            service_config_to_test, service_type, protocol, implementation_name, event_manager
        )

        # Step 2: Set up tester-specific attributes
        self.setup_tester_specific_attributes(service_config_to_test)

        # Step 3: Initialize template renderer (hook method for customization)
        self._setup_template_renderer(include_protocol_in_template, protocol)

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
        from pathlib import Path
        import inspect

        # Get the directory of the calling class (the actual service implementation)
        frame = inspect.currentframe()
        try:
            # Go up the stack to find the service class file
            caller_frame = frame.f_back.f_back  # Skip standard_tester_initialization and __init__
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
        implementation_name = implementation_name or getattr(self, "implementation_name", "unknown")
        return f"{implementation_name}:latest"

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
        from panther.core.utils import ServiceTemplateRenderer

        plugin_dir = self._plugin_dir or self._get_plugin_dir()

        if include_protocol_in_template and protocol:
            protocol_name = getattr(protocol, "name", None)
            if protocol_name:
                self.template_renderer = ServiceTemplateRenderer(plugin_dir, protocol_name)
            else:
                self.template_renderer = ServiceTemplateRenderer(plugin_dir)
        else:
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
