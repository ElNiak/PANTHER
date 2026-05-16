"""
Topology Renderer - Native NiceGUI ECharts implementation
for experiment topology visualization.
"""
import logging
from typing import Dict, Any, List
from nicegui import ui
from panther.webapp.services.topology_service import TopologyService

logger = logging.getLogger(__name__)


class TopologyRenderer:
    """Native ECharts based topology diagram renderer."""

    def __init__(self):
        self.topology_service = TopologyService()
        self.current_test_index = 0
        self.graph_data = None
        self.chart = None

    def render(self, config: Dict[str, Any]) -> None:
        """Render complete topology diagram for given config."""
        self.graph_data = self.topology_service.parse_config_to_graph(config)
        self.current_test_index = 0

        if not self.graph_data.get("tests"):
            ui.label("No test cases found in configuration").classes("text-grey-6")
            return

        # View mode selector
        with ui.row().classes("items-center gap-4 q-mb-md"):
            view_mode = ui.toggle({
                "aggregated": "🔘 Full Config Overview",
                "per_test": "⚪ Per Test View"
            }, value="aggregated").classes("q-mr-auto")

        # Statistics panel
        stats = self.graph_data["aggregated"]
        with ui.row().classes("items-center gap-4 q-mb-md"):
            ui.chip(f"{stats['total_tests']} Tests", icon="checklist", color="#8c8c8c").props("outline dense")
            ui.chip(f"{stats['unique_services']} Services", icon="dns", color="#8c8c8c").props("outline dense")
            ui.chip(f"{stats['unique_connections']} Connections", icon="link", color="#8c8c8c").props("outline dense")

        diagram_area = ui.element('div').classes("w-full")

        def update_view(mode):
            diagram_area.clear()
            with diagram_area:
                if mode.value == "aggregated":
                    self._render_test_diagram(self.graph_data["aggregated"], is_aggregated=True)
                else:
                    # Render per-test tabs
                    test_names = [test["name"] for test in self.graph_data["tests"]]
                    with ui.tabs().classes("w-full q-mb-md") as tabs:
                        for name in test_names:
                            ui.tab(name)

                    with ui.tab_panels(tabs, value=test_names[0]).classes("w-full").on('transition', self._on_test_change):
                        for test in self.graph_data["tests"]:
                            with ui.tab_panel(test["name"]):
                                self._render_test_diagram(test)

        view_mode.on_value_change(update_view)

        # Initial render
        with diagram_area:
            self._render_test_diagram(self.graph_data["aggregated"], is_aggregated=True)

    def _render_test_diagram(self, test_data: Dict[str, Any], is_aggregated: bool = False) -> None:
        """Render diagram for a single test case or aggregated view."""
        nodes = test_data["nodes"]
        edges = test_data["edges"]
        scaling = self.topology_service.get_scaling_factors(len(nodes))

        # Network info header
        with ui.row().classes("items-center gap-4 q-mb-sm"):
            if is_aggregated:
                for network_type in test_data.get("network_types", []):
                    ui.chip(network_type, icon="lan", color="#8c8c8c").props("outline")
            else:
                ui.chip(test_data["network_type"], icon="lan", color="#8c8c8c").props("outline")
                
                if test_data["execution_environment"]:
                    for env in test_data["execution_environment"]:
                        ui.chip(env["type"], icon="settings", color="teal").props("outline")

            ui.label(f"{len(nodes)} services • {len(edges)} connections").classes("text-body2 text-grey-7")

        # Legend
        with ui.row().classes("gap-4 q-mb-md"):
            ui.chip("IUT", color="green").props("dense")
            ui.chip("TESTER", color="blue").props("dense")
            ui.chip("Server = Circle • Client = Rounded", color="grey-5").props("dense outline")

        # ECharts Graph
        options = self._build_echarts_options(test_data, scaling)
        
        self.chart = ui.echart(options).classes("w-full h-[420px]")
        self.chart.on('click', self._on_node_click)

    def _build_echarts_options(self, test_data: Dict[str, Any], scaling: Dict[str, float]) -> Dict[str, Any]:
        """Build ECharts configuration options."""
        nodes = test_data["nodes"]
        edges = test_data["edges"]

        # Apply scaling factors
        scaled_nodes = []
        for node in nodes:
            scaled_node = node.copy()
            scaled_node["symbolSize"] = int(node["symbolSize"] * scaling["node_scale"])
            scaled_nodes.append(scaled_node)

        return {
            "tooltip": {
                "trigger": "item",
                "formatter": "{c}"
            },
            "animation": True,
            "animationDuration": 500,
            "animationEasingUpdate": "quinticInOut",
            "series": [
                {
                    "type": "graph",
                    "layout": "force",
                    "roam": True,
                    "draggable": True,
                    "focusNodeAdjacency": True,
                    "autoCurveness": True,
                    "nodes": scaled_nodes,
                    "links": edges,
                    "label": {
                        "show": True,
                        "position": "inside",
                        "formatter": "{b}",
                        "fontSize": scaling["label_font"],
                        "color": "#030303",
                        "fontWeight": "bold"
                    },
                    "edgeLabel": {
                        "show": len(edges) <= 4,
                        "fontSize": 10,
                        "formatter": "{c}"
                    },
                    "lineStyle": {
                        "color": "source",
                        "curveness": 0.1,
                        "width": scaling["edge_width"],
                        "opacity": 0.7
                    },
                    "emphasis": {
                        "lineStyle": {
                            "width": scaling["edge_width"] * 1.5,
                            "opacity": 1
                        }
                    },
                    "force": {
                        "repulsion": 250 * scaling["node_scale"],
                        "gravity": 0.05,
                        "edgeLength": 120 * scaling["node_scale"],
                        "layoutAnimation": True
                    }
                }
            ]
        }

    def _on_test_change(self, event) -> None:
        """Handle test tab change."""
        self.current_test_index = event.args[0]
        logger.debug(f"Switched to test index: {self.current_test_index}")

    def _on_node_click(self, event) -> None:
        """Handle node click event."""
        try:
            # NiceGUI ECharts event structure
            event_data = event.args[0] if isinstance(event.args, list) else event.args
            data = event_data.get("data", event_data)
            
            ui.notify(f"Selected: {data.get('name', 'Unknown')}", type="info")
            logger.debug(f"Node clicked: {data.get('id', 'Unknown')}")
        except Exception as e:
            logger.debug(f"Click handler error: {e}")

    def export_svg(self) -> None:
        """Export current diagram as SVG."""
        if self.chart:
            ui.notify("SVG export triggered", type="info")
            # ECharts SVG export will be implemented here