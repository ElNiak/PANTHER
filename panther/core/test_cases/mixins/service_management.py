"""Service management functionality for test cases."""

import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from panther.config.core.models.service import ImplementationType
from panther.core.docker_builder.plugin_mixin.service_manager_docker_mixin import (
    ServiceManagerDockerMixin,
)
from panther.core.utils.log_context import log_context
from panther.plugins.services.services_interface import IServiceManager


class ServiceManagementMixin:
    """Mixin providing service management capabilities for test cases."""

    def setup_services(self) -> None:
        """Set up services based on test configuration."""
        self.logger.info("Setting up services")

        try:
            # Get service emitter from registry
            service_emitter = None
            if self.emitter_registry:
                service_emitter = self.emitter_registry.service_emitter

            service_names = list(self.services.keys())

            service_metadata = self.generate_service_metadata()

            service_emitter.emit_service_setup_started(
                test_case=self.test_name,
                service_count=len(self.services),
                service_names=service_names,
                service_metadata=service_metadata,
            )

            # Setup testers first (they act as servers)
            self.setup_testers()

            # Then setup implementations (they act as clients)
            self.setup_implementations()

            # Service setup completed

            self.logger.info(
                f"Successfully set up {len(self.service_managers)} services"
            )

        except Exception as e:
            self.logger.error(f"Failed to setup services (test will be skipped): {e}")
            # Service setup failed
            raise

    def generate_service_metadata(self):
        """Generate metadata for all configured services."""
        service_metadata = []
        # Build metadata from service configurations
        for service_name, service_config in self.services.items():
            # Handle both enum and string types for implementation.type
            service_type = "unknown"
            if hasattr(service_config.implementation, "type"):
                impl_type = service_config.implementation.type
                if hasattr(impl_type, "value"):
                    # Enum type (old system)
                    service_type = impl_type.value
                else:
                    # String type (new system)
                    service_type = str(impl_type).lower()

            # Handle both enum and string types for protocol.role
            protocol_role = "unknown"
            if hasattr(service_config, "protocol") and hasattr(
                service_config.protocol, "role"
            ):
                role = service_config.protocol.role
                if hasattr(role, "value"):
                    # Enum type (old system)
                    protocol_role = role.value
                else:
                    # String type (new system)
                    protocol_role = str(role).lower()

            metadata = {
                "service_type": service_type,
                "implementation": (
                    service_config.implementation.name
                    if hasattr(service_config.implementation, "name")
                    else "unknown"
                ),
                "config": {
                    "test_case": self.test_name,
                    "protocol": (
                        service_config.protocol.name
                        if hasattr(service_config, "protocol")
                        else "unknown"
                    ),
                    "role": protocol_role,
                },
            }
            service_metadata.append(metadata)
        return service_metadata

    def setup_testers(self) -> None:
        """Set up tester services from test configuration."""
        self.logger.info("Setting up testers")

        for service_name, service_details in self.services.items():
            implementation = service_details.implementation
            impl_type = implementation.type

            if (
                impl_type == ImplementationType.TESTERS
                or impl_type == "TESTERS"
                or impl_type == "testers"
            ):
                with log_context(service_id=service_name, phase="setup_testers"):
                    self.logger.info(f"Setting up tester: {service_name}")

                    try:
                        # Create service manager
                        service_manager = self._create_service_manager(
                            service_name, service_details
                        )

                        if service_manager:
                            self.service_managers.append(service_manager)
                            self.logger.info(
                                f"Tester {service_name} set up successfully ({service_manager})"
                            )

                    except Exception as e:
                        self.logger.error(f"Failed to setup tester {service_name}: {e}")
                        raise

    def setup_implementations(self) -> None:
        """Set up implementation (IUT) services from test configuration."""
        self.logger.info("Setting up implementations")

        for service_name, service_details in self.services.items():
            implementation = service_details.implementation
            impl_type = implementation.type

            if (
                impl_type == ImplementationType.IUT
                or impl_type == "IUT"
                or impl_type == "iut"
            ):
                with log_context(
                    service_id=service_name, phase="setup_implementations"
                ):
                    self.logger.info(f"Setting up implementation: {service_name}")

                    try:
                        # Create service manager
                        service_manager = self._create_service_manager(
                            service_name, service_details
                        )

                        if service_manager:
                            self.service_managers.append(service_manager)
                            self.logger.info(
                                f"Implementation {service_name} set up successfully ({service_manager})"
                            )

                    except Exception as e:
                        self.logger.error(
                            f"Failed to setup implementation {service_name}: {e}"
                        )
                        raise

    def prepare_services(self) -> None:
        """Prepare services (e.g., build Docker images)."""
        self.logger.info("Preparing services (building Docker images if required)")

        if not hasattr(self, "service_managers") or not self.service_managers:
            # Check if services are actually configured
            if hasattr(self, "services") and self.services:
                self.logger.warning(
                    "Services are configured but no service managers were created. Check plugin paths and service configurations."
                )
                self.logger.debug(
                    "Configured services: %s",
                    list(self.services.keys()) if self.services else "None",
                )
            else:
                self.logger.debug("No services configured for this test")
            return

        # Reset base image flag for this test run to ensure base image is built once per experiment
        try:
            ServiceManagerDockerMixin.reset_base_image_flag()
            self.logger.debug("Reset base Docker image flag for new test run")
        except ImportError:
            self.logger.debug(
                "ServiceManagerDockerMixin not available, skipping base image reset"
            )

        try:
            # Get service emitter if available
            service_emitter = None
            if self.emitter_registry:
                service_emitter = self.emitter_registry.service_emitter

            # Service preparation started

            # Prepare each service
            for service_manager in self.service_managers:
                service_name = (
                    service_manager.service_name
                    if hasattr(service_manager, "service_name")
                    else service_manager.get_implementation_name()
                )

                with log_context(service_id=service_name, phase="prepare_services"):
                    self.logger.debug("Preparing service manager: %s", service_name)

                    # Call prepare method if it exists
                    if hasattr(service_manager, "prepare") and callable(
                        getattr(service_manager, "prepare")
                    ):
                        try:
                            service_manager.prepare(self.plugin_manager)
                            self.logger.debug(
                                "Successfully prepared service: %s", service_name
                            )
                        except Exception as e:
                            self.logger.error(
                                f"Failed to prepare service {service_name}: {e}"
                            )
                            raise
                    else:
                        self.logger.debug(
                            "Service manager %s has no prepare method, skipping",
                            service_name,
                        )

        except Exception as e:
            self.logger.error(f"Service preparation failed for '{service_name}': {e}")
            # Service preparation failed
            raise

    def teardown_services(self) -> None:
        """Stop all services managed by service managers."""
        self.logger.info("Tearing down services")

        try:
            # Get service emitter if available
            service_emitter = None
            if self.emitter_registry:
                service_emitter = self.emitter_registry.service_emitter

            # Emit service teardown started for each service
            for service_manager in self.service_managers:
                service_name = getattr(service_manager, "service_name", "unknown")
                if service_emitter:
                    service_emitter.emit_service_teardown_started(
                        service_id=f"{self.test_name}_{service_name}",
                        service_name=service_name,
                    )

            # Teardown each service
            for service_manager in self.service_managers:
                service_name = getattr(service_manager, "service_name", "unknown")
                with log_context(service_id=service_name, phase="teardown"):
                    try:
                        self.logger.info(f"Stopping service: {service_name}")
                        service_manager.stop()

                        # Emit service stopped and destroyed events
                        if service_emitter:
                            service_emitter.emit_service_stopped(
                                service_id=f"{self.test_name}_{service_name}",
                                service_name=service_name,
                            )
                            service_emitter.emit_service_destroyed(
                                service_id=f"{self.test_name}_{service_name}",
                                service_name=service_name,
                                cleanup_details={"test_case": self.test_name},
                            )

                        # Clean up service state to prevent memory leaks
                        if self.emitter_registry:
                            self.emitter_registry.cleanup_service_state(
                                f"{self.test_name}_{service_name}"
                            )

                    except Exception as e:
                        self.logger.error(f"Failed to stop service {service_name}: {e}")
                        # Emit service error event
                        if service_emitter:
                            service_emitter.emit_service_error(
                                service_id=f"{self.test_name}_{service_name}",
                                service_name=service_name,
                                error_message=str(e),
                                error_type=type(e).__name__,
                            )
                        # Continue with other services

            # Clear service managers
            self.service_managers.clear()

            self.logger.info("All services torn down")

        except Exception as e:
            self.logger.error(f"Service teardown failed: {e}")
            # Don't re-raise, allow cleanup to continue

    def _create_service_manager(
        self, service_name: str, service_details: Dict[str, Any]
    ) -> Optional[IServiceManager]:
        """Create a service manager for the given service configuration."""
        implementation = service_details.implementation
        impl_name = implementation.name
        impl_type = implementation.type
        protocol = service_details.protocol
        protocol_name = protocol.name

        self.logger.debug(
            f"Creating service manager for {service_name}: "
            f"impl={impl_name}, type={impl_type}, protocol={protocol_name}"
        )

        try:
            # Get the implementation directory from plugin catalog
            # Handle both enum and string types
            if hasattr(impl_type, "value"):
                type_str = impl_type.value
            else:
                type_str = str(impl_type).lower()

            # Map TESTERS to tester for plugin catalog lookup
            if type_str == "testers":
                type_str = "tester"
            elif type_str == "iut":
                type_str = "iut"  # Keep as is

            plugin_id = f"{type_str}:{impl_name}"
            plugin_manifest = self.plugin_manager.plugin_catalog.catalog.get(plugin_id)

            if not plugin_manifest:
                self.logger.error(f"Plugin not found in catalog: {plugin_id}")
                return None

            implementation_dir = (
                Path(plugin_manifest.file_path) if plugin_manifest.file_path else None
            )

            if not implementation_dir:
                self.logger.error(f"No implementation directory found for {plugin_id}")
                return None

            self.logger.debug(f"Plugin manifest file_path: {plugin_manifest.file_path}")
            self.logger.debug(f"Implementation dir: {implementation_dir}")

            if service_manager := self.plugin_manager.create_service_manager(
                protocol=protocol,
                implementation=implementation,
                implementation_dir=implementation_dir,
                service_config_to_test=service_details,
                event_manager=self.event_manager,
                emitter_registry=self.emitter_registry,
                global_config=self.global_config,
                experiment_context=self,
            ):
                # Set service name and additional attributes
                service_manager.service_name = service_name
                service_manager.timeout = service_details.timeout
                service_manager.ports = (
                    service_details.ports if hasattr(service_details, "ports") else []
                )

                # Set protocol details
                service_manager.protocol_name = protocol_name
                service_manager.protocol_role = protocol.role
                service_manager.protocol_target = getattr(protocol, "target", None)

                # Set test context if the service manager supports it
                if hasattr(service_manager, "set_test_context"):
                    service_manager.set_test_context(self.test_name)

                return service_manager
            else:
                self.logger.error(
                    f"Failed to create service manager for {service_name}"
                )
                return None

        except Exception as e:
            self.logger.error(f"Error creating service manager for {service_name}: {e}")
            raise
