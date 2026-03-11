"""Dashboard page — home page with summary stats and live experiment counters."""

import logging
from pathlib import Path

from nicegui import app, ui

from panther.core.events.base.event_base import BaseEvent
from panther.core.events.event_summarizer import EventImportance
from panther.webapp.components.stat_cards import stat_card
from panther.webapp.services.experiment_service import get_experiment_service
from panther.webapp.services.plugin_service import PluginService
from panther.webapp.services.results_service import ResultsService

logger = logging.getLogger(__name__)


def content():
    """Render the dashboard page content."""
    output_dir = app.storage.general.get("output_dir", "outputs")

    plugin_svc = PluginService()
    results_svc = ResultsService(output_dir)
    experiment_svc = get_experiment_service()

    plugin_count = len(plugin_svc.list_plugins())
    experiment_count = results_svc.count_experiments()
    config_path = app.storage.general.get("config_path")

    ui.label("Overview").classes("text-h5 q-mb-md")

    with ui.row().classes("gap-4 q-mb-lg"):
        stat_card("Plugins", str(plugin_count), icon="extension", color="primary")
        stat_card(
            "Past Experiments",
            str(experiment_count),
            icon="history",
            color="secondary",
        )
        stat_card(
            "Loaded Config",
            Path(config_path).name if config_path else "None",
            icon="description",
            color="accent",
        )

    # ── Live experiment stat cards (updated via WebObserver events) ────
    ui.label("Live Experiment").classes("text-h6 q-mt-md q-mb-sm")

    with ui.row().classes("gap-4 q-mb-lg") as live_row:
        with ui.card().classes("q-pa-md"):
            with ui.row().classes("items-center gap-3 no-wrap"):
                ui.icon("science", size="md").classes("text-teal")
                with ui.column().classes("gap-0"):
                    ui.label("Tests Passed").classes("text-caption text-grey-7")
                    tests_passed_label = ui.label("—").classes("text-h5 font-bold")

        with ui.card().classes("q-pa-md"):
            with ui.row().classes("items-center gap-3 no-wrap"):
                ui.icon("sync", size="md").classes("text-deep-purple")
                with ui.column().classes("gap-0"):
                    ui.label("Current Phase").classes("text-caption text-grey-7")
                    phase_label = ui.label("Idle").classes("text-h5 font-bold")

        with ui.card().classes("q-pa-md"):
            with ui.row().classes("items-center gap-3 no-wrap"):
                ui.icon("timer", size="md").classes("text-amber")
                with ui.column().classes("gap-0"):
                    ui.label("Status").classes("text-caption text-grey-7")
                    status_label = ui.label(experiment_svc.status).classes(
                        "text-h5 font-bold"
                    )

    # Track test pass/fail counts locally
    counters = {"passed": 0, "failed": 0, "total": 0}

    # Capture client context for background-thread safety
    client = ui.context.client

    def _on_live_event(event: BaseEvent):
        try:
            with client:
                event_type = event.get_type()
                if event_type == "test.completed":
                    counters["total"] += 1
                    if event.data.get("passed"):
                        counters["passed"] += 1
                    else:
                        counters["failed"] += 1
                    tests_passed_label.text = (
                        f"{counters['passed']}/{counters['total']}"
                    )
                elif event_type.startswith("experiment.phase"):
                    phase_label.text = event.data.get(
                        "phase", event_type.split(".")[-1]
                    )
                elif event_type == "experiment.started":
                    counters.update(passed=0, failed=0, total=0)
                    tests_passed_label.text = "0/0"
                    phase_label.text = "Running"
                    status_label.text = "Running"
                elif event_type == "experiment.completed":
                    status_label.text = "Completed"
                elif event_type == "experiment.failed":
                    status_label.text = "Failed"
        except RuntimeError:
            pass  # client disconnected

    sub = experiment_svc.web_observer.subscribe(
        _on_live_event,
        event_types={"experiment", "test"},
        importance=EventImportance.HIGH,
    )

    # Unsubscribe on page disconnect
    client.on_disconnect(lambda: experiment_svc.web_observer.unsubscribe(sub))

    ui.separator()

    ui.label("Quick Actions").classes("text-h6 q-mt-md q-mb-sm")
    with ui.row().classes("gap-3"):
        ui.button("New Config", icon="add", on_click=lambda: ui.navigate.to("/config"))
        ui.button(
            "Browse Results", icon="folder", on_click=lambda: ui.navigate.to("/results")
        )
        ui.button(
            "View Plugins",
            icon="extension",
            on_click=lambda: ui.navigate.to("/plugins"),
        )
