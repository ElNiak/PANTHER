"""Protocol configuration models."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from pydantic import Field

from .base_model import BaseUnifiedModel


class BaseProtocolConfig(BaseUnifiedModel, ABC):
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
    initial_max_data: Optional[int] = Field(10485760, description="Initial max data")
    initial_max_stream_data_bidi_local: Optional[int] = Field(1048576, description="Initial max stream data bidi local")
    initial_max_stream_data_bidi_remote: Optional[int] = Field(1048576, description="Initial max stream data bidi remote")
    initial_max_stream_data_uni: Optional[int] = Field(1048576, description="Initial max stream data uni")
    initial_max_streams_bidi: Optional[int] = Field(100, description="Initial max streams bidi")
    initial_max_streams_uni: Optional[int] = Field(100, description="Initial max streams uni")
    max_idle_timeout: Optional[int] = Field(30000, description="Max idle timeout in ms")
    
    # TLS parameters
    alpn_protocols: List[str] = Field(default_factory=lambda: ["h3"], description="ALPN protocols")
    cipher_suites: Optional[List[str]] = Field(None, description="TLS cipher suites")
    key_file: Optional[str] = Field(None, description="TLS key file path")
    cert_file: Optional[str] = Field(None, description="TLS certificate file path")
    ca_file: Optional[str] = Field(None, description="CA certificate file path")
    verify_mode: Optional[str] = Field(None, description="TLS verify mode")
    
    # HTTP-specific parameters
    http_version: Optional[str] = Field(None, description="HTTP version (1.1, 2, 3)")
    request_headers: Dict[str, str] = Field(default_factory=dict, description="HTTP request headers")
    response_headers: Dict[str, str] = Field(default_factory=dict, description="HTTP response headers")
    body_size: Optional[int] = Field(None, description="HTTP body size")
    method: Optional[str] = Field("GET", description="HTTP method")
    path: Optional[str] = Field("/", description="HTTP path")
    
    # Connection parameters
    connection_timeout: Optional[int] = Field(10000, description="Connection timeout in ms")
    keep_alive: Optional[bool] = Field(True, description="Enable keep-alive")
    retry_count: Optional[int] = Field(3, description="Connection retry count")
    
    # Performance parameters
    congestion_control: Optional[str] = Field(None, description="Congestion control algorithm")
    pacing: Optional[bool] = Field(True, description="Enable pacing")
    
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
            params.update({
                "initial_max_data": self.initial_max_data,
                "initial_max_stream_data_bidi_local": self.initial_max_stream_data_bidi_local,
                "initial_max_stream_data_bidi_remote": self.initial_max_stream_data_bidi_remote,
                "initial_max_stream_data_uni": self.initial_max_stream_data_uni,
                "initial_max_streams_bidi": self.initial_max_streams_bidi,
                "initial_max_streams_uni": self.initial_max_streams_uni,
                "max_idle_timeout": self.max_idle_timeout,
            })
            
            if self.congestion_control:
                params["congestion_control"] = self.congestion_control
            if self.pacing is not None:
                params["pacing"] = self.pacing
        
        return params


class PeerToPeerProtocolConfig(BaseProtocolConfig):
    """Configuration for peer-to-peer protocols."""
    
    # P2P specific parameters
    peer_id: Optional[str] = Field(None, description="Peer identifier")
    bootstrap_peers: List[str] = Field(default_factory=list, description="Bootstrap peer addresses")
    listen_addresses: List[str] = Field(default_factory=list, description="Listen addresses")
    
    # Discovery parameters
    enable_mdns: bool = Field(True, description="Enable mDNS discovery")
    enable_dht: bool = Field(True, description="Enable DHT")
    discovery_interval: int = Field(30, description="Discovery interval in seconds")
    
    # Connection parameters
    max_peers: int = Field(50, description="Maximum number of peers")
    connection_timeout: int = Field(30, description="Connection timeout in seconds")
    ping_interval: int = Field(60, description="Ping interval in seconds")
    
    # Security parameters
    enable_encryption: bool = Field(True, description="Enable encryption")
    require_authentication: bool = Field(False, description="Require peer authentication")
    
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