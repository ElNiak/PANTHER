"""
Shadow NS network resolver for network-aware command resolution.

This module provides Shadow NS-specific implementation of network
placeholder resolution using static IP assignment following Shadow networking patterns.
"""

from typing import Dict, List

from panther.config.core.models.network_resolution import (
    NetworkAttribute,
    NetworkFormat,
    NetworkResolutionContext,
    NetworkResolutionResult,
    NetworkServiceInfo,
    PlaceholderInfo,
)
from panther.core.exceptions.network_resolution_exceptions import (
    NetworkDiscoveryException,
    ServiceResolutionException,
)

from ..base_network_resolver import BaseNetworkResolver


class ShadowNetworkResolver(BaseNetworkResolver):
    """Network resolver for Shadow NS environments."""

    def _initialize_environment_specific(self):
        """Shadow NS specific initialization."""
        # Shadow NS static IP assignment strategy
        # Based on shadow-template.jinja patterns
        self.server_ip = "11.0.0.1"  # Servers get this IP
        self.client_ip = "11.0.0.2"  # Clients get this IP
        self.default_port = 4433  # Default port for services

        # Service role registry for IP assignment
        self.service_roles: Dict[str, str] = {}  # service_name -> role

    def _resolve_single_placeholder(
        self, placeholder: PlaceholderInfo, context: NetworkResolutionContext
    ) -> NetworkResolutionResult:
        """
        Resolve a single placeholder for Shadow NS environment.

        Args:
            placeholder: Placeholder information to resolve
            context: Network resolution context

        Returns:
            Network resolution result
        """
        # Use base class validation
        self._validate_placeholder(placeholder)

        # Use base class service info handling
        service_info = self._ensure_service_info(placeholder, context)

        # Generate resolved value using environment-specific logic
        resolved_value = self._generate_resolved_value(placeholder, service_info)

        # Use base class result creation
        return self._create_resolution_result(placeholder, resolved_value, service_info)

    def _get_service_ip_by_role(self, service_name: str) -> str:
        """
        Get IP address for service based on its role following Shadow patterns.

        Args:
            service_name: Name of the service

        Returns:
            IP address based on service role
        """
        role = self.service_roles.get(service_name, "server")  # Default to server

        if role == "client":
            return self.client_ip
        else:
            return self.server_ip

    def _generate_resolved_value(
        self, placeholder: PlaceholderInfo, service_info: NetworkServiceInfo
    ) -> str:
        """
        Generate resolved value for Shadow NS environment.

        Shadow NS strategy:
        - IP: Use static assignment (11.0.0.1 for servers, 11.0.0.2 for clients)
        - Port: Use default port or service-specific port
        - Hostname: Use assigned IP address

        Args:
            placeholder: Placeholder information
            service_info: Service network information

        Returns:
            Resolved value string
        """
        if placeholder.attribute == NetworkAttribute.IP:
            return self._format_ip_address(
                service_info.ip_address, placeholder.format_type
            )

        elif placeholder.attribute == NetworkAttribute.HOSTNAME:
            # For Shadow NS, hostname is the assigned IP
            return service_info.ip_address

        elif placeholder.attribute == NetworkAttribute.SERVICE_NAME:
            return service_info.service_name

        elif placeholder.attribute == NetworkAttribute.PORT:
            if service_info.port:
                return str(service_info.port)
            else:
                return str(self.default_port)

        else:
            raise ServiceResolutionException(
                f"Unsupported attribute for Shadow NS: {placeholder.attribute}",
                service_info.service_name,
                placeholder.attribute.value,
                placeholder.format_type.value,
            )

    def _format_ip_address(self, ip_address: str, format_type: NetworkFormat) -> str:
        """
        Format Shadow NS IP address in requested format.

        Args:
            ip_address: IP address to format (e.g., "11.0.0.1")
            format_type: Requested format (dotted, decimal, string, etc.)

        Returns:
            Formatted IP address string
        """
        if format_type == NetworkFormat.DOTTED or format_type == NetworkFormat.STRING:
            return ip_address

        elif format_type == NetworkFormat.DECIMAL:
            # Convert IP to decimal format
            # Example: 11.0.0.1 = (11 << 24) + (0 << 16) + (0 << 8) + 1
            octets = ip_address.split(".")
            decimal_value = (
                (int(octets[0]) << 24)
                + (int(octets[1]) << 16)
                + (int(octets[2]) << 8)
                + int(octets[3])
            )
            return str(decimal_value)

        elif format_type == NetworkFormat.HOSTNAME:
            # For Shadow NS, hostname is the IP
            return ip_address

        elif format_type == NetworkFormat.INTEGER:
            # Same as decimal for compatibility
            octets = ip_address.split(".")
            decimal_value = (
                (int(octets[0]) << 24)
                + (int(octets[1]) << 16)
                + (int(octets[2]) << 8)
                + int(octets[3])
            )
            return str(decimal_value)

        else:
            # Default to dotted notation
            return ip_address

    def get_service_ip(
        self, service_name: str, context: NetworkResolutionContext
    ) -> str:
        """
        Get IP address for a service in Shadow NS environment.

        Args:
            service_name: Name of the service
            context: Network resolution context

        Returns:
            IP address based on service role
        """
        return self._get_service_ip_by_role(service_name)

    def get_service_info(
        self, service_name: str, context: NetworkResolutionContext
    ) -> NetworkServiceInfo:
        """
        Get service information for Shadow NS service.

        Args:
            service_name: Name of the service
            context: Network resolution context

        Returns:
            Network service information
        """
        service_info = context.get_service_info(service_name)

        if not service_info:
            # Create service info with Shadow-specific assignment
            service_ip = self._get_service_ip_by_role(service_name)

            service_info = NetworkServiceInfo(
                service_name=service_name,
                hostname=service_ip,
                ip_address=service_ip,
                port=self.default_port,
                additional_info={
                    "environment": "shadow_ns",
                    "ip_assignment": "static_shadow_pattern",
                    "role": self.service_roles.get(service_name, "unknown"),
                    "server_ip": self.server_ip,
                    "client_ip": self.client_ip,
                },
            )
            context.add_service(service_info)

        return service_info

    def populate_service_network_info(self, context: NetworkResolutionContext) -> None:
        """
        Populate network information for Shadow NS services.

        For Shadow NS, this method ensures all services have proper
        IP assignments based on their roles (client vs server).

        Args:
            context: Network resolution context to populate
        """
        try:
            # Ensure all services have proper Shadow NS configuration
            for service_name, service_info in context.available_services.items():
                role = self.service_roles.get(service_name, "server")
                assigned_ip = self.client_ip if role == "client" else self.server_ip

                if not service_info.hostname:
                    service_info.hostname = assigned_ip

                if not service_info.ip_address:
                    service_info.ip_address = assigned_ip

                if not service_info.port:
                    service_info.port = self.default_port

                # Add Shadow NS-specific metadata
                service_info.additional_info.update(
                    {
                        "environment": "shadow_ns",
                        "ip_assignment": "static_shadow_pattern",
                        "role": role,
                        "assigned_ip": assigned_ip,
                    }
                )

            self.logger.debug(
                f"Populated Shadow NS network info for {len(context.available_services)} services"
            )

        except Exception as e:
            raise NetworkDiscoveryException(
                f"Failed to populate service network info: {str(e)}",
                "shadow_service_discovery",
                "shadow_ns",
                str(e),
            )

    def register_service_roles(self, service_roles: Dict[str, str]) -> None:
        """
        Register service roles for IP assignment.

        Args:
            service_roles: Dictionary mapping service name to role (client/server)
        """
        self.service_roles.update(service_roles)
        self.logger.debug(
            f"Registered roles for {len(service_roles)} Shadow NS services"
        )

    def get_service_roles(self) -> Dict[str, str]:
        """Get copy of current service roles."""
        return self.service_roles.copy()

    def supports_runtime_resolution(self) -> bool:
        """Check if this resolver supports runtime resolution."""
        return False  # Shadow NS uses static assignment

    # Abstract method implementations required by BaseNetworkResolver

    def _get_environment_name(self) -> str:
        """Get environment name for Shadow NS."""
        return "shadow_ns"

    def _get_resolution_method(self) -> str:
        """Get Shadow NS resolution method."""
        return "shadow_static"

    def _create_default_service_info(
        self, placeholder: PlaceholderInfo
    ) -> NetworkServiceInfo:
        """
        Create Shadow NS specific default service info.

        For Shadow NS, creates service info with static IP assignment based on service role.

        Args:
            placeholder: Placeholder requiring service info

        Returns:
            Default service info for Shadow NS environment
        """
        # Get IP assignment based on service role
        service_ip = self._get_service_ip_by_role(placeholder.service)

        return NetworkServiceInfo(
            service_name=placeholder.service,
            hostname=service_ip,
            ip_address=service_ip,
            port=self.default_port,
            additional_info={
                "environment": "shadow_ns",
                "ip_assignment": "static_shadow_pattern",
                "role": self.service_roles.get(placeholder.service, "unknown"),
            },
        )

    def get_resolution_capabilities(self) -> Dict[str, bool]:
        """Get capabilities of this resolver."""
        return {
            "runtime_ip_resolution": False,
            "static_ip_resolution": True,
            "hostname_resolution": True,
            "port_resolution": True,
            "service_name_resolution": True,
            "decimal_ip_format": True,
            "dotted_ip_format": True,
            "string_ip_format": True,
            "integer_ip_format": True,
            "role_based_assignment": True,
        }

    def create_resolution_context(
        self, environment_type: str, service_managers: Dict[str, "IServiceManager"]
    ) -> NetworkResolutionContext:
        """
        Create network resolution context for Shadow NS environment.

        Args:
            environment_type: Type of environment (should be "shadow_ns")
            service_managers: Dictionary of service managers by name

        Returns:
            Network resolution context
        """
        from panther.plugins.services.services_interface import IServiceManager

        context = NetworkResolutionContext(environment_type=environment_type)

        # Add all services to context with Shadow NS-specific network info
        for service_name, service_manager in service_managers.items():
            # Try to determine role from service manager
            role = "server"  # Default
            if hasattr(service_manager, "role") and service_manager.role:
                role = getattr(service_manager.role, "name", "server").lower()

            # Register the role
            self.service_roles[service_name] = role

            # Assign IP based on role
            assigned_ip = self.client_ip if role == "client" else self.server_ip

            service_info = NetworkServiceInfo(
                service_name=service_name,
                hostname=assigned_ip,
                ip_address=assigned_ip,
                port=self.default_port,
                additional_info={
                    "environment": environment_type,
                    "ip_assignment": "static_shadow_pattern",
                    "role": role,
                    "assigned_ip": assigned_ip,
                },
            )
            context.add_service(service_info)

        self.logger.debug(
            f"Created Shadow NS resolution context for {len(service_managers)} services"
        )
        return context
