"""TopologyEditor — vis.js Network graph for visual experiment topology.

Renders a `vis.js <https://visjs.github.io/vis-network/>`_ Network graph
inside a NiceGUI container, providing a visual representation of the
PANTHER (Protocol ANalysis and Testing Harness for Extensible Research)
experiment topology: IUT (Implementation Under Test) services, tester
services, and the protocol connections between them.

This module provides the **scaffold** — static graph rendering, Python-to-JS
data exchange, and click event callbacks.  The contributor builds interactive
features on top: palette sidebar with drag-and-drop node creation, edge
creation interactions, properties panel (click node to open a PydanticForm),
YAML export/import, validation (red borders, warnings), auto-layout, and
undo/redo.

Usage::

    from panther.webapp.components.topology_editor import TopologyEditor

    editor = TopologyEditor(
        nodes=[{"id": 1, "label": "picoquic", "group": "iut"}],
        edges=[{"from": 1, "to": 2, "label": "quic"}],
        on_node_click=lambda node_id, node_data: print(f"Clicked {node_id}"),
    )
    editor.set_graph(new_nodes, new_edges)
    graph = editor.get_graph()  # {"nodes": [...], "edges": [...]}
"""

from __future__ import annotations

import json
import logging
from typing import Any, Callable

from nicegui import ui

logger = logging.getLogger(__name__)

# vis.js CDN URLs (vis-network standalone, no vis-data needed for basic usage)
_VIS_CSS = "https://unpkg.com/vis-network@9.1.9/dist/dist/vis-network.min.css"
_VIS_JS = "https://unpkg.com/vis-network@9.1.9/dist/vis-network.min.js"

# Node group styles for different service types
DEFAULT_GROUPS = {
    "iut": {"color": {"background": "#4CAF50", "border": "#388E3C"}, "shape": "box"},
    "tester": {
        "color": {"background": "#2196F3", "border": "#1565C0"},
        "shape": "diamond",
    },
    "environment": {
        "color": {"background": "#FF9800", "border": "#E65100"},
        "shape": "ellipse",
    },
}


class TopologyEditor:
    """vis.js Network graph rendered inside a NiceGUI container.

    The scaffold provides:

    - Static graph rendering with group-based node styling (IUT = green
      box, tester = blue diamond, environment = orange ellipse).
    - ``set_graph()`` / ``get_graph()`` for Python-to-JavaScript data
      exchange.
    - ``on_node_click`` / ``on_edge_click`` event callbacks bridged from
      JavaScript custom events to Python callables.

    Planned interactive features (to be built by the contributor):

    - Palette sidebar with drag-and-drop node creation.
    - Edge creation interactions.
    - Properties panel (click node to open a ``PydanticForm``).
    - YAML export/import.
    - Validation (red borders, warnings).
    - Auto-layout, undo/redo.

    Args:
        nodes: Initial node dicts for vis.js (each must have ``id``; may
            have ``label``, ``group``, etc.).
        edges: Initial edge dicts for vis.js (each has ``from``, ``to``,
            and optionally ``label``).
        on_node_click: Callback receiving ``(node_id, node_data)`` when a
            node is clicked.
        on_edge_click: Callback receiving ``(edge_id, edge_data)`` when an
            edge is clicked.
        height: CSS height for the graph container.
        options: Extra vis.js Network options merged into the defaults.

    Example::

        editor = TopologyEditor(
            nodes=[{"id": 1, "label": "picoquic", "group": "iut"}],
            edges=[{"from": 1, "to": 2, "label": "quic"}],
        )
    """

    _head_loaded = False

    def __init__(
        self,
        nodes: list[dict[str, Any]] | None = None,
        edges: list[dict[str, Any]] | None = None,
        on_node_click: Callable[[int | str, dict], None] | None = None,
        on_edge_click: Callable[[str, dict], None] | None = None,
        height: str = "500px",
        options: dict[str, Any] | None = None,
    ) -> None:
        """Initialise the topology editor with optional graph data and callbacks."""
        self._nodes = nodes or []
        self._edges = edges or []
        self._on_node_click = on_node_click
        self._on_edge_click = on_edge_click
        self._options = options or {}

        # Load vis.js from CDN (once per app)
        if not TopologyEditor._head_loaded:
            ui.add_head_html(
                f'<link rel="stylesheet" href="{_VIS_CSS}">\n'
                f'<script src="{_VIS_JS}"></script>'
            )
            TopologyEditor._head_loaded = True

        # Create the container element
        self._container = (
            ui.element("div")
            .classes("w-full")
            .style(f"height: {height}; border: 1px solid #ccc; border-radius: 4px;")
        )
        self._container_id = f"topology-{id(self)}"
        self._container._props["id"] = self._container_id

        # Wire up event handlers via JavaScript bridge
        if on_node_click:
            self._container.on(
                "node-click",
                lambda e: self._handle_node_click(e),
            )
        if on_edge_click:
            self._container.on(
                "edge-click",
                lambda e: self._handle_edge_click(e),
            )

        # Initialize the network after the element is mounted
        ui.timer(0.1, self._init_network, once=True)

    def _init_network(self) -> None:
        """Initialize the vis.js Network in the browser."""
        nodes_json = json.dumps(self._nodes)
        edges_json = json.dumps(self._edges)
        options_json = json.dumps(
            {
                "groups": DEFAULT_GROUPS,
                "physics": {"enabled": True, "stabilization": {"iterations": 100}},
                "interaction": {"hover": True, "selectConnectedEdges": False},
                "edges": {
                    "arrows": {"to": {"enabled": True}},
                    "font": {"size": 12, "align": "middle"},
                    "smooth": {"type": "cubicBezier"},
                },
                "nodes": {
                    "font": {"size": 14},
                    "borderWidth": 2,
                },
                **self._options,
            }
        )

        js = f"""
        (function() {{
            const container = document.getElementById('{self._container_id}');
            if (!container || typeof vis === 'undefined') {{
                console.error('TopologyEditor: container or vis.js not found');
                return;
            }}
            const nodes = new vis.DataSet({nodes_json});
            const edges = new vis.DataSet({edges_json});
            const options = {options_json};
            const network = new vis.Network(container, {{nodes, edges}}, options);

            // Store references for later access
            container._visNetwork = network;
            container._visNodes = nodes;
            container._visEdges = edges;

            // Event: node click
            network.on('click', function(params) {{
                if (params.nodes.length > 0) {{
                    const nodeId = params.nodes[0];
                    const nodeData = nodes.get(nodeId);
                    container.dispatchEvent(new CustomEvent('node-click', {{
                        detail: {{id: nodeId, data: nodeData}},
                        bubbles: true
                    }}));
                }} else if (params.edges.length > 0) {{
                    const edgeId = params.edges[0];
                    const edgeData = edges.get(edgeId);
                    container.dispatchEvent(new CustomEvent('edge-click', {{
                        detail: {{id: edgeId, data: edgeData}},
                        bubbles: true
                    }}));
                }}
            }});

            // Fit the view after stabilization
            network.once('stabilizationIterationsDone', function() {{
                network.fit({{animation: true}});
            }});
        }})();
        """
        ui.run_javascript(js)

    def _handle_node_click(self, e) -> None:
        """Handle node click event from JavaScript."""
        if self._on_node_click and hasattr(e, "args") and e.args:
            detail = e.args.get("detail", {}) if isinstance(e.args, dict) else {}
            self._on_node_click(detail.get("id"), detail.get("data", {}))

    def _handle_edge_click(self, e) -> None:
        """Handle edge click event from JavaScript."""
        if self._on_edge_click and hasattr(e, "args") and e.args:
            detail = e.args.get("detail", {}) if isinstance(e.args, dict) else {}
            self._on_edge_click(detail.get("id"), detail.get("data", {}))

    def set_graph(self, nodes: list[dict], edges: list[dict]) -> None:
        """Replace the entire graph with new nodes and edges via JavaScript."""
        self._nodes = nodes
        self._edges = edges
        nodes_json = json.dumps(nodes)
        edges_json = json.dumps(edges)
        js = f"""
        (function() {{
            const container = document.getElementById('{self._container_id}');
            if (!container || !container._visNodes) return;
            container._visNodes.clear();
            container._visEdges.clear();
            container._visNodes.add({nodes_json});
            container._visEdges.add({edges_json});
            container._visNetwork.fit({{animation: true}});
        }})();
        """
        ui.run_javascript(js)

    def get_graph(self) -> dict[str, list[dict]]:
        """Return the current graph data (Python-side cache).

        For the live browser state, use ``get_graph_async()``.
        """
        return {"nodes": list(self._nodes), "edges": list(self._edges)}

    async def get_graph_async(self) -> dict[str, list[dict]]:
        """Fetch the current graph data from the browser."""
        js = f"""
        (function() {{
            const container = document.getElementById('{self._container_id}');
            if (!container || !container._visNodes) return {{nodes: [], edges: []}};
            return {{
                nodes: container._visNodes.get(),
                edges: container._visEdges.get()
            }};
        }})();
        """
        result = await ui.run_javascript(js)
        if isinstance(result, dict):
            self._nodes = result.get("nodes", [])
            self._edges = result.get("edges", [])
            return result
        return {"nodes": [], "edges": []}
