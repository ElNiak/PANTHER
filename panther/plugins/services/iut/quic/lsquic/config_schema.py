"""LSQUIC plugin configuration schema."""

from typing import Dict, Optional

from pydantic import Field

from panther.config.core.models.plugin import ServicePluginConfig


class LsquicConfig(ServicePluginConfig):
    """Configuration for LSQUIC service plugin.

    This configuration supports the dual approach pattern where plugin-specific
    fields can be accessed either through the typed config or the plugin_config dict.
    """

    # Standard plugin fields (inherited from ServicePluginConfig)
    # - enabled: bool
    # - version: Optional[str]
    # - priority: int
    # - docker_image: Optional[str]
    # - build_from_source: bool
    # - source_repository: Optional[str]

    # LSQUIC-specific fields
    name: str = Field(default="lsquic", description="Implementation name")

    # Server-specific options
    doc_root: str = Field(
        default="/var/www", description="Document root for serving files"
    )
    enable_push: bool = Field(default=True, description="Enable HTTP/3 PUSH")
    max_conns: Optional[int] = Field(
        default=None, description="Maximum number of connections"
    )

    # Client-specific options
    request_path: str = Field(default="/", description="Request path")
    method: str = Field(default="GET", description="HTTP method")
    headers: Optional[Dict[str, str]] = Field(
        default_factory=dict, description="Request headers"
    )
    output_file: Optional[str] = Field(default=None, description="Output file path")

    # Environment paths
    library_path: str = Field(
        default="/opt/lsquic/lib", description="LSQUIC library path"
    )
    logs_dir: str = Field(default="/app/logs/artifacts", description="Logs directory")

    # Performance options
    max_packet_size: Optional[int] = Field(
        default=None, description="Maximum packet size"
    )
    initial_max_data: Optional[int] = Field(
        default=None, description="Initial max data limit"
    )
    initial_max_stream_data: Optional[int] = Field(
        default=None, description="Initial max stream data"
    )

    # QUIC protocol options
    quic_version: Optional[str] = Field(default=None, description="QUIC version to use")
    handshake_timeout: Optional[int] = Field(
        default=None, description="Handshake timeout in seconds"
    )
    idle_timeout: Optional[int] = Field(
        default=None, description="Idle timeout in seconds"
    )

    # Debugging options
    verbose: bool = Field(default=False, description="Enable verbose logging")
    debug_level: Optional[int] = Field(default=None, description="Debug logging level")
