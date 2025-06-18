"""Base class for all HTTP service implementations."""

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Protocol

from panther.core.command_processor.command_utils import CommandUtils
from panther.plugins.services.services_interface import IServiceManager


class BaseHTTPServiceManager(IServiceManager, ABC):
    """
    Base class for HTTP protocol implementations.

    This class provides common functionality for HTTP service implementations,
    reducing code duplication across different HTTP service managers.
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
        """Initialize the base HTTP service manager.

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
        # Extract common HTTP parameters
        params = self._extract_common_params(**kwargs)

        # Build command based on role
        if params["role"] == "server":
            return self._build_server_command(params, **kwargs)
        elif params["role"] == "client":
            return self._build_client_command(params, **kwargs)
        else:
            raise ValueError(f"Unsupported role: {params['role']}")

    def _extract_common_params(self, **kwargs) -> Dict[str, Any]:
        """Extract common HTTP parameters from kwargs."""
        return {
            "role": kwargs.get("role", "server"),
            "host": kwargs.get("host", "localhost"),
            "port": kwargs.get("port", 80),
            "protocol_version": kwargs.get("protocol_version", "1.1"),
            "timeout": kwargs.get("timeout", 30),
            "content_type": kwargs.get("content_type", "text/html"),
            "method": kwargs.get("method", "GET"),
            "url_path": kwargs.get("url_path", "/"),
            "keep_alive": kwargs.get("keep_alive", False),
            "max_connections": kwargs.get("max_connections", 100),
        }

    def _build_server_command(self, params: Dict[str, Any], **kwargs) -> str:
        """Build HTTP server command."""
        # Start with implementation binary
        cmd_parts = [self._get_binary_name()]

        # Add common server arguments
        cmd_parts.extend(self._build_common_server_args(params))

        # Add implementation-specific arguments
        cmd_parts.extend(self._get_server_specific_args(**kwargs))

        return " ".join(CommandUtils.quote_args(cmd_parts))

    def _build_client_command(self, params: Dict[str, Any], **kwargs) -> str:
        """Build HTTP client command."""
        # Start with implementation binary
        cmd_parts = [self._get_binary_name()]

        # Add common client arguments
        cmd_parts.extend(self._build_common_client_args(params))

        # Add implementation-specific arguments
        cmd_parts.extend(self._get_client_specific_args(**kwargs))

        return " ".join(CommandUtils.quote_args(cmd_parts))

    def _build_common_server_args(self, params: Dict[str, Any]) -> List[str]:
        """Build common HTTP server arguments."""
        args = []

        # Basic server configuration
        args.extend(["--server"])
        args.extend(["--port", str(params["port"])])
        args.extend(["--bind", params["host"]])

        # HTTP version support
        if params["protocol_version"] == "2.0":
            args.append("--http2")
        elif params["protocol_version"] == "3.0":
            args.append("--http3")

        # Connection management
        if params["keep_alive"]:
            args.append("--keep-alive")
        args.extend(["--max-connections", str(params["max_connections"])])

        # Timeout settings
        args.extend(["--timeout", str(params["timeout"])])

        return args

    def _build_common_client_args(self, params: Dict[str, Any]) -> List[str]:
        """Build common HTTP client arguments."""
        args = []

        # Basic client configuration
        args.extend(["--client"])

        # Target configuration
        url = f"http://{params['host']}:{params['port']}{params['url_path']}"
        args.extend(["--url", url])

        # HTTP method
        args.extend(["--method", params["method"]])

        # HTTP version
        if params["protocol_version"] == "2.0":
            args.append("--http2")
        elif params["protocol_version"] == "3.0":
            args.append("--http3")

        # Connection settings
        if params["keep_alive"]:
            args.append("--keep-alive")

        # Timeout settings
        args.extend(["--timeout", str(params["timeout"])])

        return args

    def get_supported_features(self) -> Dict[str, bool]:
        """Return implementation-specific feature support.

        Override this method to specify which HTTP features your implementation supports.
        """
        return {
            "http_1_1": True,
            "http_2": False,
            "http_3": False,
            "keep_alive": True,
            "chunked_encoding": True,
            "compression": False,
            "tls": False,
        }

    def get_default_port(self) -> int:
        """Return the default port for HTTP."""
        return 80

    def get_tls_port(self) -> int:
        """Return the default port for HTTPS."""
        return 443

    def supports_tls(self) -> bool:
        """Check if the implementation supports TLS."""
        return self.get_supported_features().get("tls", False)

    def supports_http2(self) -> bool:
        """Check if the implementation supports HTTP/2."""
        return self.get_supported_features().get("http_2", False)

    def supports_http3(self) -> bool:
        """Check if the implementation supports HTTP/3."""
        return self.get_supported_features().get("http_3", False)

    # Event emission helpers
    def emit_event(self, event):
        """Emit an event through the event manager."""
        if hasattr(self, "event_manager") and self.event_manager:
            self.event_manager.emit_event(event)

    def __str__(self) -> str:
        """String representation of the service manager."""
        return f"{self.__class__.__name__}(implementation={self._get_implementation_name()})"

    def __repr__(self) -> str:
        """Developer representation of the service manager."""
        return (
            f"{self.__class__.__name__}("
            f"implementation={self._get_implementation_name()}, "
            f"service_type={self.service_type}, "
            f"protocol={getattr(self.protocol, 'name', 'unknown') if self.protocol else 'none'}"
            f")"
        )
