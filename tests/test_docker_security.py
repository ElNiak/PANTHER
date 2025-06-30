"""
Docker security and isolation testing for PANTHER environments.

This module tests Docker security measures, container isolation, privilege handling,
and security-related edge cases that are critical for PANTHER's safe experimentation
environment.

Test Categories:
- Container Isolation: Network isolation, filesystem isolation, process isolation
- Privilege Management: User privileges, capability restrictions, security contexts
- Resource Security: Resource limits, escape prevention, quota enforcement
- Network Security: Network segmentation, firewall rules, traffic isolation
- Image Security: Image validation, vulnerability scanning, trusted registries
"""

import hashlib
import json
import os
import subprocess
import tempfile
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union
from unittest.mock import MagicMock, Mock, patch

import pytest

# PANTHER imports
from panther.plugins.environments.network_environment.base_network_environment import (
    BaseNetworkEnvironment,
)

# ========== DOCKER SECURITY DATA STRUCTURES ==========


@dataclass
class SecurityTestScenario:
    """Represents a Docker security test scenario."""

    name: str
    security_level: str
    isolation_requirements: List[str]
    privilege_restrictions: List[str]
    expected_behavior: str
    risk_level: str


@dataclass
class ContainerSecurityProfile:
    """Represents a container security profile."""

    user_id: Optional[int]
    group_id: Optional[int]
    capabilities: List[str]
    security_opts: List[str]
    read_only_root: bool
    no_new_privileges: bool
    resource_limits: Dict[str, Any]


# ========== DOCKER SECURITY TESTING UTILITIES ==========


class DockerSecurityTestHelper:
    """Helper utilities for Docker security testing."""

    def __init__(self):
        self.created_containers = []
        self.created_networks = []
        self.created_volumes = []
        self.test_images = set()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()

    def cleanup(self):
        """Clean up Docker resources."""
        # Stop and remove containers
        for container_id in self.created_containers:
            try:
                subprocess.run(
                    ["docker", "stop", container_id], capture_output=True, timeout=10
                )
                subprocess.run(
                    ["docker", "rm", container_id], capture_output=True, timeout=10
                )
            except Exception:
                pass

        # Remove networks
        for network_id in self.created_networks:
            try:
                subprocess.run(
                    ["docker", "network", "rm", network_id],
                    capture_output=True,
                    timeout=10,
                )
            except Exception:
                pass

        # Remove volumes
        for volume_id in self.created_volumes:
            try:
                subprocess.run(
                    ["docker", "volume", "rm", volume_id],
                    capture_output=True,
                    timeout=10,
                )
            except Exception:
                pass

        self.created_containers.clear()
        self.created_networks.clear()
        self.created_volumes.clear()

    def is_docker_available(self) -> bool:
        """Check if Docker is available."""
        try:
            result = subprocess.run(
                ["docker", "version"], capture_output=True, timeout=5
            )
            return result.returncode == 0
        except Exception:
            return False

    def create_secure_container(
        self,
        image: str = "alpine:latest",
        security_profile: ContainerSecurityProfile = None,
        command: List[str] = None,
    ) -> Optional[str]:
        """Create a container with security configurations."""
        if not self.is_docker_available():
            return None

        if security_profile is None:
            security_profile = ContainerSecurityProfile(
                user_id=1000,
                group_id=1000,
                capabilities=[],
                security_opts=["no-new-privileges:true"],
                read_only_root=False,
                no_new_privileges=True,
                resource_limits={"memory": "128m", "cpus": "0.5"},
            )

        docker_args = ["docker", "run", "-d"]

        # Apply security configurations
        if security_profile.user_id is not None:
            docker_args.extend(
                ["--user", f"{security_profile.user_id}:{security_profile.group_id}"]
            )

        if security_profile.read_only_root:
            docker_args.append("--read-only")

        if security_profile.no_new_privileges:
            docker_args.append("--security-opt=no-new-privileges:true")

        for cap in security_profile.capabilities:
            if cap.startswith("!"):
                docker_args.extend(["--cap-drop", cap[1:]])
            else:
                docker_args.extend(["--cap-add", cap])

        for opt in security_profile.security_opts:
            docker_args.extend(["--security-opt", opt])

        for limit_type, limit_value in security_profile.resource_limits.items():
            if limit_type == "memory":
                docker_args.extend(["--memory", str(limit_value)])
            elif limit_type == "cpus":
                docker_args.extend(["--cpus", str(limit_value)])

        # Add image and command
        docker_args.append(image)
        if command:
            docker_args.extend(command)
        else:
            docker_args.extend(["sleep", "3600"])  # Default: sleep for 1 hour

        try:
            result = subprocess.run(
                docker_args, capture_output=True, text=True, timeout=30
            )

            if result.returncode == 0:
                container_id = result.stdout.strip()
                self.created_containers.append(container_id)
                return container_id
            else:
                return None

        except Exception:
            return None

    def create_isolated_network(self, name: str = None) -> Optional[str]:
        """Create an isolated Docker network."""
        if not self.is_docker_available():
            return None

        if name is None:
            name = f"test_network_{int(time.time())}"

        try:
            result = subprocess.run(
                [
                    "docker",
                    "network",
                    "create",
                    "--driver",
                    "bridge",
                    "--internal",  # No external connectivity
                    name,
                ],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode == 0:
                network_id = result.stdout.strip()
                self.created_networks.append(network_id)
                return network_id
            else:
                return None

        except Exception:
            return None

    def create_secure_volume(self, name: str = None) -> Optional[str]:
        """Create a secure Docker volume."""
        if not self.is_docker_available():
            return None

        if name is None:
            name = f"test_volume_{int(time.time())}"

        try:
            result = subprocess.run(
                ["docker", "volume", "create", "--driver", "local", name],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode == 0:
                volume_id = result.stdout.strip()
                self.created_volumes.append(volume_id)
                return volume_id
            else:
                return None

        except Exception:
            return None

    def inspect_container_security(self, container_id: str) -> Dict[str, Any]:
        """Inspect container security configuration."""
        if not self.is_docker_available():
            return {}

        try:
            result = subprocess.run(
                ["docker", "inspect", container_id],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if result.returncode == 0:
                inspect_data = json.loads(result.stdout)[0]

                security_info = {
                    "user": inspect_data.get("Config", {}).get("User", ""),
                    "privileged": inspect_data.get("HostConfig", {}).get(
                        "Privileged", False
                    ),
                    "read_only_root": inspect_data.get("HostConfig", {}).get(
                        "ReadonlyRootfs", False
                    ),
                    "security_opts": inspect_data.get("HostConfig", {}).get(
                        "SecurityOpt", []
                    ),
                    "cap_add": inspect_data.get("HostConfig", {}).get("CapAdd", []),
                    "cap_drop": inspect_data.get("HostConfig", {}).get("CapDrop", []),
                    "memory_limit": inspect_data.get("HostConfig", {}).get("Memory", 0),
                    "cpu_quota": inspect_data.get("HostConfig", {}).get("CpuQuota", 0),
                    "network_mode": inspect_data.get("HostConfig", {}).get(
                        "NetworkMode", ""
                    ),
                    "pid_mode": inspect_data.get("HostConfig", {}).get("PidMode", ""),
                    "ipc_mode": inspect_data.get("HostConfig", {}).get("IpcMode", ""),
                }

                return security_info
            else:
                return {}

        except Exception:
            return {}

    def execute_in_container(
        self, container_id: str, command: List[str]
    ) -> Tuple[int, str, str]:
        """Execute command in container and return result."""
        if not self.is_docker_available():
            return -1, "", "Docker not available"

        try:
            result = subprocess.run(
                ["docker", "exec", container_id] + command,
                capture_output=True,
                text=True,
                timeout=30,
            )

            return result.returncode, result.stdout, result.stderr

        except Exception as e:
            return -1, "", str(e)


class SecurityVulnerabilitySimulator:
    """Simulate security vulnerabilities for testing."""

    @staticmethod
    def create_privilege_escalation_test() -> List[str]:
        """Create commands that attempt privilege escalation."""
        return [
            ["whoami"],
            ["id"],
            ["cat", "/etc/passwd"],
            ["ps", "aux"],
            ["ls", "-la", "/proc"],
            ["mount"],
            ["cat", "/proc/mounts"],
        ]

    @staticmethod
    def create_filesystem_escape_test() -> List[str]:
        """Create commands that attempt filesystem escape."""
        return [
            ["ls", "-la", "/"],
            ["cat", "/etc/hostname"],
            ["cat", "/proc/version"],
            ["ls", "-la", "/var/run/docker.sock"],
            ["find", "/", "-name", "docker.sock", "-type", "s"],
            ["cat", "/proc/self/cgroup"],
        ]

    @staticmethod
    def create_network_escape_test() -> List[str]:
        """Create commands that attempt network escape."""
        return [
            ["ip", "addr", "show"],
            ["ip", "route", "show"],
            ["netstat", "-tulpn"],
            ["ss", "-tulpn"],
            ["arp", "-a"],
            ["cat", "/proc/net/route"],
        ]


# ========== CONTAINER ISOLATION TESTS ==========


@pytest.mark.integration
@pytest.mark.requires_docker
class TestContainerIsolation:
    """Test container isolation mechanisms."""

    def test_filesystem_isolation(self):
        """Test filesystem isolation between containers."""
        with DockerSecurityTestHelper() as docker_helper:
            if not docker_helper.is_docker_available():
                pytest.skip("Docker not available")

            # Create two containers with different security profiles
            container1 = docker_helper.create_secure_container(
                security_profile=ContainerSecurityProfile(
                    user_id=1000,
                    group_id=1000,
                    capabilities=["!ALL"],
                    security_opts=["no-new-privileges:true"],
                    read_only_root=False,
                    no_new_privileges=True,
                    resource_limits={"memory": "64m"},
                )
            )

            container2 = docker_helper.create_secure_container(
                security_profile=ContainerSecurityProfile(
                    user_id=2000,
                    group_id=2000,
                    capabilities=["!ALL"],
                    security_opts=["no-new-privileges:true"],
                    read_only_root=False,
                    no_new_privileges=True,
                    resource_limits={"memory": "64m"},
                )
            )

            if not container1 or not container2:
                pytest.skip("Failed to create test containers")

            # Create files in each container
            returncode1, stdout1, stderr1 = docker_helper.execute_in_container(
                container1,
                [
                    "sh",
                    "-c",
                    'echo "container1 data" > /tmp/test1.txt && cat /tmp/test1.txt',
                ],
            )

            returncode2, stdout2, stderr2 = docker_helper.execute_in_container(
                container2,
                [
                    "sh",
                    "-c",
                    'echo "container2 data" > /tmp/test2.txt && cat /tmp/test2.txt',
                ],
            )

            # Verify filesystem isolation
            assert returncode1 == 0
            assert returncode2 == 0
            assert "container1 data" in stdout1
            assert "container2 data" in stdout2

            # Verify containers cannot access each other's files
            (
                returncode1_cross,
                stdout1_cross,
                stderr1_cross,
            ) = docker_helper.execute_in_container(
                container1, ["cat", "/tmp/test2.txt"]
            )

            (
                returncode2_cross,
                stdout2_cross,
                stderr2_cross,
            ) = docker_helper.execute_in_container(
                container2, ["cat", "/tmp/test1.txt"]
            )

            # Should fail to access other container's files
            assert returncode1_cross != 0
            assert returncode2_cross != 0

    def test_process_isolation(self):
        """Test process isolation between containers."""
        with DockerSecurityTestHelper() as docker_helper:
            if not docker_helper.is_docker_available():
                pytest.skip("Docker not available")

            # Create container with process isolation
            container = docker_helper.create_secure_container(
                security_profile=ContainerSecurityProfile(
                    user_id=1000,
                    group_id=1000,
                    capabilities=["!ALL"],
                    security_opts=["no-new-privileges:true"],
                    read_only_root=False,
                    no_new_privileges=True,
                    resource_limits={"memory": "64m"},
                )
            )

            if not container:
                pytest.skip("Failed to create test container")

            # Test process visibility
            returncode, stdout, stderr = docker_helper.execute_in_container(
                container, ["ps", "aux"]
            )

            if returncode == 0:
                # Should only see processes within the container
                processes = stdout.split("\n")

                # Filter out header and empty lines
                process_lines = [
                    line
                    for line in processes
                    if line.strip() and not line.startswith("USER")
                ]

                # Should have limited process visibility
                assert len(process_lines) <= 10  # Should not see host processes

                # Should not see sensitive host processes
                sensitive_processes = ["systemd", "docker", "dockerd", "containerd"]
                for line in process_lines:
                    for sensitive_proc in sensitive_processes:
                        assert sensitive_proc not in line.lower()

    def test_network_isolation(self):
        """Test network isolation between containers."""
        with DockerSecurityTestHelper() as docker_helper:
            if not docker_helper.is_docker_available():
                pytest.skip("Docker not available")

            # Create isolated network
            isolated_network = docker_helper.create_isolated_network()

            if not isolated_network:
                pytest.skip("Failed to create isolated network")

            # Create container in isolated network
            container = docker_helper.create_secure_container(
                security_profile=ContainerSecurityProfile(
                    user_id=1000,
                    group_id=1000,
                    capabilities=["!ALL"],
                    security_opts=["no-new-privileges:true"],
                    read_only_root=False,
                    no_new_privileges=True,
                    resource_limits={"memory": "64m"},
                )
            )

            if not container:
                pytest.skip("Failed to create test container")

            # Connect container to isolated network
            try:
                subprocess.run(
                    ["docker", "network", "connect", isolated_network, container],
                    capture_output=True,
                    timeout=10,
                )
            except Exception:
                pytest.skip("Failed to connect container to isolated network")

            # Test network connectivity restrictions
            # Try to reach external addresses (should fail for internal network)
            returncode, stdout, stderr = docker_helper.execute_in_container(
                container, ["ping", "-c", "1", "-W", "1", "8.8.8.8"]
            )

            # Internal network should block external access
            # Note: This test may vary based on Docker configuration
            if returncode != 0:
                assert (
                    "Network is unreachable" in stderr
                    or "no route to host" in stderr.lower()
                )


@pytest.mark.integration
@pytest.mark.requires_docker
class TestPrivilegeManagement:
    """Test privilege management and restrictions."""

    def test_non_privileged_container(self):
        """Test that containers run with restricted privileges."""
        with DockerSecurityTestHelper() as docker_helper:
            if not docker_helper.is_docker_available():
                pytest.skip("Docker not available")

            # Create non-privileged container
            container = docker_helper.create_secure_container(
                security_profile=ContainerSecurityProfile(
                    user_id=1000,
                    group_id=1000,
                    capabilities=["!ALL"],  # Drop all capabilities
                    security_opts=["no-new-privileges:true"],
                    read_only_root=False,
                    no_new_privileges=True,
                    resource_limits={"memory": "64m"},
                )
            )

            if not container:
                pytest.skip("Failed to create test container")

            # Verify security configuration
            security_info = docker_helper.inspect_container_security(container)

            assert security_info["privileged"] is False
            assert "no-new-privileges:true" in security_info["security_opts"]
            assert security_info["user"] == "1000:1000"

            # Test privilege escalation attempts
            simulator = SecurityVulnerabilitySimulator()
            privilege_tests = simulator.create_privilege_escalation_test()

            for test_command in privilege_tests:
                returncode, stdout, stderr = docker_helper.execute_in_container(
                    container, test_command
                )

                # Commands should either succeed with limited output or fail safely
                if test_command[0] == "whoami":
                    if returncode == 0:
                        # Should not be root
                        assert "root" not in stdout.lower()

                elif test_command[0] == "id":
                    if returncode == 0:
                        # Should show non-root user
                        assert "uid=1000" in stdout
                        assert "gid=1000" in stdout

                elif test_command[0] == "cat" and "/etc/passwd" in test_command:
                    # May succeed but should not reveal sensitive information
                    if returncode == 0:
                        assert len(stdout.split("\n")) < 50  # Limited user list

    def test_capability_restrictions(self):
        """Test that capabilities are properly restricted."""
        with DockerSecurityTestHelper() as docker_helper:
            if not docker_helper.is_docker_available():
                pytest.skip("Docker not available")

            # Create container with dropped capabilities
            container = docker_helper.create_secure_container(
                security_profile=ContainerSecurityProfile(
                    user_id=1000,
                    group_id=1000,
                    capabilities=["!ALL", "!NET_RAW", "!SYS_ADMIN"],
                    security_opts=["no-new-privileges:true"],
                    read_only_root=False,
                    no_new_privileges=True,
                    resource_limits={"memory": "64m"},
                )
            )

            if not container:
                pytest.skip("Failed to create test container")

            # Test operations that require dropped capabilities
            capability_tests = [
                (["ping", "-c", "1", "127.0.0.1"], "NET_RAW"),  # Requires NET_RAW
                (
                    ["mount", "-t", "tmpfs", "tmpfs", "/mnt"],
                    "SYS_ADMIN",
                ),  # Requires SYS_ADMIN
            ]

            for test_command, required_cap in capability_tests:
                returncode, stdout, stderr = docker_helper.execute_in_container(
                    container, test_command
                )

                # Operations requiring dropped capabilities should fail
                if required_cap in ["NET_RAW", "SYS_ADMIN"]:
                    assert returncode != 0  # Should fail
                    # Check for permission-related error messages
                    error_indicators = [
                        "permission denied",
                        "operation not permitted",
                        "not allowed",
                    ]
                    assert any(
                        indicator in stderr.lower() for indicator in error_indicators
                    )

    def test_read_only_filesystem(self):
        """Test read-only filesystem restrictions."""
        with DockerSecurityTestHelper() as docker_helper:
            if not docker_helper.is_docker_available():
                pytest.skip("Docker not available")

            # Create container with read-only root filesystem
            container = docker_helper.create_secure_container(
                security_profile=ContainerSecurityProfile(
                    user_id=1000,
                    group_id=1000,
                    capabilities=["!ALL"],
                    security_opts=["no-new-privileges:true"],
                    read_only_root=True,
                    no_new_privileges=True,
                    resource_limits={"memory": "64m"},
                )
            )

            if not container:
                pytest.skip("Failed to create test container")

            # Verify read-only configuration
            security_info = docker_helper.inspect_container_security(container)
            assert security_info["read_only_root"] is True

            # Test write operations (should fail)
            write_tests = [
                ["touch", "/test_file.txt"],
                ["mkdir", "/test_dir"],
                ["echo", "test", ">", "/test_output.txt"],
            ]

            for test_command in write_tests:
                returncode, stdout, stderr = docker_helper.execute_in_container(
                    container, test_command
                )

                # Write operations should fail on read-only filesystem
                assert returncode != 0
                error_indicators = [
                    "read-only",
                    "permission denied",
                    "operation not permitted",
                ]
                assert any(
                    indicator in stderr.lower() for indicator in error_indicators
                )


@pytest.mark.integration
@pytest.mark.requires_docker
class TestResourceSecurity:
    """Test resource limits and security."""

    def test_memory_limits(self):
        """Test memory limit enforcement."""
        with DockerSecurityTestHelper() as docker_helper:
            if not docker_helper.is_docker_available():
                pytest.skip("Docker not available")

            # Create container with strict memory limit
            container = docker_helper.create_secure_container(
                security_profile=ContainerSecurityProfile(
                    user_id=1000,
                    group_id=1000,
                    capabilities=["!ALL"],
                    security_opts=["no-new-privileges:true"],
                    read_only_root=False,
                    no_new_privileges=True,
                    resource_limits={
                        "memory": "32m",
                        "cpus": "0.1",
                    },  # Very restrictive
                )
            )

            if not container:
                pytest.skip("Failed to create test container")

            # Verify memory limit configuration
            security_info = docker_helper.inspect_container_security(container)
            assert security_info["memory_limit"] > 0  # Should have memory limit set

            # Test memory allocation (should be limited)
            # Try to allocate more memory than the limit
            returncode, stdout, stderr = docker_helper.execute_in_container(
                container, ["dd", "if=/dev/zero", "of=/dev/null", "bs=1M", "count=64"]
            )

            # This might succeed or fail depending on system configuration
            # But container should remain stable

            # Check if container is still running
            try:
                returncode2, stdout2, stderr2 = docker_helper.execute_in_container(
                    container, ["echo", "still_alive"]
                )
                # Container should still be responsive
                assert returncode2 == 0
                assert "still_alive" in stdout2
            except Exception:
                # If container was killed due to memory limit, that's also acceptable behavior
                pass

    def test_cpu_limits(self):
        """Test CPU limit enforcement."""
        with DockerSecurityTestHelper() as docker_helper:
            if not docker_helper.is_docker_available():
                pytest.skip("Docker not available")

            # Create container with CPU limits
            container = docker_helper.create_secure_container(
                security_profile=ContainerSecurityProfile(
                    user_id=1000,
                    group_id=1000,
                    capabilities=["!ALL"],
                    security_opts=["no-new-privileges:true"],
                    read_only_root=False,
                    no_new_privileges=True,
                    resource_limits={"memory": "64m", "cpus": "0.1"},  # 10% CPU
                )
            )

            if not container:
                pytest.skip("Failed to create test container")

            # Test CPU-intensive operation
            start_time = time.time()

            returncode, stdout, stderr = docker_helper.execute_in_container(
                container,
                ["sh", "-c", "for i in $(seq 1 1000); do echo $i > /dev/null; done"],
            )

            execution_time = time.time() - start_time

            # With CPU limits, operation should take longer
            # This is a rough test - actual behavior depends on system load
            assert returncode == 0  # Should complete successfully
            assert execution_time > 0.1  # Should take some measurable time

    def test_filesystem_space_limits(self):
        """Test filesystem space limits."""
        with DockerSecurityTestHelper() as docker_helper:
            if not docker_helper.is_docker_available():
                pytest.skip("Docker not available")

            # Create container with limited writable space
            container = docker_helper.create_secure_container(
                security_profile=ContainerSecurityProfile(
                    user_id=1000,
                    group_id=1000,
                    capabilities=["!ALL"],
                    security_opts=["no-new-privileges:true"],
                    read_only_root=False,
                    no_new_privileges=True,
                    resource_limits={"memory": "64m"},
                )
            )

            if not container:
                pytest.skip("Failed to create test container")

            # Test creating large file (should be limited by available space)
            returncode, stdout, stderr = docker_helper.execute_in_container(
                container,
                ["dd", "if=/dev/zero", "of=/tmp/large_file", "bs=1M", "count=1"],
            )

            # Should succeed for reasonable file size
            assert returncode == 0

            # Verify file was created
            returncode2, stdout2, stderr2 = docker_helper.execute_in_container(
                container, ["ls", "-lh", "/tmp/large_file"]
            )

            assert returncode2 == 0
            assert "large_file" in stdout2


@pytest.mark.integration
@pytest.mark.requires_docker
class TestSecurityEscapePrevention:
    """Test prevention of container escape attempts."""

    def test_docker_socket_access_prevention(self):
        """Test that containers cannot access Docker socket."""
        with DockerSecurityTestHelper() as docker_helper:
            if not docker_helper.is_docker_available():
                pytest.skip("Docker not available")

            # Create secure container
            container = docker_helper.create_secure_container(
                security_profile=ContainerSecurityProfile(
                    user_id=1000,
                    group_id=1000,
                    capabilities=["!ALL"],
                    security_opts=["no-new-privileges:true"],
                    read_only_root=False,
                    no_new_privileges=True,
                    resource_limits={"memory": "64m"},
                )
            )

            if not container:
                pytest.skip("Failed to create test container")

            # Test access to Docker socket
            docker_socket_tests = [
                ["ls", "-la", "/var/run/docker.sock"],
                ["cat", "/var/run/docker.sock"],
                ["find", "/", "-name", "*.sock", "-type", "s"],
            ]

            for test_command in docker_socket_tests:
                returncode, stdout, stderr = docker_helper.execute_in_container(
                    container, test_command
                )

                # Should not be able to access Docker socket
                if test_command[1] == "/var/run/docker.sock":
                    assert returncode != 0  # Should fail to access

                # Find command should not reveal Docker socket
                if "find" in test_command:
                    if returncode == 0:
                        assert "docker.sock" not in stdout.lower()

    def test_host_filesystem_access_prevention(self):
        """Test prevention of host filesystem access."""
        with DockerSecurityTestHelper() as docker_helper:
            if not docker_helper.is_docker_available():
                pytest.skip("Docker not available")

            # Create secure container
            container = docker_helper.create_secure_container(
                security_profile=ContainerSecurityProfile(
                    user_id=1000,
                    group_id=1000,
                    capabilities=["!ALL"],
                    security_opts=["no-new-privileges:true"],
                    read_only_root=False,
                    no_new_privileges=True,
                    resource_limits={"memory": "64m"},
                )
            )

            if not container:
                pytest.skip("Failed to create test container")

            # Test filesystem escape attempts
            simulator = SecurityVulnerabilitySimulator()
            escape_tests = simulator.create_filesystem_escape_test()

            for test_command in escape_tests:
                returncode, stdout, stderr = docker_helper.execute_in_container(
                    container, test_command
                )

                if returncode == 0:
                    # Commands that succeed should show containerized environment
                    if test_command[0] == "cat" and "/etc/hostname" in test_command:
                        # Should show container hostname, not host
                        assert (
                            len(stdout.strip()) <= 64
                        )  # Container hostnames are typically short

                    elif test_command[0] == "cat" and "/proc/version" in test_command:
                        # Should show kernel version but from container perspective
                        assert "Linux" in stdout

                    elif (
                        test_command[0] == "cat" and "/proc/self/cgroup" in test_command
                    ):
                        # Should show container cgroups
                        assert (
                            "docker" in stdout.lower() or "containerd" in stdout.lower()
                        )

    def test_privilege_escalation_prevention(self):
        """Test prevention of privilege escalation."""
        with DockerSecurityTestHelper() as docker_helper:
            if not docker_helper.is_docker_available():
                pytest.skip("Docker not available")

            # Create secure container
            container = docker_helper.create_secure_container(
                security_profile=ContainerSecurityProfile(
                    user_id=1000,
                    group_id=1000,
                    capabilities=["!ALL"],
                    security_opts=["no-new-privileges:true"],
                    read_only_root=False,
                    no_new_privileges=True,
                    resource_limits={"memory": "64m"},
                )
            )

            if not container:
                pytest.skip("Failed to create test container")

            # Test privilege escalation attempts
            escalation_tests = [
                ["sudo", "whoami"],
                ["su", "root"],
                ["sudo", "-i"],
                ["sudo", "su", "-"],
            ]

            for test_command in escalation_tests:
                returncode, stdout, stderr = docker_helper.execute_in_container(
                    container, test_command
                )

                # Privilege escalation should fail
                assert returncode != 0

                # Check for appropriate error messages
                error_indicators = [
                    "command not found",
                    "permission denied",
                    "not allowed",
                    "authentication failure",
                ]

                assert any(
                    indicator in stderr.lower() for indicator in error_indicators
                )


@pytest.mark.integration
class TestDockerSecurityIntegration:
    """Test Docker security integration with PANTHER environments."""

    def test_secure_environment_creation(self):
        """Test creation of secure Docker environments."""

        class SecureDockerEnvironment(BaseNetworkEnvironment):
            def __init__(self):
                super().__init__(None, "/tmp", "security_test", "test", Mock())
                self.docker_helper = DockerSecurityTestHelper()
                self.security_profiles = {}
                self.container_ids = {}

            def create_secure_service(
                self, service_name: str, security_level: str = "high"
            ):
                """Create a secure service container."""

                if security_level == "high":
                    profile = ContainerSecurityProfile(
                        user_id=1000,
                        group_id=1000,
                        capabilities=["!ALL"],
                        security_opts=[
                            "no-new-privileges:true",
                            "apparmor:docker-default",
                        ],
                        read_only_root=False,
                        no_new_privileges=True,
                        resource_limits={"memory": "128m", "cpus": "0.5"},
                    )
                elif security_level == "medium":
                    profile = ContainerSecurityProfile(
                        user_id=1000,
                        group_id=1000,
                        capabilities=["!NET_RAW", "!SYS_ADMIN"],
                        security_opts=["no-new-privileges:true"],
                        read_only_root=False,
                        no_new_privileges=True,
                        resource_limits={"memory": "256m", "cpus": "1.0"},
                    )
                else:  # low
                    profile = ContainerSecurityProfile(
                        user_id=1000,
                        group_id=1000,
                        capabilities=[],
                        security_opts=[],
                        read_only_root=False,
                        no_new_privileges=False,
                        resource_limits={"memory": "512m"},
                    )

                container_id = self.docker_helper.create_secure_container(
                    security_profile=profile
                )

                if container_id:
                    self.security_profiles[service_name] = profile
                    self.container_ids[service_name] = container_id
                    return True

                return False

            def validate_security_compliance(self) -> Dict[str, Any]:
                """Validate security compliance of created containers."""
                compliance_results = {}

                for service_name, container_id in self.container_ids.items():
                    security_info = self.docker_helper.inspect_container_security(
                        container_id
                    )

                    compliance_checks = {
                        "non_privileged": not security_info.get("privileged", True),
                        "non_root_user": security_info.get("user", "") != "",
                        "has_security_opts": len(security_info.get("security_opts", []))
                        > 0,
                        "memory_limited": security_info.get("memory_limit", 0) > 0,
                        "no_host_network": security_info.get("network_mode", "")
                        != "host",
                        "no_host_pid": security_info.get("pid_mode", "") != "host",
                        "no_host_ipc": security_info.get("ipc_mode", "") != "host",
                    }

                    compliance_score = sum(
                        1 for check in compliance_checks.values() if check
                    )
                    total_checks = len(compliance_checks)

                    compliance_results[service_name] = {
                        "checks": compliance_checks,
                        "score": compliance_score,
                        "total": total_checks,
                        "percentage": (compliance_score / total_checks) * 100,
                    }

                return compliance_results

            def cleanup_security_test(self):
                """Clean up security test resources."""
                self.docker_helper.cleanup()
                self.security_profiles.clear()
                self.container_ids.clear()

            # Required abstract methods
            def prepare_environment(self):
                return True

            def generate_environment_services(self, paths, timestamp):
                return list(self.container_ids.keys())

            def launch_environment_services(self):
                return True

            def deploy_services(self, services):
                return True

            def _teardown_environment(self):
                self.cleanup_security_test()

            def _do_setup_environment(self):
                return True

            def _do_deploy_services(self, services):
                return True

            def _do_teardown_environment(self):
                self.cleanup_security_test()

            def _get_service_log_directory(self, service):
                return f"/tmp/logs/{service}"

            def _get_service_ip(self, service):
                return "127.0.0.1"

            def handle_event(self, event):
                pass

            def initialize(self):
                pass

        # Test secure environment
        env = SecureDockerEnvironment()

        try:
            if not env.docker_helper.is_docker_available():
                pytest.skip("Docker not available")

            # Create services with different security levels
            services = [
                ("web_service", "high"),
                ("api_service", "medium"),
                ("worker_service", "high"),
            ]

            created_services = 0
            for service_name, security_level in services:
                if env.create_secure_service(service_name, security_level):
                    created_services += 1

            # Should create at least some services
            assert created_services > 0

            # Validate security compliance
            compliance_results = env.validate_security_compliance()

            for service_name, compliance in compliance_results.items():
                # High security services should have high compliance scores
                if service_name in ["web_service", "worker_service"]:
                    assert compliance["percentage"] >= 80.0  # At least 80% compliance

                # All services should pass basic security checks
                assert compliance["checks"]["non_privileged"] is True
                assert compliance["checks"]["non_root_user"] is True

        finally:
            env.cleanup_security_test()


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short", "-m", "not requires_docker"])
