"""Tests for environment and plugin config constraints."""

import pytest

from panther.config.core.models.environment import EnvironmentConfig
from panther.config.core.models.plugin import ProtocolPluginConfig


class TestEnvironmentConstraints:
    def test_monitoring_interval_zero(self):
        with pytest.raises(Exception):
            EnvironmentConfig(type="docker_compose", monitoring_interval_seconds=0)

    def test_failure_threshold_zero(self):
        with pytest.raises(Exception):
            EnvironmentConfig(type="docker_compose", failure_threshold_count=0)


class TestPluginConstraints:
    def test_port_too_high(self):
        with pytest.raises(Exception):
            ProtocolPluginConfig(protocol_version="1.0", default_port=70000)

    def test_port_zero(self):
        with pytest.raises(Exception):
            ProtocolPluginConfig(protocol_version="1.0", default_port=0)

    def test_priority_negative(self):
        with pytest.raises(Exception):
            ProtocolPluginConfig(protocol_version="1.0", default_port=443, priority=-1)
