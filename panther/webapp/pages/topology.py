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

logger = logging.getLogger(__name__)


def content():
    """Render the topology editor page."""
    logger.info("Loading topology editor page")

    config_service = ConfigService()
    config_files = config_service.list_configs()
    
    loaded_config = {"value": None}
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
            
            with ui.column():
                ui.label("Network Type:").classes("text-body2 text-grey-7")
                network_type_label = ui.label("-")

    # Topology diagram area
    with ui.card().classes("w-full q-pa-lg"):
        with ui.row().classes("items-center justify-between q-mb-md"):
            ui.label("Network Topology View").classes("text-h6 text-grey-7")
            
            with ui.row().classes("gap-2"):
                ui.button("Refresh Diagram", icon="graphic_eq", on_click=lambda: ui.notify("Diagram rendering coming soon")).props("flat")
                ui.button("Export SVG", icon="download", on_click=lambda: ui.notify("Export functionality coming soon")).props("flat")
        
        ui.separator().classes("q-my-md")
        
        with ui.element('div').classes("w-full h-[500px] flex items-center justify-center bg-grey-1 rounded"):
            with ui.column().classes("items-center gap-2 text-grey-6"):
                ui.icon("account_tree", size="64px", color="grey-5")
                ui.label("Topology Diagram Placeholder").classes("text-h6 text-grey-6")
                ui.label("Select a configuration file above to load the topology graph").classes("text-body1 text-grey-5")

    def select_config(path: str):
        """Handle config file selection."""
        if not path:
            loaded_config["value"] = None
            test_count_label.set_text("-")
            service_count_label.set_text("-")
            network_type_label.set_text("-")
            info_card.set_visibility(False)
            return
        
        try:
            config = config_service.load_config(path)
            loaded_config["value"] = config
            
            # Update info labels
            test_count = len(config.get("tests", []))
            test_count_label.set_text(str(test_count))
            
            service_count = sum(len(test.get("services", {})) for test in config.get("tests", []))
            service_count_label.set_text(str(service_count))
            
            if config.get("tests"):
                network_type = config["tests"][0].get("network_environment", {}).get("type", "-")
                network_type_label.set_text(network_type)
            else:
                network_type_label.set_text("-")
            
            info_card.set_visibility(True)
            ui.notify(f"Loaded configuration: {path.split('/')[-1]}", type="positive")
            logger.info(f"Successfully loaded config for topology view: {path}")
        except Exception as e:
            ui.notify(f"Failed to load config: {str(e)}", type="negative")
            logger.error(f"Error loading config {path}: {e}")
            loaded_config["value"] = None
            test_count_label.set_text("-")
            service_count_label.set_text("-")
            network_type_label.set_text("-")
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
