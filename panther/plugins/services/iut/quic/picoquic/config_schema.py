from dataclasses import dataclass, field
from typing import Optional
from enum import Enum
from config.config_schema import ProtocolConfig, ImplementationType, ImplementationConfig


@dataclass
class PicoquicConfig(ImplementationConfig):
    name: str  = "picoquic" # Implementation name
    type: ImplementationType = ImplementationType.iut  # Default type for panther_ivy