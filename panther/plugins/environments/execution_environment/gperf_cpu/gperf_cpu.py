from typing import TYPE_CHECKING, List, Optional

"""
Refactored gperf CPU execution environment using shared command generation utilities.

This demonstrates how the shared utilities eliminate duplication and simplify
plugin implementation while maintaining all functionality.
"""

from panther.core.observer.management.event_manager import EventManager
from panther.plugins.core.plugin_decorators import register_plugin
from panther.plugins.core.structures.plugin_type import PluginType
from panther.plugins.environments.execution_environment.base_execution_environment import (
    BaseExecutionEnvironment,
)
from panther.plugins.environments.execution_environment.command_generation_utils import (
    create_execution_environment_builder,
)
from panther.plugins.environments.execution_environment.gperf_cpu.config_schema import (
    GperfCpuConfig,
)
from panther.plugins.services.services_interface import IServiceManager

if TYPE_CHECKING:
    pass


@register_plugin(
    plugin_type=PluginType.EXECUTION_ENVIRONMENT,
    name="gperf_cpu",
    version="1.0.0",
    description="Google Performance Tools CPU profiling environment",
    author="PANTHER Team",
    capabilities=["cpu_profiling", "performance_analysis"],
    external_dependencies=["libgoogle-perftools-dev", "google-perftools"],
    runtime_mode="profile",
)
class GperfCpuEnvironment(BaseExecutionEnvironment):
    """

    CPU profiling execution environment using gperftools.

    This environment uses shared command generation utilities to eliminate
    code duplication while providing comprehensive CPU profiling capabilities.
    """

    def __init__(
        self,
        env_config_to_test: GperfCpuConfig,
        output_dir: str,
        env_type: str,
        env_sub_type: str,
        event_manager: EventManager,
    ):
        """Initialize the gperf CPU environment."""
        super().__init__(
            env_config_to_test, output_dir, env_type, env_sub_type, event_manager
        )

        # Initialize plugin config cache
        self._plugin_config = None

    def _get_plugin_config(self) -> GperfCpuConfig:
        """Get plugin config with caching and fallback."""
        if self._plugin_config is None:
            try:
                self._plugin_config = self.env_config_to_test.get_plugin_config(
                    GperfCpuConfig
                )
            except Exception as e:
                self.logger.debug(f"Could not get plugin config, using defaults: {e}")
                self._plugin_config = GperfCpuConfig()
        return self._plugin_config

    def _setup_plugin_specific_environment(
        self, services_managers: List[IServiceManager], timestamp: str
    ):
        """
        Set up gperf CPU profiling for compatible services using shared utilities.

        Args:
            services_managers: List of service managers to potentially modify
            timestamp: Timestamp for this execution (used for file naming)
        """
        for service in services_managers:
            # Only apply to services that support gperf
            if not getattr(
                service.service_config_to_test.implementation, "gperf_compatible", True
            ):
                self.logger.debug(
                    "Skipping gperf CPU profiling for %s (not gperf compatible)",
                    getattr(service, "service_name", service.__class__.__name__),
                )
                continue

            # Create command builder using shared utilities
            command_builder = create_execution_environment_builder(
                service=service,
                environment_name="gperf_cpu",
                timestamp=timestamp,
                register_output_callback=self.register_output_file,
                logger=self.logger,
            )

            # Register output files and get their paths
            profile_file = command_builder.register_output_file(
                file_type="cpu_profile",
                extension="prof",
                description="CPU profile data",
            )

            # Build the gperf wrapper command using dual approach
            plugin_config = self._get_plugin_config()

            # First try plugin_config dict
            profiler_lib = None
            if (
                hasattr(self.env_config_to_test, "plugin_config")
                and self.env_config_to_test.plugin_config
            ):
                profiler_lib = self.env_config_to_test.plugin_config.get(
                    "profiler_library"
                )

            # Second try typed config
            if profiler_lib is None:
                profiler_lib = plugin_config.profiler_library

            profiler_lib = profiler_lib or "/usr/lib/x86_64-linux-gnu/libprofiler.so.0"

            # Build environment variables for profiling
            env_vars = {
                "CPUPROFILE": profile_file,
            }

            # Add optional profiling parameters using dual approach
            # Get sampling_frequency
            sampling_frequency = None
            if (
                hasattr(self.env_config_to_test, "plugin_config")
                and self.env_config_to_test.plugin_config
            ):
                sampling_frequency = self.env_config_to_test.plugin_config.get(
                    "sampling_frequency"
                )
            if sampling_frequency is None:
                sampling_frequency = plugin_config.sampling_frequency

            if sampling_frequency:
                env_vars["CPUPROFILE_FREQUENCY"] = str(sampling_frequency)

            # Get use_realtime_signal
            use_realtime_signal = None
            if (
                hasattr(self.env_config_to_test, "plugin_config")
                and self.env_config_to_test.plugin_config
            ):
                use_realtime_signal = self.env_config_to_test.plugin_config.get(
                    "use_realtime_signal"
                )
            if use_realtime_signal is None:
                use_realtime_signal = plugin_config.use_realtime_signal

            if use_realtime_signal:
                env_vars["CPUPROFILE_REALTIME"] = "1"

            # Create the wrapper command
            wrapper_command = f"env LD_PRELOAD={profiler_lib}"
            for key, value in env_vars.items():
                wrapper_command += f" {key}={value}"

            # Add wrapper with conditional check for library existence
            command_builder.add_conditional_wrapper(
                condition=f'[ -f "{profiler_lib}" ]',
                wrapper_command=wrapper_command,
                description=f"Setup gperf CPU profiling for {command_builder.service_name}",
                fallback_message=f"gperf profiler library not found: {profiler_lib}",
                is_critical=False,
            )

            # Add post-processing for PDF generation if enabled using dual approach
            generate_pdf = None
            if (
                hasattr(self.env_config_to_test, "plugin_config")
                and self.env_config_to_test.plugin_config
            ):
                generate_pdf = self.env_config_to_test.plugin_config.get("generate_pdf")
            if generate_pdf is None:
                generate_pdf = plugin_config.generate_pdf

            if generate_pdf:
                pdf_file = command_builder.register_output_file(
                    file_type="cpu_profile_pdf",
                    extension="pdf",
                    description="CPU profile PDF visualization",
                )

                # Build pprof command with optional parameters
                pprof_options = []
                if self.env_config_to_test.pprof_options:
                    pprof_options.extend(self.env_config_to_test.pprof_options)

                # Add filtering options
                if self.env_config_to_test.exclude_functions:
                    for func in self.env_config_to_test.exclude_functions:
                        pprof_options.extend(["--ignore", func])

                if self.env_config_to_test.include_only_functions:
                    for func in self.env_config_to_test.include_only_functions:
                        pprof_options.extend(["--focus", func])

                pprof_opts_str = " ".join(pprof_options) if pprof_options else ""
                processing_command = (
                    f"pprof --pdf {pprof_opts_str} {profile_file} > {pdf_file}"
                )

                command_builder.add_post_processing(
                    input_file=profile_file,
                    output_file=pdf_file,
                    processing_command=processing_command,
                    description="CPU profile PDF generation",
                    file_type="cpu_profile_pdf",
                    error_message="Failed to generate CPU profile PDF (pprof may not be available)",
                )

            # Build and apply all commands to the service
            results = command_builder.build_and_apply(self.modify_service_commands)

            self.logger.info(
                "Successfully configured gperf CPU profiling for service %s",
                command_builder.service_name,
            )
            self.logger.debug("Applied modifications: %s", results)

    def to_command(
        self, pid: Optional[int] = None, output_file: Optional[str] = None
    ) -> str:
        """
        Generate the gperf CPU profiling command for execution.

        Args:
            pid: Optional process ID to attach to (not supported by gperf)
            output_file: Optional output file path

        Returns:
            str: Command string for gperf CPU profiling wrapper
        """
        if output_file is None:
            output_file = self.env_config_to_test.output_file or "/tmp/cpu_profile.prof"

        profiler_lib = (
            self.env_config_to_test.profiler_library
            or "/usr/lib/x86_64-linux-gnu/libprofiler.so.0"
        )

        # Build environment variables
        env_vars = [f"CPUPROFILE={output_file}"]

        if self.env_config_to_test.sampling_frequency:
            env_vars.append(
                f"CPUPROFILE_FREQUENCY={self.env_config_to_test.sampling_frequency}"
            )

        if self.env_config_to_test.use_realtime_signal:
            env_vars.append("CPUPROFILE_REALTIME=1")

        # Note: pid parameter is not supported by gperf CPU profiling
        if pid:
            self.logger.warning(
                "PID parameter (%d) ignored - gperf CPU profiling does not support attaching to existing processes",
                pid,
            )

        # Build the complete command
        env_string = " ".join(env_vars)
        return f"env LD_PRELOAD={profiler_lib} {env_string}"

    def update_environment(
        self,
        execution_environment,
        global_config,
        plugin_manager,
        services_managers,
        test_config,
    ) -> None:
        """
        Update environment for gperf CPU profiling execution.

        Args:
            execution_environment: Current execution environment
            global_config: Global configuration
            plugin_manager: Plugin manager instance
            services_managers: List of service managers
            test_config: Test configuration
        """
        # Add any gperf CPU-specific environment updates here
        self.logger.debug("Updated environment for gperf CPU profiling execution")
        pass
