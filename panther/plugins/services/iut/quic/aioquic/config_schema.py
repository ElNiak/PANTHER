"""Aioquic QUIC plugin configuration schema."""

from typing import Optional

from pydantic import Field

from panther.config.core.models.plugin import ServicePluginConfig


class AioquicConfig(ServicePluginConfig):
    """Aioquic QUIC implementation configuration.

    Aioquic is a pure-Python QUIC and HTTP/3 implementation built on
    asyncio. It provides a complete QUIC stack without native dependencies,
    making it highly portable and easy to debug. Aioquic supports HTTP/3,
    WebSockets over HTTP/3, server push, datagrams, and stream priority.

    Language: Python (asyncio) | Source: https://github.com/aiortc/aioquic
    Build time: ~2 min | Docker image: ~150MB

    Inherited from ServicePluginConfig / BasePluginConfig:
        enabled (bool): Whether the plugin is enabled. Default: True.
        version (Optional[str]): Plugin version. Default: None.
        priority (int): Plugin execution priority. Default: 100.
        docker_image (Optional[str]): Docker image name. Default: None.
        build_from_source (bool): Build from source. Default: True.
        source_repository (Optional[str]): Source repository URL.

    Example YAML::

        services:
          client:
            implementation:
              name: aioquic
              type: iut
            protocol:
              name: quic
              version: rfc9000
              role: client
    """

    # Aioquic-specific fields
    name: str = Field(default="aioquic", description="Implementation name")

    # Server-specific options
    server_root: str = Field(
        default="/var/www", description="Document root for serving files"
    )
    server_certificate: Optional[str] = Field(
        default="/certs/cert.pem", description="Server certificate path"
    )
    server_private_key: Optional[str] = Field(
        default="/certs/key.pem", description="Server private key path"
    )
    session_ticket_store: Optional[str] = Field(
        default=None, description="Session ticket store path"
    )

    # Client-specific options
    client_output_dir: str = Field(
        default="/app/logs/artifacts", description="Client output directory"
    )
    client_insecure: bool = Field(
        default=True, description="Skip certificate verification"
    )
    client_legacy_http: bool = Field(
        default=False, description="Enable legacy HTTP support"
    )

    # Common options
    verbose: bool = Field(default=False, description="Enable verbose logging")
    secrets_log: Optional[str] = Field(
        default=None, description="Path to secrets log file"
    )

    # Python-specific paths
    python_path: str = Field(
        default="/opt/aioquic", description="Python path for aioquic"
    )
    examples_dir: str = Field(
        default="/opt/aioquic/examples", description="Examples directory"
    )

    # HTTP/3 specific options
    enable_http3: bool = Field(default=True, description="Enable HTTP/3 support")
    enable_websockets: bool = Field(
        default=True, description="Enable WebSocket support"
    )
    enable_priority: bool = Field(default=True, description="Enable stream priority")
    enable_push: bool = Field(default=True, description="Enable server push")
    enable_datagram: bool = Field(default=True, description="Enable datagram support")
