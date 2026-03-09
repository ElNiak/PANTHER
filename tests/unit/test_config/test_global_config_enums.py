"""Tests for global_config enums and constraints."""

import pytest

from panther.config.core.models.global_config import (
    DockerConfig,
    DockerNetworkMode,
    DockerUserMappingConfig,
    ExportFormat,
    FastFailConfig,
    FeatureLogLevelsConfig,
    LoggingLevel,
    MetricsConfig,
    ProgressConfig,
)


class TestDockerNetworkModeEnum:
    def test_valid_values(self):
        for val in ["bridge", "host", "none", "overlay"]:
            assert DockerNetworkMode(val).value == val

    def test_invalid_value(self):
        with pytest.raises(ValueError):
            DockerNetworkMode("invalid")

    def test_docker_config_accepts_string(self):
        dc = DockerConfig(network_mode="host")
        assert dc.network_mode == DockerNetworkMode.HOST


class TestExportFormatEnum:
    def test_valid_values(self):
        for val in ["json", "csv", "prometheus"]:
            assert ExportFormat(val).value == val

    def test_metrics_config_accepts_string(self):
        mc = MetricsConfig(export_format="prometheus")
        assert mc.export_format == ExportFormat.PROMETHEUS


class TestFeatureLogLevelsUsesLoggingLevel:
    def test_accepts_valid_level(self):
        flc = FeatureLogLevelsConfig(docker_build="DEBUG")
        assert flc.docker_build == LoggingLevel.DEBUG

    def test_rejects_invalid_level(self):
        with pytest.raises(Exception):
            FeatureLogLevelsConfig(docker_build="INVALID")


class TestGlobalConfigConstraints:
    def test_uid_too_high(self):
        with pytest.raises(Exception):
            DockerUserMappingConfig(custom_uid=70000)

    def test_uid_negative(self):
        with pytest.raises(Exception):
            DockerUserMappingConfig(custom_uid=-1)

    def test_update_interval_too_low(self):
        with pytest.raises(Exception):
            ProgressConfig(update_interval=0.001)

    def test_cascade_threshold_zero(self):
        with pytest.raises(Exception):
            FastFailConfig(timeout_cascade_threshold=0)

    def test_publish_interval_zero(self):
        with pytest.raises(Exception):
            MetricsConfig(publish_interval=0)

    def test_retention_too_high(self):
        with pytest.raises(Exception):
            MetricsConfig(retention_days=400)
