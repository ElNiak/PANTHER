"""Picoquic Shadow QUIC plugin configuration schema."""

from typing import Optional

from pydantic import Field

from panther.config.core.models import (
    ImplementationType,
    ServicePluginConfig,
    VersionBase,
)


class PicoquicShadowVersion(VersionBase):
    """Version information for Picoquic Shadow.

    Extends VersionBase with optional client/server role-specific
    configuration loaded from YAML version files.

    Inherited from VersionBase:
        version: Git tag or release version string.
        commit: Git commit hash for reproducible builds.
        dependencies: Build-time dependency specifications.
    """

    client: Optional[dict] = Field(default_factory=dict)
    server: Optional[dict] = Field(default_factory=dict)


class PicoquicShadowConfig(ServicePluginConfig):
    """Picoquic Shadow network simulator variant configuration.

    This is a Shadow-compatible build of Picoquic, the minimal C QUIC
    implementation by private-octopus. It is compiled with modifications
    that allow it to run inside the Shadow discrete-event network
    simulator, enabling reproducible, large-scale network experiments
    with controlled topology and timing.

    Unlike standard Picoquic, this variant sets ``shadow_compatible=True``
    and may use a different build configuration optimized for
    deterministic execution under Shadow.

    Language: C (Shadow-compatible) |
    Source: https://github.com/private-octopus/picoquic
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
              name: picoquic_shadow
              type: iut
            protocol:
              name: quic
              version: rfc9000
              role: server
        network_environment:
          type: shadow_ns
    """

    VERSION_CLASS = PicoquicShadowVersion

    name: str = Field(default="picoquic_shadow", description="Implementation name")
    type: ImplementationType = Field(
        default=ImplementationType.IUT, description="Implementation type"
    )
    shadow_compatible: bool = Field(
        default=True, description="Whether compatible with Shadow network simulator"
    )

    # Version configuration loaded dynamically from YAML files
    version: PicoquicShadowVersion = Field(
        default_factory=lambda: PicoquicShadowConfig.load_version(),
        description="Version configuration",
    )
