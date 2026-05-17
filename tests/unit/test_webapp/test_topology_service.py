"""Unit tests for topology graph generation logic."""

import pytest

from panther.webapp.services.topology_service import TopologyService


def _experiment_from_tests(*tests):
    return {"tests": list(tests)}


@pytest.mark.unit
def test_server_only_creates_single_node_no_edges(topology_2_service):
    service = TopologyService()
    server_only_test = {
        **topology_2_service,
        "services": {
            "picoquic_server": topology_2_service["services"]["picoquic_server"],
        },
    }

    graph = service.parse_config_to_graph(_experiment_from_tests(server_only_test))
    test_graph = graph["tests"][0]

    assert len(test_graph["nodes"]) == 1
    assert test_graph["nodes"][0]["id"] == "picoquic_server"
    assert test_graph["nodes"][0]["role"] == "server"
    assert test_graph["nodes"][0]["symbol"] == "circle"
    assert len(test_graph["edges"]) == 0


@pytest.mark.unit
def test_server_and_client_create_directed_edge(topology_2_service):
    service = TopologyService()
    graph = service.parse_config_to_graph(_experiment_from_tests(topology_2_service))
    test_graph = graph["tests"][0]

    node_ids = {n["id"] for n in test_graph["nodes"]}
    assert node_ids == {"picoquic_server", "picoquic_client"}

    client = next(n for n in test_graph["nodes"] if n["id"] == "picoquic_client")
    assert client["role"] == "client"
    assert client["symbol"] == "roundRect"

    assert len(test_graph["edges"]) == 1
    edge = test_graph["edges"][0]
    assert edge["source"] == "picoquic_client"
    assert edge["target"] == "picoquic_server"
    assert edge["protocol"] == "quic"
    assert edge["protocol_version"] == "rfc9000"


@pytest.mark.unit
def test_missing_target_creates_no_edge(topology_2_service):
    service = TopologyService()
    broken_target = {
        **topology_2_service,
        "services": {
            **topology_2_service["services"],
            "picoquic_client": {
                **topology_2_service["services"]["picoquic_client"],
                "protocol": {
                    **topology_2_service["services"]["picoquic_client"]["protocol"],
                    "target": "does_not_exist",
                },
            },
        },
    }

    graph = service.parse_config_to_graph(_experiment_from_tests(broken_target))
    test_graph = graph["tests"][0]

    assert len(test_graph["nodes"]) == 2
    assert len(test_graph["edges"]) == 0


@pytest.mark.unit
def test_aggregated_dedup_counts_and_env_merge(topology_2_service):
    service = TopologyService()
    second_test = {
        **topology_2_service,
        "name": "same_services_other_env",
        "network_environment": {"type": "shadow_ns"},
        "execution_environment": [{"type": "strace"}],
    }
    first_test = {
        **topology_2_service,
        "name": "same_services_base",
        "network_environment": {"type": "docker_compose"},
        "execution_environment": [{"type": "gperf_cpu"}],
    }

    graph = service.parse_config_to_graph(
        _experiment_from_tests(first_test, second_test)
    )
    aggregated = graph["aggregated"]

    assert aggregated["total_tests"] == 2
    assert aggregated["unique_services"] == 2
    assert aggregated["unique_connections"] == 1
    assert set(aggregated["network_types"]) == {"docker_compose", "shadow_ns"}

    by_id = {n["id"]: n for n in aggregated["nodes"]}
    assert by_id["picoquic_server"]["test_count"] == 2
    assert by_id["picoquic_client"]["test_count"] == 2
    assert set(by_id["picoquic_server"]["execution_envs"]) == {"gperf_cpu", "strace"}
    assert set(by_id["picoquic_client"]["execution_envs"]) == {"gperf_cpu", "strace"}

    edge = aggregated["edges"][0]
    assert edge["count"] == 2
    assert edge["name"].endswith("×2")


@pytest.mark.unit
def test_per_test_isolation_keeps_indexes(topology_2_service, topology_3_service):
    service = TopologyService()
    graph = service.parse_config_to_graph(
        _experiment_from_tests(topology_2_service, topology_3_service)
    )

    first = graph["tests"][0]
    second = graph["tests"][1]

    assert first["index"] == 0
    assert second["index"] == 1

    assert {n["id"] for n in first["nodes"]} == {
        "picoquic_server",
        "picoquic_client",
    }
    assert {n["id"] for n in second["nodes"]} == {
        "picoquic_server",
        "picoquic_client",
        "ivy_tester",
    }

    assert len(first["edges"]) == 1
    assert len(second["edges"]) == 2
