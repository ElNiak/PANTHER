from abc import abstractmethod
from typing import TYPE_CHECKING, List

from panther.config.core.models.environment import EnvironmentConfig
from panther.config.core.models.global_config import GlobalConfig
from panther.core.observer.management.event_manager import EventManager
from panther.plugins.environments.environment_interface import IEnvironmentPlugin
from panther.plugins.services.services_interface import IServiceManager

# PluginManager functionality now integrated into PluginManager

if TYPE_CHECKING:
    from panther.config.core.models.experiment import TestConfig
    from panther.plugins.plugin_manager import PluginManager


class IExecutionEnvironment(IEnvironmentPlugin):
    """
    Execution Environment Interface - Process Analysis Framework

    IExecutionEnvironment extends IEnvironmentPlugin to provide process execution analysis
    capabilities for PANTHER protocol testing. Unlike network environments that orchestrate
    multiple services, execution environments wrap individual service execution with analysis
    tools like strace, Valgrind, GDB, and profiling utilities.

    ## Architecture Role

    Execution environments serve as analysis wrappers that enhance service execution with:

    1. **Process Instrumentation**: Runtime analysis through system call tracing, profiling, debugging
    2. **Output Collection**: Automated capture of traces, profiles, memory reports, and debug logs
    3. **Service Integration**: Seamless wrapping of existing services without configuration changes
    4. **Command Generation**: Dynamic command construction for complex analysis tool invocation
    5. **Lifecycle Coordination**: Synchronized startup/teardown with network environment services

    ```mermaid
    sequenceDiagram
        participant NE as NetworkEnvironment
        participant EE as ExecutionEnvironment
        participant AM as AnalysisTool
        participant SM as ServiceManager

        NE->>EE: setup_environment()
        EE->>EE: configure_analysis_tool()
        EE->>AM: prepare_instrumentation()

        NE->>SM: start_service()
        SM->>EE: wrap_execution()
        EE->>AM: instrument_process()
        AM->>SM: execute_with_analysis()

        Note over AM,SM: Service Execution + Analysis

        NE->>EE: teardown_environment()
        EE->>AM: finalize_output()
        EE->>EE: collect_artifacts()
    ```

    ## Execution Environment Categories

    Implementations provide different types of process analysis:

    ### System Call Analysis
    - **strace**: System call tracing and analysis
    - **ltrace**: Library call tracing

    ### Memory Analysis
    - **Valgrind Memcheck**: Memory error detection and leak analysis
    - **Valgrind Helgrind**: Thread safety and race condition detection
    - **AddressSanitizer**: Runtime memory error detection

    ### Performance Analysis
    - **GPerf CPU**: CPU profiling and performance analysis
    - **GPerf Heap**: Memory allocation profiling
    - **Perf**: System-wide performance monitoring

    ### Debug Analysis
    - **GDB**: Interactive and automated debugging
    - **Core Dump Analysis**: Post-mortem debugging

    ### Iteration Testing
    - **Iterations**: Repeated execution for statistical analysis
    - **Stress Testing**: High-load execution scenarios

    ## Command Generation Pattern

    Execution environments use sophisticated command generation to wrap service execution:

    1. **Base Command**: Original service execution command from service manager
    2. **Tool Wrapping**: Analysis tool command prefix/suffix generation
    3. **Output Redirection**: Tool-specific output file and logging configuration
    4. **Environment Variables**: Tool configuration through environment settings
    5. **Argument Processing**: Complex tool option handling and validation

    ## Service Integration Strategy

    Execution environments integrate with services through command wrapping:

    - **Transparent Wrapping**: Services execute normally with analysis overhead
    - **Output Isolation**: Analysis output separated from service output
    - **Error Isolation**: Analysis tool failures don't crash service execution
    - **Resource Management**: Analysis tool resource limits and cleanup

    ## Output Collection Framework

    Structured output collection ensures analysis artifacts are organized:

    - **Tool-Specific Outputs**: Each tool generates standardized output formats
    - **Timestamped Files**: Output files include execution session timestamps
    - **Hierarchical Organization**: Outputs organized by tool type and service
    - **Metadata Generation**: Analysis metadata for post-processing and reporting

    ## Lifecycle Coordination with Network Environments

    Execution environments coordinate closely with network environments:

    1. **Setup Phase**: Analysis tools configured before service deployment
    2. **Execution Phase**: Services wrapped with analysis instrumentation
    3. **Monitoring Phase**: Analysis output monitored during service execution
    4. **Teardown Phase**: Analysis finalized and artifacts collected

    ## Error Handling and Resilience

    Robust error handling ensures test reliability:

    - **Tool Failures**: Analysis tool crashes don't affect service execution
    - **Output Errors**: Missing or corrupted analysis output logged but not fatal
    - **Resource Exhaustion**: Analysis tool resource limits prevent system impact
    - **Configuration Errors**: Invalid tool configuration detected early with fallbacks

    Attributes:
        services_managers (List[IServiceManager]): Service instances to wrap with analysis
        test_config (TestConfig): Current test configuration defining analysis parameters
        analysis_tool (str): Specific analysis tool name (strace, valgrind, gdb, etc.)
        output_config (Dict): Tool-specific output configuration and file paths
        command_builder (ExecutionEnvironmentCommandBuilder): Dynamic command generation utility
        tool_options (Dict): Analysis tool-specific options and parameters

    Methods:
        setup_environment(): Configure analysis tool and prepare for service wrapping
        teardown_environment(): Finalize analysis output and collect artifacts
        wrap_service_command(): Generate analysis-wrapped service execution command
        collect_analysis_output(): Gather tool-specific output files and metadata
        validate_tool_configuration(): Verify analysis tool setup and options
    """

    def __init__(
        self,
        env_config_to_test: EnvironmentConfig,
        output_dir: str,
        env_type: str,
        env_sub_type: str,
        event_manager: EventManager,
    ):
        super().__init__(
            env_config_to_test, output_dir, env_type, env_sub_type, event_manager
        )
        self.services_managers = []
        self.test_config = None

    def is_network_environment(self):
        """
        Execution environment classification for framework orchestration.

        Returns False to indicate this is an execution environment that provides
        process analysis capabilities, as opposed to network environments that
        orchestrate multiple services with network isolation.

        This classification affects framework behavior:
        - Execution environments wrap service execution with analysis tools
        - Network environments coordinate service lifecycle and network topology

        Returns:
            bool: Always False for execution environment implementations
        """
        return False

    @abstractmethod
    def setup_environment(
        self,
        services_managers: List[IServiceManager],
        test_config: "TestConfig",
        global_config: GlobalConfig,
        timestamp: str,
        plugin_manager: "PluginManager",
    ):
        """
        Configure analysis tool and prepare for service execution wrapping.

        Initialize the execution environment with:
        1. Analysis tool configuration and validation
        2. Output directory structure creation
        3. Command generation preparation
        4. Service manager integration setup
        5. Tool-specific environment variable configuration

        This method prepares the execution environment to wrap service execution
        with the configured analysis tool while ensuring proper output collection
        and error handling.

        Args:
            services_managers (List[IServiceManager]): Service instances to analyze
            test_config (TestConfig): Test configuration with analysis parameters
            global_config (GlobalConfig): Framework-wide configuration settings
            timestamp (str): Unique timestamp for output file coordination
            plugin_manager (PluginManager): Plugin management for dynamic loading

        Raises:
            NotImplementedError: Must be implemented by concrete execution environment classes
            ConfigurationError: Invalid tool configuration or missing dependencies
            EnvironmentError: Analysis tool setup failures or resource issues
        """
        raise NotImplementedError()

    def teardown_environment(self):
        """
        Finalize analysis output and collect artifacts for post-processing.

        Complete execution environment cleanup including:
        1. Analysis tool finalization and output flushing
        2. Artifact collection and organization
        3. Metadata generation for analysis results
        4. Resource cleanup and temporary file removal
        5. Analysis summary and statistics generation

        This method ensures all analysis artifacts are properly collected
        and organized for post-test analysis while cleaning up any temporary
        resources or analysis tool processes.

        Default implementation provides no-op behavior for environments
        that don't require explicit teardown, but can be overridden for
        complex analysis tools requiring cleanup.
        """
        pass
