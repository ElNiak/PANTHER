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


class PicoquicShadowVersion(VersionBase):
    """Version information for Picoquic Shadow.

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

    name: str = Field(default="picoquic_shadow", description="Implementation name")
    type: ImplementationType = Field(
        default=ImplementationType.IUT, description="Implementation type"
    )
    shadow_compatible: bool = Field(
        default=True, description="Whether compatible with Shadow network simulator"
    )

    # Version configuration loaded dynamically from YAML files
    version: PicoquicShadowVersion = Field(
        default_factory=lambda: PicoquicShadowConfig.load_versions_from_files(),
        description="Version configuration",
    )

    @staticmethod
    def load_versions_from_files(
        version_configs_dir: str = f"{Path(os.path.dirname(__file__))}/version_configs/",
    ) -> PicoquicShadowVersion:
        """Load version configurations dynamically from YAML files."""
        logging.debug(f"Loading PicoquicShadow versions from {version_configs_dir}")
        for version_file in os.listdir(version_configs_dir):
            if version_file.endswith(".yaml"):
                version_path = os.path.join(version_configs_dir, version_file)
                raw_version_config = OmegaConf.load(version_path)
                logging.debug(
                    f"Loaded raw PicoquicShadow version config: {raw_version_config}"
                )
                # Create default instance and merge with loaded config
                default_version = PicoquicShadowVersion()
                try:
                    # Pydantic v2
                    default_dict = default_version.model_dump()
                except AttributeError:
                    # Pydantic v1
                    default_dict = default_version.dict()

                merged_config = OmegaConf.merge(default_dict, raw_version_config)
                version_dict = OmegaConf.to_container(merged_config)
                version_config = PicoquicShadowVersion(**version_dict)
                logging.debug(f"Loaded PicoquicShadow version {version_config}")
                return version_config
