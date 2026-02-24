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

    name: str = Field(default="quant", description="Implementation name")
    type: ImplementationType = Field(
        default=ImplementationType.IUT, description="Implementation type"
    )

    # Version configuration loaded dynamically from YAML files
    version: QuantVersion = Field(
        default_factory=lambda: QuantConfig.load_versions_from_files(),
        description="Version configuration",
    )

    @staticmethod
    def load_versions_from_files(
        version_configs_dir: str = f"{Path(os.path.dirname(__file__))}/version_configs/",
    ) -> QuantVersion:
        """Load version configurations dynamically from YAML files."""
        logging.debug(f"Loading Quant versions from {version_configs_dir}")
        for version_file in os.listdir(version_configs_dir):
            if version_file.endswith(".yaml"):
                version_path = os.path.join(version_configs_dir, version_file)
                raw_version_config = OmegaConf.load(version_path)
                logging.debug(f"Loaded raw Quant version config: {raw_version_config}")
                # Create default instance and merge with loaded config
                default_version = QuantVersion()
                try:
                    # Pydantic v2
                    default_dict = default_version.model_dump()
                except AttributeError:
                    # Pydantic v1
                    default_dict = default_version.dict()

                merged_config = OmegaConf.merge(default_dict, raw_version_config)
                version_dict = OmegaConf.to_container(merged_config)
                version_config = QuantVersion(**version_dict)
                logging.debug(f"Loaded Quant version {version_config}")
                return version_config
