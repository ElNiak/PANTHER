"""Ping-pong MiniP plugin configuration schema."""

from typing import Optional

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

    VERSION_CLASS = PingPongVersion

    name: str = Field(default="ping-pong", description="Implementation name")
    type: ImplementationType = Field(
        default=ImplementationType.IUT, description="Implementation type"
    )
    shadow_compatible: bool = Field(
        default=True, description="Whether compatible with Shadow network simulator"
    )

    # Version configuration loaded dynamically from YAML files
    version: PingPongVersion = Field(
        default_factory=lambda: PingPongConfig.load_version(),
        description="Version configuration",
    )
