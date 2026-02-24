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


class MvfstVersion(VersionBase):
    """Version information for MVFST.

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

    name: str = Field(default="mvfst", description="Implementation name")
    type: ImplementationType = Field(
        default=ImplementationType.IUT, description="Implementation type"
    )
    # Version configuration loaded dynamically from YAML files
    version: MvfstVersion = Field(
        default_factory=lambda: MvfstConfig.load_versions_from_files(),
        description="Version configuration",
    )

    @staticmethod
    def load_versions_from_files(
        version_configs_dir: str = f"{Path(os.path.dirname(__file__))}/version_configs/",
    ) -> MvfstVersion:
        """Load version configurations dynamically from YAML files."""
        logging.debug(f"Loading Mvfst versions from {version_configs_dir}")
        for version_file in os.listdir(version_configs_dir):
            if version_file.endswith(".yaml"):
                version_path = os.path.join(version_configs_dir, version_file)
                raw_version_config = OmegaConf.load(version_path)
                logging.debug(f"Loaded raw Mvfst version config: {raw_version_config}")
                # Create default instance and merge with loaded config
                default_version = MvfstVersion()
                try:
                    # Pydantic v2
                    default_dict = default_version.model_dump()
                except AttributeError:
                    # Pydantic v1
                    default_dict = default_version.dict()

                merged_config = OmegaConf.merge(default_dict, raw_version_config)
                version_dict = OmegaConf.to_container(merged_config)
                version_config = MvfstVersion(**version_dict)
                logging.debug(f"Loaded Mvfst version {version_config}")
                return version_config
