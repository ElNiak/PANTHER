from typing import Dict, Optional

from pydantic import Field

from panther.config.core.models.plugin import NetworkEnvironmentPluginConfig


class LocalhostSingleContainerConfig(NetworkEnvironmentPluginConfig):
    """Configuration for localhost single container network environment."""
    
    type: str = Field(
        default="localhost_single_container",
        description="Network environment type"
    )
    version: str = Field(
        default="3.8",
        description="Docker version compatibility"
    )
    service_prefix: Optional[str] = Field(
        default=None,
        description="Optional prefix for service names"
    )
    environment: Dict[str, str] = Field(
        default_factory=dict,
        description="Environment variables"
    )
