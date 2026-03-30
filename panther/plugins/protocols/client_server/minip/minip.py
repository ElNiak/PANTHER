"""MiniP protocol manager.

This class manages the MiniP protocol configurations and provides
version-specific parameters for MiniP implementations.
"""

import logging

from panther.plugins.core.plugin_decorators import register_protocol
from panther.plugins.protocols.client_server.client_server import (
    ClientServerProtocolBase,
)


@register_protocol(
    name="minip",
    description="MiniP Protocol Manager",
    version="0.1.0",
    author="PANTHER Team",
    license="MIT",
    tags=["transport", "secure", "multiplexed"],
    versions=["flaky", "fail", "functional", "random", "vulnerable"],
)
class MiniPProtocol(ClientServerProtocolBase):
    """MiniP protocol manager.

    This class manages MiniP protocol configurations and provides
    version-specific parameters for MiniP implementations.
    """

    def __init__(self):
        """Initialize MiniP protocol manager."""
        # Skip parent init since we don't need the old YAML loading
        self.logger = logging.getLogger("MiniPProtocol")

    def validate_config(self):
        """Validate protocol configuration."""
        # Configuration is validated through the schema
        pass

    def load_config(self) -> dict:
        """Load protocol configuration."""
        # Return the default config from decorator
        return self.get_protocol_metadata().get("default_config", {})

    def get_version_parameters(self, version: str) -> dict:
        """Get version-specific parameters.

        Args:
            version: Protocol version identifier

        Returns:
            Version-specific parameters
        """
        # Version-specific parameters that might differ
        version_params = {
            "rfc9000": {
                "initial_version": "00000001",
                "version_negotiation": True,
                "compatible_versions": ["rfc9000"],
            },
            "draft-29": {
                "initial_version": "ff00001d",  # 0xFF00001D
                "version_negotiation": True,
                "compatible_versions": ["draft-29"],
            },
            "draft-27": {
                "initial_version": "ff00001b",  # 0xFF00001B
                "version_negotiation": True,
                "compatible_versions": ["draft-27"],
            },
            "draft-27-vuln1": {
                "initial_version": "ff00001b",
                "version_negotiation": True,
                "compatible_versions": ["draft-27"],
                # Specific parameters for vulnerability testing
                "enable_vuln_test": "vuln1",
            },
            "draft-27-vuln2": {
                "initial_version": "ff00001b",
                "version_negotiation": True,
                "compatible_versions": ["draft-27"],
                # Specific parameters for vulnerability testing
                "enable_vuln_test": "vuln2",
            },
        }

        return version_params.get(version, {})

    @classmethod
    def get_default_server_port(cls) -> int:
        """Get the default server port for QUIC."""
        return 4443

    @classmethod
    def get_default_client_port(cls) -> int:
        """Get the default client port for QUIC (usually ephemeral)."""
        return 0  # Ephemeral port
