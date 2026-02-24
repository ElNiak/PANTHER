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


class QuinnVersion(VersionBase):
    """Version information for Quinn.

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


class QuinnConfig(ServicePluginConfig):
    """Quinn QUIC implementation configuration.

    Quinn is a pure Rust implementation of QUIC built on the Tokio async
    runtime. It provides an ergonomic Rust API with strong type safety
    and uses rustls for TLS 1.3. Quinn is designed for async Rust
    applications and integrates well with the Tokio ecosystem, supporting
    both client and server roles.

    Language: Rust (Tokio) | Source: https://github.com/quinn-rs/quinn
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
          client:
            implementation:
              name: quinn
              type: iut
            protocol:
              name: quic
              version: rfc9000
              role: client
    """

    name: str = Field(default="quinn", description="Implementation name")
    type: ImplementationType = Field(
        default=ImplementationType.IUT, description="Implementation type"
    )

    # Version configuration loaded dynamically from YAML files
    version: QuinnVersion = Field(
        default_factory=lambda: QuinnConfig.load_versions_from_files(),
        description="Version configuration",
    )

    @staticmethod
    def load_versions_from_files(
        version_configs_dir: str = f"{Path(os.path.dirname(__file__))}/version_configs/",
    ) -> QuinnVersion:
        """Load version configurations dynamically from YAML files."""
        logging.debug(f"Loading Quinn versions from {version_configs_dir}")
        for version_file in os.listdir(version_configs_dir):
            if version_file.endswith(".yaml"):
                version_path = os.path.join(version_configs_dir, version_file)
                raw_version_config = OmegaConf.load(version_path)
                logging.debug(f"Loaded raw Quinn version config: {raw_version_config}")
                # Create default instance and merge with loaded config
                default_version = QuinnVersion()
                try:
                    # Pydantic v2
                    default_dict = default_version.model_dump()
                except AttributeError:
                    # Pydantic v1
                    default_dict = default_version.dict()

                merged_config = OmegaConf.merge(default_dict, raw_version_config)
                version_dict = OmegaConf.to_container(merged_config)
                version_config = QuinnVersion(**version_dict)
                logging.debug(f"Loaded Quinn version {version_config}")
                return version_config
