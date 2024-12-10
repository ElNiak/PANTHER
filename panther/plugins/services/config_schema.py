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
    timeout: int = field(default=100)  # Timeout for the service
    implementation: ImplementationConfig = field(default_factory=lambda: ImplementationConfig(name="implem_name"))  # Implementation details
    protocol: ProtocolConfig             = field(default_factory=ProtocolConfig)  # Protocol configuration
    ports: List[str]                     = field(default_factory=list)  # List of ports
    generate_new_certificates: bool = field(default=False)  # Flag to generate new certificates
    volumes: List[str] = field(default_factory=list)
    directories_to_start: List[str] = field(default_factory=list)
    