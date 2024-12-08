from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from plugins.services.services_interface import IServiceManager
from plugins.plugin_loader import PluginLoader

class IImplementationManager(IServiceManager):
    def __init__(
        self,
        type: str,
        protocol: str,
        implementation_name: str,
    ):
        super().__init__(type, protocol,implementation_name)
    
    def is_tester(self):
        return False
    