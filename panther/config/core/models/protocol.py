"""Protocol configuration models."""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import Field, field_validator

from ..base import BaseConfig


class HttpMethod(str, Enum):
    """HTTP request method."""

    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"


class HttpVersion(str, Enum):
    """HTTP version."""

    HTTP_1_0 = "1.0"
    HTTP_1_1 = "1.1"
    HTTP_2 = "2"
    HTTP_3 = "3"


class TlsVerifyMode(str, Enum):
    """TLS certificate verification mode."""

    NONE = "none"
    OPTIONAL = "optional"
    REQUIRED = "required"


class CongestionControl(str, Enum):
    """Congestion control algorithm."""

    RENO = "reno"
    CUBIC = "cubic"
    BBR = "bbr"
    BBR2 = "bbr2"


class BaseProtocolConfig(BaseConfig, ABC):
    """Abstract base class for protocol configurations."""

    name: str = Field(..., description="Protocol name")
    version: Optional[str] = Field(None, description="Protocol version")

    @abstractmethod
    def get_default_parameters(self) -> Dict[str, Any]:
        """Get default parameters for this protocol.

        Returns:
            Dictionary of default parameters
        """
        pass

    @abstractmethod
    def validate_version(self) -> bool:
        """Validate protocol version.

        Returns:
            True if version is valid
        """
        pass


class ClientServerProtocolConfig(BaseProtocolConfig):
    """Configuration for client-server protocols."""

    # QUIC-specific parameters
    quic_version: Optional[str] = Field(None, description="QUIC version string")
    initial_max_data: Optional[int] = Field(
        10485760, ge=0, description="Initial max data"
    )
    initial_max_stream_data_bidi_local: Optional[int] = Field(
        1048576, ge=0, description="Initial max stream data bidi local"
    )
    initial_max_stream_data_bidi_remote: Optional[int] = Field(
        1048576, ge=0, description="Initial max stream data bidi remote"
    )
    initial_max_stream_data_uni: Optional[int] = Field(
        1048576, ge=0, description="Initial max stream data uni"
    )
    initial_max_streams_bidi: Optional[int] = Field(
        100, ge=0, description="Initial max streams bidi"
    )
    initial_max_streams_uni: Optional[int] = Field(
        100, ge=0, description="Initial max streams uni"
    )
    max_idle_timeout: Optional[int] = Field(
        30000, ge=0, description="Max idle timeout in ms"
    )

    # TLS parameters
    alpn_protocols: List[str] = Field(
        default_factory=lambda: ["h3"], description="ALPN protocols"
    )
    cipher_suites: Optional[List[str]] = Field(None, description="TLS cipher suites")
    key_file: Optional[str] = Field(None, description="TLS key file path")
    cert_file: Optional[str] = Field(None, description="TLS certificate file path")
    ca_file: Optional[str] = Field(None, description="CA certificate file path")
    verify_mode: Optional[TlsVerifyMode] = Field(
        None,
        description="TLS verify mode",
        examples=["none", "optional", "required"],
    )

    # HTTP-specific parameters
    http_version: Optional[HttpVersion] = Field(
        None,
        description="HTTP version",
        examples=["1.0", "1.1", "2", "3"],
    )
    request_headers: Dict[str, str] = Field(
        default_factory=dict, description="HTTP request headers"
    )
    response_headers: Dict[str, str] = Field(
        default_factory=dict, description="HTTP response headers"
    )
    body_size: Optional[int] = Field(None, ge=0, description="HTTP body size")
    method: Optional[HttpMethod] = Field(
        HttpMethod.GET,
        description="HTTP method",
        examples=["GET", "POST", "PUT", "DELETE"],
    )
    path: Optional[str] = Field("/", description="HTTP path")

    # Connection parameters
    connection_timeout: Optional[int] = Field(
        10000, ge=0, description="Connection timeout in ms"
    )
    keep_alive: Optional[bool] = Field(True, description="Enable keep-alive")
    retry_count: Optional[int] = Field(
        3, ge=0, le=100, description="Connection retry count"
    )

    # Performance parameters
    congestion_control: Optional[CongestionControl] = Field(
        None,
        description="Congestion control algorithm",
        examples=["reno", "cubic", "bbr", "bbr2"],
    )
    pacing: Optional[bool] = Field(True, description="Enable pacing")

    @field_validator("method", mode="before")
    @classmethod
    def validate_method(cls, v):
        """Convert string to HttpMethod enum."""
        if isinstance(v, str):
            try:
                return HttpMethod(v.upper())
            except ValueError:
                valid = [e.value for e in HttpMethod]
                raise ValueError(f"Invalid HTTP method '{v}'. Valid: {valid}")
        return v

    @field_validator("http_version", mode="before")
    @classmethod
    def validate_http_version(cls, v):
        """Convert string to HttpVersion enum."""
        if v is None:
            return v
        if isinstance(v, str):
            try:
                return HttpVersion(v)
            except ValueError:
                valid = [e.value for e in HttpVersion]
                raise ValueError(f"Invalid HTTP version '{v}'. Valid: {valid}")
        return v

    @field_validator("verify_mode", mode="before")
    @classmethod
    def validate_verify_mode(cls, v):
        """Convert string to TlsVerifyMode enum."""
        if v is None:
            return v
        if isinstance(v, str):
            try:
                return TlsVerifyMode(v.lower())
            except ValueError:
                valid = [e.value for e in TlsVerifyMode]
                raise ValueError(f"Invalid TLS verify mode '{v}'. Valid: {valid}")
        return v

    @field_validator("congestion_control", mode="before")
    @classmethod
    def validate_congestion_control(cls, v):
        """Convert string to CongestionControl enum."""
        if v is None:
            return v
        if isinstance(v, str):
            try:
                return CongestionControl(v.lower())
            except ValueError:
                valid = [e.value for e in CongestionControl]
                raise ValueError(f"Invalid congestion control '{v}'. Valid: {valid}")
        return v

    def get_default_parameters(self) -> Dict[str, Any]:
        """Get default parameters based on protocol."""
        if self.name.lower() == "quic":
            return {
                "quic_version": self.version or "rfc9000",
                "initial_max_data": self.initial_max_data,
                "initial_max_streams_bidi": self.initial_max_streams_bidi,
                "max_idle_timeout": self.max_idle_timeout,
                "alpn_protocols": self.alpn_protocols,
            }
        elif self.name.lower() == "http":
            return {
                "http_version": self.http_version or "1.1",
                "method": self.method,
                "path": self.path,
                "keep_alive": self.keep_alive,
            }
        else:
            return {}

    def validate_version(self) -> bool:
        """Validate protocol version."""
        if self.name.lower() == "quic":
            valid_versions = ["rfc9000", "draft-29", "draft-32"]
            return self.version in valid_versions if self.version else True
        elif self.name.lower() == "http":
            valid_versions = ["1.0", "1.1", "2", "3"]
            return self.http_version in valid_versions if self.http_version else True
        return True

    def get_transport_parameters(self) -> Dict[str, Any]:
        """Get transport-specific parameters.

        Returns:
            Dictionary of transport parameters
        """
        params = {}

        if self.name.lower() == "quic":
            params.update(
                {
                    "initial_max_data": self.initial_max_data,
                    "initial_max_stream_data_bidi_local": self.initial_max_stream_data_bidi_local,
                    "initial_max_stream_data_bidi_remote": self.initial_max_stream_data_bidi_remote,
                    "initial_max_stream_data_uni": self.initial_max_stream_data_uni,
                    "initial_max_streams_bidi": self.initial_max_streams_bidi,
                    "initial_max_streams_uni": self.initial_max_streams_uni,
                    "max_idle_timeout": self.max_idle_timeout,
                }
            )

            if self.congestion_control:
                params["congestion_control"] = self.congestion_control
            if self.pacing is not None:
                params["pacing"] = self.pacing

        return params


class PeerToPeerProtocolConfig(BaseProtocolConfig):
    """Configuration for peer-to-peer protocols."""

    # P2P specific parameters
    peer_id: Optional[str] = Field(None, description="Peer identifier")
    bootstrap_peers: List[str] = Field(
        default_factory=list, description="Bootstrap peer addresses"
    )
    listen_addresses: List[str] = Field(
        default_factory=list, description="Listen addresses"
    )

    # Discovery parameters
    enable_mdns: bool = Field(True, description="Enable mDNS discovery")
    enable_dht: bool = Field(True, description="Enable DHT")
    discovery_interval: int = Field(
        30, ge=1, le=86400, description="Discovery interval in seconds"
    )

    # Connection parameters
    max_peers: int = Field(50, ge=1, le=10000, description="Maximum number of peers")
    connection_timeout: int = Field(
        30, ge=1, le=3600, description="Connection timeout in seconds"
    )
    ping_interval: int = Field(
        60, ge=1, le=86400, description="Ping interval in seconds"
    )

    # Security parameters
    enable_encryption: bool = Field(True, description="Enable encryption")
    require_authentication: bool = Field(
        False, description="Require peer authentication"
    )

    def get_default_parameters(self) -> Dict[str, Any]:
        """Get default parameters for P2P protocol."""
        return {
            "enable_mdns": self.enable_mdns,
            "enable_dht": self.enable_dht,
            "max_peers": self.max_peers,
            "enable_encryption": self.enable_encryption,
        }

    def validate_version(self) -> bool:
        """Validate protocol version."""
        # P2P protocols might have different versioning
        return True

    def add_bootstrap_peer(self, peer_address: str) -> None:
        """Add a bootstrap peer.

        Args:
            peer_address: Peer address to add
        """
        if peer_address not in self.bootstrap_peers:
            self.bootstrap_peers.append(peer_address)

    def add_listen_address(self, address: str) -> None:
        """Add a listen address.

        Args:
            address: Address to listen on
        """
        if address not in self.listen_addresses:
            self.listen_addresses.append(address)
