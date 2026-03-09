"""Quant QUIC plugin configuration schema."""

from typing import ClassVar, Optional

from pydantic import Field

from panther.config.core.models.service import (
    ImplementationConfig,
    ProtocolConfig,
    ServiceConfig,
    VersionBase,
)


class QuantVersion(VersionBase):
    """Version information for Quant."""

    client: Optional[dict] = Field(
        default_factory=dict, description="Client configuration"
    )
    server: Optional[dict] = Field(
        default_factory=dict, description="Server configuration"
    )


class QuantConfig(ServiceConfig):
    """Quant QUIC implementation configuration.

    Quant is a minimal, embeddable C implementation of QUIC developed by
    NTAP (NetApp Advanced Technology Group).

    Language: C | Source: https://github.com/NTAP/quant
    Build time: ~5 min | Docker image: ~150MB

    Example YAML::

        services:
          client:
            implementation:
              name: quant
              type: iut
            protocol:
              name: quic
              version: rfc9000
              role: client
    """

    VERSION_CLASS: ClassVar[Optional[type]] = QuantVersion

    implementation: ImplementationConfig = Field(
        default_factory=lambda: ImplementationConfig(name="quant", type="iut"),
        description="Implementation configuration",
    )
    protocol: ProtocolConfig = Field(
        default_factory=lambda: ProtocolConfig(name="quic", role="server"),
        description="Protocol configuration",
    )
    version: QuantVersion = Field(
        default_factory=lambda: QuantConfig.load_version(),
        description="Version configuration",
    )
