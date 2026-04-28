"""
Topology Service - Transforms experiment config into graph data model
for visual topology representation.
"""
import logging
from typing import Dict, List, Any, Tuple, Optional

logger = logging.getLogger(__name__)


class TopologyService:
    """Service to convert experiment configuration to graph topology model."""

    # Color coding for different service types
    NODE_COLORS = {
        "IUT": "#22c55e",      # Green
        "TESTERS": "#3b82f6",  # Blue
        "default": "#6b7280"   # Grey
    }

    # Symbol codes for ECharts
    NODE_SHAPES = {
        "server": "circle",
        "client": "roundRect"
    }

    def parse_config_to_graph(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parse full experiment config into complete graph data structure.
        
        Returns structure compatible with ECharts graph series:
        {
            "tests": [
                {
                    "name": "Test name",
                    "nodes": [...],
                    "edges": [...],
                    "groups": [...]
                },
                ...
            ],
            "aggregated": {
                "nodes": [...],
                "edges": [...],
                "groups": [...]
            }
        }
        """
        tests = config.get("tests", [])
        result = {"tests": [], "aggregated": None}

        for test_idx, test in enumerate(tests):
            test_graph = self._parse_single_test(test, test_idx)
            result["tests"].append(test_graph)

        # Create aggregated view across all tests
        result["aggregated"] = self._create_aggregated_view(result["tests"])

        return result

    def _create_aggregated_view(self, all_tests: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create aggregated view combining all services across all tests."""
        unique_services = {}
        unique_connections = {}
        network_environments = set()

        # Collect all unique services and connections
        for test in all_tests:
            network_environments.add(test["network_type"])
            
            for node in test["nodes"]:
                service_id = node["id"]
                if service_id not in unique_services:
                    unique_services[service_id] = node.copy()
                    unique_services[service_id]["test_count"] = 1
                    unique_services[service_id]["networks"] = {test["network_type"]}
                    unique_services[service_id]["execution_envs"] = set()
                else:
                    unique_services[service_id]["test_count"] += 1
                    unique_services[service_id]["networks"].add(test["network_type"])

            for env in test["execution_environment"]:
                for node in test["nodes"]:
                    unique_services[node["id"]]["execution_envs"].add(env["type"])

            for edge in test["edges"]:
                conn_key = f"{edge['source']}->{edge['target']}"
                if conn_key not in unique_connections:
                    unique_connections[conn_key] = edge.copy()
                    unique_connections[conn_key]["count"] = 1
                else:
                    unique_connections[conn_key]["count"] += 1

        # Convert sets to lists for JSON serialization
        nodes = list(unique_services.values())
        for node in nodes:
            node["networks"] = list(node["networks"])
            node["execution_envs"] = list(node["execution_envs"])
            node["name"] = f"{node['name']}\n×{node['test_count']}"

        edges = list(unique_connections.values())
        for edge in edges:
            edge["lineStyle"]["width"] = 1.5 + (edge["count"] * 0.5)
            edge["name"] = f"{edge['protocol']} ×{edge['count']}"

        return {
            "name": "Full Config Overview",
            "nodes": nodes,
            "edges": edges,
            "network_types": list(network_environments),
            "total_tests": len(all_tests),
            "unique_services": len(nodes),
            "unique_connections": len(edges)
        }

    def _parse_single_test(self, test: Dict[str, Any], test_index: int) -> Dict[str, Any]:
        """Parse a single test case into nodes, edges and groups."""
        services = test.get("services", {})
        network_env = test.get("network_environment", {})

        nodes = []
        edges = []

        # Extract service nodes
        for service_id, service_data in services.items():
            node = self._create_node(service_id, service_data)
            nodes.append(node)

        # Extract connections between services
        edges = self._extract_connections(services)

        # Create network group
        group = self._create_network_group(network_env)

        return {
            "name": test.get("name", f"Test {test_index + 1}"),
            "index": test_index,
            "nodes": nodes,
            "edges": edges,
            "group": group,
            "network_type": network_env.get("type", "unknown"),
            "iterations": test.get("iterations", 1),
            "execution_environment": test.get("execution_environment", [])
        }

    def _create_node(self, service_id: str, service_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a graph node from service definition."""
        implementation = service_data.get("implementation", {})
        protocol = service_data.get("protocol", {})

        impl_type = implementation.get("type", "default")
        role = protocol.get("role", "unknown")
        protocol_name = protocol.get("name", "")
        protocol_version = protocol.get("version", "")

        node = {
            "id": service_id,
            "name": service_data.get("name", service_id),
            "category": impl_type,
            "role": role,
            "protocol": protocol_name,
            "protocol_version": protocol_version,
            "timeout": service_data.get("timeout", None),
            "ports": service_data.get("ports", []),
            "has_certificates": service_data.get("generate_new_certificates", False),
            "target": protocol.get("target", None),
            
            # ECharts specific properties
            "symbolSize": self._calculate_node_size(service_data),
            "itemStyle": {
                "color": self.NODE_COLORS.get(impl_type, self.NODE_COLORS["default"])
            },
            "symbol": self.NODE_SHAPES.get(role, "circle"),
            
            # Tooltip content
            "tooltip": self._build_node_tooltip(service_id, service_data)
        }

        return node

    def _extract_connections(self, services: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract connection edges between services based on target references."""
        edges = []
        service_ids = set(services.keys())

        for source_id, service_data in services.items():
            protocol = service_data.get("protocol", {})
            target_id = protocol.get("target")

            if target_id and target_id in service_ids:
                edge = {
                    "source": source_id,
                    "target": target_id,
                    "protocol": protocol.get("name", ""),
                    "protocol_version": protocol.get("version", ""),
                    "lineStyle": {
                        "width": 2 + len(service_data.get("ports", [])),
                        "curveness": 0.1
                    },
                    "label": {
                        "show": True,
                        "formatter": protocol.get("name", "").upper()
                    }
                }
                edges.append(edge)

        return edges

    def _create_network_group(self, network_env: Dict[str, Any]) -> Dict[str, Any]:
        """Create network environment group metadata."""
        network_type = network_env.get("type", "unknown")
        
        group = {
            "type": network_type,
            "properties": {}
        }

        if network_type == "shadow_ns":
            network = network_env.get("network", {})
            group["properties"] = {
                "latency": network.get("latency"),
                "jitter": network.get("jitter"),
                "packet_loss": network.get("packet_loss"),
                "stop_time": network_env.get("general", {}).get("stop_time")
            }

        return group

    def _calculate_node_size(self, service_data: Dict[str, Any]) -> int:
        """Calculate node size based on number of ports and complexity."""
        base_size = 40
        port_count = len(service_data.get("ports", []))
        return min(70, base_size + port_count * 3)

    def _build_node_tooltip(self, service_id: str, data: Dict[str, Any]) -> str:
        """Build HTML tooltip content for node."""
        impl = data.get("implementation", {})
        proto = data.get("protocol", {})
        
        lines = [
            f"<b>{data.get('name', service_id)}</b>",
            f"Type: {impl.get('type', 'N/A')}",
            f"Implementation: {impl.get('name', 'N/A')}",
            f"Protocol: {proto.get('name', 'N/A')} {proto.get('version', '')}",
            f"Role: {proto.get('role', 'N/A')}",
            f"Timeout: {data.get('timeout', 'N/A')}s",
            f"Ports: {len(data.get('ports', []))}"
        ]

        if data.get("generate_new_certificates"):
            lines.append("🔒 Certificates enabled")
            
        if proto.get("target"):
            lines.append(f"→ Target: {proto.get('target')}")

        return "<br>".join(lines)

    def get_scaling_factors(self, node_count: int) -> Dict[str, float]:
        """
        Return scaling factors based on number of nodes to ensure
        diagram always fits and remains readable.
        """
        if node_count <= 4:
            return {"node_scale": 1.2, "label_font": 14, "edge_width": 2.5}
        elif node_count <= 8:
            return {"node_scale": 1.0, "label_font": 12, "edge_width": 2.0}
        elif node_count <= 12:
            return {"node_scale": 0.85, "label_font": 11, "edge_width": 1.5}
        else:
            return {"node_scale": 0.7, "label_font": 10, "edge_width": 1.0}


# Singleton instance for API usage
_topology_service_instance = None


def get_topology_service() -> TopologyService:
    """Get or create singleton TopologyService instance."""
    global _topology_service_instance
    if _topology_service_instance is None:
        _topology_service_instance = TopologyService()
    return _topology_service_instance
