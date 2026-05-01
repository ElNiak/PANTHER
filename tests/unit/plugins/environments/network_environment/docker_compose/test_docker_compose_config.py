"""Tests for docker_compose plugin config_schema (Path α extension)."""

import pytest

pytestmark = [pytest.mark.unit]


def test_auxiliary_network_config_defaults():
    """AuxiliaryNetworkConfig defaults to panther_aux_network on 10.0.0.0/24."""
    from panther.plugins.environments.network_environment.docker_compose.config_schema import (
        AuxiliaryNetworkConfig,
    )

    cfg = AuxiliaryNetworkConfig()
    assert cfg.name == "panther_aux_network"
    assert cfg.subnet == "10.0.0.0/24"


def test_auxiliary_network_config_custom():
    """AuxiliaryNetworkConfig accepts custom name and subnet."""
    from panther.plugins.environments.network_environment.docker_compose.config_schema import (
        AuxiliaryNetworkConfig,
    )

    cfg = AuxiliaryNetworkConfig(name="custom_aux", subnet="192.168.99.0/24")
    assert cfg.name == "custom_aux"
    assert cfg.subnet == "192.168.99.0/24"


def test_auxiliary_network_config_extra_forbid():
    """AuxiliaryNetworkConfig must reject unknown fields (extra='forbid')."""
    from pydantic import ValidationError

    from panther.plugins.environments.network_environment.docker_compose.config_schema import (
        AuxiliaryNetworkConfig,
    )

    with pytest.raises(ValidationError):
        AuxiliaryNetworkConfig(name="x", subnet="10.0.0.0/24", driver="bridge")  # noqa


def test_docker_compose_config_auxiliary_network_default_none():
    """DockerComposeConfig.auxiliary_network defaults to None."""
    from panther.plugins.environments.network_environment.docker_compose.config_schema import (
        DockerComposeConfig,
    )

    cfg = DockerComposeConfig()
    assert cfg.auxiliary_network is None


def test_docker_compose_config_auxiliary_network_round_trip():
    """DockerComposeConfig.auxiliary_network round-trips through model_dump/model_validate."""
    from panther.plugins.environments.network_environment.docker_compose.config_schema import (
        DockerComposeConfig,
    )

    cfg = DockerComposeConfig.model_validate(
        {
            "auxiliary_network": {"name": "test_aux", "subnet": "10.0.0.0/16"},
        }
    )
    assert cfg.auxiliary_network is not None
    assert cfg.auxiliary_network.name == "test_aux"
    assert cfg.auxiliary_network.subnet == "10.0.0.0/16"
    payload = cfg.model_dump()
    assert payload["auxiliary_network"] == {"name": "test_aux", "subnet": "10.0.0.0/16"}
