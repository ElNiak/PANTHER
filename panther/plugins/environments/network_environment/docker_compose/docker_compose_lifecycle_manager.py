"""Docker Compose Lifecycle Management Module for PANTHER framework.

This module provides lifecycle management functionality for Docker Compose environments,
including service deployment, monitoring, and cleanup operations.
"""

import logging
import os
import subprocess
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from panther.plugins.environments.network_environment.mixins import (
    StatusMonitorMixin,
    SubprocessExecutorMixin,
)
from panther.plugins.environments.network_environment.utils import (
    NetworkEnvironmentUtils,
)
from panther.plugins.services.services_interface import IServiceManager


class DockerComposeLifecycleManager:
    """Manages the complete lifecycle of Docker Compose services.

    This class handles:
    - Service deployment and startup
    - Health monitoring and readiness checks
    - Background monitoring processes
    - Service teardown and cleanup
    """

    def __init__(
        self,
        services_managers: List[IServiceManager],
        network_name: str,
        config_file_path: Path,
        output_dir: Path,
        timeout: int,
        docker_executor: Optional[SubprocessExecutorMixin] = None,
        status_monitor: Optional[StatusMonitorMixin] = None,
        port_manager: Optional[Any] = None,
        output_manager: Optional[Any] = None,
        logger: Optional[logging.Logger] = None,
    ):
        """Initialize the lifecycle manager.

        Args:
            services_managers: List of service managers to manage
            network_name: Docker network name for service communication
            config_file_path: Path to Docker Compose configuration file
            output_dir: Base output directory for logs and files
            timeout: Timeout for service operations in seconds
            docker_executor: Docker command executor for container operations
            status_monitor: Status monitoring mixin for health checks
            port_manager: Port management for cleanup verification
            output_manager: Output management for service registration
            logger: Logger instance for lifecycle operations
        """
        self.services_managers = services_managers
        self.network_name = network_name
        self.config_file_path = config_file_path
        self.output_dir = output_dir
        self.timeout = timeout
        self.docker_executor = docker_executor
        self.status_monitor = status_monitor
        self.port_manager = port_manager
        self.output_manager = output_manager
        self.logger = logger or logging.getLogger(self.__class__.__name__)

        # Background monitoring state
        self.background_monitor = None

    def extract_service_environment_variables(self) -> Dict[str, Any]:
        """Extract and process environment variables from all service managers.

        Returns:
            Dictionary of environment variables processed from all services
        """
        self.logger.debug("Extracting environment variables from all services")

        all_env_vars = {}

        # First, collect all raw environment variables that need to be resolved
        raw_env_vars = {}

        for service in self.services_managers:
            service_name = service.service_name
            # Get environment variables from service.environments (set by _load_version_environment_variables)
            raw_env_vars = self.collect_service_environment_variables(
                raw_env_vars, service, service_name
            )

        # Now resolve variable references in the collected environment variables
        # This handles cases like IVY_DIR=$SOURCE_DIR/panther_ivy
        resolved_env_vars = self._resolve_environment_variables(raw_env_vars)

        # Add to final environment variables
        all_env_vars |= resolved_env_vars

        # Add common environment variables
        all_env_vars.update(
            {
                "COMPOSE_PROJECT_NAME": self.network_name,
                "COMPOSE_FILE": str(self.config_file_path),
                "OUTPUT_DIR": str(self.output_dir),
                # Add UID and GID for Docker user mapping
                "UID": str(os.getuid()) if hasattr(os, "getuid") else "0",
                "GID": str(os.getgid()) if hasattr(os, "getgid") else "0",
            }
        )
        self.logger.info(
            f"Extracted and resolved {len(all_env_vars)} total environment variables"
        )
        return all_env_vars

    def collect_service_environment_variables(
        self, raw_env_vars, service, service_name
    ):
        # CRITICAL: Call adapt_environment_paths before collecting variables
        # This ensures template variables like IS_APT_PATH are properly set
        if hasattr(service, "adapt_environment_paths"):
            # Determine architecture mode from service configuration
            use_system_models = self._determine_architecture_mode(service)
            self.logger.debug(
                f"Calling adapt_environment_paths for {service_name} with use_system_models={use_system_models}"
            )

            # Get current environment variables to pass to adaptation
            service_env_vars = {}
            if hasattr(service, "environments") and service.environments:
                service_env_vars.update(service.environments)
            elif (
                hasattr(service, "environment_variables")
                and service.environment_variables
            ):
                service_env_vars.update(service.environment_variables)

            # Call the service's path adaptation method
            try:
                service.adapt_environment_paths(service_env_vars, use_system_models)
                self.logger.debug(
                    f"Successfully adapted environment paths for {service_name}"
                )

                # Update the service's environment variables with adapted values
                if hasattr(service, "environments"):
                    service.environments.update(service_env_vars)
                elif hasattr(service, "environment_variables"):
                    service.environment_variables.update(service_env_vars)

            except Exception as e:
                self.logger.warning(
                    f"Failed to adapt environment paths for {service_name}: {e}"
                )

        # Now collect the environment variables (potentially adapted)
        if hasattr(service, "environments") and service.environments:
            service_env = service.environments
            self.logger.debug(
                f"Service {service_name} has {len(service_env)} environment variables from environments"
            )
            # Collect all environment variables from this service
            for key, value in service_env.items():
                # Convert all values to strings (subprocess requires string env vars)
                raw_env_vars[key] = str(value)
                self.logger.debug(
                    f"Collected env var {key}={value} from service {service_name}"
                )

            # Also check for environment_variables attribute (legacy support)
        elif (
            hasattr(service, "environment_variables") and service.environment_variables
        ):
            service_env = service.environment_variables
            self.logger.debug(
                f"Service {service_name} has {len(service_env)} environment variables from environment_variables"
            )

            for key, value in service_env.items():
                # Convert all values to strings (subprocess requires string env vars)
                raw_env_vars[key] = str(value)

        else:
            self.logger.debug(f"Service {service_name} has no environment variables")
        return raw_env_vars

    def _determine_architecture_mode(self, service) -> bool:
        """
        Determine whether to use system models (APT architecture) based on service configuration.

        Args:
            service: Service manager instance

        Returns:
            bool: True for APT architecture, False for individual protocol architecture
        """
        # Check if service has explicit configuration for architecture mode
        if hasattr(service, "use_system_models"):
            return service.use_system_models

        # Check service configuration for APT indicators
        if hasattr(service, "service_config_to_test"):
            config = service.service_config_to_test

            # Look for APT-related configuration keys
            if hasattr(config, "use_apt_protocols") and config.use_apt_protocols:
                return True
            if hasattr(config, "protocol_path") and "apt/apt_protocols" in str(
                config.protocol_path
            ):
                return True

        # Check environment variables for APT indicators
        env_vars = {}
        if hasattr(service, "environments") and service.environments:
            env_vars = service.environments
        elif (
            hasattr(service, "environment_variables") and service.environment_variables
        ):
            env_vars = service.environment_variables

        # Look for APT path indicators in environment
        for key, value in env_vars.items():
            if isinstance(value, str):
                if "apt/apt_protocols" in value or "apt_protocols" in value:
                    return True

        # Default to individual protocol architecture (non-APT)
        self.logger.debug(
            f"No APT indicators found for {service.service_name}, using individual protocol architecture"
        )
        return False

    def _resolve_environment_variables(
        self, env_vars: Dict[str, str]
    ) -> Dict[str, str]:
        """Resolve variable references in environment variables.

        Args:
            env_vars: Dictionary of environment variables with potential references

        Returns:
            Dictionary with resolved environment variables
        """
        resolved = {}
        max_iterations = 10  # Prevent infinite loops

        # Start with a copy of the input
        working_vars = env_vars.copy()

        # Add some base variables that don't have references - these are defaults
        base_vars = {
            "SOURCE_DIR": "/opt",
            "ROOTPATH": "/opt",
            "MODEL_TYPE": "protocol",
            # TODO: This version should be resolved dynamically rather than hardcoded
            "PYTHON_IVY_DIR": "/root/.pyenv/versions/3.10.12/lib/python3.10/site-packages/panther_ms_ivy-1.10.0-py3.10-linux-x86_64.egg/ivy/",
        }

        # Update working vars with base values if not already set
        for key, value in base_vars.items():
            if key not in working_vars:
                working_vars[key] = value

        # Handle self-referencing variables by replacing them with defaults
        for key, value in working_vars.items():
            if isinstance(value, str) and value in [f"${key}", f"${{{key}}}"]:
                if key in base_vars:
                    working_vars[key] = base_vars[key]
                    self.logger.debug(
                        f"Resolved self-referencing variable {key}: {value} -> {base_vars[key]}"
                    )

        # Resolve standard variables iteratively
        for iteration in range(max_iterations):
            changed = False

            for key, value in working_vars.items():
                if isinstance(value, str) and "$" in value:
                    # Skip Docker-specific variables that should be preserved
                    if (
                        value in ["${UID}", "${GID}"]
                        or value.startswith("$LD_LIBRARY_PATH:")
                        or value.startswith("$IVY_INCLUDE_PATH:")
                        or value.startswith("$PATH:")
                        or value.startswith("$PYTHONPATH:")
                    ):
                        continue

                    # Try to resolve variable references
                    new_value = value

                    # Replace known variables using both working_vars and base_vars
                    all_vars = {**base_vars, **working_vars}
                    for var_name, var_value in all_vars.items():
                        if isinstance(var_value, str) and "$" not in var_value:
                            # Only use resolved values for substitution
                            new_value = new_value.replace(f"${var_name}", var_value)
                            new_value = new_value.replace(f"${{{var_name}}}", var_value)

                    if new_value != value:
                        working_vars[key] = new_value
                        changed = True
                        self.logger.debug(f"Resolved {key}: {value} -> {new_value}")

            if not changed:
                # No more changes, we're done
                break

        # Copy all resolved variables to output
        resolved |= working_vars

        # Log any remaining unresolved variables (except special cases)
        unresolved_count = 0
        for key, value in resolved.items():
            if isinstance(value, str) and "$" in value:
                # Check if it's a special case that should be preserved
                if (
                    value.startswith("$LD_LIBRARY_PATH:")
                    or value.startswith("$IVY_INCLUDE_PATH:")
                    or value.startswith("$PYTHONPATH:")
                    or value.startswith("$PATH:")
                    or value in ["${UID}", "${GID}"]
                ):
                    # These are variables that Docker should handle
                    self.logger.debug(
                        f"Preserving Docker/system variable {key}={value}"
                    )
                else:
                    self.logger.warning(
                        f"Could not fully resolve environment variable {key}={value}"
                    )
                    unresolved_count += 1

        if unresolved_count > 0:
            self.logger.warning(
                f"Failed to resolve {unresolved_count} environment variables"
            )
        else:
            self.logger.debug("All environment variables resolved successfully")

        return resolved

    def _pre_launch_cleanup(self) -> None:
        """Clean up stale Docker resources before launching new services.

        Runs ``docker compose down -v --remove-orphans`` to remove leftover
        containers, networks, and volumes from a previous crashed run.  Failures
        are expected when there is nothing to clean up and are logged at debug
        level only.
        """
        self.logger.info("Pre-launch cleanup: removing stale Docker resources")
        try:
            compose_args = [
                "compose",
                "-f",
                str(self.config_file_path),
                "-p",
                self.network_name,
                "down",
                "-v",
                "--remove-orphans",
            ]
            self.docker_executor.execute_docker_command(
                docker_args=compose_args,
                timeout=30,
            )
            self.logger.info("Pre-launch cleanup completed")
        except Exception as e:
            error_str = str(e).lower()
            if "not found" in error_str or "no such" in error_str:
                self.logger.debug("Pre-launch cleanup (no previous run): %s", e)
            else:
                self.logger.warning(
                    "Pre-launch cleanup error (may cause resource conflicts): %s",
                    e,
                )

    def launch_services(self) -> None:
        """Launch Docker Compose services with extracted environment variables."""
        self.logger.info("Launching Docker Compose services")

        if not self.docker_executor:
            raise RuntimeError("Docker executor not available for service launch")

        # Clean up stale resources from any previous crashed run
        self._pre_launch_cleanup()

        # Extract environment variables for the Docker Compose execution
        # Start with current environment to preserve PATH and other system variables
        env_vars = os.environ.copy()
        # Add service-specific environment variables
        service_env_vars = self.extract_service_environment_variables()

        env_vars |= service_env_vars

        compose_args = [
            "docker",
            "compose",
            "-f",
            str(self.config_file_path),
            "up",
            "-d",
        ]
        self.logger.info(f"Docker Compose config file path: {self.config_file_path}")
        self.logger.info(f"Docker Compose args: {compose_args}")
        try:
            self.launch_docker_compose(compose_args, env_vars)
        except Exception as e:
            self.logger.error(f"Error launching Docker Compose services: {e}")
            raise

    def launch_docker_compose(self, compose_args, env_vars):
        # Debug log output_dir
        self.logger.debug(
            f"output_dir type: {type(self.output_dir)}, value: {self.output_dir}"
        )
        # Ensure output_dir is a Path object
        if not isinstance(self.output_dir, Path):
            self.logger.error(
                f"output_dir is not a Path object: {type(self.output_dir)}"
            )
            self.output_dir = Path(str(self.output_dir))

        # Prepare log file paths
        stdout_file = str(self.output_dir / "logs" / "docker_compose_up.stdout.log")
        stderr_file = str(self.output_dir / "logs" / "docker_compose_up.stderr.log")

        self.logger.debug(f"stdout_file: {stdout_file}")
        self.logger.debug(f"stderr_file: {stderr_file}")

        # Build complete command as list

        self.logger.info(f"Executing Docker Compose command: {' '.join(compose_args)}")
        self.logger.info(f"With environment variables: {list(env_vars.keys())}")
        self.logger.info(f"Current working directory: {os.getcwd()}")

        # Start Docker Compose
        self.docker_executor.execute_with_logging(
            command=compose_args,
            stdout_file=stdout_file,
            stderr_file=stderr_file,
            timeout=self.timeout,
            env=env_vars,
        )

    def teardown_services(self) -> None:
        """Tear down Docker Compose services and clean up resources."""
        self.logger.info("Tearing down Docker Compose services")

        if not self.docker_executor:
            self.logger.warning("No docker executor available for teardown")
            return

        try:
            # Stop and remove containers, networks, and volumes
            self.stop_docker_services()

            # Clean up any remaining Docker resources
            try:
                NetworkEnvironmentUtils.cleanup_docker_resources(
                    prefix=self.network_name,
                    remove_volumes=True,
                    remove_networks=True,
                )
                self.logger.info("Docker resources cleaned up")
            except Exception as e:
                self.logger.warning(f"Error during Docker resource cleanup: {e}")

            # Wait for complete cleanup
            self.wait_for_cleanup()

        except Exception as e:
            self.logger.error(f"Error during service teardown: {e}")
            raise

    def stop_docker_services(self):
        if hasattr(self.docker_executor, "execute_docker_command"):
            # Force-kill containers first to avoid hanging on graceful shutdown
            try:
                kill_args = [
                    "compose",
                    "-f",
                    str(self.config_file_path),
                    "-p",
                    self.network_name,
                    "kill",
                ]
                self.docker_executor.execute_docker_command(
                    docker_args=kill_args,
                    timeout=30,
                )
                self.logger.debug("Docker Compose containers killed")
            except subprocess.CalledProcessError as e:
                self.logger.debug(
                    f"Docker Compose kill (expected if no containers running): {e}"
                )
            except Exception as e:
                self.logger.warning(f"Unexpected error during Docker Compose kill: {e}")

            # Then clean removal of containers, networks, and volumes
            compose_args = [
                "compose",
                "-f",
                str(self.config_file_path),
                "-p",
                self.network_name,
                "down",
                "-v",
                "--remove-orphans",
            ]
            result = self.docker_executor.execute_docker_command(
                docker_args=compose_args,
                timeout=self.timeout,
            )
            self.logger.debug(f"Docker Compose services stopped - {result}")
        else:
            self.logger.warning("Cannot execute docker compose down command")

    def wait_for_cleanup(self, timeout: int = 30) -> None:
        """Wait for complete container cleanup and port release.

        Args:
            timeout: Maximum time to wait for cleanup in seconds
        """
        self.logger.info(f"Waiting for complete cleanup (timeout: {timeout}s)")

        if not self.docker_executor:
            self.logger.warning("No docker executor available for cleanup verification")
            return

        start_time = time.time()

        while time.time() - start_time < timeout:
            # Check if any containers from our services are still running
            for service in self.services_managers:
                service_name = service.service_name
                try:
                    # Check for any containers with this service name
                    self.check_container_existence(service_name)
                except Exception as e:
                    self.logger.debug(
                        f"Error checking container cleanup for {service_name}: {e}"
                    )
            if self.check_ports_status():
                self.logger.info("Cleanup completed successfully")
                return

            time.sleep(2)  # Wait before next check

        self.logger.warning(f"Cleanup verification timed out after {timeout} seconds")

    def check_ports_status(self) -> bool:
        all_cleaned: bool = True
        self.logger.debug("Checking if all ports are released")
        if self.port_manager and hasattr(self.port_manager, "verify_ports_released"):
            try:
                if not self.port_manager.verify_ports_released(self.services_managers):
                    self.logger.debug("Some ports are still in use")
                    all_cleaned = False
            except Exception as e:
                self.logger.debug(f"Error checking port cleanup: {e}")
        self.logger.debug(f"Port cleanup status: {all_cleaned}")
        return all_cleaned

    def check_container_existence(self, service_name):
        docker_args = [
            "ps",
            "-a",
            "--filter",
            f"name={service_name}",
            "--format",
            "{{.Names}}",
        ]

        if hasattr(self.docker_executor, "execute_docker_command"):
            result = self.docker_executor.execute_docker_command(
                docker_args=docker_args, check=False
            )
            if hasattr(result, "stdout") and result.stdout.strip():
                self.logger.debug(f"Container {service_name} still exists")
                all_cleaned = False
            elif isinstance(result, str) and result.strip():
                self.logger.debug(f"Container {service_name} still exists")
                all_cleaned = False

    def _register_service_outputs(self) -> None:
        """Register service outputs with the output collection system."""
        if not self.output_manager:
            self.logger.debug(
                "No output manager available for service output registration"
            )
            return

        try:
            # Check if output manager has registration capability
            if hasattr(self.output_manager, "perform_final_output_registration"):
                # This will be handled by the output manager's registration process
                self.logger.debug(
                    "Output registration will be handled by output manager"
                )
            else:
                self.logger.debug(
                    "Output manager does not support service registration"
                )

        except Exception as e:
            self.logger.warning(f"Error during service output registration: {e}")

    def stop_background_monitoring(self) -> None:
        """Stop background monitoring if active."""
        if self.background_monitor:
            self.logger.info("Stopping background monitoring...")
            try:
                if hasattr(self.background_monitor, "stop_monitoring"):
                    self.background_monitor.stop_monitoring()
                self.background_monitor = None
                self.logger.info("Background monitoring stopped")
            except Exception as e:
                self.logger.warning(f"Error stopping background monitoring: {e}")

    def get_service_status(self) -> Dict[str, bool]:
        """Get the current status of all managed services.

        Returns:
            Dictionary mapping service names to their ready status
        """
        status = {}
        for service in self.services_managers:
            service_name = service.service_name
            status[service_name] = self.is_service_ready(service_name)
        return status
