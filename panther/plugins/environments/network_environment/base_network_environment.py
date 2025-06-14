"""Base class for network environment implementations with common functionality."""

import os
import subprocess
import time
from abc import abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional

from omegaconf import OmegaConf

from panther.config.config_experiment_schema import TestConfig
from panther.config.config_global_schema import GlobalConfig
from panther.plugins.environments.environment_event_methods import (
    EnvironmentPluginEventMixin,
)
from panther.plugins.environments.network_environment.network_environment_interface import (
    INetworkEnvironment,
)
from panther.plugins.services.services_interface import IServiceManager

if TYPE_CHECKING:
    from panther.plugins.environments.execution_environment.execution_environment_interface import (
        IExecutionEnvironment,
    )
    from panther.plugins.plugin_manager import PluginManager


class BaseNetworkEnvironment(INetworkEnvironment, EnvironmentPluginEventMixin):
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

        # Process output directory
        self._process_output_directory(output_dir)

        # Initialize common attributes
        self._initialize_common_attributes()

        # Setup base configuration
        self._validate_base_config()

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
        self.update_environment(
            execution_environment,
            global_config,
            plugin_manager,
            services_managers,
            test_config,
        )

        try:
            # Record setup start time
            self.setup_start_time = time.time()

            # Notify setup started
            self.notify_environment_setup_started()

            # Perform base setup
            if not self._setup_environment():
                raise RuntimeError("Base environment setup failed")

            # Prepare environment
            self.prepare_environment()

            # Generate services
            self.generate_environment_services(
                paths={
                    "service_dir": str(self.output_dir),
                    "log_dir": str(self.log_dirs),
                    "template_dir": str(self.templates_dir),
                },
                timestamp=timestamp,
            )

            # Verify generated files
            self._verify_generated_files()

            # Setup execution plugins if needed
            if self.execution_environment:
                self.setup_execution_plugins(timestamp)

            # Mark setup complete
            self.setup_complete = True
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

    def _setup_environment(self) -> bool:
        """
        Perform base environment setup.

        Override this method in subclasses for specific setup requirements.
        """
        self.logger.info(f"Setting up {self.env_sub_type} environment")
        return True

    def _verify_generated_files(self) -> None:
        """
        Verify that required files were generated.

        Override this method in subclasses to check specific files.
        """
        # Base implementation checks common files
        if hasattr(self, "rendered_services_network_config_file_path"):
            if not os.path.exists(self.rendered_services_network_config_file_path):
                raise RuntimeError(
                    f"Generated config file not found: "
                    f"{self.rendered_services_network_config_file_path}"
                )

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
            self.logger.info(f"Running {self.env_sub_type} environment")

            # Record deployment start time
            self.deployment_start_time = time.time()

            # Launch services
            self.launch_environment_services()

            # Deploy services
            self.deploy_services()

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

            return True

        except Exception as e:
            self.logger.error(f"Failed to prepare environment: {e}")
            return False

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
            raise
