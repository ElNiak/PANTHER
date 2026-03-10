"""quic-go QUIC plugin configuration schema."""

from typing import ClassVar, Optional

from pydantic import Field

from panther.config.core.models.service import (
    ImplementationConfig,
    ProtocolConfig,
    ServiceConfig,
    VersionBase,
)


class QuicGoVersion(VersionBase):
    """Version information for quic-go."""

    client: Optional[dict] = Field(
        default_factory=dict, description="Client configuration"
    )
    server: Optional[dict] = Field(
        default_factory=dict, description="Server configuration"
    )


class QuicGoConfig(ServiceConfig):
    """quic-go QUIC implementation configuration.

    quic-go is a pure Go implementation of the QUIC protocol.

    Language: Go | Source: https://github.com/quic-go/quic-go
    Build time: ~3 min | Docker image: ~200MB

    Example YAML::

        services:
          server:
            implementation:
              name: quic-go
              type: iut
            protocol:
              name: quic
              version: rfc9000
              role: server
    """

    VERSION_CLASS: ClassVar[Optional[type]] = QuicGoVersion

    implementation: ImplementationConfig = Field(
        default_factory=lambda: ImplementationConfig(name="quic-go", type="iut"),
        description="Implementation configuration",
    )
    protocol: ProtocolConfig = Field(
        default_factory=lambda: ProtocolConfig(name="quic", role="server"),
        description="Protocol configuration",
    )
    version: QuicGoVersion = Field(
        default_factory=lambda: QuicGoConfig.load_version(),
        description="Version configuration",
    )
