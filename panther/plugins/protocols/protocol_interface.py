"""Interface for protocol configuration managers."""

from pathlib import Path

import yaml

from panther.plugins.plugin_interface import IPlugin


class IProtocolManager(IPlugin):
    """Manage protocol configurations for network testing services.

    This abstract base class provides a standard interface for protocol-specific
    configuration management within the PANTHER testing framework. Protocol managers
    handle loading, validation, and access to protocol-specific parameters.

    Attributes:
        service_config_to_test_path (str): Path to the service configuration file.
        service_config_to_test (dict): Loaded configuration data from YAML file.

    Examples:
        Protocol managers handle configuration loading and validation:

        >>> # This is an abstract class, use concrete implementations
        >>> # like QUICProtocol or MiniPProtocol in practice
    """

    def __init__(
        self,
        service_type: str,
    ):
        """Initialize protocol manager with service type configuration.

        Args:
            service_type: Type of service protocol to manage (e.g., 'quic', 'http').

        Raises:
            FileNotFoundError: If the protocol configuration file doesn't exist.
            yaml.YAMLError: If the configuration file contains invalid YAML.
        """
        # TODO enforce service_type validation
        super().__init__()
        self.service_config_to_test_path = f"panther/plugins/protocols/{service_type}/"
        self.service_config_to_test = self.load_config()
        self.validate_config()

    def validate_config(self):
        """Validate the loaded protocol configuration.

        This method should be overridden by concrete implementations to provide
        protocol-specific validation logic. The default implementation performs
        no validation.

        Raises:
            ValueError: If configuration contains invalid or missing required fields.
        """
        pass

    def load_config(self) -> dict:
        """Load protocol configuration from YAML file.

        Reads and parses the YAML configuration file for this protocol type.
        The configuration file path is determined by the service_type provided
        during initialization.

        Returns:
            dict: Parsed configuration data from the YAML file.

        Raises:
            FileNotFoundError: If the configuration file doesn't exist.
            yaml.YAMLError: If the YAML file is malformed.
            PermissionError: If the file cannot be read due to permissions.

        Examples:
            Configuration loading returns a dictionary:

            >>> # Example return value structure
            >>> # {'protocol_version': 'quic-1.0', 'timeout': 30}
        """
        config_file = Path(self.service_config_to_test_path)
        if not config_file.exists():
            self.logger.error(
                "Configuration file '%s' does not exist.",
                self.service_config_to_test_path,
            )
        with open(self.service_config_to_test_path) as f:
            return yaml.safe_load(f)
