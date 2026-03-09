"""Quiche QUIC plugin configuration schema."""

from typing import ClassVar, Optional

from pydantic import Field

from panther.config.core.models.service import (
    ImplementationConfig,
    ProtocolConfig,
    ServiceConfig,
    VersionBase,
)


class QuicheVersion(VersionBase):
    """Version information for Quiche."""

    client: Optional[dict] = Field(default_factory=dict)
    server: Optional[dict] = Field(default_factory=dict)


class QuicheConfig(ServiceConfig):
    """Quiche QUIC implementation configuration.

    Quiche is Cloudflare's Rust implementation of QUIC and HTTP/3.

    Language: Rust (with C FFI) | Source: https://github.com/cloudflare/quiche
    Build time: ~10 min | Docker image: ~300MB

    Example YAML::

        services:
          server:
            implementation:
              name: quiche
              type: iut
            protocol:
              name: quic
              version: rfc9000
              role: server
    """

    VERSION_CLASS: ClassVar[Optional[type]] = QuicheVersion

    implementation: ImplementationConfig = Field(
        default_factory=lambda: ImplementationConfig(name="quiche", type="iut"),
        description="Implementation configuration",
    )
    protocol: ProtocolConfig = Field(
        default_factory=lambda: ProtocolConfig(name="quic", role="server"),
        description="Protocol configuration",
    )
    version: QuicheVersion = Field(
        default_factory=lambda: QuicheConfig.load_version(),
        description="Version configuration",
    )
