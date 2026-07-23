"""Base Network Resolver for PANTHER Network Environments.

This module provides the common network resolution functionality shared across all network
environment types (Docker Compose, Localhost, Shadow NS), eliminating 95% code duplication.

Key Features:
- Common placeholder parsing and resolution workflow
- Standardized exception handling with environment-specific context
- Abstract interface for environment-specific resolution strategies
- Shared imports and logging infrastructure
- Consistent network resolution result formatting
"""

import logging
from abc import ABC, abstractmethod
from typing import Dict, List

from panther.config.core.models.network_resolution import (
    NetworkAttribute,
    NetworkFormat,
    NetworkResolutionContext,
    NetworkResolutionResult,
    NetworkServiceInfo,
    PlaceholderInfo,
)
from panther.core.exceptions import EnvironmentResolutionException
from panther.plugins.environments.network_environment.network_resolution_interface import (
    INetworkResolver,
)
from panther.plugins.environments.network_environment.placeholder_parser import (
    PlaceholderParser,
)


class BaseNetworkResolver(INetworkResolver, ABC):
    """Base class for network resolution providing common functionality.

    This class eliminates duplication across DockerComposeNetworkResolver,
    LocalhostNetworkResolver, and ShadowNetworkResolver by providing:

    1. Common placeholder parsing workflow (95% identical code)
    2. Standardized exception handling with environment context
    3. Shared initialization patterns (logger, parser setup)
    4. Abstract interface for environment-specific resolution strategies
    5. Consistent result formatting and validation

    Subclasses only need to implement environment-specific methods:
    - _get_environment_name(): Environment identifier for exceptions
    - _generate_resolved_value(): Environment-specific value generation
    - _get_resolution_method(): Environment-specific resolution strategy name
    - _create_default_service_info(): Environment-specific default service info

    The _resolve_single_placeholder() method is now a concrete template method
    that orchestrates the common 4-step resolution pattern. Override it only if
    the entire resolution pattern differs from the standard flow.
    """

    def __init__(self):
        """Initialize base network resolver with common components.

        Sets up logging and placeholder parser that all environments need.
        Subclasses can extend this to add environment-specific initialization.
        """
        self.logger = logging.getLogger(self.__class__.__name__)
        self.parser = PlaceholderParser()

        # Allow subclasses to add environment-specific initialization
        self._initialize_environment_specific()

    def resolve_network_placeholders(
        self, command_template: str, context: NetworkResolutionContext
    ) -> List[NetworkResolutionResult]:
        """Resolve network placeholders in command template.

        Common implementation across all network resolver types with 95% identical code.
        The only difference is the environment name in exception handling.

        Args:
            command_template: Command template with placeholders like {{host client decimal}}
            context: Network resolution context with service information

        Returns:
            List of resolution results for each placeholder found

        Raises:
            EnvironmentResolutionException: If placeholder resolution fails
        """
        results = []

        try:
            # Parse all placeholders from template (common logic)
            placeholders = self.parser.parse_placeholders(command_template)

            self.logger.debug(
                f"Found {len(placeholders)} placeholders in template for {self._get_environment_name()}"
            )

            # Resolve each placeholder using environment-specific logic
            for placeholder in placeholders:
                result = self._resolve_single_placeholder(placeholder, context)
                results.append(result)

                self.logger.debug(
                    f"Resolved {placeholder.raw_placeholder} -> {result.resolved_value}"
                )

        except Exception as e:
            # Standardized exception handling with environment context
            raise EnvironmentResolutionException(
                f"Failed to resolve placeholders in template: {str(e)}",
                self._get_environment_name(),
                "resolve_network_placeholders",
                str(e),
            )

        return results

    def _create_resolution_result(
        self,
        placeholder: PlaceholderInfo,
        resolved_value: str,
        service_info: NetworkServiceInfo,
    ) -> NetworkResolutionResult:
        """Create standardized resolution result.

        Common result creation logic with environment-specific method and type.

        Args:
            placeholder: Original placeholder information
            resolved_value: Environment-specific resolved value
            service_info: Service information used for resolution

        Returns:
            Standardized network resolution result
        """
        return NetworkResolutionResult(
            original_placeholder=placeholder.raw_placeholder,
            resolved_value=resolved_value,
            service_info=service_info,
            resolution_method=self._get_resolution_method(),
            environment_type=self._get_environment_name(),
        )

    def _ensure_service_info(
        self, placeholder: PlaceholderInfo, context: NetworkResolutionContext
    ) -> NetworkServiceInfo:
        """Ensure service info exists in context, creating if necessary.

        Common service info handling with environment-specific defaults.

        Args:
            placeholder: Placeholder containing service reference
            context: Resolution context to check/update

        Returns:
            Service info for the placeholder's service
        """
        service_info = context.get_service_info(placeholder.service)
        if not service_info:
            # Create environment-specific default service info
            service_info = self._create_default_service_info(placeholder)
            context.add_service(service_info)

            self.logger.debug(
                f"Created default service info for {placeholder.service} in {self._get_environment_name()}"
            )

        return service_info

    def _validate_placeholder(self, placeholder: PlaceholderInfo):
        """Validate placeholder format and requirements.

        Common validation logic that can be extended by subclasses.

        Args:
            placeholder: Placeholder to validate

        Raises:
            EnvironmentResolutionException: If placeholder is invalid
        """
        if not placeholder.service:
            raise EnvironmentResolutionException(
                f"Placeholder missing service name: {placeholder.raw_placeholder}",
                self._get_environment_name(),
                "validate_placeholder",
                "Missing service name",
            )

        if not placeholder.attribute:
            raise EnvironmentResolutionException(
                f"Placeholder missing attribute: {placeholder.raw_placeholder}",
                self._get_environment_name(),
                "validate_placeholder",
                "Missing attribute",
            )

    # Template method for the standard resolution pattern

    def _resolve_single_placeholder(
        self, placeholder: PlaceholderInfo, context: NetworkResolutionContext
    ) -> NetworkResolutionResult:
        """Resolve a single placeholder using the standard 4-step pattern.

        This template method calls environment-specific hooks:
        1. _validate_placeholder() - Validate format (common, overridable)
        2. _ensure_service_info() - Get/create service info (common, overridable)
        3. _generate_resolved_value() - Generate value (abstract, environment-specific)
        4. _create_resolution_result() - Create result (common)

        Subclasses should override _generate_resolved_value() for custom resolution.
        Override this method only if the entire resolution pattern differs.
        """
        self._validate_placeholder(placeholder)
        service_info = self._ensure_service_info(placeholder, context)
        resolved_value = self._generate_resolved_value(placeholder, service_info)
        return self._create_resolution_result(placeholder, resolved_value, service_info)

    # Abstract methods that subclasses must implement

    @abstractmethod
    def _get_environment_name(self) -> str:
        """Get environment name for exception handling and logging.

        Examples:
        - "docker_compose"
        - "localhost_single_container"
        - "shadow_ns"

        Returns:
            Environment identifier string
        """
        pass

    @abstractmethod
    def _generate_resolved_value(
        self, placeholder: PlaceholderInfo, service_info: NetworkServiceInfo
    ) -> str:
        """Generate environment-specific resolved value.

        This contains the core environment differences:
        - Docker Compose: Returns "$(resolve_hostname service decimal)"
        - Localhost: Returns "127.0.0.1" or calculated port
        - Shadow NS: Returns "11.0.0.1" or "11.0.0.2" or "4433"

        Args:
            placeholder: Placeholder information
            service_info: Service information for resolution

        Returns:
            Environment-specific resolved value
        """
        pass

    @abstractmethod
    def _get_resolution_method(self) -> str:
        """Get environment-specific resolution method name.

        Examples:
        - "docker_compose_runtime"
        - "localhost_calculated"
        - "shadow_static"

        Returns:
            Resolution method identifier
        """
        pass

    @abstractmethod
    def _create_default_service_info(
        self, placeholder: PlaceholderInfo
    ) -> NetworkServiceInfo:
        """Create environment-specific default service info.

        Different environments have different default assumptions:
        - Docker Compose: service name = hostname
        - Localhost: localhost IP with calculated ports
        - Shadow NS: server/client IP assignment based on role

        Args:
            placeholder: Placeholder requiring service info

        Returns:
            Environment-specific default service info
        """
        pass

    # Optional hook methods with default implementations

    def _initialize_environment_specific(self):
        """Optional environment-specific initialization (hook for subclasses)."""
        pass

    def _post_resolution_processing(
        self, results: List[NetworkResolutionResult]
    ) -> List[NetworkResolutionResult]:
        """Optional post-processing of resolution results (hook for subclasses).

        Args:
            results: Resolution results to process

        Returns:
            Processed resolution results (default: unchanged)
        """
        return results

    def _handle_resolution_exception(
        self, exception: Exception, placeholder: PlaceholderInfo
    ):
        """Optional custom exception handling (hook for subclasses).

        Args:
            exception: Exception that occurred during resolution
            placeholder: Placeholder that caused the exception
        """
        # Default: re-raise as EnvironmentResolutionException
        raise EnvironmentResolutionException(
            f"Failed to resolve placeholder {placeholder.raw_placeholder}: {str(exception)}",
            self._get_environment_name(),
            "resolve_placeholder",
            str(exception),
        )
