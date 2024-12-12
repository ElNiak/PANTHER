from dataclasses import dataclass, field

from panther.plugins.protocols.config_schema import ProtocolConfig
from panther.plugins.services.iut.config_schema import ImplementationConfig


# Service Configuration
@dataclass
class ServiceConfig:
    """
    ServiceConfig class represents the configuration for a service.

    Attributes:
        name (str): Service name.
        timeout (int): Timeout for the service. Defaults to 100.
        implementation (ImplementationConfig): Implementation details. Defaults to an ImplementationConfig instance with name "implem_name".
        protocol (ProtocolConfig): Protocol configuration. Defaults to a ProtocolConfig instance.
        ports (List[str]): List of ports. Defaults to an empty list.
        generate_new_certificates (bool): Flag to generate new certificates. Defaults to False.
        volumes (List[str]): List of volumes. Defaults to an empty list.
        directories_to_start (List[str]): List of directories to start. Defaults to an empty list.
    """

    name: str  # Service name
    timeout: int = field(default=100)  # Timeout for the service
    implementation: ImplementationConfig = field(
        default_factory=lambda: ImplementationConfig(name="implem_name")
    )  # Implementation details
    protocol: ProtocolConfig = field(
        default_factory=ProtocolConfig
    )  # Protocol configuration
    ports: list[str] = field(default_factory=list)  # List of ports
    generate_new_certificates: bool = field(
        default=False
    )  # Flag to generate new certificates
    volumes: list[str] = field(default_factory=list)
    directories_to_start: list[str] = field(default_factory=list)
