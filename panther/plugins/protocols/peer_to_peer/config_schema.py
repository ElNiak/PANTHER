from dataclasses import dataclass, field

from panther.plugins.protocols.config_schema import ProtocolBase


@dataclass
class PeerToPeerProtocol(ProtocolBase):
    peers: list[str] = field(default_factory=list)
