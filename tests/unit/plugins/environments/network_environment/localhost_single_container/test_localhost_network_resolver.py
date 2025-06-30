"""Unit tests for localhost network resolver."""

from unittest.mock import Mock

import pytest

from panther.config.core.models.network_resolution import (
    NetworkAttribute,
    NetworkFormat,
    NetworkResolutionContext,
    NetworkServiceInfo,
    PlaceholderInfo,
)
from panther.plugins.environments.network_environment.localhost_single_container.localhost_network_resolver import (
    LocalhostNetworkResolver,
)


class TestLocalhostNetworkResolver:
    """Test cases for LocalhostNetworkResolver."""

    def setup_method(self):
        """Set up test fixtures."""
        self.resolver = LocalhostNetworkResolver()
        self.test_services = ["ivy_service", "picoquic_server", "quiche_client"]

    def test_resolver_initialization(self):
        """Test resolver is properly initialized."""
        assert self.resolver.localhost_ip == "127.0.0.1"
        assert self.resolver.base_port == 5000
        assert self.resolver.port_offset == 10
        assert self.resolver.service_registry == {}

    def test_service_registration(self):
        """Test service registration creates consistent indices."""
        self.resolver.register_services(self.test_services)
        registry = self.resolver.get_service_registry()

        assert len(registry) == 3
        assert registry["ivy_service"] == 0
        assert registry["picoquic_server"] == 1
        assert registry["quiche_client"] == 2

    def test_port_calculation(self):
        """Test port calculation with service indices."""
        assert self.resolver._calculate_port(0) == 5000
        assert self.resolver._calculate_port(1) == 5010
        assert self.resolver._calculate_port(2) == 5020

    def test_service_index_assignment(self):
        """Test service index assignment is consistent."""
        context = NetworkResolutionContext(environment_type="localhost")

        # First call should assign index 0
        index1 = self.resolver._get_service_index("service1", context)
        assert index1 == 0

        # Second call should assign index 1
        index2 = self.resolver._get_service_index("service2", context)
        assert index2 == 1

        # Calling again with same service should return same index
        index1_again = self.resolver._get_service_index("service1", context)
        assert index1_again == 0

    def test_ip_format_conversion(self):
        """Test IP address format conversion."""
        # Standard/dotted format
        assert self.resolver._format_ip_address(NetworkFormat.DOTTED) == "127.0.0.1"
        assert self.resolver._format_ip_address(NetworkFormat.STRING) == "127.0.0.1"

        # Decimal format
        assert self.resolver._format_ip_address(NetworkFormat.DECIMAL) == "2130706433"

        # Integer format (same as decimal)
        assert self.resolver._format_ip_address(NetworkFormat.INTEGER) == "2130706433"

        # Hostname format
        assert self.resolver._format_ip_address(NetworkFormat.HOSTNAME) == "127.0.0.1"

    def test_create_resolution_context(self):
        """Test resolution context creation."""
        mock_service_managers = {name: Mock() for name in self.test_services}
        context = self.resolver.create_resolution_context(
            "localhost_single_container", mock_service_managers
        )

        assert context.environment_type == "localhost_single_container"
        assert len(context.available_services) == 3

        # Check service info
        ivy_service = context.get_service_info("ivy_service")
        assert ivy_service.service_name == "ivy_service"
        assert ivy_service.ip_address == "127.0.0.1"
        assert ivy_service.hostname == "127.0.0.1"
        assert ivy_service.port == 5000

    def test_placeholder_resolution_ip_decimal(self):
        """Test IP placeholder resolution in decimal format."""
        context = NetworkResolutionContext(environment_type="localhost")
        placeholder = PlaceholderInfo(
            service="picoquic_server",
            attribute=NetworkAttribute.IP,
            format_type=NetworkFormat.DECIMAL,
            raw_placeholder="@{picoquic_server:ip:decimal}",
        )

        result = self.resolver._resolve_single_placeholder(placeholder, context)

        assert result.original_placeholder == "@{picoquic_server:ip:decimal}"
        assert result.resolved_value == "2130706433"
        assert result.environment_type == "localhost_single_container"

    def test_placeholder_resolution_hostname(self):
        """Test hostname placeholder resolution."""
        context = NetworkResolutionContext(environment_type="localhost")
        placeholder = PlaceholderInfo(
            service="ivy_service",
            attribute=NetworkAttribute.HOSTNAME,
            format_type=NetworkFormat.STRING,
            raw_placeholder="@{ivy_service:hostname}",
        )

        result = self.resolver._resolve_single_placeholder(placeholder, context)

        assert result.original_placeholder == "@{ivy_service:hostname}"
        assert result.resolved_value == "127.0.0.1"

    def test_placeholder_resolution_port(self):
        """Test port placeholder resolution."""
        # Register services to ensure consistent indexing
        self.resolver.register_services(self.test_services)

        context = NetworkResolutionContext(environment_type="localhost")
        placeholder = PlaceholderInfo(
            service="picoquic_server",
            attribute=NetworkAttribute.PORT,
            format_type=NetworkFormat.STRING,
            raw_placeholder="@{picoquic_server:port}",
        )

        result = self.resolver._resolve_single_placeholder(placeholder, context)

        assert result.original_placeholder == "@{picoquic_server:port}"
        assert result.resolved_value == "5010"  # Base 5000 + (index 1 * 10)

    def test_placeholder_resolution_service_name(self):
        """Test service name placeholder resolution."""
        context = NetworkResolutionContext(environment_type="localhost")
        placeholder = PlaceholderInfo(
            service="quiche_client",
            attribute=NetworkAttribute.SERVICE_NAME,
            format_type=NetworkFormat.STRING,
            raw_placeholder="@{quiche_client:service_name}",
        )

        result = self.resolver._resolve_single_placeholder(placeholder, context)

        assert result.original_placeholder == "@{quiche_client:service_name}"
        assert result.resolved_value == "quiche_client"

    def test_full_command_resolution(self):
        """Test full command template resolution."""
        # Register services first
        self.resolver.register_services(self.test_services)

        # Create context
        mock_service_managers = {name: Mock() for name in self.test_services}
        context = self.resolver.create_resolution_context(
            "localhost_single_container", mock_service_managers
        )

        # Test command with multiple placeholders
        command = "ivy_client --server_addr=@{picoquic_server:ip:decimal} --server_port=@{picoquic_server:port}"
        results = self.resolver.resolve_network_placeholders(command, context)

        assert len(results) == 2

        # Apply substitutions
        resolved_command = command
        for result in results:
            placeholder, value = result.to_substitution_pair()
            resolved_command = resolved_command.replace(placeholder, value)

        expected = "ivy_client --server_addr=2130706433 --server_port=5010"
        assert resolved_command == expected

    def test_populate_service_network_info(self):
        """Test service network info population."""
        context = NetworkResolutionContext(environment_type="localhost")

        # Add a service with incomplete info
        incomplete_service = NetworkServiceInfo(
            service_name="test_service", hostname=None, ip_address=None, port=None
        )
        context.add_service(incomplete_service)

        # Populate should complete the info
        self.resolver.populate_service_network_info(context)

        service_info = context.get_service_info("test_service")
        assert service_info.hostname == "127.0.0.1"
        assert service_info.ip_address == "127.0.0.1"
        assert service_info.port == 5000  # First service gets port 5000

    def test_get_service_info(self):
        """Test service info retrieval and creation."""
        context = NetworkResolutionContext(environment_type="localhost")

        # Should create new service info if not exists
        service_info = self.resolver.get_service_info("new_service", context)

        assert service_info.service_name == "new_service"
        assert service_info.hostname == "127.0.0.1"
        assert service_info.ip_address == "127.0.0.1"
        assert service_info.port == 5000  # First service
        assert "service_index" in service_info.additional_info

    def test_resolver_capabilities(self):
        """Test resolver capabilities reporting."""
        capabilities = self.resolver.get_resolution_capabilities()

        assert capabilities["runtime_ip_resolution"] is False
        assert capabilities["static_ip_resolution"] is True
        assert capabilities["hostname_resolution"] is True
        assert capabilities["port_resolution"] is True
        assert capabilities["decimal_ip_format"] is True
        assert capabilities["calculated_ports"] is True

    def test_supports_runtime_resolution(self):
        """Test runtime resolution support check."""
        assert self.resolver.supports_runtime_resolution() is False

    def test_get_service_ip(self):
        """Test service IP address retrieval."""
        context = NetworkResolutionContext(environment_type="localhost")

        ip = self.resolver.get_service_ip("any_service", context)
        assert ip == "127.0.0.1"

    def test_error_handling_invalid_attribute(self):
        """Test error handling for invalid attributes."""
        context = NetworkResolutionContext(environment_type="localhost")

        # Create service info
        service_info = NetworkServiceInfo(
            service_name="test_service",
            hostname="127.0.0.1",
            ip_address="127.0.0.1",
            port=5000,
        )

        # This should raise an exception for an invalid attribute
        with pytest.raises(Exception):
            # Create a mock placeholder with invalid attribute
            placeholder = Mock()
            placeholder.attribute = "invalid_attribute"
            placeholder.format_type = NetworkFormat.STRING

            self.resolver._generate_resolved_value(placeholder, service_info)
