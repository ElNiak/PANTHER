from dataclasses import dataclass, field
from typing import List, Dict, Any


@dataclass
class QUICManagedOptions:
    """
    Managed options for the QUIC protocol.
    This includes all possible options and their default values.
    """

    initial_versions: List[str] = field(default_factory=lambda: ["1.0", "1.1"])
    alpn_options: List[str] = field(
        default_factory=lambda: ["h3-23", "h3-24", "h3-29", "h3-30"]
    )
    congestion_controls: List[str] = field(
        default_factory=lambda: ["cubic", "bbr", "reno"]
    )
    enable_tls: bool = True
    max_packet_size: int = 1350
    additional_options: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MiniPManagedOptions:
    """
    Managed options for the MiniP protocol.
    This includes all possible options and their default values.
    """

    pass
