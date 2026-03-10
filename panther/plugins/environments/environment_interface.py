"""Environment plugin interface for PANTHER."""

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
    """Core interface for all PANTHER environment implementations.

    Bridges the plugin architecture with environment management for both
    network environments (Docker Compose, Shadow NS) and execution analysis
    environments (Valgrind, strace). Provides lifecycle management with
    event notifications through `EnvironmentEventEmitter`.

    Environment classification:
        - Network environments: orchestrate multiple services in isolated networks.
          Returns ``True`` from `is_network_environment()`.
        - Execution environments: wrap individual service execution with analysis tools.
          Returns ``False`` from `is_network_environment()`.

    Attributes:
        templates_dir: Directory path for environment-specific configuration templates.
        output_dir: Root directory for all environment output artifacts.
        env_type: Primary environment category (network_environment, execution_environment).
        env_sub_type: Specific implementation (docker_compose, shadow_ns, strace, etc.).
        log_dirs: Structured logging directory within output_dir.
        env_config_to_test: Type-specific environment configuration.
        event_manager: Centralized event system for framework coordination.
        event_emitter: Standardized environment event emission.
        services_managers: Coordinated service management instances.
        test_config: Current test case configuration.
        global_config: Framework-wide configuration settings.
    """

    def __init__(
        self,
        env_config_to_test: EnvironmentConfig,
        output_dir: str,
        env_type: str,
        env_sub_type: str,
        event_manager: EventManager,
    ):
        """Initialize IEnvironmentPlugin."""
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
        """Environment classification method for plugin orchestration.

        Returns True for network environments (Docker Compose, Shadow NS) that provide
        network isolation and service orchestration. Returns False for execution
        environments (strace, Valgrind) that wrap individual process execution.

        This classification drives framework behavior:
        - Network environments coordinate multiple services with network topology
        - Execution environments enhance single service execution with analysis tools

        Returns:
            bool: True if this is a network environment, False for execution environment
        """
        pass

    def set_event_manager(self, event_manager: EventManager):
        """Update event manager reference for dynamic event system integration.

        Args:
            event_manager: The event manager instance for framework-wide event coordination
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
        """Orchestrate complete environment setup with integrated event tracking.

        This method coordinates the full environment initialization sequence:
        1. Store configuration references for environment operations
        2. Emit setup started event for monitoring and logging
        3. Execute environment-specific setup through update_environment()
        4. Emit completion event with success/failure status

        The setup process integrates service managers, execution environments,
        and configuration while maintaining event-driven visibility into the
        environment lifecycle.

        Args:
            services_managers: List of service management instances for coordination
            test_config: Test case configuration defining services and protocols
            global_config: Framework-wide configuration and settings
            timestamp: Unique timestamp for this test execution session
            plugin_manager: Plugin management system for dynamic loading
            execution_environment: List of execution analysis environments to integrate

        Raises:
            Exception: Any setup failure, with error details captured in failure event
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
        """Environment-specific service deployment implementation.

        This method contains the core logic for deploying services within
        the specific environment context (Docker containers, Shadow processes, etc.).
        Called during the setup phase after configuration is established.

        Implementation varies by environment type:
        - Docker Compose: docker-compose up with service coordination
        - Shadow NS: Shadow process spawning with network topology
        - Execution: Process wrapper setup with analysis tool integration
        """
        pass

    @abstractmethod
    def teardown_environment(self) -> None:
        """Orchestrate complete environment cleanup with event tracking.

        Coordinates orderly environment shutdown including:
        1. Service termination and resource cleanup
        2. Output collection and finalization
        3. Event emission for lifecycle tracking
        4. Error handling for partial teardown scenarios

        Must be implemented to ensure proper resource deallocation
        regardless of setup success/failure state.
        """
        pass

    @abstractmethod
    def _do_teardown_environment(self) -> None:
        """Environment-specific teardown implementation.

        Contains the core cleanup logic for the specific environment type:
        - Docker Compose: Container stops, network cleanup, volume removal
        - Shadow NS: Process termination, simulation state cleanup
        - Execution: Analysis tool finalization, output collection

        Called by teardown_environment() after event emission setup.
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
        """Apply configuration updates to active environment.

        Handles dynamic reconfiguration of environment settings during
        test execution, including service updates, network changes,
        and execution environment modifications.

        Args:
            execution_environment: Updated execution analysis environments
            global_config: Current framework-wide configuration
            plugin_manager: Plugin management system reference
            services_managers: Updated service management instances
            test_config: Current test case configuration
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
        """Bootstrap environment with framework integration.

        Performs initial environment preparation including:
        1. Configuration validation and processing
        2. Output directory structure creation
        3. Template and resource preparation
        4. Framework integration validation

        Called before setup_environment() to establish basic environment
        readiness for test execution.

        Args:
            test_config: Test configuration defining services and protocols
            output_dir: Root directory for environment output artifacts
            event_manager: Framework event system for integration
            global_config: Framework-wide configuration settings

        Returns:
            bool: True if initialization succeeded and environment is ready,
                 False if critical initialization failures occurred
        """
        pass
