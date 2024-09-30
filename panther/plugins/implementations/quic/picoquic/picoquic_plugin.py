from core.interfaces.protocol_interface import IProtocolPlugin
from plugins.implementations.quic.picoquic.service_manager import PicoquicServiceManager

class PicoquicPlugin(IProtocolPlugin):
    def __init__(self):
        self.service_managers = {}
    
    def get_service_manager(self, implementation_name: str):
        if implementation_name not in self.service_managers:
            # Dynamically import the service manager
            if implementation_name == "picoquic":
                from .service_manager import PicoquicServiceManager
                self.service_managers[implementation_name] = PicoquicServiceManager()
            else:
                raise ValueError(f"Unknown implementation '{implementation_name}' for QUIC protocol.")
        return self.service_managers[implementation_name]
