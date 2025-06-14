from abc import ABC
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

from omegaconf import OmegaConf

from panther.core.observer.management.event_manager import EventManager
from panther.plugins.environments.execution_environment.iterations.config_schema import (
    IterationsConfig,
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
    name="iterations",
    version="1.0.0",
    description="Multiple test iterations execution environment",
    author="PANTHER Team",
    capabilities=["repeated_testing", "statistical_analysis", "performance_variance"],
    external_dependencies=[],
)
class IterationsEnvironment(
    ExecutionEnvironmentMixin,
    StandardOutputCollectorMixin,
    CommandModificationMixin,
    IExecutionEnvironment,
    ABC,
):
    """
    IterationsEnvironment is a class that sets up and manages an execution environment for running multiple test iterations.

    Attributes:
        global_config (GlobalConfig): The global configuration for the environment.
        env_config_to_test (IterationsConfig): The specific configuration for the iterations environment to test.
        services_managers (list[IServiceManager]): List of service managers to handle services within the environment.
        test_config (TestConfig): Configuration for the test being executed.
        plugin_manager (PluginManager): Loader for plugins used in the environment.

    Methods:
        __init__(env_config_to_test: IterationsConfig, output_dir: str, env_type: str, env_sub_type: str, event_manager: EventManager):
            Initializes the IterationsEnvironment with the given configuration and parameters.

        setup_environment(services_managers: list[IServiceManager], test_config: TestConfig, global_config: GlobalConfig, timestamp: str, plugin_manager: "PluginManager"):
            Sets up the environment with the provided service managers, test configuration, global configuration, and plugin manager.

        to_command(service_name: str | None = None, output_file: str | None = None) -> str:
            Generates the iterations wrapper command for execution. Returns the bash loop wrapper for multiple iterations.

        __repr__() -> str:
            Returns a string representation of the IterationsEnvironment instance.
    """

    # TODO enforce config in environment
    def __init__(
        self,
        env_config_to_test: IterationsConfig,
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

    def initialize(self, test_config, output_dir, event_manager, global_config):
        """
        Initialize the iterations environment with configuration settings.

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
            self.logger.debug("IterationsEnvironment initialized successfully")
            return True
        except Exception as e:
            self.logger.error("Failed to initialize IterationsEnvironment: %s", e)
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
            self.logger.debug("Service cmds before iterations modification: %s", service.run_cmd)
            service_name = getattr(service, "service_name", service.__class__.__name__)

            # Use ServiceCommandBuilder for proper command building
            from panther.core.command_processor.command_builder import ServiceCommandBuilder
            from panther.plugins.protocols.config_schema import RoleEnum

            # Get the service role
            service_role = getattr(service, "role", RoleEnum.server)

            # Create command builder
            command_builder = ServiceCommandBuilder(service_role)

            # Generate output file path
            output_file = f"/app/logs/{service_name}_iterations_{timestamp}.log"
            self.register_output_file("iterations", output_file, service_name)

            # Get the iterations configuration
            iterations = self.env_config_to_test.iterations if self.env_config_to_test else 1

            # Only set up iterations wrapper if we have more than 1 iteration
            if iterations > 1:
                delay = (
                    self.env_config_to_test.delay_between_iterations
                    if self.env_config_to_test
                    else 0
                )

                # Build iterations command for wrapping around the command execution
                iterations_cmd = self.to_command(service_name, output_file)

                # Build wrapper setup command following the strace pattern
                wrapper_setup_cmd = f"""
# Create iterations wrapper script
cat > /tmp/iterations_wrapper_{service_name}.sh << 'ITER_EOF'
#!/bin/bash
iterations_log="{output_file}"
iterations_count={iterations}
delay_between={delay}

for iteration in $(seq 1 $iterations_count); do
    echo "Starting iteration $iteration of $iterations_count" >> "$iterations_log"
    if [ $iteration -gt 1 ] && [ $delay_between -gt 0 ]; then
        echo "Waiting $delay_between seconds between iterations..." >> "$iterations_log"
        sleep $delay_between
    fi

    # Execute the wrapped command
    "$@"
    exit_code=$?

    echo "Completed iteration $iteration of $iterations_count (exit code: $exit_code)" >> "$iterations_log"

    # If command failed, should we continue? For now, continue iterations
    if [ $exit_code -ne 0 ]; then
        echo "Iteration $iteration failed with exit code $exit_code, continuing..." >> "$iterations_log"
    fi
done

echo "All iterations completed" >> "$iterations_log"
ITER_EOF

chmod +x /tmp/iterations_wrapper_{service_name}.sh

if [ -z "$EXEC_ENV_WRAPPERS" ]; then
    export EXEC_ENV_WRAPPERS="/tmp/iterations_wrapper_{service_name}.sh"
else
    export EXEC_ENV_WRAPPERS="/tmp/iterations_wrapper_{service_name}.sh $EXEC_ENV_WRAPPERS"
fi
echo "Added iterations wrapper for {iterations} iterations" >> /app/logs/{service_name}_exec_env_setup.log
""".strip()

                # Use CommandBuilder to add the command with proper metadata
                command_builder.add_command(
                    command=wrapper_setup_cmd,
                    description=f"Setup iterations wrapper for {service_name} ({iterations} iterations)",
                    is_multiline=True,
                    is_critical=False,  # Don't fail if iterations setup fails
                    environment={"ITERATIONS_OUTPUT_FILE": output_file},
                )

                # Process the commands through CommandProcessor
                processed_commands = command_builder.process_commands()

                # The processed commands are now structured properly
                # We need to add them to the service's pre_run_cmds
                if processed_commands:
                    # The processed_commands is a list of command dictionaries
                    # We need to extract the actual command strings
                    iterations_commands = []
                    for cmd_dict in processed_commands:
                        # Extract the command from the processed structure
                        if isinstance(cmd_dict, dict) and "command" in cmd_dict:
                            iterations_commands.append(cmd_dict["command"])
                        else:
                            # Fallback if structure is different
                            iterations_commands.append(str(cmd_dict))

                    # Debug: Check if service has run_cmd attribute and print before modification
                    self.logger.debug("Service object type: %s", type(service))
                    self.logger.debug(
                        "Service has run_cmd attribute: %s", hasattr(service, "run_cmd")
                    )
                    if hasattr(service, "run_cmd"):
                        self.logger.debug("Service run_cmd type: %s", type(service.run_cmd))
                        self.logger.debug(
                            "Pre-run commands before modification: %s",
                            service.run_cmd.get("pre_run_cmds", "ATTRIBUTE_NOT_FOUND"),
                        )

                    # Use the CommandModificationMixin to properly modify the service
                    applied_modifications = self.modify_service_commands(
                        service, "iterations_wrapper", {"pre_run_cmds": iterations_commands}
                    )

                    self.logger.info(
                        "Enhanced service %s with iterations wrapper setup for %d iterations",
                        service_name,
                        iterations,
                    )
                    self.logger.debug("Applied modifications: %s", applied_modifications)
                    self.logger.debug(
                        "Service cmds after iterations modification: %s", service.run_cmd
                    )
                    if hasattr(service, "run_cmd"):
                        self.logger.debug(
                            "Pre-run commands after modification: %s",
                            service.run_cmd.get("pre_run_cmds", "ATTRIBUTE_NOT_FOUND"),
                        )
                else:
                    self.logger.warning(
                        "No iterations commands were processed for service %s", service_name
                    )
            else:
                self.logger.info(
                    "Service %s configured for single iteration, no wrapper needed", service_name
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
        Implementation of environment setup for iterations (from parent interface).

        Args:
            services_managers: List of service managers
            test_config: Test configuration
            global_config: Global configuration
            timestamp: Timestamp for this execution
            plugin_manager: Plugin manager instance
            execution_environment: List of execution environments (unused for iterations)
        """
        # execution_environment is not needed for iterations setup but required by interface
        _ = execution_environment
        # Delegate to the concrete implementation
        self.setup_environment(
            services_managers, test_config, global_config, timestamp, plugin_manager
        )

    def _do_deploy_services(self):
        """
        Implementation of service deployment for iterations.

        For execution environments like iterations, deployment is typically handled
        by the network environment, so this is usually a no-op.
        """
        self.logger.debug("IterationsEnvironment deployment: no specific deployment needed")

    def _do_teardown_environment(self):
        """
        Implementation of environment teardown for iterations.
        """
        self.logger.debug("IterationsEnvironment teardown: cleaning up iterations resources")
        # No specific cleanup needed for iterations

    def handle_event(self, event):
        """
        Handle events sent to this execution environment.

        Args:
            event: The event to handle
        """
        event_type = type(event).__name__
        self.logger.debug("IterationsEnvironment received event: %s", event_type)

        # Handle environment-specific events if needed
        if event_type == "ServiceStartedEvent":
            self.logger.debug("Service started, iterations should be active")
        elif event_type == "ServiceStoppedEvent":
            self.logger.debug("Service stopped, iterations collection complete")
        else:
            self.logger.debug("Unhandled event type: %s", event_type)

    def to_command(self, service_name: str | None = None, output_file: str | None = None) -> str:
        """
        Generate the iterations wrapper script path.

        Args:
            service_name: Name of the service for logging purposes
            output_file: Optional output file path for iteration logs

        Returns:
            Path to the iterations wrapper script
        """
        iterations = self.env_config_to_test.iterations if self.env_config_to_test else 1

        if iterations <= 1:
            # No wrapper needed for single iteration
            return ""

        # Return the path to the wrapper script that will be created
        service_part = f"_{service_name}" if service_name else ""
        return f"/tmp/iterations_wrapper{service_part}.sh"

    def __repr__(self):
        return (
            f"IterationsEnvironment(env_config_to_test={self.env_config_to_test}, "
            f"output_dir={self.output_dir}, event_manager={self.event_manager}, "
            f"services_managers={self.services_managers}, test_config={self.test_config})"
        )
