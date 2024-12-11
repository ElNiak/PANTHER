from dataclasses import dataclass, field
import logging
import os
from typing import Optional
from enum import Enum

from omegaconf import OmegaConf

from plugins.services.iut.config_schema import ImplementationConfig, VersionBase
from plugins.services.iut.config_schema import ImplementationType

from dataclasses import dataclass, field
from typing import List, Dict

@dataclass
class PicoquicShadowVersion(VersionBase):
    version: str = ""
    commit: str = ""
    dependencies: List[Dict[str, str]] = field(default_factory=list)
    client: Optional[Dict] = field(default_factory=dict)
    server: Optional[Dict] = field(default_factory=dict)
    
@dataclass
class PicoquicShadowConfig(ImplementationConfig):
    name: str  = "picoquic_shadow" # Implementation name
    type: ImplementationType = ImplementationType.iut  # Default type for picoquic
    shadow_compatible: bool = field(default=True) 
    # These field must not be included in the experiment configuration file
    version: PicoquicShadowVersion = field(default_factory=lambda: PicoquicShadowConfig.load_versions_from_files())
    
    @staticmethod
    def load_versions_from_files(version_configs_dir: str = "plugins/services/iut/quic/picoquic/version_configs/") -> PicoquicShadowVersion:
        """Load version configurations dynamically from YAML files."""
        logging.debug(f"Loading PicoquicShadow versions from {version_configs_dir}")
        for version_file in os.listdir(version_configs_dir):
            if version_file.endswith(".yaml"):
                version_path = os.path.join(version_configs_dir, version_file)
                raw_version_config = OmegaConf.load(version_path)
                logging.debug(f"Loaded raw PicoquicShadow version config: {raw_version_config}")
                version_config = OmegaConf.to_object(OmegaConf.merge(PicoquicShadowVersion, raw_version_config))
                logging.debug(f"Loaded PicoquicShadow version {version_config}")
                return version_config