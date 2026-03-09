"""Plugin configuration models."""

from typing import Optional

from pydantic import Field

from ..base import BaseConfig


class ProtocolPluginConfig(BaseConfig):
    """Base configuration for protocol plugins."""

    enabled: bool = Field(True, description="Whether the plugin is enabled")
    version: Optional[str] = Field(None, description="Plugin version")
    priority: int = Field(
        100,
        ge=0,
        le=1000,
        description="Plugin execution priority",
        examples=[0, 50, 100, 200],
    )
