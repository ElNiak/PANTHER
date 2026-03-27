"""Base execution environment class that eliminates code duplication across execution environment plugins.

This module provides a standardized base class that combines all common mixins and interfaces,
implements boilerplate methods, and defines the template for execution environment plugins.
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

from panther.config.core.models.global_config import GlobalConfig
from panther.core.observer.management.event_manager import EventManager
from panther.core.outputs.output_environment_mixins import StandardOutputCollectorMixin
from panther.core.utils import log_omega_config_summary
from panther.core.utils.string_representation_mixin import StringRepresentationMixin
from panther.plugins.environments.environment_utils import EnvironmentUtilities
from panther.plugins.environments.execution_environment.execution_environment_interface import (
    IExecutionEnvironment,
)
from panther.plugins.services.services_interface import IServiceManager

if TYPE_CHECKING:
    from panther.config.core.models.experiment import TestConfig
    from panther.plugins.plugin_manager import PluginManager


class BaseExecutionEnvironment(
    StandardOutputCollectorMixin,
    IExecutionEnvironment,
    StringRepresentationMixin,
    ABC,
):
    """Base class for all execution environment plugins.

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
        """Initialize the base execution environment.

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
        # From EnvironmentPluginMixin
        self._environment_initialized = False
        self._output_directories = {}
        self._environment_state = "uninitialized"
        # From ExecutionEnvironmentMixin
        self.services_managers = []
        self.test_config = None
        self.global_config = None
        self.plugin_manager = None
        self.timestamp = None
        # Standardized environment initialization
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
        """Initialize the execution environment with configuration settings.

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

    # --- Plugin config helpers ---

    def _get_config_value(self, field_name: str, default: Any = None) -> Any:
        """Get a config value directly from env_config_to_test."""
        return getattr(self.env_config_to_test, field_name, default)

    def _do_deploy_services(self):
        """Implementation of service deployment.

        For execution environments, deployment is typically handled
        by the network environment, so this is usually a no-op.
        """
        self.logger.debug(
            f"{self.__class__.__name__} deployment: no specific deployment needed"
        )

    def _do_teardown_environment(self):
        """Implementation of environment teardown."""
        self.logger.debug(f"{self.__class__.__name__} teardown: cleaning up resources")

    def handle_event(self, event):
        """Handle events sent to this execution environment.

        Args:
            event: The event to handle
        """
        event_name = getattr(event, "name", type(event).__name__)
        entity_type = getattr(event, "entity_type", None)
        self.logger.debug(f"{self.__class__.__name__} received event: %s", event_name)
        if entity_type is not None and str(entity_type) != "service":
            self.logger.debug(
                "Ignoring non-service event: %s.%s", entity_type, event_name
            )
            return
        if event_name == "started":
            self.logger.debug(
                "Service started, environment monitoring should be active"
            )
        elif event_name == "stopped":
            self.logger.debug("Service stopped, environment collection complete")
        else:
            self.logger.debug("Unhandled event type: %s", event_name)

    def setup_environment(
        self,
        services_managers: List[IServiceManager],
        test_config: "TestConfig",
        global_config: GlobalConfig,
        timestamp: str,
        plugin_manager: "PluginManager",
    ):
        """Default implementation of environment setup.

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
        """Get output patterns specific to this execution environment.

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
        """Get additional patterns for discovering outputs.

        Override this in subclasses to provide custom discovery patterns.

        Returns:
            Dict mapping output types to lists of glob patterns
        """
        return {}

    @abstractmethod
    def _setup_plugin_specific_environment(
        self, services_managers: List[IServiceManager], timestamp: str
    ):
        """Plugin-specific environment setup logic.

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
        """Generate the environment-specific command.

        This method must be implemented by each plugin to provide its specific
        command generation logic.

        Returns:
            str: Command string for this environment
        """
        raise NotImplementedError(
            "Each plugin must implement its command generation logic"
        )

    # --- Command modification (inlined from CommandModificationMixin) ---

    def modify_service_commands(
        self, service, modification_type: str, modifications: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Modify service commands with proper event emission.

        Args:
            service: Service manager instance
            modification_type: Type of modification (e.g., 'command_wrapping')
            modifications: Dictionary of modifications to apply

        Returns:
            Dictionary of applied modifications
        """
        service_name = getattr(service, "service_name", service.__class__.__name__)
        self.logger.info(
            f"Modifying service {service_name} command with {modification_type} modifications: {modifications}"
        )
        self.logger.debug(
            f"CommandModificationMixin.modify_service_commands called for {service_name}"
        )
        self.logger.debug(
            f"Modification type: {modification_type}, Modifications: {modifications}"
        )

        # Emit start event
        if hasattr(self, "environment_emitter") and self.environment_emitter:
            self.environment_emitter.emit_environment_modification_started(
                environment_id=f"{self.env_sub_type}_{service_name}",
                environment_name=self.env_sub_type,
                environment_type="execution",
                target_service=service_name,
                modification_type=modification_type,
            )

        # Store original state
        original_state = {}

        # Apply modifications
        applied_modifications = {}

        for key, value in modifications.items():
            if key == "pre_run_cmds":
                # Store original state
                original_state["pre_run_cmds"] = service.run_cmd.get(
                    "pre_run_cmds", []
                ).copy()
                self.logger.debug(
                    f"Original pre_run_cmds: {original_state['pre_run_cmds']}"
                )
                self.logger.debug(f"Adding commands: {value}")
                # Apply modification
                current_cmds = service.run_cmd.get("pre_run_cmds", [])
                self.logger.debug(f"Current commands before append: {current_cmds}")
                service.run_cmd["pre_run_cmds"] = current_cmds + value
                self.logger.debug(
                    f"Commands after append: {service.run_cmd['pre_run_cmds']}"
                )
                applied_modifications["pre_run_cmds"] = service.run_cmd["pre_run_cmds"]

            elif key == "post_run_cmds":
                # Store original state
                original_state["post_run_cmds"] = service.run_cmd.get(
                    "post_run_cmds", []
                ).copy()
                # Apply modification
                service.run_cmd["post_run_cmds"] = (
                    service.run_cmd.get("post_run_cmds", []) + value
                )
                applied_modifications["post_run_cmds"] = service.run_cmd[
                    "post_run_cmds"
                ]

            elif key == "environment":
                # Ensure nested structure exists
                if "run_cmd" not in service.run_cmd:
                    service.run_cmd["run_cmd"] = {}
                if "command_env" not in service.run_cmd["run_cmd"]:
                    service.run_cmd["run_cmd"]["command_env"] = {}

                # Store original state
                original_state["environment"] = service.run_cmd["run_cmd"][
                    "command_env"
                ].copy()
                # Apply modification
                service.run_cmd["run_cmd"]["command_env"].update(value)
                applied_modifications["environment"] = service.run_cmd["run_cmd"][
                    "command_env"
                ]

        # Log the modifications
        if hasattr(self, "logger"):
            self.logger.debug(
                f"Applied {modification_type} modifications to {service_name}"
            )
            for key, value in applied_modifications.items():
                self.logger.debug(f"  {key}: {value}")

        # Emit completion event
        if hasattr(self, "environment_emitter") and self.environment_emitter:
            self.environment_emitter.emit_environment_modification_completed(
                environment_id=f"{self.env_sub_type}_{service_name}",
                environment_name=self.env_sub_type,
                environment_type="execution",
                modifications={
                    k: {
                        "original": original_state.get(k, {}),
                        "modified": applied_modifications.get(k, {}),
                    }
                    for k in modifications
                },
                modification_summary=f"Applied {modification_type} modifications",
            )

        return applied_modifications

    def wrap_command_with_tool(
        self, service, tool_command: str, output_file: str = None
    ) -> str:
        """Helper method to wrap a service command with a tool command.

        Args:
            service: Service manager instance
            tool_command: Tool command to wrap with
            output_file: Optional output file path

        Returns:
            Complete wrapped command
        """
        # Build the command
        if output_file:
            full_command = f"{tool_command} -o {output_file}"
        else:
            full_command = tool_command

        # Apply the modification
        self.modify_service_commands(
            service, "command_wrapping", {"pre_run_cmds": [full_command]}
        )

        return full_command

    # --- Environment plugin (inlined from EnvironmentPluginMixin) ---

    def standardized_environment_initialization(
        self,
        env_config_to_test: Any,
        output_dir: str,
        env_type: str,
        env_sub_type: str,
        event_manager=None,
    ) -> None:
        """Perform standardized environment plugin initialization.

        Args:
            env_config_to_test: Environment configuration
            output_dir: Output directory
            env_type: Environment type
            env_sub_type: Environment sub-type
            event_manager: Event manager instance
        """
        # Store basic attributes
        self.env_config_to_test = env_config_to_test
        # Ensure output_dir is always an absolute path
        self.output_dir = str(Path(output_dir).resolve())
        self.env_type = env_type
        self.env_sub_type = env_sub_type
        self.event_manager = event_manager

        # Set up output directories
        self._output_directories = EnvironmentUtilities.setup_output_directories(
            output_dir, env_sub_type
        )

        # Standard logging
        EnvironmentUtilities.standardize_environment_initialization(
            self.logger, env_type, env_sub_type
        )

        self._environment_initialized = True
        self._environment_state = "initialized"

    @property
    def environment_state(self) -> str:
        """Get the current environment state."""
        return self._environment_state

    @property
    def output_directories(self) -> Dict[str, Path]:
        """Get the output directories."""
        return self._output_directories

    def get_logs_directory(self) -> Path:
        """Get the logs directory path."""
        return self._output_directories.get("logs", Path(self.output_dir) / "logs")

    def get_results_directory(self) -> Path:
        """Get the results directory path."""
        return self._output_directories.get(
            "results", Path(self.output_dir) / "results"
        )

    def get_artifacts_directory(self) -> Path:
        """Get the artifacts directory path."""
        return self._output_directories.get(
            "artifacts", Path(self.output_dir) / "artifacts"
        )

    def update_environment_state(self, new_state: str) -> None:
        """Update the environment state.

        Args:
            new_state: New state value
        """
        old_state = self._environment_state
        self._environment_state = new_state
        self.logger.debug(f"Environment state changed: {old_state} -> {new_state}")

    # --- Execution environment (inlined from ExecutionEnvironmentMixin) ---

    def setup_execution_environment(
        self,
        services_managers: List[Any],
        test_config: Any,
        global_config: Any,
        timestamp: str,
        plugin_manager: Any,
    ) -> None:
        """Set up execution environment with service managers and configurations.

        Args:
            services_managers: List of service managers
            test_config: Test configuration
            global_config: Global configuration
            timestamp: Execution timestamp
            plugin_manager: Plugin loader instance
        """
        self.services_managers = services_managers
        self.test_config = test_config
        self.global_config = global_config
        self.timestamp = timestamp
        self.plugin_manager = plugin_manager

        self.update_environment_state("setup_in_progress")

        # Log setup information
        self.logger.info(
            f"Setting up execution environment with {len(services_managers)} services"
        )
        self.log_operation_start(
            "execution environment setup", service_count=len(services_managers)
        )

    def get_service_managers(self) -> List[Any]:
        """Get the list of service managers."""
        return self.services_managers

    def get_service_manager_by_name(self, name: str) -> Optional[Any]:
        """Get a service manager by name.

        Args:
            name: Service manager name

        Returns:
            Service manager instance or None
        """
        for service_manager in self.services_managers:
            if (
                hasattr(service_manager, "service_name")
                and service_manager.service_name == name
            ):
                return service_manager
            elif (
                hasattr(service_manager, "implementation_name")
                and service_manager.implementation_name == name
            ):
                return service_manager
        return None

    def _get_key_attributes(self) -> Dict[str, Any]:
        """Get key attributes for string representation."""
        attrs = super()._get_key_attributes()

        # Show service count instead of full list
        if hasattr(self, "services_managers") and self.services_managers:
            attrs["services"] = len(self.services_managers)

        return attrs
