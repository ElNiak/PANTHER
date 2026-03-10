"""Tests for ServiceConfig.get_service_name and port operations."""

import pytest

from panther.config.core.models.service import ServiceConfig


@pytest.mark.unit
def test_get_service_name_returns_string():
    svc = ServiceConfig(
        implementation={"name": "picoquic", "type": "iut"},
        protocol={"name": "quic", "version": "rfc9000", "role": "server"},
    )
    assert svc.get_service_name() == "picoquic_server"


@pytest.mark.unit
def test_get_service_name_client():
    svc = ServiceConfig(
        implementation={"name": "aioquic", "type": "iut"},
        protocol={
            "name": "quic",
            "version": "rfc9000",
            "role": "client",
            "target": "server",
        },
    )
    assert svc.get_service_name() == "aioquic_client"


@pytest.mark.unit
def test_add_port_mapping_valid():
    svc = ServiceConfig(
        implementation={"name": "picoquic", "type": "iut"},
        protocol={"name": "quic", "version": "rfc9000", "role": "server"},
    )
    svc.add_port_mapping(8080, 80)
    assert "8080:80" in svc.ports


@pytest.mark.unit
def test_add_port_mapping_invalid():
    svc = ServiceConfig(
        implementation={"name": "picoquic", "type": "iut"},
        protocol={"name": "quic", "version": "rfc9000", "role": "server"},
    )
    with pytest.raises(ValueError, match="1-65535"):
        svc.add_port_mapping(0, 80)
    with pytest.raises(ValueError, match="1-65535"):
        svc.add_port_mapping(8080, 70000)
