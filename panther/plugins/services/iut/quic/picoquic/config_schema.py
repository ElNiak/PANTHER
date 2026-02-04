import logging
import os
from pathlib import Path
from typing import Dict, List, Optional

from omegaconf import OmegaConf
from pydantic import BaseModel, Field

from panther.config.core.models.plugin import ServicePluginConfig
from panther.config.core.models.service import ImplementationType, VersionBase


class PicoquicVersion(VersionBase):
    """Version information for Picoquic."""

    # Provide defaults for required base fields
    version: str = Field(default="", description="Version string")
    commit: str = Field(default="", description="Git commit hash")
    dependencies: List[Dict[str, str]] = Field(
        default_factory=list, description="List of dependencies"
    )

    # Additional fields beyond VersionBase
    client: Optional[dict] = Field(
        default_factory=dict, description="Client-specific configuration"
    )
    server: Optional[dict] = Field(
        default_factory=dict, description="Server-specific configuration"
    )


class PicoquicConfig(ServicePluginConfig):
    """Configuration for Picoquic QUIC implementation."""

    name: str = Field(default="picoquic", description="Implementation name")
    type: ImplementationType = Field(
        default_factory=lambda: ImplementationType.IUT,
        description="Implementation type",
    )
    version: PicoquicVersion = Field(
        default_factory=lambda: PicoquicConfig.load_versions_from_files(),
        description="Version configuration",
    )

    # QUIC-specific parameters
    alpn: Optional[str] = Field(default=None, description="ALPN protocol identifier")
    initial_rtt: Optional[int] = Field(
        default=None, description="Initial RTT in milliseconds"
    )
    max_stream_data: Optional[int] = Field(
        default=None, description="Maximum stream data in bytes"
    )
    max_data: Optional[int] = Field(
        default=None, description="Maximum connection data in bytes"
    )

    @staticmethod
    def load_versions_from_files(
        version_configs_dir: str = f"{Path(os.path.dirname(__file__))}/version_configs/",
        version: Optional[str] = None,
        protocol_version_override: Optional[str] = None,
    ) -> PicoquicVersion:
        """Load version configurations dynamically from YAML files.

        Args:
            version_configs_dir: Directory containing version YAML files
            version: Specific version to load (e.g., 'rfc9000'). If None, loads first found.
            protocol_version_override: Protocol version from experiment config to use as override

        Returns:
            PicoquicVersion configuration

        Raises:
            FileNotFoundError: If specified version file not found
            ValueError: If no version files found
        """
        logging.debug("Loading Picoquic versions from %s", version_configs_dir)

        # Use protocol version override if provided, otherwise use explicit version
        effective_version = protocol_version_override or version

        if effective_version:
            # Load specific version file
            version_file = f"{effective_version}.yaml"
            version_path = os.path.join(version_configs_dir, version_file)

            if not os.path.exists(version_path):
                raise FileNotFoundError(
                    f"Version config file not found: {version_path}"
                )

            logging.debug(f"Loading specific Picoquic version: {effective_version}")
            raw_version_config = OmegaConf.load(version_path)
            logging.debug(f"Loaded raw Picoquic version config: {raw_version_config}")

            # Convert OmegaConf to dict and create Pydantic model
            version_dict = OmegaConf.to_container(raw_version_config)
            version_config = PicoquicVersion(**version_dict)
            logging.debug(f"Loaded Picoquic version {version_config}")
            return version_config

        else:
            # Legacy behavior: load first found file (sorted for deterministic order)
            version_files = sorted(
                [f for f in os.listdir(version_configs_dir) if f.endswith(".yaml")]
            )

            if not version_files:
                raise ValueError(
                    f"No version config files found in {version_configs_dir}"
                )

            version_file = version_files[0]
            logging.warning(
                f"No version specified, loading first found: {version_file}"
            )
            version_path = os.path.join(version_configs_dir, version_file)

            raw_version_config = OmegaConf.load(version_path)
            logging.debug(f"Loaded raw Picoquic version config: {raw_version_config}")

            # Convert OmegaConf to dict and create Pydantic model
            version_dict = OmegaConf.to_container(raw_version_config)
            version_config = PicoquicVersion(**version_dict)
            logging.debug(f"Loaded Picoquic version {version_config}")
            return version_config

    @classmethod
    def create_with_protocol_context(cls, protocol=None):
        """Create PicoquicConfig instance with optional protocol context.

        If protocol version is provided, loads version-specific configuration.
        Otherwise creates standard instance.

        Args:
            protocol: Optional protocol configuration containing version info

        Returns:
            PicoquicConfig instance with appropriate version configuration
        """
        logging.debug("Creaol context")
        if protocol and hasattr(protocol, "version") and protocol.version:
            try:
                version_config = cls.load_versions_from_files(
                    protocol_version_override=protocol.version
                )
                return cls(version=version_config)
            except (FileNotFoundError, ValueError) as e:
                raise ValueError(
                    f"Could not load protocol version {protocol.version}: {e}"
                ) from e
        return cls()
