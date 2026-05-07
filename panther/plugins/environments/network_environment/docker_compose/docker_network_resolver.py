"""Docker Compose network resolver for network-aware command resolution.

This module provides Docker Compose-specific implementation of network
placeholder resolution using Docker DNS and runtime hostname resolution.
"""

import ipaddress
from typing import Dict

from panther.config.core.models.network_resolution import (
    NetworkAttribute,
    NetworkFormat,
    NetworkResolutionContext,
    NetworkServiceInfo,
    PlaceholderInfo,
)
from panther.core.exceptions import (
    NetworkDiscoveryException,
    ServiceResolutionException,
)

from ..base_network_resolver import BaseNetworkResolver


class DockerComposeNetworkResolver(BaseNetworkResolver):
    """Network resolver for Docker Compose environments."""

    def _initialize_environment_specific(self):
        """Docker Compose specific initialization."""
        # Docker Compose doesn't need additional initialization beyond base class
        pass

    def _generate_resolved_value(
        self, placeholder: PlaceholderInfo, service_info: NetworkServiceInfo
    ) -> str:
        """Generate resolved value for Docker Compose environment.

        Docker Compose strategy:
        - Primary IPs: use $(resolve_hostname service_name format) for runtime
          resolution by the entrypoint.sh script.
        - Secondary endpoints (Path α): inline the statically-assigned IP
          directly because docker-compose materializes them at compose-time
          via ipv4_address on the auxiliary network.

        Args:
            placeholder: Placeholder information
            service_info: Service network information

        Returns:
            Resolved value string
        """
        # Path α short-circuit: secondary endpoints get statically-inlined IPs.
        if placeholder.secondary_name is not None:
            ip = service_info.secondary_endpoints.get(placeholder.secondary_name)
            if ip is None:
                # Graceful degrade: tests that don't reference the secondary
                # endpoint receive a sentinel 0.0.0.0; tests that DO reference
                # it will fail loudly at runtime when binding/connecting.
                self.logger.warning(
                    "Secondary endpoint %r not configured for service %r; "
                    "using sentinel 0.0.0.0. Benign for tests that don't "
                    "reference the endpoint; tests that do will fail at "
                    "bind/connect time.",
                    placeholder.secondary_name,
                    service_info.service_name,
                )
                return self._format_ip("0.0.0.0", placeholder.format_type)
            return self._format_ip(ip, placeholder.format_type)

        service_name = service_info.service_name

        if placeholder.attribute == NetworkAttribute.IP:
            if placeholder.format_type == NetworkFormat.DECIMAL:
                return f"$(resolve_hostname {service_name} decimal)"
            elif placeholder.format_type == NetworkFormat.DOTTED:
                return f"$(resolve_hostname {service_name} dotted)"
            elif placeholder.format_type == NetworkFormat.HEX:
                return f"$(resolve_hostname {service_name} hex)"
            else:
                return f"$(resolve_hostname {service_name} dotted)"

        elif placeholder.attribute == NetworkAttribute.HOSTNAME:
            # Docker Compose uses service name as hostname
            return service_name

        elif placeholder.attribute == NetworkAttribute.SERVICE_NAME:
            return service_name

        elif placeholder.attribute == NetworkAttribute.PORT:
            if service_info.port:
                return str(service_info.port)
            else:
                # For Docker Compose, ports are typically handled by docker-compose.yml
                # Return placeholder for dynamic resolution if needed
                return f"$(get_service_port {service_name})"

        else:
            raise ServiceResolutionException(
                f"Unsupported attribute for Docker Compose: {placeholder.attribute}",
                service_name,
                placeholder.attribute.value,
                placeholder.format_type.value,
            )

    def get_service_ip(
        self, service_name: str, context: NetworkResolutionContext
    ) -> str:
        """Get IP address for a service in Docker Compose environment.

        Args:
            service_name: Name of the service
            context: Network resolution context

        Returns:
            Runtime resolution command for Docker Compose
        """
        # Docker Compose uses runtime resolution
        return f"$(resolve_hostname {service_name} dotted)"

    def get_service_info(
        self, service_name: str, context: NetworkResolutionContext
    ) -> NetworkServiceInfo:
        """Get service information for Docker Compose service.

        Args:
            service_name: Name of the service
            context: Network resolution context

        Returns:
            Network service information
        """
        service_info = context.get_service_info(service_name)

        if not service_info:
            # Create basic service info for Docker Compose
            service_info = NetworkServiceInfo(
                service_name=service_name,
                hostname=service_name,  # Docker uses service name as hostname
                additional_info={
                    "docker_compose_service": "true",
                    "dns_resolution": "automatic",
                },
            )
            context.add_service(service_info)

        return service_info

    def populate_service_network_info(self, context: NetworkResolutionContext) -> None:
        """Populate network information for Docker Compose services.

        For Docker Compose, this method ensures all services have basic
        network information with runtime resolution capabilities.

        Args:
            context: Network resolution context to populate
        """
        try:
            # Ensure all services have hostname set to service name
            for service_name, service_info in context.available_services.items():
                if not service_info.hostname:
                    service_info.hostname = service_name

                # Add Docker Compose specific metadata
                service_info.additional_info.update(
                    {
                        "docker_compose_service": "true",
                        "dns_resolution": "automatic",
                        "ip_resolution": "runtime",
                    }
                )

            self.logger.debug(
                f"Populated network info for {len(context.available_services)} services"
            )

        except Exception as e:
            raise NetworkDiscoveryException(
                f"Failed to populate service network info: {str(e)}",
                "docker_compose_service_discovery",
                "docker_compose",
                str(e),
            )

    def supports_runtime_resolution(self) -> bool:
        """Check if this resolver supports runtime resolution."""
        return True

    def get_resolution_capabilities(self) -> Dict[str, bool]:
        """Get capabilities of this resolver."""
        return {
            "runtime_ip_resolution": True,
            "static_ip_resolution": False,
            "hostname_resolution": True,
            "port_resolution": True,
            "service_name_resolution": True,
            "decimal_ip_format": True,
            "dotted_ip_format": True,
            "hex_ip_format": True,
        }

    # Abstract method implementations required by BaseNetworkResolver

    def _get_environment_name(self) -> str:
        """Get environment name for Docker Compose."""
        return "docker_compose"

    def _get_resolution_method(self) -> str:
        """Get Docker Compose resolution method."""
        return "docker_compose_runtime"

    def _create_default_service_info(
        self, placeholder: PlaceholderInfo
    ) -> NetworkServiceInfo:
        """Create Docker Compose specific default service info."""
        return NetworkServiceInfo(
            service_name=placeholder.service,
            hostname=placeholder.service,  # Docker Compose uses service name as hostname
            additional_info={
                "docker_compose_service": "true",
                "dns_resolution": "automatic",
            },
        )

    @staticmethod
    def _format_ip(ip_str: str, format_type: NetworkFormat) -> str:
        """Format an IPv4 address per the requested NetworkFormat.

        Local helper for Path α secondary-endpoint resolution. Does NOT import
        IvyNetworkResolutionMixin._format_ip_hex from the panther_ivy submodule
        to keep the outer-worktree resolver independent of submodule code.
        """
        addr = ipaddress.IPv4Address(ip_str)
        if format_type == NetworkFormat.HEX:
            return f"0x{int(addr):08x}"
        if format_type == NetworkFormat.DECIMAL:
            return str(int(addr))
        # Default / DOTTED / others
        return str(addr)
