"""Regression tests for FRR BGP neighbour discovery.

The IUT's bgpd.conf needs the *peer's* address. `entrypoint.sh.jinja:470` writes
each service's address to ``/app/coordination/${SERVICE_NAME}_ip.txt``, but
``frr_bgp.py`` used to read a hardcoded ``ivy_tester_ip.txt``. Any experiment
whose tester service was named something else matched nothing, and the
``hostname -i`` fallback then returned the IUT's OWN address -- so FRR peered
with itself, looped on NOTIFICATION(2,2) Bad Peer AS [rfc4271:6.2], and the
tester was never contacted. The failure was silent because the fallback
succeeded.

Observed 2026-09-09 with a tester service named ``tester``::

    Generated bgpd.conf: router-id=172.18.0.2 neighbor=172.18.0.2

and after the fix, same config::

    Generated bgpd.conf: router-id=172.18.0.2 neighbor=172.18.0.3
"""

from __future__ import annotations

import pytest

from panther.plugins.services.iut.bgp.frr_bgp.frr_bgp import FrrBgpServiceManager


@pytest.fixture
def pre_run_script() -> str:
    """Return the bgpd.conf-generating pre-run command.

    Builds the manager without running ``__init__`` so the test exercises only
    command generation, not the plugin bootstrap.
    """
    manager = FrrBgpServiceManager.__new__(FrrBgpServiceManager)
    manager._build_template_context = lambda: {  # type: ignore[method-assign]
        "as_number": 2,
        "router_id": "172.18.0.2",
        "neighbor_ip": "172.18.0.3",
        "neighbor_as": 1,
        "hold_time": 180,
        "keepalive_time": 60,
        "listen_port": 179,
    }
    commands = manager.generate_pre_run_commands()
    script = next(c for c in commands if "bgpd.conf" in str(c))
    return str(script)


class TestFrrBgpPeerDiscovery:
    def test_does_not_hardcode_a_tester_service_name(self, pre_run_script: str) -> None:
        """The peer filename must be derived, never guessed."""
        assert "ivy_tester_ip.txt" not in pre_run_script

    def test_excludes_own_ip_file_when_selecting_peer(
        self, pre_run_script: str
    ) -> None:
        """Peer = the one *_ip.txt that is not ${SERVICE_NAME}_ip.txt."""
        assert "/app/coordination/*_ip.txt" in pre_run_script
        assert "/${SERVICE_NAME}_ip.txt$" in pre_run_script

    def test_refuses_to_self_peer_instead_of_falling_back(
        self, pre_run_script: str
    ) -> None:
        """No silent fallback to our own address; fail loudly instead.

        `hostname -i` was the old fallback and is what produced the self-peer.
        """
        assert "hostname -i" not in pre_run_script
        assert "refusing to self-peer" in pre_run_script
        assert "exit 1" in pre_run_script

    def test_guard_compares_neighbour_against_self(self, pre_run_script: str) -> None:
        """Even a populated peer file must not equal SELF_IP."""
        assert '"$NEIGHBOR_IP" = "$SELF_IP"' in pre_run_script

    def test_still_configures_neighbour_from_discovered_ip(
        self, pre_run_script: str
    ) -> None:
        """The happy path is unchanged: bgpd.conf is written with the peer."""
        assert "router bgp 2" in pre_run_script
        assert "remote-as 1" in pre_run_script
        assert "/etc/frr/bgpd.conf" in pre_run_script
