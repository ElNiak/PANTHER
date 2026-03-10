"""Execution environment interface for process analysis tools."""

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
    """Interface for process analysis execution environments.

    Extends `IEnvironmentPlugin` to wrap individual service execution with
    analysis tools (strace, Valgrind, GDB, profilers). Unlike network
    environments that orchestrate multiple services, execution environments
    instrument single processes.

    Command generation follows a layered pattern:
        1. Base command from service manager
        2. Tool wrapping (prefix/suffix)
        3. Output redirection and logging
        4. Environment variable configuration

    Attributes:
        services_managers: Service instances to wrap with analysis.
        test_config: Current test configuration.
        analysis_tool: Specific analysis tool name (strace, valgrind, gdb, etc.).
        command_builder: Dynamic command generation utility.
    """

    def __init__(
        self,
        env_config_to_test: EnvironmentConfig,
        output_dir: str,
        env_type: str,
        env_sub_type: str,
        event_manager: EventManager,
    ):
        """Initialize IExecutionEnvironment."""
        super().__init__(
            env_config_to_test, output_dir, env_type, env_sub_type, event_manager
        )
        self.services_managers = []
        self.test_config = None

    def is_network_environment(self):
        """Execution environment classification for framework orchestration.

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
        """Configure analysis tool and prepare for service execution wrapping.

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
        """Finalize analysis output and collect artifacts for post-processing.

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
