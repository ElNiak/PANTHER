"""Unit tests for Shadow NS network resolver.

This module tests the Shadow NS-specific implementation of network
placeholder resolution using static IP assignment patterns.
"""

from typing import Dict, List
from unittest.mock import Mock, patch

import pytest

from panther.config.core.models.network_resolution import (
    NetworkAttribute,
    NetworkFormat,
    NetworkResolutionContext,
    NetworkResolutionResult,
    NetworkServiceInfo,
    PlaceholderInfo,
)
from panther.core.exceptions.network_resolution_exceptions import (
    EnvironmentResolutionException,
    NetworkDiscoveryException,
    ServiceResolutionException,
)
from panther.plugins.environments.network_environment.shadow_ns.shadow_network_resolver import (
    ShadowNetworkResolver,
)


class TestShadowNetworkResolver:
    """Test cases for Shadow NS network resolver."""

    def setup_method(self):
        """Set up test fixtures."""
        self.resolver = ShadowNetworkResolver()

    def test_initialization(self):
        """Test resolver initialization."""
        assert self.resolver.logger is not None
        assert self.resolver.parser is not None
        assert self.resolver.server_ip == "11.0.0.1"
        assert self.resolver.client_ip == "11.0.0.2"
        assert self.resolver.default_port == 4433
        assert isinstance(self.resolver.service_roles, dict)
        assert len(self.resolver.service_roles) == 0

    def test_register_service_roles(self):
        """Test service role registration."""
        service_roles = {
            "ivy_server": "server",
            "ivy_client": "client",
            "test_service": "server",
        }

        self.resolver.register_service_roles(service_roles)

        assert self.resolver.service_roles == service_roles
        assert len(self.resolver.service_roles) == 3

    def test_get_service_roles(self):
        """Test getting service roles copy."""
        original_roles = {"service1": "client", "service2": "server"}
        self.resolver.service_roles = original_roles

        roles_copy = self.resolver.get_service_roles()

        assert roles_copy == original_roles
        assert roles_copy is not self.resolver.service_roles  # Should be a copy

    def test_get_service_ip_by_role_server(self):
        """Test IP assignment for server role."""
        self.resolver.service_roles["test_server"] = "server"

        ip = self.resolver._get_service_ip_by_role("test_server")

        assert ip == "11.0.0.1"

    def test_get_service_ip_by_role_client(self):
        """Test IP assignment for client role."""
        self.resolver.service_roles["test_client"] = "client"

        ip = self.resolver._get_service_ip_by_role("test_client")

        assert ip == "11.0.0.2"

    def test_get_service_ip_by_role_unknown_defaults_to_server(self):
        """Test IP assignment for unknown service defaults to server."""
        ip = self.resolver._get_service_ip_by_role("unknown_service")

        assert ip == "11.0.0.1"  # Should default to server IP

    def test_format_ip_address_dotted(self):
        """Test IP formatting in dotted notation."""
        result = self.resolver._format_ip_address("11.0.0.1", NetworkFormat.DOTTED)
        assert result == "11.0.0.1"

    def test_format_ip_address_string(self):
        """Test IP formatting as string."""
        result = self.resolver._format_ip_address("11.0.0.1", NetworkFormat.STRING)
        assert result == "11.0.0.1"

    def test_format_ip_address_decimal(self):
        """Test IP formatting as decimal."""
        # 11.0.0.1 = (11 << 24) + (0 << 16) + (0 << 8) + 1 = 184549377
        result = self.resolver._format_ip_address("11.0.0.1", NetworkFormat.DECIMAL)
        assert result == "184549377"

    def test_format_ip_address_integer(self):
        """Test IP formatting as integer."""
        # Same as decimal for compatibility
        result = self.resolver._format_ip_address("11.0.0.1", NetworkFormat.INTEGER)
        assert result == "184549377"

    def test_format_ip_address_hostname(self):
        """Test IP formatting as hostname."""
        result = self.resolver._format_ip_address("11.0.0.1", NetworkFormat.HOSTNAME)
        assert result == "11.0.0.1"

    def test_format_ip_address_client_decimal(self):
        """Test client IP formatting as decimal."""
        # 11.0.0.2 = (11 << 24) + (0 << 16) + (0 << 8) + 2 = 184549378
        result = self.resolver._format_ip_address("11.0.0.2", NetworkFormat.DECIMAL)
        assert result == "184549378"

    def test_get_service_ip(self):
        """Test getting service IP address."""
        context = NetworkResolutionContext(environment_type="shadow_ns")
        self.resolver.service_roles["test_service"] = "client"

        ip = self.resolver.get_service_ip("test_service", context)

        assert ip == "11.0.0.2"

    def test_supports_runtime_resolution(self):
        """Test runtime resolution support."""
        assert self.resolver.supports_runtime_resolution() is False

    def test_get_resolution_capabilities(self):
        """Test getting resolver capabilities."""
        capabilities = self.resolver.get_resolution_capabilities()

        expected_capabilities = {
            "runtime_ip_resolution": False,
            "static_ip_resolution": True,
            "hostname_resolution": True,
            "port_resolution": True,
            "service_name_resolution": True,
            "decimal_ip_format": True,
            "dotted_ip_format": True,
            "string_ip_format": True,
            "integer_ip_format": True,
            "role_based_assignment": True,
        }

        assert capabilities == expected_capabilities

    def test_get_service_info_creates_new_info(self):
        """Test getting service info creates new service info if not exists."""
        context = NetworkResolutionContext(environment_type="shadow_ns")
        self.resolver.service_roles["test_service"] = "server"

        service_info = self.resolver.get_service_info("test_service", context)

        assert service_info.service_name == "test_service"
        assert service_info.hostname == "11.0.0.1"
        assert service_info.ip_address == "11.0.0.1"
        assert service_info.port == 4433
        assert service_info.additional_info["environment"] == "shadow_ns"
        assert service_info.additional_info["role"] == "server"

    def test_get_service_info_returns_existing(self):
        """Test getting service info returns existing service info."""
        context = NetworkResolutionContext(environment_type="shadow_ns")
        existing_info = NetworkServiceInfo(
            service_name="existing_service",
            hostname="existing_host",
            ip_address="192.168.1.1",
            port=8080,
        )
        context.add_service(existing_info)

        service_info = self.resolver.get_service_info("existing_service", context)

        assert service_info is existing_info
        assert service_info.hostname == "existing_host"
        assert service_info.ip_address == "192.168.1.1"

    def test_populate_service_network_info(self):
        """Test populating service network information."""
        context = NetworkResolutionContext(environment_type="shadow_ns")

        # Add services with minimal info
        service1 = NetworkServiceInfo(service_name="server_service")
        service2 = NetworkServiceInfo(service_name="client_service")
        context.add_service(service1)
        context.add_service(service2)

        # Set up roles
        self.resolver.service_roles = {
            "server_service": "server",
            "client_service": "client",
        }

        self.resolver.populate_service_network_info(context)

        # Check server service
        server_info = context.get_service_info("server_service")
        assert server_info.hostname == "11.0.0.1"
        assert server_info.ip_address == "11.0.0.1"
        assert server_info.port == 4433
        assert server_info.additional_info["environment"] == "shadow_ns"
        assert server_info.additional_info["role"] == "server"

        # Check client service
        client_info = context.get_service_info("client_service")
        assert client_info.hostname == "11.0.0.2"
        assert client_info.ip_address == "11.0.0.2"
        assert client_info.port == 4433
        assert client_info.additional_info["role"] == "client"

    def test_populate_service_network_info_exception_handling(self):
        """Test network discovery exception handling during population."""
        context = NetworkResolutionContext(environment_type="shadow_ns")

        # Make available_services a property that raises an exception when iterated
        # Use a mock context that raises on .items() call
        mock_context = Mock(spec=NetworkResolutionContext)
        mock_context.available_services = Mock()
        mock_context.available_services.items = Mock(
            side_effect=Exception("Test error")
        )

        with pytest.raises(NetworkDiscoveryException) as exc_info:
            self.resolver.populate_service_network_info(mock_context)

        assert "Failed to populate service network info" in str(exc_info.value)
        resolution_ctx = exc_info.value.context["resolution_context"]
        assert resolution_ctx["discovery_method"] == "shadow_service_discovery"
        assert resolution_ctx["network_environment"] == "shadow_ns"

    def test_create_resolution_context(self):
        """Test creating resolution context."""
        # Mock service managers
        mock_server = Mock()
        mock_server.role.name = "server"

        mock_client = Mock()
        mock_client.role.name = "client"

        service_managers = {"test_server": mock_server, "test_client": mock_client}

        context = self.resolver.create_resolution_context("shadow_ns", service_managers)

        assert context.environment_type == "shadow_ns"
        assert len(context.available_services) == 2

        # Check service roles were registered
        assert self.resolver.service_roles["test_server"] == "server"
        assert self.resolver.service_roles["test_client"] == "client"

        # Check service info was created
        server_info = context.get_service_info("test_server")
        assert server_info.ip_address == "11.0.0.1"

        client_info = context.get_service_info("test_client")
        assert client_info.ip_address == "11.0.0.2"

    def test_create_resolution_context_role_fallback(self):
        """Test creating resolution context with role fallback."""
        # Mock service manager without role
        mock_service = Mock()
        mock_service.role = None

        service_managers = {"test_service": mock_service}

        context = self.resolver.create_resolution_context("shadow_ns", service_managers)

        # Should default to server role
        assert self.resolver.service_roles["test_service"] == "server"

        service_info = context.get_service_info("test_service")
        assert service_info.ip_address == "11.0.0.1"

    def test_resolve_network_placeholders_success(self):
        """Test successful network placeholder resolution."""
        # Mock placeholder
        mock_placeholder = Mock()
        mock_placeholder.service = "test_service"
        mock_placeholder.attribute = NetworkAttribute.IP
        mock_placeholder.format_type = NetworkFormat.DOTTED
        mock_placeholder.raw_placeholder = "@{test_service:ip:dotted}"

        # Create resolver and mock its parser directly
        resolver = ShadowNetworkResolver()
        resolver.parser = Mock()
        resolver.parser.parse_placeholders.return_value = [mock_placeholder]
        resolver.service_roles["test_service"] = "server"

        context = NetworkResolutionContext(environment_type="shadow_ns")

        results = resolver.resolve_network_placeholders(
            "command @{test_service:ip:dotted}", context
        )

        assert len(results) == 1
        assert results[0].original_placeholder == "@{test_service:ip:dotted}"
        assert results[0].resolved_value == "11.0.0.1"
        assert results[0].resolution_method == "shadow_static"
        assert results[0].environment_type == "shadow_ns"

    def test_resolve_network_placeholders_exception_handling(self):
        """Test exception handling during placeholder resolution."""
        # Create resolver and mock its parser to raise exception
        resolver = ShadowNetworkResolver()
        resolver.parser = Mock()
        resolver.parser.parse_placeholders.side_effect = Exception("Parser error")

        context = NetworkResolutionContext(environment_type="shadow_ns")

        with pytest.raises(EnvironmentResolutionException) as exc_info:
            resolver.resolve_network_placeholders("command @{test:ip:dotted}", context)

        assert "Failed to resolve placeholders in template" in str(exc_info.value)
        resolution_ctx = exc_info.value.context["resolution_context"]
        assert resolution_ctx["environment_type"] == "shadow_ns"

    def test_generate_resolved_value_ip_dotted(self):
        """Test generating resolved value for IP in dotted format."""
        placeholder = PlaceholderInfo(
            service="test_service",
            attribute=NetworkAttribute.IP,
            format_type=NetworkFormat.DOTTED,
            raw_placeholder="@{test_service:ip:dotted}",
        )

        service_info = NetworkServiceInfo(
            service_name="test_service", ip_address="11.0.0.1"
        )

        result = self.resolver._generate_resolved_value(placeholder, service_info)
        assert result == "11.0.0.1"

    def test_generate_resolved_value_hostname(self):
        """Test generating resolved value for hostname."""
        placeholder = PlaceholderInfo(
            service="test_service",
            attribute=NetworkAttribute.HOSTNAME,
            format_type=NetworkFormat.STRING,
            raw_placeholder="@{test_service:hostname:string}",
        )

        service_info = NetworkServiceInfo(
            service_name="test_service", ip_address="11.0.0.2"
        )

        result = self.resolver._generate_resolved_value(placeholder, service_info)
        assert result == "11.0.0.2"  # For Shadow NS, hostname is IP

    def test_generate_resolved_value_service_name(self):
        """Test generating resolved value for service name."""
        placeholder = PlaceholderInfo(
            service="test_service",
            attribute=NetworkAttribute.SERVICE_NAME,
            format_type=NetworkFormat.STRING,
            raw_placeholder="@{test_service:service_name:string}",
        )

        service_info = NetworkServiceInfo(service_name="test_service")

        result = self.resolver._generate_resolved_value(placeholder, service_info)
        assert result == "test_service"

    def test_generate_resolved_value_port(self):
        """Test generating resolved value for port."""
        placeholder = PlaceholderInfo(
            service="test_service",
            attribute=NetworkAttribute.PORT,
            format_type=NetworkFormat.STRING,
            raw_placeholder="@{test_service:port:string}",
        )

        service_info = NetworkServiceInfo(service_name="test_service", port=8080)

        result = self.resolver._generate_resolved_value(placeholder, service_info)
        assert result == "8080"

    def test_generate_resolved_value_port_default(self):
        """Test generating resolved value for port with default."""
        placeholder = PlaceholderInfo(
            service="test_service",
            attribute=NetworkAttribute.PORT,
            format_type=NetworkFormat.STRING,
            raw_placeholder="@{test_service:port:string}",
        )

        service_info = NetworkServiceInfo(service_name="test_service")  # No port set

        result = self.resolver._generate_resolved_value(placeholder, service_info)
        assert result == "4433"  # Should use default port

    def test_generate_resolved_value_unsupported_attribute(self):
        """Test exception for unsupported attribute."""
        # Use a Mock placeholder with an unsupported attribute value
        # since Pydantic v2 validates enum values and rejects invalid strings
        mock_attr = Mock()
        mock_attr.value = "unsupported_attr"

        placeholder = Mock()
        placeholder.service = "test_service"
        placeholder.attribute = mock_attr  # Not a valid NetworkAttribute
        placeholder.format_type = NetworkFormat.STRING
        placeholder.raw_placeholder = "@{test_service:unsupported:string}"

        service_info = NetworkServiceInfo(service_name="test_service")

        with pytest.raises(ServiceResolutionException) as exc_info:
            self.resolver._generate_resolved_value(placeholder, service_info)

        assert "Unsupported attribute for Shadow NS" in str(exc_info.value)
        resolution_ctx = exc_info.value.context["resolution_context"]
        assert resolution_ctx["service_name"] == "test_service"
