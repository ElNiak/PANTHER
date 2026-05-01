"""Tests for DockerComposeNetworkResolver (Path α secondary-endpoint short-circuit)."""

import pytest

from panther.config.core.models.network_resolution import (
    NetworkAttribute,
    NetworkFormat,
    NetworkServiceInfo,
    PlaceholderInfo,
)
from panther.plugins.environments.network_environment.docker_compose.docker_network_resolver import (
    DockerComposeNetworkResolver,
)

pytestmark = [pytest.mark.unit]


def _service_info_with_secondary(secondary_endpoints):
    return NetworkServiceInfo(
        service_name="ivy_tester",
        ip_address="172.19.0.3",
        secondary_endpoints=secondary_endpoints,
    )


def _placeholder_with_secondary(secondary_name, format_type):
    return PlaceholderInfo(
        service="ivy_tester",
        attribute=NetworkAttribute.IP,
        format_type=format_type,
        secondary_name=secondary_name,
        raw_placeholder=f"@{{ivy_tester:ip[{secondary_name}]:{format_type.value}}}",
    )


def test_generate_resolved_value_secondary_endpoint_hex():
    resolver = DockerComposeNetworkResolver()
    info = _service_info_with_secondary({"bgp_c": "10.0.0.2"})
    placeholder = _placeholder_with_secondary("bgp_c", NetworkFormat.HEX)
    assert resolver._generate_resolved_value(placeholder, info) == "0x0a000002"


def test_generate_resolved_value_secondary_endpoint_dotted():
    resolver = DockerComposeNetworkResolver()
    info = _service_info_with_secondary({"bgp_c": "10.0.0.2"})
    placeholder = _placeholder_with_secondary("bgp_c", NetworkFormat.DOTTED)
    assert resolver._generate_resolved_value(placeholder, info) == "10.0.0.2"


def test_generate_resolved_value_secondary_endpoint_decimal():
    resolver = DockerComposeNetworkResolver()
    info = _service_info_with_secondary({"bgp_c": "10.0.0.2"})
    placeholder = _placeholder_with_secondary("bgp_c", NetworkFormat.DECIMAL)
    assert resolver._generate_resolved_value(placeholder, info) == "167772162"


def test_generate_resolved_value_unknown_secondary_raises():
    from panther.core.exceptions import ServiceResolutionException

    resolver = DockerComposeNetworkResolver()
    info = _service_info_with_secondary({"bgp_c": "10.0.0.2"})
    placeholder = _placeholder_with_secondary("bgp_d", NetworkFormat.HEX)
    with pytest.raises(ServiceResolutionException, match="bgp_d"):
        resolver._generate_resolved_value(placeholder, info)


def test_generate_resolved_value_primary_path_unchanged():
    """When placeholder.secondary_name is None, behavior must match pre-B.3 (resolve_hostname call)."""
    resolver = DockerComposeNetworkResolver()
    info = NetworkServiceInfo(service_name="ivy_tester", ip_address="172.19.0.3")
    placeholder = PlaceholderInfo(
        service="ivy_tester",
        attribute=NetworkAttribute.IP,
        format_type=NetworkFormat.HEX,
        raw_placeholder="@{ivy_tester:ip:hex}",
    )
    result = resolver._generate_resolved_value(placeholder, info)
    assert result == "$(resolve_hostname ivy_tester hex)"
