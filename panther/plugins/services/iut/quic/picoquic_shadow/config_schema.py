"""Picoquic Shadow QUIC plugin configuration schema."""

from typing import ClassVar, Optional

from pydantic import Field

from panther.config.core.models.service import (
    ImplementationConfig,
    ProtocolConfig,
    ServiceConfig,
    VersionBase,
)


class PicoquicShadowVersion(VersionBase):
    """Version information for Picoquic Shadow."""

    client: Optional[dict] = Field(default_factory=dict)
    server: Optional[dict] = Field(default_factory=dict)


class PicoquicShadowConfig(ServiceConfig):
    """Picoquic Shadow network simulator variant configuration.

    This is a Shadow-compatible build of Picoquic.

    Language: C (Shadow-compatible) |
    Source: https://github.com/private-octopus/picoquic
    Build time: ~5 min | Docker image: ~200MB

    Example YAML::

        services:
          server:
            implementation:
              name: picoquic_shadow
              type: iut
            protocol:
              name: quic
              version: rfc9000
              role: server
        network_environment:
          type: shadow_ns
    """

    VERSION_CLASS: ClassVar[Optional[type]] = PicoquicShadowVersion

    implementation: ImplementationConfig = Field(
        default_factory=lambda: ImplementationConfig(
            name="picoquic_shadow", type="iut", shadow_compatible=True
        ),
        description="Implementation configuration",
    )
    protocol: ProtocolConfig = Field(
        default_factory=lambda: ProtocolConfig(name="quic", role="server"),
        description="Protocol configuration",
    )
    version: PicoquicShadowVersion = Field(
        default_factory=lambda: PicoquicShadowConfig.load_version(),
        description="Version configuration",
    )
