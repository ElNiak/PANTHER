"""Tests for environment config constraints."""

import pytest

from panther.config.core.models.environment import EnvironmentConfig


class TestEnvironmentConstraints:
    def test_monitoring_interval_zero(self):
        with pytest.raises(Exception):
            EnvironmentConfig(type="docker_compose", monitoring_interval_seconds=0)

    def test_failure_threshold_zero(self):
        with pytest.raises(Exception):
            EnvironmentConfig(type="docker_compose", failure_threshold_count=0)
