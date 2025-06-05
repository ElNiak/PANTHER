import logging
import os
from pathlib import Path
from typing import Any

from panther.plugins.environments.environment_event_methods import EnvironmentPluginEventMixin
from panther.plugins.environments.environment_interface import IEnvironmentPlugin
from panther.plugins.services.services_interface import IServiceManager
from panther.config.config_experiment_schema import TestConfig
from panther.config.config_global_schema import GlobalConfig
from panther.plugins.environments.execution_environment.execution_environment_interface import (
    IExecutionEnvironment,
)
from panther.plugins.plugin_loader import PluginLoader
from panther.core.observer.event_emitter import EventEmitter


class BaseEnvironmentPlugin(IEnvironmentPlugin, EnvironmentPluginEventMixin):
    """
    Base class for all environment plugins, implementing common functionality
    and standardized event emission.
    """

    def __init__(
        self,
        env_config_to_test,
        output_dir: str,
        env_type: str,
        env_sub_type: str,
        event_manager=None,
    ):
        super().__init__(env_config_to_test, output_dir, env_type, env_sub_type, event_manager)
        self.logger = logging.getLogger(f"{self.__class__.__name__}")
        self._plugin_dir = Path(os.path.dirname(__file__)).parent.parent.parent / "plugins"

        # Set up event emitter if event_manager is provided
        if event_manager:
            self.event_emitter = EventEmitter(event_manager)

        # Initialize properties
        self.services_managers = []
        self.test_config = None
        self.global_config = None
        self.plugin_loader = None

    def setup_environment(
        self,
        services_managers: list[IServiceManager],
        test_config: TestConfig,
        global_config: GlobalConfig,
        timestamp: str,
        plugin_loader: PluginLoader,
        execution_environment: list[IExecutionEnvironment],
    ) -> None:
        """
        Sets up the environment with proper event notifications.
        """
        try:
            # Store references for later use
            self.services_managers = services_managers
            self.test_config = test_config
            self.global_config = global_config
            self.plugin_loader = plugin_loader

            # Emit environment setup started event
            self.notify_environment_setup_started(
                details={
                    "environment_type": self.env_type,
                    "environment_name": self.env_sub_type,
                    "test_name": test_config.name if test_config else "unknown",
                }
            )

            # Perform actual setup implementation
            self._do_setup_environment(
                services_managers,
                test_config,
                global_config,
                timestamp,
                plugin_loader,
                execution_environment,
            )

            # Emit environment setup completed event (success)
            self.notify_environment_setup_completed(
                success=True,
                details={
                    "environment_type": self.env_type,
                    "environment_name": self.env_sub_type,
                    "test_name": test_config.name if test_config else "unknown",
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
                    "test_name": test_config.name if test_config else "unknown",
                },
            )
            raise

    def _do_setup_environment(
        self,
        services_managers: list[IServiceManager],
        test_config: TestConfig,
        global_config: GlobalConfig,
        timestamp: str,
        plugin_loader: PluginLoader,
        execution_environment: list[IExecutionEnvironment],
    ) -> None:
        """
        Implementation of environment setup, to be overridden by subclasses.
        """
        raise NotImplementedError("Subclasses must implement _do_setup_environment")

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

    def _do_deploy_services(self) -> None:
        """
        Implementation of service deployment, to be overridden by subclasses.
        """
        raise NotImplementedError("Subclasses must implement _do_deploy_services")

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

    def _do_teardown_environment(self) -> None:
        """
        Implementation of environment teardown, to be overridden by subclasses.
        """
        raise NotImplementedError("Subclasses must implement _do_teardown_environment")

    def notify_environment_event(self, event_name: str, details: dict[str, Any] = None):
        """
        Notify of a generic environment event.

        Args:
            event_name: The name of the event
            details: Additional details about the event
        """
        if hasattr(self, "event_emitter"):
            self.event_emitter.emit_event(f"environment.{event_name}", details or {})

    def update_environment(
        self,
        execution_environment,
        global_config,
        plugin_loader,
        services_managers,
        test_config,
    ) -> None:
        """
        Update environment configuration.
        """
        self.services_managers = services_managers
        self.test_config = test_config
        self.global_config = global_config
        self.plugin_loader = plugin_loader
