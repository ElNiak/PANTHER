import logging
import os
from pathlib import Path
from typing import Dict, List, Optional

from omegaconf import OmegaConf
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

    version: str = Field(default="")
    commit: str = Field(default="")
    dependencies: List[Dict[str, str]] = Field(default_factory=list)
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

    name: str = Field(default="quiche", description="Implementation name")
    type: ImplementationType = Field(
        default=ImplementationType.IUT, description="Implementation type"
    )
    # Version configuration loaded dynamically from YAML files
    version: QuicheVersion = Field(
        default_factory=lambda: QuicheConfig.load_versions_from_files(),
        description="Version configuration",
    )

    @staticmethod
    def load_versions_from_files(
        version_configs_dir: str = f"{Path(os.path.dirname(__file__))}/version_configs/",
    ) -> QuicheVersion:
        """Load version configurations dynamically from YAML files."""
        logging.debug(f"Loading Quiche versions from {version_configs_dir}")
        for version_file in os.listdir(version_configs_dir):
            if version_file.endswith(".yaml"):
                version_path = os.path.join(version_configs_dir, version_file)
                raw_version_config = OmegaConf.load(version_path)
                logging.debug(f"Loaded raw Quiche version config: {raw_version_config}")
                # Create default instance and merge with loaded config
                default_version = QuicheVersion()
                try:
                    # Pydantic v2
                    default_dict = default_version.model_dump()
                except AttributeError:
                    # Pydantic v1
                    default_dict = default_version.dict()

                merged_config = OmegaConf.merge(default_dict, raw_version_config)
                version_dict = OmegaConf.to_container(merged_config)
                version_config = QuicheVersion(**version_dict)
                logging.debug(f"Loaded Quiche version {version_config}")
                return version_config
