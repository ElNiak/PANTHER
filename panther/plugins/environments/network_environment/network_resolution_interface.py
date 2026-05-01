"""
Interface for network-aware command resolution.

This module defines the interface that network environments must implement
to support network placeholder resolution.
"""

from abc import ABC, abstractmethod
from typing import Dict, List

from panther.config.core.models.network_resolution import (
    NetworkResolutionContext,
    NetworkResolutionResult,
    NetworkServiceInfo,
    PlaceholderInfo,
)


class INetworkResolver(ABC):
    """Interface for network-aware command resolution."""

    @abstractmethod
    def resolve_network_placeholders(
        self, command_template: str, context: NetworkResolutionContext
    ) -> List[NetworkResolutionResult]:
        """
        Resolve network placeholders in a command template.

        Args:
            command_template: Command template with placeholders
            context: Network resolution context

        Returns:
            List of resolution results

        Raises:
            NetworkResolutionException: If resolution fails
        """
        pass

    @abstractmethod
    def get_service_ip(
        self, service_name: str, context: NetworkResolutionContext
    ) -> str:
        """
        Get IP address for a service.

        Args:
            service_name: Name of the service
            context: Network resolution context

        Returns:
            IP address as string

        Raises:
            ServiceResolutionException: If service not found or resolution fails
        """
        pass

    @abstractmethod
    def get_service_info(
        self, service_name: str, context: NetworkResolutionContext
    ) -> NetworkServiceInfo:
        """
        Get comprehensive network information for a service.

        Args:
            service_name: Name of the service
            context: Network resolution context

        Returns:
            Network service information

        Raises:
            ServiceResolutionException: If service not found
        """
        pass

    @abstractmethod
    def populate_service_network_info(self, context: NetworkResolutionContext) -> None:
        """
        Populate network information for all services in context.

        This method should discover and populate network information
        for all services using environment-specific mechanisms.

        Args:
            context: Network resolution context to populate

        Raises:
            NetworkDiscoveryException: If discovery fails
        """
        pass

    def create_resolution_context(
        self, environment_type: str, service_managers: Dict[str, any] = None
    ) -> NetworkResolutionContext:
        """
        Create a network resolution context for this environment.

        Args:
            environment_type: Type of network environment
            service_managers: Optional service manager instances

        Returns:
            Initialized network resolution context
        """
        context = NetworkResolutionContext(
            environment_type=environment_type,
            available_services={},
            resolution_config={},
        )

        # If service managers provided, extract basic service info
        if service_managers:
            for service_name, manager in service_managers.items():
                service_info = NetworkServiceInfo(
                    service_name=service_name,
                    protocol_role=getattr(manager, "protocol_role", None),
                    secondary_endpoints=getattr(manager, "secondary_endpoints", {})
                    or {},
                )
                context.add_service(service_info)

        return context

    def validate_resolution_support(
        self, placeholders: List[PlaceholderInfo]
    ) -> List[str]:
        """
        Validate that this resolver can handle the given placeholders.

        Args:
            placeholders: List of placeholders to validate

        Returns:
            List of error messages for unsupported placeholders
        """
        errors = []

        for placeholder in placeholders:
            # Basic validation - subclasses can override for specific checks
            if not placeholder.service:
                errors.append(
                    f"Empty service name in placeholder: {placeholder.raw_placeholder}"
                )

        return errors
