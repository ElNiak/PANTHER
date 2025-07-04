from typing import TYPE_CHECKING, Dict, List, Optional, Tuple

"""
GDB debugging execution environment for systematic crash analysis and stack trace generation.

This environment provides comprehensive debugging capabilities with automatic stack traces,
debug symbols, and crash analysis for PANTHER services.
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
from panther.plugins.environments.execution_environment.gdb.config_schema import (
    GdbConfig,
)
from panther.plugins.services.services_interface import IServiceManager

if TYPE_CHECKING:
    pass


@register_plugin(
    plugin_type=PluginType.EXECUTION_ENVIRONMENT,
    name="gdb",
    version="1.0.0",
    description="GDB debugging environment for crash analysis and stack traces",
    author="PANTHER Team",
    capabilities=["debugging", "stack_traces", "crash_analysis", "core_dumps"],
    external_dependencies=["gdb"],
    runtime_mode="debug",
)
class GdbEnvironment(BaseExecutionEnvironment):
    """
    GDB debugging execution environment.

    This environment provides systematic debugging capabilities including:
    - Automatic stack traces on crashes
    - Debug symbol compilation
    - Core dump generation and analysis
    - AddressSanitizer integration
    - Comprehensive crash reporting
    """

    def __init__(
        self,
        env_config_to_test: GdbConfig,
        output_dir: str,
        env_type: str,
        env_sub_type: str,
        event_manager: EventManager,
        target_platform: Optional[str] = None,
    ):
        """Initialize the GDB debugging environment."""
        super().__init__(
            env_config_to_test, output_dir, env_type, env_sub_type, event_manager
        )

        # Initialize plugin config cache
        self._plugin_config = None
        self.target_platform = target_platform

    def _get_plugin_config(self) -> GdbConfig:
        """Get plugin config with caching and fallback."""
        if self._plugin_config is None:
            try:
                self._plugin_config = self.env_config_to_test.get_plugin_config(
                    GdbConfig
                )
            except Exception as e:
                self.logger.debug(f"Could not get plugin config, using defaults: {e}")
                self._plugin_config = GdbConfig()
        return self._plugin_config

    def _setup_plugin_specific_environment(
        self, services_managers: List[IServiceManager], timestamp: str
    ):
        """
        Set up GDB debugging for compatible services.

        Args:
            services_managers: List of service managers to potentially modify
            timestamp: Timestamp for this execution (used for file naming)
        """
        for service in services_managers:
            service_name = getattr(service, "service_name", service.__class__.__name__)

            # Check if service supports debugging - be more robust in the check
            debug_compatible = True
            debug_check_reason = "default True"

            # Check multiple possible locations for debug_compatible flag
            if hasattr(service.service_config_to_test, "implementation"):
                impl_debug_compat = getattr(
                    service.service_config_to_test.implementation,
                    "debug_compatible",
                    None,
                )
                if impl_debug_compat is not None:
                    debug_compatible = impl_debug_compat
                    debug_check_reason = (
                        f"implementation.debug_compatible={impl_debug_compat}"
                    )

            # Also check the service manager itself for debug_compatible
            if hasattr(service, "debug_compatible"):
                service_debug_compat = getattr(service, "debug_compatible", None)
                if service_debug_compat is not None:
                    debug_compatible = service_debug_compat
                    debug_check_reason = (
                        f"service.debug_compatible={service_debug_compat}"
                    )

            # Check if implementation config has debug_compatible explicitly set to False
            if hasattr(service.service_config_to_test, "implementation") and hasattr(
                service.service_config_to_test.implementation, "__dict__"
            ):
                impl_dict = service.service_config_to_test.implementation.__dict__
                if "debug_compatible" in impl_dict:
                    debug_compatible = impl_dict["debug_compatible"]
                    debug_check_reason = f"implementation.__dict__['debug_compatible']={debug_compatible}"

            self.logger.debug(
                "GDB debug compatibility check for %s: %s (%s)",
                service_name,
                debug_compatible,
                debug_check_reason,
            )

            if not debug_compatible:
                self.logger.debug(
                    "Skipping GDB debugging for %s (not debug compatible)",
                    service_name,
                )
                continue

            # Create command builder using shared utilities
            command_builder = create_execution_environment_builder(
                service=service,
                environment_name="gdb",
                timestamp=timestamp,
                register_output_callback=self.register_output_file,
                logger=self.logger,
            )

            plugin_config = self._get_plugin_config()

            # Register output files
            gdb_log_file = command_builder.register_output_file(
                file_type="gdb_log",
                extension="log",
                description="GDB session log",
            )

            core_dump_file = command_builder.register_output_file(
                file_type="core_dump",
                extension="core",
                description="Core dump file",
            )

            stack_trace_file = command_builder.register_output_file(
                file_type="stack_trace",
                extension="trace",
                description="Stack trace output",
            )

            # Get configuration values with dual approach
            gdb_binary = self._get_config_value(
                "gdb_binary", plugin_config.gdb_binary, "/usr/bin/gdb"
            )
            enable_core_dumps = self._get_config_value(
                "enable_core_dumps", plugin_config.enable_core_dumps, True
            )
            auto_backtrace = self._get_config_value(
                "auto_backtrace", plugin_config.auto_backtrace, True
            )

            # Create GDB script for automated debugging
            gdb_script = self._create_gdb_script(
                plugin_config, gdb_log_file, stack_trace_file, auto_backtrace
            )

            gdb_script_file = command_builder.register_output_file(
                file_type="gdb_script",
                extension="gdb",
                description="GDB automation script",
            )

            # Build the GDB command similar to strace pattern
            gdb_cmd = self._build_gdb_command(gdb_binary, gdb_script_file, gdb_log_file)

            # Split GDB command into setup and main wrapper parts
            setup_commands, main_wrapper = self._split_gdb_command(
                gdb_cmd,
                gdb_script,
                gdb_script_file,
                getattr(service, "service_name", service.__class__.__name__),
            )

            # Add the GDB wrapper using shared architecture
            command_builder.add_wrapper_command(
                wrapper_command="",  # Legacy parameter - not used with new architecture
                description="Setup GDB debugging for " + command_builder.service_name,
                additional_env_vars=self._get_debug_env_vars(
                    plugin_config, core_dump_file
                ),
                is_critical=False,
                setup_commands=setup_commands,
                main_command_wrapper=main_wrapper,
            )

            # Add post-processing for stack trace analysis
            if auto_backtrace:
                command_builder.add_post_processing(
                    input_file=gdb_log_file,
                    output_file=stack_trace_file,
                    processing_command="grep -A 50 '#0 ' "
                    + gdb_log_file
                    + " > "
                    + stack_trace_file
                    + " || echo 'No stack trace found' > "
                    + stack_trace_file,
                    description="Extract stack trace from GDB log",
                    file_type="stack_trace",
                    error_message="Failed to extract stack trace from GDB output",
                )

            # Build and apply all commands to the service
            results = command_builder.build_and_apply(self.modify_service_commands)

            self.logger.info(
                "Successfully configured GDB debugging for service %s",
                command_builder.service_name,
            )
            self.logger.debug("Applied modifications: %s", results)

    def _get_config_value(self, key: str, typed_value, default_value):
        """Get configuration value using dual approach (dict then typed config)."""
        # First try plugin_config dict
        if (
            hasattr(self.env_config_to_test, "plugin_config")
            and self.env_config_to_test.plugin_config
        ):
            dict_value = self.env_config_to_test.plugin_config.get(key)
            if dict_value is not None:
                return dict_value

        # Second try typed config
        if typed_value is not None:
            return typed_value

        # Finally use default
        return default_value

    def _build_gdb_command(
        self, gdb_binary: str, gdb_script_file: str, log_file: str
    ) -> str:
        """
        Build the GDB command with configured options.

        Args:
            gdb_binary: Path to GDB binary
            gdb_script_file: Path to GDB script file
            log_file: Path to log file

        Returns:
            str: Complete GDB command
        """
        plugin_config = self._get_plugin_config()
        execution_timeout = None  # self._get_config_value("execution_timeout", plugin_config.execution_timeout, 300)

        # Basic GDB command structure
        gdb_cmd_parts = [
            gdb_binary,
            "--batch",
            "--quiet",
            "--command=" + gdb_script_file,
            "--args",
        ]

        gdb_cmd = " ".join(gdb_cmd_parts)

        # Add timeout wrapper
        if execution_timeout:
            gdb_cmd = "timeout " + str(execution_timeout) + " " + gdb_cmd

        return gdb_cmd

    def _split_gdb_command(
        self,
        full_gdb_cmd: str,
        gdb_script: str,
        gdb_script_file: str,
        service_name: str,
    ) -> Tuple[List[str], str]:
        """
        Split the full GDB command into setup commands and main wrapper.

        Args:
            full_gdb_cmd: The complete GDB command
            gdb_script: The GDB script content
            gdb_script_file: Path to GDB script file
            service_name: Name of the service for logging

        Returns:
            Tuple of (setup_commands_list, main_command_wrapper)
        """
        plugin_config = self._get_plugin_config()
        gdb_binary = self._get_config_value(
            "gdb_binary", plugin_config.gdb_binary, "/usr/bin/gdb"
        )

        setup_commands = []

        # Create GDB script file using HERE document approach (safer than f-strings)
        # Split into separate lines to ensure proper EOF termination
        script_creation_cmd = (
            "cat > " + gdb_script_file + " << 'EOF'\n" + gdb_script + "\nEOF"
        )
        setup_commands.append(script_creation_cmd)

        # Add GDB availability check without f-strings
        log_file = "/app/logs/" + service_name + "_gdb_exec_env_setup.log"
        availability_check = (
            "# Check GDB availability and setup\n"
            + "ulimit -c unlimited;                 # allow core files\n"
            + "echo '/tmp/core.%e.%p' | sudo tee /proc/sys/kernel/core_pattern;\n"
            + "touch "
            + log_file
            + "\n"
            + "touch "
            + log_file
            + ".err\n"
            + "if ! command -v "
            + gdb_binary
            + " >/dev/null 2>&1; then\n"
            + "    echo 'ERROR: GDB not found at "
            + gdb_binary
            + "' >> "
            + log_file
            + "\n"
            + "    echo 'Available debugging tools:' >> "
            + log_file
            + "\n"
            + "    ls -la /usr/bin/gdb* 2>/dev/null >> "
            + log_file
            + " || echo 'No GDB found in /usr/bin/' >> "
            + log_file
            + "\n"
            + "    which gdb >> "
            + log_file
            + " 2>&1 || echo 'gdb not in PATH' >> "
            + log_file
            + "\n"
            + "    dpkg -l | grep gdb >> "
            + log_file
            + " 2>&1 || echo 'gdb package not installed' >> "
            + log_file
            + "\n"
            + "else\n"
            + "    echo 'GDB found at: "
            + gdb_binary
            + "' >> "
            + log_file
            + "\n"
            + "    "
            + gdb_binary
            + " --version >> "
            + log_file
            + " 2>&1 || echo 'GDB version check failed' >> "
            + log_file
            + "\n"
            + "fi\n"
            + "\n"
            + "# Setup core dump handling\n"
            + "ulimit -c unlimited 2>/dev/null || echo 'Could not set unlimited core dumps' >> "
            + log_file
            + "\n"
            + "echo '/tmp/core.%e.%p' | sudo tee /proc/sys/kernel/core_pattern 2>/dev/null || echo 'Could not set core pattern' >> "
            + log_file
        )

        setup_commands.append(availability_check)

        # Create the wrapper command that runs GDB with the target program
        # Extract the base GDB command without timeout for the wrapper
        if full_gdb_cmd.startswith("timeout "):
            # Remove timeout prefix for the wrapper (timeout will be handled at service level)
            gdb_base_cmd = " ".join(full_gdb_cmd.split()[2:])  # Skip "timeout 300"
        else:
            gdb_base_cmd = full_gdb_cmd

        # CRITICAL FIX: GDB --args expects executable immediately, no -- separator needed
        # Unlike strace, GDB's --args flag requires direct executable specification
        gdb_wrapper = f'{gdb_base_cmd} "$@"'

        return setup_commands, gdb_wrapper

    def _get_debug_env_vars(
        self, config: GdbConfig, core_dump_file: str
    ) -> Dict[str, str]:
        """Get debug environment variables."""
        env_vars = {}

        # Core dump setup
        if self._get_config_value("enable_core_dumps", config.enable_core_dumps, True):
            env_vars["CORE_DUMP_FILE"] = core_dump_file

        # AddressSanitizer if enabled
        if self._get_config_value("enable_asan", config.enable_asan, False):
            asan_options = self._get_config_value(
                "asan_options", config.asan_options, []
            )
            if asan_options:
                env_vars["ASAN_OPTIONS"] = ":".join(asan_options)

        # Debug environment variables
        debug_env_vars = self._get_config_value(
            "debug_env_vars", config.debug_env_vars, {}
        )
        env_vars.update({k: str(v) for k, v in debug_env_vars.items()})

        return env_vars

    def _get_architecture_info(self) -> tuple[str, dict]:
        """Parse target platform and return appropriate register mappings."""
        # Use target_platform if available, otherwise detect from Docker target
        target_platform = self.target_platform

        if not target_platform:
            # Fallback to x86_64 if no target platform specified
            self.logger.debug("No target platform specified, defaulting to x86_64")
            target_platform = "linux/amd64"

        self.logger.debug(f"Using target platform: {target_platform}")

        # Parse architecture from target platform string
        # Common formats: linux/amd64, linux/arm64, linux/arm/v7, etc.
        arch_info = {
            "detected_arch": "x86_64",
            "syscall_reg": "$rdi",
            "arg_regs": ["$rdi", "$rsi", "$rdx", "$rcx"],
            "return_reg": "$rax",
            "arch_name": "x86_64",
        }

        try:
            platform_lower = target_platform.lower()

            if "amd64" in platform_lower or "x86_64" in platform_lower:
                arch_info.update(
                    {
                        "detected_arch": "x86_64",
                        "syscall_reg": "$rdi",
                        "arg_regs": ["$rdi", "$rsi", "$rdx", "$rcx"],
                        "return_reg": "$rax",
                        "arch_name": "x86_64",
                    }
                )
            elif "arm64" in platform_lower or "aarch64" in platform_lower:
                arch_info.update(
                    {
                        "detected_arch": "arm64",
                        "syscall_reg": "$x8",
                        "arg_regs": ["$x0", "$x1", "$x2", "$x3"],
                        "return_reg": "$x0",
                        "arch_name": "arm64",
                    }
                )
            elif "arm" in platform_lower:
                # ARM32 (includes arm/v7, arm/v6, etc.)
                arch_info.update(
                    {
                        "detected_arch": "arm32",
                        "syscall_reg": "$r7",
                        "arg_regs": ["$r0", "$r1", "$r2", "$r3"],
                        "return_reg": "$r0",
                        "arch_name": "arm32",
                    }
                )

            self.logger.debug(
                f"Parsed architecture: {arch_info['detected_arch']} from platform: {target_platform}"
            )

        except Exception as e:
            self.logger.debug(f"Architecture parsing failed: {e}, using default x86_64")

        return arch_info["detected_arch"], arch_info

    def _create_gdb_script(
        self, config: GdbConfig, log_file: str, trace_file: str, auto_backtrace: bool
    ) -> str:
        """Create GDB automation script for strace-like error detection and debugging."""
        script_lines = [
            "# GDB automation script for PANTHER debugging - Enhanced strace-like monitoring",
            "set logging file " + log_file,
            "set logging on",
            "set confirm off",
            "set print pretty on",
            "set print object on",
            "set print static-members on",
            "set print vtbl on",
            "set print demangle on",
            "set demangle-style gnu-v3",
            "set pagination off",
            "set height 0",
            "set width 0",
        ]

        # Enhanced strace-like system call monitoring
        script_lines.extend(
            [
                "",
                "# === STRACE-LIKE SYSTEM CALL MONITORING ===",
                "# Catch all syscalls for comprehensive monitoring",
                "catch syscall",
                "",
                "# Enhanced error detection - general syscall monitoring",
                "# Note: Using general syscall catching to avoid compatibility issues",
                "# The 'catch syscall' above already catches all syscalls including:",
                "# openat, creat, read, write, socket, connect, bind, listen, accept, mmap, etc.",
            ]
        )

        # Add signal handling with strace-like comprehensiveness
        break_signals = self._get_config_value(
            "break_on_signals",
            config.break_on_signals,
            ["SIGSEGV", "SIGABRT", "SIGFPE"],
        )
        script_lines.extend(
            [
                "",
                "# === ENHANCED SIGNAL MONITORING ===",
            ]
        )

        # Add comprehensive signal monitoring (more than strace)
        comprehensive_signals = break_signals + [
            "SIGBUS",
            "SIGILL",
            "SIGTRAP",
            "SIGPIPE",
            "SIGTERM",
        ]
        for signal in set(comprehensive_signals):  # Remove duplicates
            script_lines.append("handle " + signal + " stop print")

        # Add exception handling for C++
        if self._get_config_value(
            "break_on_exceptions", config.break_on_exceptions, True
        ):
            script_lines.extend(
                [
                    "",
                    "# === C++ EXCEPTION MONITORING ===",
                    "catch throw",
                    "catch catch",
                    "catch rethrow",
                ]
            )

        # Add memory error detection with deferred breakpoints (will be set when symbols load)
        script_lines.extend(
            [
                "",
                "# === MEMORY ERROR DETECTION ===",
                "# Set deferred breakpoints - these will be applied when symbols become available",
                "set breakpoint pending on",
                "",
                "# Break on common memory errors - will activate when symbols load",
                "break __stack_chk_fail",  # Stack overflow detection
                "break abort",  # Abort calls
                "break _exit",  # Exit calls
                "break exit",  # Exit calls
                "break __assert_fail",  # Assertion failures
                "break malloc_printerr",  # Heap corruption
            ]
        )

        # Add network error monitoring with deferred breakpoints
        script_lines.extend(
            [
                "",
                "# === NETWORK ERROR MONITORING ===",
                "# Monitor network operations - deferred until symbols load",
                "break connect",  # Connection attempts
                "break bind",  # Bind attempts
                "break listen",  # Listen attempts
            ]
        )

        # Add initialization commands
        init_commands = self._get_config_value(
            "init_commands", config.init_commands, []
        )
        if init_commands:
            script_lines.extend(
                [
                    "",
                    "# === CUSTOM INITIALIZATION ===",
                ]
            )
            script_lines.extend(init_commands)

        # Define comprehensive error analysis function (enhanced strace-like output)
        if auto_backtrace:
            max_depth = self._get_config_value(
                "max_backtrace_depth", config.max_backtrace_depth, 50
            )
            backtrace_full = self._get_config_value(
                "backtrace_full", config.backtrace_full, True
            )

            script_lines.extend(
                [
                    "",
                    "# === COMPREHENSIVE ERROR ANALYSIS FUNCTION ===",
                    "define analyze_error",
                    "  set logging file " + trace_file,
                    "  set logging redirect on",
                    "  echo '\\n=== ERROR DETECTED ===\\n'",
                    '  printf "Timestamp: %s\\n", (char*)ctime((time_t*)&$pc)',
                    "  echo '\\n--- Process State ---\\n'",
                    "  info program",
                    "  info proc",
                    "  echo '\\n--- Registers ---\\n'",
                    "  info registers",
                    "  echo '\\n--- Memory Layout ---\\n'",
                    "  info proc mappings",
                    "  echo '\\n--- Current Instruction ---\\n'",
                    "  x/5i $pc",
                ]
            )

            if backtrace_full:
                script_lines.extend(
                    [
                        "  echo '\\n--- Full Stack Trace ---\\n'",
                        "  bt full " + str(max_depth),
                        "  echo '\\n--- Thread Information ---\\n'",
                        "  info threads",
                        "  thread apply all bt 10",
                    ]
                )
            else:
                script_lines.extend(
                    [
                        "  echo '\\n--- Stack Trace ---\\n'",
                        "  bt " + str(max_depth),
                    ]
                )

            # Add post-crash commands with strace-like syscall analysis
            post_crash_commands = self._get_config_value(
                "post_crash_commands", config.post_crash_commands, []
            )
            enhanced_commands = [
                "info locals",
                "info args",
                "disassemble",
                "info sharedlibrary",
                "info files",
                "info signals",
            ] + post_crash_commands

            for cmd in enhanced_commands:
                script_lines.append("  " + cmd)

            script_lines.extend(
                [
                    "  echo '\\n--- Syscall Context ---\\n'",
                    "  # Try to show syscall information if available",
                    "  if ($_siginfo)",
                    '    printf "Signal info: si_signo=%d, si_code=%d, si_addr=%p\\n", $_siginfo.si_signo, $_siginfo.si_code, $_siginfo.si_addr',
                    "  end",
                    "  set logging redirect off",
                    "  set logging off",
                    "end",
                    "",
                ]
            )

            # Get architecture-specific register info
            arch_name, arch_info = self._get_architecture_info()

            # Define architecture-aware syscall monitoring function
            script_lines.extend(
                [
                    "# === ARCHITECTURE-AWARE SYSCALL MONITORING FUNCTION ===",
                    f"# Target architecture: {arch_name}",
                    "define monitor_syscall",
                    "  set logging redirect on",
                    "  # Architecture-specific register handling",
                    f"  printf \"SYSCALL [{arch_name}]: %ld\\n\", (long){arch_info['syscall_reg']}",
                    f'  printf "Args [{arch_name}]: "',
                ]
            )

            # Add argument register printing
            for i, reg in enumerate(arch_info["arg_regs"][:4]):
                if i > 0:
                    script_lines.append('  printf ", "')
                script_lines.append(f'  printf "arg{i}=%ld", (long){reg}')

            script_lines.extend(
                [
                    '  printf "\\n"',
                    f"  printf \"Return [{arch_name}]: %ld\\n\", (long){arch_info['return_reg']}",
                    "  set logging redirect off",
                    "end",
                    "",
                ]
            )

        # Add comprehensive monitoring commands
        script_lines.extend(
            [
                "# === MONITORING COMMANDS ===",
                "commands",
                "  # Auto-run error analysis on any breakpoint hit",
            ]
        )

        # Evaluate auto_backtrace at script generation time, not runtime
        if auto_backtrace:
            script_lines.extend(
                [
                    "  analyze_error",
                ]
            )

        script_lines.extend(
            [
                "  # Continue execution to monitor more events",
                "  continue",
                "end",
                "",
            ]
        )

        # Add syscall-specific monitoring (similar to strace filtering)
        script_lines.extend(
            [
                "# === SYSCALL-SPECIFIC MONITORING ===",
                "commands 1",  # For syscall breakpoints
                "  monitor_syscall",
                "  continue",
                "end",
                "",
            ]
        )

        # Add run command with enhanced monitoring
        run_command = self._get_config_value("run_command", config.run_command, "run")
        script_lines.extend(
            [
                "# === EXECUTION START ===",
                run_command,
                "",
                "# If program exits normally, show summary",
                "echo '\\n=== EXECUTION COMPLETED ===\\n'",
                "info program",
                "quit",
            ]
        )

        return "\n".join(script_lines)

    def to_command(
        self, pid: Optional[int] = None, output_file: Optional[str] = None
    ) -> str:
        """
        Generate the GDB debugging command for execution.

        Args:
            pid: Optional process ID to attach to
            output_file: Optional output file path

        Returns:
            str: Command string for GDB debugging
        """
        plugin_config = self._get_plugin_config()
        gdb_binary = self._get_config_value(
            "gdb_binary", plugin_config.gdb_binary, "/usr/bin/gdb"
        )

        if output_file is None:
            output_file = "/tmp/gdb_session.log"

        # Build GDB command
        gdb_cmd = [gdb_binary, "--batch", "--quiet"]

        # Add logging
        gdb_cmd.extend(["-ex", "set logging file " + output_file])
        gdb_cmd.extend(["-ex", "set logging on"])

        if pid:
            # Attach to existing process
            gdb_cmd.extend(["--pid", str(pid)])
            gdb_cmd.extend(["-ex", "bt", "-ex", "detach", "-ex", "quit"])
        else:
            # Run with arguments (will be appended)
            gdb_cmd.append("--args")

        return " ".join(gdb_cmd)

    def update_environment(
        self,
        execution_environment,
        global_config,
        plugin_manager,
        services_managers,
        test_config,
    ) -> None:
        """
        Update environment for GDB debugging execution.

        Args:
            execution_environment: Current execution environment
            global_config: Global configuration
            plugin_manager: Plugin manager instance
            services_managers: List of service managers
            test_config: Test configuration
        """
        # Add any GDB-specific environment updates here
        self.logger.debug("Updated environment for GDB debugging execution")

        # Ensure core dumps are enabled system-wide if possible
        try:
            import os
            import resource

            # Try to enable core dumps (may require privileges)
            resource.setrlimit(
                resource.RLIMIT_CORE, (resource.RLIM_INFINITY, resource.RLIM_INFINITY)
            )
            self.logger.debug("Enabled unlimited core dump size")
        except Exception as e:
            self.logger.debug(f"Could not set core dump limit: {e}")
