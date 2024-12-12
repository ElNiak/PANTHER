from pathlib import Path

import yaml

from panther.plugins.plugin_interface import IPlugin


class IProtocolManager(IPlugin):
    """
    IProtocolManager is a class that manages protocol configurations for a given service type.

    Attributes:
        service_config_to_test_path (str): The path to the service configuration file.
        service_config_to_test (dict): The loaded configuration data.

    Methods:
        __init__(service_type: str):
            Initializes the IProtocolManager with the specified service type.

        validate_config():

        load_config() -> dict:
            Loads the YAML configuration file and returns its contents as a dictionary.
    """

    def __init__(
        self,
        service_type: str,
    ):
        # TODO enforce
        super().__init__()
        self.service_config_to_test_path = f"panther/plugins/protocols/{service_type}/"
        self.service_config_to_test = self.load_config()
        self.validate_config()

    def validate_config(self):
        """
        Validates the configuration file.
        """
        pass

    def load_config(self) -> dict:
        """
        Loads the YAML configuration file.
        """
        config_file = Path(self.service_config_to_test_path)
        if not config_file.exists():
            self.logger.error(
                f"Configuration file '{self.service_config_to_test_path}' does not exist."
            )
        with open(self.service_config_to_test_path) as f:
            return yaml.safe_load(f)
