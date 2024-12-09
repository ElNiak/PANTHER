from enum import Enum
from omegaconf import MISSING
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Literal, Type

from plugins.services.iut.config_schema import ImplementationConfig, ProtocolConfig


# Service Configuration
@dataclass
class ServiceConfig:
    name: str = MISSING # Service name
    implementation: ImplementationConfig = MISSING  # Implementation details
    protocol: ProtocolConfig             = MISSING  # Protocol configuration
    ports: List[str]                     = field(default_factory=list)  # List of ports
    generate_new_certificates: Optional[bool] = False
    