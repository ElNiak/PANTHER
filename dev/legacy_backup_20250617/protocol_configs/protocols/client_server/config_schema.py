from dataclasses import dataclass
from typing import Optional

from panther.plugins.protocols.config_schema import ProtocolBase


# Base protocol configuration
@dataclass
class ClientServerProtocol(ProtocolBase):
    client: Optional[str] = None
    server: Optional[str] = None
