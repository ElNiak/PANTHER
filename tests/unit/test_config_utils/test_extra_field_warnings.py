"""Tests for extra field warning detection in builders."""

import pytest

from panther.config.core.components.builders import ServiceBuilder


class TestServiceBuilderExtraFieldWarnings:
    def test_protocol_extra_field_warns(self):
        builder = ServiceBuilder()
        service_dict = {
            "implementation": {"name": "picoquic", "type": "iut"},
            "protocol": {"name": "quic", "role": "server", "caca2": True},
            "ports": ["4443:4443"],
        }
        service = builder.build(service_dict, auto_fix=True)
        warnings = builder.context.warnings
        assert any("caca2" in w for w in warnings)

    def test_service_extra_field_warns(self):
        builder = ServiceBuilder()
        service_dict = {
            "implementation": {"name": "picoquic", "type": "iut"},
            "protocol": {"name": "quic", "role": "server"},
            "ports": ["4443:4443"],
            "caca": True,
        }
        service = builder.build(service_dict, auto_fix=True)
        warnings = builder.context.warnings
        assert any("caca" in w for w in warnings)

    def test_no_warning_for_valid_fields(self):
        builder = ServiceBuilder()
        service_dict = {
            "implementation": {"name": "picoquic", "type": "iut"},
            "protocol": {"name": "quic", "role": "server"},
            "ports": ["4443:4443"],
            "timeout": 120,
        }
        service = builder.build(service_dict, auto_fix=True)
        warnings = [w for w in builder.context.warnings if "Unknown field" in w]
        assert warnings == []
