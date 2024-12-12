from dataclasses import dataclass
from enum import Enum


# Base protocol configuration
@dataclass
class ProtocolBase:
    name: str

    def validate(self):
        """Common validation logic for protocols."""
        pass


ProtocolType = Enum("ProtocolType", ["peer_to_peer", "client_server"])
RoleEnum = Enum("RoleEnum", ["server", "client", "peer"])


@dataclass
class ProtocolConfig:
    name: str | None = None
    version: str | None = None
    role: str | None = None
    target: str | None = None
    protocol_type: ProtocolType = ProtocolType.client_server
