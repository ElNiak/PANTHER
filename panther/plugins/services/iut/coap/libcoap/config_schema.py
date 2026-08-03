"""LibCoAP CoAP plugin configuration schema."""

from typing import ClassVar, Optional

from pydantic import Field

from panther.config.core.models.service import (
    ImplementationConfig,
    ProtocolConfig,
    ServiceConfig,
    VersionBase,
)


class LibcoapVersion(VersionBase):
    """Version information for the LibCoAP implementation."""

    server: Optional[dict] = Field(default_factory=dict)
    client: Optional[dict] = Field(default_factory=dict)


class LibcoapConfig(ServiceConfig):
    """LibCoAP implementation configuration.

    Builds the libcoap examples in the image and runs its client or server
    binary as the CoAP implementation under test.

    Example YAML::

        services:
          coap_server:
            implementation:
              name: libcoap
              type: iut
            protocol:
              name: coap
              role: server
    """

    VERSION_CLASS: ClassVar[Optional[type]] = LibcoapVersion

    implementation: ImplementationConfig = Field(
        default_factory=lambda: ImplementationConfig(name="libcoap", type="iut"),
        description="Implementation configuration",
    )
    protocol: ProtocolConfig = Field(
        default_factory=lambda: ProtocolConfig(name="coap", role="server"),
        description="Protocol configuration",
    )
    version: LibcoapVersion = Field(
        default_factory=lambda: LibcoapConfig.load_version(),
        description="Version configuration",
    )
