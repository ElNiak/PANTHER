"""Mvfst QUIC plugin configuration schema."""

from typing import Optional

from pydantic import Field

from panther.config.core.models import (
    ImplementationType,
    ServicePluginConfig,
    VersionBase,
)


class MvfstVersion(VersionBase):
    """Version information for MVFST.

    Extends VersionBase with optional client/server role-specific
    configuration loaded from YAML version files.

    Inherited from VersionBase:
        version: Git tag or release version string.
        commit: Git commit hash for reproducible builds.
        dependencies: Build-time dependency specifications.
    """

    client: Optional[dict] = Field(default_factory=dict)
    server: Optional[dict] = Field(default_factory=dict)


class MvfstConfig(ServicePluginConfig):
    """MVFST QUIC implementation configuration.

    MVFST (pronounced "move fast") is Meta's C++ implementation of the
    QUIC transport protocol. It is used in production at Meta for mobile
    and server-side networking. Built on Folly, it features congestion
    control experimentation hooks and integration with Meta's networking
    infrastructure.

    Language: C++ | Source: https://github.com/facebook/mvfst
    Build time: ~15 min | Docker image: ~500MB

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
              name: mvfst
              type: iut
            protocol:
              name: quic
              version: rfc9000
              role: server
    """

    VERSION_CLASS = MvfstVersion

    name: str = Field(default="mvfst", description="Implementation name")
    type: ImplementationType = Field(
        default=ImplementationType.IUT, description="Implementation type"
    )
    # Version configuration loaded dynamically from YAML files
    version: MvfstVersion = Field(
        default_factory=lambda: MvfstConfig.load_version(),
        description="Version configuration",
    )
