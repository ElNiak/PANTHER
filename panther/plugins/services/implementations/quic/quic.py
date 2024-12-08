# panther_core/plugins/quic/plugin.py

from plugins.services.protocol_interface import IProtocolManager

class QuicProtocolPlugin(IProtocolManager):
    def __init__(self,type: str):
        super().__init__(type)
        self.available_roles    = ["client", "server"]
        self.supported_versions = ["rfc9000", "draft29", "draft27"]