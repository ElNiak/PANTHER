"""Base class for network environment implementations with common functionality."""

import os
import subprocess
import time
from abc import abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional

from omegaconf import OmegaConf

from panther.config.core.models.experiment import TestConfig
from panther.config.core.models.global_config import GlobalConfig
from panther.config.core.models.service import ProtocolRole
from panther.core.outputs.output_collector import IOutputCollector
from panther.core.utils.string_representation_mixin import StringRepresentationMixin

# EnvironmentPluginEventMixin is already inherited through INetworkEnvironment
from panther.plugins.environments.network_environment.network_environment_interface import (
    INetworkEnvironment,
)
from panther.plugins.services.services_interface import IServiceManager

if TYPE_CHECKING:
    from panther.plugins.environments.execution_environment.execution_environment_interface import (
        IExecutionEnvironment,
    )
    from panther.plugins.plugin_manager import PluginManager


class BaseNetworkEnvironment(INetworkEnvironment, StringRepresentationMixin):
    """
    Base implementation of INetworkEnvironment with common functionality.

    This class provides shared implementations for:
    - Configuration processing and validation
    - Directory management
    - Common setup/teardown workflows
    - Error handling patterns
    - Status monitoring

    Subclasses should override abstract methods for environment-specific behavior.
    """

    def __init__(
        self,
        env_config_to_test,
        output_dir: str,
        env_type: str,
        env_sub_type: str,
        event_manager,
    ):
        """Initialize base network environment with common setup."""
        super().__init__(
            env_config_to_test, output_dir, env_type, env_sub_type, event_manager
        )
        # Initialize common attributes
        self._initialize_common_attributes()

    def _process_output_directory(self, output_dir: Any) -> None:
        """Process and validate output directory."""
        # Convert Path to string if needed
        if isinstance(output_dir, Path):
            output_dir = str(output_dir)

        self.output_dir = Path(output_dir)

        # Ensure required directories exist
        self._ensure_directories()

    def _ensure_directories(self) -> None:
        """Ensure all required directories exist."""
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(os.path.join(self.output_dir, "logs"), exist_ok=True)
        self.logger.debug(f"Ensured directories exist: {self.output_dir}")

    def _initialize_common_attributes(self) -> None:
        """Initialize attributes common to all network environments."""
        self.processes = []
        self.deployed = False
        self.setup_complete = False
        self.teardown_complete = False

        # Timing attributes
        self.setup_start_time = None
        self.setup_end_time = None
        self.deployment_start_time = None
        self.deployment_end_time = None

        # Early termination tracking
        self._early_termination_requested = False
        self._early_termination_reason = None
        self._early_termination_details = None

    def _get_user_mapping_config(self) -> Optional[str]:
        """
        Get user mapping configuration for containers.

        Returns:
            Optional[str]: User mapping string in format 'uid:gid' or None for root
        """
        if not hasattr(self, "global_config") or not self.global_config:
            return None

        docker_config = self.global_config.docker
        user_config = docker_config.user_mapping

        if user_config.run_as_host_user:
            try:
                import os

                uid = user_config.custom_uid or os.getuid()
                gid = user_config.custom_gid or os.getgid()
                return f"{uid}:{gid}"
            except (AttributeError, OSError):
                if user_config.fallback_to_root:
                    self.logger.warning("Cannot get host user ID, falling back to root")
                    return None
                else:
                    raise RuntimeError(
                        "Cannot determine host user ID and fallback disabled"
                    )
        elif user_config.custom_uid and user_config.custom_gid:
            return f"{user_config.custom_uid}:{user_config.custom_gid}"

        return None

    def _validate_base_config(self) -> None:
        """Validate base configuration requirements."""
        if not self.env_config_to_test:
            self.logger.warning("No environment configuration provided")

        if not self.templates_dir or not os.path.exists(self.templates_dir):
            self.logger.warning(f"Templates directory not found: {self.templates_dir}")

    def setup_environment(
        self,
        services_managers: List[IServiceManager],
        test_config: TestConfig,
        global_config: GlobalConfig,
        timestamp: str,
        plugin_manager: Optional["PluginManager"],
        execution_environment: List["IExecutionEnvironment"],
    ) -> bool:
        """
        Common setup workflow for network environments.

        This method provides the standard setup sequence while allowing
        subclasses to customize specific steps.
        """
        self.notify_environment_setup_started(
            details={
                "output_dir": str(self.output_dir),
                "log_dirs": str(self.log_dirs),
                "template_dir": str(self.templates_dir),
                "timestamp": timestamp,
            }
        )

        self.logger.debug(
            f"Initializing {self.env_sub_type} environment with output directory: {self.output_dir}"
            f" and log directories: {self.log_dirs}"
            f" and template directory: {self.templates_dir}"
            f" and timestamp: {timestamp}"
            f" and execution environment: {execution_environment}"
        )
        self.setup_start_time = time.time()
        self.logger.info(f"Setting up {self.env_sub_type} environment")
        self.update_environment(
            execution_environment,
            global_config,
            plugin_manager,
            services_managers,
            test_config,
        )

        # Process output directory
        self._process_output_directory(self.output_dir)

        # Setup base configuration
        self._validate_base_config()

        try:
            # Prepare environment
            self.prepare_environment()

            # Generate services (with execution environment modifications applied)
            self.generate_environment_services(
                paths={
                    "output_dir": str(self.output_dir),
                    "log_dir": str(self.log_dirs),
                    "template_dir": str(self.templates_dir),
                },
                timestamp=timestamp,
            )

            self.setup_end_time = time.time()
            # Notify success
            self.notify_environment_setup_completed(
                success=True,
                details={"duration": self.setup_end_time - self.setup_start_time},
            )

            return True

        except Exception as e:
            self.logger.error(f"Environment setup failed: {e}")

            # Notify failure
            self.notify_environment_setup_completed(
                success=False, details={"error": str(e)}
            )

            # Attempt cleanup
            self._safe_cleanup()

            raise

    def teardown_environment(self) -> None:
        """
        Common teardown workflow for network environments.

        This method provides the standard teardown sequence while allowing
        subclasses to customize specific steps.
        """
        if self.teardown_complete:
            self.logger.debug("Environment already torn down")
            return

        try:
            self.logger.info(f"Tearing down {self.env_sub_type} environment")

            # Notify teardown started
            self.notify_environment_event("environment_teardown_started")

            # Perform environment-specific teardown
            self._teardown_environment()

            # Register outputs after services have stopped but before cleanup
            try:
                self.logger.info("Collecting outputs from all services")
                # Collect outputs using the mixin if available
                if hasattr(self, "collect_outputs"):
                    if final_outputs := self.collect_outputs():
                        self.logger.info(
                            f"Successfully collected {len(final_outputs)} output files"
                        )
                    else:
                        self.logger.warning(
                            "No outputs collected despite registration attempts"
                        )
                else:
                    self.logger.warning(
                        "collect_outputs method not available - outputs registered but not collected"
                    )

            except Exception as e:
                self.logger.error(f"Failed to collect outputs during teardown: {e}")

            # Clean up processes
            self._cleanup_processes()

            # Mark teardown complete
            self.teardown_complete = True

            # Notify teardown completed
            self.notify_environment_teardown(success=True)

        except Exception as e:
            self.logger.error(f"Error during teardown: {e}")

            # Notify teardown failure
            self.notify_environment_teardown(success=False, details={"error": str(e)})

            # Don't re-raise to allow cleanup to continue

    @abstractmethod
    def _teardown_environment(self) -> None:
        """
        Perform environment-specific teardown.

        Subclasses must implement this method for their specific teardown logic.
        """
        raise NotImplementedError()

    @abstractmethod
    def _get_service_log_directory(self, service_name: str) -> Path:
        """
        Get the log directory for a specific service.

        Args:
            service_name: Name of the service

        Returns:
            Path to the service's log directory
        """
        raise NotImplementedError()

    def _cleanup_processes(self) -> None:
        """Clean up any remaining processes."""
        for proc in self.processes:
            if proc and proc.poll() is None:
                try:
                    proc.terminate()
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
                except Exception as e:
                    self.logger.error(f"Error terminating process: {e}")

        self.processes.clear()

    def _safe_cleanup(self) -> None:
        """
        Perform safe cleanup in case of errors.

        This method should not raise exceptions.
        """
        try:
            self._cleanup_processes()
        except Exception as e:
            self.logger.error(f"Error during safe cleanup: {e}")

    def run(self) -> bool:
        """
        Common run implementation.

        Most network environments have similar run logic.
        """
        try:
            if self.deployed:
                self.logger.debug(f"{self.env_sub_type} environment already deployed")
                return True

            self.logger.info(f"Running {self.env_sub_type} environment")

            # Record deployment start time
            self.deployment_start_time = time.time()

            # Launch services
            self.launch_environment_services()

            # Mark as deployed
            self.deployed = True

            self.deployment_end_time = time.time()

            self.logger.info(
                f"{self.env_sub_type} environment deployed successfully in "
                f"{self.deployment_end_time - self.deployment_start_time:.2f} seconds"
            )

            return True

        except Exception as e:
            self.logger.error(f"Failed to run environment: {e}")
            raise

    def prepare(self) -> bool:
        """
        Common prepare implementation.

        Most network environments have similar prepare logic.
        """
        try:
            self.logger.info(f"Preparing {self.env_sub_type} environment")

            # Ensure directories exist
            self._ensure_directories()

            # Create log directories for services
            for service in self.services_managers:
                self.create_log_dir(service)

            # Add packet capture commands to services
            self._add_packet_capture_commands()
            self.__add_wait_for_testers()
            self.__add_volumes_to_services()
            self.logger.info("Environment prepared successfully")

            return True

        except Exception as e:
            self.logger.error(f"Failed to prepare environment: {e}")
            return False

    def __add_volumes_to_services(self) -> None:
        """
        Add shared volumes to all services.

        This method injects shared volumes into each service's configuration
        to ensure they can access common resources.
        """
        if not hasattr(self, "services_managers") or not self.services_managers:
            self.logger.debug("No services managers available for volume injection")
            return
        self.logger.info("Adding shared volumes to services")
        for service in self.services_managers:
            # Ensure volumes list exists
            if not hasattr(service, "volumes"):
                service.volumes = []

            self.logger.debug(f"Added shared volumes to {service.service_name}")
        else:
            self.logger.debug(
                f"Skipping volume injection for tester service: {service.service_name}"
            )

    def __add_wait_for_testers(self) -> None:
        """
        Add wait commands for all services to ensure they are ready before running tests.

        This method injects wait commands into each service's pre_run_cmds
        to ensure they are ready before proceeding with the experiment.
        """
        if not hasattr(self, "services_managers") or not self.services_managers:
            self.logger.debug(
                "No services managers available for wait command injection"
            )
            return
        self.logger.info("Adding wait commands to services")
        for service in self.services_managers:
            self.logger.debug(
                f"Processing service: {service.service_name} (client={service.is_client()}, server={service.is_server()}, tester={service.is_tester()})"
            )
            # Ensure coordination volume
            if "coordination:/app/coordination" not in service.volumes:
                service.volumes.append("coordination:/app/coordination")

            # Determine service characteristics
            wait_commands = []

            # All non-tester services wait for ivy compilation first
            if not service.is_tester():
                wait_script = (
                    'echo "Non-tester service '
                    + service.service_name
                    + ' waiting for ivy compilation..." >> /app/logs/coordination.log\n'
                    "WAIT_COUNT=0\n"
                    "while [ $WAIT_COUNT -lt 300 ]; do\n"
                    "\tif ls /app/coordination/*ivy*_ready 1>/dev/null 2>&1; then\n"
                    '\t\techo "Ivy compilation complete for '
                    + service.service_name
                    + '" >> /app/logs/coordination.log\n'
                    "\t\tbreak\n"
                    "\tfi\n"
                    "\tsleep 1\n"
                    "\tWAIT_COUNT=$((WAIT_COUNT + 1))\n"
                    "done\n"
                    "if [ $WAIT_COUNT -ge 300 ]; then\n"
                    '\techo "ERROR: Timeout waiting for ivy compilation for '
                    + service.service_name
                    + '" >> /app/logs/coordination.log\n'
                    "\texit 1\n"
                    "fi"
                )
                wait_commands.append(wait_script)

            # After ivy compilation, different services have different additional waits
            if service.is_client():
                # Client services also wait for server readiness
                wait_script = (
                    '\necho "Client '
                    + service.service_name
                    + ' now waiting for server services..." >> /app/logs/coordination.log\n'
                    "WAIT_COUNT=0\n"
                    "while [ $WAIT_COUNT -lt 300 ]; do\n"
                    "\tif ls /app/coordination/*server*_ready 1>/dev/null 2>&1; then\n"
                    '\t\techo "Server services ready - client '
                    + service.service_name
                    + ' can proceed" >> /app/logs/coordination.log\n'
                    "\t\tbreak\n"
                    "\tfi\n"
                    "\tsleep 1\n"
                    "\tWAIT_COUNT=$((WAIT_COUNT + 1))\n"
                    "done\n"
                    "if [ $WAIT_COUNT -ge 300 ]; then\n"
                    '\techo "ERROR: Timeout waiting for server services for client '
                    + service.service_name
                    + '" >> /app/logs/coordination.log\n'
                    "\texit 1\n"
                    "fi"
                )
                wait_commands.append(wait_script)
            else:
                # Other non-tester services just wait for ivy
                wait_commands.append(
                    'echo "Ivy compilation complete - '
                    + service.service_name
                    + ' ready to proceed" >> /app/logs/coordination.log'
                )

            # Add wait commands to post_compile_cmds if any were defined
            if wait_commands:
                service.run_cmd["post_compile_cmds"] = (
                    service.run_cmd["post_compile_cmds"] + wait_commands
                )
                self.logger.debug(
                    f"Added coordination wait commands to {service.service_name} (client={service.is_client()}, server={service.is_server()}, tester={service.is_tester()})"
                )
            else:
                self.logger.debug(
                    f"No coordination wait needed for {service.service_name}"
                )

    def _add_packet_capture_commands(self) -> None:
        """
        Add packet capture commands to all services.

        This method injects tshark commands into each service's pre_run_cmds
        to enable packet capture for network analysis.
        """
        if not hasattr(self, "services_managers") or not self.services_managers:
            self.logger.debug(
                "No services managers available for packet capture injection"
            )
            return

        self.logger.info("Adding packet capture commands to services")

        for service in self.services_managers:
            try:
                service_name = getattr(
                    service, "service_name", service.__class__.__name__
                )

                # Get service timeout or use default
                timeout = getattr(
                    service, "timeout", getattr(service, "service_timeout", 60)
                )
                if hasattr(service, "service_config_to_test") and hasattr(
                    service.service_config_to_test, "timeout"
                ):
                    timeout = service.service_config_to_test.timeout

                pcap_file = f"/app/logs/{service_name}.pcap"
                # Create the pcap file first
                touch_cmd = f"touch {pcap_file};"
                # Run tshark in background for packet capture
                tshark_cmd = f"(tshark -a duration:{timeout} -i any -w {pcap_file} &);"
                # Add to pre_run_cmds using the mixin method if available
                service.run_cmd["pre_run_cmds"] = service.run_cmd["pre_run_cmds"] + [
                    f"echo 'Starting packet capture for {service_name}...' >> /app/logs/packet_capture.log;",
                    touch_cmd,
                    tshark_cmd,
                    f"echo 'Packet capture command added for {service_name}' >> /app/logs/packet_capture.log;",
                ]

            except Exception as e:
                service_name = getattr(service, "service_name", "unknown")
                self.logger.error(
                    f"Failed to add packet capture for service {service_name}: {e}"
                )

    def _ip_to_decimal(self, ip: str) -> str:
        """
        Convert IP address to decimal format.

        Args:
            ip: IP address in dotted notation (e.g., "192.168.1.1")

        Returns:
            IP address as decimal string
        """
        try:
            parts = ip.split(".")
            if len(parts) != 4:
                raise ValueError(f"Invalid IP format: {ip}")
            decimal = 0
            for i, part in enumerate(parts):
                decimal += int(part) << (24 - (i * 8))
            return str(decimal)
        except Exception as e:
            self.logger.error(f"Failed to convert IP to decimal: {ip} - {e}")
            return "0"

    def _get_service_port(self, service: IServiceManager) -> int:
        """
        Extract port from service configuration.

        Args:
            service: Service manager instance

        Returns:
            Port number
        """
        try:
            # Try to get port from service config
            if hasattr(service, "service_config_to_test"):
                config = service.service_config_to_test
                if hasattr(config, "network") and hasattr(config.network, "port"):
                    return config.network.port
                if hasattr(config, "port"):
                    return config.port

            # Default port based on protocol
            if hasattr(service, "service_protocol"):
                protocol_name = service.service_protocol.name.lower()
                if "quic" in protocol_name:
                    return 4443
                elif "http" in protocol_name:
                    return 80

            # Fallback
            return 4443
        except Exception as e:
            self.logger.error(
                f"Failed to get port for service {service.service_name}: {e}"
            )
            return 4443

    @abstractmethod
    def _get_service_ip(self, service_name: str) -> str:
        """
        Get IP address for a service.

        This method must be implemented by each network environment to provide
        the appropriate IP resolution mechanism.

        Args:
            service_name: Name of the service

        Returns:
            IP address as string
        """
        raise NotImplementedError("Subclasses must implement IP resolution")

    def should_terminate_early(self) -> bool:
        """Check if experiment should terminate early due to environment issues."""
        return self._early_termination_requested

    def request_early_termination(self, reason: str, details: dict = None):
        """Request early experiment termination."""
        self._early_termination_requested = True
        self._early_termination_reason = reason
        self._early_termination_details = details or {}
        self.logger.info(f"Early termination requested: {reason}")

        # Also emit the event through the proper channel
        if hasattr(self, "notify_experiment_early_finish"):
            self.notify_experiment_early_finish(reason, details)

    @abstractmethod
    def _get_service_log_directory(self, service_name: str) -> Path:
        """
        Get the log directory for a specific service.

        This method must be implemented by each environment to provide
        the correct path mapping for service log directories.

        Args:
            service_name: Name of the service

        Returns:
            Path to the service's log directory
        """
        raise NotImplementedError(
            "Subclasses must implement service log directory resolution"
        )

    def _do_deploy_services(self):
        raise NotImplementedError

    def _do_teardown_environment(self):
        raise NotImplementedError

    def initialize(self, test_config, output_dir, event_manager, global_config):
        raise NotImplementedError

    def generate_environment_services(self, paths, timestamp):
        raise NotImplementedError

    def prepare_environment(self):
        raise NotImplementedError

    def launch_environment_services(self):
        raise NotImplementedError

    def deploy_services(self):
        raise NotImplementedError
