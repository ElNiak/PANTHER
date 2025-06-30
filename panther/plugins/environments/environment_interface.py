import os
from abc import abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING, List, Optional, Union

from panther.config.core.models.environment import EnvironmentConfig
from panther.core.events.environment.emitter import EnvironmentEventEmitter
from panther.core.observer.management.event_manager import EventManager
from panther.plugins.environments.environment_event_methods import (
    EnvironmentPluginEventMixin,
)
from panther.plugins.plugin_interface import IPlugin

# PluginManager functionality now integrated into PluginManager

if TYPE_CHECKING:
    from panther.config.core.models.experiment import TestConfig
    from panther.config.core.models.global_config import GlobalConfig
    from panther.plugins.environments.execution_environment.execution_environment_interface import (
        IExecutionEnvironment,
    )
    from panther.plugins.plugin_manager import PluginManager
    from panther.plugins.services.services_interface import IServiceManager


class IEnvironmentPlugin(IPlugin, EnvironmentPluginEventMixin):
    """
    IEnvironmentPlugin is an abstract base class that defines the interface for environment plugins.

    Attributes:
        templates_dir (str): Directory path for templates specific to the environment type and subtype.
        output_dir (str): Directory path for output files.
        env_type (str): Type of the environment.
        env_sub_type (str): Subtype of the environment.
        log_dirs (str): Directory path for log files.
        plugin_manager: Plugin manager for loading plugins.
        env_config_to_test (EnvironmentConfig): Configuration of the environment to be tested.
        event_manager (EventManager): Manager for handling events.

    Methods:
        is_network_environment():
            Abstract method. Returns True if the plugin is a network environment.

        setup_environment():
            Abstract method. Sets up the required environment before running experiments.

        teardown_environment():
            Abstract method. Tears down the environment after experiments are completed.
    """

    def __init__(
        self,
        env_config_to_test: EnvironmentConfig,
        output_dir: str,
        env_type: str,
        env_sub_type: str,
        event_manager: EventManager,
    ):
        super().__init__()
        self._plugin_dir = Path(os.path.dirname(__file__))
        self.templates_dir: str = (
            f"{self._plugin_dir}/{env_type}/{env_sub_type}/templates"
        )
        self.output_dir = output_dir
        self.env_type = env_type
        self.env_sub_type = env_sub_type
        self.log_dirs = os.path.join(self.output_dir, "logs")
        self.plugin_manager = None
        self.env_config_to_test = env_config_to_test
        self.event_manager = event_manager

        # Initialize event emitter for standardized event emission
        self.event_emitter = EnvironmentEventEmitter(event_manager)

        # Initialize properties
        self.services_managers = []
        self.test_config = None
        self.global_config = None
        self.plugin_manager = None

    @abstractmethod
    def is_network_environment(self):
        """
        Returns True if the plugin is a network environment.
        """
        pass

    def set_event_manager(self, event_manager: EventManager):
        """
        Set the event manager for this plugin. (For Mixin)

        Args:
            event_manager: The event manager to set
        """
        self.event_manager = event_manager
        self.event_emitter = EnvironmentEventEmitter(event_manager)

    def setup_environment(
        self,
        services_managers: List["IServiceManager"],
        test_config: "TestConfig",
        global_config: "GlobalConfig",
        timestamp: str,
        plugin_manager: "Optional[PluginManager]",
        execution_environment: List["IExecutionEnvironment"],
    ) -> None:
        """
        Sets up the environment with proper event notifications.
        """
        try:
            self.logger.debug(
                "EnvirontmentI - Setting up environment: %s (%s)",
                self.env_type,
                self.env_sub_type,
            )
            # Store references for later use
            self.services_managers = services_managers
            self.test_config = test_config
            self.global_config = global_config
            self.plugin_manager = plugin_manager

            # Emit environment setup started event
            self.notify_environment_setup_started(
                details={
                    "environment_type": self.env_type,
                    "environment_name": self.env_sub_type,
                    "test_case": test_config.name if test_config else "unknown",
                }
            )

            self.update_environment(
                execution_environment=execution_environment,
                global_config=global_config,
                plugin_manager=plugin_manager,
                services_managers=services_managers,
                test_config=test_config,
            )

            # Emit environment setup completed event (success)
            self.notify_environment_setup_completed(
                success=True,
                details={
                    "environment_type": self.env_type,
                    "environment_name": self.env_sub_type,
                    "test_case": test_config.name if test_config else "unknown",
                },
            )

        except Exception as e:
            # Emit environment setup completed event (failure)
            self.notify_environment_setup_completed(
                success=False,
                details={
                    "environment_type": self.env_type,
                    "environment_name": self.env_sub_type,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "test_case": test_config.name if test_config else "unknown",
                },
            )
            raise

    @abstractmethod
    def _do_deploy_services(self) -> None:
        """
        Implementation of service deployment, to be overridden by subclasses.
        """
        pass

    @abstractmethod
    def teardown_environment(self) -> None:
        """
        Teardown the environment with proper event notifications.
        """
        pass

    @abstractmethod
    def _do_teardown_environment(self) -> None:
        """
        Implementation of environment teardown, to be overridden by subclasses.
        """
        pass

    @abstractmethod
    def update_environment(
        self,
        execution_environment,
        global_config: "GlobalConfig",
        plugin_manager: "Optional[PluginManager]",
        services_managers: "List[IServiceManager]",
        test_config: "TestConfig",
    ) -> None:
        """
        Update environment configuration.
        """
        pass

    @abstractmethod
    def initialize(
        self,
        test_config: "TestConfig",
        output_dir: str,
        event_manager: "EventManager",
        global_config: "GlobalConfig",
    ) -> bool:
        """
        Initialize the environment with configuration settings.

        Args:
            test_config: Test configuration to use for this environment
            output_dir: Directory to write environment files
            event_manager: Shared event manager instance for emitting events
            global_config: Global configuration settings

        Returns:
            bool: True if initialization succeeded, False otherwise
        """
        pass
