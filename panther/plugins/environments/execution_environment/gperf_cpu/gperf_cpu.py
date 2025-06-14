from abc import ABC
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from panther.plugins.plugin_manager import PluginManager

from omegaconf import OmegaConf
from panther.core.observer.management.event_manager import EventManager
from panther.config.config_experiment_schema import TestConfig
from panther.config.config_global_schema import GlobalConfig
from panther.plugins.environments.execution_environment.gperf_cpu.config_schema import (
    GperfCpuConfig,
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
    name="gperf_cpu",
    version="1.0.0",
    description="CPU profiling execution environment using Google Performance Tools",
    author="PANTHER Team",
    capabilities=["cpu_profiling", "performance_analysis", "hotspot_detection"],
    external_dependencies=["gperf"],
)
class GperfCpuEnvironment(
    ExecutionEnvironmentMixin,
    StandardOutputCollectorMixin,
    CommandModificationMixin,
    IExecutionEnvironment,
    ABC,
):
    """
    GperfCpuEnvironment is a class that sets up and manages the execution environment
    for CPU profiling using gperf.

    Attributes:
        env_config_to_test (GperfCpuConfig): Configuration specific to the environment being tested.
        output_dir (str): Directory where output files will be stored.
        env_type (str): Type of the environment.
        env_sub_type (str): Sub-type of the environment.
        event_manager (EventManager): Manager for handling events.
        global_config (GlobalConfig): Global configuration settings.
        services_managers (list[IServiceManager]): List of service managers.
        test_config (TestConfig): Configuration for the test.
        plugin_manager (PluginManager): Loader for plugins.
        logger (Logger): Logger for logging information.

    Methods:
        __init__(env_config_to_test, output_dir, env_type, env_sub_type, event_manager):
            Initializes the GperfCpuEnvironment with the given configuration and parameters.

        setup_environment(services_managers, test_config, global_config, timestamp, plugin_manager):
            Sets up the environment with the provided services managers, test configuration,
            global configuration, timestamp, and plugin manager.

        to_command(service_name):
            Generates the gperf command based on the configuration.

        __repr__():
            Returns a string representation of the GperfCpuEnvironment instance.
    """

    def __init__(
        self,
        env_config_to_test: GperfCpuConfig,
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

    def setup_environment(
        self,
        services_managers: list[IServiceManager],
        test_config: TestConfig,
        global_config: GlobalConfig,
        timestamp: str,
        plugin_manager: "PluginManager",
    ):
        # Use standardized setup from mixin
        self.setup_execution_environment(
            services_managers, test_config, global_config, timestamp, plugin_manager
        )

        for service in self.services_managers:
            self.logger.debug("Service cmds before gperf_cpu modification: %s", service.run_cmd)
            if service.service_config_to_test.implementation.gperf_compatible:
                service_name = getattr(service, "service_name", service.__class__.__name__)

                # Use ServiceCommandBuilder for proper command building
                from panther.core.command_processor.command_builder import ServiceCommandBuilder
                from panther.plugins.protocols.config_schema import RoleEnum

                # Get the service role
                service_role = getattr(service, "role", RoleEnum.server)

                # Create command builder
                command_builder = ServiceCommandBuilder(service_role)

                # Generate output file paths
                profile_file = f"/app/logs/{service_name}_cpu_profile_{timestamp}.prof"
                pdf_file = f"/app/logs/{service_name}_cpu_profile_{timestamp}.pdf"

                # Register output files with the mixin
                self.register_output_file("cpu_profile", profile_file, service_name)
                self.register_output_file("cpu_profile_pdf", pdf_file, service_name)

                # Build gperf CPU wrapper setup command using the EXEC_ENV_WRAPPERS pattern
                wrapper_setup_cmd = f"""
# Setup gperf CPU profiling wrapper
if [ -z "$EXEC_ENV_WRAPPERS" ]; then
    export EXEC_ENV_WRAPPERS="env LD_PRELOAD=/usr/lib/x86_64-linux-gnu/libprofiler.so.0 CPUPROFILE={profile_file}"
else
    export EXEC_ENV_WRAPPERS="env LD_PRELOAD=/usr/lib/x86_64-linux-gnu/libprofiler.so.0 CPUPROFILE={profile_file} $EXEC_ENV_WRAPPERS"
fi
echo "Added gperf CPU profiling wrapper" >> /app/logs/{service_name}_exec_env_setup.log
""".strip()

                # Use CommandBuilder to add the command with proper metadata
                command_builder.add_command(
                    command=wrapper_setup_cmd,
                    description=f"Setup gperf CPU profiling wrapper for {service_name}",
                    is_multiline=True,
                    is_critical=False,  # Don't fail if gperf setup fails
                    environment={"CPUPROFILE_OUTPUT": profile_file},
                )

                # Add post-processing command to generate PDF if enabled
                post_run_commands = []
                if self.env_config_to_test.generate_pdf:
                    pprof_options = (
                        " ".join(self.env_config_to_test.pprof_options)
                        if self.env_config_to_test.pprof_options
                        else ""
                    )
                    post_process_cmd = f"""
# Generate PDF from CPU profile
if [ -f "{profile_file}" ]; then
    pprof --pdf {pprof_options} {profile_file} > {pdf_file} 2>/dev/null || echo "Failed to generate CPU profile PDF"
    echo "Generated CPU profile PDF: {pdf_file}" >> /app/logs/{service_name}_exec_env_setup.log
else
    echo "CPU profile not found: {profile_file}" >> /app/logs/{service_name}_exec_env_setup.log
fi
""".strip()

                    command_builder.add_command(
                        command=post_process_cmd,
                        description=f"Generate PDF from CPU profile for {service_name}",
                        is_multiline=True,
                        is_critical=False,
                    )

                # Process the commands through CommandProcessor
                processed_commands = command_builder.process_commands()

                # Extract the actual command strings from processed commands
                if processed_commands:
                    gperf_commands = []

                    for i, cmd_dict in enumerate(processed_commands):
                        if isinstance(cmd_dict, dict) and "command" in cmd_dict:
                            if i == 0:  # First command is the wrapper setup
                                gperf_commands.append(cmd_dict["command"])
                            elif (
                                self.env_config_to_test.generate_pdf and i == 1
                            ):  # Second command is post-processing if PDF is enabled
                                post_run_commands.append(cmd_dict["command"])
                        else:
                            # Fallback if structure is different
                            gperf_commands.append(str(cmd_dict))

                    # Use the CommandModificationMixin to properly modify the service
                    # Add pre-run commands
                    if gperf_commands:
                        applied_modifications = self.modify_service_commands(
                            service, "gperf_cpu_wrapper", {"pre_run_cmds": gperf_commands}
                        )
                        self.logger.info(
                            "Added gperf CPU profiling wrapper to service %s", service_name
                        )
                        self.logger.debug(
                            "Applied pre-run modifications: %s", applied_modifications
                        )

                    # Add post-run commands
                    if post_run_commands:
                        applied_post_modifications = self.modify_service_commands(
                            service,
                            "gperf_cpu_post_processing",
                            {"post_run_cmds": post_run_commands},
                        )
                        self.logger.info(
                            "Added gperf CPU post-processing to service %s", service_name
                        )
                        self.logger.debug(
                            "Applied post-run modifications: %s", applied_post_modifications
                        )

                    # Mark that gperf is enabled for this service
                    service.environments["GPERF"] = True

                    self.logger.debug(
                        "Service cmds after gperf_cpu modification: %s", service.run_cmd
                    )
                else:
                    self.logger.warning(
                        "No gperf CPU commands were processed for service %s", service_name
                    )
            else:
                self.logger.debug("Service %s is not gperf compatible", service)

        self.logger.debug("Test Config: %s", OmegaConf.to_yaml(self.test_config))
        self.logger.debug("Global Config: %s", OmegaConf.to_yaml(self.global_config))

    def to_command(self, profile_file: str | None = None) -> str:
        """
        Generate the gperf CPU profiling wrapper command.

        :param profile_file: Optional path to the CPU profile output file.
        :return: Command string for CPU profiling wrapper.
        """
        # Build the LD_PRELOAD environment wrapper for CPU profiling
        command_parts = ["env"]

        # Add LD_PRELOAD for the profiler library
        # Try multiple possible locations for the library
        profiler_lib = (
            self.env_config_to_test.profiler_library or "/usr/lib/x86_64-linux-gnu/libprofiler.so.0"
        )
        command_parts.append(f"LD_PRELOAD={profiler_lib}")

        # Add CPUPROFILE environment variable if profile file is specified
        if profile_file:
            command_parts.append(f"CPUPROFILE={profile_file}")

        # Add sampling frequency if specified
        if (
            hasattr(self.env_config_to_test, "sampling_frequency")
            and self.env_config_to_test.sampling_frequency
        ):
            command_parts.append(
                f"CPUPROFILE_FREQUENCY={self.env_config_to_test.sampling_frequency}"
            )

        # Add real-time signal if specified
        if (
            hasattr(self.env_config_to_test, "use_realtime_signal")
            and self.env_config_to_test.use_realtime_signal
        ):
            command_parts.append("CPUPROFILE_REALTIME=1")

        return " ".join(command_parts)

    def initialize(self, test_config, output_dir, event_manager, global_config):
        """
        Initialize the gperf CPU environment with configuration settings.

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
            self.logger.debug("GperfCpuEnvironment initialized successfully")
            return True
        except Exception as e:
            self.logger.error("Failed to initialize GperfCpuEnvironment: %s", e)
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
        Implementation of environment setup for gperf CPU (from parent interface).

        Args:
            services_managers: List of service managers
            test_config: Test configuration
            global_config: Global configuration
            timestamp: Timestamp for this execution
            plugin_manager: Plugin manager instance
            execution_environment: List of execution environments (unused for gperf CPU)
        """
        # execution_environment is not needed for gperf CPU setup but required by interface
        _ = execution_environment
        # Delegate to the concrete implementation
        self.setup_environment(
            services_managers, test_config, global_config, timestamp, plugin_manager
        )

    def _do_deploy_services(self):
        """
        Implementation of service deployment for gperf CPU.

        For execution environments like gperf CPU, deployment is typically handled
        by the network environment, so this is usually a no-op.
        """
        self.logger.debug("GperfCpuEnvironment deployment: no specific deployment needed")

    def _do_teardown_environment(self):
        """
        Implementation of environment teardown for gperf CPU.
        """
        self.logger.debug("GperfCpuEnvironment teardown: cleaning up gperf CPU resources")
        # Collect any remaining output files
        outputs = self.collect_outputs()
        if outputs:
            self.logger.info("Collected gperf CPU outputs: %s", list(outputs.keys()))

    def handle_event(self, event):
        """
        Handle events sent to this execution environment.

        Args:
            event: The event to handle
        """
        event_type = type(event).__name__
        self.logger.debug("GperfCpuEnvironment received event: %s", event_type)

        # Handle environment-specific events if needed
        if event_type == "ServiceStartedEvent":
            self.logger.debug("Service started, gperf CPU profiling should be active")
        elif event_type == "ServiceStoppedEvent":
            self.logger.debug("Service stopped, gperf CPU collection complete")
        else:
            self.logger.debug("Unhandled event type: %s", event_type)

    def __repr__(self):
        return (
            f"GperfCpuEnvironment("
            f"env_config_to_test={self.env_config_to_test}, "
            f"output_dir={self.output_dir}, "
            f"event_manager={self.event_manager}, "
            f"services_managers={self.services_managers}, "
            f"test_config={self.test_config})"
        )
