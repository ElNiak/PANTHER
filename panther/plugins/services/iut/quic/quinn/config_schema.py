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
    """Configuration for Quinn QUIC implementation."""

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
