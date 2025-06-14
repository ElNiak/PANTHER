from abc import ABC
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

from omegaconf import OmegaConf

from panther.core.observer.management.event_manager import EventManager
from panther.plugins.environments.execution_environment.strace.config_schema import (
    StraceConfig,
)
from panther.plugins.environments.execution_environment.execution_environment_interface import (
    IExecutionEnvironment,
)

# PluginManager functionality now integrated into PluginManager
from panther.plugins.plugin_decorators import register_plugin
from panther.core.utils.environment_utils import ExecutionEnvironmentMixin
from panther.core.outputs.execution_environment_mixins import (
    StandardOutputCollectorMixin,
    CommandModificationMixin,
)


@register_plugin(
    plugin_type="environment",
    name="strace",
    version="1.0.0",
    description="System call tracing execution environment",
    author="PANTHER Team",
    capabilities=["syscall_tracing", "performance_analysis", "debugging"],
    external_dependencies=["strace>=4.0"],
)
class StraceEnvironment(
    ExecutionEnvironmentMixin,
    StandardOutputCollectorMixin,
    CommandModificationMixin,
    IExecutionEnvironment,
    ABC,
):
    """
    StraceEnvironment is a class that sets up and manages an execution environment using strace for system call tracing.

    Attributes:
        global_config (GlobalConfig): The global configuration for the environment.
        env_config_to_test (StraceConfig): The specific configuration for the strace environment to test.
        services_managers (list[IServiceManager]): List of service managers to handle services within the environment.
        test_config (TestConfig): Configuration for the test being executed.
        plugin_manager (PluginManager): Loader for plugins used in the environment.

    Methods:
        __init__(env_config_to_test: StraceConfig, output_dir: str, env_type: str, env_sub_type: str, event_manager: EventManager):
            Initializes the StraceEnvironment with the given configuration and parameters.

        setup_environment(services_managers: list[IServiceManager], test_config: TestConfig, global_config: GlobalConfig, timestamp: str, plugin_manager: "PluginManager"):
            Sets up the environment with the provided service managers, test configuration, global configuration, and plugin manager.

        to_command(pid: int | None = None) -> str:
            Generates the strace command for execution. Optionally attaches to a specific process ID.

        __repr__() -> str:
            Returns a string representation of the StraceEnvironment instance.
    """

    # TODO enforce config in environment
    def __init__(
        self,
        env_config_to_test: StraceConfig,
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

    def to_command(self, pid: int | None = None, output_file: str | None = None) -> str:
        """
        Generate the strace command for execution.
        :param pid: Optional process ID to attach to.
        :param output_file: Optional output file path.
        :return: Strace command as a string.
        """
        excluded = ",".join(f"{syscall}" for syscall in self.env_config_to_test.excluded_syscalls)
        command = [
            self.env_config_to_test.strace_binary,
        ]

        # Include kernel stack if enabled
        if self.env_config_to_test.include_kernel_stack:
            command.append("-k")

        # Exclude specified syscalls
        if excluded:
            command.append(f'-e trace="!{excluded}"')

        # Attach to specific PID if provided
        if pid:
            command.extend(["-p", str(pid)])

        # Focus on network syscalls if enabled
        if self.env_config_to_test.trace_network_syscalls:
            command.append("-e trace=network")

        # File syscalls
        if self.env_config_to_test.trace_file_syscalls:
            command.append("-e trace=file")

        # Output format options
        if self.env_config_to_test.output_format == "verbose":
            command.append("-v")
        elif self.env_config_to_test.output_format == "raw":
            command.append("-x")

        # Decode file descriptors
        if self.env_config_to_test.decode_fds:
            command.append("-y")

        # Timestamps
        if self.env_config_to_test.timestamps:
            if self.env_config_to_test.timestamp_format == "relative":
                command.append("-r")
            elif self.env_config_to_test.timestamp_format == "time":
                command.append("-t")
            elif self.env_config_to_test.timestamp_format == "us":
                command.append("-ttt")

        # Follow children
        if self.env_config_to_test.trace_children:
            command.append("-f")

        # String limit
        if self.env_config_to_test.string_limit is not None:
            command.append(f"-s {self.env_config_to_test.string_limit}")

        # Stack traces
        if self.env_config_to_test.stack_traces:
            command.append("-k")

        # Error injection
        if self.env_config_to_test.inject_errors:
            command.append(f"-e inject={self.env_config_to_test.inject_errors}")

        # Add any additional parameters
        if self.env_config_to_test.additional_parameters:
            command.extend(self.env_config_to_test.additional_parameters)

        # Add output file
        if output_file:
            command.append(f"-o {output_file}")

        return " ".join(command)

    def initialize(self, test_config, output_dir, event_manager, global_config):
        """
        Initialize the strace environment with configuration settings.

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
            self.logger.debug("StraceEnvironment initialized successfully")
            return True
        except Exception as e:
            self.logger.error("Failed to initialize StraceEnvironment: %s", e)
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
            self.logger.debug("Service cmds before strace modification: %s", service.run_cmd)
            service_name = getattr(service, "service_name", service.__class__.__name__)

            # Use ServiceCommandBuilder for proper command building
            from panther.core.command_processor.command_builder import ServiceCommandBuilder
            from panther.plugins.protocols.config_schema import RoleEnum

            # Get the service role
            service_role = getattr(service, "role", RoleEnum.server)

            # Create command builder
            command_builder = ServiceCommandBuilder(service_role)

            # Generate output file path
            output_file = f"/app/logs/{service_name}_strace_{timestamp}.out"
            self.register_output_file("trace", output_file, service_name)

            # Build strace command for wrapping the main command execution
            strace_cmd = self.to_command(output_file=output_file)

            # Add strace wrapper setup command using the proper add_command method
            wrapper_setup_cmd = f"""
if [ -z "$EXEC_ENV_WRAPPERS" ]; then
    export EXEC_ENV_WRAPPERS="{strace_cmd}"
else
    export EXEC_ENV_WRAPPERS="{strace_cmd} $EXEC_ENV_WRAPPERS"
fi
echo "Added strace wrapper: {strace_cmd}" >> /app/logs/{service_name}_exec_env_setup.log
""".strip()

            # Use CommandBuilder to add the command with proper metadata
            command_builder.add_command(
                command=wrapper_setup_cmd,
                description=f"Setup strace wrapper for {service_name}",
                is_multiline=True,
                is_critical=False,  # Don't fail if strace setup fails
                environment={"STRACE_OUTPUT_FILE": output_file},
            )

            # Process the commands through CommandProcessor
            processed_commands = command_builder.process_commands()

            # The processed commands are now structured properly
            # We need to add them to the service's pre_run_cmds
            if processed_commands:
                # The processed_commands is a list of command dictionaries
                # We need to extract the actual command strings
                strace_commands = []
                for cmd_dict in processed_commands:
                    # Extract the command from the processed structure
                    if isinstance(cmd_dict, dict) and "command" in cmd_dict:
                        strace_commands.append(cmd_dict["command"])
                    else:
                        # Fallback if structure is different
                        strace_commands.append(str(cmd_dict))

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
                    service, "strace_wrapper", {"pre_run_cmds": strace_commands}
                )

                self.logger.info("Enhanced service %s with strace wrapper setup", service_name)
                self.logger.debug("Applied modifications: %s", applied_modifications)
                self.logger.debug("Service cmds after strace modification: %s", service.run_cmd)
                if hasattr(service, "run_cmd"):
                    self.logger.debug(
                        "Pre-run commands after modification: %s",
                        service.run_cmd.get("pre_run_cmds", "ATTRIBUTE_NOT_FOUND"),
                    )
            else:
                self.logger.warning(
                    "No strace commands were processed for service %s", service_name
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
        Implementation of environment setup for strace (from parent interface).

        Args:
            services_managers: List of service managers
            test_config: Test configuration
            global_config: Global configuration
            timestamp: Timestamp for this execution
            plugin_manager: Plugin manager instance
            execution_environment: List of execution environments (unused for strace)
        """
        # execution_environment is not needed for strace setup but required by interface
        _ = execution_environment
        # Delegate to the concrete implementation
        self.setup_environment(
            services_managers, test_config, global_config, timestamp, plugin_manager
        )

    def _do_deploy_services(self):
        """
        Implementation of service deployment for strace.

        For execution environments like strace, deployment is typically handled
        by the network environment, so this is usually a no-op.
        """
        self.logger.debug("StraceEnvironment deployment: no specific deployment needed")

    def _do_teardown_environment(self):
        """
        Implementation of environment teardown for strace.
        """
        self.logger.debug("StraceEnvironment teardown: cleaning up strace resources")
        # No specific cleanup needed for strace

    def handle_event(self, event):
        """
        Handle events sent to this execution environment.

        Args:
            event: The event to handle
        """
        event_type = type(event).__name__
        self.logger.debug("StraceEnvironment received event: %s", event_type)

        # Handle environment-specific events if needed
        if event_type == "ServiceStartedEvent":
            self.logger.debug("Service started, strace should be active")
        elif event_type == "ServiceStoppedEvent":
            self.logger.debug("Service stopped, strace collection complete")
        else:
            self.logger.debug("Unhandled event type: %s", event_type)

    def __repr__(self):
        return (
            f"StraceEnvironment(env_config_to_test={self.env_config_to_test}, "
            f"output_dir={self.output_dir}, event_manager={self.event_manager}, "
            f"services_managers={self.services_managers}, test_config={self.test_config})"
        )
