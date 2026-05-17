"""Unit tests for topology renderer node-click navigation behavior."""

from types import SimpleNamespace

import pytest
from nicegui import app

from panther.webapp.components.topology.topology_renderer import TopologyRenderer


def _event_for_node(node_id: str, node_name: str):
    payload = {"data": {"id": node_id, "name": node_name}}
    return SimpleNamespace(args=[payload])


@pytest.mark.unit
def test_click_in_aggregated_mode_stores_first_matching_test(monkeypatch):
    renderer = TopologyRenderer()
    renderer.current_config_path = "experiment-config/base/test.yaml"
    renderer.current_loaded_config = {
        "tests": [
            {"name": "T1", "services": {"svc_a": {}, "svc_b": {}}},
            {"name": "T2", "services": {"svc_a": {}, "svc_c": {}}},
        ]
    }
    renderer.graph_data = {"tests": [{}]}

    js_calls = []
    nav_storage = {}
    monkeypatch.setattr(
        "panther.webapp.components.topology.topology_renderer.ui.run_javascript",
        lambda js: js_calls.append(js),
    )
    nav_storage = app.storage.general
    nav_storage.clear()

    renderer._on_node_click(
        _event_for_node("svc_a", "svc_a\n×2"),
        is_aggregated=True,
    )

    assert (
        nav_storage["topology_nav"]["config_path"] == "experiment-config/base/test.yaml"
    )
    assert nav_storage["topology_nav"]["test_index"] == "0"
    assert nav_storage["topology_nav"]["service_id"] == "svc_a"
    assert nav_storage["topology_nav"]["service_name"] == "svc_a"
    assert nav_storage["topology_nav"]["source"] == "topology"
    assert js_calls, "Expected client-side navigation JavaScript to be emitted"


@pytest.mark.unit
def test_click_in_per_test_mode_uses_override_index(monkeypatch):
    renderer = TopologyRenderer()
    renderer.current_config_path = "experiment-config/base/per_test.yaml"
    renderer.current_loaded_config = {
        "tests": [
            {"name": "T1", "services": {"svc_server": {}, "svc_client": {}}},
            {"name": "T2", "services": {"svc_server_2": {}, "svc_client_2": {}}},
        ]
    }
    renderer.graph_data = {"tests": [{}, {}]}
    renderer.current_test_index = 0

    js_calls = []
    nav_storage = {}
    monkeypatch.setattr(
        "panther.webapp.components.topology.topology_renderer.ui.run_javascript",
        lambda js: js_calls.append(js),
    )
    nav_storage = app.storage.general
    nav_storage.clear()

    renderer._on_node_click(
        _event_for_node("svc_client_2", "svc_client_2"),
        test_index_override=1,
        is_aggregated=False,
    )

    assert nav_storage["topology_nav"]["test_index"] == "1"
    assert nav_storage["topology_nav"]["service_id"] == "svc_client_2"
    assert nav_storage["topology_nav"]["service_name"] == "svc_client_2"
    assert nav_storage["topology_nav"]["source"] == "topology"
    assert js_calls, "Expected client-side navigation JavaScript to be emitted"


@pytest.mark.unit
def test_click_in_aggregated_mode_defaults_to_test_zero_for_unknown_service(
    monkeypatch,
):
    renderer = TopologyRenderer()
    renderer.current_config_path = "experiment-config/base/unknown.yaml"
    renderer.current_loaded_config = {
        "tests": [
            {"name": "T1", "services": {"svc_a": {}}},
            {"name": "T2", "services": {"svc_b": {}}},
        ]
    }
    renderer.graph_data = {"tests": [{}, {}]}

    monkeypatch.setattr(
        "panther.webapp.components.topology.topology_renderer.ui.run_javascript",
        lambda js: None,
    )
    nav_storage = app.storage.general
    nav_storage.clear()

    renderer._on_node_click(
        _event_for_node("does_not_exist", "does_not_exist"),
        is_aggregated=True,
    )

    assert nav_storage["topology_nav"]["test_index"] == "0"
