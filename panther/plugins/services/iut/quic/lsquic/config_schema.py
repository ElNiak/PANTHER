import logging
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional

from omegaconf import OmegaConf

from panther.config.core.models import (
    ImplementationConfig,
    ImplementationType,
    VersionBase,
)


@dataclass
class LsquicVersion(VersionBase):
    version: str = ""
    commit: str = ""
    dependencies: List[Dict[str, str]] = field(default_factory=list)
    client: Optional[dict] = field(default_factory=dict)
    server: Optional[dict] = field(default_factory=dict)


@dataclass
class LsquicConfig(ImplementationConfig):
    name: str = "lsquic"  # Implementation name
    type: ImplementationType = ImplementationType.IUT  # Default type for picoquic
    # These field must not be included in the experiment configuration file
    version: LsquicVersion = field(
        default_factory=lambda: LsquicConfig.load_versions_from_files()
    )

    @staticmethod
    def load_versions_from_files(
        version_configs_dir: str = f"{Path(os.path.dirname(__file__))}/version_configs/",
    ) -> LsquicVersion:
        """Load version configurations dynamically from YAML files."""
        logging.debug(f"Loading Lsquic versions from {version_configs_dir}")
        for version_file in os.listdir(version_configs_dir):
            if version_file.endswith(".yaml"):
                version_path = os.path.join(version_configs_dir, version_file)
                raw_version_config = OmegaConf.load(version_path)
                logging.debug(f"Loaded raw Lsquic version config: {raw_version_config}")
                version_config = OmegaConf.to_object(
                    OmegaConf.merge(LsquicVersion, raw_version_config)
                )
                logging.debug(f"Loaded Lsquic version {version_config}")
                return version_config
