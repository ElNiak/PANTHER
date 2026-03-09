"""Google Performance Tools heap profiler execution environment plugin."""

from typing import TYPE_CHECKING, List, Optional

"""
Memory heap profiling execution environment using Google Performance Tools (gperf) with shared utilities.

This plugin provides heap profiling capabilities for services by wrapping them
with gperf heap profiling tools and generating memory analysis reports.
Uses shared command generation utilities to eliminate code duplication.
"""

from panther.core.observer.management.event_manager import EventManager
from panther.plugins.core.plugin_decorators import register_plugin
from panther.plugins.core.structures.plugin_type import PluginType
from panther.plugins.environments.execution_environment.base_execution_environment import (
    BaseExecutionEnvironment,
)
from panther.plugins.environments.execution_environment.command_generation_utils import (
    CommandGenerationUtilsFactory,
    create_execution_environment_builder,
)
from panther.plugins.environments.execution_environment.gperf_heap.config_schema import (
    GperfHeapConfig,
)
from panther.plugins.services.services_interface import IServiceManager

if TYPE_CHECKING:
    pass


@register_plugin(
    plugin_type=PluginType.EXECUTION_ENVIRONMENT,
    name="gperf_heap",
    version="1.0.0",
    description="Memory heap profiling execution environment using Google Performance Tools",
    author="PANTHER Team",
    capabilities=["heap_profiling", "memory_analysis", "leak_detection"],
    external_dependencies=["gperf"],
    runtime_mode="profile",  # Set to debug mode for comprehensive analysis
)
class GperfHeapEnvironment(BaseExecutionEnvironment):
    """Memory heap profiling execution environment using Google Performance Tools.

    This environment wraps services with gperf heap profiling to collect
    memory usage data and generate heap analysis reports. Uses shared command
    generation utilities for consistent and maintainable command building.
    """

    def __init__(
        self,
        env_config_to_test: GperfHeapConfig,
        output_dir: str,
        env_type: str,
        env_sub_type: str,
        event_manager: EventManager,
        target_platform: Optional[str] = None,
    ):
        """Initialize the gperf heap environment."""
        super().__init__(
            env_config_to_test, output_dir, env_type, env_sub_type, event_manager
        )

        self.target_platform = target_platform

    def _setup_plugin_specific_environment(
        self, services_managers: List[IServiceManager], timestamp: str
    ):
        """Set up gperf heap profiling for all services using shared utilities.

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
                    "Skipping gperf heap profiling for %s (not gperf compatible)",
                    getattr(service, "service_name", service.__class__.__name__),
                )
                continue

            # Create command builder using shared utilities
            command_builder = create_execution_environment_builder(
                service=service,
                environment_name="gperf_heap",
                timestamp=timestamp,
                register_output_callback=self.register_output_file,
                logger=self.logger,
            )

            # Register output files and get their paths
            heap_profile_file = command_builder.register_output_file(
                file_type="heap_profile",
                extension="prof",
                description="Heap profile data",
            )

            heap_analysis_file = command_builder.register_output_file(
                file_type="heap_analysis",
                extension="txt",
                description="Heap analysis results",
            )
            # Build gperf heap profiling environment variables
            heap_env_vars = self._build_heap_environment_vars(heap_profile_file)

            # Add heap profiling wrapper (just environment variables)
            command_builder.add_wrapper_command(
                wrapper_command="",  # No wrapper command needed, just env vars
                additional_env_vars=heap_env_vars,
            )

            # Get service name for logging
            service_name = getattr(service, "service_name", service.__class__.__name__)

            # Add post-processing command for heap analysis generation
            post_process_cmd = self._build_post_processing_command(
                heap_profile_file, heap_analysis_file, service_name
            )

            command_builder.add_post_processing(
                command=post_process_cmd,
                input_file=heap_profile_file,
                processing_command=f"pprof --text {heap_profile_file}",
            )

            # Build and apply all commands
            command_builder.build_and_apply(self)

    def _build_heap_environment_vars(self, heap_profile_file: str) -> dict:
        """Build the environment variables for gperf heap profiling.

        Args:
            heap_profile_file: Path to write heap profile data

        Returns:
            dict: Environment variables for heap profiling
        """
        env_vars = {
            "HEAPPROFILE": heap_profile_file,
            "LD_PRELOAD": "/usr/lib/x86_64-linux-gnu/libtcmalloc_and_profiler.so.4:$LD_PRELOAD",
        }

        # Add sampling frequency if configured
        allocation_interval = self._get_config_value("heap_profile_allocation_interval")
        if allocation_interval:
            env_vars["HEAP_PROFILE_ALLOCATION_INTERVAL"] = str(allocation_interval)

        # Add heap check level if configured
        heap_check_type = self._get_config_value("heap_check_type")
        if heap_check_type:
            env_vars["HEAPCHECK"] = str(heap_check_type)

        # Add profile options
        profile_only_peak = self._get_config_value("profile_only_peak")
        if profile_only_peak:
            env_vars["HEAP_PROFILE_ONLY_PEAK"] = "1"

        return env_vars

    def _build_post_processing_command(
        self, heap_profile_file: str, heap_analysis_file: str, service_name: str
    ) -> str:
        """Build the post-processing command for generating heap analysis.

        Args:
            heap_profile_file: Path to heap profile file
            heap_analysis_file: Path to heap analysis file
            service_name: Name of the service being profiled

        Returns:
            str: Complete post-processing command
        """
        pprof_binary = self._get_config_value("pprof_binary", "pprof")

        return f"""
# Generate GPerf heap analysis
echo "=== GPerf Heap Analysis ===" > {heap_analysis_file}
echo "Generated at: $(date)" >> {heap_analysis_file}
echo "" >> {heap_analysis_file}

# Find the actual heap profile files (gperf creates numbered files)
profile_files=$(find $(dirname {heap_profile_file}) -name "$(basename {heap_profile_file})*" -type f 2>/dev/null)

if [ -n "$profile_files" ]; then
    # Get the latest profile file
    latest_profile=$(echo "$profile_files" | sort -V | tail -1)
    echo "Analyzing profile: $latest_profile" >> {heap_analysis_file}
    echo "" >> {heap_analysis_file}

    # Generate top memory consumers
    echo "=== Top Memory Consumers ===" >> {heap_analysis_file}
    {pprof_binary} --text --lines $latest_profile 2>/dev/null | head -20 >> {heap_analysis_file} || echo "Failed to generate text report" >> {heap_analysis_file}

    echo "" >> {heap_analysis_file}
    echo "=== Memory Allocation Tree ===" >> {heap_analysis_file}
    {pprof_binary} --tree --lines $latest_profile 2>/dev/null | head -30 >> {heap_analysis_file} || echo "Failed to generate tree report" >> {heap_analysis_file}
else
    echo "No heap profile files found" >> {heap_analysis_file}
fi

echo "Heap analysis completed for {service_name}" >> /app/logs/{service_name}_heap_analysis.log
""".strip()

    def to_command(self, output_file: Optional[str] = None) -> str:
        """Generate the gperf heap profiling command for execution.

        Args:
            output_file: Optional output file path

        Returns:
            str: Command string for heap profiling
        """
        if output_file is None:
            output_file = "/tmp/heap_profile"

        env_vars = self._build_heap_environment_vars(output_file)
        env_string = " ".join([f"{k}={v}" for k, v in env_vars.items()])

        return f"env {env_string}"

    def update_environment(
        self,
        execution_environment,
        global_config,
        plugin_manager,
        services_managers,
        test_config,
    ) -> None:
        """Update environment for gperf heap profiling execution.

        Args:
            execution_environment: Current execution environment
            global_config: Global configuration
            plugin_manager: Plugin manager instance
            services_managers: List of service managers
            test_config: Test configuration
        """
        # Add any gperf heap-specific environment updates here
        self.logger.debug("Updated environment for gperf heap profiling execution")
        pass
