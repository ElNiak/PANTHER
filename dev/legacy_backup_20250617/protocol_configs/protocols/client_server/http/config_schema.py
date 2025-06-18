from dataclasses import dataclass
from enum import Enum
from typing import Optional

from panther.plugins.protocols.config_schema import (
    ProtocolConfig,
    ProtocolType,
    RoleEnum,
)

# TODO init that directly from folder ?
VersionEnum = Enum("VersionEnum", ["0.9", "2", "3"])


@dataclass
class HttpConfig(ProtocolConfig):
    """
    HttpConfig is a configuration class for the HTTP protocol.

    Attributes:
        name (str): The name of the protocol, default is "HTTP".
        version (VersionEnum): The protocol version, default is VersionEnum.random.
        role (RoleEnum): The role in the protocol, either server or client, default is RoleEnum.server.
        target (Optional[str]): An optional target service name, default is None.
        protocol_type (ProtocolType): The type of protocol, default is ProtocolType.client_server.
    """

    name: str = "HTTP"
    version: VersionEnum = VersionEnum.random  # Protocol version (e.g., rfc9000)
    role: RoleEnum = RoleEnum.server  # Role (server or client)
    target: Optional[str] = None  # Optional target service name
    protocol_type: ProtocolType = ProtocolType.client_server
