"""Topology Service — Convert config files to graph format for React Flow.

This service handles conversion between PANTHER YAML configuration files
and the graph format used by the React Flow topology editor.
"""

import logging
import math
import yaml
from pathlib import Path
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


class TopologyService:
    """Service for converting experiment configs to topology graphs."""

    def __init__(self):
        """Initialize topology service."""
        # Locate experiment config directory relative to project root
        project_root = Path(__file__).parent.parent.parent.parent
        self.config_dir = project_root / "experiment-config" / "base"

    def list_config_files(self) -> List[str]:
        """List available YAML configuration files.

        Returns:
            List of config filenames
        """
        try:
            files = []
            for ext in ["*.yaml", "*.yml"]:
                files.extend(self.config_dir.glob(ext))
            
            return sorted([f.name for f in files])
        except Exception as e:
            logger.error("Failed to list config files: %s", e)
            return []

    def load_config(self, filename: str) -> Dict[str, Any]:
        """Load and parse a YAML config file.

        Args:
            filename: Name of the config file to load

        Returns:
            Parsed config dictionary
        """
        try:
            file_path = self.config_dir / filename
            with open(file_path, 'r') as f:
                config = yaml.safe_load(f)
            return config
        except Exception as e:
            logger.error("Failed to load config %s: %s", filename, e)
            return {}

    def config_to_graph(self, config: Dict[str, Any]) -> Dict[str, List[Any]]:
        """Convert experiment config to React Flow graph format.

        Args:
            config: Parsed experiment configuration

        Returns:
            Dictionary with 'nodes' and 'edges' lists
        """
        nodes = []
        edges = []

        try:
            # Extract first test (most configs have one test)
            tests = config.get('tests', [])
            if not tests:
                return {"nodes": [], "edges": []}
            
            test = tests[0]
            services = test.get('services', {})

            # Positioning strategy - arrange nodes in a grid
            node_positions = self._calculate_node_positions(len(services))

            # Create nodes from services
            for idx, (service_name, service_config) in enumerate(services.items()):
                implementation = service_config.get('implementation', {})
                protocol = service_config.get('protocol', {})

                node = {
                    'id': service_name,
                    'type': 'service',
                    'position': node_positions[idx],
                    'data': {
                        'label': service_name,
                        'type': implementation.get('type', 'iut'),
                        'implementation': implementation.get('name', 'unknown'),
                        'protocol': protocol.get('name', 'unknown'),
                        'role': protocol.get('role', 'unknown'),
                    }
                }
                nodes.append(node)

                # Create edge from target reference
                target = protocol.get('target')
                if target and target in services:
                    edge = {
                        'id': f"{service_name}-{target}",
                        'source': service_name,
                        'target': target,
                        'label': f"{protocol.get('name', '')} {protocol.get('version', '')}".strip(),
                        'animated': True,
                        'style': {'stroke': '#2563eb', 'strokeWidth': 2}
                    }
                    edges.append(edge)

            # Add dependency edges
            for service_name, service_config in services.items():
                for dep in service_config.get('depends_on', []):
                    if dep in services and not any(e['id'] == f"dep-{service_name}-{dep}" for e in edges):
                        edge = {
                            'id': f"dep-{service_name}-{dep}",
                            'source': dep,
                            'target': service_name,
                            'label': "depends on",
                            'style': {'stroke': '#94a3b8', 'strokeWidth': 1, 'strokeDasharray': '5,5'}
                        }
                        edges.append(edge)

            return {
                'nodes': nodes,
                'edges': edges,
                'test_name': test.get('name', ''),
                'network_environment': test.get('network_environment', {}).get('type', 'unknown')
            }

        except Exception as e:
            logger.error("Failed to convert config to graph: %s", e)
            return {"nodes": [], "edges": []}

    def _calculate_node_positions(self, node_count: int) -> List[Dict[str, float]]:
        """Calculate positions for nodes in a circular layout.

        Args:
            node_count: Number of nodes to position

        Returns:
            List of {x, y} positions
        """
        positions = []
        center_x = 400
        center_y = 300
        radius = max(200, node_count * 50)

        for i in range(node_count):
            angle = (2 * 3.14159 * i) / node_count
            x = center_x + radius * math.cos(angle)
            y = center_y + radius * math.sin(angle)
            positions.append({'x': x, 'y': y})

        return positions


# Global service instance
_topology_service = None


def get_topology_service() -> TopologyService:
    """Get or create the global topology service instance."""
    global _topology_service
    if _topology_service is None:
        _topology_service = TopologyService()
    return _topology_service