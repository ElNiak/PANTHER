"""Peer-to-peer protocol base class.

Intermediate base for protocols with symmetric peer topology.
"""

from abc import abstractmethod
from typing import Optional

from panther.config.core.models.service import ProtocolRole
from panther.plugins.protocols.protocol_interface import IProtocolManager


class PeerToPeerProtocolBase(IProtocolManager):
    """Base class for peer-to-peer protocol managers.

    Provides shared semantics for protocols where all parties are peers
    with equal capabilities. Peers may optionally specify targets for
    initial bootstrapping.

    Subclasses: (future) BitTorrentProtocol
    """

    VALID_ROLES = {ProtocolRole.PEER}

    @classmethod
    def get_topology_type(cls) -> str:
        """Return the protocol topology type."""
        return "peer_to_peer"

    @classmethod
    def requires_target(cls, role: ProtocolRole) -> bool:
        """Whether a peer must specify a target. Peers optionally specify targets."""
        return False

    @classmethod
    def validate_role(cls, role: ProtocolRole) -> None:
        """Validate that role is appropriate for P2P protocols.

        Raises:
            ValueError: If role is not PEER.
        """
        if role not in cls.VALID_ROLES:
            raise ValueError(
                f"Peer-to-peer protocols only support role 'peer', got '{role.value}'"
            )

    @classmethod
    @abstractmethod
    def get_default_peer_port(cls) -> int:
        """Default port for peer communication."""
        ...

    @classmethod
    def supports_bootstrap_mode(cls) -> bool:
        """Whether this protocol supports bootstrap/seed nodes."""
        return False

    @classmethod
    def get_peer_discovery_port(cls) -> Optional[int]:
        """Port for peer discovery, if separate from data port."""
        return None
