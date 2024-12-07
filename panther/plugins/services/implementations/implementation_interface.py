from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from plugins.services.services_interface import IServiceManager
from plugins.plugin_loader import PluginLoader


# TODO create a new module "services" and move this interface there with 'implementations' and 'testers' interfaces
class IImplementationManager(IServiceManager):
    def __init__(self):
        pass
    
    def is_tester(self):
        return False
    