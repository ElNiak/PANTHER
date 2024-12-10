from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from config.config_experiment_schema import ServiceConfig
from plugins.protocols.config_schema import ProtocolConfig
from plugins.services.services_interface import IServiceManager

class IImplementationManager(IServiceManager):
    def __init__(
        self,
        service_config_to_test: ServiceConfig,
        service_type: str,
        protocol: ProtocolConfig,
        implementation_name: str,
    ):
        super().__init__(service_config_to_test, service_type, protocol,implementation_name)
    
    def is_tester(self):
        return False
    