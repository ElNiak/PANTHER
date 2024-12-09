# panther_core/plugins/minip/plugin.py

from panther.plugins.protocols.protocol_interface import IProtocolManager
class MinipProtocolPlugin(IProtocolManager):
    def __init__(self,type: str):
        super().__init__(type)
        self.available_roles    = ["client", "server"]
        self.supported_versions = ["1"]
    
