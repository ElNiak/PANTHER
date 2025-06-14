from abc import ABC
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from panther.plugins.plugin_manager import PluginManager

from omegaconf import OmegaConf

from panther.core.observer.management.event_manager import EventManager
from panther.config.config_experiment_schema import TestConfig
from panther.config.config_global_schema import GlobalConfig
from panther.plugins.environments.execution_environment.memcheck.config_schema import (
    MemcheckConfig,
)
from panther.plugins.environments.execution_environment.execution_environment_interface import (
    IExecutionEnvironment,
)

# PluginManager functionality now integrated into PluginManager
from panther.plugins.services.services_interface import IServiceManager
from panther.plugins.plugin_decorators import register_plugin
from panther.core.utils.environment_utils import ExecutionEnvironmentMixin
from panther.core.outputs.execution_environment_mixins import (
    StandardOutputCollectorMixin,
    CommandModificationMixin,
)


@register_plugin(
    plugin_type="environment",
    name="memcheck",
    version="1.0.0",
    description="Memory error detection using Valgrind Memcheck",
    author="PANTHER Team",
    capabilities=["memory_error_detection", "leak_detection", "use_after_free", "buffer_overflow"],
    external_dependencies=["valgrind>=3.15"],
)
class MemcheckEnvironment(
    ExecutionEnvironmentMixin,
    StandardOutputCollectorMixin,
    CommandModificationMixin,
    IExecutionEnvironment,
    ABC,
):
    """
    MemcheckEnvironment provides an execution environment for running services under Valgrind's Memcheck tool.
    This class is responsible for configuring and setting up the environment to perform memory checking on services,
    using Valgrind's Memcheck. It manages the environment configuration, service managers, test and global configurations,
    and integrates with an event manager and plugin manager.
    Attributes:
        global_config (GlobalConfig): The global configuration for the environment.
        env_config_to_test (MemcheckConfig): The specific Memcheck configuration to use for testing.
        services_managers (list[IServiceManager]): List of service managers to be managed in this environment.
        test_config (TestConfig): The test configuration for the current test run.
        plugin_manager (PluginManager): Loader for plugins used in the environment.
    Methods:
        __init__(env_config_to_test, output_dir, env_type, env_sub_type, event_manager):
            Initializes the MemcheckEnvironment with the provided configuration and managers.
        setup_environment(services_managers, test_config, global_config, timestamp, plugin_manager):
            Sets up the environment by configuring service managers, test and global configurations, and plugin manager.
            Also prepares the services to run under Memcheck.
        to_command(pid=None) -> str:
            Generates the Valgrind Memcheck command string to be used for running or attaching to a process.
        __repr__():
            Returns a string representation of the MemcheckEnvironment instance.
    """

    def __init__(
        self,
        env_config_to_test: MemcheckConfig,
        output_dir: str,
        env_type: str,
        env_sub_type: str,
        event_manager: EventManager,
    ):
        """
        Initializes the Memcheck environment with the provided configuration and parameters.

        Args:
            env_config_to_test (MemcheckConfig): The configuration object for the environment to be tested.
            output_dir (str): The directory where output files will be stored.
            env_type (str): The type of the environment.
            env_sub_type (str): The subtype of the environment.
            event_manager (EventManager): The event manager instance for handling events.
        """
        super().__init__(env_config_to_test, output_dir, env_type, env_sub_type, event_manager)
        # Use standardized environment initialization
        self.standardized_environment_initialization(
            env_config_to_test, output_dir, env_type, env_sub_type, event_manager
        )

    def setup_environment(
        self,
        services_managers: list[IServiceManager],
        test_config: TestConfig,
        global_config: GlobalConfig,
        timestamp: str,
        plugin_manager: "PluginManager",
    ):
        """
        Sets up the execution environment for the test by configuring service managers and logging configuration details.

        Args:
            services_managers (list[IServiceManager]): List of service manager instances to be configured.
            test_config (TestConfig): The test-specific configuration object.
            global_config (GlobalConfig): The global configuration object.
            timestamp (str): Timestamp string for the current test run.
            plugin_manager (PluginManager): Loader for managing plugins.

        Side Effects:
            - Updates each service manager's `run_cmd` dictionary by appending the command generated by `self.to_command()` to the "pre_run_cmds" list.
            - Logs detailed configuration and command information for debugging purposes.
            - Sets instance attributes for later use.
        """
        # Use standardized setup from mixin
        self.setup_execution_environment(
            services_managers, test_config, global_config, timestamp, plugin_manager
        )

        for service in self.services_managers:
            self.logger.debug("Service cmds before memcheck modification: %s", service.run_cmd)
            service_name = getattr(service, "service_name", service.__class__.__name__)

            # Use ServiceCommandBuilder for proper command building
            from panther.core.command_processor.command_builder import ServiceCommandBuilder
            from panther.plugins.protocols.config_schema import RoleEnum

            # Get the service role
            service_role = getattr(service, "role", RoleEnum.server)

            # Create command builder
            command_builder = ServiceCommandBuilder(service_role)

            # Generate output file path
            output_file = f"/app/logs/{service_name}_memcheck_{timestamp}.log"
            self.register_output_file("memcheck", output_file, service_name)

            # Build memcheck command for wrapping the main command execution
            memcheck_cmd = self.to_command(output_file=output_file)

            # Add memcheck wrapper setup command using the proper add_command method
            wrapper_setup_cmd = f"""
if [ -z "$EXEC_ENV_WRAPPERS" ]; then
    export EXEC_ENV_WRAPPERS="{memcheck_cmd}"
else
    export EXEC_ENV_WRAPPERS="{memcheck_cmd} $EXEC_ENV_WRAPPERS"
fi
echo "Added memcheck wrapper: {memcheck_cmd}" >> /app/logs/{service_name}_exec_env_setup.log
""".strip()

            # Use CommandBuilder to add the command with proper metadata
            command_builder.add_command(
                command=wrapper_setup_cmd,
                description=f"Setup memcheck wrapper for {service_name}",
                is_multiline=True,
                is_critical=False,  # Don't fail if memcheck setup fails
                environment={"MEMCHECK_OUTPUT_FILE": output_file},
            )

            # Process the commands through CommandProcessor
            processed_commands = command_builder.process_commands()

            # The processed commands are now structured properly
            # We need to add them to the service's pre_run_cmds
            if processed_commands:
                # The processed_commands is a list of command dictionaries
                # We need to extract the actual command strings
                memcheck_commands = []
                for cmd_dict in processed_commands:
                    # Extract the command from the processed structure
                    if isinstance(cmd_dict, dict) and "command" in cmd_dict:
                        memcheck_commands.append(cmd_dict["command"])
                    else:
                        # Fallback if structure is different
                        memcheck_commands.append(str(cmd_dict))

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
                    service, "memcheck_wrapper", {"pre_run_cmds": memcheck_commands}
                )

                self.logger.info("Enhanced service %s with memcheck wrapper setup", service_name)
                self.logger.debug("Applied modifications: %s", applied_modifications)
                self.logger.debug("Service cmds after memcheck modification: %s", service.run_cmd)
                if hasattr(service, "run_cmd"):
                    self.logger.debug(
                        "Pre-run commands after modification: %s",
                        service.run_cmd.get("pre_run_cmds", "ATTRIBUTE_NOT_FOUND"),
                    )
            else:
                self.logger.warning(
                    "No memcheck commands were processed for service %s", service_name
                )

        self.logger.debug("Test Config: %s", OmegaConf.to_yaml(self.test_config))
        self.logger.debug("Global Config: %s", OmegaConf.to_yaml(self.global_config))

    def to_command(self, pid: int | None = None, output_file: str | None = None) -> str:
        """
        Generate the Valgrind Memcheck command for execution.
        :param pid: Optional process ID to attach to.
        :param output_file: Optional output file path.
        :return: Valgrind Memcheck command as a string.
        """
        # Use the existing configuration, don't create a new one
        command = [
            "valgrind",
            "--tool=memcheck",
            f"--leak-check={self.env_config_to_test.leak_check}",
            f"--leak-resolution={self.env_config_to_test.leak_resolution}",
            f"--show-leak-kinds={self.env_config_to_test.show_leak_kinds}",
            f"--errors-for-leak-kinds={self.env_config_to_test.errors_for_leak_kinds}",
            "--child-silent-after-fork=yes",
        ]

        # Track origins if enabled
        if self.env_config_to_test.track_origins:
            command.append("--track-origins=yes")

        # Output format
        if self.env_config_to_test.output_format == "xml":
            command.append("--xml=yes")
            if output_file:
                command.append(f"--xml-file={output_file}")
        else:
            if output_file:
                command.append(f"--log-file={output_file}")

        # Suppressions
        if self.env_config_to_test.generate_suppressions:
            command.append("--gen-suppressions=all")

        if self.env_config_to_test.suppression_file:
            command.append(f"--suppressions={self.env_config_to_test.suppression_file}")

        # XML user comment
        if (
            self.env_config_to_test.xml_user_comment
            and self.env_config_to_test.output_format == "xml"
        ):
            command.append(f"--xml-user-comment={self.env_config_to_test.xml_user_comment}")

        # Additional parameters
        if self.env_config_to_test.additional_parameters:
            command.extend(self.env_config_to_test.additional_parameters)

        # Attach to specific PID if provided
        if pid:
            command.append(f"--pid={pid}")

        return " ".join(command)

    def initialize(self, test_config, output_dir, event_manager, global_config):
        """
        Initialize the memcheck environment with configuration settings.

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
            self.logger.debug("MemcheckEnvironment initialized successfully")
            return True
        except Exception as e:
            self.logger.error("Failed to initialize MemcheckEnvironment: %s", e)
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
        Implementation of environment setup for memcheck (from parent interface).

        Args:
            services_managers: List of service managers
            test_config: Test configuration
            global_config: Global configuration
            timestamp: Timestamp for this execution
            plugin_manager: Plugin manager instance
            execution_environment: List of execution environments (unused for memcheck)
        """
        # execution_environment is not needed for memcheck setup but required by interface
        _ = execution_environment
        # Delegate to the concrete implementation
        self.setup_environment(
            services_managers, test_config, global_config, timestamp, plugin_manager
        )

    def _do_deploy_services(self):
        """
        Implementation of service deployment for memcheck.

        For execution environments like memcheck, deployment is typically handled
        by the network environment, so this is usually a no-op.
        """
        self.logger.debug("MemcheckEnvironment deployment: no specific deployment needed")

    def _do_teardown_environment(self):
        """
        Implementation of environment teardown for memcheck.
        """
        self.logger.debug("MemcheckEnvironment teardown: cleaning up memcheck resources")
        # No specific cleanup needed for memcheck

    def handle_event(self, event):
        """
        Handle events sent to this execution environment.

        Args:
            event: The event to handle
        """
        event_type = type(event).__name__
        self.logger.debug("MemcheckEnvironment received event: %s", event_type)

        # Handle environment-specific events if needed
        if event_type == "ServiceStartedEvent":
            self.logger.debug("Service started, memcheck should be active")
        elif event_type == "ServiceStoppedEvent":
            self.logger.debug("Service stopped, memcheck collection complete")
        else:
            self.logger.debug("Unhandled event type: %s", event_type)

    def __repr__(self):
        return (
            f"MemcheckEnvironment(env_config_to_test={self.env_config_to_test}, "
            f"output_dir={self.output_dir}, event_manager={self.event_manager}, "
            f"services_managers={self.services_managers}, test_config={self.test_config})"
        )
