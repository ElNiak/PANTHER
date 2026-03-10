"""Environment configuration models."""

from typing import List, Optional

from pydantic import Field

from ..base import BaseConfig


class EnvironmentConfig(BaseConfig):
    """Base environment configuration."""

    type: str = Field(
        ...,
        description="Environment type",
        json_schema_extra={
            "widget_type": "plugin_select",
            "plugin_type": "network_environment",
        },
    )
    enabled: bool = Field(True, description="Whether this environment is enabled")

    # Background monitoring configuration
    enable_background_monitoring: bool = Field(
        True, description="Enable background monitoring"
    )
    monitoring_interval_seconds: int = Field(
        5,
        ge=1,
        le=3600,
        description="Monitoring interval in seconds",
        examples=[5, 10, 30],
        json_schema_extra={"unit": "seconds"},
    )
    failure_threshold_count: int = Field(
        1,
        ge=1,
        le=100,
        description="Failure threshold count",
        examples=[1, 3, 5],
    )
    allow_partial_deployment: bool = Field(
        False, description="Allow partial deployment"
    )
    critical_services: List[str] = Field(
        default_factory=list, description="Critical services list"
    )


class NetworkEnvironmentConfig(EnvironmentConfig):
    """Base network environment configuration."""

    # Fields merged from former NetworkEnvironmentPluginConfig
    network_name: str = Field("panther_network", description="Network name")
    subnet: Optional[str] = Field(None, description="Network subnet")
    enable_ipv6: bool = Field(False, description="Enable IPv6 support")


class ExecutionEnvironmentConfig(EnvironmentConfig):
    """Base execution environment configuration."""

    type: str = Field(
        ...,
        description="Execution environment type",
        json_schema_extra={
            "widget_type": "plugin_select",
            "plugin_type": "execution_environment",
        },
    )

    # Fields merged from former ExecutionEnvironmentPluginConfig
    output_format: str = Field("json", description="Output format for results")
    collect_metrics: bool = Field(True, description="Whether to collect metrics")
