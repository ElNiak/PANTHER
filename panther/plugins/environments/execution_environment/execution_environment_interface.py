from abc import abstractmethod

from panther.plugins.plugin_loader import PluginLoader

from panther.config.config_global_schema import GlobalConfig

from panther.config.config_experiment_schema import TestConfig

from panther.plugins.services.services_interface import IServiceManager

from panther.core.observer.event_manager import EventManager
from panther.plugins.environments.config_schema import EnvironmentConfig
from panther.plugins.environments.environment_interface import IEnvironmentPlugin


class IExecutionEnvironment(IEnvironmentPlugin):
    """
    IExecutionEnvironment is an abstract base class that defines the interface for execution environment plugins.

    Attributes:
        services_managers (list): A list to store service managers.
        test_config (TestConfig): Configuration for the test, initially set to None.

    Methods:
        __init__(env_config_to_test, output_dir, env_type, env_sub_type, event_manager):
            Initializes the execution environment with the given configuration.

        is_network_environment():
            Returns True if the plugin is a network environment. Default implementation returns False.

        setup_environment(services_managers, test_config, global_config, timestamp, plugin_loader):
            Abstract method to set up the required environment before running experiments. Must be implemented by subclasses.

        teardown_environment():
            Tears down the environment after experiments are completed. Default implementation does nothing.
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
        Returns True if the plugin is an network environment.
        """
        return False

    @abstractmethod
    def setup_environment(
        self,
        services_managers: list[IServiceManager],
        test_config: TestConfig,
        global_config: GlobalConfig,
        timestamp: str,
        plugin_loader: PluginLoader,
    ):
        """
        Sets up the required environment before running experiments.
        """
        raise NotImplementedError()

    def teardown_environment(self):
        """
        Tears down the environment after experiments are completed.
        """
        pass
