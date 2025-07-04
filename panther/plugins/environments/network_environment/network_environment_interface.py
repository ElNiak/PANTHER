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
    INetworkEnvironment is an abstract class that defines the interface for network environment plugins.
    It inherits from IEnvironmentPlugin and provides methods for setting up, updating, and managing network environments.
    Attributes:
        docker_name (str): Name of the Docker container.
        execution_environment (list): List of execution environments.
        network_name (str): Name of the network.
        execution_environment (list): List of execution environments.
        services (dict): Dictionary of services.
        deployment_commands (dict): Dictionary of deployment commands.
        timeout (int): Timeout value.
        global_config (GlobalConfig): Global configuration.
        test_config (TestConfig): Test configuration.
        services_managers (list): List of service managers.
        logger (Logger): Logger instance.
        jinja_env (Environment): Jinja2 environment for template rendering.
    Methods:
        __init__(env_config_to_test, output_dir, env_type, env_sub_type, event_manager):
            Initializes the network environment with the given configuration.
        setup_execution_plugins(timestamp):
            Sets up execution plugins for the environment.
        update_environment(execution_environment, global_config, plugin_manager, services_managers, test_config):
            Updates the environment with the given configuration and services.
        create_log_dir(service):
            Creates a log directory for the given service.
        generate_from_template(template_name, paths, timestamp, rendered_out_file, out_file, additional_param=None):
            Generates a file from a Jinja2 template.
        get_docker_name():
            Retrieves the Docker container name.
        resolve_environment_variables(env_vars):
            Resolves environment variables incrementally, ensuring no duplication and preserving unresolved tokens.
        is_network_environment():
        generate_environment_services(paths, timestamp):
            Abstract method to generate the services required for the network environment.
        prepare_environment():
            Abstract method to prepare the environment for running experiments.
        launch_environment_services():
            Abstract method to launch the services in the network environment.
        deploy_services():
            Abstract method to deploy the specified services in the network environment.
        setup_environment(services_managers, test_config, global_config, timestamp, plugin_manager, execution_environment):
            Abstract method to set up the required environment before running experiments.
        teardown_environment():
            Abstract method to tear down the environment after experiments are completed.
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
        Sets up the execution plugins for each execution environment.

        This method iterates through the list of execution environments and sets up each one by calling its
        `setup_environment` method with the necessary parameters. If an error occurs during the setup of any
        execution environment, it logs the error along with the traceback.

        Args:
            timestamp (str): The timestamp to be used during the setup of the execution environments.

        Raises:
            Exception: If an error occurs during the setup of any execution environment, it is caught and logged.
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
        Updates the network environment with the provided configuration and services.

        Args:
            execution_environment (Any): The execution environment to be used.
            global_config (OmegaConf): The global configuration settings.
            plugin_manager (Any): The plugin manager instance.
            services_managers (List[IServiceManager]): A list of service manager instances.
            test_config (OmegaConf): The test configuration settings.

        Returns:
            None
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
        Creates a log directory for the given service if it does not already exist.

        Args:
            service (IServiceManager): The service manager instance containing the service name.

        Logs:
            Info: Logs the creation of the log directory if it was created.
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
        Generates a configuration file from a Jinja2 template.

        Args:
            template_name (str): The name of the Jinja2 template to use.
            paths (dict): A dictionary of paths to be used in the template.
            timestamp (str): A timestamp to be included in the rendered template.
            rendered_out_file (str): The file path where the rendered template will be saved.
            out_file (str): The file path where the final output will be saved.
            additional_param (dict, optional): Additional parameters to be passed to the template. Defaults to None.
            structured_commands (dict, optional): Structured command arguments for enhanced command generation.

        Returns:
            None

        Note:
            This method handles the conversion of ShellCommand objects to strings.
            No preprocessing of commands should be done before calling this method
            to avoid duplicate command generation in the output files.
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
        Returns True if the plugin is a network environment.
        """
        return True

    @abstractmethod
    def generate_environment_services(self, paths: Dict[str, str], timestamp: str):
        """
        Generates the services required for the network environment.

        :param services: A dictionary containing the services to be generated.
        :return: A list of generated services.
        """
        raise NotImplementedError()

    @abstractmethod
    def prepare_environment(self):
        """
        Prepares the environment for running experiments.
        """
        raise NotImplementedError()

    @abstractmethod
    def launch_environment_services(self):
        """
        Launches the services in the network environment.
        """
        raise NotImplementedError()

    @abstractmethod
    def run(self):
        """
        Runs the services in the network environment.
        This method should be implemented to handle the execution of services.
        """
        raise NotImplementedError()

    @abstractmethod
    def deploy_services(self):
        """
        Deploys the specified services in the network environment.
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
        Sets up the required environment before running experiments.
        """
        raise NotImplementedError()

    @abstractmethod
    def teardown_environment(self):
        """
        Tears down the environment after experiments are completed.
        """
        raise NotImplementedError()
