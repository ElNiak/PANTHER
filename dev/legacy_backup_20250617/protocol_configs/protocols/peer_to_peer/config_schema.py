from dataclasses import dataclass, field
from typing import List

from panther.plugins.protocols.config_schema import ProtocolBase


@dataclass
class PeerToPeerProtocol(ProtocolBase):
    peers: List[str] = field(default_factory=list)
