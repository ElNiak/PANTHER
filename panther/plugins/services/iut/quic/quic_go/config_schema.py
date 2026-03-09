"""quic-go QUIC plugin configuration schema."""

from typing import Optional

from pydantic import Field

from panther.config.core.models import (
    ImplementationType,
    ServicePluginConfig,
    VersionBase,
)


class QuicGoVersion(VersionBase):
    """Version information for quic-go.

    Extends VersionBase with optional client/server role-specific
    configuration loaded from YAML version files.

    Inherited from VersionBase:
        version: Git tag or release version string.
        commit: Git commit hash for reproducible builds.
        dependencies: Build-time dependency specifications.
    """

    client: Optional[dict] = Field(
        default_factory=dict, description="Client configuration"
    )
    server: Optional[dict] = Field(
        default_factory=dict, description="Server configuration"
    )


class QuicGoConfig(ServicePluginConfig):
    """quic-go QUIC implementation configuration.

    quic-go is a pure Go implementation of the QUIC protocol. It provides
    a complete QUIC stack with HTTP/3 support, leveraging Go's built-in
    concurrency primitives for efficient connection handling. quic-go is
    widely used in the Go ecosystem and powers projects like Caddy and
    Syncthing.

    Language: Go | Source: https://github.com/quic-go/quic-go
    Build time: ~3 min | Docker image: ~200MB

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
              name: quic-go
              type: iut
            protocol:
              name: quic
              version: rfc9000
              role: server
    """

    VERSION_CLASS = QuicGoVersion

    name: str = Field(default="quic-go", description="Implementation name")
    type: ImplementationType = Field(
        default=ImplementationType.IUT, description="Implementation type"
    )

    # Version configuration loaded dynamically from YAML files
    version: QuicGoVersion = Field(
        default_factory=lambda: QuicGoConfig.load_version(),
        description="Version configuration",
    )
