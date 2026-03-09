"""Quant QUIC plugin configuration schema."""

from typing import Dict, List, Optional

from pydantic import Field

from panther.config.core.models import (
    ImplementationType,
    ServicePluginConfig,
    VersionBase,
)


class QuantVersion(VersionBase):
    """Version information for Quant.

    Extends VersionBase with optional client/server role-specific
    configuration loaded from YAML version files.

    Inherited from VersionBase:
        version: Git tag or release version string.
        commit: Git commit hash for reproducible builds.
        dependencies: Build-time dependency specifications.
    """

    version: str = Field(default="", description="Version string")
    commit: str = Field(default="", description="Git commit hash")
    dependencies: List[Dict[str, str]] = Field(
        default_factory=list, description="Dependencies list"
    )
    client: Optional[dict] = Field(
        default_factory=dict, description="Client configuration"
    )
    server: Optional[dict] = Field(
        default_factory=dict, description="Server configuration"
    )


class QuantConfig(ServicePluginConfig):
    """Quant QUIC implementation configuration.

    Quant is a minimal, embeddable C implementation of QUIC developed by
    NTAP (NetApp Advanced Technology Group). It focuses on a small code
    footprint and low resource usage, targeting embedded systems and
    constrained environments. Quant uses the warpcore userspace UDP/IP
    stack for high-performance I/O.

    Language: C | Source: https://github.com/NTAP/quant
    Build time: ~5 min | Docker image: ~150MB

    Inherited from ServicePluginConfig / BasePluginConfig:
        enabled (bool): Whether the plugin is enabled. Default: True.
        version (Optional[str]): Plugin version. Default: None.
        priority (int): Plugin execution priority. Default: 100.
        docker_image (Optional[str]): Docker image name. Default: None.
        build_from_source (bool): Build from source. Default: True.
        source_repository (Optional[str]): Source repository URL.

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

    VERSION_CLASS = QuantVersion

    name: str = Field(default="quant", description="Implementation name")
    type: ImplementationType = Field(
        default=ImplementationType.IUT, description="Implementation type"
    )

    # Version configuration loaded dynamically from YAML files
    version: QuantVersion = Field(
        default_factory=lambda: QuantConfig.load_version(),
        description="Version configuration",
    )
