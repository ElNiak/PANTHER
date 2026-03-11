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

logger = logging.getLogger(__name__)


def content():
    """Render the topology editor placeholder page."""
    ui.label("Visual Experiment Designer").classes("text-h5 q-mb-md")

    with ui.card().classes("w-full q-pa-lg"):
        ui.label("Topology Editor — To Be Implemented").classes("text-h6 text-grey-7")
        ui.separator().classes("q-my-md")

        ui.label(
            "This page will provide a drag-and-drop interface for composing "
            "experiment configurations as a visual graph. Services become nodes, "
            "protocol relationships become edges, and network environments group them."
        ).classes("text-body1 q-mb-md")

        ui.label("Candidate visualization approaches:").classes(
            "text-subtitle2 q-mb-sm"
        )

        approaches = [
            (
                "vis.js Network",
                "Mature JS graph library with built-in physics and manipulation API. "
                "Requires CDN + JavaScript bridge.",
            ),
            (
                "React Flow",
                "React-based node editor with rich custom node support. "
                "Requires npm build step + iframe/webcomponent embedding.",
            ),
            (
                "NiceGUI Native",
                "Pure SVG/ECharts approach using only NiceGUI built-in capabilities. "
                "Zero external dependencies but requires custom drag-and-drop.",
            ),
        ]

        for name, desc in approaches:
            with ui.row().classes("items-start gap-2 q-mb-sm"):
                ui.icon("radio_button_unchecked", color="grey").classes(
                    "text-sm q-mt-xs"
                )
                with ui.column().classes("gap-0"):
                    ui.label(name).classes("text-subtitle2")
                    ui.label(desc).classes("text-caption text-grey-7")

        ui.separator().classes("q-my-md")
        ui.label(
            "See ARCHITECTURE.md § 'Visual Topology Editor' for graph-relevant "
            "config fields and § 'Config Model Hierarchy' for the data model."
        ).classes("text-caption text-grey-6")
