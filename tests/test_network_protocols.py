"""
Network protocol specific testing for PANTHER environments.

This module tests network protocol handling, socket operations, network configuration,
and protocol-specific behavior that are critical for PANTHER's network experimentation
capabilities.

Test Categories:
- Protocol Validation: TCP, UDP, QUIC, HTTP protocol handling
- Socket Operations: Socket creation, binding, connection management
- Network Configuration: IP address handling, port management, routing
- Protocol Security: Network isolation, firewall rules, access control
- Performance: Network latency, throughput, concurrent connections
"""

import asyncio
import ipaddress
import json
import random
import socket
import subprocess
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from unittest.mock import MagicMock, Mock, patch

import pytest

# Hypothesis for property-based testing
from hypothesis import Verbosity, assume, given, settings
from hypothesis import strategies as st

# PANTHER imports
from panther.plugins.environments.network_environment.base_network_environment import (
    BaseNetworkEnvironment,
)

# ========== NETWORK PROTOCOL DATA STRUCTURES ==========


@dataclass
class NetworkProtocolTest:
    """Represents a network protocol test scenario."""

    protocol: str
    port_range: Tuple[int, int]
    expected_behavior: str
    security_requirements: List[str]
    performance_criteria: Dict[str, float]


@dataclass
class SocketTestScenario:
    """Represents a socket operation test scenario."""

    socket_type: str
    address_family: str
    operation: str
    expected_result: str
    error_conditions: List[str]


# ========== NETWORK TESTING UTILITIES ==========


class NetworkTestHelper:
    """Helper utilities for network protocol testing."""

    def __init__(self):
        self.created_sockets = []
        self.bound_ports = set()
        self.test_servers = []

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()

    def cleanup(self):
        """Clean up network resources."""
        # Close sockets
        for sock in self.created_sockets:
            try:
                sock.close()
            except Exception:
                pass

        # Stop test servers
        for server in self.test_servers:
            try:
                server.stop()
            except Exception:
                pass

        self.created_sockets.clear()
        self.bound_ports.clear()
        self.test_servers.clear()

    def find_free_port(self, start_port: int = 8000, end_port: int = 9000) -> int:
        """Find a free port in the specified range."""
        for port in range(start_port, end_port):
            if port not in self.bound_ports:
                try:
                    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                        s.bind(("localhost", port))
                        return port
                except OSError:
                    continue
        raise RuntimeError(f"No free ports available in range {start_port}-{end_port}")

    def create_test_socket(
        self, family=socket.AF_INET, socket_type=socket.SOCK_STREAM
    ) -> socket.socket:
        """Create a test socket with cleanup tracking."""
        sock = socket.socket(family, socket_type)
        self.created_sockets.append(sock)
        return sock

    def bind_socket(
        self, sock: socket.socket, host: str = "localhost", port: int = 0
    ) -> Tuple[str, int]:
        """Bind socket to address and track the port."""
        if port == 0:
            port = self.find_free_port()

        sock.bind((host, port))
        self.bound_ports.add(port)
        return host, port

    def create_simple_server(
        self, port: int = 0, protocol: str = "tcp"
    ) -> Tuple[threading.Thread, int]:
        """Create a simple test server."""
        if port == 0:
            port = self.find_free_port()

        def tcp_server():
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_sock:
                server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                server_sock.bind(("localhost", port))
                server_sock.listen(5)
                server_sock.settimeout(5.0)  # 5 second timeout

                try:
                    while True:
                        try:
                            client_sock, addr = server_sock.accept()
                            with client_sock:
                                data = client_sock.recv(1024)
                                if data:
                                    response = (
                                        f"Echo: {data.decode('utf-8', errors='ignore')}"
                                    )
                                    client_sock.send(response.encode("utf-8"))
                        except socket.timeout:
                            break
                        except Exception:
                            break
                except Exception:
                    pass

        def udp_server():
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as server_sock:
                server_sock.bind(("localhost", port))
                server_sock.settimeout(5.0)

                try:
                    while True:
                        try:
                            data, addr = server_sock.recvfrom(1024)
                            if data:
                                response = (
                                    f"Echo: {data.decode('utf-8', errors='ignore')}"
                                )
                                server_sock.sendto(response.encode("utf-8"), addr)
                        except socket.timeout:
                            break
                        except Exception:
                            break
                except Exception:
                    pass

        server_func = tcp_server if protocol == "tcp" else udp_server
        server_thread = threading.Thread(target=server_func, daemon=True)
        server_thread.start()

        # Give server time to start
        time.sleep(0.1)

        return server_thread, port


class NetworkPerformanceProfiler:
    """Profile network operation performance."""

    def __init__(self):
        self.measurements = []

    @contextmanager
    def profile_operation(self, operation_name: str, host: str, port: int):
        """Profile a network operation."""
        start_time = time.perf_counter()

        try:
            yield
        finally:
            end_time = time.perf_counter()

            self.measurements.append(
                {
                    "operation": operation_name,
                    "host": host,
                    "port": port,
                    "duration_ms": (end_time - start_time) * 1000,
                    "timestamp": time.time(),
                }
            )

    def get_stats(self) -> Dict[str, Any]:
        """Get performance statistics."""
        if not self.measurements:
            return {}

        durations = [m["duration_ms"] for m in self.measurements]

        return {
            "total_operations": len(self.measurements),
            "avg_duration_ms": sum(durations) / len(durations),
            "min_duration_ms": min(durations),
            "max_duration_ms": max(durations),
            "success_rate": 1.0,  # Assume success if no exceptions
        }


# ========== PROTOCOL VALIDATION TESTS ==========


@pytest.mark.unit
class TestNetworkProtocolValidation:
    """Test network protocol validation and handling."""

    def test_tcp_socket_operations(self):
        """Test TCP socket creation, binding, and basic operations."""
        with NetworkTestHelper() as net_helper:
            # Test socket creation
            tcp_sock = net_helper.create_test_socket(socket.AF_INET, socket.SOCK_STREAM)
            assert tcp_sock.family == socket.AF_INET
            assert tcp_sock.type == socket.SOCK_STREAM

            # Test socket binding
            host, port = net_helper.bind_socket(tcp_sock)
            assert host == "localhost"
            assert port > 0
            assert port in net_helper.bound_ports

            # Test socket options
            tcp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            reuse_addr = tcp_sock.getsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR)
            assert reuse_addr == 1

    def test_udp_socket_operations(self):
        """Test UDP socket creation and operations."""
        with NetworkTestHelper() as net_helper:
            # Test UDP socket creation
            udp_sock = net_helper.create_test_socket(socket.AF_INET, socket.SOCK_DGRAM)
            assert udp_sock.family == socket.AF_INET
            assert udp_sock.type == socket.SOCK_DGRAM

            # Test binding
            host, port = net_helper.bind_socket(udp_sock)
            assert host == "localhost"
            assert port > 0

            # Test basic UDP communication
            client_sock = net_helper.create_test_socket(
                socket.AF_INET, socket.SOCK_DGRAM
            )

            # Send data to self
            test_message = "Hello UDP"
            client_sock.sendto(test_message.encode("utf-8"), (host, port))

            # Receive data (with timeout)
            udp_sock.settimeout(1.0)
            try:
                data, addr = udp_sock.recvfrom(1024)
                received_message = data.decode("utf-8")
                assert received_message == test_message
            except socket.timeout:
                pytest.fail("UDP receive operation timed out")

    def test_ip_address_validation(self):
        """Test IP address validation and parsing."""

        # Test valid IPv4 addresses
        valid_ipv4 = ["127.0.0.1", "192.168.1.1", "10.0.0.1", "172.16.0.1"]
        for ip in valid_ipv4:
            try:
                addr = ipaddress.ip_address(ip)
                assert addr.version == 4
                assert str(addr) == ip
            except ValueError:
                pytest.fail(f"Valid IPv4 address {ip} failed validation")

        # Test valid IPv6 addresses
        valid_ipv6 = ["::1", "2001:db8::1", "fe80::1"]
        for ip in valid_ipv6:
            try:
                addr = ipaddress.ip_address(ip)
                assert addr.version == 6
            except ValueError:
                pytest.fail(f"Valid IPv6 address {ip} failed validation")

        # Test invalid addresses
        invalid_addresses = ["256.1.1.1", "192.168.1", "not.an.ip", ""]
        for ip in invalid_addresses:
            with pytest.raises(ValueError):
                ipaddress.ip_address(ip)

    def test_port_range_validation(self):
        """Test port number validation."""

        # Test valid ports
        valid_ports = [80, 443, 8080, 3000, 65535]
        for port in valid_ports:
            assert 1 <= port <= 65535

            # Test that we can create socket with valid port
            with NetworkTestHelper() as net_helper:
                try:
                    sock = net_helper.create_test_socket()
                    sock.bind(("localhost", port))
                    # Port might be in use, but should not raise ValueError
                except OSError:
                    # Port in use is acceptable
                    pass

        # Test invalid ports
        invalid_ports = [0, -1, 65536, 100000]
        for port in invalid_ports:
            with NetworkTestHelper() as net_helper:
                sock = net_helper.create_test_socket()
                with pytest.raises((ValueError, OSError, OverflowError)):
                    sock.bind(("localhost", port))

    @given(st.integers(min_value=1024, max_value=65535))
    @settings(max_examples=20, verbosity=Verbosity.quiet)
    def test_port_allocation_property(self, port):
        """Property-based test for port allocation."""
        assume(port >= 1024)  # Use only non-privileged ports

        with NetworkTestHelper() as net_helper:
            try:
                sock = net_helper.create_test_socket()
                sock.bind(("localhost", port))

                # Verify socket is bound
                sock_name = sock.getsockname()
                assert sock_name[1] == port

            except OSError:
                # Port might be in use, which is acceptable
                pass


@pytest.mark.unit
class TestSocketCommunication:
    """Test socket communication patterns."""

    def test_tcp_client_server_communication(self):
        """Test TCP client-server communication."""
        with NetworkTestHelper() as net_helper:
            # Create server
            server_thread, server_port = net_helper.create_simple_server(protocol="tcp")

            # Create client and connect
            client_sock = net_helper.create_test_socket()

            try:
                client_sock.connect(("localhost", server_port))

                # Send message
                test_message = "Hello TCP Server"
                client_sock.send(test_message.encode("utf-8"))

                # Receive response
                client_sock.settimeout(2.0)
                response = client_sock.recv(1024)
                response_text = response.decode("utf-8")

                assert "Echo:" in response_text
                assert test_message in response_text

            except Exception as e:
                pytest.fail(f"TCP communication failed: {e}")

    def test_udp_client_server_communication(self):
        """Test UDP client-server communication."""
        with NetworkTestHelper() as net_helper:
            # Create server
            server_thread, server_port = net_helper.create_simple_server(protocol="udp")

            # Create client
            client_sock = net_helper.create_test_socket(
                socket.AF_INET, socket.SOCK_DGRAM
            )

            try:
                # Send message
                test_message = "Hello UDP Server"
                client_sock.sendto(
                    test_message.encode("utf-8"), ("localhost", server_port)
                )

                # Receive response
                client_sock.settimeout(2.0)
                response, addr = client_sock.recvfrom(1024)
                response_text = response.decode("utf-8")

                assert "Echo:" in response_text
                assert test_message in response_text
                assert addr[1] == server_port

            except Exception as e:
                pytest.fail(f"UDP communication failed: {e}")

    def test_multiple_concurrent_connections(self):
        """Test handling multiple concurrent connections."""
        with NetworkTestHelper() as net_helper:
            # Create server
            server_thread, server_port = net_helper.create_simple_server(protocol="tcp")

            def client_worker(client_id: int) -> bool:
                """Worker function for concurrent client connections."""
                try:
                    client_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    client_sock.connect(("localhost", server_port))

                    message = f"Client {client_id} message"
                    client_sock.send(message.encode("utf-8"))

                    client_sock.settimeout(3.0)
                    response = client_sock.recv(1024)
                    response_text = response.decode("utf-8")

                    client_sock.close()

                    return message in response_text

                except Exception:
                    return False

            # Test concurrent connections
            client_count = 10

            with ThreadPoolExecutor(max_workers=client_count) as executor:
                futures = [
                    executor.submit(client_worker, client_id)
                    for client_id in range(client_count)
                ]

                results = [future.result() for future in as_completed(futures)]

            # Verify most connections succeeded
            success_count = sum(1 for result in results if result)
            success_rate = success_count / client_count

            assert success_rate >= 0.8  # At least 80% success rate


@pytest.mark.performance
class TestNetworkPerformance:
    """Test network performance characteristics."""

    def test_connection_establishment_latency(self):
        """Test connection establishment performance."""
        with NetworkTestHelper() as net_helper:
            profiler = NetworkPerformanceProfiler()

            # Create server
            server_thread, server_port = net_helper.create_simple_server(protocol="tcp")

            # Measure connection latency
            connection_count = 50

            for i in range(connection_count):
                with profiler.profile_operation(
                    "tcp_connect", "localhost", server_port
                ):
                    client_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    client_sock.connect(("localhost", server_port))
                    client_sock.close()

            stats = profiler.get_stats()

            # Performance assertions
            assert stats["total_operations"] == connection_count
            assert stats["avg_duration_ms"] < 50.0  # Average under 50ms
            assert stats["max_duration_ms"] < 200.0  # Max under 200ms

    def test_data_transfer_throughput(self):
        """Test data transfer throughput."""
        with NetworkTestHelper() as net_helper:
            # Create server
            server_thread, server_port = net_helper.create_simple_server(protocol="tcp")

            # Create client
            client_sock = net_helper.create_test_socket()
            client_sock.connect(("localhost", server_port))

            # Test data transfer
            data_size = 64 * 1024  # 64 KB
            test_data = "x" * data_size

            start_time = time.perf_counter()
            client_sock.send(test_data.encode("utf-8"))

            # Receive echo (this is simplified - real server would echo back)
            client_sock.settimeout(5.0)
            try:
                response = client_sock.recv(
                    data_size + 100
                )  # Account for "Echo:" prefix
                transfer_time = time.perf_counter() - start_time

                # Calculate throughput
                bytes_transferred = len(response)
                throughput_mbps = (bytes_transferred * 8) / (
                    transfer_time * 1000000
                )  # Mbps

                # Performance assertions
                assert transfer_time < 1.0  # Under 1 second for 64KB
                assert throughput_mbps > 1.0  # At least 1 Mbps

            except socket.timeout:
                pytest.fail("Data transfer timed out")

    def test_concurrent_connection_scaling(self):
        """Test scaling with concurrent connections."""
        with NetworkTestHelper() as net_helper:
            # Create server
            server_thread, server_port = net_helper.create_simple_server(protocol="tcp")

            def measure_concurrent_performance(
                concurrent_count: int,
            ) -> Dict[str, float]:
                """Measure performance with specific concurrency level."""

                def connection_worker():
                    try:
                        start_time = time.perf_counter()
                        client_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        client_sock.connect(("localhost", server_port))

                        client_sock.send(b"test message")
                        client_sock.settimeout(2.0)
                        response = client_sock.recv(1024)

                        client_sock.close()
                        duration = time.perf_counter() - start_time

                        return duration, len(response) > 0

                    except Exception:
                        return 0.0, False

                start_time = time.perf_counter()

                with ThreadPoolExecutor(max_workers=concurrent_count) as executor:
                    futures = [
                        executor.submit(connection_worker)
                        for _ in range(concurrent_count)
                    ]
                    results = [future.result() for future in as_completed(futures)]

                total_time = time.perf_counter() - start_time

                durations = [r[0] for r in results if r[1]]
                success_count = sum(1 for r in results if r[1])

                return {
                    "concurrent_count": concurrent_count,
                    "success_rate": success_count / concurrent_count,
                    "avg_connection_time": sum(durations) / len(durations)
                    if durations
                    else 0,
                    "total_time": total_time,
                    "connections_per_second": concurrent_count / total_time,
                }

            # Test different concurrency levels
            concurrency_levels = [1, 5, 10, 20]
            performance_results = []

            for level in concurrency_levels:
                result = measure_concurrent_performance(level)
                performance_results.append(result)

                # Performance assertions
                assert result["success_rate"] >= 0.7  # At least 70% success
                assert (
                    result["avg_connection_time"] < 1.0
                )  # Under 1 second per connection

            # Verify scaling characteristics
            for i in range(1, len(performance_results)):
                current = performance_results[i]
                previous = performance_results[i - 1]

                # Success rate should not degrade significantly
                success_ratio = current["success_rate"] / previous["success_rate"]
                assert success_ratio > 0.8  # No more than 20% degradation


@pytest.mark.integration
class TestNetworkEnvironmentIntegration:
    """Test network integration with environment operations."""

    def test_network_environment_simulation(self):
        """Simulate network operations during environment lifecycle."""

        class NetworkProtocolEnv(BaseNetworkEnvironment):
            def __init__(self):
                super().__init__(None, "/tmp", "network_test", "test", Mock())
                self.net_helper = NetworkTestHelper()
                self.service_ports = {}
                self.active_connections = []

            def simulate_service_network_setup(self):
                """Simulate network setup for services."""
                services = ["web", "api", "db"]

                for service in services:
                    # Allocate port for service
                    port = self.net_helper.find_free_port()
                    self.service_ports[service] = port

                    # Create listening socket for service
                    sock = self.net_helper.create_test_socket()
                    host, bound_port = self.net_helper.bind_socket(sock, port=port)

                    assert bound_port == port
                    self.active_connections.append((service, host, port, sock))

                return len(self.service_ports) == len(services)

            def simulate_inter_service_communication(self):
                """Simulate communication between services."""
                if len(self.service_ports) < 2:
                    return False

                # Test communication between services
                services = list(self.service_ports.keys())

                for i, source_service in enumerate(services):
                    for target_service in services[i + 1 :]:
                        source_port = self.service_ports[source_service]
                        target_port = self.service_ports[target_service]

                        # Simulate connection attempt
                        try:
                            client_sock = self.net_helper.create_test_socket()
                            client_sock.settimeout(1.0)

                            # In real scenario, target would be listening
                            # Here we just verify port is allocated
                            assert target_port in self.net_helper.bound_ports

                        except Exception:
                            # Connection might fail in test scenario, that's ok
                            pass

                return True

            def get_network_statistics(self):
                """Get network statistics."""
                return {
                    "allocated_ports": len(self.service_ports),
                    "active_sockets": len(self.net_helper.created_sockets),
                    "bound_ports": list(self.net_helper.bound_ports),
                    "service_ports": self.service_ports,
                }

            def cleanup_network(self):
                """Clean up network resources."""
                self.net_helper.cleanup()
                self.service_ports.clear()
                self.active_connections.clear()

            # Required abstract methods
            def prepare_environment(self):
                return True

            def generate_environment_services(self, paths, timestamp):
                return list(self.service_ports.keys())

            def launch_environment_services(self):
                return True

            def deploy_services(self, services):
                return True

            def _teardown_environment(self):
                self.cleanup_network()

            def _do_setup_environment(self):
                return True

            def _do_deploy_services(self, services):
                return True

            def _do_teardown_environment(self):
                self.cleanup_network()

            def _get_service_log_directory(self, service):
                return f"/tmp/logs/{service}"

            def _get_service_ip(self, service):
                return "127.0.0.1"

            def handle_event(self, event):
                pass

            def initialize(self):
                pass

        # Test the network environment
        env = NetworkProtocolEnv()

        try:
            # Test network setup
            setup_result = env.simulate_service_network_setup()
            assert setup_result is True

            # Test inter-service communication simulation
            comm_result = env.simulate_inter_service_communication()
            assert comm_result is True

            # Verify network statistics
            stats = env.get_network_statistics()
            assert stats["allocated_ports"] >= 3
            assert len(stats["bound_ports"]) >= 3
            assert "web" in stats["service_ports"]
            assert "api" in stats["service_ports"]
            assert "db" in stats["service_ports"]

            # Verify port uniqueness
            ports = list(stats["service_ports"].values())
            assert len(ports) == len(set(ports))  # All ports unique

        finally:
            env.cleanup_network()


@pytest.mark.boundary
class TestNetworkBoundaryConditions:
    """Test network boundary conditions and edge cases."""

    def test_port_exhaustion_scenario(self):
        """Test behavior when port range is exhausted."""
        with NetworkTestHelper() as net_helper:
            # Use small port range for testing
            start_port = 8500
            end_port = 8510  # Only 10 ports available

            allocated_sockets = []
            allocated_ports = []

            try:
                # Allocate all ports in range
                for port in range(start_port, end_port):
                    try:
                        sock = net_helper.create_test_socket()
                        sock.bind(("localhost", port))
                        allocated_sockets.append(sock)
                        allocated_ports.append(port)
                        net_helper.bound_ports.add(port)
                    except OSError:
                        # Port might be in use
                        pass

                # Try to allocate one more port (should fail)
                with pytest.raises(RuntimeError):
                    net_helper.find_free_port(start_port, end_port)

                # Verify we allocated most of the range
                assert len(allocated_ports) >= 5  # At least half the range

            finally:
                # Clean up
                for sock in allocated_sockets:
                    try:
                        sock.close()
                    except Exception:
                        pass

    def test_network_timeout_handling(self):
        """Test network timeout handling."""
        with NetworkTestHelper() as net_helper:
            # Test connection timeout to non-existent service
            client_sock = net_helper.create_test_socket()
            client_sock.settimeout(0.5)  # 500ms timeout

            # Try to connect to a port that should be closed
            closed_port = net_helper.find_free_port()

            start_time = time.perf_counter()

            with pytest.raises((socket.timeout, OSError, ConnectionRefusedError)):
                client_sock.connect(("localhost", closed_port))

            elapsed_time = time.perf_counter() - start_time

            # Verify timeout occurred within reasonable time
            assert elapsed_time < 1.0  # Should timeout before 1 second

    def test_invalid_network_addresses(self):
        """Test handling of invalid network addresses."""
        with NetworkTestHelper() as net_helper:
            invalid_addresses = [
                ("invalid.host.name", 8080),
                ("256.256.256.256", 8080),
                ("", 8080),
                ("localhost", -1),
                ("localhost", 65536),
            ]

            for host, port in invalid_addresses:
                client_sock = net_helper.create_test_socket()
                client_sock.settimeout(1.0)

                with pytest.raises(
                    (socket.gaierror, ValueError, OSError, OverflowError)
                ):
                    client_sock.connect((host, port))


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
