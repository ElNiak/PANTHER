"""Unit tests for topology renderer node-click navigation behavior."""

from types import SimpleNamespace
from urllib.parse import parse_qs, urlparse

import pytest
from nicegui import app

from panther.webapp.components.topology.topology_renderer import TopologyRenderer


def _event_for_node(node_id: str, node_name: str):
    payload = {"data": {"id": node_id, "name": node_name}}
    return SimpleNamespace(args=[payload])


def _setup_js_capture(monkeypatch):
    js_calls = []
    monkeypatch.setattr(
        "panther.webapp.components.topology.topology_renderer.ui.run_javascript",
        lambda js: js_calls.append(js),
    )
    return js_calls


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

    js_calls = _setup_js_capture(monkeypatch)
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

    js_calls = _setup_js_capture(monkeypatch)
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


@pytest.mark.unit
def test_navigation_javascript_url_encodes_query_params(monkeypatch):
    renderer = TopologyRenderer()
    renderer.current_config_path = "experiment-config/base/config with spaces.yaml"
    renderer.current_loaded_config = {
        "tests": [{"name": "T1", "services": {"client service": {}}}]
    }
    renderer.graph_data = {"tests": [{}]}
    js_calls = _setup_js_capture(monkeypatch)
    app.storage.general.clear()

    renderer._on_node_click(
        _event_for_node("client service", "Client Service\n×2"),
        is_aggregated=True,
    )

    assert app.storage.general["topology_nav"]["service_name"] == "Client Service"
    query_line = next(line for line in js_calls[0].splitlines() if "/config?" in line)
    url = query_line.split('"URL: ')[1].rstrip('";')
    query = parse_qs(urlparse(url).query)
    assert query["config_path"] == ["experiment-config/base/config with spaces.yaml"]
    assert query["service_id"] == ["client service"]
    assert query["service_name"] == ["Client Service"]


@pytest.mark.unit
def test_click_accepts_dict_style_event_payload(monkeypatch):
    renderer = TopologyRenderer()
    renderer.current_config_path = "experiment-config/base/dict.yaml"
    renderer.current_loaded_config = {
        "tests": [{"name": "T1", "services": {"svc_dict": {}}}]
    }
    renderer.graph_data = {"tests": [{}]}
    _setup_js_capture(monkeypatch)
    app.storage.general.clear()

    renderer._on_node_click(
        SimpleNamespace(args={"data": {"id": "svc_dict", "name": "Dict Service"}}),
        is_aggregated=True,
    )

    assert app.storage.general["topology_nav"]["service_id"] == "svc_dict"
    assert app.storage.general["topology_nav"]["service_name"] == "Dict Service"


@pytest.mark.unit
def test_build_echarts_options_preserves_graph_and_applies_scaling():
    renderer = TopologyRenderer()
    test_data = {
        "nodes": [
            {
                "id": "server",
                "name": "server",
                "symbolSize": 40,
                "tooltip": "server",
            },
            {
                "id": "client",
                "name": "client",
                "symbolSize": 50,
                "tooltip": "client",
            },
        ],
        "edges": [
            {
                "source": "client",
                "target": "server",
                "protocol": "quic",
            }
        ],
    }

    options = renderer._build_echarts_options(
        test_data,
        {"node_scale": 1.2, "label_font": 14, "edge_width": 2.5},
    )
    series = options["series"][0]

    assert series["type"] == "graph"
    assert series["layout"] == "force"
    assert series["roam"] is True
    assert series["draggable"] is True
    assert series["nodes"][0]["symbolSize"] == 48
    assert series["nodes"][1]["symbolSize"] == 60
    assert series["links"] == test_data["edges"]
    assert series["label"]["fontSize"] == 14
    assert series["lineStyle"]["width"] == 2.5
    assert series["edgeLabel"]["show"] is True


@pytest.mark.unit
def test_build_echarts_options_hides_edge_labels_for_dense_graph():
    renderer = TopologyRenderer()
    test_data = {
        "nodes": [{"id": "server", "name": "server", "symbolSize": 40}],
        "edges": [{"source": f"client_{idx}", "target": "server"} for idx in range(5)],
    }

    options = renderer._build_echarts_options(
        test_data,
        {"node_scale": 1.0, "label_font": 12, "edge_width": 2.0},
    )

    assert options["series"][0]["edgeLabel"]["show"] is False
