import os
from abc import abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Union

if TYPE_CHECKING:
    from panther.plugins.plugin_manager import PluginManager

from jinja2 import Environment, FileSystemLoader, select_autoescape
from omegaconf import OmegaConf

from panther.config.core.models.environment import EnvironmentConfig
from panther.config.core.models.experiment import TestConfig
from panther.config.core.models.global_config import GlobalConfig
from panther.core.observer.management.event_manager import EventManager
from panther.core.utils import log_omega_config_summary
from panther.plugins.environments.environment_interface import IEnvironmentPlugin
from panther.plugins.environments.execution_environment.execution_environment_interface import (
    IExecutionEnvironment,
)
from panther.plugins.services.services_interface import IServiceManager

# PluginManager functionality now integrated into PluginManager


class INetworkEnvironment(IEnvironmentPlugin):
    """
    Network Environment Interface - Service Orchestration Framework

    INetworkEnvironment extends IEnvironmentPlugin to provide network-isolated service orchestration
    capabilities for protocol testing scenarios. This interface abstracts the complexity of managing
    multiple services within controlled network topologies, supporting Docker Compose, Shadow NS
    simulation, and localhost container environments.

    ## Architecture Role

    Network environments serve as the foundation for PANTHER's protocol testing by providing:

    1. **Service Lifecycle Management**: Coordinated startup, monitoring, and teardown of multiple services
    2. **Network Isolation**: Controlled network topologies for reproducible protocol testing
    3. **Template-Driven Configuration**: Jinja2-based configuration generation for dynamic service setup
    4. **Execution Environment Integration**: Seamless coordination with analysis tools (strace, Valgrind)
    5. **Event-Driven Monitoring**: Real-time environment state tracking and logging

    ```mermaid
    graph TD
        A[Network Environment] --> B[Service Orchestration]
        A --> C[Network Topology]
        A --> D[Template Engine]
        A --> E[Execution Integration]

        B --> F[Docker Compose]
        B --> G[Shadow NS]
        B --> H[Localhost Containers]

        C --> I[Network Isolation]
        C --> J[Port Management]
        C --> K[Service Discovery]

        D --> L[Jinja2 Templates]
        D --> M[Configuration Generation]
        D --> N[Variable Resolution]

        E --> O[Analysis Tools]
        E --> P[Output Collection]
        E --> Q[Lifecycle Coordination]
    ```

    ## Service Orchestration Pattern

    Network environments implement a standardized service lifecycle:

    1. **Generate Services**: Create service configurations from templates and test config
    2. **Prepare Environment**: Set up network topology and resource allocation
    3. **Launch Services**: Start services in dependency order with health monitoring
    4. **Deploy Services**: Execute service-specific deployment commands
    5. **Coordinate Execution**: Integrate execution environments for analysis
    6. **Teardown**: Orderly shutdown with resource cleanup and output collection

    ## Template-Driven Configuration

    The Jinja2 template engine enables dynamic configuration generation:

    - **Service Templates**: Docker Compose files, Shadow configuration, startup scripts
    - **Variable Resolution**: Test config parameters, paths, timestamps, service discovery
    - **Security Features**: Autoescape, caching disabled, controlled template access
    - **Filter Extensions**: Path resolution, type checking, shell/YAML quoting

    ## Network Environment Types

    Implementations provide different network isolation strategies:

    - **Docker Compose**: Container-based isolation with Docker networks
    - **Shadow NS**: Network simulation with configurable topology and latency
    - **Localhost Single Container**: Simplified single-service testing environment

    ## Execution Environment Coordination

    Network environments seamlessly integrate with execution analysis tools:

    - **Plugin Setup**: Automatic execution environment initialization
    - **Service Wrapping**: Process execution wrapped with analysis tools
    - **Output Coordination**: Centralized collection of network and execution outputs
    - **Lifecycle Synchronization**: Coordinated startup/teardown sequences

    ## Error Handling and Resilience

    Robust error handling ensures test reliability:

    - **Service Failures**: Individual service failures don't crash entire environment
    - **Template Errors**: Configuration generation errors with detailed diagnostics
    - **Network Issues**: Network setup failures with fallback strategies
    - **Resource Cleanup**: Guaranteed cleanup even on partial setup failures

    Attributes:
        docker_name (str): Docker container identifier for network environment coordination
        network_name (str): Network namespace or Docker network name for service isolation
        execution_environment (List[IExecutionEnvironment]): Integrated execution analysis tools
        services (Dict): Runtime service configuration and state management
        deployment_commands (Dict): Service-specific deployment command sequences
        timeout (int): Default timeout for service operations and health checks
        global_config (GlobalConfig): Framework-wide configuration settings
        test_config (TestConfig): Current test case configuration with service definitions
        services_managers (List[IServiceManager]): Coordinated service management instances
        jinja_env (Environment): Jinja2 template engine with security and performance configuration
        plugin_setup (bool): Flag tracking execution plugin initialization state
    Methods:
        setup_execution_plugins(): Initialize and configure execution analysis environments
        update_environment(): Apply configuration changes to active network environment
        create_log_dir(): Ensure structured logging directories for service output
        generate_from_template(): Jinja2-based configuration file generation with variable resolution
        get_docker_name(): Retrieve Docker container identifier for service coordination
        resolve_environment_variables(): Incremental environment variable resolution with conflict prevention
        generate_environment_services(): Abstract service configuration generation
        prepare_environment(): Abstract network topology and resource preparation
        launch_environment_services(): Abstract service startup with dependency coordination
        deploy_services(): Abstract service deployment command execution
        run(): Abstract main execution loop for environment operation
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
        self.docker_name = None
        self.network_name = f"{env_sub_type}_network"
        self.execution_environment = []

        self.services = {}
        self.deployment_commands = {}
        self.timeout = 60

        self.global_config = None
        self.test_config = None
        self.services_managers = None

        self.logger.debug(
            "Environment settings: %s in %s",
            self.env_config_to_test,
            self.templates_dir,
        )
        self.jinja_env = Environment(
            loader=FileSystemLoader(self.templates_dir),
            autoescape=select_autoescape(["html", "xml", "yml", "yaml"]),
            enable_async=False,
            auto_reload=False,
            cache_size=0,  # Disable caching for security
        )
        self.jinja_env.filters["realpath"] = lambda x: os.path.abspath(x)
        self.jinja_env.filters["is_dict"] = lambda x: isinstance(x, dict)

        # Add regex_replace filter for Docker image name sanitization
        import re

        self.jinja_env.filters[
            "regex_replace"
        ] = lambda value, pattern, replacement: re.sub(pattern, replacement, str(value))
        self.jinja_env.trim_blocks = True
        self.jinja_env.lstrip_blocks = True

        self.plugin_setup = False

    def setup_execution_plugins(self, timestamp):
        """
        Initialize and configure execution analysis environments for coordinated operation.

        This method orchestrates the setup of execution environments (strace, Valgrind, etc.)
        that will wrap service execution to provide analysis capabilities. Each execution
        environment is configured with the current test context and service managers.

        The setup process ensures:
        1. Each execution environment receives current configuration context
        2. Execution environments can coordinate with service lifecycle
        3. Failed execution environment setup is logged but doesn't halt network setup
        4. Plugin setup state is tracked for coordination

        Args:
            timestamp (str): Unique timestamp for this test execution session,
                           used for output file naming and coordination

        Raises:
            Exception: Individual execution environment setup failures are caught,
                      logged with full traceback, and don't propagate to prevent
                      network environment setup failure
        """
        # Debug logging for execution environment setup
        for execution_env in self.execution_environment:
            try:
                self.logger.debug("Setting up execution environment: %s", execution_env)
                execution_env.setup_environment(
                    services_managers=self.services_managers,
                    test_config=self.test_config,
                    global_config=self.global_config,
                    timestamp=timestamp,
                    plugin_manager=self.plugin_manager,
                )
            except Exception as e:
                self.logger.error("Failed to setup execution environment: %s", e)

    def update_environment(
        self,
        execution_environment,
        global_config: "GlobalConfig",
        plugin_manager: "PluginManager",
        services_managers: List[IServiceManager],
        test_config: "TestConfig",
    ):
        """
        Apply configuration updates to active network environment state.

        This method synchronizes the network environment with updated configuration,
        service definitions, and execution contexts. It ensures the environment
        maintains consistency with the current test execution state.

        Configuration updates include:
        1. Service manager registration for service lifecycle coordination
        2. Test configuration updates affecting service behavior
        3. Execution environment integration for analysis tool coordination
        4. Plugin manager updates for dynamic plugin loading
        5. Global configuration changes affecting framework behavior

        The method also performs debug logging of the updated configuration
        to support troubleshooting and monitoring.

        Args:
            execution_environment: Updated list of execution analysis environments
            global_config (GlobalConfig): Current framework-wide configuration settings
            plugin_manager (PluginManager): Plugin management system for dynamic loading
            services_managers (List[IServiceManager]): Updated service management instances
            test_config (TestConfig): Current test case configuration and service definitions

        Returns:
            None: Updates are applied to instance state
        """
        self.services_managers: List[IServiceManager] = services_managers
        self.test_config = test_config
        self.execution_environment = execution_environment
        self.plugin_manager = plugin_manager
        self.global_config = global_config

        self.logger.debug(
            "Output directory: %s, Log directory: %s", self.output_dir, self.log_dirs
        )
        self.logger.debug("Setup environment with:")
        for service in self.services_managers:
            self.logger.debug("Service: %s", service)
        # Log configuration for debugging using summarizer
        from panther.core.utils import log_omega_config_summary

        log_omega_config_summary(self.logger, "Test Config", self.test_config)
        log_omega_config_summary(self.logger, "Global Config", self.global_config)

    def create_log_dir(self, service: IServiceManager):
        """
        Ensure structured logging directory exists for service output collection.

        Creates service-specific logging directories within the environment's log
        structure to support organized output collection and analysis. The logging
        hierarchy follows the pattern: logs/{service_name}/ for each service.

        This method ensures:
        1. Service-specific log directories are created as needed
        2. Logging structure supports multiple concurrent services
        3. Directory creation is idempotent (safe to call multiple times)
        4. Log directory creation is tracked for monitoring

        Args:
            service (IServiceManager): Service manager instance containing the
                                     service name for directory creation

        Logs:
            Info: Logs successful log directory creation for monitoring and debugging
        """
        log_dir = os.path.join(self.log_dirs, service.service_name)
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
            self.logger.info("Created log directory: %s", log_dir)

    def generate_from_template(
        self,
        template_name,
        paths,
        timestamp,
        rendered_out_file,
        out_file,
        additional_param=None,
        structured_commands=None,
        **kwargs,
    ):
        """
        Generate configuration files from Jinja2 templates with comprehensive variable resolution.

        This method transforms Jinja2 templates into environment-specific configuration files
        (Docker Compose, Shadow config, startup scripts) by resolving variables from test
        configuration, service definitions, and runtime context.

        Template Generation Process:
        1. Load template from environment-specific templates directory
        2. Resolve variables from multiple sources (test config, services, paths, etc.)
        3. Apply security filters for shell and YAML quoting
        4. Render template with full variable context
        5. Write rendered output to both generated and final locations

        Variable Sources:
        - services: Service manager instances with configuration
        - test_config: Test case configuration and parameters
        - paths: Environment-specific path mappings
        - timestamp: Unique execution session identifier
        - additional_param: Custom parameters for specific templates
        - structured_commands: Command generation context for execution environments

        Security Features:
        - Template autoescape for HTML/XML/YAML content
        - Shell command quoting via shlex.quote
        - YAML value quoting for safe serialization
        - Disabled template caching to prevent stale configuration

        Args:
            template_name (str): Jinja2 template filename within templates directory
            paths (Dict[str, str]): Path mappings for container/host resolution
            timestamp (str): Unique timestamp for output file naming
            rendered_out_file (str): Path for rendered template output (debugging)
            out_file (str): Path for final configuration file
            additional_param (Dict, optional): Custom template variables
            structured_commands (Dict, optional): Command generation context for execution tools
            **kwargs: Additional template variables

        Returns:
            None: Configuration files are written to specified paths

        Note:
            ShellCommand objects are automatically converted to strings during rendering.
            No preprocessing of commands should be done before calling this method
            to avoid duplicate command generation in output files.
        """
        # # Register shell and YAML quoting filters
        # self.jinja_env.filters["quote_shell"] = lambda s: shlex.quote(str(s))
        # self.jinja_env.filters["quote_yaml"] = lambda s: yaml.safe_dump(str(s)).strip()

        template = self.jinja_env.get_template(template_name)
        self.logger.debug("Template: %s", template)
        self.logger.debug("Services: %s", self.services_managers)
        # Use summarizer for concise config logging
        log_omega_config_summary(self.logger, "Deployment Info", self.test_config)
        self.logger.debug("Paths: %s", paths)
        self.logger.debug("Timestamp: %s", timestamp)
        self.logger.debug("Additional Param: %s", additional_param)
        self.logger.debug("Structured Commands:")
        if structured_commands is None:
            self.logger.debug("  None")
        else:
            for cmd_phase, commands in structured_commands.items():
                self.logger.debug("  %s: %s", cmd_phase, commands)
        rendered = template.render(
            services=self.services_managers,
            test_config=self.test_config,
            paths=paths,
            timestamp=timestamp,
            additional_param=additional_param,
            structured_commands=structured_commands,
            log_dir=self.log_dirs,
            output_dir=self.output_dir,
            experiment_name=str(self.output_dir).split("/")[-1],
            **kwargs,  # Pass any additional parameters to the template
        )
        # Write the rendered content to <env>.generated.yml
        with open(out_file, "w") as f:
            f.write(rendered)
        with open(rendered_out_file, "w") as f:
            f.write(rendered)

    def is_network_environment(self):
        """
        Network environment classification for framework orchestration.

        Returns True to indicate this is a network environment that provides
        service orchestration and network isolation capabilities, as opposed
        to execution environments that wrap individual process execution.

        Returns:
            bool: Always True for network environment implementations
        """
        return True

    @abstractmethod
    def generate_environment_services(self, paths: Dict[str, str], timestamp: str):
        """
        Generate service configurations from templates and test definition.

        Transform test case service definitions into environment-specific service
        configurations (Docker Compose services, Shadow processes, etc.) using
        template-driven generation with path resolution and timestamp coordination.

        Args:
            paths (Dict[str, str]): Path mappings for container/host resolution
            timestamp (str): Unique timestamp for configuration file naming

        Returns:
            Generated service configurations specific to environment type

        Raises:
            NotImplementedError: Must be implemented by concrete environment classes
        """
        raise NotImplementedError()

    @abstractmethod
    def prepare_environment(self):
        """
        Prepare network topology and resource allocation for service execution.

        Initialize the network environment infrastructure including:
        1. Network namespace or Docker network creation
        2. Resource allocation and limits configuration
        3. Security and isolation setup
        4. Pre-service infrastructure preparation

        Raises:
            NotImplementedError: Must be implemented by concrete environment classes
        """
        raise NotImplementedError()

    @abstractmethod
    def launch_environment_services(self):
        """
        Launch services in dependency order with health monitoring.

        Orchestrate service startup ensuring:
        1. Service dependency resolution and ordering
        2. Health checks and readiness verification
        3. Network connectivity validation
        4. Failure detection and recovery strategies

        Raises:
            NotImplementedError: Must be implemented by concrete environment classes
        """
        raise NotImplementedError()

    @abstractmethod
    def run(self):
        """
        Execute main environment operation loop with service coordination.

        Implement the primary execution loop for environment operation including:
        1. Service monitoring and health checking
        2. Event processing and state updates
        3. Failure detection and recovery
        4. Graceful shutdown coordination

        Raises:
            NotImplementedError: Must be implemented by concrete environment classes
        """
        raise NotImplementedError()

    @abstractmethod
    def deploy_services(self):
        """
        Execute service-specific deployment commands and initialization.

        Perform post-launch service deployment including:
        1. Service-specific configuration application
        2. Deployment command execution
        3. Service initialization and setup
        4. Deployment verification and validation

        Raises:
            NotImplementedError: Must be implemented by concrete environment classes
        """
        raise NotImplementedError()

    @abstractmethod
    def setup_environment(
        self,
        services_managers: List[IServiceManager],
        test_config: TestConfig,
        global_config: GlobalConfig,
        timestamp: str,
        plugin_manager: "Optional[PluginManager]",
        execution_environment: List[IExecutionEnvironment],
    ):
        """
        Orchestrate complete network environment setup with service coordination.

        Coordinate the full network environment initialization including:
        1. Service configuration generation and validation
        2. Network topology setup and isolation
        3. Service deployment and health verification
        4. Execution environment integration and coordination

        Args:
            services_managers (List[IServiceManager]): Service management instances
            test_config (TestConfig): Test case configuration and service definitions
            global_config (GlobalConfig): Framework-wide configuration settings
            timestamp (str): Unique timestamp for session coordination
            plugin_manager (Optional[PluginManager]): Plugin management for dynamic loading
            execution_environment (List[IExecutionEnvironment]): Analysis tool integration

        Raises:
            NotImplementedError: Must be implemented by concrete environment classes
        """
        raise NotImplementedError()

    @abstractmethod
    def teardown_environment(self):
        """
        Orchestrate complete network environment cleanup with resource deallocation.

        Coordinate orderly environment shutdown including:
        1. Service termination and graceful shutdown
        2. Network resource cleanup and deallocation
        3. Output collection and finalization
        4. Execution environment cleanup and analysis
        5. Event emission for lifecycle tracking

        Raises:
            NotImplementedError: Must be implemented by concrete environment classes
        """
        raise NotImplementedError()
