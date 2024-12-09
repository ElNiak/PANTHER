from dataclasses import dataclass
from enum import Enum
from typing import Dict, Type
from omegaconf import MISSING

# Implementation Configuration
# IUT: Implementation Under Test
# Tester: Implementation used for testing
ImplementationType = Enum("ImplementationType", ["iut", "testers"])
@dataclass
class ImplementationConfig:
    name: str  # Implementation name (e.g., picoquic, panther_ivy)
    type: ImplementationType = ImplementationType.iut  # Must be either "iut" or "testers"
  
@dataclass
class ProtocolConfig:
    name : str = MISSING
    
def protocol_factory(protocol_data: Dict) -> ProtocolConfig:
    """
    Factory function to dynamically resolve and instantiate the correct ProtocolConfig subclass.

    :param protocol_data: A dictionary containing the protocol configuration.
    :return: An instance of the appropriate ProtocolConfig subclass.
    """
    from plugins.services.iut.quic.config_schema import QuicConfig
    # Map protocol names to their corresponding classes
    PROTOCOL_CLASS_MAP: Dict[str, Type[ProtocolConfig]] = {
        "quic": QuicConfig,
    }
    protocol_name = protocol_data.get("name").lower()
    protocol_class = PROTOCOL_CLASS_MAP.get(protocol_name)
    if protocol_class is None:
        raise ValueError(f"Unsupported protocol: {protocol_name}")
    return protocol_class(**protocol_data)
