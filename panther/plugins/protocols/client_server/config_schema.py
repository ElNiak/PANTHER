from dataclasses import dataclass, field
from typing import List, Dict, Optional, Type

from plugins.protocols.config_schema import ProtocolBase

# Base protocol configuration
@dataclass
class ClientServerProtocol(ProtocolBase):
    client: Optional[str] = None
    server: Optional[str] = None
