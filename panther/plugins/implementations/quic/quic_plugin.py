# panther_core/plugins/quic/plugin.py

from plugins.implementations.protocol_interface import IProtocolPlugin
from plugins.implementations.quic.picoquic.service_manager import PicoquicServiceManager

class QuicProtocolPlugin(IProtocolPlugin):
    def __init__(self):
        self.service_managers = {}
    
    def get_service_manager(self, implementation_name: str):
        """
        Returns an instance of the ServiceManager for the specified implementation.
        """
        if implementation_name not in self.service_managers:
            if implementation_name == "picoquic":
                self.service_managers[implementation_name] = PicoquicServiceManager()
            else:
                raise ValueError(f"Unknown implementation '{implementation_name}' for QUIC protocol.")
        return self.service_managers[implementation_name]
