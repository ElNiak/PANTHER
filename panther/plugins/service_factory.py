"""
Service Factory Module

This module handles service manager creation and configuration
for the PANTHER framework.
"""

from pathlib import Path
from typing import Any

from panther.config.config_experiment_schema import ServiceConfig
from panther.core.observer.management.event_manager import EventManager
from panther.core.utils.logging_mixin import LoggerMixin
from panther.plugins.plugin_config_resolver import PluginConfigResolver
from panther.plugins.plugin_discovery import PluginDiscovery
from panther.plugins.plugin_manifest import PluginRegistration, PluginType
from panther.plugins.protocols.config_schema import ProtocolConfig
from panther.plugins.services.iut.config_schema import ImplementationConfig
from panther.plugins.services.services_interface import IServiceManager


class ServiceFactory(LoggerMixin):
    """
    Handles service manager creation and configuration.

    This class provides functionality for:
    - Service manager instantiation
    - Service configuration management
    - Service-specific logic and validation
    - Service manager class loading
    """

    def __init__(
        self,
        config_resolver: PluginConfigResolver,
        plugin_discovery: PluginDiscovery,
        event_manager: EventManager | None = None,
        plugin_event_emitter=None,
    ):
        """
        Initialize the service factory.

        Args:
            config_resolver: Configuration resolver instance
            plugin_discovery: Plugin discovery instance
            event_manager: Event manager for plugin events
            plugin_event_emitter: Plugin event emitter instance
        """
        super().__init__()

        self.config_resolver = config_resolver
        self.plugin_discovery = plugin_discovery
        self.event_manager = event_manager
        self.plugin_event_emitter = plugin_event_emitter

        # Plugin registrations
        self.registrations: dict[str, PluginRegistration] = {}

    def create_service_manager(
        self,
        protocol: ProtocolConfig,
        implementation: ImplementationConfig,
        implementation_dir: Path,
        service_config_to_test: ServiceConfig,
        event_manager: EventManager | None = None,
        emitter_registry=None,
    ) -> IServiceManager:
        """
        Create a service manager instance using the catalog-based approach.

        Args:
            protocol: Protocol configuration
            implementation: Implementation configuration
            implementation_dir: Directory containing implementation files
            service_config_to_test: Service configuration to test
            event_manager: Event manager instance
            emitter_registry: Emitter registry for events

        Returns:
            Service manager instance
        """
        self.logger.debug(
            "Creating service manager for %s (%s)",
            implementation.name,
            implementation.type,
        )

        # Check if we have a catalog entry for this plugin
        impl_type_str = (
            implementation.type
            if isinstance(implementation.type, str)
            else implementation.type.name
        )
        plugin_type = PluginType.TESTER if impl_type_str.lower() == "testers" else PluginType.IUT
        plugin_id = f"{plugin_type.value}:{implementation.name}"
        manifest = self.plugin_discovery.plugin_catalog.catalog.get(plugin_id)

        try:
            # Determine module name and path
            impl_name = implementation.name

            if impl_type_str.lower() == "testers":
                service_file_path = implementation_dir / f"{impl_name}.py"
            else:
                service_file_path = implementation_dir / f"{impl_name}.py"

            self.logger.debug("Loading service module from %s", service_file_path)

            # Use PluginManagerUtils to load the plugin class
            from panther.plugins.plugin_loader_utils import (
                PluginManagerUtils,
            )  # pylint: disable=import-outside-toplevel

            service_manager_class = PluginManagerUtils.load_plugin_class(
                plugin_path=service_file_path,
                class_suffix="ServiceManager",
                name_transform=lambda name: self.config_resolver.get_class_name(name, suffix=""),
            )

            # Create the instance - try with emitter_registry first, fallback without it
            # This ensures backward compatibility with service managers that don't support emitter_registry yet
            try:
                service_manager = service_manager_class(  # type: ignore[misc]
                    service_config_to_test=service_config_to_test,
                    service_type=implementation.type,
                    protocol=protocol,
                    implementation_name=impl_name,
                    event_manager=event_manager or self.event_manager,
                    emitter_registry=emitter_registry,
                )
            except TypeError as e:
                if "emitter_registry" in str(e):
                    # Service manager doesn't support emitter_registry yet, fallback to legacy approach
                    self.logger.debug(
                        "Service manager %s doesn't support emitter_registry parameter, using legacy approach",
                        impl_name,
                    )
                    service_manager = service_manager_class(  # type: ignore[misc]
                        service_config_to_test=service_config_to_test,
                        service_type=implementation.type,
                        protocol=protocol,
                        implementation_name=impl_name,
                        event_manager=event_manager or self.event_manager,
                    )
                else:
                    raise

            # Register if we have a manifest
            if manifest:
                registration = PluginRegistration(
                    manifest=manifest,
                    instance=service_manager,
                    loaded=True,
                    active=True,
                )
                self.registrations[plugin_id] = registration

            # Emit plugin loaded event if we have event system
            if self.plugin_event_emitter:
                self.plugin_event_emitter.emit_plugin_loading_completed(
                    plugin_id=plugin_id,
                    plugin_name=impl_name,
                    plugin_type=plugin_type.value,
                    # Note: details parameter not supported, omitting for now
                )

            self.logger.info(
                "Successfully created service manager for %s (%s)",
                implementation.name,
                implementation.type,
            )
            return service_manager

        except Exception as e:
            # Emit plugin loading failed event
            if self.plugin_event_emitter:
                self.plugin_event_emitter.emit_plugin_loading_failed(
                    plugin_id=plugin_id,
                    plugin_name=implementation.name,
                    plugin_type=plugin_type.value,
                    error_message=str(e),
                    error_details={
                        "service_type": implementation.type,
                        "implementation_dir": str(implementation_dir),
                        "exception_type": type(e).__name__,
                    },
                )

            self.logger.error(
                "Failed to create service manager for %s (%s): %s",
                implementation.name,
                implementation.type,
                e,
            )
            raise

    def validate_service_requirements(self, service_config: ServiceConfig) -> bool:
        """
        Validate that service requirements are met.

        Args:
            service_config: Service configuration to validate

        Returns:
            True if requirements are satisfied, False otherwise
        """
        try:
            # Check if service implementation is available
            if hasattr(service_config, "implementation") and service_config.implementation:
                impl = service_config.implementation
                plugin_id = f"service.{impl.type}.{impl.name}"

                if not self.plugin_discovery.is_plugin_available(plugin_id):
                    self.logger.warning("Service implementation not available: %s", plugin_id)
                    return False

                # Validate dependencies
                dependencies_ok, missing_deps = self.plugin_discovery.validate_plugin_dependencies(
                    impl.name
                )
                if not dependencies_ok:
                    self.logger.warning(
                        "Missing dependencies for service %s: %s",
                        impl.name,
                        missing_deps,
                    )
                    return False

            return True

        except Exception as e:  # pylint: disable=broad-exception-caught
            self.logger.error("Error validating service requirements: %s", e)
            return False

    def get_available_service_types(self) -> list[str]:
        """
        Get all available service types.

        Returns:
            List of available service types
        """
        try:
            service_types = set()
            all_plugins = self.plugin_discovery.list_available_plugins()

            # Look for service-related plugin types
            for (
                plugin_type,
                plugin_names,
            ) in all_plugins.items():  # pylint: disable=unused-variable
                if "service" in plugin_type.lower() or plugin_type in ["iut", "tester"]:
                    service_types.add(plugin_type)

            return list(service_types)

        except Exception as e:  # pylint: disable=broad-exception-caught
            self.logger.error("Error getting available service types: %s", e)
            return []

    def get_service_implementations(self, service_type: str) -> list[str]:
        """
        Get all available implementations for a service type.

        Args:
            service_type: The service type (e.g., 'iut', 'tester')

        Returns:
            List of implementation names
        """
        try:
            implementations = []
            all_plugins = self.plugin_discovery.list_available_plugins()

            # Get implementations for the specified service type
            if service_type in all_plugins:
                implementations = all_plugins[service_type]

            self.logger.debug(
                "Found %d implementations for service type %s",
                len(implementations),
                service_type,
            )
            return implementations

        except Exception as e:  # pylint: disable=broad-exception-caught
            self.logger.error(
                "Error getting implementations for service type %s: %s", service_type, e
            )
            return []

    def get_service_for_protocol(self, protocol: str, service_type: str | None = None) -> list[str]:
        """
        Get all available services that support a specific protocol.

        Args:
            protocol: The protocol name (e.g., 'quic')
            service_type: Optional service type filter

        Returns:
            List of service names that support the protocol
        """
        try:
            # Use plugin discovery to get implementations for protocol
            implementations = self.plugin_discovery.get_implementations_for_protocol(protocol)

            # Filter by service type if specified
            if service_type:
                filtered_implementations = []
                for impl in implementations:
                    # Check if implementation belongs to the specified service type
                    manifest = self.plugin_discovery.get_plugin_manifest(impl)
                    if (
                        manifest
                        and hasattr(manifest, "categories")
                        and service_type in manifest.categories
                    ):
                        filtered_implementations.append(impl)
                implementations = filtered_implementations

            return implementations

        except Exception as e:  # pylint: disable=broad-exception-caught
            self.logger.error("Error getting services for protocol %s: %s", protocol, e)
            return []

    def validate_service_configuration(
        self, service_config: ServiceConfig
    ) -> tuple[bool, list[str]]:
        """
        Validate a service configuration.

        Args:
            service_config: Service configuration to validate

        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []

        try:
            # Check required fields
            if not hasattr(service_config, "implementation") or not service_config.implementation:
                errors.append("Service configuration missing implementation")
                return False, errors

            impl = service_config.implementation

            # Check implementation type and name
            if not hasattr(impl, "type") or not impl.type:
                errors.append("Implementation missing type")

            if not hasattr(impl, "name") or not impl.name:
                errors.append("Implementation missing name")

            # Validate that implementation is available
            if not self.validate_service_requirements(service_config):
                errors.append(f"Service requirements not met for {impl.name}")

            is_valid = len(errors) == 0

            self.logger.debug(
                "Service configuration validation: %s (errors: %s)",
                "passed" if is_valid else "failed",
                errors,
            )

            return is_valid, errors

        except Exception as e:  # pylint: disable=broad-exception-caught
            self.logger.error("Error validating service configuration: %s", e)
            return False, [f"Validation error: {str(e)}"]

    def get_service_info(self, service_name: str) -> dict[str, Any] | None:
        """
        Get information about a specific service.

        Args:
            service_name: Name of the service

        Returns:
            Service information dictionary or None if not found
        """
        try:
            manifest = self.plugin_discovery.get_plugin_manifest(service_name)

            if manifest is None:
                return None

            # Build service info from manifest
            service_info = {
                "name": manifest.name,
                "type": (manifest.plugin_type.value if manifest.plugin_type else "unknown"),
                "version": getattr(manifest, "version", "unknown"),
                "description": getattr(manifest, "description", ""),
                "capabilities": getattr(manifest, "capabilities", []),
                "dependencies": getattr(manifest, "dependencies", []),
                "supported_protocols": getattr(manifest, "supported_protocols", []),
            }

            return service_info

        except Exception as e:  # pylint: disable=broad-exception-caught
            self.logger.error("Error getting service info for %s: %s", service_name, e)
            return None
