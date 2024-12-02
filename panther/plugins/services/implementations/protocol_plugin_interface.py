# factories/protocol_plugin_interface.py
from abc import ABC, abstractmethod

class ProtocolPluginInterface(ABC):
    @property
    @abstractmethod
    def protocol_name(self) -> str:
        """Returns the name of the protocol (e.g., 'QUIC', 'HTTP')"""
        pass
    
    @abstractmethod
    def get_managed_options(self):
        """
        Returns the managed options for this protocol.
        This should include all possible configurations and their default values.
        """
        pass

    @abstractmethod
    def validate_options(self, selected_options: dict) -> bool:
        """
        Validates the selected options against the managed options.
        :param selected_options: The selected experiment options to validate.
        :return: True if valid, False otherwise.
        """
        pass
    
    @abstractmethod
    def create_client(self, implementation: str, params: dict, protocol_params: dict):
        """Creates a client object for the specified implementation with protocol-specific parameters."""
        pass

    @abstractmethod
    def create_server(self, implementation: str, params: dict, protocol_params: dict):
        """Creates a server object for the specified implementation with protocol-specific parameters."""
        pass

    @abstractmethod
    def load_sub_plugins(self):
        """Loads sub-plugins for specific implementations."""
        pass
