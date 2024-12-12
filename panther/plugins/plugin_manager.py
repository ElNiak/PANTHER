import importlib.util
import logging
from pathlib import Path

from panther.core.observer.event_manager import EventManager
from panther.config.config_experiment_schema import ServiceConfig, TestConfig
from panther.plugins.protocols.config_schema import ProtocolConfig
from panther.plugins.services.iut.config_schema import ImplementationConfig
from panther.plugins.services.services_interface import IServiceManager
from panther.plugins.environments.network_environment.network_environment_interface import (
    INetworkEnvironment,
)
from panther.plugins.environments.execution_environment.execution_environment_interface import (
    IExecutionEnvironment,
)
from panther.plugins.services.iut.implementation_interface import IImplementationManager
from panther.plugins.environments.environment_interface import IEnvironmentPlugin
from panther.plugins.plugin_loader import PluginLoader


class PluginManager:
    """
    Manages the loading and instantiation of various plugins for the system.

    Attributes:
        plugins_loader (PluginLoader): The loader responsible for loading plugins.
        logger (logging.Logger): Logger instance for logging messages.
        protocol_plugins (Dict[str, IServiceManager]): Dictionary to store protocol plugins.
        network_environment_plugins (Dict[str, INetworkEnvironment]): Dictionary to store network environment plugins.
        execution_environment_plugins (Dict[str, IExecutionEnvironment]): Dictionary to store execution environment plugins.

    Methods:
        create_service_manager(protocol: ProtocolConfig, implementation: ImplementationConfig, implementation_dir: Path, service_config_to_test: ServiceConfig) -> IServiceManager:
            Creates and returns an instance of a service manager for the given protocol and implementation.

        create_environment_manager(environment: str, test_config: TestConfig, environment_dir: Path, output_dir: Path, event_manager: EventManager) -> IEnvironmentPlugin:
            Creates and returns an instance of an environment manager for the given environment.
    """

    def __init__(self, plugins_loader: PluginLoader):
        self.plugins_loader = plugins_loader
        self.logger = logging.getLogger("PluginManager")
        self.protocol_plugins: dict[str, IServiceManager] = {}
        self.network_environment_plugins: dict[str, INetworkEnvironment] = {}
        self.execution_environment_plugins: dict[str, IExecutionEnvironment] = {}

    def create_service_manager(
        self,
        protocol: ProtocolConfig,
        implementation: ImplementationConfig,
        implementation_dir: Path,
        service_config_to_test: ServiceConfig,
    ) -> IServiceManager:
        """
        Creates an instance of a service manager for a given protocol and implementation.

        This method dynamically loads a service manager class from a specified implementation
        directory and creates an instance of it. The service manager class must inherit from
        IServiceManager.

        Args:
            protocol (ProtocolConfig): The protocol configuration.
            implementation (ImplementationConfig): The implementation configuration.
            implementation_dir (Path): The directory where the implementation is located.
            service_config_to_test (ServiceConfig): The service configuration to test.

        Returns:
            IServiceManager: An instance of the service manager.

        Raises:
            FileNotFoundError: If the service manager file does not exist.
            AttributeError: If the service manager class is not found or does not inherit from IServiceManager.
            ImportError: If the module cannot be loaded.
        """
        service_manager_path = implementation_dir / f"{implementation.name}.py"
        if not service_manager_path.exists():
            self.logger.error(
                f"Service manager file '{service_manager_path}' does not exist."
            )
            raise FileNotFoundError(
                f"Service manager file '{service_manager_path}' not found."
            )

        # Here we trying to load the service manager class from the implementation plugin
        service_module_name = f"{protocol.name}.{implementation.name}"
        spec = importlib.util.spec_from_file_location(
            service_module_name, service_manager_path
        )
        self.logger.debug(
            f"Loading module from '{service_manager_path}' as '{service_module_name}' with spec {spec}"
        )
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            # We are trying to load the class from the module
            class_name = PluginLoader.get_class_name(
                implementation.name, suffix="ServiceManager"
            )
            self.logger.debug(f"Loading class '{class_name}' from module '{module}'")
            service_manager_class = getattr(module, class_name, None)
            if service_manager_class and issubclass(
                service_manager_class, IServiceManager
            ):
                # Less elegant way (than service_type = service_manager_class.service_type)
                # to determine the service type BUT it works and no need to define property
                service_type = (
                    "iut"
                    if issubclass(service_manager_class, IImplementationManager)
                    else "testers"
                )
                instance = service_manager_class(
                    service_config_to_test=service_config_to_test,
                    service_type=service_type,
                    protocol=protocol,
                    implementation_name=implementation.name,
                )
                self.logger.debug(f"Preparing instance of '{class_name}'")
                instance.prepare(self.plugins_loader)
                self.logger.debug(f"Created instance of '{class_name}'")
                return instance
            else:
                self.logger.error(
                    f"Service manager class '{class_name}' not found or does not inherit from IImplementationManager."
                )
                raise AttributeError(
                    f"Service manager class '{class_name}' not found or invalid."
                )
        else:
            self.logger.error(f"Cannot load module from '{service_manager_path}'")
            raise ImportError(f"Cannot load module from '{service_manager_path}'")

    def create_environment_manager(
        self,
        environment: str,
        test_config: TestConfig,
        environment_dir: Path,
        output_dir: Path,
        event_manager: EventManager,
    ) -> IEnvironmentPlugin:
        """
        Creates an instance of an environment manager by dynamically loading the appropriate
        environment plugin module and class.

        Args:
            environment (str): The name of the environment to be managed.
            test_config (TestConfig): The test configuration object containing environment settings.
            environment_dir (Path): The directory path where environment plugins are located.
            output_dir (Path): The directory path where output files should be stored.
            event_manager (EventManager): The event manager instance to handle events.

        Returns:
            IEnvironmentPlugin: An instance of the environment manager class.

        Raises:
            FileNotFoundError: If the environment plugin file does not exist.
            AttributeError: If the environment class is not found or does not inherit from IEnvironmentPlugin.
            ImportError: If the module cannot be loaded.
        """
        environment_plugin_path = environment_dir / environment / f"{environment}.py"
        if not environment_plugin_path.exists():
            self.logger.error(
                f"Environment plugin file '{environment_plugin_path}' does not exist."
            )
            raise FileNotFoundError(
                f"Environment plugin file '{environment_plugin_path}' not found."
            )

        # Here we trying to load the environment manager class from the environment plugin
        environment_module_name = f"environments.{environment}"
        spec = importlib.util.spec_from_file_location(
            environment_module_name, environment_plugin_path
        )
        self.logger.debug(
            f"Loading module from '{environment_plugin_path}' as '{environment_module_name}' with spec {spec}"
        )
        if spec and spec.loader:
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            class_name = PluginLoader.get_class_name(environment, suffix="Environment")
            environment_class = getattr(module, class_name, None)
            if environment_class and issubclass(environment_class, IEnvironmentPlugin):
                self.logger.debug(
                    f"Loading test configuration for '{environment}' - {environment_dir.name}"
                )
                env_config = (
                    test_config.execution_environments
                    if environment_dir.name == "execution_environment"
                    else test_config.network_environment
                )
                self.logger.debug(
                    f"Loading class '{class_name}' from module '{module}'"
                )
                instance = environment_class(
                    env_config_to_test=env_config,
                    output_dir=str(output_dir),
                    env_type=environment_dir.name,
                    env_sub_type=environment,
                    event_manager=event_manager,
                )
                self.logger.debug(f"Created instance of '{class_name}'")
                return instance
            else:
                self.logger.error(
                    f"Environment class '{class_name}' not found or does not inherit from IEnvironmentPlugin."
                )
                raise AttributeError(
                    f"Environment class '{class_name}' not found or invalid."
                )
        else:
            self.logger.error(f"Cannot load module from '{environment_plugin_path}'")
            raise ImportError(f"Cannot load module from '{environment_plugin_path}'")
