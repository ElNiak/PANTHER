"""
Localhost network resolver for network-aware command resolution.

This module provides localhost-specific implementation of network
placeholder resolution using calculated IP/port assignments for single container environment.
"""

from typing import Dict, List

from panther.config.core.models.network_resolution import (
    NetworkAttribute,
    NetworkFormat,
    NetworkResolutionContext,
    NetworkServiceInfo,
    PlaceholderInfo,
)
from panther.core.exceptions.network_resolution_exceptions import (
    NetworkDiscoveryException,
    ServiceResolutionException,
)

from ..base_network_resolver import BaseNetworkResolver


class LocalhostNetworkResolver(BaseNetworkResolver):
    """Network resolver for localhost single container environments."""

    def _initialize_environment_specific(self):
        """Localhost specific initialization."""
        # Service registry for consistent port assignment
        self.service_registry: Dict[str, int] = {}  # service_name -> index
        self.base_port = 5000
        self.port_offset = 10

        # Localhost constants
        self.localhost_ip = "127.0.0.1"

    def _get_service_index(
        self, service_name: str, context: NetworkResolutionContext
    ) -> int:
        """
        Get or assign service index for consistent port calculation.

        Args:
            service_name: Name of the service
            context: Network resolution context

        Returns:
            Service index for port calculation
        """
        if service_name not in self.service_registry:
            # Assign next available index
            self.service_registry[service_name] = len(self.service_registry)
            self.logger.debug(
                f"Assigned index {self.service_registry[service_name]} to service {service_name}"
            )

        return self.service_registry[service_name]

    def _calculate_port(self, service_index: int) -> int:
        """
        Calculate port for service based on index.

        Args:
            service_index: Index of the service

        Returns:
            Calculated port number
        """
        return self.base_port + (service_index * self.port_offset)

    def _generate_resolved_value(
        self, placeholder: PlaceholderInfo, service_info: NetworkServiceInfo
    ) -> str:
        """
        Generate resolved value for localhost environment.

        Localhost strategy:
        - IP: Always 127.0.0.1 (in requested format)
        - Port: Calculated from service index
        - Hostname: 127.0.0.1 or service name based on context

        Args:
            placeholder: Placeholder information
            service_info: Service network information

        Returns:
            Resolved value string
        """
        if placeholder.attribute == NetworkAttribute.IP:
            return self._format_ip_address(placeholder.format_type)

        elif placeholder.attribute == NetworkAttribute.HOSTNAME:
            # For localhost, hostname can be either IP or service name
            return self.localhost_ip

        elif placeholder.attribute == NetworkAttribute.SERVICE_NAME:
            return service_info.service_name

        elif placeholder.attribute == NetworkAttribute.PORT:
            if service_info.port:
                return str(service_info.port)
            else:
                # Calculate port on demand if not set
                service_index = int(
                    service_info.additional_info.get("service_index", "0")
                )
                calculated_port = self._calculate_port(service_index)
                return str(calculated_port)

        else:
            raise ServiceResolutionException(
                f"Unsupported attribute for localhost: {placeholder.attribute}",
                service_info.service_name,
                placeholder.attribute.value,
                placeholder.format_type.value,
            )

    def _format_ip_address(self, format_type: NetworkFormat) -> str:
        """
        Format localhost IP address in requested format.

        Args:
            format_type: Requested format (dotted, decimal, string, etc.)

        Returns:
            Formatted IP address string
        """
        if format_type == NetworkFormat.DOTTED or format_type == NetworkFormat.STRING:
            return self.localhost_ip

        elif format_type == NetworkFormat.DECIMAL:
            # Convert 127.0.0.1 to decimal: (127 << 24) + (0 << 16) + (0 << 8) + 1
            return str((127 << 24) + 1)  # 2130706433

        elif format_type == NetworkFormat.HOSTNAME:
            # For localhost, hostname is the IP
            return self.localhost_ip

        elif format_type == NetworkFormat.INTEGER:
            # Same as decimal for compatibility
            return str((127 << 24) + 1)  # 2130706433

        else:
            # Default to dotted notation
            return self.localhost_ip

    def get_service_ip(
        self, service_name: str, context: NetworkResolutionContext
    ) -> str:
        """
        Get IP address for a service in localhost environment.

        Args:
            service_name: Name of the service
            context: Network resolution context

        Returns:
            IP address (always 127.0.0.1 for localhost)
        """
        return self.localhost_ip

    def get_service_info(
        self, service_name: str, context: NetworkResolutionContext
    ) -> NetworkServiceInfo:
        """
        Get service information for localhost service.

        Args:
            service_name: Name of the service
            context: Network resolution context

        Returns:
            Network service information
        """
        service_info = context.get_service_info(service_name)

        if not service_info:
            # Create placeholder for service info creation
            from panther.config.core.models.network_resolution import (
                NetworkAttribute,
                NetworkFormat,
                PlaceholderInfo,
            )

            placeholder = PlaceholderInfo(
                raw_placeholder=f"{{{{host {service_name} dotted}}}}",
                service=service_name,
                attribute=NetworkAttribute.IP,
                format_type=NetworkFormat.DOTTED,
            )
            service_info = self._create_default_service_info(placeholder)
            context.add_service(service_info)

        return service_info

    def populate_service_network_info(self, context: NetworkResolutionContext) -> None:
        """
        Populate network information for localhost services.

        For localhost, this method ensures all services have calculated
        IP and port assignments with consistent indexing.

        Args:
            context: Network resolution context to populate
        """
        try:
            # Ensure all services have proper localhost configuration
            for service_name, service_info in context.available_services.items():
                if not service_info.hostname:
                    service_info.hostname = self.localhost_ip

                if not service_info.ip_address:
                    service_info.ip_address = self.localhost_ip

                if not service_info.port:
                    service_index = self._get_service_index(service_name, context)
                    service_info.port = self._calculate_port(service_index)

                # Add localhost-specific metadata
                service_info.additional_info.update(
                    {
                        "environment": "localhost_single_container",
                        "ip_resolution": "static_localhost",
                        "port_resolution": "calculated",
                    }
                )

            self.logger.debug(
                f"Populated network info for {len(context.available_services)} localhost services"
            )

        except Exception as e:
            raise NetworkDiscoveryException(
                f"Failed to populate service network info: {str(e)}",
                "localhost_service_discovery",
                "localhost_single_container",
                str(e),
            )

    def register_services(self, service_names: List[str]) -> None:
        """
        Register services for consistent index assignment.

        Args:
            service_names: List of service names to register
        """
        for service_name in service_names:
            if service_name not in self.service_registry:
                self.service_registry[service_name] = len(self.service_registry)

        self.logger.debug(
            f"Registered {len(service_names)} services in localhost registry"
        )

    def get_service_registry(self) -> Dict[str, int]:
        """Get copy of current service registry."""
        return self.service_registry.copy()

    def supports_runtime_resolution(self) -> bool:
        """Check if this resolver supports runtime resolution."""
        return False  # Localhost uses static calculation

    def _get_environment_name(self) -> str:
        """Get environment name for exception handling and logging."""
        return "localhost_single_container"

    def _get_resolution_method(self) -> str:
        """Get environment-specific resolution method name."""
        return "localhost_calculated"

    def _create_default_service_info(
        self, placeholder: PlaceholderInfo
    ) -> NetworkServiceInfo:
        """
        Create environment-specific default service info.

        For localhost, creates service info with localhost IP and calculated ports.

        Args:
            placeholder: Placeholder requiring service info

        Returns:
            Default service info for localhost environment
        """
        # Direct service index assignment without context dependency
        if placeholder.service not in self.service_registry:
            self.service_registry[placeholder.service] = len(self.service_registry)

        service_index = self.service_registry[placeholder.service]
        calculated_port = self._calculate_port(service_index)

        return NetworkServiceInfo(
            service_name=placeholder.service,
            hostname=self.localhost_ip,
            ip_address=self.localhost_ip,
            port=calculated_port,
            additional_info={
                "service_index": str(service_index),
                "environment": self._get_environment_name(),
                "port_calculation": f"{self.base_port} + ({service_index} * {self.port_offset})",
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
            "calculated_ports": True,
        }

    def create_resolution_context(
        self, environment_type: str, service_managers: Dict[str, "IServiceManager"]
    ) -> NetworkResolutionContext:
        """
        Create network resolution context for localhost environment.

        Args:
            environment_type: Type of environment (should be "localhost_single_container")
            service_managers: Dictionary of service managers by name

        Returns:
            Network resolution context
        """
        from panther.config.core.models.network_resolution import (
            NetworkAttribute,
            NetworkFormat,
            PlaceholderInfo,
        )
        from panther.plugins.services.services_interface import IServiceManager

        context = NetworkResolutionContext(environment_type=environment_type)

        # Add all services to context using consistent service info creation
        for service_name, service_manager in service_managers.items():
            # Create placeholder for service info generation
            placeholder = PlaceholderInfo(
                raw_placeholder=f"{{{{host {service_name} dotted}}}}",
                service=service_name,
                attribute=NetworkAttribute.IP,
                format_type=NetworkFormat.DOTTED,
            )
            service_info = self._create_default_service_info(placeholder)
            context.add_service(service_info)

        self.logger.debug(
            f"Created resolution context for {len(service_managers)} localhost services"
        )
        return context
