from dataclasses import dataclass, field
from enum import Enum


@dataclass
class Parameter:
    value: str | None = None
    description: str | None = None


@dataclass
class VersionBase:
    version: str
    commit: str
    dependencies: list[dict[str, str]]


# Implementation Configuration
# IUT: Implementation Under Test
# Tester: Implementation used for testing
ImplementationType = Enum("ImplementationType", ["iut", "testers"])


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
        ImplementationType.iut
    )  # Must be either "iut" or "testers"
    shadow_compatible: bool = field(
        default=False
    )  # This field must be ignored by OmegaConf
    gperf_compatible: bool = field(default=False)
