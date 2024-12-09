from dataclasses import dataclass
from typing import Optional

from config.config_experiment_schema import ProtocolConfig


@dataclass
class MiniPConfig(ProtocolConfig):
    name: str = "minip"
    version: str  # Protocol version (e.g., rfc9000)
    role: str  # Role (server or client)
    target: Optional[str] = None  # Optional target service name