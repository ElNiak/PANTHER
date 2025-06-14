"""
Base execution environment class that eliminates code duplication across execution environment plugins.

This module provides a standardized base class that combines all common mixins and interfaces,
implements boilerplate methods, and defines the template for execution environment plugins.
"""

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from omegaconf import OmegaConf

from panther.config.config_global_schema import GlobalConfig
from panther.core.observer.management.event_manager import EventManager
from panther.core.outputs.execution_environment_mixins import (
    CommandModificationMixin,
    StandardOutputCollectorMixin,
)
from panther.plugins.environments.environment_utils import ExecutionEnvironmentMixin
from panther.plugins.environments.execution_environment.execution_environment_interface import (
    IExecutionEnvironment,
)
from panther.plugins.services.services_interface import IServiceManager

if TYPE_CHECKING:
    from panther.config.config_experiment_schema import TestConfig
    from panther.plugins.plugin_manager import PluginManager


class BaseExecutionEnvironment(
    ExecutionEnvironmentMixin,
    StandardOutputCollectorMixin,
    CommandModificationMixin,
    IExecutionEnvironment,
    ABC,
):
    """
    Base class for all execution environment plugins.

    This class eliminates code duplication by providing common implementations
    of boilerplate methods and standardizing the plugin structure.

    Attributes:
        env_config_to_test: Configuration specific to the environment being tested
        output_dir: Directory where output files will be stored
        env_type: Type of the environment
        env_sub_type: Sub-type of the environment
        event_manager: Manager for handling events
        global_config: Global configuration settings
        services_managers: List of service managers
        test_config: Configuration for the test
        plugin_manager: Plugin manager instance
        logger: Logger for logging information
    """

    def __init__(
        self,
        env_config_to_test,
        output_dir: str,
        env_type: str,
        env_sub_type: str,
        event_manager: EventManager,
    ):
        """
        Initialize the base execution environment.

        Args:
            env_config_to_test: Configuration specific to the environment
            output_dir: Directory where output files will be stored
            env_type: Type of the environment
            env_sub_type: Sub-type of the environment
            event_manager: Manager for handling events
        """
        super().__init__(
            env_config_to_test, output_dir, env_type, env_sub_type, event_manager
        )
        # Use standardized environment initialization from mixin
        self.standardized_environment_initialization(
            env_config_to_test, output_dir, env_type, env_sub_type, event_manager
        )

    def initialize(self, test_config, output_dir, event_manager, global_config):
        """
        Initialize the execution environment with configuration settings.

        Args:
            test_config: Test configuration to use for this environment
            output_dir: Directory to write environment files
            event_manager: Shared event manager instance for emitting events
            global_config: Global configuration settings

        Returns:
            bool: True if initialization succeeded, False otherwise
        """
        try:
            self.test_config = test_config
            self.output_dir = output_dir
            self.event_manager = event_manager
            self.global_config = global_config
            self.is_initialized = True
            self.logger.debug(f"{self.__class__.__name__} initialized successfully")
            return True
        except Exception as e:
            self.logger.error(f"Failed to initialize {self.__class__.__name__}: %s", e)
            return False

    def _do_setup_environment(
        self,
        services_managers,
        test_config,
        global_config,
        timestamp,
        plugin_manager,
        execution_environment=None,
    ):
        """
        Implementation of environment setup (from parent interface).

        Args:
            services_managers: List of service managers
            test_config: Test configuration
            global_config: Global configuration
            timestamp: Timestamp for this execution
            plugin_manager: Plugin manager instance
            execution_environment: List of execution environments (unused for most environments)
        """
        # execution_environment is not needed for most execution environments but required by interface
        _ = execution_environment
        # Delegate to the concrete implementation
        self.setup_environment(
            services_managers, test_config, global_config, timestamp, plugin_manager
        )

    def _do_deploy_services(self):
        """
        Implementation of service deployment.

        For execution environments, deployment is typically handled
        by the network environment, so this is usually a no-op.
        """
        self.logger.debug(
            f"{self.__class__.__name__} deployment: no specific deployment needed"
        )

    def _do_teardown_environment(self):
        """
        Implementation of environment teardown.
        """
        self.logger.debug(f"{self.__class__.__name__} teardown: cleaning up resources")
        # Collect any remaining output files
        outputs = self.collect_outputs()
        if outputs:
            self.logger.info(
                f"Collected {self.__class__.__name__} outputs: %s", list(outputs.keys())
            )

    def handle_event(self, event):
        """
        Handle events sent to this execution environment.

        Args:
            event: The event to handle
        """
        event_type = type(event).__name__
        self.logger.debug(f"{self.__class__.__name__} received event: %s", event_type)

        # Handle common environment-specific events
        if event_type == "ServiceStartedEvent":
            self.logger.debug(
                "Service started, environment monitoring should be active"
            )
        elif event_type == "ServiceStoppedEvent":
            self.logger.debug("Service stopped, environment collection complete")
        else:
            self.logger.debug("Unhandled event type: %s", event_type)

    def setup_environment(
        self,
        services_managers: list[IServiceManager],
        test_config: "TestConfig",
        global_config: GlobalConfig,
        timestamp: str,
        plugin_manager: "PluginManager",
    ):
        """
        Default implementation of environment setup.

        This method provides common setup patterns and can be extended by subclasses.

        Args:
            services_managers: List of service managers
            test_config: Test configuration
            global_config: Global configuration
            timestamp: Timestamp for this execution
            plugin_manager: Plugin manager instance
        """
        # Use standardized setup from mixin
        self.setup_execution_environment(
            services_managers, test_config, global_config, timestamp, plugin_manager
        )

        # Log configuration for debugging
        self.logger.debug("Test Config: %s", OmegaConf.to_yaml(self.test_config))
        self.logger.debug("Global Config: %s", OmegaConf.to_yaml(self.global_config))

        # Call plugin-specific setup
        self._setup_plugin_specific_environment(services_managers, timestamp)

    @abstractmethod
    def _setup_plugin_specific_environment(
        self, services_managers: list[IServiceManager], timestamp: str
    ):
        """
        Plugin-specific environment setup logic.

        This method must be implemented by each plugin to provide its specific
        environment configuration and service modifications.

        Args:
            services_managers: List of service managers to potentially modify
            timestamp: Timestamp for this execution (useful for file naming)
        """
        raise NotImplementedError(
            "Each plugin must implement its specific environment setup"
        )

    @abstractmethod
    def to_command(self, *args, **kwargs) -> str:
        """
        Generate the environment-specific command.

        This method must be implemented by each plugin to provide its specific
        command generation logic.

        Returns:
            str: Command string for this environment
        """
        raise NotImplementedError(
            "Each plugin must implement its command generation logic"
        )

    def __repr__(self):
        """
        String representation of the execution environment instance.
        """
        return (
            f"{self.__class__.__name__}("
            f"env_config_to_test={self.env_config_to_test}, "
            f"output_dir={self.output_dir}, "
            f"event_manager={self.event_manager}, "
            f"services_managers={self.services_managers}, "
            f"test_config={self.test_config})"
        )
