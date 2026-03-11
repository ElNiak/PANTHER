"""Layout — shared header, sidebar navigation, and activity feed.

Provides the ``create_layout()`` function used by every page in the
PANTHER (Protocol ANalysis and Testing Harness for Extensible Research)
web dashboard to render a consistent chrome: a branded header bar, a
left-drawer navigation sidebar with links to all major pages, a live
activity feed showing recent important events, and a footer.

The activity feed subscribes to the ``WebObserver`` event system so that
HIGH-importance events appear in the sidebar in real time, and CRITICAL
events trigger toast notifications.  Subscriptions are cleaned up
automatically when the browser client disconnects.
"""

import logging
from pathlib import Path

from nicegui import ui

from panther.core.events.base.event_base import BaseEvent
from panther.core.events.event_summarizer import EventImportance
from panther.webapp.services.experiment_service import get_experiment_service

logger = logging.getLogger(__name__)

# Resolve static directory relative to this file
STATIC_DIR = Path(__file__).parent.parent / "static"

NAV_ITEMS = [
    ("/", "Dashboard", "dashboard"),
    ("/config", "Config Builder", "settings"),
    ("/topology", "Topology Editor", "hub"),
    ("/experiments", "Experiments", "science"),
    ("/results", "Results", "assessment"),
    ("/plugins", "Plugins", "extension"),
]


def create_layout(page_title: str = "PANTHER"):
    """Create the shared page layout with header and sidebar navigation.

    Renders the full page chrome (header, left drawer, footer) and wires
    two event subscriptions via the experiment service's ``WebObserver``:

    * **CRITICAL** events produce toast notifications (immediate, unbatched).
    * **HIGH** events are appended to the sidebar activity feed (batched).

    Both subscriptions are unsubscribed on client disconnect to avoid
    stale callbacks.

    Args:
        page_title: Title shown next to the PANTHER logo in the header.
    """
    experiment_svc = get_experiment_service()
    observer = experiment_svc.web_observer

    ui.colors(primary="#1a237e", secondary="#283593", accent="#536dfe")

    with ui.header().classes("items-center justify-between bg-primary"):
        with ui.row().classes("items-center gap-4"):
            ui.icon("security", size="sm").classes("text-white")
            ui.label("PANTHER").classes("text-h6 text-white font-bold no-margin")
            ui.label(f"/ {page_title}").classes("text-subtitle1 text-white")

        with ui.row().classes("items-center gap-2"):
            ui.label("Protocol Testing Dashboard").classes("text-caption text-white")

    with ui.left_drawer(value=True).classes("bg-grey-2"):
        ui.label("Navigation").classes("text-subtitle2 q-mb-sm")
        for path, label, icon in NAV_ITEMS:
            with ui.link(target=path).classes("no-underline"):
                with ui.row().classes(
                    "items-center gap-2 q-pa-sm rounded "
                    "cursor-pointer hover:bg-grey-3 full-width"
                ):
                    ui.icon(icon, size="xs")
                    ui.label(label).classes("text-body2")

        ui.separator().classes("q-my-md")

        # ── Activity feed (recent important events) ───────────────────
        ui.label("Recent Activity").classes("text-subtitle2 q-mb-xs")
        activity_container = ui.column().classes("w-full gap-1")

        # Pre-populate from history
        recent = observer.get_event_history(limit=10)
        with activity_container:
            for evt in recent[-5:]:
                _render_activity_item(evt)

        ui.separator().classes("q-my-md")
        ui.label("PANTHER v1.2.1").classes("text-caption text-grey-7")

    with ui.footer().classes("bg-grey-1 text-grey-7 text-caption"):
        ui.label(
            "PANTHER - Protocol Analysis and Testing Harness " "for Extensible Research"
        )

    # Capture client context for background-thread safety
    client = ui.context.client

    # ── 4.2: Global toast notifications for CRITICAL events ───────────
    def _on_critical(event: BaseEvent):
        event_type = event.get_type()
        msg = f"{event_type}: {event.entity_id}"
        try:
            with client:
                if event_type.endswith(".failed") or event_type.endswith(".crashed"):
                    ui.notify(msg, type="negative", position="top-right", timeout=8000)
                else:
                    ui.notify(msg, type="warning", position="top-right", timeout=5000)
        except RuntimeError:
            pass  # client disconnected

    toast_sub = observer.subscribe(
        _on_critical,
        importance=EventImportance.CRITICAL,
        batched=False,  # toasts should be immediate
    )

    # ── 4.5: Cross-page activity feed ─────────────────────────────────
    def _on_activity(event: BaseEvent):
        try:
            with client:
                with activity_container:
                    _render_activity_item(event)
                    # Keep only last 10 items
                    while len(activity_container.default_slot.children) > 10:
                        activity_container.remove(
                            activity_container.default_slot.children[0]
                        )
        except RuntimeError:
            pass  # client disconnected

    feed_sub = observer.subscribe(
        _on_activity,
        importance=EventImportance.HIGH,
    )

    # Cleanup on disconnect
    client.on_disconnect(
        lambda: (
            observer.unsubscribe(toast_sub),
            observer.unsubscribe(feed_sub),
        )
    )


def _render_activity_item(event: BaseEvent):
    """Render a single activity item in the sidebar feed."""
    event_type = event.get_type()
    ts = event.timestamp.strftime("%H:%M:%S")

    # Pick icon/color based on event type prefix
    if "experiment" in event_type:
        icon, color = "science", "deep-purple"
    elif "test" in event_type:
        icon, color = "check_circle", "teal"
    elif "service" in event_type:
        icon, color = "dns", "blue"
    else:
        icon, color = "info", "grey"

    with ui.row().classes("items-center gap-1 w-full"):
        ui.icon(icon, size="xs").classes(f"text-{color}")
        with ui.column().classes("gap-0"):
            ui.label(event_type).classes("text-caption font-bold").style(
                "font-size: 0.7rem"
            )
            ui.label(f"{event.entity_id} @ {ts}").classes(
                "text-caption text-grey-6"
            ).style("font-size: 0.65rem")
