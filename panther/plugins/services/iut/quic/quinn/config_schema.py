"""Quinn QUIC plugin configuration schema."""

from typing import ClassVar, Optional

from pydantic import Field

from panther.config.core.models.service import (
    ImplementationConfig,
    ProtocolConfig,
    ServiceConfig,
    VersionBase,
)


class QuinnVersion(VersionBase):
    """Version information for Quinn."""

    client: Optional[dict] = Field(
        default_factory=dict, description="Client configuration"
    )
    server: Optional[dict] = Field(
        default_factory=dict, description="Server configuration"
    )


class QuinnConfig(ServiceConfig):
    """Quinn QUIC implementation configuration.

    Quinn is a pure Rust implementation of QUIC built on the Tokio async
    runtime.

    Language: Rust (Tokio) | Source: https://github.com/quinn-rs/quinn
    Build time: ~10 min | Docker image: ~300MB

    Example YAML::

        services:
          client:
            implementation:
              name: quinn
              type: iut
            protocol:
              name: quic
              version: rfc9000
              role: client
    """

    VERSION_CLASS: ClassVar[Optional[type]] = QuinnVersion

    implementation: ImplementationConfig = Field(
        default_factory=lambda: ImplementationConfig(name="quinn", type="iut"),
        description="Implementation configuration",
    )
    protocol: ProtocolConfig = Field(
        default_factory=lambda: ProtocolConfig(name="quic", role="server"),
        description="Protocol configuration",
    )
    version: QuinnVersion = Field(
        default_factory=lambda: QuinnConfig.load_version(),
        description="Version configuration",
    )
