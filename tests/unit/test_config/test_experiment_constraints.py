"""Tests for experiment config constraints."""

import pytest

from panther.config.core.models.experiment import StepsConfig, TestConfig


class TestExperimentConstraints:
    def test_wait_too_high(self):
        with pytest.raises(Exception):
            StepsConfig(wait=100000)

    def test_iterations_too_high(self):
        with pytest.raises(Exception):
            TestConfig(
                name="test",
                network_environment={"type": "docker_compose"},
                services={
                    "s": {
                        "implementation": {"name": "test", "type": "iut"},
                        "protocol": {"name": "quic", "role": "server"},
                    }
                },
                iterations=1001,
            )

    def test_name_empty(self):
        with pytest.raises(Exception):
            TestConfig(
                name="",
                network_environment={"type": "docker_compose"},
                services={
                    "s": {
                        "implementation": {"name": "test", "type": "iut"},
                        "protocol": {"name": "quic", "role": "server"},
                    }
                },
            )

    def test_timeout_too_high(self):
        with pytest.raises(Exception):
            TestConfig(
                name="test",
                network_environment={"type": "docker_compose"},
                services={
                    "s": {
                        "implementation": {"name": "test", "type": "iut"},
                        "protocol": {"name": "quic", "role": "server"},
                    }
                },
                timeout=100000,
            )
