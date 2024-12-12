from abc import ABC

from panther.config.config_experiment_schema import ServiceConfig
from panther.plugins.services.services_interface import IServiceManager


class ITesterManager(IServiceManager, ABC):

    def __init__(
        self,
        service_config_to_test: ServiceConfig,
        service_type: str,
        protocol: str,
        implementation_name: str,
    ):
        super().__init__(
            service_config_to_test, service_type, protocol, implementation_name
        )
