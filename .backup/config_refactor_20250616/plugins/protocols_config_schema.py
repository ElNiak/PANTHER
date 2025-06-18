from dataclasses import dataclass
from enum import Enum
from typing import Optional


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
    name: Optional[str] = None
    version: Optional[str] = None
    role: Optional[str] = None
    target: Optional[str] = None
    protocol_type: ProtocolType = ProtocolType.client_server

    @classmethod
    def get_default_server_port(cls) -> Optional[int]:
        """Get the default server port for this protocol.

        Override in protocol-specific configurations.
        """
        return None

    @classmethod
    def get_default_client_port(cls) -> Optional[int]:
        """Get the default client port for this protocol.

        Override in protocol-specific configurations.
        """
        return None

    def requires_server_port(self) -> bool:
        """Check if this protocol configuration requires a server port."""
        return self.role and self.role.lower() == "server"

    def get_default_port_mapping(self) -> Optional[str]:
        """Get default port mapping for this protocol configuration."""
        if self.requires_server_port():
            port = self.get_default_server_port()
            if port:
                return f"{port}:{port}"
        return None
