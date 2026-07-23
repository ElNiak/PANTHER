"""FRRouting BGP plugin configuration schema."""

from typing import ClassVar, Optional

from pydantic import Field

from panther.config.core.models.service import (
    ImplementationConfig,
    ProtocolConfig,
    ServiceConfig,
    VersionBase,
)


class FrrBgpVersion(VersionBase):
    """Version information for FRRouting BGP implementation."""

    server: Optional[dict] = Field(default_factory=dict)
    client: Optional[dict] = Field(default_factory=dict)


class FrrBgpConfig(ServiceConfig):
    """FRRouting BGP implementation configuration.

    Uses the official FRRouting Docker image to run bgpd.

    Example YAML::

        services:
          bgp_router:
            implementation:
              name: frr_bgp
              type: iut
            protocol:
              name: bgp
              role: server
    """

    VERSION_CLASS: ClassVar[Optional[type]] = FrrBgpVersion

    implementation: ImplementationConfig = Field(
        default_factory=lambda: ImplementationConfig(name="frr_bgp", type="iut"),
        description="Implementation configuration",
    )
    protocol: ProtocolConfig = Field(
        default_factory=lambda: ProtocolConfig(name="bgp", role="server"),
        description="Protocol configuration",
    )
    version: FrrBgpVersion = Field(
        default_factory=lambda: FrrBgpConfig.load_version(),
        description="Version configuration",
    )
