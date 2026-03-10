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


class PingPongVersion(VersionBase):
    """Version information for Ping-Pong MinIP implementation.

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


class PingPongConfig(ServicePluginConfig):
    """Ping-Pong MinIP implementation configuration.

    Simple client-server protocol for testing basic network communication
    patterns. Demonstrates essential MinIP protocol components through
    straightforward ping-pong request-response exchange.

    Multiple variants are available via version configuration:

    - **Functional** -- correct implementation for baseline conformance testing
    - **Vulnerable** -- intentional security flaws for security testing
    - **Flaky** -- intermittently unreliable for fault tolerance testing
    - **Random** -- non-deterministic behavior for stress testing
    - **Fail** -- consistently fails for negative testing

    Language: C | Build time: <1 min | Docker image: ~100MB

    Inherited from ServicePluginConfig / BasePluginConfig:
        enabled (bool): Whether the plugin is enabled. Default: True.

    Example YAML::

        services:
          server:
            implementation:
              name: ping-pong
              type: iut
            protocol:
              name: minip
              role: server
    """

    name: str = Field(default="ping-pong", description="Implementation name")
    type: ImplementationType = Field(
        default=ImplementationType.IUT, description="Implementation type"
    )
    shadow_compatible: bool = Field(
        default=True, description="Whether compatible with Shadow network simulator"
    )

    # Version configuration loaded dynamically from YAML files
    version: PingPongVersion = Field(
        default_factory=lambda: PingPongConfig.load_versions_from_files(),
        description="Version configuration",
    )

    @staticmethod
    def load_versions_from_files(
        version_configs_dir: str = f"{Path(os.path.dirname(__file__))}/version_configs/",
    ) -> PingPongVersion:
        """Load version configurations dynamically from YAML files."""
        logging.debug(f"Loading PingPong versions from {version_configs_dir}")
        for version_file in os.listdir(version_configs_dir):
            if version_file.endswith(".yaml"):
                version_path = os.path.join(version_configs_dir, version_file)
                raw_version_config = OmegaConf.load(version_path)
                logging.debug(
                    f"Loaded raw PingPong version config: {raw_version_config}"
                )
                # Create default instance and merge with loaded config
                default_version = PingPongVersion()
                try:
                    # Pydantic v2
                    default_dict = default_version.model_dump()
                except AttributeError:
                    # Pydantic v1
                    default_dict = default_version.dict()

                merged_config = OmegaConf.merge(default_dict, raw_version_config)
                version_dict = OmegaConf.to_container(merged_config)
                version_config = PingPongVersion(**version_dict)
                logging.debug(f"Loaded Picoquic version {version_config}")
                return version_config
