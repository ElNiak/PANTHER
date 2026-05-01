"""Tests for the network resolution interface (context builder)."""

import pytest

pytestmark = [pytest.mark.unit]


class _FakeManager:
    """
    Minimal stand-in for a service manager carrying just the attributes.

    `create_resolution_context` reads via `getattr`.
    """

    def __init__(self, protocol_role=None, secondary_endpoints=None):
        self.protocol_role = protocol_role
        self.secondary_endpoints = secondary_endpoints or {}


def test_create_resolution_context_propagates_secondary_endpoints():
    """create_resolution_context must copy secondary_endpoints from manager → NetworkServiceInfo."""
    from panther.plugins.environments.network_environment.network_resolution_interface import (
        INetworkResolver,
    )

    # Build a minimal concrete subclass so we can call the inherited method.
    class _Resolver(INetworkResolver):
        def resolve_network_placeholders(self, *_args, **_kwargs):
            return []

        def get_service_ip(self, *_args, **_kwargs):
            return ""

        def get_service_info(self, *_args, **_kwargs):
            return None

        def populate_service_network_info(self, *_args, **_kwargs):
            pass

    resolver = _Resolver()
    manager = _FakeManager(
        protocol_role="server",
        secondary_endpoints={"bgp_c": "10.0.0.2"},
    )
    ctx = resolver.create_resolution_context(
        environment_type="docker_compose",
        service_managers={"ivy_tester": manager},
    )

    info = ctx.get_service_info("ivy_tester")
    assert info is not None
    assert info.protocol_role == "server"
    assert info.secondary_endpoints == {"bgp_c": "10.0.0.2"}


def test_create_resolution_context_default_secondary_endpoints_empty():
    """Manager without secondary_endpoints should yield empty dict on NetworkServiceInfo."""
    from panther.plugins.environments.network_environment.network_resolution_interface import (
        INetworkResolver,
    )

    class _Resolver(INetworkResolver):
        def resolve_network_placeholders(self, *_args, **_kwargs):
            return []

        def get_service_ip(self, *_args, **_kwargs):
            return ""

        def get_service_info(self, *_args, **_kwargs):
            return None

        def populate_service_network_info(self, *_args, **_kwargs):
            pass

    resolver = _Resolver()

    # Manager with no secondary_endpoints attr (legacy manager / shadow / localhost case)
    class _BareManager:
        protocol_role = "client"

    ctx = resolver.create_resolution_context(
        environment_type="localhost",
        service_managers={"impl": _BareManager()},
    )
    info = ctx.get_service_info("impl")
    assert info is not None
    assert info.secondary_endpoints == {}
