"""Topology editor page — visual experiment designer (to be implemented).

This page is the student's core thesis contribution. It should provide a
graphical interface for composing PANTHER experiment topologies: services as
nodes, protocol relationships as edges, network environments as groups.

The student designs and implements this page after evaluating visualization
libraries (see ``components/topology_editor.py`` for the 3 candidate approaches).

See ``ARCHITECTURE.md`` § "Config Model Hierarchy" for graph-relevant fields.
"""

import logging

from nicegui import ui
from panther.webapp.services.config_service import ConfigService
from panther.webapp.components.topology.topology_renderer import TopologyRenderer

logger = logging.getLogger(__name__)


def content():
    """Render the topology editor page."""
    logger.info("Loading topology editor page")

    config_service = ConfigService()
    config_files = config_service.list_configs()
    
    loaded_config = {"value": None}
    current_config_path = {"value": ""}
    ui.label("Visual Experiment Designer").classes("text-h5 q-mb-md")

    # Config file selector
    with ui.card().classes("w-full q-pa-md q-mb-md"):
        with ui.row().classes("items-center gap-4 w-full"):
            ui.label("Select Config File:").classes("text-subtitle1")
            
            config_options = [("", "--- Select a configuration file ---")] + [
                (cf["path"], cf["name"]) for cf in config_files
            ]
            
            config_select = ui.select(
                options=dict(config_options),
                label="Experiment Configuration",
                value="",
                on_change=lambda e: select_config(e.value)
            ).classes("flex-grow")
            
            refresh_button = ui.button(
                icon="refresh",
                on_click=lambda: refresh_config_list()
            ).props("flat round")

    # Config information panel
    info_card = ui.card().classes("w-full q-pa-md q-mb-md")
    with info_card:
        ui.label("Loaded Configuration Details").classes("text-subtitle1 q-mb-sm")
        ui.separator().classes("q-my-sm")
        
        with ui.row().classes("gap-8"):
            with ui.column():
                ui.label("Tests:").classes("text-body2 text-grey-7")
                test_count_label = ui.label("-")
            
            with ui.column():
                ui.label("Services:").classes("text-body2 text-grey-7")
                service_count_label = ui.label("-")
        
        # Network Environment Breakdown
        network_env_row = ui.row().classes("gap-4 q-mt-sm")
        with network_env_row:
            ui.label("Network Environments:").classes("text-body2 text-grey-7")
            network_env_chips_container = ui.row().classes("gap-2")
        
        # Execution Environment Breakdown
        exec_env_row = ui.row().classes("gap-4 q-mt-xs")
        with exec_env_row:
            ui.label("Execution Environments:").classes("text-body2 text-grey-7")
            exec_env_chips_container = ui.row().classes("gap-2")
        
        # Per-test breakdown
        test_env_details = ui.column().classes("gap-1 q-mt-xs")

    # Topology diagram area
    diagram_container = ui.card().classes("w-full q-pa-lg")
    topology_renderer = TopologyRenderer()

    with diagram_container:
        with ui.row().classes("items-center justify-between q-mb-md"):
            ui.label("Network Topology View").classes("text-h6 text-grey-7")
            
            with ui.row().classes("gap-2"):
                ui.button("Refresh Diagram", icon="graphic_eq", on_click=lambda: refresh_diagram()).props("flat")
                ui.button("Export SVG", icon="download", on_click=lambda: topology_renderer.export_svg()).props("flat")
        
        ui.separator().classes("q-my-md")
        
        diagram_area = ui.element('div').classes("w-full")
        
        with diagram_area:
            with ui.column().classes("items-center gap-2 text-grey-6"):
                ui.icon("account_tree", size="64px", color="grey-5")
                ui.label("Topology Diagram").classes("text-h6 text-grey-6")
                ui.label("Select a configuration file above to load the topology graph").classes("text-body1 text-grey-5")

    def select_config(path: str):
        """Handle config file selection."""
        if not path:
            loaded_config["value"] = None
            test_count_label.set_text("-")
            service_count_label.set_text("-")
            network_env_chips_container.clear()
            exec_env_chips_container.clear()
            test_env_details.clear()
            info_card.set_visibility(False)
            return
        
        try:
            config = config_service.load_config(path)
            loaded_config["value"] = config
            current_config_path["value"] = path
            
            tests = config.get("tests", [])
            
            # Update info labels
            test_count = len(tests)
            test_count_label.set_text(str(test_count))
            
            service_count = sum(len(test.get("services", {})) for test in tests)
            service_count_label.set_text(str(service_count))
            
            # Aggregate unique network environments across all tests
            network_envs = set()
            exec_envs = set()
            test_summaries = []
            for test in tests:
                net_type = test.get("network_environment", {}).get("type", "unknown")
                network_envs.add(net_type)
                for env in test.get("execution_environment", []):
                    exec_envs.add(env.get("type", "unknown"))
                test_name = test.get("name", "Unnamed")
                iterations = test.get("iterations", 1)
                test_summaries.append(f"{test_name}: {net_type}{' ×' + str(iterations) + ' iterations' if iterations > 1 else ''}")
            
            # Populate network environment chips
            network_env_chips_container.clear()
            with network_env_chips_container:
                if network_envs:
                    for net_type in sorted(network_envs):
                        if net_type == "docker_compose":
                            ui.chip("🐳 Docker Compose", icon="cloud").props("outline dense").classes("text-body2")
                        elif net_type == "shadow_ns":
                            ui.chip("🌐 Shadow NS", icon="ac_unit").props("outline dense").classes("text-body2")
                        elif net_type == "localhost":
                            ui.chip("🖥️ Localhost", icon="computer").props("outline dense").classes("text-body2")
                        else:
                            ui.chip(net_type, icon="lan").props("outline dense").classes("text-body2")
                else:
                    ui.label("None").classes("text-grey-5")
            
            # Populate execution environment chips
            exec_env_chips_container.clear()
            with exec_env_chips_container:
                if exec_envs:
                    for env_type in sorted(exec_envs):
                        if env_type == "strace":
                            ui.chip("🔍 strace", icon="search").props("outline dense").classes("text-body2")
                        elif env_type == "gdb":
                            ui.chip("🐛 GDB", icon="bug_report").props("outline dense").classes("text-body2")
                        elif env_type == "gperf_cpu":
                            ui.chip("⚡ gperftools CPU", icon="speed").props("outline dense").classes("text-body2")
                        elif env_type == "gperf_heap":
                            ui.chip("📊 gperftools Heap", icon="bar_chart").props("outline dense").classes("text-body2")
                        else:
                            ui.chip(env_type, icon="settings").props("outline dense").classes("text-body2")
                else:
                    ui.label("None").classes("text-grey-5")
            
            # Per-test breakdown
            test_env_details.clear()
            with test_env_details:
                for summary in test_summaries:
                    ui.label(summary).classes("text-body2 text-grey-6")
            
            info_card.set_visibility(True)
            
            # Render topology diagram with config path for navigation
            diagram_area.clear()
            with diagram_area:
                topology_renderer.render(config, config_path=path)
            
            ui.notify(f"Loaded configuration: {path.split('/')[-1]}", type="positive")
            logger.info(f"Successfully loaded config for topology view: {path}")
        except Exception as e:
            ui.notify(f"Failed to load config: {str(e)}", type="negative")
            logger.error(f"Error loading config {path}: {e}")
            loaded_config["value"] = None
            test_count_label.set_text("-")
            service_count_label.set_text("-")
            network_env_chips_container.clear()
            exec_env_chips_container.clear()
            test_env_details.clear()
            info_card.set_visibility(False)
    
    def refresh_config_list():
        """Refresh the list of available config files."""
        updated_configs = config_service.list_configs()
        config_options = [("", "--- Select a configuration file ---")] + [
            (cf["path"], cf["name"]) for cf in updated_configs
        ]
        config_select.options = dict(config_options)
        ui.notify("Config file list refreshed", type="info")
        logger.debug("Refreshed config list for topology page")

    def refresh_diagram():
        """Refresh currently displayed topology diagram by re-reading from disk."""
        path = current_config_path["value"]
        if path:
            try:
                fresh_config = config_service.load_config(path)
                loaded_config["value"] = fresh_config
                diagram_area.clear()
                with diagram_area:
                    topology_renderer.render(fresh_config, config_path=path)
                ui.notify("Diagram refreshed from disk", type="info")
                logger.info(f"Refreshed topology from disk: {path}")
            except Exception as e:
                ui.notify(f"Refresh failed: {str(e)}", type="negative")
                logger.error(f"Error refreshing config {path}: {e}")
        else:
            ui.notify("No configuration loaded", type="warning")
