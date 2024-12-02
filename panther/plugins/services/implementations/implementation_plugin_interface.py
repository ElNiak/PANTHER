# factories/implementation_plugin_interface.py
from abc import ABC, abstractmethod

class ImplementationPluginInterface(ABC):
    """
    Interface for all implementation-specific plugins. This ensures that each plugin can create
    and configure client and server objects for its specific implementation.
    """
    @property
    @abstractmethod
    def implementation_name(self) -> str:
        """
        Returns the name of the implementation (e.g., 'quiche', 'quinn').
        This is used to identify the plugin within the protocol plugin.
        """
        pass

    @abstractmethod
    def create_client(self, params: dict, protocol_params: dict):
        """
        Creates and configures a client object for this implementation.
        :param params: A dictionary of parameters specific to this client instance (e.g., host, port).
        :param protocol_params: A dictionary of additional protocol-specific parameters.
        :return: A client object that can be used to run tests or experiments.
        """
        pass

    @abstractmethod
    def create_server(self, params: dict, protocol_params: dict):
        """
        Creates and configures a server object for this implementation.
        :param params: A dictionary of parameters specific to this server instance (e.g., host, port).
        :param protocol_params: A dictionary of additional protocol-specific parameters.
        :return: A server object that can be used to run tests or experiments.
        """
        pass
