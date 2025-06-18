from typing import TYPE_CHECKING, Dict, List, Optional, Tuple, Union

"""
Refactored strace execution environment using shared command generation utilities.

This demonstrates how the shared utilities work with different command patterns
while maintaining the specific functionality of strace.
"""

from panther.core.observer.management.event_manager import EventManager
from panther.plugins.environments.execution_environment.base_execution_environment import (
    BaseExecutionEnvironment,
)
from panther.plugins.environments.execution_environment.command_generation_utils import (
    create_execution_environment_builder,
)
from panther.plugins.environments.execution_environment.strace.config_schema import (
    StraceConfig,
)
from panther.plugins.plugin_decorators import register_plugin
from panther.plugins.services.services_interface import IServiceManager

if TYPE_CHECKING:
    pass


@register_plugin(
    plugin_type="environment",
    name="strace",
    version="1.0.0",
    description="System call tracing execution environment",
    author="PANTHER Team",
    capabilities=["syscall_tracing", "performance_analysis", "debugging"],
    external_dependencies=["strace>=4.0"],
)
class StraceEnvironment(BaseExecutionEnvironment):
    """

    System call tracing execution environment using strace.

    This environment uses shared command generation utilities while maintaining
    the specific strace command building logic.
    """

    def __init__(
        self,
        env_config_to_test: StraceConfig,
        output_dir: str,
        env_type: str,
        env_sub_type: str,
        event_manager: EventManager,
    ):
        """Initialize the strace environment."""
        super().__init__(
            env_config_to_test, output_dir, env_type, env_sub_type, event_manager
        )

    def get_output_patterns(self) -> List[Tuple[str, str]]:
        """
        Get strace-specific output patterns.

        Returns:
            List of (output_type, filename_pattern) tuples
        """
        return [
            ("strace_log", "strace_{service_name}.log"),
            ("strace_summary", "strace_summary_{service_name}.txt"),
            ("syscall_stats", "strace_stats_{service_name}.log"),
            ("timing", "strace_timing_{service_name}.log"),
        ]

    def get_additional_output_discovery_patterns(self) -> Dict[str, List[str]]:
        """
        Get additional strace discovery patterns.

        Returns:
            Dict mapping output types to lists of glob patterns
        """
        return {
            "strace_child": ["strace_*_child_*.log"],
            "strace_error": ["*strace*.err", "*strace*error*"],
            "strace_filtered": ["strace_filtered_*.log"],
        }

    def _setup_plugin_specific_environment(
        self, services_managers: List[IServiceManager], timestamp: str
    ):
        """
        Set up strace tracing for all services using shared utilities.

        Args:
            services_managers: List of service managers to potentially modify
            timestamp: Timestamp for this execution (used for file naming)
        """
        self.logger.info(
            f"Setting up strace environment for {len(services_managers)} services"
        )

        for service in services_managers:
            service_name = getattr(service, "service_name", service.__class__.__name__)
            self.logger.info(f"Configuring strace for service: {service_name}")

            # Create command builder using shared utilities
            command_builder = create_execution_environment_builder(
                service=service,
                environment_name="strace",
                timestamp=timestamp,
                register_output_callback=self.register_output_file,
                logger=self.logger,
            )

            # Register output files and get their paths
            strace_output_file = command_builder.register_output_file(
                file_type="strace_log",
                extension="log",
                description="System call trace log",
            )

            strace_summary_file = command_builder.register_output_file(
                file_type="strace_summary",
                extension="txt",
                description="Strace analysis summary",
            )

            self.logger.info(f"Registered strace output files for {service_name}:")
            self.logger.info(f"  Log file: {strace_output_file}")
            self.logger.info(f"  Summary file: {strace_summary_file}")

            # Build the strace command using the utility method
            strace_cmd = self._build_strace_command(strace_output_file)
            self.logger.info(f"Built strace command for {service_name}: {strace_cmd}")

            # Add the strace wrapper
            command_builder.add_wrapper_command(
                wrapper_command=strace_cmd,
                description=f"Setup strace wrapper for {command_builder.service_name}",
                additional_env_vars={"STRACE_OUTPUT": strace_output_file},
                is_critical=False,
            )

            # Add comprehensive post-processing for strace analysis
            self._add_strace_analysis_commands(
                command_builder, strace_output_file, strace_summary_file
            )

            # Build and apply all commands to the service
            results = command_builder.build_and_apply(self.modify_service_commands)

            self.logger.info(
                "Successfully configured strace for service %s",
                command_builder.service_name,
            )
            self.logger.info("Applied modifications: %s", results)

            # Log the final service command structure for debugging
            if hasattr(service, "run_cmd"):
                self.logger.debug(
                    f"Final service run_cmd for {service_name}: {service.run_cmd}"
                )
            else:
                self.logger.warning(f"Service {service_name} has no run_cmd attribute")

    def _build_strace_command(self, output_file: str) -> str:
        """
        Build the strace command with configured options.

        Args:
            output_file: Path to write strace output

        Returns:
            str: Complete strace command
        """
        # Create directory for output file to ensure it can be written
        output_dir = "/".join(output_file.split("/")[:-1])
        mkdir_cmd = f"mkdir -p {output_dir}"

        command_parts = [self.env_config_to_test.strace_binary]

        # Add output file
        command_parts.extend(["-o", output_file])

        # Include kernel stack if enabled
        if self.env_config_to_test.include_kernel_stack:
            command_parts.append("-k")

        # Add timestamp information (simplified approach)
        command_parts.append("-tt")

        # Exclude specified syscalls
        if self.env_config_to_test.excluded_syscalls:
            excluded = ",".join(self.env_config_to_test.excluded_syscalls)
            command_parts.extend(["-e", f"trace=!{excluded}"])

        # Focus on network syscalls if enabled
        if self.env_config_to_test.trace_network_syscalls:
            network_syscalls = "network,read,write,send,recv,connect,bind,listen,accept"
            command_parts.extend(["-e", f"trace={network_syscalls}"])

        strace_cmd = " ".join(command_parts)

        # Add timeout if specified
        if self.env_config_to_test.timeout:
            # Note: strace doesn't have built-in timeout, use timeout command
            strace_cmd = f"timeout {self.env_config_to_test.timeout} {strace_cmd}"

        # Add any additional parameters
        if self.env_config_to_test.additional_parameters:
            additional = " ".join(self.env_config_to_test.additional_parameters)
            strace_cmd = f"{strace_cmd} {additional}"

        # Return command with directory creation
        return f"{mkdir_cmd} && {strace_cmd}"

    def _add_strace_analysis_commands(
        self, command_builder, strace_output_file: str, summary_file: str
    ):
        """
        Add comprehensive strace analysis post-processing commands.

        Args:
            command_builder: The command builder to add commands to
            strace_output_file: Path to the strace output file
            summary_file: Path to the summary file to generate
        """
        service_name = command_builder.service_name

        # Generate comprehensive strace summary
        analysis_command = f"""
echo "=== Strace Analysis for {service_name} ===" > {summary_file}
echo "Generated at: $(date)" >> {summary_file}
echo "Strace output file: {strace_output_file}" >> {summary_file}
echo "" >> {summary_file}

# System call counts
echo "=== Top 20 System Calls ===" >> {summary_file}
if [ -f "{strace_output_file}" ]; then
    grep -oE '^[a-zA-Z_]+\\(' {strace_output_file} | sed 's/($//' | Union[sort, uniq]-c | sort -nr | head -20 >> {summary_file} 2>/dev/null || echo "No system calls found" >> {summary_file}
else
    echo "Strace output file not found" >> {summary_file}
fi

echo "" >> {summary_file}

# Network activity analysis
echo "=== Network Activity Summary ===" >> {summary_file}
if [ -f "{strace_output_file}" ]; then
    echo "Network system calls:" >> {summary_file}
    grep -E '(Union[socket, connect, bind, listen, accept, send, recv])\\(' {strace_output_file} | wc -l >> {summary_file} 2>/dev/null || echo "0" >> {summary_file}

    echo "File I/O operations:" >> {summary_file}
    grep -E '(Union[read, write, open, close])\\(' {strace_output_file} | wc -l >> {summary_file} 2>/dev/null || echo "0" >> {summary_file}
else
    echo "No network activity data available" >> {summary_file}
fi

echo "" >> {summary_file}

# Error analysis
echo "=== Error Analysis ===" >> {summary_file}
if [ -f "{strace_output_file}" ]; then
    echo "Common errors found:" >> {summary_file}
    grep -E 'EACCES|ENOENT|EPERM|ECONNREFUSED|ETIMEDOUT|EADDRINUSE' {strace_output_file} | cut -d' ' -f1 | Union[sort, uniq]-c | sort -nr >> {summary_file} 2>/dev/null || echo "No errors found" >> {summary_file}
else
    echo "No error data available" >> {summary_file}
fi

echo "" >> {summary_file}

# Performance insights
echo "=== Performance Insights ===" >> {summary_file}
if [ -f "{strace_output_file}" ]; then
    echo "Process lifecycle:" >> {summary_file}
    grep -E '(Union[execve, fork, clone, exit_group])\\(' {strace_output_file} | wc -l >> {summary_file} 2>/dev/null || echo "0 lifecycle events" >> {summary_file}

    echo "Signal handling:" >> {summary_file}
    grep -E '(Union[signal, kill, sigaction])\\(' {strace_output_file} | wc -l >> {summary_file} 2>/dev/null || echo "0 signal events" >> {summary_file}
else
    echo "No performance data available" >> {summary_file}
fi

echo "Analysis complete" >> {summary_file}
"""

        command_builder.add_post_processing(
            input_file=strace_output_file,
            output_file=summary_file,
            processing_command=analysis_command.strip(),
            description="strace analysis and summary generation",
            file_type="strace_summary",
        )

        # Add optional detailed analysis if configured
        if (
            hasattr(self.env_config_to_test, "generate_detailed_analysis")
            and self.env_config_to_test.generate_detailed_analysis
        ):
            detailed_file = command_builder.register_output_file(
                file_type="strace_detailed",
                extension="detailed.txt",
                description="Detailed strace analysis",
            )

            detailed_command = f"""
echo "=== Detailed Strace Analysis for {service_name} ===" > {detailed_file}
echo "" >> {detailed_file}

if [ -f "{strace_output_file}" ]; then
    echo "=== All Unique System Calls ===" >> {detailed_file}
    grep -oE '^[a-zA-Z_]+\\(' {strace_output_file} | sed 's/($//' | sort -u >> {detailed_file} 2>/dev/null

    echo "" >> {detailed_file}
    echo "=== File Operations ===" >> {detailed_file}
    grep -E '(Union[open, openat, creat])\\(' {strace_output_file} | head -50 >> {detailed_file} 2>/dev/null || echo "No file operations found" >> {detailed_file}

    echo "" >> {detailed_file}
    echo "=== Network Operations ===" >> {detailed_file}
    grep -E '(Union[socket, connect, bind, listen])\\(' {strace_output_file} | head -50 >> {detailed_file} 2>/dev/null || echo "No network operations found" >> {detailed_file}
else
    echo "Strace output file not found for detailed analysis" >> {detailed_file}
fi
"""

            command_builder.add_post_processing(
                input_file=strace_output_file,
                output_file=detailed_file,
                processing_command=detailed_command.strip(),
                description="detailed strace analysis",
                file_type="strace_detailed",
            )

    def to_command(
        self, pid: Optional[int] = None, output_file: Optional[str] = None
    ) -> str:
        """
        Generate the strace command for execution.

        Args:
            pid: Optional process ID to attach to
            output_file: Optional output file path

        Returns:
            str: Command string for strace wrapper
        """
        if output_file is None:
            output_file = self.env_config_to_test.output_file or "/tmp/strace.log"

        # Use the same command building logic as the wrapper
        return self._build_strace_command(output_file)

    def update_environment(
        self,
        execution_environment,
        global_config,
        plugin_manager,
        services_managers,
        test_config,
    ) -> None:
        """
        Update environment for strace execution.

        This method is called to update the environment configuration
        for strace-specific requirements.

        Args:
            execution_environment: Current execution environment
            global_config: Global configuration
            plugin_manager: Plugin manager instance
            services_managers: List of service managers
            test_config: Test configuration
        """
        # Add any strace-specific environment updates here
        # For now, this is a no-op as strace doesn't require
        # special environment modifications
        self.logger.debug("Updated environment for strace execution")
        pass
