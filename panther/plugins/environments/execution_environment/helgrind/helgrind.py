"""
Helgrind execution environment for thread error detection using Valgrind.

This plugin provides comprehensive thread error detection capabilities including
data race detection, lock order validation, and POSIX threads API misuse detection.
"""

from typing import TYPE_CHECKING, List, Optional, Union

from panther.core.observer.management.event_manager import EventManager
from panther.plugins.core.plugin_decorators import register_plugin
from panther.plugins.core.structures.plugin_type import PluginType
from panther.plugins.environments.execution_environment.base_execution_environment import (
    BaseExecutionEnvironment,
)
from panther.plugins.environments.execution_environment.command_generation_utils import (
    create_execution_environment_builder,
)
from panther.plugins.environments.execution_environment.helgrind.config_schema import (
    HelgrindConfig,
)
from panther.plugins.services.services_interface import IServiceManager

if TYPE_CHECKING:
    pass


@register_plugin(
    plugin_type=PluginType.EXECUTION_ENVIRONMENT,
    name="helgrind",
    version="1.0.0",
    description="Valgrind Helgrind thread error detection environment",
    author="PANTHER Team",
    capabilities=[
        "thread_error_detection",
        "race_condition_analysis",
        "deadlock_detection",
    ],
    external_dependencies=["valgrind>=3.15"],
    runtime_mode="debug",  # Set to minimal mode for reduced resource usage
)
class HelgrindEnvironment(BaseExecutionEnvironment):
    """

    Thread error detection execution environment using Valgrind Helgrind.

    This environment uses shared command generation utilities to eliminate
    code duplication while providing comprehensive thread error detection.
    """

    _config_class = HelgrindConfig

    def __init__(
        self,
        env_config_to_test: HelgrindConfig,
        output_dir: str,
        env_type: str,
        env_sub_type: str,
        event_manager: EventManager,
        target_platform: Optional[str] = None,
    ):
        """Initialize the Helgrind environment."""
        super().__init__(
            env_config_to_test, output_dir, env_type, env_sub_type, event_manager
        )

        self.target_platform = target_platform

    def _setup_plugin_specific_environment(
        self, services_managers: List[IServiceManager], timestamp: str
    ):
        """
        Set up Helgrind thread error detection for services using shared utilities.

        Args:
            services_managers: List of service managers to potentially modify
            timestamp: Timestamp for this execution (used for file naming)
        """
        for service in services_managers:
            # Create command builder using shared utilities
            command_builder = create_execution_environment_builder(
                service=service,
                environment_name="helgrind",
                timestamp=timestamp,
                register_output_callback=self.register_output_file,
                logger=self.logger,
            )

            # Register output files and get their paths
            helgrind_output_file = command_builder.register_output_file(
                file_type="helgrind_log",
                extension="log",
                description="Helgrind thread error detection log",
            )

            helgrind_summary_file = command_builder.register_output_file(
                file_type="helgrind_summary",
                extension="txt",
                description="Helgrind analysis summary",
            )

            # Build the Helgrind command using Valgrind
            helgrind_cmd = self._build_helgrind_command(helgrind_output_file)

            # Add the Helgrind wrapper with conditional check for Valgrind
            command_builder.add_conditional_wrapper(
                condition="command -v valgrind >/dev/null 2>&1",
                wrapper_command=helgrind_cmd,
                description=f"Setup Helgrind wrapper for {command_builder.service_name}",
                fallback_message="Valgrind not found - Helgrind thread error detection disabled",
                is_critical=False,
            )

            # Add comprehensive post-processing for thread error analysis
            self._add_helgrind_analysis_commands(
                command_builder, helgrind_output_file, helgrind_summary_file
            )

            # Build and apply all commands to the service
            results = command_builder.build_and_apply(self.modify_service_commands)

            self.logger.info(
                "Successfully configured Helgrind for service %s",
                command_builder.service_name,
            )
            self.logger.debug("Applied modifications: %s", results)

    def _build_helgrind_command(self, output_file: str) -> str:
        """
        Build the Helgrind command with configured options.

        Args:
            output_file: Path to write Helgrind output

        Returns:
            str: Complete Helgrind command
        """
        valgrind_binary = self._get_config_value("valgrind_binary", "valgrind")
        self.valgrind_binary = valgrind_binary
        command_parts = [self.valgrind_binary]

        # Specify Helgrind tool
        command_parts.extend(["--tool=helgrind"])

        # Add output file
        command_parts.extend([f"--log-file={output_file}"])

        # Set output format
        output_format = self._get_config_value("output_format")
        if output_format == "xml":
            command_parts.append("--xml=yes")
            command_parts.append(f"--xml-file={output_file}.xml")

        # History level for race detection
        history_level = self._get_config_value("history_level", "full")
        command_parts.append(f"--history-level={history_level}")

        # Conflict cache size
        conflict_cache_size = self._get_config_value("conflict_cache_size", 2000000)
        command_parts.append(f"--conflict-cache-size={conflict_cache_size}")

        # Lock order tracking
        track_lockorders = self._get_config_value("track_lockorders")
        if track_lockorders is False:
            command_parts.append("--track-lockorders=no")

        # Stack reference checking
        check_stack_refs = self._get_config_value("check_stack_refs")
        if check_stack_refs is False:
            command_parts.append("--check-stack-refs=no")

        # Thread creation race handling
        ignore_thread_creation = self._get_config_value("ignore_thread_creation")
        if ignore_thread_creation:
            command_parts.append("--ignore-thread-creation=yes")

        # Free-as-write option
        free_is_write = self._get_config_value("free_is_write")
        if free_is_write:
            command_parts.append("--free-is-write=yes")

        # Cache size
        cache_size = self._get_config_value("cache_size", 32)
        command_parts.append(f"--cache-size={cache_size}M")

        # Suppression file
        suppression_file = self._get_config_value("suppression_file")
        if suppression_file:
            command_parts.append(f"--suppressions={suppression_file}")

        # Additional general Valgrind options
        show_below_main = self._get_config_value("show_below_main")
        if show_below_main:
            command_parts.append("--show-below-main=yes")

        track_fds = self._get_config_value("track_fds")
        if track_fds:
            command_parts.append("--track-fds=yes")

        time_stamp = self._get_config_value("time_stamp")
        if time_stamp:
            command_parts.append("--time-stamp=yes")

        # Verbosity
        verbosity = self._get_config_value("verbosity", 0)
        if verbosity > 0:
            command_parts.append("--verbose" * verbosity)

        # Additional parameters
        additional_parameters = self._get_config_value("additional_parameters")
        if additional_parameters:
            command_parts.extend(additional_parameters)

        return " ".join(command_parts)

    def _add_helgrind_analysis_commands(
        self, command_builder, helgrind_output_file: str, summary_file: str
    ):
        """
        Add comprehensive Helgrind analysis post-processing commands.

        Args:
            command_builder: The command builder to add commands to
            helgrind_output_file: Path to the Helgrind output file
            summary_file: Path to the summary file to generate
        """
        service_name = command_builder.service_name

        # Generate comprehensive Helgrind analysis
        analysis_command = f"""
echo "=== Helgrind Thread Error Analysis for {service_name} ===" > {summary_file}
echo "Generated at: $(date)" >> {summary_file}
echo "Helgrind output file: {helgrind_output_file}" >> {summary_file}
echo "" >> {summary_file}

# Check if Helgrind output exists
if [ -f "{helgrind_output_file}" ]; then
    echo "=== Thread Error Summary ===" >> {summary_file}

    # Count different types of errors
    echo "Data race detections:" >> {summary_file}
    grep -c "Possible data race" {helgrind_output_file} 2>/dev/null || echo "0" >> {summary_file}

    echo "Lock order violations:" >> {summary_file}
    grep -c "Thread #[0-9]*: lock order" {helgrind_output_file} 2>/dev/null || echo "0" >> {summary_file}

    echo "Thread API misuse:" >> {summary_file}
    grep -c "Thread #[0-9]*: pthread_" {helgrind_output_file} | head -1 >> {summary_file} 2>/dev/null || echo "0" >> {summary_file}

    echo "" >> {summary_file}

    # Race condition details
    echo "=== Data Race Details ===" >> {summary_file}
    if grep -q "Possible data race" {helgrind_output_file} 2>/dev/null; then
        echo "Data races found - see full log for details" >> {summary_file}
        grep -A 5 "Possible data race" {helgrind_output_file} | head -20 >> {summary_file} 2>/dev/null
    else
        echo "No data races detected" >> {summary_file}
    fi

    echo "" >> {summary_file}

    # Lock order analysis
    echo "=== Lock Order Analysis ===" >> {summary_file}
    if grep -q "lock order" {helgrind_output_file} 2>/dev/null; then
        echo "Lock order violations found - potential deadlock risks" >> {summary_file}
        grep -B 2 -A 3 "lock order" {helgrind_output_file} | head -15 >> {summary_file} 2>/dev/null
    else
        echo "No lock order violations detected" >> {summary_file}
    fi

    echo "" >> {summary_file}

    # Thread synchronization issues
    echo "=== Thread Synchronization Issues ===" >> {summary_file}
    if grep -q "Thread #[0-9]*:" {helgrind_output_file} 2>/dev/null; then
        echo "Thread count:" >> {summary_file}
        grep -o "Thread #[0-9]*:" {helgrind_output_file} | sort -u | wc -l >> {summary_file} 2>/dev/null

        echo "Synchronization primitives used:" >> {summary_file}
        grep -o "pthread_[a-z_]*" {helgrind_output_file} | sort | uniq -c | head -10 >> {summary_file} 2>/dev/null || echo "None detected" >> {summary_file}
    else
        echo "No detailed thread information available" >> {summary_file}
    fi

    echo "" >> {summary_file}

    # Error severity assessment
    echo "=== Error Severity Assessment ===" >> {summary_file}
    total_errors=$(grep -c "Possible data race\\|lock order\\|Thread #" {helgrind_output_file} 2>/dev/null || echo "0")
    if [ "$' + '{total_errors:-0}" -eq 0 ] 2>/dev/null; then
        echo "✓ No thread errors detected - program appears thread-safe" >> {summary_file}
    elif [ "$' + '{total_errors:-0}" -le 5 ] 2>/dev/null; then
        echo "⚠ Low severity: $' + '{total_errors:-0} potential thread issues found" >> {summary_file}
    elif [ "$' + '{total_errors:-0}" -le 20 ] 2>/dev/null; then
        echo "⚠ Medium severity: $' + '{total_errors:-0} thread issues found" >> {summary_file}
    else
        echo "🚨 High severity: $' + '{total_errors:-0} thread issues found - review recommended" >> {summary_file}
    fi

else
    echo "Helgrind output file not found - analysis cannot be performed" >> {summary_file}
    echo "This may indicate Valgrind/Helgrind was not available or failed to run" >> {summary_file}
fi

echo "" >> {summary_file}
echo "Analysis complete. For detailed information, examine the full Helgrind log." >> {summary_file}
"""

        command_builder.add_post_processing(
            input_file=helgrind_output_file,
            output_file=summary_file,
            processing_command=analysis_command.strip(),
            description="Helgrind thread error analysis and summary generation",
            file_type="helgrind_summary",
        )

        # Add detailed race condition analysis if configured
        generate_detailed_analysis = self._get_config_value(
            "generate_detailed_analysis"
        )

        if generate_detailed_analysis:
            detailed_file = command_builder.register_output_file(
                file_type="helgrind_detailed",
                extension="detailed.txt",
                description="Detailed Helgrind race condition analysis",
            )

            detailed_command = f"""
echo "=== Detailed Helgrind Analysis for {service_name} ===" > {detailed_file}
echo "" >> {detailed_file}

if [ -f "{helgrind_output_file}" ]; then
    echo "=== All Detected Race Conditions ===" >> {detailed_file}
    grep -A 10 "Possible data race" {helgrind_output_file} >> {detailed_file} 2>/dev/null || echo "No race conditions found" >> {detailed_file}

    echo "" >> {detailed_file}
    echo "=== Lock Order Violations ===" >> {detailed_file}
    grep -A 15 "lock order" {helgrind_output_file} >> {detailed_file} 2>/dev/null || echo "No lock order violations found" >> {detailed_file}

    echo "" >> {detailed_file}
    echo "=== Thread API Issues ===" >> {detailed_file}
    grep -A 5 "pthread_" {helgrind_output_file} | head -50 >> {detailed_file} 2>/dev/null || echo "No thread API issues found" >> {detailed_file}
else
    echo "Helgrind output file not found for detailed analysis" >> {detailed_file}
fi
"""

            command_builder.add_post_processing(
                input_file=helgrind_output_file,
                output_file=detailed_file,
                processing_command=detailed_command.strip(),
                description="detailed Helgrind race condition analysis",
                file_type="helgrind_detailed",
            )

    def to_command(
        self, pid: Optional[int] = None, output_file: Optional[str] = None
    ) -> str:
        """
        Generate the Helgrind command for execution.

        Args:
            pid: Optional process ID to attach to
            output_file: Optional output file path

        Returns:
            str: Command string for Helgrind wrapper
        """
        if output_file is None:
            output_file = self._get_config_value("output_file", "/tmp/helgrind.log")

        # Note: pid parameter is not directly supported by Helgrind (runs from start)
        if pid:
            self.logger.warning(
                "PID parameter (%d) not supported - Helgrind must run from process start",
                pid,
            )

        # Use the same command building logic as the wrapper
        return self._build_helgrind_command(output_file)

    def update_environment(
        self,
        execution_environment,
        global_config,
        plugin_manager,
        services_managers,
        test_config,
    ) -> None:
        """
        Update environment for helgrind execution.

        Args:
            execution_environment: Current execution environment
            global_config: Global configuration
            plugin_manager: Plugin manager instance
            services_managers: List of service managers
            test_config: Test configuration
        """
        # Add any helgrind-specific environment updates here
        self.logger.debug("Updated environment for helgrind execution")
        pass
