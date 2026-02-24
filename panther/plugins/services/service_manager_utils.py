"""
Service Manager Utilities

This module provides common utilities and mixins for service managers,
integrating with PANTHER's existing patterns and interfaces.
"""

import logging
from typing import Any, Optional, Union

logger = logging.getLogger(__name__)


class ServiceManagerUtilities:
    """Common utility methods for service managers.

    MRO: Utility class (not in MRO chain). Used by service managers for shared utilities.
    """

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
        logger.debug(
            "Loaded %s configuration: %s", logger.name or "Service", service_config
        )

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
        service_manager.service_name = getattr(
            service_config_to_test, "name", implementation_name
        )
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
