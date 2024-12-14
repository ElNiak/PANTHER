from abc import abstractmethod
import os
from pathlib import Path
from panther.core.observer.event_manager import EventManager
from panther.plugins.environments.config_schema import EnvironmentConfig
from panther.plugins.plugin_interface import IPlugin


class IEnvironmentPlugin(IPlugin):
    """
    IEnvironmentPlugin is an abstract base class that defines the interface for environment plugins.

    Attributes:
        templates_dir (str): Directory path for templates specific to the environment type and subtype.
        output_dir (str): Directory path for output files.
        env_type (str): Type of the environment.
        env_sub_type (str): Subtype of the environment.
        log_dirs (str): Directory path for log files.
        plugin_loader: Loader for the plugin (initially set to None).
        env_config_to_test (EnvironmentConfig): Configuration of the environment to be tested.
        event_manager (EventManager): Manager for handling events.

    Methods:
        is_network_environment():
            Abstract method. Returns True if the plugin is a network environment.

        setup_environment():
            Abstract method. Sets up the required environment before running experiments.

        teardown_environment():
            Abstract method. Tears down the environment after experiments are completed.
    """

    def __init__(
        self,
        env_config_to_test: EnvironmentConfig,
        output_dir: str,
        env_type: str,
        env_sub_type: str,
        event_manager: EventManager,
    ):
        super().__init__()
        self._plugin_dir = Path(os.path.dirname(__file__))
        self.templates_dir: str = (
            f"{self._plugin_dir}/{env_type}/{env_sub_type}/templates"
        )
        self.output_dir = output_dir
        self.env_type = env_type
        self.env_sub_type = env_sub_type
        self.log_dirs = os.path.join(self.output_dir, "logs")
        self.plugin_loader = None
        self.env_config_to_test = env_config_to_test
        self.event_manager = event_manager

    @abstractmethod
    def is_network_environment(self):
        """
        Returns True if the plugin is a network environment.
        """
        pass

    @abstractmethod
    def setup_environment(self):
        """
        Sets up the required environment before running experiments.
        """
        pass

    @abstractmethod
    def teardown_environment(self):
        """
        Tears down the environment after experiments are completed.
        """
        pass
