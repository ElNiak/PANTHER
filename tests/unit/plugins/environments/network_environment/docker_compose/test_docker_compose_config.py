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


# ============================================================================
# Render-context helper tests (Path α single-IP guard + default-source-of-truth)
# ============================================================================


def test_auxiliary_network_render_context_uses_schema_defaults_when_unset():
    """Render context picks defaults from AuxiliaryNetworkConfig(), not duplicated literals."""
    from panther.plugins.environments.network_environment.docker_compose.config_schema import (
        AuxiliaryNetworkConfig,
    )
    from panther.plugins.environments.network_environment.docker_compose.docker_compose import (
        DockerComposeEnvironment,
    )

    env = DockerComposeEnvironment.__new__(DockerComposeEnvironment)
    env.env_config_to_test = type("E", (), {"auxiliary_network": None})()
    expected = AuxiliaryNetworkConfig()

    ctx = env._auxiliary_network_render_context([])
    assert ctx["aux_network_name"] == expected.name
    assert ctx["aux_network_subnet"] == expected.subnet
    assert ctx["any_service_has_secondary_endpoints"] is False


def test_auxiliary_network_render_context_raises_on_multi_secondary():
    """Multi-secondary-endpoint per service must fail loud, not silently drop entries."""
    from panther.plugins.environments.network_environment.docker_compose.docker_compose import (
        DockerComposeEnvironment,
    )

    env = DockerComposeEnvironment.__new__(DockerComposeEnvironment)
    env.env_config_to_test = type("E", (), {"auxiliary_network": None})()

    bad_service = type(
        "S",
        (),
        {
            "service_name": "ivy_tester",
            "service_config_to_test": type(
                "C",
                (),
                {"secondary_endpoints": {"bgp_c": "10.0.0.2", "bgp_d": "10.0.0.3"}},
            )(),
        },
    )()

    with pytest.raises(ValueError, match="secondary_endpoints"):
        env._auxiliary_network_render_context([bad_service])


# ============================================================================
# Template Render Tests
# ============================================================================


class _MockServiceConfig:
    """Mock ServiceConfig for template render tests."""

    def __init__(
        self, secondary_endpoints=None, ports=None, generate_new_certificates=False
    ):
        self.secondary_endpoints = secondary_endpoints or {}
        self.ports = ports or []
        self.generate_new_certificates = generate_new_certificates


class _MockService:
    """Minimal mock of a service-with-container-name object the template iterates over."""

    def __init__(self, service_name="ivy_tester", secondary_endpoints=None):
        self.service_name = service_name
        self.docker_image_tag = "panther/ivy_tester:latest"
        self.service_protocol = type("P", (), {"version": "rfc4271"})()
        self.implementation_name = "ivy_tester"
        self.build_mode = None
        self.runtime_mode = "minimal"
        self.z3_source = "local"
        self.service_config_to_test = _MockServiceConfig(
            secondary_endpoints=secondary_endpoints
        )
        self.environments = {}
        self.volumes = []
        self.run_cmd = {"run_cmd": {"working_dir": "/app"}}


def test_template_renders_aux_network_for_service_with_secondary_endpoints():
    """Service with secondary_endpoints declared -> aux network appears in render."""
    from pathlib import Path

    import yaml
    from jinja2 import Environment, FileSystemLoader

    template_dir = Path(
        "panther/plugins/environments/network_environment/docker_compose/templates"
    )
    env = Environment(loader=FileSystemLoader(str(template_dir)))
    # Register custom filters used by template
    env.filters["regex_replace"] = lambda v, *_args, **_kw: v
    env.filters["realpath"] = lambda v: v
    env.filters["is_dict"] = lambda v: isinstance(v, dict)
    template = env.get_template("docker-compose.yml.jinja")
    rendered = template.render(
        experiment_name="test",
        services=[_MockService(secondary_endpoints={"bgp_c": "10.0.0.2"})],
        any_service_has_secondary_endpoints=True,
        aux_network_name="panther_aux_network",
        aux_network_subnet="10.0.0.0/24",
        log_dir="/tmp/logs",
        output_dir="/tmp/output",
        docker_user_mapping=None,
        additional_param=type(
            "AP",
            (),
            {
                "computed_target_platform": "linux/amd64",
                "docker_config": None,
            },
        )(),
    )
    parsed = yaml.safe_load(rendered)
    svc_networks = parsed["services"]["ivy_tester"]["networks"]
    assert "panther_network" in svc_networks
    assert "panther_aux_network" in svc_networks
    assert svc_networks["panther_aux_network"]["ipv4_address"] == "10.0.0.2"
    assert "panther_aux_network" in parsed["networks"]
    assert (
        parsed["networks"]["panther_aux_network"]["ipam"]["config"][0]["subnet"]
        == "10.0.0.0/24"
    )


def test_template_omits_aux_network_when_no_secondary_endpoints():
    """No secondary_endpoints -> no aux network in render."""
    from pathlib import Path

    import yaml
    from jinja2 import Environment, FileSystemLoader

    template_dir = Path(
        "panther/plugins/environments/network_environment/docker_compose/templates"
    )
    env = Environment(loader=FileSystemLoader(str(template_dir)))
    env.filters["regex_replace"] = lambda v, *_args, **_kw: v
    env.filters["realpath"] = lambda v: v
    env.filters["is_dict"] = lambda v: isinstance(v, dict)
    template = env.get_template("docker-compose.yml.jinja")
    rendered = template.render(
        experiment_name="test",
        services=[_MockService(secondary_endpoints={})],
        any_service_has_secondary_endpoints=False,
        aux_network_name="panther_aux_network",
        aux_network_subnet="10.0.0.0/24",
        log_dir="/tmp/logs",
        output_dir="/tmp/output",
        docker_user_mapping=None,
        additional_param=type(
            "AP",
            (),
            {
                "computed_target_platform": "linux/amd64",
                "docker_config": None,
            },
        )(),
    )
    parsed = yaml.safe_load(rendered)
    assert "panther_aux_network" not in parsed["services"]["ivy_tester"]["networks"]
    assert "panther_aux_network" not in parsed.get("networks", {})
