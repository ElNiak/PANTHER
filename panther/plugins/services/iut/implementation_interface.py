from abc import ABC
from panther.config.config_experiment_schema import ServiceConfig
from panther.plugins.protocols.config_schema import ProtocolConfig
from panther.plugins.services.services_interface import IServiceManager


class IImplementationManager(IServiceManager, ABC):
    """
    IImplementationManager is an abstract base class that inherits from IServiceManager and ABC.

    Attributes:
        service_config_to_test (ServiceConfig): The configuration of the service to be tested.
        service_type (str): The type of the service.
        protocol (ProtocolConfig): The protocol configuration.
        implementation_name (str): The name of the implementation.

    Methods:
        __init__(service_config_to_test, service_type, protocol, implementation_name):
            Initializes the IImplementationManager with the given service configuration, service type, protocol, and implementation name.

        is_tester():
            Returns False indicating that this implementation is not a tester.
    """

    def __init__(
        self,
        service_config_to_test: ServiceConfig,
        service_type: str,
        protocol: ProtocolConfig,
        implementation_name: str,
    ):
        super().__init__(
            service_config_to_test, service_type, protocol, implementation_name
        )

    def is_tester(self):
        return False
