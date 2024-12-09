from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional, Type

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
    protocol_type : ProtocolType = ProtocolType.client_server
