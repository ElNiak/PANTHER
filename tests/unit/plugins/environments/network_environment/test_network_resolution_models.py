import pytest

from panther.config.core.models.network_resolution import NetworkServiceInfo


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
