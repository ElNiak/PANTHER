"""Docker Compose Port Manager for PANTHER Framework.

This module handles all port-related operations for Docker Compose environments,
including port availability checking, conflict resolution, and dynamic port allocation.

Extracted from the Docker Compose god class to improve maintainability and
follow single responsibility principle.
"""

import logging
import socket
import subprocess
from typing import Dict, List, Optional, Tuple

from panther.core.exceptions.fast_fail import PortConflictException
from panther.plugins.environments.network_environment.mixins import (
    SubprocessExecutorMixin,
)


class DockerComposePortManager(SubprocessExecutorMixin):
    """Manages port allocation and conflict resolution for Docker Compose environments.

    This class handles:
    - Port availability checking with retry logic
    - Port conflict detection and resolution
    - Dynamic port allocation when conflicts occur
    - Stale container cleanup to free ports
    - Detailed port usage logging for troubleshooting
    """

    def __init__(self, logger: Optional[logging.Logger] = None):
        """Initialize the port manager.

        Args:
            logger: Logger instance for port management operations
        """
        self.logger = logger or logging.getLogger(self.__class__.__name__)

        # Initialize the mixin for subprocess execution
        super().__init__()

    def check_port_availability(self, services_managers: List) -> None:
        """Check if required ports are available before starting containers.

        This is the main entry point for port validation. It performs:
        1. Stale container cleanup
        2. Port availability checking for all services
        3. Conflict resolution attempts
        4. Dynamic port allocation as last resort

        Args:
            services_managers: List of service manager instances

        Raises:
            PortConflictException: If unresolvable port conflicts exist
        """
        self.logger.info("Checking port availability for all services...")

        # First, clean up any stale containers that might be holding ports
        self._cleanup_stale_containers()

        conflicts = []
        for service in services_managers:
            if (
                hasattr(service, "service_config_to_test")
                and service.service_config_to_test.ports
            ):
                service_name = service.service_name
                for port_mapping in service.service_config_to_test.ports:
                    if ":" in port_mapping:
                        host_port = int(port_mapping.split(":")[0])

                        # Check if port is available using bind() for more accurate detection
                        if not self._is_port_available(host_port):
                            conflicts.append((host_port, service_name))
                            self.logger.warning(
                                f"Port {host_port} is already in use (needed by {service_name}), "
                                "will attempt dynamic reallocation"
                            )
                        else:
                            self.logger.debug(
                                f"Port {host_port} is available for {service_name}"
                            )

        if conflicts:
            # Try to resolve conflicts with retry and cleanup
            resolved_conflicts = self._attempt_port_conflict_resolution(conflicts)

            if resolved_conflicts:
                # Try dynamic port allocation as last resort
                if self._attempt_dynamic_port_allocation(
                    resolved_conflicts, services_managers
                ):
                    self.logger.info(
                        "All port conflicts resolved using dynamic allocation"
                    )
                else:
                    # Some conflicts remain unresolved
                    port, service = resolved_conflicts[0]
                    # Provide more detailed error information
                    self._log_port_usage_details(port)
                    raise PortConflictException(
                        f"Cannot start Docker Compose: port {port} is already in use",
                        port,
                        service,
                    )
            else:
                self.logger.info("All port conflicts resolved successfully")

    def verify_ports_released(self, services_managers: List) -> bool:
        """Verify that all ports used by services are no longer in use.

        Args:
            services_managers: List of service manager instances

        Returns:
            bool: True if all ports are released, False otherwise
        """
        # Collect all ports used by services
        used_ports = set()
        for service in services_managers:
            if (
                hasattr(service, "service_config_to_test")
                and service.service_config_to_test.ports
            ):
                for port_mapping in service.service_config_to_test.ports:
                    # Port mappings are in format "host_port:container_port"
                    if ":" in port_mapping:
                        host_port = port_mapping.split(":")[0]
                        try:
                            used_ports.add(int(host_port))
                        except ValueError:
                            continue

        # Check if any ports are still in use using the improved method
        ports_in_use = []
        for port in used_ports:
            if not self._is_port_available(port, max_retries=1):
                ports_in_use.append(port)

        if ports_in_use:
            self.logger.debug(f"Ports still in use: {ports_in_use}")
            return False

        return True

    def _is_port_available(self, port: int, max_retries: int = 3) -> bool:
        """Check if a port is available using bind() method with retry logic.

        Checks both localhost and 0.0.0.0 because Docker binds to 0.0.0.0
        by default. A port can appear available on localhost but be occupied
        on 0.0.0.0 (e.g., macOS AirPlay Receiver on port 5000).

        Args:
            port: Port number to check
            max_retries: Maximum number of retry attempts

        Returns:
            bool: True if port is available, False otherwise
        """
        import time

        for attempt in range(max_retries):
            try:
                # Check both 0.0.0.0 and localhost — Docker uses 0.0.0.0
                for host in ("0.0.0.0", "localhost"):
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                    sock.settimeout(1)
                    sock.bind((host, port))
                    sock.close()
                return True
            except OSError as e:
                if attempt < max_retries - 1:
                    # Port might be in TIME_WAIT state, wait briefly and retry
                    self.logger.debug(
                        f"Port {port} check attempt {attempt + 1} failed: {e}, retrying..."
                    )
                    time.sleep(0.5)
                else:
                    self.logger.debug(f"Port {port} is not available: {e}")
                    return False
            except Exception as e:
                self.logger.debug(f"Unexpected error checking port {port}: {e}")
                return False

        return False

    def _cleanup_stale_containers(self) -> None:
        """Remove any stale PANTHER containers that might be holding ports."""
        try:
            # Find containers with PANTHER-related names
            cmd = [
                "docker",
                "ps",
                "-a",
                "--format",
                "{{.Names}}",
                "--filter",
                "name=panther",
            ]
            result = self.execute_command(cmd, timeout=10, check=False)

            if result.returncode == 0 and result.stdout.strip():
                stale_containers = result.stdout.strip().split("\n")
                self.logger.info(
                    f"Found {len(stale_containers)} stale PANTHER containers"
                )

                for container in stale_containers:
                    if container.strip():
                        self.logger.debug(f"Removing stale container: {container}")
                        self.execute_command(
                            ["docker", "rm", "-f", container.strip()],
                            timeout=30,
                            check=False,
                        )

            # Also check for containers using specific service patterns
            service_patterns = [
                "picoquic",
                "ivy",
                "aioquic",
                "lsquic",
                "mvfst",
                "quiche",
                "quinn",
                "quic_go",
            ]
            for pattern in service_patterns:
                cmd = [
                    "docker",
                    "ps",
                    "-a",
                    "--format",
                    "{{.Names}}",
                    "--filter",
                    f"name={pattern}",
                ]
                result = self.execute_command(cmd, timeout=10, check=False)

                if result.returncode == 0 and result.stdout.strip():
                    containers = result.stdout.strip().split("\n")
                    for container in containers:
                        if container.strip():
                            self.logger.debug(
                                f"Removing stale service container: {container}"
                            )
                            self.execute_command(
                                ["docker", "rm", "-f", container.strip()],
                                timeout=30,
                                check=False,
                            )

        except Exception as e:
            self.logger.debug(f"Error during stale container cleanup: {e}")

    def _attempt_port_conflict_resolution(
        self, conflicts: List[Tuple[int, str]]
    ) -> List[Tuple[int, str]]:
        """Attempt to resolve port conflicts through cleanup and waiting.

        Args:
            conflicts: List of (port, service_name) tuples

        Returns:
            List of remaining unresolved conflicts
        """
        self.logger.info(f"Attempting to resolve {len(conflicts)} port conflicts...")

        # Wait a moment for any TIME_WAIT states to clear
        import time

        time.sleep(2)

        # Force Docker network cleanup
        try:
            self.execute_command(
                ["docker", "network", "prune", "-f"], timeout=30, check=False
            )
        except Exception as e:
            self.logger.debug(f"Docker network cleanup failed: {e}")

        # Re-check each conflicted port
        remaining_conflicts = []
        for port, service_name in conflicts:
            if not self._is_port_available(port, max_retries=2):
                remaining_conflicts.append((port, service_name))
            else:
                self.logger.info(f"Port {port} conflict resolved for {service_name}")

        return remaining_conflicts

    def _log_port_usage_details(self, port: int) -> None:
        """Log detailed information about what is using a port."""
        try:
            # Try to find what's using the port using lsof if available
            try:
                result = subprocess.run(
                    ["lsof", "-i", f":{port}"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if result.returncode == 0 and result.stdout:
                    self.logger.error(f"Port {port} is being used by:")
                    for line in result.stdout.split("\n")[1:]:  # Skip header
                        if line.strip():
                            self.logger.error(f"  {line}")
                else:
                    self.logger.debug(f"No lsof output for port {port}")
            except (subprocess.TimeoutExpired, FileNotFoundError):
                # lsof not available or timed out
                self.logger.debug(f"Could not determine what is using port {port}")

            # Also check Docker containers
            try:
                result = subprocess.run(
                    [
                        "docker",
                        "ps",
                        "--format",
                        "{{.Names}} {{.Ports}}",
                        "--filter",
                        f"publish={port}",
                    ],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if result.returncode == 0 and result.stdout.strip():
                    self.logger.error(f"Docker containers using port {port}:")
                    for line in result.stdout.split("\n"):
                        if line.strip():
                            self.logger.error(f"  {line}")
            except subprocess.TimeoutExpired:
                pass

        except Exception as e:
            self.logger.debug(f"Error logging port usage details: {e}")

    def _attempt_dynamic_port_allocation(
        self, conflicts: List[Tuple[int, str]], services_managers: List
    ) -> bool:
        """Attempt to resolve port conflicts by dynamically allocating alternative ports.

        Args:
            conflicts: List of (port, service_name) tuples with unresolved conflicts
            services_managers: List of service manager instances

        Returns:
            bool: True if all conflicts were resolved, False otherwise
        """
        self.logger.info(
            "Attempting dynamic port allocation for remaining conflicts..."
        )

        port_mappings = {}
        for original_port, service_name in conflicts:
            # Find an available alternative port
            alternative_port = self._find_available_port(original_port)
            if alternative_port:
                port_mappings[service_name] = (original_port, alternative_port)
                self.logger.info(
                    f"Assigned alternative port {alternative_port} to {service_name} (original: {original_port})"
                )
            else:
                self.logger.error(
                    f"Could not find alternative port for {service_name} (original: {original_port})"
                )
                return False

        # Apply the new port mappings to the service configurations
        if self._apply_dynamic_port_mappings(port_mappings, services_managers):
            self.logger.info("Successfully applied dynamic port mappings")
            return True
        else:
            self.logger.error("Failed to apply dynamic port mappings")
            return False

    def _find_available_port(
        self, original_port: int, port_range: int = 1000
    ) -> Optional[int]:
        """Find an available port starting from original_port + 1000.

        Args:
            original_port: The original conflicted port
            port_range: Range of ports to search

        Returns:
            int: Available port number, or None if none found
        """
        # Start searching from original_port + 1000 to avoid common port ranges
        start_port = original_port + 1000
        end_port = start_port + port_range

        for port in range(start_port, end_port):
            if self._is_port_available(port, max_retries=1):
                return port

        # If no port found in that range, try a different range
        start_port = 50000  # Use high port numbers that are typically available
        end_port = 60000

        for port in range(start_port, end_port):
            if self._is_port_available(port, max_retries=1):
                return port

        return None

    def _apply_dynamic_port_mappings(
        self, port_mappings: Dict[str, Tuple[int, int]], services_managers: List
    ) -> bool:
        """Apply dynamic port mappings to service configurations.

        Args:
            port_mappings: Dict mapping service_name to (original_port, new_port) tuples
            services_managers: List of service manager instances

        Returns:
            bool: True if successfully applied, False otherwise
        """
        try:
            for service in services_managers:
                service_name = service.service_name
                if service_name in port_mappings:
                    original_port, new_port = port_mappings[service_name]

                    # Update service configuration ports
                    if (
                        hasattr(service, "service_config_to_test")
                        and service.service_config_to_test.ports
                    ):
                        updated_ports = []
                        for port_mapping in service.service_config_to_test.ports:
                            if ":" in port_mapping:
                                host_port, container_port = port_mapping.split(":", 1)
                                if int(host_port) == original_port:
                                    updated_ports.append(f"{new_port}:{container_port}")
                                    self.logger.debug(
                                        f"Updated port mapping for {service_name}: {port_mapping} -> {new_port}:{container_port}"
                                    )
                                else:
                                    updated_ports.append(port_mapping)
                            else:
                                updated_ports.append(port_mapping)

                        # Update the service configuration
                        service.service_config_to_test.ports = updated_ports
                        self.logger.info(
                            f"Updated port configuration for service {service_name}"
                        )

            return True

        except Exception as e:
            self.logger.error(f"Error applying dynamic port mappings: {e}")
            return False
