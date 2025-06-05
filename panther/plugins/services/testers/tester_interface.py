from abc import ABC

from panther.config.config_experiment_schema import ServiceConfig
from panther.plugins.protocols.config_schema import ProtocolConfig
from panther.core.observer.event_manager import EventManager
from panther.plugins.services.service_base import ServiceBase


class ITesterManager(ServiceBase, ABC):

    def __init__(
        self,
        service_config_to_test: ServiceConfig,
        service_type: str,
        protocol: ProtocolConfig,
        implementation_name: str,
        event_manager: EventManager | None = None,
    ):
        super().__init__(
            service_config_to_test, service_type, protocol, implementation_name, event_manager
        )
