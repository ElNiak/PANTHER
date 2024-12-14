from dataclasses import dataclass, field
import logging
import os
from pathlib import Path

from omegaconf import OmegaConf

from panther.plugins.services.iut.config_schema import ImplementationConfig, VersionBase
from panther.plugins.services.iut.config_schema import ImplementationType


@dataclass
class PicoquicVersion(VersionBase):
    version: str = ""
    commit: str = ""
    dependencies: list[dict[str, str]] = field(default_factory=list)
    client: dict | None = field(default_factory=dict)
    server: dict | None = field(default_factory=dict)


@dataclass
class PicoquicConfig(ImplementationConfig):
    name: str = "picoquic"  # Implementation name
    type: ImplementationType = ImplementationType.iut  # Default type for picoquic
    # These field must not be included in the experiment configuration file
    version: PicoquicVersion = field(
        default_factory=lambda: PicoquicConfig.load_versions_from_files()
    )

    @staticmethod
    def load_versions_from_files(
        version_configs_dir: str =f"{Path(os.path.dirname(__file__))}/version_configs/",
    ) -> PicoquicVersion:
        """Load version configurations dynamically from YAML files."""
        logging.debug(f"Loading Picoquic versions from {version_configs_dir}")
        for version_file in os.listdir(version_configs_dir):
            if version_file.endswith(".yaml"):
                version_path = os.path.join(version_configs_dir, version_file)
                raw_version_config = OmegaConf.load(version_path)
                logging.debug(
                    f"Loaded raw Picoquic version config: {raw_version_config}"
                )
                version_config = OmegaConf.to_object(
                    OmegaConf.merge(PicoquicVersion, raw_version_config)
                )
                logging.debug(f"Loaded Picoquic version {version_config}")
                return version_config
