"""
Topology Renderer - Native NiceGUI ECharts implementation
for experiment topology visualization.
"""

import json
import logging
from typing import Any, Dict
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
        self.current_config_path = None
        self.current_loaded_config = None

    def render(self, config: Dict[str, Any], config_path: str = "") -> None:
        """Render complete topology diagram for given config.

        Args:
            config: The parsed configuration dictionary.
            config_path: The filesystem path of the loaded config file, used
                for navigation back to the config builder on node click.
        """
        self.graph_data = self.topology_service.parse_config_to_graph(config)
        self.current_test_index = 0
        self.current_config_path = config_path
        self.current_loaded_config = config

        if not self.graph_data.get("tests"):
            ui.label("No test cases found in configuration").classes("text-grey-6")
            return

        # View mode selector
        with ui.row().classes("items-center gap-4 q-mb-md"):
            view_mode = ui.toggle(
                {
                    "aggregated": "🔘 Full Config Overview",
                    "per_test": "⚪ Per Test View",
                },
                value="aggregated",
            ).classes("q-mr-auto")

        # Statistics panel
        stats = self.graph_data["aggregated"]
        with ui.row().classes("items-center gap-4 q-mb-md"):
            ui.chip(
                f"{stats['total_tests']} Tests", icon="checklist", color="#8c8c8c"
            ).props("outline dense")
            ui.chip(
                f"{stats['unique_services']} Services", icon="dns", color="#8c8c8c"
            ).props("outline dense")
            ui.chip(
                f"{stats['unique_connections']} Connections",
                icon="link",
                color="#8c8c8c",
            ).props("outline dense")

        diagram_area = ui.element("div").classes("w-full")

        def update_view(mode):
            diagram_area.clear()
            with diagram_area:
                if mode.value == "aggregated":
                    self._render_test_diagram(
                        self.graph_data["aggregated"], is_aggregated=True
                    )
                else:
                    # Render per-test tabs
                    test_names = [test["name"] for test in self.graph_data["tests"]]
                    with ui.tabs().classes("w-full q-mb-md") as tabs:
                        for name in test_names:
                            ui.tab(name)

                    with (
                        ui.tab_panels(tabs, value=test_names[0])
                        .classes("w-full")
                        .on("transition", self._on_test_change)
                    ):
                        for test in self.graph_data["tests"]:
                            with ui.tab_panel(test["name"]):
                                self._render_test_diagram(test)

        view_mode.on_value_change(update_view)

        # Initial render
        with diagram_area:
            self._render_test_diagram(self.graph_data["aggregated"], is_aggregated=True)

    def _render_test_diagram(
        self, test_data: Dict[str, Any], is_aggregated: bool = False
    ) -> None:
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
                ui.chip(test_data["network_type"], icon="lan", color="#8c8c8c").props(
                    "outline"
                )

                if test_data["execution_environment"]:
                    for env in test_data["execution_environment"]:
                        ui.chip(env["type"], icon="settings", color="teal").props(
                            "outline"
                        )

            ui.label(f"{len(nodes)} services • {len(edges)} connections").classes(
                "text-body2 text-grey-7"
            )

        # Legend
        with ui.row().classes("gap-4 q-mb-md"):
            ui.chip("IUT", color="green").props("dense")
            ui.chip("TESTER", color="blue").props("dense")
            ui.chip("Server = Circle • Client = Rounded", color="grey-5").props(
                "dense outline"
            )

        # ECharts Graph
        options = self._build_echarts_options(test_data, scaling)

        # Store metadata about which test view this chart represents
        self._current_chart_is_aggregated = is_aggregated
        if not is_aggregated:
            self._current_chart_test_index = test_data.get(
                "index", self.current_test_index
            )

        chart_test_index = test_data.get("index", self.current_test_index)
        self.chart = ui.echart(options).classes("w-full h-[420px]")
        self.chart.on(
            "click",
            lambda event, test_idx=chart_test_index, aggregated=is_aggregated: self._on_node_click(
                event,
                test_index_override=test_idx,
                is_aggregated=aggregated,
            ),
        )

    def _build_echarts_options(
        self, test_data: Dict[str, Any], scaling: Dict[str, float]
    ) -> Dict[str, Any]:
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
            "tooltip": {"trigger": "item", "formatter": "{c}"},
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
                        "fontWeight": "bold",
                    },
                    "edgeLabel": {
                        "show": len(edges) <= 4,
                        "fontSize": 10,
                        "formatter": "{c}",
                    },
                    "lineStyle": {
                        "color": "source",
                        "curveness": 0.1,
                        "width": scaling["edge_width"],
                        "opacity": 0.7,
                    },
                    "emphasis": {
                        "lineStyle": {
                            "width": scaling["edge_width"] * 1.5,
                            "opacity": 1,
                        }
                    },
                    "force": {
                        "repulsion": 250 * scaling["node_scale"],
                        "gravity": 0.05,
                        "edgeLength": 120 * scaling["node_scale"],
                        "layoutAnimation": True,
                    },
                }
            ],
        }

    def _on_test_change(self, event) -> None:
        """Handle test tab change."""
        self.current_test_index = event.args[0]
        logger.debug(f"Switched to test index: {self.current_test_index}")

    def _on_node_click(
        self,
        event,
        test_index_override: int | None = None,
        is_aggregated: bool | None = None,
    ) -> None:
        """Handle node click event - navigate to config builder with node context."""
        try:
            # NiceGUI ECharts event structure
            event_data = event.args[0] if isinstance(event.args, list) else event.args
            data = event_data.get("data", event_data)

            node_id = data.get("id", "Unknown")
            node_name = data.get("name", "Unknown")

            logger.info(f"Node clicked: id={node_id}, name={node_name}")
            logger.debug(f"Full node data: {json.dumps(data, default=str)}")

            # Determine which test this node belongs to
            # In aggregated view, we need to find which test(s) contain this service
            # In per-test view, we know the current test index
            test_index = 0
            chart_is_aggregated = (
                is_aggregated
                if is_aggregated is not None
                else getattr(self, "_current_chart_is_aggregated", False)
            )
            if chart_is_aggregated:
                # Aggregated view: search all tests for this service
                if self.graph_data and self.current_loaded_config:
                    tests = self.current_loaded_config.get("tests", [])
                    for idx, test in enumerate(tests):
                        services = test.get("services", {})
                        if node_id in services:
                            test_index = idx
                            logger.debug(
                                f"Found service '{node_id}' in test index {idx} ({test.get('name', 'unnamed')})"
                            )
                            break
            else:
                # Per-test view: use the current test index
                test_index = (
                    test_index_override
                    if test_index_override is not None
                    else getattr(
                        self, "_current_chart_test_index", self.current_test_index
                    )
                )

            logger.info(
                f"Navigating to config builder: config_path={self.current_config_path}, "
                f"test_index={test_index}, service_id={node_id}"
            )

            # Strip the name of any aggregated annotations (like newlines for test counts)
            clean_name = node_name.split("\n")[0] if "\n" in node_name else node_name

            # Store navigation data in app.storage.general (server-side, persists across pages)
            from nicegui import app as nicegui_app

            nicegui_app.storage.general["topology_nav"] = {
                "config_path": self.current_config_path or "",
                "test_index": str(test_index),
                "service_id": node_id,
                "service_name": clean_name,
                "source": "topology",
                "timestamp": str(__import__("datetime").datetime.now()),
            }
            logger.info(
                f"Stored topology nav data in app.storage.general: {nicegui_app.storage.general['topology_nav']}"
            )

            # Navigate using JavaScript with query params AND debug logging
            from urllib.parse import urlencode

            params = {
                "config_path": self.current_config_path or "",
                "test_index": str(test_index),
                "service_id": node_id,
                "service_name": clean_name,
                "source": "topology",
            }
            query_string = urlencode(params)

            # Navigate to config builder
            ui.run_javascript(
                f"""
                // Debug logging from client side
                console.log("=== PANTHER Topology Node Click ===");
                console.log("Node clicked:", {json.dumps(clean_name)});
                console.log("Node ID:", {json.dumps(node_id)});
                console.log("Config Path:", {json.dumps(self.current_config_path or '')});
                console.log("Test Index:", {json.dumps(str(test_index))});
                console.log("=== Navigating to Config Builder ===");
                console.log("URL: /config?{query_string}");

                // Navigate to config builder
                window.location.href = "/config?{query_string}";
            """
            )

        except Exception as e:
            logger.error(f"Node click handler error: {e}", exc_info=True)
            ui.notify(f"Error navigating to config: {str(e)}", type="negative")

    def export_svg(self) -> None:
        """Export current diagram as SVG."""
        if self.chart:
            ui.notify("SVG export triggered", type="info")
            # ECharts SVG export will be implemented here
