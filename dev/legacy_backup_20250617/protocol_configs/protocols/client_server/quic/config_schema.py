from dataclasses import dataclass
from enum import Enum
from typing import Optional

from panther.plugins.protocols.config_schema import (
    ProtocolConfig,
    ProtocolType,
    RoleEnum,
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
        target (Optional[str]): An optional target service name, default is None.
        protocol_type (ProtocolType): The type of protocol, default is ProtocolType.client_server.
    """

    name: str = "QUIC"
    version: VersionEnum = VersionEnum.rfc9000  # Protocol version (e.g., rfc9000)
    role: RoleEnum = RoleEnum.server  # Role (server or client)
    target: Optional[str] = None  # Optional target service name
    protocol_type: ProtocolType = ProtocolType.client_server

    @classmethod
    def get_default_server_port(cls) -> int:
        """Get the default server port for QUIC protocol."""
        return 4443

    @classmethod
    def get_default_client_port(cls) -> Optional[int]:
        """Get the default client port for QUIC protocol.

        Returns None as clients typically don't need exposed ports.
        """
        return None

    def requires_server_port(self) -> bool:
        """Check if this protocol configuration requires a server port."""
        return self.role == RoleEnum.server

    def get_default_port_mapping(self) -> Optional[str]:
        """Get default port mapping for this protocol configuration."""
        if self.role == RoleEnum.server:
            port = self.get_default_server_port()
            return f"{port}:{port}"
        return None
