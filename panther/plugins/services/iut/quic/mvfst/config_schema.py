"""Mvfst QUIC plugin configuration schema."""

from typing import ClassVar, Optional

from pydantic import Field

from panther.config.core.models.service import (
    ImplementationConfig,
    ProtocolConfig,
    ServiceConfig,
    VersionBase,
)


class MvfstVersion(VersionBase):
    """Version information for MVFST."""

    client: Optional[dict] = Field(default_factory=dict)
    server: Optional[dict] = Field(default_factory=dict)


class MvfstConfig(ServiceConfig):
    """MVFST QUIC implementation configuration.

    MVFST (pronounced "move fast") is Meta's C++ implementation of the
    QUIC transport protocol.

    Language: C++ | Source: https://github.com/facebook/mvfst
    Build time: ~15 min | Docker image: ~500MB

    Example YAML::

        services:
          server:
            implementation:
              name: mvfst
              type: iut
            protocol:
              name: quic
              version: rfc9000
              role: server
    """

    VERSION_CLASS: ClassVar[Optional[type]] = MvfstVersion

    implementation: ImplementationConfig = Field(
        default_factory=lambda: ImplementationConfig(name="mvfst", type="iut"),
        description="Implementation configuration",
    )
    protocol: ProtocolConfig = Field(
        default_factory=lambda: ProtocolConfig(name="quic", role="server"),
        description="Protocol configuration",
    )
    version: MvfstVersion = Field(
        default_factory=lambda: MvfstConfig.load_version(),
        description="Version configuration",
    )
