"""Functional tests for localhost placeholder resolution end-to-end behavior."""

import pytest

from panther.plugins.environments.network_environment.localhost_single_container.localhost_network_resolver import (
    LocalhostNetworkResolver,
)


class TestLocalhostPlaceholderResolutionFunctional:
    """Functional tests for localhost placeholder resolution."""

    def test_realistic_ivy_service_scenario(self):
        """Test realistic Ivy service command resolution scenario."""
        # Arrange: Set up resolver with typical PANTHER services
        resolver = LocalhostNetworkResolver()
        services = ["ivy_service", "picoquic_server", "quiche_client", "quic_go_server"]
        resolver.register_services(services)

        # Create context as would happen in real environment
        mock_service_managers = {name: None for name in services}
        context = resolver.create_resolution_context(
            "localhost_single_container", mock_service_managers
        )

        # Act: Test typical Ivy commands that would fail with empty parameters
        test_scenarios = [
            {
                "name": "Ivy client connecting to picoquic server",
                "command": "ivy_client --server_addr=@{picoquic_server:ip:decimal} --server_port=@{picoquic_server:port} --cid=test_cid",
                "expected_contains": ["2130706433", "5010", "cid=test_cid"],
            },
            {
                "name": "QUIC client with localhost hostname",
                "command": "quiche_client --host=@{ivy_service:hostname} --port=@{ivy_service:port} --data=/test.txt",
                "expected_contains": ["127.0.0.1", "5000", "/test.txt"],
            },
            {
                "name": "Server configuration with self-reference",
                "command": "quic_go_server --bind=@{quic_go_server:ip} --port=@{quic_go_server:port} --cert=/certs/server.crt",
                "expected_contains": ["127.0.0.1", "5030", "/certs/server.crt"],
            },
            {
                "name": "Complex multi-service scenario",
                "command": "test_harness --client=@{ivy_service:service_name} --server=@{picoquic_server:hostname}:@{picoquic_server:port}",
                "expected_contains": ["ivy_service", "127.0.0.1:5010"],
            },
        ]

        # Act & Assert: Test each scenario
        for scenario in test_scenarios:
            results = resolver.resolve_network_placeholders(
                scenario["command"], context
            )

            resolved_command = scenario["command"]
            for result in results:
                placeholder, value = result.to_substitution_pair()
                resolved_command = resolved_command.replace(placeholder, value)

            # Verify all expected content is present
            for expected in scenario["expected_contains"]:
                assert (
                    expected in resolved_command
                ), f"Expected '{expected}' in resolved command: {resolved_command}"

            # Verify no unresolved placeholders remain
            assert (
                "@{" not in resolved_command
            ), f"Unresolved placeholder in: {resolved_command}"

            print(f"✓ {scenario['name']}: {resolved_command}")

    def test_port_assignment_consistency(self):
        """Test that port assignments follow the documented pattern."""
        # Arrange: Set up resolver with known services
        resolver = LocalhostNetworkResolver()
        services = ["service_a", "service_b", "service_c", "service_d"]
        resolver.register_services(services)

        # Act: Check port assignments
        registry = resolver.get_service_registry()

        # Assert: Verify port calculation follows base_port + (index * offset) pattern
        expected_ports = {
            "service_a": 5000,  # 5000 + (0 * 10)
            "service_b": 5010,  # 5000 + (1 * 10)
            "service_c": 5020,  # 5000 + (2 * 10)
            "service_d": 5030,  # 5000 + (3 * 10)
        }

        for service_name, expected_port in expected_ports.items():
            index = registry[service_name]
            actual_port = resolver._calculate_port(index)
            assert (
                actual_port == expected_port
            ), f"Service {service_name} expected port {expected_port}, got {actual_port}"

    def test_ip_format_accuracy(self):
        """Test that IP format conversions are mathematically correct."""
        # Arrange
        resolver = LocalhostNetworkResolver()

        # Act & Assert: Test each format conversion
        from panther.config.core.models.network_resolution import NetworkFormat

        # Test decimal conversion: 127.0.0.1 = (127 << 24) + (0 << 16) + (0 << 8) + 1
        decimal_result = resolver._format_ip_address(NetworkFormat.DECIMAL)
        expected_decimal = str((127 << 24) + 1)  # 2130706433
        assert (
            decimal_result == expected_decimal
        ), f"Decimal conversion incorrect: {decimal_result} != {expected_decimal}"

        # Test dotted notation
        dotted_result = resolver._format_ip_address(NetworkFormat.DOTTED)
        assert dotted_result == "127.0.0.1", f"Dotted format incorrect: {dotted_result}"

        # Test string format
        string_result = resolver._format_ip_address(NetworkFormat.STRING)
        assert string_result == "127.0.0.1", f"String format incorrect: {string_result}"

    def test_resolver_capabilities_accuracy(self):
        """Test that resolver reports its capabilities accurately."""
        # Arrange
        resolver = LocalhostNetworkResolver()

        # Act
        capabilities = resolver.get_resolution_capabilities()

        # Assert: Verify localhost-specific capabilities
        expected_capabilities = {
            "runtime_ip_resolution": False,  # Localhost uses static calculation
            "static_ip_resolution": True,  # All IPs are 127.0.0.1
            "hostname_resolution": True,  # Hostnames supported
            "port_resolution": True,  # Calculated ports
            "service_name_resolution": True,  # Service names supported
            "decimal_ip_format": True,  # Decimal format supported
            "dotted_ip_format": True,  # Dotted format supported
            "calculated_ports": True,  # Port calculation supported
        }

        for capability, expected_value in expected_capabilities.items():
            assert capability in capabilities, f"Missing capability: {capability}"
            assert (
                capabilities[capability] == expected_value
            ), f"Capability {capability} expected {expected_value}, got {capabilities[capability]}"

    def test_empty_parameters_problem_solution(self):
        """Test that the implementation solves the original 'empty parameters' problem."""
        # Arrange: Simulate the original problem scenario
        resolver = LocalhostNetworkResolver()
        resolver.register_services(["ivy_service", "target_server"])

        mock_service_managers = {"ivy_service": None, "target_server": None}
        context = resolver.create_resolution_context(
            "localhost_single_container", mock_service_managers
        )

        # Act: Test the problematic command from the original issue
        # Original problem: "Parameters empty: seed= the_cid= server_port= iversion= server_addr="
        problematic_command = "ivy_server --seed=@{ivy_service:service_name} --the_cid=test_cid --server_port=@{target_server:port} --iversion=1 --server_addr=@{target_server:ip:decimal}"

        results = resolver.resolve_network_placeholders(problematic_command, context)
        resolved_command = problematic_command

        for result in results:
            placeholder, value = result.to_substitution_pair()
            resolved_command = resolved_command.replace(placeholder, value)

        # Assert: Verify all parameters now have values
        assert "seed=ivy_service" in resolved_command
        assert "server_port=5010" in resolved_command  # target_server gets index 1
        assert "server_addr=2130706433" in resolved_command  # Decimal format
        assert "the_cid=test_cid" in resolved_command  # Non-placeholder preserved
        assert "iversion=1" in resolved_command  # Non-placeholder preserved

        # Most importantly: no empty parameters
        assert "seed=" not in resolved_command.replace("seed=ivy_service", "")
        assert "server_port=" not in resolved_command.replace("server_port=5010", "")
        assert "server_addr=" not in resolved_command.replace(
            "server_addr=2130706433", ""
        )

        print(f"✓ Original problem solved: {resolved_command}")
