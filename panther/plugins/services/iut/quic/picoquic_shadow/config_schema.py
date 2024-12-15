from dataclasses import dataclass, field
import logging
import os
from pathlib import Path

from omegaconf import OmegaConf

from panther.plugins.services.iut.config_schema import ImplementationConfig, VersionBase
from panther.plugins.services.iut.config_schema import ImplementationType


@dataclass
class PicoquicShadowVersion(VersionBase):
    version: str = ""
    commit: str = ""
    dependencies: list[dict[str, str]] = field(default_factory=list)
    client: dict | None = field(default_factory=dict)
    server: dict | None = field(default_factory=dict)


@dataclass
class PicoquicShadowConfig(ImplementationConfig):
    """
    PicoquicShadowConfig class is a configuration class for the PicoquicShadow implementation.
    Attributes:
        name (str): Implementation name, default is "picoquic_shadow".
        type (ImplementationType): Default type for picoquic, default is ImplementationType.iut.
        shadow_compatible (bool): Indicates if the implementation is shadow compatible, default is True.
        version (PicoquicShadowVersion): Version configuration loaded dynamically from YAML files.
    Methods:
        load_versions_from_files(version_configs_dir: str =f"{ Path(os.path.dirname(__file__))}/quic/picoquic/version_configs/") -> PicoquicShadowVersion:
            Loads version configurations dynamically from YAML files located in the specified directory.
    """

    name: str = "picoquic_shadow"  # Implementation name
    type: ImplementationType = ImplementationType.iut  # Default type for picoquic
    shadow_compatible: bool = field(default=True)
    # These field must not be included in the experiment configuration file
    version: PicoquicShadowVersion = field(
        default_factory=lambda: PicoquicShadowConfig.load_versions_from_files()
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
                version_config = OmegaConf.to_object(
                    OmegaConf.merge(PicoquicShadowVersion, raw_version_config)
                )
                logging.debug(f"Loaded PicoquicShadow version {version_config}")
                return version_config
