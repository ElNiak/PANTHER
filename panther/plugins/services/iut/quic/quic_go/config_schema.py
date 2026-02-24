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


class QuicGoVersion(VersionBase):
    """Version information for quic-go.

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

    name: str = Field(default="quic-go", description="Implementation name")
    type: ImplementationType = Field(
        default=ImplementationType.IUT, description="Implementation type"
    )

    # Version configuration loaded dynamically from YAML files
    version: QuicGoVersion = Field(
        default_factory=lambda: QuicGoConfig.load_versions_from_files(),
        description="Version configuration",
    )

    @staticmethod
    def load_versions_from_files(
        version_configs_dir: str = f"{Path(os.path.dirname(__file__))}/version_configs/",
    ) -> QuicGoVersion:
        """Load version configurations dynamically from YAML files."""
        logging.debug(f"Loading QuicGo versions from {version_configs_dir}")
        for version_file in os.listdir(version_configs_dir):
            if version_file.endswith(".yaml"):
                version_path = os.path.join(version_configs_dir, version_file)
                raw_version_config = OmegaConf.load(version_path)
                logging.debug(f"Loaded raw QuicGo version config: {raw_version_config}")
                # Create default instance and merge with loaded config
                default_version = QuicGoVersion()
                try:
                    # Pydantic v2
                    default_dict = default_version.model_dump()
                except AttributeError:
                    # Pydantic v1
                    default_dict = default_version.dict()

                merged_config = OmegaConf.merge(default_dict, raw_version_config)
                version_dict = OmegaConf.to_container(merged_config)
                version_config = QuicGoVersion(**version_dict)
                logging.debug(f"Loaded QuicGo version {version_config}")
                return version_config
