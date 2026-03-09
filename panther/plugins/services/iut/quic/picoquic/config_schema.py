"""Picoquic QUIC plugin configuration schema."""

from typing import Optional

from pydantic import Field

from panther.config.core.models.plugin import ServicePluginConfig
from panther.config.core.models.service import ImplementationType, VersionBase


class PicoquicVersion(VersionBase):
    """Version information for Picoquic.

    Extends VersionBase with optional client/server role-specific
    configuration loaded from YAML version files.

    Inherited from VersionBase:
        version: Git tag or release version string.
        commit: Git commit hash for reproducible builds.
        dependencies: Build-time dependency specifications.
    """

    # Additional fields beyond VersionBase
    client: Optional[dict] = Field(
        default_factory=dict, description="Client-specific configuration"
    )
    server: Optional[dict] = Field(
        default_factory=dict, description="Server-specific configuration"
    )


class PicoquicConfig(ServicePluginConfig):
    """Picoquic QUIC implementation configuration.

    Picoquic is a minimal, standards-focused C implementation of QUIC
    (RFC 9000) developed by private-octopus. It supports both client and
    server roles with configurable protocol versions, and is known for
    its lightweight footprint and strict standards compliance. Picoquic
    also supports protocol version negotiation and multipath QUIC.

    Language: C | Source: https://github.com/private-octopus/picoquic
    Build time: ~5 min | Docker image: ~200MB

    Inherited from ServicePluginConfig / BasePluginConfig:
        enabled (bool): Whether the plugin is enabled. Default: True.
        version (Optional[str]): Plugin version. Default: None.
        priority (int): Plugin execution priority. Default: 100.
        docker_image (Optional[str]): Docker image name. Default: None.
        build_from_source (bool): Build from source. Default: True.
        source_repository (Optional[str]): Source repository URL.

    Example YAML::

        services:
          server:
            implementation:
              name: picoquic
              type: iut
            protocol:
              name: quic
              version: rfc9000
              role: server
    """

    VERSION_CLASS = PicoquicVersion

    name: str = Field(default="picoquic", description="Implementation name")
    type: ImplementationType = Field(
        default_factory=lambda: ImplementationType.IUT,
        description="Implementation type",
    )
    version: PicoquicVersion = Field(
        default_factory=lambda: PicoquicConfig.load_version(),
        description="Version configuration",
    )

    # QUIC-specific parameters
    alpn: Optional[str] = Field(default=None, description="ALPN protocol identifier")
    initial_rtt: Optional[int] = Field(
        default=None, description="Initial RTT in milliseconds"
    )
    max_stream_data: Optional[int] = Field(
        default=None, description="Maximum stream data in bytes"
    )
    max_data: Optional[int] = Field(
        default=None, description="Maximum connection data in bytes"
    )
