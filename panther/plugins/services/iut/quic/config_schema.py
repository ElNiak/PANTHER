from dataclasses import dataclass
from enum import Enum
from typing import Optional

from config.config_schema import ProtocolConfig

RoleEnum = Enum("RoleEnum", ["server", "client"])
VersionEnum = Enum("VersionEnum", ["rfc9000", "draft29", "draft27"])

@dataclass
class QuicConfig(ProtocolConfig):
    name: str = "QUIC"
    version: VersionEnum = VersionEnum.rfc9000 # Protocol version (e.g., rfc9000)
    role: RoleEnum = RoleEnum.server # Role (server or client)
    target: Optional[str] = None  # Optional target service name