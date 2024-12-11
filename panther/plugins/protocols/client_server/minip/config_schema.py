from dataclasses import dataclass
from typing import Optional
from enum import Enum

from plugins.protocols.config_schema import ProtocolConfig, RoleEnum, ProtocolType

# TODO init that directly from folder ?
VersionEnum = Enum("VersionEnum", ["random","functional","vulnerable","flaky","fail"])
@dataclass
class MinipConfig(ProtocolConfig):
    name: str = "MiniP"
    version: VersionEnum = VersionEnum.random # Protocol version (e.g., rfc9000)
    role: RoleEnum = RoleEnum.server # Role (server or client)
    target: Optional[str] = None  # Optional target service name
    protocol_type: ProtocolType = ProtocolType.client_server