import pytest

from panther.config.core.models.network_resolution import (
    NetworkAttribute,
    NetworkFormat,
    NetworkServiceInfo,
    PlaceholderInfo,
)


@pytest.mark.unit
def test_network_service_info_secondary_endpoints_default_empty():
    info = NetworkServiceInfo(service_name="ivy_tester", ip_address="172.19.0.3")
    assert info.secondary_endpoints == {}


@pytest.mark.unit
def test_network_service_info_secondary_endpoints_round_trip():
    info = NetworkServiceInfo(
        service_name="ivy_tester",
        ip_address="172.19.0.3",
        secondary_endpoints={"bgp_c": "10.0.0.2"},
    )
    payload = info.model_dump()
    rebuilt = NetworkServiceInfo.model_validate(payload)
    assert rebuilt.secondary_endpoints == {"bgp_c": "10.0.0.2"}


@pytest.mark.unit
def test_network_service_info_impl_pool_default_none():
    info = NetworkServiceInfo(service_name="ivy_tester", ip_address="172.19.0.3")
    assert info.impl_pool is None


@pytest.mark.unit
def test_network_service_info_impl_pool_round_trip():
    info = NetworkServiceInfo(
        service_name="ivy_tester",
        ip_address="172.19.0.3",
        impl_pool=["frr", "gobgp"],
    )
    rebuilt = NetworkServiceInfo.model_validate(info.model_dump())
    assert rebuilt.impl_pool == ["frr", "gobgp"]


@pytest.mark.unit
def test_placeholder_info_secondary_name_default_none():
    info = PlaceholderInfo(
        service="ivy_tester",
        attribute=NetworkAttribute.IP,
        format_type=NetworkFormat.HEX,
        raw_placeholder="@{ivy_tester:ip:hex}",
    )
    assert info.secondary_name is None


@pytest.mark.unit
def test_placeholder_info_secondary_name_round_trip():
    info = PlaceholderInfo(
        service="ivy_tester",
        attribute=NetworkAttribute.IP,
        format_type=NetworkFormat.HEX,
        secondary_name="bgp_c",
        raw_placeholder="@{ivy_tester:ip[bgp_c]:hex}",
    )
    rebuilt = PlaceholderInfo.model_validate(info.model_dump())
    assert rebuilt.secondary_name == "bgp_c"
