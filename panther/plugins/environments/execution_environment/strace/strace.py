"""
Refactored strace execution environment using shared command generation utilities.

This demonstrates how the shared utilities work with different command patterns
while maintaining the specific functionality of strace.
"""
import platform
from typing import TYPE_CHECKING, Dict, List, Optional, Tuple, Union

from panther.core.observer.management.event_manager import EventManager
from panther.plugins.core.plugin_decorators import register_plugin
from panther.plugins.core.structures.plugin_type import PluginType
from panther.plugins.environments.execution_environment.base_execution_environment import (
    BaseExecutionEnvironment,
)
from panther.plugins.environments.execution_environment.command_generation_utils import (
    create_execution_environment_builder,
)
from panther.plugins.environments.execution_environment.strace.config_schema import (
    StraceConfig,
)
from panther.plugins.services.services_interface import IServiceManager

if TYPE_CHECKING:
    pass


@register_plugin(
    plugin_type=PluginType.EXECUTION_ENVIRONMENT,
    name="strace",
    version="1.0.0",
    description="System call tracing execution environment",
    author="PANTHER Team",
    capabilities=["syscall_tracing", "performance_analysis", "debugging"],
    external_dependencies=["strace>=4.0"],
    runtime_mode="debug",
)
class StraceEnvironment(BaseExecutionEnvironment):
    """
    System Call Tracing Execution Environment - strace Integration

    StraceEnvironment provides comprehensive system call tracing capabilities for PANTHER protocol testing
    using the strace tool. This execution environment wraps service execution with detailed system call
    monitoring, enabling deep analysis of service behavior, network operations, file I/O patterns,
    and performance characteristics.

    ## Architecture Integration

    The strace environment extends BaseExecutionEnvironment to provide:

    1. **System Call Instrumentation**: Comprehensive tracing of all system calls made by services
    2. **Network Analysis**: Focused monitoring of network-related system calls (socket, connect, etc.)
    3. **Performance Insights**: Timing analysis and syscall frequency statistics
    4. **Error Detection**: Capture and analysis of system call errors and failures
    5. **Multi-Process Support**: Tracing of child processes and process trees

    ```mermaid
    sequenceDiagram
        participant NE as NetworkEnvironment
        participant SE as StraceEnvironment
        participant ST as StraceWrapper
        participant SV as Service

        NE->>SE: setup_environment()
        SE->>SE: configure_strace_options()
        SE->>ST: create_wrapper_command()

        NE->>SV: start_service()
        SV->>ST: execute_with_strace()
        ST->>ST: log_system_calls()

        Note over ST,SV: Service Execution + Tracing

        NE->>SE: teardown_environment()
        SE->>SE: analyze_trace_output()
        SE->>SE: generate_summary_reports()
    ```

    ## System Call Analysis Capabilities

    ### Core Tracing Features
    - **Complete Syscall Coverage**: Traces all system calls with arguments and return values
    - **Timing Information**: Microsecond-precision timing for performance analysis
    - **Process Tree Tracking**: Follows fork(), clone(), and execve() to trace child processes
    - **Signal Monitoring**: Captures signal delivery and handling
    - **File Descriptor Tracking**: Monitors file and socket operations with full path resolution

    ### Network-Specific Analysis
    - **Socket Operations**: Detailed tracing of socket(), bind(), listen(), accept(), connect()
    - **Data Transfer**: Monitoring of send(), recv(), read(), write() with data sizes
    - **Protocol Analysis**: Identifies network protocols and connection patterns
    - **Error Detection**: Captures network errors like ECONNREFUSED, ETIMEDOUT, EADDRINUSE

    ### Performance Metrics
    - **Syscall Frequency**: Statistical analysis of most frequently called system calls
    - **Execution Time**: Timing analysis for performance bottleneck identification
    - **Resource Usage**: File descriptor usage, memory allocation patterns
    - **Error Rates**: System call failure rates and error pattern analysis

    ## Configuration Options

    The strace environment supports extensive configuration through StraceConfig:

    ### Basic Options
    - `strace_binary`: Path to strace executable (default: "strace")
    - `output_file`: Base output file path for trace logs
    - `timeout`: Maximum execution time for strace (disabled by default)
    - `include_kernel_stack`: Include kernel stack traces (x86_64 only)

    ### Tracing Scope
    - `trace_all_syscalls`: Trace all system calls vs. network-focused subset
    - `trace_network_syscalls`: Focus on network-related system calls
    - `excluded_syscalls`: List of system calls to exclude from tracing
    - `additional_parameters`: Custom strace command-line parameters

    ### Analysis Options
    - `generate_detailed_analysis`: Enable comprehensive post-processing analysis
    - Analysis includes syscall statistics, network activity summary, error analysis

    ## Output Generation and Analysis

    ### Primary Output Files
    1. **strace_log**: Raw system call trace with full details
       - File pattern: `strace_{service_name}.log`
       - Contains: Complete syscall trace with arguments, return values, timing

    2. **strace_summary**: Automated analysis summary
       - File pattern: `strace_summary_{service_name}.txt`
       - Contains: Top syscalls, network activity, error analysis, performance insights

    3. **strace_detailed**: Extended analysis (optional)
       - File pattern: `strace_detailed_{service_name}.detailed.txt`
       - Contains: Complete syscall catalog, file operations, network operations

    ### Automated Analysis Features
    - **Top 20 System Calls**: Frequency analysis of most common operations
    - **Network Activity Summary**: Count of network syscalls and I/O operations
    - **Error Analysis**: Detection and categorization of common errors
    - **Performance Insights**: Process lifecycle events and signal handling

    ## Command Generation Architecture

    Uses shared command generation utilities for consistent execution environment integration:

    ### Setup Phase
    1. **Availability Checking**: Verify strace binary and runtime dependencies
    2. **Output Directory Creation**: Ensure trace output directories exist
    3. **Core Dump Configuration**: Enable core dumps for debugging
    4. **Dynamic Linker Verification**: Confirm runtime library availability

    ### Wrapper Command Generation
    1. **Option Assembly**: Build strace command with configured options
    2. **Output Redirection**: Configure trace output to service-specific files
    3. **Command Splitting**: Separate setup commands from main wrapper
    4. **Argument Passthrough**: Ensure "$@" properly wraps target service commands

    ### Post-Processing Integration
    1. **Analysis Command Registration**: Register automated analysis scripts
    2. **Summary Generation**: Create human-readable analysis summaries
    3. **Error Extraction**: Extract and categorize system call errors
    4. **Performance Metrics**: Generate timing and frequency statistics

    ## Error Handling and Resilience

    Robust error handling ensures trace collection reliability:

    - **Tool Availability**: Graceful fallback if strace is not available
    - **Permission Issues**: Detailed logging of privilege and access errors
    - **Output Failures**: Fallback strategies for write permission problems
    - **Process Tracking**: Continued tracing even if child processes fail

    ## Plugin Registration

    Registered as EXECUTION_ENVIRONMENT plugin with capabilities:
    - syscall_tracing: Complete system call monitoring and analysis
    - performance_analysis: Performance bottleneck identification
    - debugging: Deep service behavior analysis and troubleshooting

    ## Performance Impact

    - **CPU Overhead**: 10-30% depending on syscall frequency and trace options
    - **Memory Usage**: Minimal, trace data written directly to files
    - **Disk I/O**: High for active services, proportional to syscall frequency
    - **Network Impact**: None, passive monitoring of syscall interface

    ## Integration with Network Environments

    Seamlessly integrates with all network environment types:

    - **Docker Compose**: Container-level strace with volume-mounted output
    - **Shadow NS**: Process-level tracing within simulation environment
    - **Localhost**: Direct process tracing with local file output

    Attributes:
        target_platform (Optional[str]): Target platform for platform-specific options
        _plugin_config (StraceConfig): Cached plugin configuration with strace options

    Methods:
        get_output_patterns(): Define strace-specific output file patterns
        get_additional_output_discovery_patterns(): Additional output discovery patterns
        _setup_plugin_specific_environment(): Configure strace for all services
        _build_strace_command(): Generate strace command with configured options
        _split_strace_command(): Split setup and wrapper commands
        _add_strace_analysis_commands(): Add post-processing analysis commands
        to_command(): Generate strace command for standalone execution
    """

    def __init__(
        self,
        env_config_to_test: StraceConfig,
        output_dir: str,
        env_type: str,
        env_sub_type: str,
        event_manager: EventManager,
        target_platform: Optional[str] = None,
    ):
        """Initialize the strace environment."""
        super().__init__(
            env_config_to_test, output_dir, env_type, env_sub_type, event_manager
        )

        # Initialize plugin config cache
        self._plugin_config = None
        self.target_platform = target_platform

    def _get_plugin_config(self) -> StraceConfig:
        """Get plugin config with caching and fallback."""
        if self._plugin_config is None:
            try:
                self.logger.debug("Fetching strace plugin config")
                self._plugin_config = self.env_config_to_test.get_plugin_config(
                    StraceConfig
                )
            except Exception as e:
                self.logger.debug(f"Could not get plugin config, using defaults: {e}")
                self._plugin_config = StraceConfig()
        return self._plugin_config

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
        self.logger.debug(
            f"Services to configure: {[getattr(s, 'service_name', s.__class__.__name__) for s in services_managers]}"
        )

        for service in services_managers:
            service_name = getattr(service, "service_name", service.__class__.__name__)

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

            self.logger.debug(f"Registered strace output files for {service_name}:")
            self.logger.debug(f"  Log file: {strace_output_file}")
            self.logger.debug(f"  Summary file: {strace_summary_file}")

            # Build the strace command using the utility method
            strace_cmd = self._build_strace_command(strace_output_file)
            self.logger.debug(f"Built strace command for {service_name}: {strace_cmd}")

            # Split strace command into setup and main wrapper parts
            setup_commands, main_wrapper = self._split_strace_command(
                strace_cmd, service_name
            )

            self.logger.debug(
                f"Setup commands for {service_name}: {len(setup_commands)} commands"
            )
            self.logger.debug(f"Main wrapper for {service_name}: {main_wrapper}")

            # Add the strace wrapper using new architecture
            self.logger.debug(f"Adding strace wrapper command for {service_name}")
            command_builder.add_wrapper_command(
                wrapper_command="",  # Legacy parameter - not used with new architecture
                description=f"Setup strace wrapper for {command_builder.service_name}\n",
                additional_env_vars={
                    "STRACE_OUTPUT": strace_output_file,
                    "STRACE": "1",
                },
                is_critical=False,
                setup_commands=setup_commands,
                main_command_wrapper=main_wrapper,
            )
            self.logger.debug(f"Wrapper command added successfully for {service_name}")

            # Add comprehensive post-processing for strace analysis
            self._add_strace_analysis_commands(
                command_builder, strace_output_file, strace_summary_file
            )

            # Build and apply all commands to the service
            self.logger.debug(f"About to build and apply commands for {service_name}")
            results = command_builder.build_and_apply(self.modify_service_commands)
            self.logger.debug(f"build_and_apply returned for {service_name}: {results}")

            self.logger.info(
                "Successfully configured strace for service %s",
                command_builder.service_name,
            )
            self.logger.debug("Applied modifications: %s", results)

            # Debug: Check if modification callback was actually called
            self.logger.debug(
                f"Strace configuration completed for {service_name}. Callback results: {results}"
            )

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
        mkdir_cmd = f"mkdir -p {output_dir}; touch {output_file};"

        # Get plugin config
        plugin_config = self._get_plugin_config()

        # Get strace binary using dual approach
        strace_binary = None
        if (
            hasattr(self.env_config_to_test, "plugin_config")
            and self.env_config_to_test.plugin_config
        ):
            strace_binary = self.env_config_to_test.plugin_config.get("strace_binary")
        if strace_binary is None:
            strace_binary = plugin_config.strace_binary

        command_parts = [strace_binary]  # "sudo",

        # Add output file
        command_parts.extend(["-o", output_file])

        # Include kernel stack if enabled using dual approach
        include_kernel_stack = None
        if (
            hasattr(self.env_config_to_test, "plugin_config")
            and self.env_config_to_test.plugin_config
        ):
            include_kernel_stack = self.env_config_to_test.plugin_config.get(
                "include_kernel_stack"
            )
        if include_kernel_stack is None:
            include_kernel_stack = plugin_config.include_kernel_stack
        if include_kernel_stack:
            machine = platform.machine().lower()
            command_parts.append("-k") if machine in ["x86_64", "i386", "i686"] else ""

        command_parts.extend(("-tt", "-yy", "-f", "-yy"))  # "-e verbose=all" # TODO
        # Exclude specified syscalls using dual approach
        excluded_syscalls = None
        if (
            hasattr(self.env_config_to_test, "plugin_config")
            and self.env_config_to_test.plugin_config
        ):
            excluded_syscalls = self.env_config_to_test.plugin_config.get(
                "excluded_syscalls"
            )
        if excluded_syscalls is None:
            excluded_syscalls = plugin_config.excluded_syscalls
        if excluded_syscalls:
            excluded = ",".join(excluded_syscalls)
            command_parts.extend(["-e", f"trace=!{excluded}"])

        # Focus on network syscalls if enabled using dual approach
        if (
            hasattr(plugin_config, "trace_all_syscalls")
            and plugin_config.trace_all_syscalls
            or (
                hasattr(self.env_config_to_test, "plugin_config")
                and self.env_config_to_test.plugin_config
                and self.env_config_to_test.plugin_config.get("trace_all_syscalls")
            )
        ):
            command_parts.append("-e trace=all")
        else:
            trace_network_syscalls = None
            if (
                hasattr(self.env_config_to_test, "plugin_config")
                and self.env_config_to_test.plugin_config
            ):
                trace_network_syscalls = self.env_config_to_test.plugin_config.get(
                    "trace_network_syscalls"
                )
            if trace_network_syscalls is None:
                trace_network_syscalls = plugin_config.trace_network_syscalls
            if trace_network_syscalls:
                network_syscalls = (
                    "network,read,write,send,recv,connect,bind,listen,accept"
                )
                command_parts.extend(["-e", f"trace={network_syscalls}"])

        strace_cmd = " ".join(command_parts)

        # Add timeout if specified using dual approach
        # DISABLED: Let service-level timeout handle process lifecycle instead of strace wrapper timeout
        # This allows strace to capture the full execution without being artificially terminated
        timeout = None
        if (
            hasattr(self.env_config_to_test, "plugin_config")
            and self.env_config_to_test.plugin_config
        ):
            timeout = self.env_config_to_test.plugin_config.get("timeout")
        if timeout is None:
            timeout = plugin_config.timeout
        # if timeout:
        #     # Note: strace doesn't have built-in timeout, use timeout command
        #     strace_cmd = f"timeout {timeout} {strace_cmd}"

        # Add any additional parameters using dual approach
        additional_parameters = None
        if (
            hasattr(self.env_config_to_test, "plugin_config")
            and self.env_config_to_test.plugin_config
        ):
            additional_parameters = self.env_config_to_test.plugin_config.get(
                "additional_parameters"
            )
        if additional_parameters is None:
            additional_parameters = plugin_config.additional_parameters
        if additional_parameters:
            additional = " ".join(additional_parameters)
            strace_cmd = f"{strace_cmd} {additional}"

        # Return command with directory creation
        return f"{mkdir_cmd} && {strace_cmd}"

    def _split_strace_command(
        self, full_strace_cmd: str, service_name: str
    ) -> Tuple[List[str], str]:
        """
        Split the full strace command into setup commands and main wrapper.

        Args:
            full_strace_cmd: The complete strace command (includes setup)
            service_name: Name of the service for logging

        Returns:
            Tuple of (setup_commands_list, main_command_wrapper)
        """
        # Split the command at '&&' to separate setup from main strace command
        parts = full_strace_cmd.split(" && ", 1)

        if len(parts) == 2:
            mkdir_cmd = parts[0]  # Directory creation
            strace_base_cmd = parts[1]  # Main strace command without the target
        else:
            # No && separator, assume the whole thing is the strace command
            mkdir_cmd = ""
            strace_base_cmd = full_strace_cmd

        # Build setup commands list
        setup_commands = []

        # Add directory creation if present
        if mkdir_cmd:
            setup_commands.append(mkdir_cmd)

        # Add strace availability check
        plugin_config = self._get_plugin_config()
        strace_binary = plugin_config.strace_binary
        availability_check = f"""# Confirm dynamic linker and runtime availability
ls -l /lib64/ld-linux-x86-64.so.2 || echo 'Dynamic linker not found' >> /app/logs/{service_name}_strace_exec_env_setup.log
ls -l /lib64/libc.so.6 || echo 'C library not found' >> /app/logs/{service_name}_strace_exec_env_setup.log
file $(which strace) || echo 'strace binary not found' >> /app/logs/{service_name}_strace_exec_env_setup.log
# inside the container or host
ulimit -c unlimited;                 # allow core files
echo '/tmp/core.%e.%p' | sudo tee /proc/sys/kernel/core_pattern;
# Check if strace is available
touch /app/logs/{service_name}_strace_exec_env_setup.log
touch /app/logs/{service_name}_strace_exec_env_setup.log.err
if ! command -v {strace_binary} >/dev/null 2>&1; then
    echo 'ERROR: strace not found at {strace_binary}' >> /app/logs/{service_name}_strace_exec_env_setup.log
    echo 'Available debugging tools:' >> /app/logs/{service_name}_strace_exec_env_setup.log
    ls -la /usr/bin/strace* 2>/dev/null >> /app/logs/{service_name}_strace_exec_env_setup.log || echo 'No strace found in /usr/bin/' >> /app/logs/{service_name}_strace_exec_env_setup.log
    which strace >> /app/logs/{service_name}_strace_exec_env_setup.log 2>&1 || echo 'strace not in PATH' >> /app/logs/{service_name}_strace_exec_env_setup.log
    dpkg -l | grep strace >> /app/logs/{service_name}_strace_exec_env_setup.log 2>&1 || echo 'strace package not installed' >> /app/logs/{service_name}_strace_exec_env_setup.log
else
    echo 'strace found at: {strace_binary}' >> /app/logs/{service_name}_strace_exec_env_setup.log
    {strace_binary} --version >> /app/logs/{service_name}_strace_exec_env_setup.log 2>&1 || echo 'strace version check failed' >> /app/logs/{service_name}_strace_exec_env_setup.log
fi"""

        setup_commands.append(availability_check)

        # Create the wrapper command that can wrap any command passed to it
        # This is the key fix: add "$@" to make it a proper wrapper
        # Use -- to separate strace options from the command to trace
        strace_wrapper = f'{strace_base_cmd} -- "$@"'

        return setup_commands, strace_wrapper

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
    grep -oE '^[a-zA-Z_]+\\(' {strace_output_file} | sed 's/($//' | sort | uniq -c | sort -nr | head -20 >> {summary_file} 2>/dev/null || echo "No system calls found" >> {summary_file}
else
    echo "Strace output file not found" >> {summary_file}
fi

echo "" >> {summary_file}

# Network activity analysis
echo "=== Network Activity Summary ===" >> {summary_file}
if [ -f "{strace_output_file}" ]; then
    echo "Network system calls:" >> {summary_file}
    grep -E '((socket|connect|bind|listen|accept|send|recv))\\(' {strace_output_file} | wc -l >> {summary_file} 2>/dev/null || echo "0" >> {summary_file}

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
    grep -E 'EACCES|ENOENT|EPERM|ECONNREFUSED|ETIMEDOUT|EADDRINUSE' {strace_output_file} | cut -d' ' -f1 | sort | uniq -c | sort -nr >> {summary_file} 2>/dev/null || echo "No errors found" >> {summary_file}
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

        # Add optional detailed analysis if configured using dual approach
        plugin_config = self._get_plugin_config()
        generate_detailed_analysis = None
        if (
            hasattr(self.env_config_to_test, "plugin_config")
            and self.env_config_to_test.plugin_config
        ):
            generate_detailed_analysis = self.env_config_to_test.plugin_config.get(
                "generate_detailed_analysis"
            )
        if generate_detailed_analysis is None and hasattr(
            plugin_config, "generate_detailed_analysis"
        ):
            generate_detailed_analysis = plugin_config.generate_detailed_analysis

        if generate_detailed_analysis:
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
            # Get output file using dual approach
            plugin_config = self._get_plugin_config()
            output_file_value = None
            if (
                hasattr(self.env_config_to_test, "plugin_config")
                and self.env_config_to_test.plugin_config
            ):
                output_file_value = self.env_config_to_test.plugin_config.get(
                    "output_file"
                )
            if output_file_value is None:
                output_file_value = plugin_config.output_file
            output_file = output_file_value or "/tmp/strace.log"

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
