"""Dashboard page -- overview with summary statistics and real-time monitoring.

Provides an overview of the PANTHER (Protocol ANalysis and Testing
Harness for Extensible Research) system status.

This is the landing page users see when they open the webapp. It provides three
sections:

1. **Overview cards** -- static statistics fetched once when the page loads:
   total registered plugins (via ``PluginService``), number of past
   experiment runs (via ``ResultsService``), and the currently loaded
   configuration file path (from ``app.storage.general``).

2. **Live experiment cards** -- reactive labels (tests passed, current
   phase, overall status) updated in real time by subscribing to the
   ``WebObserver`` event bus exposed by ``ExperimentService``.  Events
   of type ``test.completed``, ``experiment.phase.*``, ``experiment.started``,
   ``experiment.completed``, and ``experiment.failed`` drive label changes.

3. **Quick-action buttons** -- navigation shortcuts to the config builder,
   results browser, and plugin pages.

NiceGUI patterns used:
    * ``ui.row`` / ``ui.card`` for the card grid layout.
    * ``ui.timer`` is *not* used here; instead the page relies on
      push-based ``WebObserver.subscribe()`` callbacks.
    * ``ui.context.client`` is captured to safely update the UI from
      background threads (the experiment runner publishes events off the
      main thread).
    * ``client.on_disconnect`` ensures subscription cleanup when the
      browser tab navigates away.

Data sources:
    * ``PluginService.list_plugins()``
    * ``ResultsService.count_experiments()``
    * ``ExperimentService`` (singleton via ``get_experiment_service()``)
    * ``app.storage.general`` for ``output_dir`` and ``config_path``
"""

import logging
from pathlib import Path

from nicegui import app, ui

from panther.core.events.base.event_base import BaseEvent
from panther.core.events.event_summarizer import EventImportance
from panther.webapp.components.display.stat_cards import stat_card
from panther.webapp.services.experiment_service import get_experiment_service
from panther.webapp.services.plugin_service import PluginService
from panther.webapp.services.results import ResultsService

logger = logging.getLogger(__name__)


def content():
    """Render the dashboard page content.

    Called by the NiceGUI router when the user navigates to ``/``.
    The function is structured as a single top-to-bottom layout builder:

    1. Instantiates service objects (``PluginService``, ``ResultsService``,
       ``ExperimentService``) and queries static counts.
    2. Builds a row of ``stat_card`` components for the static overview.
    3. Creates a "Live Experiment" section with three cards whose labels
       are captured in local variables (``tests_passed_label``,
       ``phase_label``, ``status_label``).
    4. Subscribes ``_on_live_event`` to the ``WebObserver`` for
       ``experiment`` and ``test`` event families, filtering to
       ``EventImportance.HIGH``.  The closure mutates a ``counters``
       dict and updates labels via the captured NiceGUI ``client``
       context.
    5. Registers a disconnect handler to unsubscribe automatically.
    6. Adds a "Quick Actions" row with navigation buttons.
    """
    logger.info("Loading dashboard page")
    output_dir = app.storage.general.get("output_dir", "outputs")

    plugin_svc = PluginService()
    results_svc = ResultsService(output_dir)
    experiment_svc = get_experiment_service()

    plugin_count = len(plugin_svc.list_plugins())
    experiment_count = results_svc.count_experiments()
    logger.debug(
        "Dashboard stats: %d plugins, %d experiments", plugin_count, experiment_count
    )
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
        """Update live stat cards in response to a WebObserver event."""
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
            logger.debug("Client disconnected during UI update")

    sub = experiment_svc.web_observer.subscribe(
        _on_live_event,
        event_types={"experiment", "test"},
        importance=EventImportance.HIGH,
    )
    logger.debug("Dashboard subscribed to live experiment events")

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
