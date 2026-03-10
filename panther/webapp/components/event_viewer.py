"""Event table and timeline visualization component."""

import logging
from typing import Any

from nicegui import ui

from panther.core.events.event_summarizer import EventImportance, EventSummarizer
from panther.webapp.utils.format_helpers import compute_duration

logger = logging.getLogger(__name__)

# Color mapping driven by EventImportance levels
_IMPORTANCE_COLORS = {
    EventImportance.LOW: "#9E9E9E",  # grey
    EventImportance.MEDIUM: "#2196F3",  # blue
    EventImportance.HIGH: "#FF9800",  # orange
    EventImportance.CRITICAL: "#F44336",  # red
}


def _event_color(event_type: str) -> str:
    """Map event_type to a color via EventSummarizer importance."""
    importance = EventSummarizer.IMPORTANT_EVENT_TYPES.get(
        event_type, EventImportance.MEDIUM
    )
    return _IMPORTANCE_COLORS[importance]


def _summarize_event(event_type: str, data: Any) -> str:
    """Produce a one-line summary using EventSummarizer when possible."""
    if not data:
        return ""
    if isinstance(data, str):
        return data
    if isinstance(data, dict):
        summary = EventSummarizer.summarize_event(event_type, data)
        return summary.summary
    return str(data)[:100]


def event_viewer(events: list[dict[str, Any]]):
    """Render events as a filterable table with an optional timeline view.

    Args:
        events: List of event dicts with at least event_type, timestamp, data.
    """
    if not events:
        ui.label("No events to display.").classes("text-grey-7")
        return

    # Collect unique event types for the filter
    event_types = sorted({e.get("event_type", "unknown") for e in events})

    with ui.tabs().classes("w-full") as view_tabs:
        table_tab = ui.tab("Table", icon="table_chart")
        timeline_tab = ui.tab("Timeline", icon="timeline")

    with ui.tab_panels(view_tabs, value=table_tab).classes("w-full"):
        with ui.tab_panel(table_tab):
            _render_table_view(events, event_types)
        with ui.tab_panel(timeline_tab):
            _render_timeline_view(events)


def _render_table_view(events: list[dict[str, Any]], event_types: list[str]):
    """Filterable, sortable table of events."""
    # Filter controls
    with ui.row().classes("w-full gap-3 q-mb-sm items-end"):
        type_filter = (
            ui.select(
                ["all"] + event_types,
                value="all",
                label="Event Type",
            )
            .props("outlined dense")
            .classes("col-3")
        )
        search_filter = (
            ui.input(placeholder="Search events...")
            .props("outlined dense clearable")
            .classes("col-3")
        )

    # Build table rows
    def _make_rows(filter_type: str = "all", search: str = "") -> list[dict[str, Any]]:
        rows = []
        for i, e in enumerate(events):
            et = e.get("event_type", "unknown")
            if filter_type != "all" and et != filter_type:
                continue
            ts = e.get("timestamp", "")
            data = e.get("data", {})
            details = _summarize_event(et, data)
            source = e.get("_source", "")
            row_str = f"{ts} {et} {details} {source}".lower()
            if search and search.lower() not in row_str:
                continue
            rows.append(
                {
                    "id": i,
                    "timestamp": ts[:19] if ts else "",
                    "event_type": et,
                    "details": details[:200],
                    "source": source,
                }
            )
        return rows

    columns = [
        {
            "name": "timestamp",
            "label": "Timestamp",
            "field": "timestamp",
            "sortable": True,
            "align": "left",
        },
        {
            "name": "event_type",
            "label": "Event Type",
            "field": "event_type",
            "sortable": True,
            "align": "left",
        },
        {
            "name": "details",
            "label": "Details",
            "field": "details",
            "align": "left",
        },
        {
            "name": "source",
            "label": "Source",
            "field": "source",
            "align": "center",
        },
    ]

    initial_rows = _make_rows()
    table = ui.table(
        columns=columns,
        rows=initial_rows,
        row_key="id",
        pagination={"rowsPerPage": 25, "sortBy": "timestamp"},
    ).classes("w-full")

    # Color-code event types via slot
    table.add_slot(
        "body-cell-event_type",
        r"""
        <q-td :props="props">
            <q-badge
                :color="{'test.started': 'blue', 'test.failed': 'red',
                          'test.completed': 'green', 'environment.deployment_started': 'teal',
                          'environment.deployment_completed': 'green',
                          'environment.output_collection_started': 'amber',
                          'environment.output_collection_completed': 'light-green',
                          'environment.outputs_collected': 'cyan',
                          'log': 'grey'}[props.value] || 'grey'"
                :label="props.value"
                outline
                class="text-capitalize"
            />
        </q-td>
        """,
    )

    def _refresh():
        table.rows = _make_rows(type_filter.value or "all", search_filter.value or "")

    type_filter.on_value_change(lambda _: _refresh())
    search_filter.on_value_change(lambda _: _refresh())


def _render_timeline_view(events: list[dict[str, Any]]):
    """Vertical timeline with color-coded nodes."""
    if not events:
        return

    with ui.scroll_area().style("max-height: 600px"):
        with ui.element("div").classes("q-ml-md"):
            prev_ts = None
            for e in events:
                et = e.get("event_type", "unknown")
                ts = e.get("timestamp", "")[:19]
                color = _event_color(et)
                data = e.get("data", {})
                details = _summarize_event(et, data)

                # Duration since previous event
                duration_label = ""
                if prev_ts and ts and prev_ts != ts:
                    duration_label = compute_duration(prev_ts, ts)

                with ui.element("div").classes("flex gap-3 q-mb-sm"):
                    # Timeline node
                    with (
                        ui.element("div")
                        .classes("flex flex-col items-center")
                        .style("min-width: 20px")
                    ):
                        ui.element("div").style(
                            f"width: 12px; height: 12px; border-radius: 50%;"
                            f" background: {color}; flex-shrink: 0;"
                        )
                        ui.element("div").style(
                            "width: 2px; flex-grow: 1; background: #e0e0e0;"
                            " min-height: 20px;"
                        )

                    # Content
                    with ui.element("div").classes("flex-grow"):
                        with ui.row().classes("items-center gap-2"):
                            ui.label(et).classes("text-body2 font-bold")
                            if ts:
                                ui.label(ts).classes("text-caption text-grey-6")
                            if duration_label:
                                ui.badge(duration_label, color="grey").props("outline")
                        if details:
                            ui.label(details[:300]).classes("text-caption text-grey-7")

                prev_ts = ts
