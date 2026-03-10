"""Ping-pong MiniP plugin configuration schema."""

from typing import ClassVar, Optional

from pydantic import Field

from panther.config.core.models.service import (
    ImplementationConfig,
    ProtocolConfig,
    ServiceConfig,
    VersionBase,
)


class PingPongVersion(VersionBase):
    """Version information for Ping-Pong MinIP implementation."""

    client: Optional[dict] = Field(default_factory=dict)
    server: Optional[dict] = Field(default_factory=dict)


class PingPongConfig(ServiceConfig):
    """Ping-Pong MinIP implementation configuration.

    Simple client-server protocol for testing basic network communication
    patterns.

    Language: C | Build time: <1 min | Docker image: ~100MB

    Example YAML::

        services:
          server:
            implementation:
              name: ping-pong
              type: iut
            protocol:
              name: minip
              role: server
    """

    VERSION_CLASS: ClassVar[Optional[type]] = PingPongVersion

    implementation: ImplementationConfig = Field(
        default_factory=lambda: ImplementationConfig(
            name="ping-pong", type="iut", shadow_compatible=True
        ),
        description="Implementation configuration",
    )
    protocol: ProtocolConfig = Field(
        default_factory=lambda: ProtocolConfig(name="minip", role="server"),
        description="Protocol configuration",
    )
    version: PingPongVersion = Field(
        default_factory=lambda: PingPongConfig.load_version(),
        description="Version configuration",
    )
