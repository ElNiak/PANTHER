from dataclasses import dataclass
from enum import Enum


ImplementationType = Enum("ImplementationType", ["iut", "testers"])
@dataclass
class ImplementationConfig:
    name: str  # Implementation name (e.g., picoquic, panther_ivy)
    type: ImplementationType = ImplementationType.iut  # Must be either "iut" or "testers"
  