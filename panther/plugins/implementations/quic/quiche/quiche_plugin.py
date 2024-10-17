from plugins.implementations.protocol_interface import IProtocolPlugin
from plugins.implementations.quic.quiche.service_manager import QuicheServiceManager

class QuichePlugin(IProtocolPlugin):
    def __init__(self):
        self.service_managers = {}
    
    def get_service_manager(self, implementation_name: str):
        if implementation_name not in self.service_managers:
            # Dynamically import the service manager
            if implementation_name == "quiche":
                from .service_manager import QuicheServiceManager
                self.service_managers[implementation_name] = QuicheServiceManager()
            else:
                raise ValueError(f"Unknown implementation '{implementation_name}' for QUIC protocol.")
        return self.service_managers[implementation_name]
