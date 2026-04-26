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

    with ui.card().classes('q-pa-lg shadow-4 full-width'):
        # Header
        with ui.row().classes('items-center q-mb-lg'):
            ui.icon('dashboard', size='md').classes('q-mr-sm text-primary')
            ui.label("PANTHER Dashboard").classes("text-h4 text-weight-bold text-primary")

        # Overview Section
        with ui.card().classes('q-pa-md q-mb-lg shadow-2'):
            ui.label("Overview").classes("text-h6 text-weight-medium q-mb-md")
            with ui.row().classes("gap-4 justify-center"):
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

        ui.separator().classes('q-mb-lg')

        # Quick Actions Section
        with ui.card().classes('q-pa-md shadow-2'):
            ui.label("Quick Actions").classes("text-h6 text-weight-medium q-mb-md")
            with ui.row().classes("gap-3 justify-center flex-wrap"):
                ui.button("New Config", icon="add", color="positive", on_click=lambda: ui.navigate.to("/config")).classes('q-px-lg')
                ui.button(
                    "Browse Results", icon="folder", color="info", on_click=lambda: ui.navigate.to("/results")
                ).classes('q-px-lg')
                ui.button(
                    "View Plugins",
                    icon="extension",
                    color="warning",
                    on_click=lambda: ui.navigate.to("/plugins"),
                ).classes('q-px-lg')

