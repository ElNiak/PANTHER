"""Plugin configuration models."""

from typing import Optional

from pydantic import Field

from ..base import BaseConfig


class ProtocolPluginConfig(BaseConfig):
    """Base configuration for protocol plugins."""

    enabled: bool = Field(True, description="Whether the plugin is enabled")
    version: Optional[str] = Field(None, description="Plugin version")
    priority: int = Field(100, description="Plugin execution priority")
    protocol_version: str = Field(..., description="Protocol version")
    default_port: int = Field(..., description="Default port number")
    supports_tls: bool = Field(True, description="Whether protocol supports TLS")

    def get_plugin_type(self) -> str:
        """Return protocol plugin type."""
        return "protocol"
