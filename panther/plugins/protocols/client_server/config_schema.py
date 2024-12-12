from dataclasses import dataclass

from panther.plugins.protocols.config_schema import ProtocolBase


# Base protocol configuration
@dataclass
class ClientServerProtocol(ProtocolBase):
    client: str | None = None
    server: str | None = None
