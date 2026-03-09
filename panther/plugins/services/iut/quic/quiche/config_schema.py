"""Quiche QUIC plugin configuration schema."""

from typing import Optional

from pydantic import Field

from panther.config.core.models import (
    ImplementationType,
    ServicePluginConfig,
    VersionBase,
)


class QuicheVersion(VersionBase):
    """Version information for Quiche.

    Extends VersionBase with optional client/server role-specific
    configuration loaded from YAML version files.

    Inherited from VersionBase:
        version: Git tag or release version string.
        commit: Git commit hash for reproducible builds.
        dependencies: Build-time dependency specifications.
    """

    client: Optional[dict] = Field(default_factory=dict)
    server: Optional[dict] = Field(default_factory=dict)


class QuicheConfig(ServicePluginConfig):
    """Quiche QUIC implementation configuration.

    Quiche is Cloudflare's Rust implementation of QUIC and HTTP/3. It
    provides a C API for FFI integration and is designed for production
    use at scale. Quiche powers Cloudflare's edge network and is built
    with BoringSSL for TLS 1.3 support.

    Language: Rust (with C FFI) | Source: https://github.com/cloudflare/quiche
    Build time: ~10 min | Docker image: ~300MB

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
              name: quiche
              type: iut
            protocol:
              name: quic
              version: rfc9000
              role: server
    """

    VERSION_CLASS = QuicheVersion

    name: str = Field(default="quiche", description="Implementation name")
    type: ImplementationType = Field(
        default=ImplementationType.IUT, description="Implementation type"
    )
    # Version configuration loaded dynamically from YAML files
    version: QuicheVersion = Field(
        default_factory=lambda: QuicheConfig.load_version(),
        description="Version configuration",
    )
