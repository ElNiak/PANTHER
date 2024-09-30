# panther_core/plugins/minip/plugin.py

from core.interfaces.protocol_interface import IProtocolPlugin
from plugins.implementations.minip.ping_pong.service_manager import PingPongServiceManager

class QuicProtocolPlugin(IProtocolPlugin):
    def __init__(self):
        self.service_managers = {}
    
    def get_service_manager(self, implementation_name: str):
        """
        Returns an instance of the ServiceManager for the specified implementation.
        """
        if implementation_name not in self.service_managers:
            if implementation_name == "ping_pong":
                self.service_managers[implementation_name] = PingPongServiceManager()
            else:
                raise ValueError(f"Unknown implementation '{implementation_name}' for QUIC protocol.")
        return self.service_managers[implementation_name]
