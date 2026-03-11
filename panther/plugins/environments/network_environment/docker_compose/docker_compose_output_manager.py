"""Docker Compose Output Management Module for PANTHER framework.

This module provides output management functionality for Docker Compose environments,
including certificate setup, file collection, and output registration.
"""

import logging
import shlex
import subprocess
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from panther.core.outputs.output_environment_mixins import StandardOutputCollectorMixin
from panther.plugins.environments.network_environment.mixins import (
    SubprocessExecutorMixin,
)
from panther.plugins.services.services_interface import IServiceManager


class DockerComposeOutputManager:
    """Manages output operations for Docker Compose environments.

    This class handles:
    - Certificate generation and setup
    - Container output collection
    - Output file registration
    - Disk space validation
    """

    def __init__(
        self,
        output_dir: Path,
        logger: Optional[logging.Logger] = None,
        docker_executor: Optional[SubprocessExecutorMixin] = None,
        output_collector: Optional[StandardOutputCollectorMixin] = None,
    ):
        """Initialize the output manager.

        Args:
            output_dir: Base output directory for all file operations
            logger: Logger instance for output operations
            docker_executor: Docker command executor for container operations
            output_collector: Output collection mixin for registration
        """
        self.output_dir = (
            Path(output_dir) if not isinstance(output_dir, Path) else output_dir
        )
        self.logger = logger or logging.getLogger(self.__class__.__name__)
        self.docker_executor = docker_executor
        self.output_collector = output_collector

    def setup_certificates(self, services_managers: List[IServiceManager]) -> None:
        """Setup certificates for services that require them."""
        # Check if any service needs certificate generation
        needs_certificates = any(
            hasattr(service, "service_config_to_test")
            and service.service_config_to_test.generate_new_certificates
            for service in services_managers
        )

        if not needs_certificates:
            self.logger.debug("No services require certificate generation")
            return

        # Create certificate directory in output directory
        cert_dir = self.output_dir / "certs"
        cert_dir.mkdir(exist_ok=True)

        cert_file = cert_dir / "cert.pem"
        key_file = cert_dir / "key.pem"

        # Generate certificates if they don't exist
        if not cert_file.exists() or not key_file.exists():
            self.logger.info("Generating self-signed certificates for services")

            # Use the certificate generation utility
            from panther.core.command_processor.utils import CommandUtils

            cert_gen_cmd = CommandUtils.create_certificate_generation_command(
                cert_dir=str(cert_dir),
                cert_name="cert",
                key_name="key",
                common_name="panther.local",
                days=365,
            )

            try:
                # Execute certificate generation command with safer approach
                # Use shlex.split to safely parse the command and avoid shell=True
                cmd_parts = shlex.split(cert_gen_cmd)
                result = subprocess.run(
                    cmd_parts,
                    shell=False,  # Explicitly set shell=False for security
                    capture_output=True,
                    text=True,
                    timeout=30,
                    check=False,  # Handle errors explicitly
                )

                if result.returncode == 0:
                    self.logger.info(f"Generated certificates in {cert_dir}")
                    self.logger.debug(f"Certificate: {cert_file}")
                    self.logger.debug(f"Private key: {key_file}")
                else:
                    self.logger.error(
                        f"Failed to generate certificates: {result.stderr}"
                    )
                    raise RuntimeError(
                        f"Certificate generation failed: {result.stderr}"
                    )

            except subprocess.TimeoutExpired:
                self.logger.error("Certificate generation timed out")
                raise RuntimeError("Certificate generation timed out")
            except Exception as e:
                self.logger.error(f"Error generating certificates: {e}")
                raise RuntimeError(f"Certificate generation error: {e}")
        else:
            self.logger.info(f"Using existing certificates in {cert_dir}")

    def copy_container_outputs_to_host(
        self, services_managers: List[IServiceManager]
    ) -> None:
        """Copy outputs from containers to host filesystem.

        Args:
            services_managers: List of service managers to process
        """
        if not self.docker_executor:
            self.logger.warning("No docker executor available for output collection")
            return

        self.logger.info("Starting container output collection")

        for service in services_managers:
            service_name = service.service_name
            self.logger.debug(f"Processing outputs for service: {service_name}")

            # Check if container exists and is accessible
            try:
                result = self.docker_executor.execute_docker_command(
                    docker_args=[
                        "ps",
                        "-a",
                        "--filter",
                        f"name={service_name}",
                        "--format",
                        "{{.Names}}",
                    ],
                    check=False,
                )
                container_check = (
                    result.stdout if hasattr(result, "stdout") else str(result)
                )
                if not container_check or service_name not in container_check:
                    self.logger.warning(
                        f"Container {service_name} not found, skipping output collection"
                    )
                    continue
            except Exception as e:
                self.logger.warning(f"Failed to check container {service_name}: {e}")
                continue

            # Check if container is running (optional - we can copy from stopped containers too)
            try:
                result = self.docker_executor.execute_docker_command(
                    docker_args=[
                        "ps",
                        "--filter",
                        f"name={service_name}",
                        "--format",
                        "{{.Names}}",
                    ],
                    check=False,
                )
                running_check = (
                    result.stdout if hasattr(result, "stdout") else str(result)
                )
                is_running = service_name in (running_check or "")
                self.logger.debug(f"Container {service_name} running: {is_running}")
            except Exception as e:
                self.logger.debug(f"Could not check if {service_name} is running: {e}")

            # Create service output directory
            service_output_dir = self.output_dir / "logs" / service_name
            service_output_dir.mkdir(parents=True, exist_ok=True)

            # Define common output paths to check in containers
            container_paths = [
                "/opt/logs",
                "/var/log",
                "/app/logs",
                "/tmp",
                "/opt/output",
                "/output",
            ]

            # Try to copy outputs from each potential path
            for container_path in container_paths:
                try:
                    # Check if path exists in container
                    result = self.docker_executor.execute_docker_command(
                        docker_args=["exec", service_name, "ls", "-la", container_path],
                        check=False,
                    )
                    ls_result = (
                        result.stdout if hasattr(result, "stdout") else str(result)
                    )

                    if (
                        not ls_result
                        or "No such file" in ls_result
                        or result.returncode != 0
                    ):
                        continue

                    # List files in the container path
                    result = self.docker_executor.execute_docker_command(
                        docker_args=[
                            "exec",
                            service_name,
                            "find",
                            container_path,
                            "-type",
                            "f",
                            "-name",
                            "*.log",
                            "-o",
                            "-name",
                            "*.pcap",
                            "-o",
                            "-name",
                            "*.json",
                            "-o",
                            "-name",
                            "*.txt",
                            "-o",
                            "-name",
                            "*.out",
                            "-o",
                            "-name",
                            "*.err",
                        ],
                        check=False,
                    )
                    files_result = (
                        result.stdout if hasattr(result, "stdout") else str(result)
                    )

                    if not files_result or result.returncode != 0:
                        continue

                    # Copy each file found
                    files = [f.strip() for f in files_result.split("\n") if f.strip()]
                    for file_path in files[:20]:  # Limit to prevent overwhelming
                        if file_path and file_path != "No files found":
                            try:
                                # Create relative path for host destination
                                rel_path = file_path.replace(container_path, "").lstrip(
                                    "/"
                                )
                                if not rel_path:
                                    rel_path = Path(file_path).name

                                host_dest = service_output_dir / rel_path
                                host_dest.parent.mkdir(parents=True, exist_ok=True)

                                # Copy file from container to host
                                copy_result = (
                                    self.docker_executor.execute_docker_command(
                                        docker_args=[
                                            "cp",
                                            f"{service_name}:{file_path}",
                                            str(host_dest),
                                        ],
                                        check=False,
                                    )
                                )

                                if host_dest.exists():
                                    self.logger.debug(
                                        f"Copied {file_path} to {host_dest}"
                                    )
                                else:
                                    self.logger.warning(f"Failed to copy {file_path}")

                            except Exception as e:
                                self.logger.debug(
                                    f"Error copying file {file_path}: {e}"
                                )
                                continue

                except Exception as e:
                    self.logger.debug(
                        f"Error processing path {container_path} in {service_name}: {e}"
                    )
                    continue

            # Also try to get container inspection and logs
            try:
                # Get container logs
                logs_result = self.docker_executor.execute_docker_command(
                    docker_args=["logs", service_name], timeout=10, check=False
                )
                if (
                    logs_result
                    and hasattr(logs_result, "stdout")
                    and logs_result.stdout
                ):
                    logs_file = service_output_dir / f"{service_name}.log"
                    logs_file.write_text(logs_result.stdout)
                    self.logger.debug(f"Saved container logs to {logs_file}")

                # Get container inspection
                inspect_result = self.docker_executor.execute_docker_command(
                    docker_args=["inspect", service_name], check=False
                )
                if (
                    inspect_result
                    and hasattr(inspect_result, "stdout")
                    and inspect_result.stdout
                ):
                    inspect_file = service_output_dir / f"{service_name}_inspect.json"
                    inspect_file.write_text(inspect_result.stdout)
                    self.logger.debug(f"Saved container inspection to {inspect_file}")

            except Exception as e:
                self.logger.debug(
                    f"Error getting container info for {service_name}: {e}"
                )

        self.logger.info("Container output collection completed")

    def perform_final_output_registration(
        self, services_managers: List[IServiceManager]
    ) -> None:
        """Perform final output registration with the output collection system.

        Args:
            services_managers: List of service managers to register outputs for
        """
        if not self.output_collector:
            self.logger.warning("No output collector available for registration")
            return

        self.logger.info("Starting final output registration")

        # Copy container outputs to host first
        self.copy_container_outputs_to_host(services_managers)

        # Wait a moment for file operations to complete
        time.sleep(2)

        # Register outputs for all services using the correct interface
        try:
            # Use the output collector's registration method with correct signature
            if hasattr(self.output_collector, "register_service_outputs"):
                self.output_collector.register_service_outputs(
                    services_managers,
                    lambda service_name: self.get_service_log_directory(service_name),
                )
                self.logger.debug(f"Registered outputs for all services")
            else:
                self.logger.warning(
                    "Output collector does not have register_service_outputs method"
                )
        except Exception as e:
            self.logger.warning(f"Failed to register service outputs: {e}")

        # Log actual output files discovered
        self.log_actual_output_files()

        self.logger.info("Final output registration completed")

    def log_actual_output_files(self) -> None:
        """Log details of actual output files discovered."""
        self.logger.info("Discovering actual output files")

        logs_dir = self.output_dir / "logs"
        if not logs_dir.exists():
            self.logger.info("No logs directory found")
            return

        total_files = 0
        total_size = 0

        for service_dir in logs_dir.iterdir():
            if service_dir.is_dir():
                service_files = list(service_dir.glob("**/*"))
                service_file_count = len([f for f in service_files if f.is_file()])

                if service_file_count > 0:
                    service_size = sum(
                        f.stat().st_size for f in service_files if f.is_file()
                    )
                    self.logger.info(
                        f"Service {service_dir.name}: {service_file_count} files, "
                        f"{service_size / 1024 / 1024:.2f} MB"
                    )
                    total_files += service_file_count
                    total_size += service_size

        if total_files > 0:
            self.logger.info(
                f"Total output: {total_files} files, {total_size / 1024 / 1024:.2f} MB"
            )
        else:
            self.logger.info("No output files discovered")

    def get_service_log_directory(self, service_name: str) -> Path:
        """Get the log directory path for a specific service."""
        return self.output_dir / "logs" / service_name

    def check_disk_space(self, required_gb: float = 2.0) -> None:
        """Check available disk space before operations.

        Args:
            required_gb: Minimum required disk space in GB

        Raises:
            RuntimeError: If insufficient disk space available
        """
        try:
            import shutil

            # Check available space
            total, used, free = shutil.disk_usage(self.output_dir)
            free_gb = free / (1024**3)  # Convert to GB

            self.logger.debug(f"Available disk space: {free_gb:.2f} GB")

            if free_gb < required_gb:
                raise RuntimeError(
                    f"Insufficient disk space. Required: {required_gb} GB, "
                    f"Available: {free_gb:.2f} GB"
                )

            self.logger.debug(f"Disk space check passed: {free_gb:.2f} GB available")

        except Exception as e:
            self.logger.warning(f"Could not check disk space: {e}")
            # Don't fail the entire operation for disk space check issues
