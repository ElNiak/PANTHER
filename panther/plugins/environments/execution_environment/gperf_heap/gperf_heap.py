from abc import ABC
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from panther.plugins.plugin_manager import PluginManager

from omegaconf import OmegaConf
from panther.core.observer.management.event_manager import EventManager
from panther.config.config_experiment_schema import TestConfig
from panther.config.config_global_schema import GlobalConfig
from panther.plugins.environments.execution_environment.gperf_heap.config_schema import (
    GperfHeapConfig,
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
    name="gperf_heap",
    version="1.0.0",
    description="Memory heap profiling execution environment using Google Performance Tools",
    author="PANTHER Team",
    capabilities=["heap_profiling", "memory_analysis", "leak_detection"],
    external_dependencies=["gperf"],
)
class GperfHeapEnvironment(
    ExecutionEnvironmentMixin,
    StandardOutputCollectorMixin,
    CommandModificationMixin,
    IExecutionEnvironment,
    ABC,
):
    """
    GperfHeapEnvironment is a class that sets up and manages the execution environment
    for heap profiling using gperf/tcmalloc.

    Attributes:
        env_config_to_test (GperfHeapConfig): Configuration specific to the environment being tested.
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
            Initializes the GperfHeapEnvironment with the given configuration and parameters.

        setup_environment(services_managers, test_config, global_config, timestamp, plugin_manager):
            Sets up the environment with the provided services managers, test configuration,
            global configuration, timestamp, and plugin manager.

        to_command(profile_file):
            Generates the gperf heap command wrapper.

        __repr__():
            Returns a string representation of the GperfHeapEnvironment instance.
    """

    def __init__(
        self,
        env_config_to_test: GperfHeapConfig,
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
            self.logger.debug("Service cmds before gperf_heap modification: %s", service.run_cmd)
            if service.service_config_to_test.implementation.gperf_compatible:
                service_name = getattr(service, "service_name", service.__class__.__name__)

                # Use ServiceCommandBuilder for proper command building
                from panther.core.command_processor.command_builder import ServiceCommandBuilder
                from panther.plugins.protocols.config_schema import RoleEnum

                # Get the service role
                service_role = getattr(service, "role", RoleEnum.server)

                # Create command builder
                command_builder = ServiceCommandBuilder(service_role)

                # Generate output file paths with timestamp
                # Heap profiler creates multiple files, so we use a base name
                profile_base = f"/app/logs/{service_name}_heap_profile_{timestamp}"
                pdf_file = f"/app/logs/{service_name}_heap_profile_{timestamp}.pdf"
                text_file = f"/app/logs/{service_name}_heap_profile_{timestamp}.txt"

                # Register output files with the mixin
                # Heap profiler creates multiple files like .0001.heap, .0002.heap, etc.
                self.register_output_file("heap_profile_base", profile_base, service_name)
                if self.env_config_to_test.generate_pdf:
                    self.register_output_file("heap_profile_pdf", pdf_file, service_name)
                if self.env_config_to_test.generate_text_report:
                    self.register_output_file("heap_profile_text", text_file, service_name)

                # Build gperf heap wrapper setup command using the EXEC_ENV_WRAPPERS pattern
                wrapper_setup_cmd = f"""
# Setup gperf heap profiling wrapper
if [ -z "$EXEC_ENV_WRAPPERS" ]; then
    export EXEC_ENV_WRAPPERS="env LD_PRELOAD=/usr/lib/x86_64-linux-gnu/libtcmalloc.so.4 HEAPPROFILE={profile_base}"
else
    export EXEC_ENV_WRAPPERS="env LD_PRELOAD=/usr/lib/x86_64-linux-gnu/libtcmalloc.so.4 HEAPPROFILE={profile_base} $EXEC_ENV_WRAPPERS"
fi
echo "Added gperf heap profiling wrapper" >> /app/logs/{service_name}_exec_env_setup.log
""".strip()

                # Add additional heap profiling environment variables based on config
                env_vars = self._build_heap_env_vars()
                if env_vars:
                    # Add environment variable setup to the wrapper command
                    env_setup = "\n".join([f"export {k}={v}" for k, v in env_vars.items()])
                    wrapper_setup_cmd = f"""
# Setup gperf heap profiling environment
{env_setup}

{wrapper_setup_cmd}
""".strip()

                # Use CommandBuilder to add the command with proper metadata
                command_builder.add_command(
                    command=wrapper_setup_cmd,
                    description=f"Setup gperf heap profiling wrapper for {service_name}",
                    is_multiline=True,
                    is_critical=False,  # Don't fail if gperf setup fails
                    environment={"HEAPPROFILE_BASE": profile_base},
                )

                # Add post-processing commands
                post_run_commands = []

                # Command to find and process heap profile files
                find_profiles_cmd = f"""
# Find and process heap profile files
echo "Looking for heap profile files with base: {profile_base}" >> /app/logs/{service_name}_exec_env_setup.log
HEAP_FILES=$(ls {profile_base}.*.heap 2>/dev/null || true)
if [ -n "$HEAP_FILES" ]; then
    echo "Found heap profile files: $HEAP_FILES" >> /app/logs/{service_name}_exec_env_setup.log
    # Get the latest heap profile (highest number)
    LATEST_HEAP=$(ls -1 {profile_base}.*.heap 2>/dev/null | sort -V | tail -1)
    echo "Latest heap profile: $LATEST_HEAP" >> /app/logs/{service_name}_exec_env_setup.log
else
    echo "No heap profile files found" >> /app/logs/{service_name}_exec_env_setup.log
fi
""".strip()

                command_builder.add_command(
                    command=find_profiles_cmd,
                    description=f"Find heap profile files for {service_name}",
                    is_multiline=True,
                    is_critical=False,
                )

                # Generate PDF if enabled
                if self.env_config_to_test.generate_pdf:
                    pprof_options = (
                        " ".join(self.env_config_to_test.pprof_options)
                        if self.env_config_to_test.pprof_options
                        else ""
                    )
                    pdf_cmd = f"""
# Generate PDF from heap profile
if [ -n "$LATEST_HEAP" ] && [ -f "$LATEST_HEAP" ]; then
    pprof --pdf {pprof_options} "$LATEST_HEAP" > {pdf_file} 2>/dev/null || echo "Failed to generate heap profile PDF"
    if [ -f "{pdf_file}" ]; then
        echo "Generated heap profile PDF: {pdf_file}" >> /app/logs/{service_name}_exec_env_setup.log
    fi
else
    echo "No heap profile found to generate PDF" >> /app/logs/{service_name}_exec_env_setup.log
fi
""".strip()

                    command_builder.add_command(
                        command=pdf_cmd,
                        description=f"Generate PDF from heap profile for {service_name}",
                        is_multiline=True,
                        is_critical=False,
                    )

                # Generate text report if enabled
                if self.env_config_to_test.generate_text_report:
                    text_cmd = f"""
# Generate text report from heap profile
if [ -n "$LATEST_HEAP" ] && [ -f "$LATEST_HEAP" ]; then
    pprof --text {pprof_options} "$LATEST_HEAP" > {text_file} 2>/dev/null || echo "Failed to generate heap profile text report"
    if [ -f "{text_file}" ]; then
        echo "Generated heap profile text report: {text_file}" >> /app/logs/{service_name}_exec_env_setup.log
    fi
else
    echo "No heap profile found to generate text report" >> /app/logs/{service_name}_exec_env_setup.log
fi
""".strip()

                    command_builder.add_command(
                        command=text_cmd,
                        description=f"Generate text report from heap profile for {service_name}",
                        is_multiline=True,
                        is_critical=False,
                    )

                # Process the commands through CommandProcessor
                processed_commands = command_builder.process_commands()

                # Extract the actual command strings from processed commands
                if processed_commands:
                    gperf_commands = []
                    post_run_commands = []

                    # First command is the wrapper setup
                    if (
                        len(processed_commands) > 0
                        and isinstance(processed_commands[0], dict)
                        and "command" in processed_commands[0]
                    ):
                        gperf_commands.append(processed_commands[0]["command"])

                    # Remaining commands are post-processing
                    for cmd_dict in processed_commands[1:]:
                        if isinstance(cmd_dict, dict) and "command" in cmd_dict:
                            post_run_commands.append(cmd_dict["command"])
                        else:
                            # Fallback if structure is different
                            post_run_commands.append(str(cmd_dict))

                    # Use the CommandModificationMixin to properly modify the service
                    # Add pre-run commands
                    if gperf_commands:
                        applied_modifications = self.modify_service_commands(
                            service, "gperf_heap_wrapper", {"pre_run_cmds": gperf_commands}
                        )
                        self.logger.info(
                            "Added gperf heap profiling wrapper to service %s", service_name
                        )
                        self.logger.debug(
                            "Applied pre-run modifications: %s", applied_modifications
                        )

                    # Add post-run commands
                    if post_run_commands:
                        applied_post_modifications = self.modify_service_commands(
                            service,
                            "gperf_heap_post_processing",
                            {"post_run_cmds": post_run_commands},
                        )
                        self.logger.info(
                            "Added gperf heap post-processing to service %s", service_name
                        )
                        self.logger.debug(
                            "Applied post-run modifications: %s", applied_post_modifications
                        )

                    # Mark that gperf is enabled for this service
                    service.environments["GPERF"] = True

                    self.logger.debug(
                        "Service cmds after gperf_heap modification: %s", service.run_cmd
                    )
                else:
                    self.logger.warning(
                        "No gperf heap commands were processed for service %s", service_name
                    )
            else:
                self.logger.debug("Service %s is not gperf compatible", service)

        self.logger.debug("Test Config: %s", OmegaConf.to_yaml(self.test_config))
        self.logger.debug("Global Config: %s", OmegaConf.to_yaml(self.global_config))

    def _build_heap_env_vars(self) -> dict[str, str]:
        """
        Build environment variables for heap profiling based on configuration.

        :return: Dictionary of environment variable names to values
        """
        env_vars = {}

        # Heap profile allocation interval
        if self.env_config_to_test.heap_profile_allocation_interval:
            env_vars["HEAP_PROFILE_ALLOCATION_INTERVAL"] = str(
                self.env_config_to_test.heap_profile_allocation_interval
            )

        # Heap profile inuse interval
        if self.env_config_to_test.heap_profile_inuse_interval:
            env_vars["HEAP_PROFILE_INUSE_INTERVAL"] = str(
                self.env_config_to_test.heap_profile_inuse_interval
            )

        # Heap profile time interval
        if self.env_config_to_test.heap_profile_time_interval:
            env_vars["HEAP_PROFILE_TIME_INTERVAL"] = str(
                self.env_config_to_test.heap_profile_time_interval
            )

        # Heap check type
        if self.env_config_to_test.heap_check_type:
            env_vars["HEAPCHECK"] = self.env_config_to_test.heap_check_type

        # Memory leak check
        if self.env_config_to_test.enable_leak_check:
            env_vars["HEAP_CHECK_REPORT"] = "true"
            if self.env_config_to_test.leak_check_at_exit:
                env_vars["HEAP_CHECK_AFTER_QUIESCE"] = "true"

        # Profile mmap
        if self.env_config_to_test.profile_mmap:
            env_vars["HEAP_PROFILE_MMAP"] = "true"

        # Only mmap profile
        if self.env_config_to_test.only_mmap_profile:
            env_vars["HEAP_PROFILE_ONLY_MMAP"] = "true"

        # Deep heap profile
        if self.env_config_to_test.deep_heap_profile > 0:
            env_vars["DEEP_HEAP_PROFILE"] = str(self.env_config_to_test.deep_heap_profile)

        return env_vars

    def to_command(self, profile_base: str | None = None) -> str:
        """
        Generate the gperf heap profiling wrapper command.

        :param profile_base: Optional base path for heap profile output files.
        :return: Command string for heap profiling wrapper.
        """
        # Build the LD_PRELOAD environment wrapper for heap profiling
        command_parts = ["env"]

        # Add LD_PRELOAD for the tcmalloc library
        # Try multiple possible locations for the library
        tcmalloc_lib = (
            self.env_config_to_test.tcmalloc_library or "/usr/lib/x86_64-linux-gnu/libtcmalloc.so.4"
        )
        command_parts.append(f"LD_PRELOAD={tcmalloc_lib}")

        # Add HEAPPROFILE environment variable if profile base is specified
        if profile_base:
            command_parts.append(f"HEAPPROFILE={profile_base}")

        # Add additional environment variables
        env_vars = self._build_heap_env_vars()
        for key, value in env_vars.items():
            command_parts.append(f"{key}={value}")

        return " ".join(command_parts)

    def initialize(self, test_config, output_dir, event_manager, global_config):
        """
        Initialize the gperf heap environment with configuration settings.

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
            self.logger.debug("GperfHeapEnvironment initialized successfully")
            return True
        except Exception as e:
            self.logger.error("Failed to initialize GperfHeapEnvironment: %s", e)
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
        Implementation of environment setup for gperf heap (from parent interface).

        Args:
            services_managers: List of service managers
            test_config: Test configuration
            global_config: Global configuration
            timestamp: Timestamp for this execution
            plugin_manager: Plugin manager instance
            execution_environment: List of execution environments (unused for gperf heap)
        """
        # execution_environment is not needed for gperf heap setup but required by interface
        _ = execution_environment
        # Delegate to the concrete implementation
        self.setup_environment(
            services_managers, test_config, global_config, timestamp, plugin_manager
        )

    def _do_deploy_services(self):
        """
        Implementation of service deployment for gperf heap.

        For execution environments like gperf heap, deployment is typically handled
        by the network environment, so this is usually a no-op.
        """
        self.logger.debug("GperfHeapEnvironment deployment: no specific deployment needed")

    def _do_teardown_environment(self):
        """
        Implementation of environment teardown for gperf heap.
        """
        self.logger.debug("GperfHeapEnvironment teardown: cleaning up gperf heap resources")
        # Collect any remaining output files
        outputs = self.collect_outputs()
        if outputs:
            self.logger.info("Collected gperf heap outputs: %s", list(outputs.keys()))

    def handle_event(self, event):
        """
        Handle events sent to this execution environment.

        Args:
            event: The event to handle
        """
        event_type = type(event).__name__
        self.logger.debug("GperfHeapEnvironment received event: %s", event_type)

        # Handle environment-specific events if needed
        if event_type == "ServiceStartedEvent":
            self.logger.debug("Service started, gperf heap profiling should be active")
        elif event_type == "ServiceStoppedEvent":
            self.logger.debug("Service stopped, gperf heap collection complete")
        else:
            self.logger.debug("Unhandled event type: %s", event_type)

    def __repr__(self):
        return (
            f"GperfHeapEnvironment("
            f"env_config_to_test={self.env_config_to_test}, "
            f"output_dir={self.output_dir}, "
            f"event_manager={self.event_manager}, "
            f"services_managers={self.services_managers}, "
            f"test_config={self.test_config})"
        )
