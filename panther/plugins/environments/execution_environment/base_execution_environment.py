"""
Base execution environment class that eliminates code duplication across execution environment plugins.

This module provides a standardized base class that combines all common mixins and interfaces,
implements boilerplate methods, and defines the template for execution environment plugins.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Tuple

from panther.config.core.models.global_config import GlobalConfig
from panther.core.command_processor.mixins import CommandModificationMixin
from panther.core.observer.management.event_manager import EventManager
from panther.core.outputs.output_environment_mixins import StandardOutputCollectorMixin
from panther.core.utils import log_omega_config_summary
from panther.core.utils.string_representation_mixin import StringRepresentationMixin
from panther.plugins.environments.execution_environment.execution_environment_interface import (
    IExecutionEnvironment,
)
from panther.plugins.environments.execution_environment_mixin import (
    ExecutionEnvironmentMixin,
)
from panther.plugins.services.services_interface import IServiceManager

if TYPE_CHECKING:
    from panther.config.core.models.experiment import TestConfig
    from panther.plugins.plugin_manager import PluginManager


class BaseExecutionEnvironment(
    ExecutionEnvironmentMixin,
    StandardOutputCollectorMixin,
    CommandModificationMixin,
    IExecutionEnvironment,
    StringRepresentationMixin,
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

    def initialize(
        self,
        test_config: "TestConfig",
        output_dir: str,
        event_manager: EventManager,
        global_config: GlobalConfig,
    ):
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
        raise NotImplementedError(
            "Each plugin must implement its own initialization logic"
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
        services_managers: List[IServiceManager],
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
        self.logger.debug(
            f"BaseExecutionEnvironment.setup_environment called for {self.__class__.__name__}"
        )
        self.logger.debug(f"Services managers count: {len(services_managers)}")
        self.logger.debug(
            f"Service names: {[getattr(s, 'service_name', s.__class__.__name__) for s in services_managers]}"
        )

        self.setup_execution_environment(
            services_managers, test_config, global_config, timestamp, plugin_manager
        )

        # Log configuration for debugging using summarizer
        log_omega_config_summary(self.logger, "Test Config", self.test_config)
        log_omega_config_summary(self.logger, "Global Config", self.global_config)

        # Call plugin-specific setup
        self.logger.debug(
            f"About to call _setup_plugin_specific_environment for {self.__class__.__name__}"
        )
        self._setup_plugin_specific_environment(services_managers, timestamp)
        self.logger.debug(
            f"Completed _setup_plugin_specific_environment for {self.__class__.__name__}"
        )

    def get_output_patterns(self) -> List[Tuple[str, str]]:
        """
        Get output patterns specific to this execution environment.

        Override this method in subclasses to provide custom patterns.

        Returns:
            List of (output_type, filename_pattern) tuples
        """
        # Default patterns for execution environments
        return [
            ("profile", f"{self.env_sub_type}_{{service_name}}.log"),
            ("summary", f"{self.env_sub_type}_summary_{{service_name}}.txt"),
            ("raw", f"{self.env_sub_type}_raw_{{service_name}}.dat"),
        ]

    def get_additional_output_discovery_patterns(self) -> Dict[str, List[str]]:
        """
        Get additional patterns for discovering outputs.

        Override this in subclasses to provide custom discovery patterns.

        Returns:
            Dict mapping output types to lists of glob patterns
        """
        return {}

    @abstractmethod
    def _setup_plugin_specific_environment(
        self, services_managers: List[IServiceManager], timestamp: str
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

    def _get_key_attributes(self) -> Dict[str, Any]:
        """Get key attributes for string representation."""
        attrs = super()._get_key_attributes()

        # Show service count instead of full list
        if hasattr(self, "services_managers") and self.services_managers:
            attrs["services"] = len(self.services_managers)

        return attrs
