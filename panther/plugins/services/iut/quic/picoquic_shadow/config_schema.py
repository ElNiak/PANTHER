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
    version: str = Field(default="")
    commit: str = Field(default="")
    dependencies: List[Dict[str, str]] = Field(default_factory=list)
    client: Optional[dict] = Field(default_factory=dict)
    server: Optional[dict] = Field(default_factory=dict)


class PicoquicShadowConfig(ServicePluginConfig):
    """
    PicoquicShadowConfig class is a configuration class for the PicoquicShadow implementation.
    Attributes:
        name (str): Implementation name, default is "picoquic_shadow".
        type (ImplementationType): Default type for picoquic, default is ImplementationType.IUT.
        shadow_compatible (bool): Indicates if the implementation is shadow compatible, default is True.
        version (PicoquicShadowVersion): Version configuration loaded dynamically from YAML files.
    Methods:
        load_versions_from_files(version_configs_dir: str =f"{ Path(os.path.dirname(__file__))}/quic/picoquic/version_configs/") -> PicoquicShadowVersion:
            Loads version configurations dynamically from YAML files located in the specified directory.
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
