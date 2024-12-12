from dataclasses import dataclass
from enum import Enum

from panther.plugins.protocols.config_schema import (
    ProtocolConfig,
    RoleEnum,
    ProtocolType,
)

# TODO init that directly from folder ?
VersionEnum = Enum(
    "VersionEnum", ["random", "functional", "vulnerable", "flaky", "fail"]
)


@dataclass
class MinipConfig(ProtocolConfig):
    """
    MinipConfig is a configuration class for the MiniP protocol.

    Attributes:
        name (str): The name of the protocol, default is "MiniP".
        version (VersionEnum): The protocol version, default is VersionEnum.random.
        role (RoleEnum): The role in the protocol, either server or client, default is RoleEnum.server.
        target (str | None): An optional target service name, default is None.
        protocol_type (ProtocolType): The type of protocol, default is ProtocolType.client_server.
    """
    name: str = "MiniP"
    version: VersionEnum = VersionEnum.random  # Protocol version (e.g., rfc9000)
    role: RoleEnum = RoleEnum.server  # Role (server or client)
    target: str | None = None  # Optional target service name
    protocol_type: ProtocolType = ProtocolType.client_server
