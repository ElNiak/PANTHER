from abc import abstractmethod
import os
from pathlib import Path
from typing import TYPE_CHECKING

from panther.core.observer.management.event_manager import EventManager
from panther.core.events import EnvironmentEventEmitter
from panther.plugins.environments.config_schema import EnvironmentConfig
from panther.plugins.plugin_interface import IPlugin
from panther.plugins.environments.environment_event_methods import EnvironmentPluginEventMixin

# PluginManager functionality now integrated into PluginManager

if TYPE_CHECKING:
    from panther.plugins.services.services_interface import IServiceManager
    from panther.config.config_experiment_schema import TestConfig
    from panther.config.config_global_schema import GlobalConfig
    from panther.plugins.environments.execution_environment.execution_environment_interface import (
        IExecutionEnvironment,
    )
    from panther.plugins.plugin_manager import PluginManager


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
        self.templates_dir: str = f"{self._plugin_dir}/{env_type}/{env_sub_type}/templates"
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
        Set the event manager for this plugin.

        Args:
            event_manager: The event manager to set
        """
        self.event_manager = event_manager
        self.event_emitter = EnvironmentEventEmitter(event_manager)

    def setup_environment(
        self,
        services_managers: list["IServiceManager"],
        test_config: "TestConfig",
        global_config: "GlobalConfig",
        timestamp: str,
        plugin_manager: "PluginManager | None",
        execution_environment: list["IExecutionEnvironment"],
    ) -> None:
        """
        Sets up the environment with proper event notifications.
        """
        try:
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

            # Perform actual setup implementation
            self._do_setup_environment(
                services_managers,
                test_config,
                global_config,
                timestamp,
                plugin_manager,
                execution_environment,
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
    def _do_setup_environment(
        self,
        services_managers: list["IServiceManager"],
        test_config: "TestConfig",
        global_config: "GlobalConfig",
        timestamp: str,
        plugin_manager: "PluginManager | None",
        execution_environment: list["IExecutionEnvironment"],
    ) -> None:
        """
        Implementation of environment setup, to be overridden by subclasses.
        """
        pass

    def deploy_services(self) -> None:
        """
        Deploy services with proper event notifications.
        """
        try:
            # Emit services deployment started event
            self.notify_environment_event(
                "services_deployment_started",
                {
                    "environment_type": self.env_type,
                    "environment_name": self.env_sub_type,
                    "service_count": len(self.services_managers),
                },
            )

            # Perform actual deployment
            self._do_deploy_services()

            # Emit services deployment completed event (success)
            self.notify_environment_event(
                "services_deployment_completed",
                {
                    "environment_type": self.env_type,
                    "environment_name": self.env_sub_type,
                    "success": True,
                },
            )

        except Exception as e:
            # Emit services deployment completed event (failure)
            self.notify_environment_event(
                "services_deployment_completed",
                {
                    "environment_type": self.env_type,
                    "environment_name": self.env_sub_type,
                    "success": False,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                },
            )
            raise

    @abstractmethod
    def _do_deploy_services(self) -> None:
        """
        Implementation of service deployment, to be overridden by subclasses.
        """
        pass

    def teardown_environment(self) -> None:
        """
        Teardown the environment with proper event notifications.
        """
        try:
            # Emit environment teardown started event
            self.notify_environment_event(
                "environment_teardown_started",
                {"environment_type": self.env_type, "environment_name": self.env_sub_type},
            )

            # Perform actual teardown
            self._do_teardown_environment()

            # Emit environment teardown completed event (success)
            self.notify_environment_teardown(
                success=True,
                details={"environment_type": self.env_type, "environment_name": self.env_sub_type},
            )

        except Exception as e:
            # Emit environment teardown completed event (failure)
            self.notify_environment_teardown(
                success=False,
                details={
                    "environment_type": self.env_type,
                    "environment_name": self.env_sub_type,
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                },
            )
            # Don't re-raise; allow other cleanup to continue
            self.logger.error(f"Error during environment teardown: {e}", exc_info=True)

    @abstractmethod
    def _do_teardown_environment(self) -> None:
        """
        Implementation of environment teardown, to be overridden by subclasses.
        """
        pass

    def update_environment(
        self,
        execution_environment,
        global_config,
        plugin_manager,
        services_managers,
        test_config,
    ) -> None:
        """
        Update environment configuration.
        """
        self.services_managers = services_managers
        self.test_config = test_config
        self.global_config = global_config
        self.plugin_manager = plugin_manager

    @abstractmethod
    def initialize(self, test_config, output_dir, event_manager, global_config):
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
