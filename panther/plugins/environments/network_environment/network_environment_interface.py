import traceback
from abc import abstractmethod
import os

from jinja2 import Environment, FileSystemLoader
from omegaconf import OmegaConf

from panther.plugins.services.services_interface import IServiceManager

from panther.config.config_experiment_schema import TestConfig

from panther.config.config_global_schema import GlobalConfig

from panther.plugins.plugin_loader import PluginLoader

from panther.core.observer.event_manager import EventManager
from panther.plugins.environments.config_schema import EnvironmentConfig
from panther.plugins.environments.execution_environment.execution_environment_interface import (
    IExecutionEnvironment,
)
from panther.plugins.environments.environment_interface import IEnvironmentPlugin


class INetworkEnvironment(IEnvironmentPlugin):
    """
    INetworkEnvironment is an abstract class that defines the interface for network environment plugins.
    It inherits from IEnvironmentPlugin and provides methods for setting up, updating, and managing network environments.
    Attributes:
        docker_name (str): Name of the Docker container.
        execution_environment (list): List of execution environments.
        network_name (str): Name of the network.
        execution_environments (list): List of execution environments.
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
        update_environment(execution_environment, global_config, plugin_loader, services_managers, test_config):
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
        setup_environment(services_managers, test_config, global_config, timestamp, plugin_loader, execution_environment):
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
        self.execution_environment = None
        self.network_name = f"{env_sub_type}_network"
        self.execution_environments = []

        self.services = {}
        self.deployment_commands = {}
        self.timeout = 60

        self.global_config = None
        self.test_config = None
        self.services_managers = None

        self.logger.debug(
            f"Environment settings: {self.env_config_to_test} in {self.templates_dir}"
        )
        self.jinja_env = Environment(loader=FileSystemLoader(self.templates_dir))
        self.jinja_env.filters["realpath"] = lambda x: os.path.abspath(x)
        self.jinja_env.filters["is_dict"] = lambda x: isinstance(x, dict)
        self.jinja_env.trim_blocks = True
        self.jinja_env.lstrip_blocks = True

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
        for execution_env in self.execution_environment:
            try:
                self.logger.debug(f"Setting up execution environment: {execution_env}")
                execution_env.setup_environment(
                    services_managers=self.services_managers,
                    test_config=self.test_config,
                    global_config=self.global_config,
                    timestamp=timestamp,
                    plugin_loader=self.plugin_loader,
                )
            except Exception as e:
                self.logger.error(
                    f"Failed to setup execution environment: {e}\n{traceback.format_exc()}"
                )

    def update_environment(
        self,
        execution_environment,
        global_config,
        plugin_loader,
        services_managers,
        test_config,
    ):
        """
        Updates the network environment with the provided configuration and services.

        Args:
            execution_environment (Any): The execution environment to be used.
            global_config (OmegaConf): The global configuration settings.
            plugin_loader (Any): The plugin loader instance.
            services_managers (List[IServiceManager]): A list of service manager instances.
            test_config (OmegaConf): The test configuration settings.

        Returns:
            None
        """
        self.services_managers: list[IServiceManager] = services_managers
        self.test_config = test_config
        self.execution_environment = execution_environment
        self.plugin_loader = plugin_loader
        self.global_config = global_config
        self.logger.debug("Setup environment with:")
        for service in self.services_managers:
            self.logger.debug(f"Service: {service}")
        self.logger.debug(f"Test Config: {OmegaConf.to_yaml(self.test_config)}")
        self.logger.debug(f"Global Config: {OmegaConf.to_yaml(self.global_config)}")

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
            self.logger.info(f"Created log directory: {log_dir}")

    def generate_from_template(
        self,
        template_name,
        paths,
        timestamp,
        rendered_out_file,
        out_file,
        additional_param=None,
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

        Returns:
            None
        """
        template = self.jinja_env.get_template(template_name)
        self.logger.debug(f"Template: {template}")
        self.logger.debug(f"Services: {self.services_managers}")
        self.logger.debug(f"Deployment Info: {self.test_config}")
        rendered = template.render(
            services=self.services_managers,
            test_config=self.test_config,
            paths=paths,
            timestamp=timestamp,
            additional_param=additional_param,
            log_dir=self.log_dirs,
            experiment_name=self.output_dir.split("/")[-1],
        )
        # Write the rendered content to shadow.generated.yml
        with open(out_file, "w") as f:
            f.write(rendered)
        with open(rendered_out_file, "w") as f:
            f.write(rendered)

    def get_docker_name(self):
        """
        Retrieves and sets the Docker container name by building a Docker image from a specified path.

        This method uses the `plugin_loader` to build a Docker image from the provided Dockerfile path,
        Docker name, and Docker version. It then extracts and sets the Docker container name by splitting
        the resulting Docker image name at the colon (':') character.

        Returns:
            str: The name of the Docker container.
        """
        self.docker_name = self.plugin_loader.build_docker_image_from_path(
            self.services_network_docker_file_path,
            self.docker_name,
            self.docker_version,
        )
        self.docker_name = self.docker_name.split(":")[0]

    def resolve_environment_variables(self, env_vars):
        """
        Resolves environment variables incrementally, ensuring no duplication
        and preserving unresolved tokens. Processes variables in dependency order.

        :param env_vars: dict, environment variables with potential references.
        :return: dict, resolved environment variables.
        """
        resolved_env = {}

        self.logger.debug("Initial environment variables:")
        for k, v in env_vars.items():
            self.logger.debug(f"{k}: {v}")

        for key, value in env_vars.items():
            if isinstance(value, str):
                resolved_value = value
                self.logger.debug(
                    f"Resolving variable: {key} - Original value: {value}"
                )
                for (
                    var_name,
                    var_value,
                ) in resolved_env.items():  # Use already resolved variables
                    if (
                        f"${{{var_name}}}" in resolved_value
                        or f"${var_name}" in resolved_value
                    ):
                        resolved_value = resolved_value.replace(
                            f"${{{var_name}}}", var_value
                        )
                        resolved_value = resolved_value.replace(
                            f"${var_name}", var_value
                        )
                        self.logger.debug(
                            f"Replaced ${var_name} in {key} with {var_value}"
                        )
                resolved_value = resolved_value.replace("$", "$$")
                resolved_env[key] = resolved_value

        self.logger.debug("Final resolved environment variables without duplication:")
        for k, v in resolved_env.items():
            self.logger.debug(f"{k}: {v}")

        return resolved_env

    def is_network_environment(self):
        """
        Returns True if the plugin is a network environment.
        """
        return True

    @abstractmethod
    def generate_environment_services(self, paths: dict[str, str], timestamp: str):
        """
        Generates the services required for the network environment.

        :param services: A dictionary containing the services to be generated.
        :return: A list of generated services.
        """
        pass

    @abstractmethod
    def prepare_environment(self):
        """
        Prepares the environment for running experiments.
        """
        pass

    @abstractmethod
    def launch_environment_services(self):
        """
        Launches the services in the network environment.
        """
        pass

    @abstractmethod
    def deploy_services(self):
        """
        Deploys the specified services in the network environment.
        """
        pass

    @abstractmethod
    def setup_environment(
        self,
        services_managers: list[IServiceManager],
        test_config: TestConfig,
        global_config: GlobalConfig,
        timestamp: str,
        plugin_loader: PluginLoader,
        execution_environment: list[IExecutionEnvironment],
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
        pass
