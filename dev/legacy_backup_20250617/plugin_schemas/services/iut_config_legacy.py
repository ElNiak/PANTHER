from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional


@dataclass
class Parameter:
    value: Optional[str] = None
    description: Optional[str] = None


@dataclass
class VersionBase:
    version: str
    commit: str
    dependencies: List[Dict[str, str]]


# Implementation Configuration
# IUT: Implementation Under Test
# Tester: Implementation used for testing
class ImplementationType(str, Enum):
    """Types of implementations in the system."""

    IUT = "iut"  # Implementation Under Test
    TESTERS = "testers"  # Implementation used for testing


@dataclass
class ImplementationConfig:
    """
    ImplementationConfig class represents the configuration for an implementation.

    Attributes:
        name (str): The name of the implementation (e.g., picoquic, panther_ivy).
        type (ImplementationType): The type of implementation, must be either "iut" or "testers".
        shadow_compatible (bool): Indicates if the implementation is compatible with shadow. This field must be ignored by OmegaConf.
        gperf_compatible (bool): Indicates if the implementation is compatible with gperf.
    """

    name: str  # Implementation name (e.g., picoquic, panther_ivy)
    type: ImplementationType = (
        ImplementationType.IUT
    )  # Must be either "iut" or "testers"
    shadow_compatible: bool = field(
        default=False
    )  # This field must be ignored by OmegaConf
    gperf_compatible: bool = field(default=False)
