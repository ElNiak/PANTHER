from dataclasses import dataclass
from enum import Enum

from panther.plugins.protocols.config_schema import (
    ProtocolConfig,
    RoleEnum,
    ProtocolType,
)


# TODO manage versions with specificities (e.g draft27, draft27-vuln1, ...)
VersionEnum = Enum("VersionEnum", ["rfc9000", "draft29", "draft27"])


@dataclass
class QuicConfig(ProtocolConfig):
    """
    QuicConfig is a configuration class for the QUIC protocol.

    Attributes:
        name (str): The name of the protocol, default is "QUIC".
        version (VersionEnum): The version of the protocol, default is VersionEnum.rfc9000.
        role (RoleEnum): The role of the protocol, either server or client, default is RoleEnum.server.
        target (str | None): An optional target service name, default is None.
        protocol_type (ProtocolType): The type of protocol, default is ProtocolType.client_server.
    """
    name: str = "QUIC"
    version: VersionEnum = VersionEnum.rfc9000  # Protocol version (e.g., rfc9000)
    role: RoleEnum = RoleEnum.server  # Role (server or client)
    target: str | None = None  # Optional target service name
    protocol_type: ProtocolType = ProtocolType.client_server
