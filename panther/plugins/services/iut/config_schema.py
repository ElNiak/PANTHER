from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional

@dataclass
class Parameter:
    value: Optional[str] = None
    description: Optional[str] = None
    
@dataclass
class VersionBase:
    commit: str
    dependencies: List[Dict[str, str]]

    def validate(self):
        """Common version validation logic."""
        pass

# Implementation Configuration
# IUT: Implementation Under Test
# Tester: Implementation used for testing
ImplementationType = Enum("ImplementationType", ["iut", "testers"])
@dataclass
class ImplementationConfig:
    name: str  # Implementation name (e.g., picoquic, panther_ivy)
    type: ImplementationType = ImplementationType.iut  # Must be either "iut" or "testers"
    shadow_compatible: bool = field(default=False)  # This field must be ignored by OmegaConf
