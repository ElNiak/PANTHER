from abc import ABC
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

from omegaconf import OmegaConf

from panther.core.observer.management.event_manager import EventManager
from panther.plugins.environments.execution_environment.helgrind.config_schema import (
    HelgrindConfig,
)
from panther.plugins.environments.execution_environment.execution_environment_interface import (
    IExecutionEnvironment,
)
from panther.plugins.plugin_decorators import register_plugin
from panther.core.utils.environment_utils import ExecutionEnvironmentMixin
from panther.core.outputs.execution_environment_mixins import (
    StandardOutputCollectorMixin,
    CommandModificationMixin,
)


@register_plugin(
    plugin_type="environment",
    name="helgrind",
    version="1.0.0",
    description="Thread error detection using Valgrind Helgrind",
    author="PANTHER Team",
    capabilities=[
        "race_detection",
        "deadlock_detection",
        "thread_safety",
        "synchronization_errors",
    ],
    external_dependencies=["valgrind>=3.15"],
)
class HelgrindEnvironment(
    ExecutionEnvironmentMixin,
    StandardOutputCollectorMixin,
    CommandModificationMixin,
    IExecutionEnvironment,
    ABC,
):
    """
    HelgrindEnvironment is a class that sets up and manages an execution environment using Valgrind Helgrind
    for thread error detection and synchronization analysis.

    Attributes:
        global_config (GlobalConfig): The global configuration for the environment.
        env_config_to_test (HelgrindConfig): The specific configuration for the Helgrind environment to test.
        services_managers (list[IServiceManager]): List of service managers to handle services within the environment.
        test_config (TestConfig): Configuration for the test being executed.
        plugin_manager (PluginManager): Loader for plugins used in the environment.

    Methods:
        __init__(env_config_to_test: HelgrindConfig, output_dir: str, env_type: str, env_sub_type: str, event_manager: EventManager):
            Initializes the HelgrindEnvironment with the given configuration and parameters.

        setup_environment(services_managers: list[IServiceManager], test_config: TestConfig, global_config: GlobalConfig, timestamp: str, plugin_manager: "PluginManager"):
            Sets up the environment with the provided service managers, test configuration, global configuration, and plugin manager.

        to_command(service_name: str, timestamp: str) -> str:
            Generates the valgrind helgrind command for execution.

        __repr__() -> str:
            Returns a string representation of the HelgrindEnvironment instance.
    """

    def __init__(
        self,
        env_config_to_test: HelgrindConfig,
        output_dir: str,
        env_type: str,
        env_sub_type: str,
        event_manager: EventManager,
    ):
        super().__init__(env_config_to_test, output_dir, env_type, env_sub_type, event_manager)
        # Use standardized environment initialization
        self.standardized_environment_initialization(
            env_config_to_test, output_dir, env_type, env_sub_type, event_manager
        )

    def to_command(self, service_name: str, timestamp: str, output_file: str | None = None) -> str:
        """
        Generate the valgrind helgrind command for execution.

        :param service_name: Name of the service being wrapped.
        :param timestamp: Timestamp for the output file.
        :param output_file: Optional output file path.
        :return: Valgrind helgrind command as a string.
        """
        command = [
            self.env_config_to_test.valgrind_binary,
            "--tool=helgrind",
        ]

        # Set output file
        if not output_file:
            output_file = f"/app/logs/{service_name}_helgrind_{timestamp}.log"
        command.append(f"--log-file={output_file}")

        # History level
        if self.env_config_to_test.history_level != "full":
            command.append(f"--history-level={self.env_config_to_test.history_level}")

        # Conflict cache size
        if self.env_config_to_test.conflict_cache_size != 1000000:
            command.append(f"--conflict-cache-size={self.env_config_to_test.conflict_cache_size}")

        # Lock order tracking
        if not self.env_config_to_test.track_lockorders:
            command.append("--track-lockorders=no")

        # Stack references checking
        if not self.env_config_to_test.check_stack_refs:
            command.append("--check-stack-refs=no")

        # Thread creation race ignoring
        if self.env_config_to_test.ignore_thread_creation:
            command.append("--ignore-thread-creation=yes")

        # Free is write
        if self.env_config_to_test.free_is_write:
            command.append("--free-is-write=yes")

        # Cache size
        if self.env_config_to_test.cache_size != 32:
            command.append(f"--cache-size={self.env_config_to_test.cache_size}")

        # Suppression file
        if self.env_config_to_test.suppression_file:
            command.append(f"--suppressions={self.env_config_to_test.suppression_file}")

        # Show below main
        if self.env_config_to_test.show_below_main:
            command.append("--show-below-main=yes")

        # Track file descriptors
        if self.env_config_to_test.track_fds:
            command.append("--track-fds=yes")

        # Timestamps
        if self.env_config_to_test.time_stamp:
            command.append("--time-stamp=yes")

        # Verbosity
        if self.env_config_to_test.verbosity > 1:
            command.append(f"-{'v' * self.env_config_to_test.verbosity}")

        # Output format
        if self.env_config_to_test.output_format == "xml":
            command.append("--xml=yes")
            command.append(f"--xml-file={output_file}.xml")

        # Additional parameters
        if self.env_config_to_test.additional_parameters:
            command.extend(self.env_config_to_test.additional_parameters)

        # Important: Always trace children for proper thread tracking
        command.append("--trace-children=yes")

        return " ".join(command)

    def initialize(self, test_config, output_dir, event_manager, global_config):
        """
        Initialize the helgrind environment with configuration settings.

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
            self.logger.debug("HelgrindEnvironment initialized successfully")
            return True
        except Exception as e:
            self.logger.error("Failed to initialize HelgrindEnvironment: %s", e)
            return False

    def setup_environment(
        self, services_managers, test_config, global_config, timestamp, plugin_manager
    ):
        """
        Sets up the required environment before running experiments.

        Args:
            services_managers: List of service managers
            test_config: Test configuration
            global_config: Global configuration
            timestamp: Timestamp for this execution
            plugin_manager: Plugin manager instance
        """
        # Use the existing setup_environment logic
        self.setup_execution_environment(
            services_managers, test_config, global_config, timestamp, plugin_manager
        )

        for service in self.services_managers:
            self.logger.debug("Service cmds before helgrind modification: %s", service.run_cmd)
            service_name = getattr(service, "service_name", service.__class__.__name__)

            # Use ServiceCommandBuilder for proper command building
            from panther.core.command_processor.command_builder import ServiceCommandBuilder
            from panther.plugins.protocols.config_schema import RoleEnum

            # Get the service role
            service_role = getattr(service, "role", RoleEnum.server)

            # Create command builder
            command_builder = ServiceCommandBuilder(service_role)

            # Generate output file path
            output_file = f"/app/logs/{service_name}_helgrind_{timestamp}.log"
            self.register_output_file("helgrind_log", output_file, service_name)

            # Register XML output if enabled
            if self.env_config_to_test.output_format == "xml":
                xml_file = f"{output_file}.xml"
                self.register_output_file("helgrind_xml", xml_file, service_name)

            # Build helgrind command for wrapping the main command execution
            helgrind_cmd = self.to_command(service_name, timestamp, output_file)

            # Add helgrind wrapper setup command using the proper add_command method
            wrapper_setup_cmd = f"""
if [ -z "$EXEC_ENV_WRAPPERS" ]; then
    export EXEC_ENV_WRAPPERS="{helgrind_cmd}"
else
    export EXEC_ENV_WRAPPERS="{helgrind_cmd} $EXEC_ENV_WRAPPERS"
fi
echo "Added helgrind wrapper: {helgrind_cmd}" >> /app/logs/{service_name}_exec_env_setup.log
""".strip()

            # Use CommandBuilder to add the command with proper metadata
            command_builder.add_command(
                command=wrapper_setup_cmd,
                description=f"Setup helgrind wrapper for {service_name}",
                is_multiline=True,
                is_critical=False,  # Don't fail if helgrind setup fails
                environment={"HELGRIND_OUTPUT_FILE": output_file},
            )

            # Process the commands through CommandProcessor
            processed_commands = command_builder.process_commands()

            # The processed commands are now structured properly
            # We need to add them to the service's pre_run_cmds
            if processed_commands:
                # The processed_commands is a list of command dictionaries
                # We need to extract the actual command strings
                helgrind_commands = []
                for cmd_dict in processed_commands:
                    # Extract the command from the processed structure
                    if isinstance(cmd_dict, dict) and "command" in cmd_dict:
                        helgrind_commands.append(cmd_dict["command"])
                    else:
                        # Fallback if structure is different
                        helgrind_commands.append(str(cmd_dict))

                # Debug: Check if service has run_cmd attribute and print before modification
                self.logger.debug("Service object type: %s", type(service))
                self.logger.debug("Service has run_cmd attribute: %s", hasattr(service, "run_cmd"))
                if hasattr(service, "run_cmd"):
                    self.logger.debug("Service run_cmd type: %s", type(service.run_cmd))
                    self.logger.debug(
                        "Pre-run commands before modification: %s",
                        service.run_cmd.get("pre_run_cmds", "ATTRIBUTE_NOT_FOUND"),
                    )

                # Use the CommandModificationMixin to properly modify the service
                applied_modifications = self.modify_service_commands(
                    service, "helgrind_wrapper", {"pre_run_cmds": helgrind_commands}
                )

                self.logger.info("Enhanced service %s with helgrind wrapper setup", service_name)
                self.logger.debug("Applied modifications: %s", applied_modifications)
                self.logger.debug("Service cmds after helgrind modification: %s", service.run_cmd)
                if hasattr(service, "run_cmd"):
                    self.logger.debug(
                        "Pre-run commands after modification: %s",
                        service.run_cmd.get("pre_run_cmds", "ATTRIBUTE_NOT_FOUND"),
                    )
            else:
                self.logger.warning(
                    "No helgrind commands were processed for service %s", service_name
                )

        self.logger.debug("Test Config: %s", OmegaConf.to_yaml(self.test_config))
        self.logger.debug("Global Config: %s", OmegaConf.to_yaml(self.global_config))

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
        Implementation of environment setup for helgrind (from parent interface).

        Args:
            services_managers: List of service managers
            test_config: Test configuration
            global_config: Global configuration
            timestamp: Timestamp for this execution
            plugin_manager: Plugin manager instance
            execution_environment: List of execution environments (unused for helgrind)
        """
        # execution_environment is not needed for helgrind setup but required by interface
        _ = execution_environment
        # Delegate to the concrete implementation
        self.setup_environment(
            services_managers, test_config, global_config, timestamp, plugin_manager
        )

    def _do_deploy_services(self):
        """
        Implementation of service deployment for helgrind.

        For execution environments like helgrind, deployment is typically handled
        by the network environment, so this is usually a no-op.
        """
        self.logger.debug("HelgrindEnvironment deployment: no specific deployment needed")

    def _do_teardown_environment(self):
        """
        Implementation of environment teardown for helgrind.
        """
        self.logger.debug("HelgrindEnvironment teardown: cleaning up helgrind resources")
        # No specific cleanup needed for helgrind

    def handle_event(self, event):
        """
        Handle events sent to this execution environment.

        Args:
            event: The event to handle
        """
        event_type = type(event).__name__
        self.logger.debug("HelgrindEnvironment received event: %s", event_type)

        # Handle environment-specific events if needed
        if event_type == "ServiceStartedEvent":
            self.logger.debug("Service started, helgrind should be active")
        elif event_type == "ServiceStoppedEvent":
            self.logger.debug("Service stopped, helgrind collection complete")
        else:
            self.logger.debug("Unhandled event type: %s", event_type)

    def __repr__(self):
        return (
            f"HelgrindEnvironment(env_config_to_test={self.env_config_to_test}, "
            f"output_dir={self.output_dir}, event_manager={self.event_manager}, "
            f"services_managers={self.services_managers}, test_config={self.test_config})"
        )
