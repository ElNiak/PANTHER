"""Base classes for service plugin implementations."""

from .http_service_base import BaseHTTPServiceManager
from .minip_service_base import BaseMinipServiceManager
from .quic_service_base import BaseQUICServiceManager

__all__ = [
    "BaseQUICServiceManager",
    "BaseHTTPServiceManager",
    "BaseMinipServiceManager",
]
