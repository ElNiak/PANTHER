import logging
import os
from pathlib import Path
from typing import Dict, List, Optional

from omegaconf import OmegaConf
from pydantic import BaseModel, Field

from panther.config.core.models.plugin import ServicePluginConfig
from panther.config.core.models.service import ImplementationType


class PicoquicVersion(BaseModel):
    """Version information for Picoquic."""
    
    version: str = Field(default="", description="Version string")
    commit: str = Field(default="", description="Git commit hash")
    dependencies: List[Dict[str, str]] = Field(
        default_factory=list,
        description="List of dependencies"
    )
    client: Optional[dict] = Field(
        default_factory=dict,
        description="Client-specific configuration"
    )
    server: Optional[dict] = Field(
        default_factory=dict,
        description="Server-specific configuration"
    )


class PicoquicConfig(ServicePluginConfig):
    """Configuration for Picoquic QUIC implementation."""
    
    name: str = Field(
        default="picoquic",
        description="Implementation name"
    )
    type: ImplementationType = Field(
        default=ImplementationType.IUT,
        description="Implementation type"
    )
    version: PicoquicVersion = Field(
        default_factory=lambda: PicoquicConfig.load_versions_from_files(),
        description="Version configuration"
    )
    
    # QUIC-specific parameters
    alpn: Optional[str] = Field(
        default=None,
        description="ALPN protocol identifier"
    )
    initial_rtt: Optional[int] = Field(
        default=None,
        description="Initial RTT in milliseconds"
    )
    max_stream_data: Optional[int] = Field(
        default=None,
        description="Maximum stream data in bytes"
    )
    max_data: Optional[int] = Field(
        default=None,
        description="Maximum connection data in bytes"
    )

    @staticmethod
    def load_versions_from_files(
        version_configs_dir: str = f"{Path(os.path.dirname(__file__))}/version_configs/",
    ) -> PicoquicVersion:
        """Load version configurations dynamically from YAML files."""
        logging.debug("Loading Picoquic versions from %s", version_configs_dir)
        for version_file in os.listdir(version_configs_dir):
            if version_file.endswith(".yaml"):
                version_path = os.path.join(version_configs_dir, version_file)
                raw_version_config = OmegaConf.load(version_path)
                logging.debug(
                    f"Loaded raw Picoquic version config: {raw_version_config}"
                )
                # Convert OmegaConf to dict and create Pydantic model
                version_dict = OmegaConf.to_container(raw_version_config)
                version_config = PicoquicVersion(**version_dict)
                logging.debug(f"Loaded Picoquic version {version_config}")
                return version_config
