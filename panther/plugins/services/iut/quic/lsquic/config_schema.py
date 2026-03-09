"""LSQUIC QUIC plugin configuration schema."""

from typing import Dict, Optional

from pydantic import Field

from panther.config.core.models.service import (
    ImplementationConfig,
    ProtocolConfig,
    ServiceConfig,
)


class LsquicConfig(ServiceConfig):
    """LSQUIC QUIC implementation configuration.

    LSQUIC (LiteSpeed QUIC) is a high-performance C implementation of
    QUIC and HTTP/3 developed by LiteSpeed Technologies. It powers the
    LiteSpeed Web Server and is optimized for production workloads with
    fine-grained control over connection limits, packet sizes, and
    protocol timeouts.

    Language: C | Source: https://github.com/litespeedtech/lsquic
    Build time: ~8 min | Docker image: ~250MB

    Example YAML::

        services:
          server:
            implementation:
              name: lsquic
              type: iut
            protocol:
              name: quic
              version: rfc9000
              role: server
    """

    # Override required fields with plugin-specific defaults
    implementation: ImplementationConfig = Field(
        default_factory=lambda: ImplementationConfig(name="lsquic", type="iut"),
        description="Implementation configuration",
    )
    protocol: ProtocolConfig = Field(
        default_factory=lambda: ProtocolConfig(name="quic", role="server"),
        description="Protocol configuration",
    )

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
