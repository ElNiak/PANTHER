"""Base class for all MINIP service implementations."""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Protocol

from panther.core.utils.string_representation_mixin import StringRepresentationMixin
from panther.plugins.services.services_interface import IServiceManager


class BaseMinipServiceManager(IServiceManager, StringRepresentationMixin, ABC):
    """
    Base class for MINIP protocol implementations.

    This class provides common functionality for MINIP service implementations,
    reducing code duplication across different MINIP service managers.
    """

    def __init__(
        self,
        service_config_to_test: Any,
        service_type: Any,  # Can be string or ImplementationType enum
        protocol: Any,
        implementation_name: str,
        event_manager: Any = None,
        emitter_registry: Any = None,
        **kwargs,
    ):
        """Initialize the base MINIP service manager.

        Args:
            service_config_to_test: Service configuration
            service_type: Type of service (IUT/tester) - string or ImplementationType enum
            protocol: Protocol configuration
            implementation_name: Name of the implementation
            event_manager: Event manager instance
            emitter_registry: Emitter registry (optional)
            **kwargs: Additional configuration
        """
        # Convert string service_type to ImplementationType enum if needed
        from panther.config.core.models.service import ImplementationType

        if isinstance(service_type, str):
            # Map string to enum
            if service_type.lower() in ["iut"]:
                service_type = ImplementationType.IUT
            elif service_type.lower() in ["testers", "tester"]:
                service_type = ImplementationType.TESTERS
            else:
                # Try to create enum from string value
                try:
                    service_type = ImplementationType(service_type.lower())
                except ValueError:
                    logging.warning(
                        f"Unknown service type '{service_type}', defaulting to IUT"
                    )
                    service_type = ImplementationType.IUT

        # Initialize base attributes
        self.service_config_to_test = service_config_to_test
        self.service_type = service_type
        self.protocol = protocol
        self.implementation_name = implementation_name
        self.event_manager = event_manager
        self.emitter_registry = emitter_registry

        # Store additional configuration
        for key, value in kwargs.items():
            setattr(self, key, value)

        self.logger = logging.getLogger(self.__class__.__name__)

    # Abstract methods that implementations must override
    @abstractmethod
    def _get_implementation_name(self) -> str:
        """Return the implementation name."""
        pass

    @abstractmethod
    def _get_binary_name(self) -> str:
        """Return the binary/executable name."""
        pass

    @abstractmethod
    def _get_server_specific_args(self, **kwargs) -> List[str]:
        """Return implementation-specific server arguments."""
        pass

    @abstractmethod
    def _get_client_specific_args(self, **kwargs) -> List[str]:
        """Return implementation-specific client arguments."""
        pass

    @abstractmethod
    def generate_deployment_commands(self) -> str:
        """Generate deployment commands for this implementation."""
        pass

    @abstractmethod
    def _do_prepare(self, plugin_manager=None):
        """Perform implementation-specific preparation."""
        pass

    # Template method for command generation
    def generate_run_command(self, **kwargs) -> str:
        """Generate run command using template method pattern.

        This method implements the template method pattern, providing a consistent
        workflow while allowing implementations to customize specific parts.
        """
        # Extract common MINIP parameters
        params = self._extract_common_params(**kwargs)

        # Build command based on role
        if params["role"] == "server":
            return self._build_server_command(params, **kwargs)
        elif params["role"] == "client":
            return self._build_client_command(params, **kwargs)
        else:
            raise ValueError(f"Unsupported role: {params['role']}")

    def _extract_common_params(self, **kwargs) -> Dict[str, Any]:
        """Extract common MINIP parameters from kwargs."""
        return {
            "role": kwargs.get("role", "server"),
            "host": kwargs.get("host", "localhost"),
            "port": kwargs.get("port", 8000),
            "protocol_version": kwargs.get("protocol_version", "1.0"),
            "timeout": kwargs.get("timeout", 30),
            "message_size": kwargs.get("message_size", 1024),
            "packet_size": kwargs.get("packet_size", 512),
            "debug_level": kwargs.get("debug_level", 0),
            "enable_logging": kwargs.get("enable_logging", True),
            "connection_type": kwargs.get("connection_type", "tcp"),
        }

    def _build_server_command(self, params: Dict[str, Any], **kwargs) -> str:
        """Build MINIP server command."""
        # Start with implementation binary
        cmd_parts = [self._get_binary_name()]

        # Add common server arguments
        cmd_parts.extend(self._build_common_server_args(params))

        # Add implementation-specific arguments
        cmd_parts.extend(self._get_server_specific_args(**kwargs))

        return " ".join(CommandUtils.quote_args(cmd_parts))

    def _build_client_command(self, params: Dict[str, Any], **kwargs) -> str:
        """Build MINIP client command."""
        # Start with implementation binary
        cmd_parts = [self._get_binary_name()]

        # Add common client arguments
        cmd_parts.extend(self._build_common_client_args(params))

        # Add implementation-specific arguments
        cmd_parts.extend(self._get_client_specific_args(**kwargs))

        return " ".join(CommandUtils.quote_args(cmd_parts))

    def _build_common_server_args(self, params: Dict[str, Any]) -> List[str]:
        """Build common MINIP server arguments."""
        args = []

        # Basic server configuration
        args.extend(["--server"])
        args.extend(["--port", str(params["port"])])
        args.extend(["--bind", params["host"]])

        # Protocol configuration
        args.extend(["--protocol-version", str(params["protocol_version"])])
        args.extend(["--connection-type", params["connection_type"]])

        # Message configuration
        args.extend(["--message-size", str(params["message_size"])])
        args.extend(["--packet-size", str(params["packet_size"])])

        # Timeout settings
        args.extend(["--timeout", str(params["timeout"])])

        # Debug configuration
        if params["debug_level"] > 0:
            args.extend(["--debug", str(params["debug_level"])])

        if params["enable_logging"]:
            args.append("--verbose")

        return args

    def _build_common_client_args(self, params: Dict[str, Any]) -> List[str]:
        """Build common MINIP client arguments."""
        args = []

        # Basic client configuration
        args.extend(["--client"])

        # Target configuration
        args.extend(["--connect", f"{params['host']}:{params['port']}"])

        # Protocol configuration
        args.extend(["--protocol-version", str(params["protocol_version"])])
        args.extend(["--connection-type", params["connection_type"]])

        # Message configuration
        args.extend(["--message-size", str(params["message_size"])])
        args.extend(["--packet-size", str(params["packet_size"])])

        # Timeout settings
        args.extend(["--timeout", str(params["timeout"])])

        # Debug configuration
        if params["debug_level"] > 0:
            args.extend(["--debug", str(params["debug_level"])])

        if params["enable_logging"]:
            args.append("--verbose")

        return args

    def get_supported_features(self) -> Dict[str, bool]:
        """Return implementation-specific feature support.

        Override this method to specify which MINIP features your implementation supports.
        """
        return {
            "tcp_connection": True,
            "udp_connection": False,
            "ping_pong": True,
            "streaming": False,
            "compression": False,
            "encryption": False,
            "flow_control": False,
        }

    def get_default_port(self) -> int:
        """Return the default port for MINIP."""
        return 8000

    def supports_tcp(self) -> bool:
        """Check if the implementation supports TCP connections."""
        return self.get_supported_features().get("tcp_connection", False)

    def supports_udp(self) -> bool:
        """Check if the implementation supports UDP connections."""
        return self.get_supported_features().get("udp_connection", False)

    def supports_ping_pong(self) -> bool:
        """Check if the implementation supports ping-pong messaging."""
        return self.get_supported_features().get("ping_pong", False)

    def supports_streaming(self) -> bool:
        """Check if the implementation supports streaming."""
        return self.get_supported_features().get("streaming", False)

    def supports_encryption(self) -> bool:
        """Check if the implementation supports encryption."""
        return self.get_supported_features().get("encryption", False)

    # Event emission helpers
    def emit_event(self, event):
        """Emit an event through the event manager."""
        if hasattr(self, "event_manager") and self.event_manager:
            self.event_manager.emit_event(event)

    # Utility methods for MINIP-specific operations
    def generate_test_message(self, size: int = None) -> str:
        """Generate a test message of specified size."""
        if size is None:
            size = 1024  # Default message size

        # Create a simple test message
        base_msg = "MINIP_TEST_MESSAGE_"
        padding_needed = size - len(base_msg) - 10  # Reserve space for counter

        if padding_needed > 0:
            padding = "x" * padding_needed
            return f"{base_msg}{padding}_END"
        else:
            return base_msg[: size - 4] + "_END"

    def validate_message_format(self, message: str) -> bool:
        """Validate that a message follows MINIP format."""
        # Basic validation - can be overridden by implementations
        return (
            isinstance(message, str)
            and len(message) > 0
            and len(message) <= 65536  # Max message size
        )

    def calculate_message_overhead(self, payload_size: int) -> int:
        """Calculate protocol overhead for a given payload size."""
        # Basic MINIP overhead calculation - can be overridden
        header_size = 16  # Basic header
        return header_size
