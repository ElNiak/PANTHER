from typing import TYPE_CHECKING, List, Optional

"""
Memcheck execution environment for memory error detection using Valgrind.

This plugin provides comprehensive memory error detection capabilities including
memory leak detection, invalid memory access detection, and uninitialized value usage.
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
from panther.plugins.environments.execution_environment.memcheck.config_schema import (
    MemcheckConfig,
)
from panther.plugins.services.services_interface import IServiceManager

if TYPE_CHECKING:
    pass


@register_plugin(
    plugin_type=PluginType.EXECUTION_ENVIRONMENT,
    name="memcheck",
    version="1.0.0",
    description="Valgrind Memcheck memory error detection environment",
    author="PANTHER Team",
    capabilities=[
        "memory_error_detection",
        "leak_detection",
        "invalid_access_detection",
    ],
    external_dependencies=["valgrind>=3.15"],
    runtime_mode="debug",  # Set to debug mode for comprehensive error detection
)
class MemcheckEnvironment(BaseExecutionEnvironment):
    """

    Memory error detection execution environment using Valgrind Memcheck.

    This environment uses shared command generation utilities to eliminate
    code duplication while providing comprehensive memory error detection.
    """

    def __init__(
        self,
        env_config_to_test: MemcheckConfig,
        output_dir: str,
        env_type: str,
        env_sub_type: str,
        event_manager: EventManager,
    ):
        """Initialize the Memcheck environment."""
        super().__init__(
            env_config_to_test, output_dir, env_type, env_sub_type, event_manager
        )

        # Initialize plugin config cache
        self._plugin_config = None

    def _get_plugin_config(self) -> MemcheckConfig:
        """Get plugin config with caching and fallback."""
        if self._plugin_config is None:
            try:
                self._plugin_config = self.env_config_to_test.get_plugin_config(
                    MemcheckConfig
                )
            except Exception as e:
                self.logger.debug(f"Could not get plugin config, using defaults: {e}")
                self._plugin_config = MemcheckConfig()
        return self._plugin_config

    def _get_config_value(self, field_name: str, default=None):
        """Helper method to get config value using dual approach."""
        # First try plugin_config dict
        value = None
        if (
            hasattr(self.env_config_to_test, "plugin_config")
            and self.env_config_to_test.plugin_config
        ):
            value = self.env_config_to_test.plugin_config.get(field_name)

        # Second try typed config
        if value is None:
            plugin_config = self._get_plugin_config()
            if hasattr(plugin_config, field_name):
                value = getattr(plugin_config, field_name)

        # Return value or default
        return value if value is not None else default

    def _setup_plugin_specific_environment(
        self, services_managers: List[IServiceManager], timestamp: str
    ):
        """
        Set up Valgrind Memcheck memory error detection for services using shared utilities.

        Args:
            services_managers: List of service managers to potentially modify
            timestamp: Timestamp for this execution (used for file naming)
        """
        for service in services_managers:
            # Create command builder using shared utilities
            command_builder = create_execution_environment_builder(
                service=service,
                environment_name="memcheck",
                timestamp=timestamp,
                register_output_callback=self.register_output_file,
                logger=self.logger,
            )

            # Register output files and get their paths
            memcheck_output_file = command_builder.register_output_file(
                file_type="memcheck_log",
                extension="log",
                description="Memcheck memory error detection log",
            )

            memcheck_summary_file = command_builder.register_output_file(
                file_type="memcheck_summary",
                extension="txt",
                description="Memcheck analysis summary",
            )

            # Build the Memcheck command using Valgrind
            memcheck_cmd = self._build_memcheck_command(memcheck_output_file)

            # Add the Memcheck wrapper with conditional check for Valgrind
            command_builder.add_conditional_wrapper(
                condition="command -v valgrind >/dev/null 2>&1",
                wrapper_command=memcheck_cmd,
                description=f"Setup Memcheck wrapper for {command_builder.service_name}",
                fallback_message="Valgrind not found - Memcheck memory error detection disabled",
                is_critical=False,
            )

            # Add comprehensive post-processing for memory error analysis
            self._add_memcheck_analysis_commands(
                command_builder, memcheck_output_file, memcheck_summary_file
            )

            # Build and apply all commands to the service
            results = command_builder.build_and_apply(self.modify_service_commands)

            self.logger.info(
                "Successfully configured Memcheck for service %s",
                command_builder.service_name,
            )
            self.logger.debug("Applied modifications: %s", results)

    def _build_memcheck_command(self, output_file: str) -> str:
        """
        Build the Memcheck command with configured options.

        Args:
            output_file: Path to write Memcheck output

        Returns:
            str: Complete Memcheck command
        """
        plugin_config = self._get_plugin_config()
        command_parts = ["valgrind", "--tool=memcheck"]

        # Add output file
        command_parts.extend([f"--log-file={output_file}"])

        # Set output format using dual approach
        output_format = None
        if (
            hasattr(self.env_config_to_test, "plugin_config")
            and self.env_config_to_test.plugin_config
        ):
            output_format = self.env_config_to_test.plugin_config.get("output_format")
        if output_format is None and hasattr(plugin_config, "output_format"):
            output_format = plugin_config.output_format

        if output_format == "xml":
            command_parts.extend(("--xml=yes", f"--xml-file={output_file}.xml"))
            # Get xml_user_comment using dual approach
            xml_user_comment = None
            if (
                hasattr(self.env_config_to_test, "plugin_config")
                and self.env_config_to_test.plugin_config
            ):
                xml_user_comment = self.env_config_to_test.plugin_config.get(
                    "xml_user_comment"
                )
            if xml_user_comment is None and hasattr(plugin_config, "xml_user_comment"):
                xml_user_comment = plugin_config.xml_user_comment

            if xml_user_comment:
                command_parts.append(f"--xml-user-comment={xml_user_comment}")

        # Leak checking options using helper
        leak_check = self._get_config_value("leak_check", "full")
        command_parts.append(f"--leak-check={leak_check}")

        leak_resolution = self._get_config_value("leak_resolution", "high")
        command_parts.append(f"--leak-resolution={leak_resolution}")

        show_leak_kinds = self._get_config_value("show_leak_kinds", "all")
        command_parts.append(f"--show-leak-kinds={show_leak_kinds}")

        errors_for_leak_kinds = self._get_config_value("errors_for_leak_kinds", "all")
        command_parts.append(f"--errors-for-leak-kinds={errors_for_leak_kinds}")

        leak_check_heuristics = self._get_config_value("leak_check_heuristics", "all")
        command_parts.append(f"--leak-check-heuristics={leak_check_heuristics}")

        if show_reachable := self._get_config_value("show_reachable"):
            command_parts.append(f"--show-reachable={show_reachable}")

        if show_possibly_lost := self._get_config_value("show_possibly_lost"):
            command_parts.append(f"--show-possibly-lost={show_possibly_lost}")

        if xtree_leak := self._get_config_value("xtree_leak"):
            command_parts.append("--xtree-leak=yes")
            xtree_leak_file = self._get_config_value(
                "xtree_leak_file", "xtree_leak.kcg"
            )
            command_parts.append(f"--xtree-leak-file={xtree_leak_file}")

        # Error detection options
        undef_value_errors = self._get_config_value("undef_value_errors", True)
        if not undef_value_errors:
            command_parts.append("--undef-value-errors=no")

        track_origins = self._get_config_value("track_origins")
        if track_origins:
            command_parts.append("--track-origins=yes")

        partial_loads_ok = self._get_config_value("partial_loads_ok", True)
        if not partial_loads_ok:
            command_parts.append("--partial-loads-ok=no")

        expensive_definedness_checks = self._get_config_value(
            "expensive_definedness_checks", "auto"
        )
        command_parts.append(
            f"--expensive-definedness-checks={expensive_definedness_checks}"
        )

        keep_stacktraces = self._get_config_value("keep_stacktraces", "alloc-and-free")
        command_parts.append(f"--keep-stacktraces={keep_stacktraces}")

        # Memory management options
        freelist_vol = self._get_config_value("freelist_vol", 20000000)
        command_parts.append(f"--freelist-vol={freelist_vol}")

        freelist_big_blocks = self._get_config_value("freelist_big_blocks", 1000000)
        command_parts.append(f"--freelist-big-blocks={freelist_big_blocks}")

        # Special handling options
        workaround_gcc296_bugs = self._get_config_value("workaround_gcc296_bugs")
        if workaround_gcc296_bugs:
            command_parts.append("--workaround-gcc296-bugs=yes")

        ignore_range_below_sp = self._get_config_value("ignore_range_below_sp")
        if ignore_range_below_sp:
            command_parts.append(f"--ignore-range-below-sp={ignore_range_below_sp}")

        show_mismatched_frees = self._get_config_value("show_mismatched_frees", True)
        if not show_mismatched_frees:
            command_parts.append("--show-mismatched-frees=no")

        show_realloc_size_zero = self._get_config_value("show_realloc_size_zero", True)
        if not show_realloc_size_zero:
            command_parts.append("--show-realloc-size-zero=no")

        ignore_ranges = self._get_config_value("ignore_ranges")
        if ignore_ranges:
            command_parts.append(f"--ignore-ranges={ignore_ranges}")

        # Fill options
        malloc_fill = self._get_config_value("malloc_fill")
        if malloc_fill:
            command_parts.append(f"--malloc-fill={malloc_fill}")

        free_fill = self._get_config_value("free_fill")
        if free_fill:
            command_parts.append(f"--free-fill={free_fill}")

        # Suppression file
        suppression_file = self._get_config_value("suppression_file")
        if suppression_file:
            command_parts.append(f"--suppressions={suppression_file}")

        # Generate suppressions
        generate_suppressions = self._get_config_value("generate_suppressions")
        if generate_suppressions:
            command_parts.append("--gen-suppressions=all")

        # Additional parameters
        additional_parameters = self._get_config_value("additional_parameters")
        if additional_parameters:
            command_parts.extend(additional_parameters)

        return " ".join(command_parts)

    def _add_memcheck_analysis_commands(
        self, command_builder, memcheck_output_file: str, summary_file: str
    ):
        """
        Add comprehensive Memcheck analysis post-processing commands.

        Args:
            command_builder: The command builder to add commands to
            memcheck_output_file: Path to the Memcheck output file
            summary_file: Path to the summary file to generate
        """
        service_name = command_builder.service_name

        # Generate comprehensive Memcheck analysis
        analysis_command = f"""
echo "=== Memcheck Memory Error Analysis for {service_name} ===" > {summary_file}
echo "Generated at: $(date)" >> {summary_file}
echo "Memcheck output file: {memcheck_output_file}" >> {summary_file}
echo "" >> {summary_file}

# Check if Memcheck output exists
if [ -f "{memcheck_output_file}" ]; then
    echo "=== Memory Error Summary ===" >> {summary_file}

    # Count different types of errors
    echo "Invalid read/write operations:" >> {summary_file}
    grep -c "Invalid read\\|Invalid write" {memcheck_output_file} 2>/dev/null || echo "0" >> {summary_file}

    echo "Use of uninitialized values:" >> {summary_file}
    grep -c "Conditional jump or move depends on uninitialised value\\|Use of uninitialised value" {memcheck_output_file} 2>/dev/null || echo "0" >> {summary_file}

    echo "Memory leaks detected:" >> {summary_file}
    grep -c "definitely lost\\|indirectly lost\\|possibly lost" {memcheck_output_file} 2>/dev/null || echo "0" >> {summary_file}

    echo "Invalid free operations:" >> {summary_file}
    grep -c "Invalid free\\|Mismatched free" {memcheck_output_file} 2>/dev/null || echo "0" >> {summary_file}

    echo "" >> {summary_file}

    # Memory leak details
    echo "=== Memory Leak Analysis ===" >> {summary_file}
    if grep -q "LEAK SUMMARY" {memcheck_output_file} 2>/dev/null; then
        echo "Leak summary found:" >> {summary_file}
        grep -A 10 "LEAK SUMMARY" {memcheck_output_file} | head -15 >> {summary_file} 2>/dev/null
    else
        echo "No memory leaks detected" >> {summary_file}
    fi

    echo "" >> {summary_file}

    # Invalid access analysis
    echo "=== Invalid Memory Access Analysis ===" >> {summary_file}
    if grep -q "Invalid read\\|Invalid write" {memcheck_output_file} 2>/dev/null; then
        echo "Invalid memory access detected - critical errors found" >> {summary_file}
        grep -B 2 -A 3 "Invalid read\\|Invalid write" {memcheck_output_file} | head -20 >> {summary_file} 2>/dev/null
    else
        echo "No invalid memory access detected" >> {summary_file}
    fi

    echo "" >> {summary_file}

    # Uninitialized value usage
    echo "=== Uninitialized Value Usage ===" >> {summary_file}
    if grep -q "uninitialised value" {memcheck_output_file} 2>/dev/null; then
        echo "Uninitialized value usage detected" >> {summary_file}
        uninit_count=$(grep -c "uninitialised value" {memcheck_output_file} 2>/dev/null || echo "0")
        echo "Total uninitialized value issues: $uninit_count" >> {summary_file}
    else
        echo "No uninitialized value usage detected" >> {summary_file}
    fi

    echo "" >> {summary_file}

    # Error severity assessment
    echo "=== Error Severity Assessment ===" >> {summary_file}

    # Count critical errors
    critical_errors=$(grep -c "Invalid read\\|Invalid write\\|Invalid free" {memcheck_output_file} 2>/dev/null || echo "0")
    leak_errors=$(grep -c "definitely lost\\|indirectly lost" {memcheck_output_file} 2>/dev/null || echo "0")
    possible_leaks=$(grep -c "possibly lost" {memcheck_output_file} 2>/dev/null || echo "0")
    uninit_errors=$(grep -c "uninitialised value" {memcheck_output_file} 2>/dev/null || echo "0")

    total_errors=$((critical_errors + leak_errors + possible_leaks + uninit_errors))

    if [ "$critical_errors" -gt 0 ]; then
        echo "🚨 CRITICAL: $critical_errors memory corruption errors found" >> {summary_file}
        echo "   These indicate serious bugs that can cause crashes or security issues" >> {summary_file}
    elif [ "$leak_errors" -gt 0 ]; then
        echo "⚠ HIGH: $leak_errors definite memory leaks found" >> {summary_file}
        echo "   Memory is not being properly freed" >> {summary_file}
    elif [ "$possible_leaks" -gt 0 ]; then
        echo "⚠ MEDIUM: $possible_leaks possible memory leaks found" >> {summary_file}
        echo "   Review code to ensure proper memory management" >> {summary_file}
    elif [ "$uninit_errors" -gt 0 ]; then
        echo "⚠ LOW: $uninit_errors uninitialized value issues found" >> {summary_file}
        echo "   Variables may not be properly initialized" >> {summary_file}
    else
        echo "✓ No memory errors detected - program appears memory-safe" >> {summary_file}
    fi

    echo "" >> {summary_file}
    echo "Total issues found: $total_errors" >> {summary_file}

else
    echo "Memcheck output file not found - analysis cannot be performed" >> {summary_file}
    echo "This may indicate Valgrind/Memcheck was not available or failed to run" >> {summary_file}
fi

echo "" >> {summary_file}
echo "Analysis complete. For detailed information, examine the full Memcheck log." >> {summary_file}
"""

        command_builder.add_post_processing(
            input_file=memcheck_output_file,
            output_file=summary_file,
            processing_command=analysis_command.strip(),
            description="Memcheck memory error analysis and summary generation",
            file_type="memcheck_summary",
        )

        # Add detailed leak analysis if configured for full leak checking
        leak_check = self._get_config_value("leak_check", "full")
        if leak_check in ["yes", "full"]:
            leak_detail_file = command_builder.register_output_file(
                file_type="memcheck_leaks",
                extension="detailed.txt",
                description="Detailed Memcheck leak analysis",
            )

            leak_command = f"""
echo "=== Detailed Memory Leak Analysis for {service_name} ===" > {leak_detail_file}
echo "" >> {leak_detail_file}

if [ -f "{memcheck_output_file}" ]; then
    echo "=== All Detected Memory Leaks ===" >> {leak_detail_file}
    grep -A 20 "definitely lost\\|indirectly lost\\|possibly lost" {memcheck_output_file} >> {leak_detail_file} 2>/dev/null || echo "No memory leaks found" >> {leak_detail_file}

    echo "" >> {leak_detail_file}
    echo "=== Leak Stack Traces ===" >> {leak_detail_file}
    grep -A 15 "bytes in [0-9]* blocks are definitely lost" {memcheck_output_file} >> {leak_detail_file} 2>/dev/null || echo "No definite leak stack traces found" >> {leak_detail_file}
else
    echo "Memcheck output file not found for detailed leak analysis" >> {leak_detail_file}
fi
"""

            command_builder.add_post_processing(
                input_file=memcheck_output_file,
                output_file=leak_detail_file,
                processing_command=leak_command.strip(),
                description="Detailed Memcheck leak analysis",
                file_type="memcheck_leaks",
            )

    def to_command(
        self, pid: Optional[int] = None, output_file: Optional[str] = None
    ) -> str:
        """
        Generate the Memcheck command for execution.

        Args:
            pid: Optional process ID to attach to
            output_file: Optional output file path

        Returns:
            str: Command string for Memcheck wrapper
        """
        if output_file is None:
            # Get output_file using dual approach
            output_file_value = self._get_config_value("output_file")
            output_file = output_file_value or "/tmp/memcheck.log"

        # Note: pid parameter is not directly supported by Memcheck (runs from start)
        if pid:
            self.logger.warning(
                "PID parameter (%d) not supported - Memcheck must run from process start",
                pid,
            )

        # Use the same command building logic as the wrapper
        return self._build_memcheck_command(output_file)

    def update_environment(
        self,
        execution_environment,
        global_config,
        plugin_manager,
        services_managers,
        test_config,
    ) -> None:
        """
        Update environment for memcheck execution.

        Args:
            execution_environment: Current execution environment
            global_config: Global configuration
            plugin_manager: Plugin manager instance
            services_managers: List of service managers
            test_config: Test configuration
        """
        # Add any memcheck-specific environment updates here
        self.logger.debug("Updated environment for memcheck execution")
        pass
