"""Tests for protocol config enums and constraints."""

import pytest

from panther.config.core.models.protocol import (
    ClientServerProtocolConfig,
    CongestionControl,
    HttpMethod,
    HttpVersion,
    PeerToPeerProtocolConfig,
    TlsVerifyMode,
)


class TestProtocolEnums:
    def test_http_method_valid(self):
        for val in ["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"]:
            assert HttpMethod(val).value == val

    def test_http_version_valid(self):
        for val in ["1.0", "1.1", "2", "3"]:
            assert HttpVersion(val).value == val

    def test_tls_verify_mode_valid(self):
        for val in ["none", "optional", "required"]:
            assert TlsVerifyMode(val).value == val

    def test_congestion_control_valid(self):
        for val in ["reno", "cubic", "bbr", "bbr2"]:
            assert CongestionControl(val).value == val

    def test_config_accepts_string_method(self):
        c = ClientServerProtocolConfig(name="http", method="POST")
        assert c.method == HttpMethod.POST


class TestProtocolConstraints:
    def test_initial_max_data_negative(self):
        with pytest.raises(Exception):
            ClientServerProtocolConfig(name="quic", initial_max_data=-1)

    def test_retry_count_too_high(self):
        with pytest.raises(Exception):
            ClientServerProtocolConfig(name="quic", retry_count=101)

    def test_max_peers_zero(self):
        with pytest.raises(Exception):
            PeerToPeerProtocolConfig(name="bt", max_peers=0)

    def test_ping_interval_zero(self):
        with pytest.raises(Exception):
            PeerToPeerProtocolConfig(name="bt", ping_interval=0)
