from dataclasses import dataclass, field
from typing import Optional
from enum import Enum

from plugins.services.iut.config_schema import ImplementationConfig
from plugins.services.iut.config_schema import ImplementationType


@dataclass
class PicoquicShadowConfig(ImplementationConfig):
    name: str  = "picoquic_shadow" # Implementation name
    type: ImplementationType = ImplementationType.iut  # Default type for panther_ivy