from enum import Enum
from omegaconf import MISSING
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Literal, Type

from plugins.protocols.config_schema import ProtocolConfig
from plugins.services.iut.config_schema import ImplementationConfig


# Service Configuration
@dataclass
class ServiceConfig:
    name: str # Service name
    implementation: ImplementationConfig = field(default_factory=lambda: ImplementationConfig(name="implem_name"))  # Implementation details
    protocol: ProtocolConfig             = field(default_factory=ProtocolConfig)  # Protocol configuration
    ports: List[str]                     = field(default_factory=list)  # List of ports
    generate_new_certificates: Optional[bool] = False
    