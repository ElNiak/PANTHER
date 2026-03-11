"""Topology editor page — visual experiment configuration.

Renders a vis.js Network graph where users can arrange services as nodes,
connect them, and configure each via a properties panel.

This is the **scaffold** page. Muhammad builds all interactive features.
"""

import logging

from nicegui import ui

from panther.core.events.base.event_base import BaseEvent
from panther.webapp.components.topology_editor import TopologyEditor
from panther.webapp.services.experiment_service import get_experiment_service

logger = logging.getLogger(__name__)

# Sample data demonstrating a minimal QUIC test topology
SAMPLE_NODES = [
    {
        "id": 1,
        "label": "picoquic\n(server)",
        "group": "iut",
        "title": "IUT: picoquic server",
    },
    {
        "id": 2,
        "label": "picoquic\n(client)",
        "group": "iut",
        "title": "IUT: picoquic client",
    },
    {
        "id": 3,
        "label": "ivy\n(tester)",
        "group": "tester",
        "title": "Tester: ivy formal verifier",
    },
    {
        "id": 4,
        "label": "docker_compose",
        "group": "environment",
        "title": "Network: docker_compose",
    },
]

SAMPLE_EDGES = [
    {"from": 1, "to": 2, "label": "quic/rfc9000", "id": "e1"},
    {"from": 3, "to": 1, "label": "monitors", "id": "e2", "dashes": True},
    {"from": 1, "to": 4, "label": "deployed on", "id": "e3", "dashes": [5, 5]},
    {"from": 2, "to": 4, "label": "deployed on", "id": "e4", "dashes": [5, 5]},
]


def content():
    """Render the topology editor page content."""
    ui.label("Visual Experiment Designer").classes("text-h5 q-mb-md")
    ui.label(
        "Drag-and-drop topology editor for composing experiment configurations. "
        "Click a node to view its properties."
    ).classes("text-body2 text-grey-7 q-mb-md")

    # Properties panel for selected node (right side)
    selected_info = {"node_id": None}

    with ui.splitter(value=75).classes("w-full") as splitter:
        with splitter.before:
            # Topology canvas
            editor = TopologyEditor(
                nodes=SAMPLE_NODES,
                edges=SAMPLE_EDGES,
                on_node_click=lambda nid, data: _on_node_click(
                    nid, data, props_container, selected_info
                ),
                height="600px",
            )

        with splitter.after:
            # Properties panel
            with ui.column().classes("w-full q-pa-md"):
                ui.label("Properties").classes("text-h6")
                props_container = ui.column().classes("w-full")
                with props_container:
                    ui.label("Click a node to view its properties.").classes(
                        "text-caption text-grey-5"
                    )

    # ── Live service status overlay via WebObserver ─────────────────
    experiment_svc = get_experiment_service()
    observer = experiment_svc.web_observer
    status_badge = ui.label("").classes("text-caption text-grey-5 q-mt-sm")

    # Capture client context for background-thread safety
    client = ui.context.client

    def _on_service_event(event: BaseEvent):
        try:
            with client:
                event_type = event.get_type()
                service_name = event.data.get(
                    "service_name", event.data.get("service_id", event.entity_id)
                )
                # Update the status badge
                if event_type == "service.started":
                    status_badge.text = f"Service started: {service_name}"
                    status_badge.classes(replace="text-caption text-teal q-mt-sm")
                elif event_type == "service.stopped":
                    status_badge.text = f"Service stopped: {service_name}"
                    status_badge.classes(replace="text-caption text-grey-5 q-mt-sm")
                elif event_type == "service.crashed":
                    status_badge.text = f"Service CRASHED: {service_name}"
                    status_badge.classes(replace="text-caption text-red q-mt-sm")
                elif event_type == "service.error":
                    status_badge.text = f"Service error: {service_name}"
                    status_badge.classes(replace="text-caption text-orange q-mt-sm")
                elif event_type == "service.ready":
                    status_badge.text = f"Service ready: {service_name}"
                    status_badge.classes(replace="text-caption text-green q-mt-sm")
        except RuntimeError:
            pass  # client disconnected

    topo_sub = observer.subscribe(
        _on_service_event,
        event_types={"service"},
        batched=False,
    )
    client.on_disconnect(lambda: observer.unsubscribe(topo_sub))

    ui.separator().classes("q-my-md")

    # Legend
    with ui.row().classes("gap-4 items-center"):
        ui.label("Legend:").classes("text-subtitle2")
        with ui.row().classes("items-center gap-1"):
            ui.icon("square", color="green").classes("text-lg")
            ui.label("IUT").classes("text-caption")
        with ui.row().classes("items-center gap-1"):
            ui.icon("diamond", color="blue").classes("text-lg")
            ui.label("Tester").classes("text-caption")
        with ui.row().classes("items-center gap-1"):
            ui.icon("circle", color="orange").classes("text-lg")
            ui.label("Environment").classes("text-caption")

    with ui.row().classes("gap-3 q-mt-md"):
        ui.button(
            "Reset View",
            icon="center_focus_strong",
            on_click=lambda: editor.set_graph(SAMPLE_NODES, SAMPLE_EDGES),
        ).props("flat")
        ui.button(
            "Export Graph",
            icon="download",
            on_click=lambda: _export_graph(editor),
        ).props("flat")


def _on_node_click(node_id, node_data, props_container, selected_info):
    """Handle node click — show properties in the side panel."""
    selected_info["node_id"] = node_id
    props_container.clear()
    with props_container:
        if not node_data:
            ui.label("No data available").classes("text-caption text-grey-5")
            return

        ui.label(f"Node: {node_data.get('label', 'unknown')}").classes("text-subtitle1")
        ui.separator().classes("q-my-sm")

        group = node_data.get("group", "unknown")
        ui.label(f"Type: {group}").classes("text-body2")
        ui.label(f"ID: {node_id}").classes("text-caption text-grey-6")

        if node_data.get("title"):
            ui.label(node_data["title"]).classes("text-caption text-grey-7 q-mt-sm")

        ui.separator().classes("q-my-sm")
        ui.label("Properties panel placeholder").classes("text-caption text-grey-5")
        ui.label(
            "Muhammad: Replace this with PydanticForm for the node's config model."
        ).classes("text-caption text-orange-7")


def _export_graph(editor: TopologyEditor):
    """Export the current graph as JSON for debugging."""
    import json

    graph = editor.get_graph()
    ui.notify(f"Graph: {len(graph['nodes'])} nodes, {len(graph['edges'])} edges")
    logger.info("Exported graph: %s", json.dumps(graph, indent=2))
