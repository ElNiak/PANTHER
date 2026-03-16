"""Client-server protocol base class.

Intermediate base for protocols with asymmetric client-server topology.
Consolidates role validation and port semantics shared by all client-server protocols.
"""

from abc import abstractmethod

from panther.config.core.models.service import ProtocolRole
from panther.plugins.protocols.protocol_interface import IProtocolManager


class ClientServerProtocolBase(IProtocolManager):
    """Base class for client-server protocol managers.

    Provides shared semantics for protocols where one party (server) listens
    and another (client) initiates connections. Subclasses must define default
    server ports; client ports default to ephemeral (0).

    Subclasses: QUICProtocol, MiniPProtocol, (future) HTTPProtocol
    """

    VALID_ROLES = {ProtocolRole.SERVER, ProtocolRole.CLIENT}

    @classmethod
    def get_topology_type(cls) -> str:
        """Return the protocol topology type."""
        return "client_server"

    @classmethod
    def requires_target(cls, role: ProtocolRole) -> bool:
        """Whether a service with this role must specify a target.

        Clients must connect to a server target.
        Servers listen and do not need a target.
        """
        return role == ProtocolRole.CLIENT

    @classmethod
    def validate_role(cls, role: ProtocolRole) -> None:
        """Validate that role is appropriate for client-server protocols.

        Raises:
            ValueError: If role is not SERVER or CLIENT.
        """
        if role not in cls.VALID_ROLES:
            raise ValueError(
                f"Client-server protocols only support roles {[r.value for r in cls.VALID_ROLES]}, got '{role.value}'"
            )

    @classmethod
    @abstractmethod
    def get_default_server_port(cls) -> int:
        """Default listening port for the server side."""
        ...

    @classmethod
    def get_default_client_port(cls) -> int:
        """Default port for the client side (ephemeral by default)."""
        return 0
