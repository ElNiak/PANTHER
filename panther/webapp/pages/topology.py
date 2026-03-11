"""Topology editor page -- visual, drag-and-drop experiment designer.

Provides a graphical interface for composing PANTHER (Protocol ANalyzer
and THreat Evaluator for Research) service topologies.

**Intended functionality:**
    This page aims to provide a graphical alternative to YAML-based
    configuration by letting users arrange services (IUTs, testers,
    network environments) as nodes in a network graph, connect them
    with protocol/deployment edges, and configure each node through a
    properties side-panel.

**Current scaffold status:**
    The page is a working scaffold that renders a vis.js Network graph
    with sample data and a node-click properties panel.  The
    interactive features (adding / removing nodes, edge creation,
    PydanticForm-based node configuration, and graph-to-YAML export)
    are planned for future implementation by the developer.

**vis.js integration:**
    The ``TopologyEditor`` component wraps the vis.js ``Network``
    library in a NiceGUI custom element.  It exposes ``set_graph()``
    for resetting the canvas and ``get_graph()`` for exporting the
    current node/edge data as a Python dict.  Node clicks are relayed
    through an ``on_node_click`` callback.

**Live service status overlay:**
    During an active experiment, the page subscribes to ``service``
    events from the ``WebObserver`` and displays a status badge
    indicating the latest service lifecycle change (started, stopped,
    crashed, ready).

**Layout:**
    A ``ui.splitter`` divides the view 75/25 between the graph canvas
    (left) and the properties panel (right).  Below the splitter, a
    legend explains the node group colours and a toolbar provides
    *Reset View* and *Export Graph* actions.

NiceGUI patterns used:
    * ``ui.splitter`` for the canvas / properties split.
    * ``TopologyEditor`` (custom NiceGUI element wrapping vis.js).
    * ``ui.context.client`` capture for thread-safe event handling.
    * ``client.on_disconnect`` for subscription cleanup.
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
    """Render the topology editor page content.

    Called by the NiceGUI router when the user navigates to
    ``/topology``.  The function:

    1. Creates a ``ui.splitter`` with a ``TopologyEditor`` on the left
       (seeded with ``SAMPLE_NODES`` / ``SAMPLE_EDGES``) and a
       properties panel on the right.
    2. Subscribes to ``service`` events from the ``WebObserver`` to
       display a live status badge below the graph.
    3. Renders a colour-coded legend and a toolbar with *Reset View*
       and *Export Graph* buttons.

    The properties panel currently shows basic node metadata (label,
    group, id, title) and a placeholder note indicating where a
    ``PydanticForm`` should be integrated for full node configuration.
    """
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
        """Update the status badge in response to a service lifecycle event."""
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
    """Populate the side-panel with properties for the clicked graph node.

    Clears the properties container and renders node metadata (label,
    group type, ID, and optional title).  Currently includes a
    placeholder note for future PydanticForm integration.

    Args:
        node_id: The vis.js node identifier.
        node_data: A dict of node attributes (label, group, title, etc.)
            as defined in ``SAMPLE_NODES``.
        props_container: The ``ui.column`` element serving as the
            properties panel.
        selected_info: A mutable dict tracking the currently selected
            node (keyed ``"node_id"``).
    """
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
            "TODO: Replace this with PydanticForm for the node's config model."
        ).classes("text-caption text-orange-7")


def _export_graph(editor: TopologyEditor):
    """Export the current graph as JSON and log it for debugging.

    Args:
        editor: The ``TopologyEditor`` instance wrapping the vis.js
            graph.
    """
    import json

    graph = editor.get_graph()
    ui.notify(f"Graph: {len(graph['nodes'])} nodes, {len(graph['edges'])} edges")
    logger.info("Exported graph: %s", json.dumps(graph, indent=2))
