"""Configuration auto-fixing functionality to handle common configuration issues."""

import logging
from typing import Any, Dict, List, Optional, Set

from panther.config.config_experiment_schema import ExperimentConfig, TestConfig


class ConfigurationAutoFixer:
    """Automatically fixes common configuration issues."""

    def __init__(self):
        """Initialize the configuration auto-fixer."""
        self.logger = logging.getLogger(__name__)
        self.fixes_applied: List[str] = []

    def fix_experiment_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Fix common issues in experiment configuration.

        Args:
            config: Raw experiment configuration dictionary

        Returns:
            Fixed configuration dictionary
        """
        self.fixes_applied.clear()
        fixed_config = config.copy()

        # Fix test configurations
        if "tests" in fixed_config:
            fixed_tests = []
            for i, test in enumerate(fixed_config["tests"]):
                fixed_test = self._fix_test_config(test, test_index=i)
                fixed_tests.append(fixed_test)
            fixed_config["tests"] = fixed_tests

        if self.fixes_applied:
            self.logger.info(f"Applied {len(self.fixes_applied)} configuration fixes:")
            for fix in self.fixes_applied:
                self.logger.info(f"  - {fix}")

        return fixed_config

    def _fix_test_config(
        self, test_config: Dict[str, Any], test_index: int
    ) -> Dict[str, Any]:
        """Fix issues in a test configuration.

        Args:
            test_config: Test configuration dictionary
            test_index: Index of the test for logging

        Returns:
            Fixed test configuration
        """
        fixed_test = test_config.copy()
        test_name = fixed_test.get("name", f"test_{test_index}")

        # Fix service configurations
        if "services" in fixed_test:
            fixed_services = {}
            used_ports = set()

            for service_name, service_config in fixed_test["services"].items():
                fixed_service = self._fix_service_config(
                    service_config, service_name, test_name, used_ports
                )
                fixed_services[service_name] = fixed_service

            fixed_test["services"] = fixed_services

        return fixed_test

    def _fix_service_config(
        self,
        service_config: Dict[str, Any],
        service_name: str,
        test_name: str,
        used_ports: Set[int],
    ) -> Dict[str, Any]:
        """Fix issues in a service configuration.

        Args:
            service_config: Service configuration dictionary
            service_name: Name of the service
            test_name: Name of the test (for logging)
            used_ports: Set of already used ports

        Returns:
            Fixed service configuration
        """
        fixed_service = service_config.copy()

        # Fix missing ports for server services
        protocol_config = fixed_service.get("protocol", {})
        role = protocol_config.get("role", "").lower()
        ports = fixed_service.get("ports", [])

        if role == "server" and not ports:
            # Auto-assign port for server using protocol defaults
            protocol_name = protocol_config.get("name", "").lower()
            default_port = self._get_default_port_for_protocol(protocol_name)

            if default_port:
                # Find an available port starting from the default
                assigned_port = self._find_available_port(default_port, used_ports)
                port_mapping = f"{assigned_port}:{assigned_port}"
                fixed_service["ports"] = [port_mapping]
                used_ports.add(assigned_port)

                fix_message = (
                    f"Auto-assigned port {assigned_port} to server service "
                    f"'{service_name}' in test '{test_name}' (protocol: {protocol_name})"
                )
                self.fixes_applied.append(fix_message)
                self.logger.debug(fix_message)

        # Track ports that are already configured
        for port_mapping in ports:
            if isinstance(port_mapping, str) and ":" in port_mapping:
                try:
                    host_port = int(port_mapping.split(":")[0])
                    used_ports.add(host_port)
                except ValueError:
                    pass

        return fixed_service

    def _get_default_port_for_protocol(self, protocol_name: str) -> Optional[int]:
        """Get default port number for a protocol.

        Args:
            protocol_name: Name of the protocol

        Returns:
            Default port number or None if unknown protocol
        """
        default_ports = {
            "quic": 4443,
            "http": 80,
            "https": 443,
            "tcp": 8080,
            "udp": 8080,
            "minip": 5000,
        }
        return default_ports.get(protocol_name.lower())

    def _find_available_port(self, start_port: int, used_ports: Set[int]) -> int:
        """Find an available port starting from the given port.

        Args:
            start_port: Port to start searching from
            used_ports: Set of already used ports

        Returns:
            Available port number
        """
        port = start_port
        while port in used_ports and port <= 65535:
            port += 1

        # If we've exhausted the range, start from a safe range
        if port > 65535:
            port = 8000
            while port in used_ports and port <= 9000:
                port += 1

        return port

    def get_fixes_applied(self) -> List[str]:
        """Get the list of fixes that were applied.

        Returns:
            List of fix descriptions
        """
        return self.fixes_applied.copy()
