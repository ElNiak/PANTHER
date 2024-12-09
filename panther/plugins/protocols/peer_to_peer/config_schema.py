from dataclasses import dataclass, field
from typing import List, Dict, Optional, Type

from plugins.protocols.config_schema import ProtocolBase

@dataclass
class PeerToPeerProtocol(ProtocolBase):
    peers: List[str] = field(default_factory=list)