"""Experiments page -- launch, monitor, and manage experiment runs.

Provides a browser-based interface for running PANTHER (Protocol
ANalyzer and THreat Evaluator for Research) experiments.

This page combines configuration selection with real-time experiment
execution monitoring in a single view.  The layout is split into
several vertically stacked sections:

**Configuration browser:**
    A filterable table (search + category dropdown) built from
    ``ConfigService.list_configs_recursive()``.  Selecting a row shows
    a preview card with test names, protocols, and services.  A *Use
    This Config* button copies the selected path into the launch input.

**Launch controls:**
    A config path input, a *Run* button, and a *Stop* button.
    ``ExperimentService.run_experiment()`` is called as an ``async``
    NiceGUI handler, allowing the UI to remain responsive.

**Real-time monitoring (WebObserver event flow):**
    Three components subscribe to the ``WebObserver`` event bus exposed
    by ``ExperimentService``:

    * ``ExperimentProgress`` -- listens for ``step.progress``,
      ``step.execution_started/completed``, and ``experiment.*`` events
      to drive a progress bar.
    * ``LogViewer`` -- receives log lines via a callback registered with
      ``experiment_svc.register_callbacks()``.  Historical lines are
      replayed on page load.
    * ``event_viewer`` -- a live event feed rebuilt on every incoming
      event, capped at the 200 most recent entries.

    All event callbacks capture ``ui.context.client`` so that UI
    mutations from background threads are safe.  Subscriptions and
    callbacks are unregistered on ``client.on_disconnect``.

**Status polling:**
    A 2-second ``ui.timer`` polls ``experiment_svc.status`` and
    ``experiment_svc.is_running`` to keep the status label and button
    visibility in sync (handles the case where the experiment finishes
    while the page is open but between event pushes).

NiceGUI patterns used:
    * ``ui.card`` for section grouping.
    * ``ui.table`` with ``selection="single"`` and ``on_select``
      callback for the config browser.
    * ``ui.timer(2.0, ...)`` for status polling.
    * ``async def on_run()`` for non-blocking experiment launch.
    * ``ui.context.client`` capture for thread-safe UI updates.
"""

import logging
from typing import Any

from nicegui import app, ui

from panther.core.events.base.event_base import BaseEvent
from panther.webapp.components.display.event_viewer import event_viewer
from panther.webapp.components.display.log_viewer import LogViewer
from panther.webapp.components.status.progress_bar import ExperimentProgress
from panther.webapp.services.config_service import ConfigService
from panther.webapp.services.experiment_service import get_experiment_service

logger = logging.getLogger(__name__)


def content():
    """Render the experiments page content.

    Called by the NiceGUI router when the user navigates to
    ``/experiments``.  The function builds the entire page layout
    imperatively and wires up three event-driven subsystems:

    1. **Config browser** -- ``ConfigService.list_configs_recursive()``
       populates a ``ui.table``.  Category and text filters narrow the
       rows client-side.  A preview panel shows config metadata on
       selection.
    2. **Launch card** -- the config path input, run / stop buttons,
       and a status label.  ``on_run`` is an ``async`` handler that
       awaits ``ExperimentService.run_experiment()``.
    3. **Monitoring section** -- ``ExperimentProgress``,
       ``LogViewer``, and ``event_viewer`` components, each fed by
       their own ``WebObserver`` subscription or callback pair.

    All subscriptions and callbacks are cleaned up via
    ``client.on_disconnect`` to prevent stale references.
    """
    config_path = app.storage.general.get("config_path")
    experiment_svc = get_experiment_service()
    config_svc = ConfigService()

    ui.label("Experiment Management").classes("text-h5 q-mb-md")

    # Forward-declare config_input so closures in the browser card can reference it.
    config_input = None

    # ── Config browser section (above launch card) ───────────────────
    all_configs = config_svc.list_configs_recursive()
    categories = sorted({c["category"] for c in all_configs if c["category"]})

    with ui.card().classes("w-full q-pa-md q-mb-md"):
        ui.label("Available Configurations").classes("text-subtitle1 q-mb-sm")

        # Filter bar
        with ui.row().classes("w-full gap-3 q-mb-sm items-end"):
            search_input = (
                ui.input(placeholder="Search configs...")
                .props("outlined dense clearable")
                .classes("col-4")
            )
            category_select = (
                ui.select(
                    ["all"] + categories,
                    value="all",
                    label="Category",
                )
                .props("outlined dense")
                .classes("col-3")
            )

        # Table
        columns = [
            {
                "name": "name",
                "label": "Config File",
                "field": "name",
                "sortable": True,
                "align": "left",
            },
            {
                "name": "category",
                "label": "Category",
                "field": "category",
                "sortable": True,
                "align": "left",
            },
            {
                "name": "tests",
                "label": "Tests",
                "field": "test_count",
                "sortable": True,
                "align": "center",
            },
            {
                "name": "modified",
                "label": "Modified",
                "field": "modified",
                "sortable": True,
                "align": "left",
            },
        ]
        rows = [
            {
                "name": c["name"],
                "category": c["category"] or "root",
                "test_count": c["summary"]["test_count"],
                "modified": c["modified"].strftime("%Y-%m-%d %H:%M"),
                "path": c["path"],
            }
            for c in all_configs
        ]

        # Build a lookup for config summaries by path
        config_by_path = {c["path"]: c for c in all_configs}

        def _on_select(e):
            """Show a preview card when a config row is selected."""
            selected = e.selection
            if not selected:
                preview_card.set_visibility(False)
                return
            row = selected[0]
            path = row["path"]
            cfg = config_by_path.get(path)
            if not cfg:
                preview_card.set_visibility(False)
                return

            summary = cfg["summary"]
            preview_title.text = cfg["name"]
            preview_path.text = f"Path: {path}"
            preview_card.set_visibility(True)

            preview_details.clear()
            with preview_details:
                if summary["environment"]:
                    ui.label(f"Environment: {summary['environment']}").classes(
                        "text-body2"
                    )
                if summary["protocols"]:
                    ui.label(f"Protocols: {', '.join(summary['protocols'])}").classes(
                        "text-body2"
                    )
                ui.label(f"Tests: {summary['test_count']}").classes("text-body2")
                for tname in summary["test_names"]:
                    ui.label(f"  \u2022 {tname}").classes("text-body2 text-grey-8")
                if summary["services"]:
                    ui.label(f"Services: {', '.join(summary['services'])}").classes(
                        "text-body2"
                    )

        config_table = ui.table(
            columns=columns,
            rows=rows,
            row_key="path",
            selection="single",
            on_select=_on_select,
            pagination={"rowsPerPage": 10, "sortBy": "category"},
        ).classes("w-full")

        # Preview panel (hidden until a row is selected)
        preview_card = ui.card().classes("w-full q-pa-md q-mt-sm")
        preview_card.set_visibility(False)

        with preview_card:
            preview_title = ui.label("").classes("text-subtitle1")
            preview_path = ui.label("").classes("text-caption text-grey-7")
            preview_details = ui.column().classes("q-mt-sm")

            def _use_config():
                sel = config_table.selected
                if sel and config_input is not None:
                    config_input.value = sel[0]["path"]
                    ui.notify(f"Config set: {sel[0]['name']}", type="positive")

            ui.button(
                "Use This Config",
                icon="check_circle",
                color="primary",
                on_click=_use_config,
            )

        # Filtering
        def _apply_filters():
            """Filter the config table rows by search text and category."""
            search = (search_input.value or "").lower().strip()
            cat = category_select.value
            filtered = []
            for r in rows:
                if cat != "all" and r["category"] != cat:
                    continue
                if search and search not in r["name"].lower():
                    continue
                filtered.append(r)
            config_table.rows = filtered
            config_table.update()

        search_input.on("update:model-value", lambda _: _apply_filters())
        category_select.on_value_change(lambda _: _apply_filters())

    # ── Launch experiment section ─────────────────────────────────────
    with ui.card().classes("w-full q-pa-md q-mb-md"):
        ui.label("Launch Experiment").classes("text-subtitle1 q-mb-sm")

        config_input = ui.input(
            label="Config file path",
            value=experiment_svc.config_path or config_path or "",
            placeholder="path/to/experiment_config.yaml",
        ).classes("w-full")

        status_label = ui.label(f"Status: {experiment_svc.status}").classes(
            "text-body2 text-grey-7 q-mt-sm"
        )

        with ui.row().classes("gap-3 q-mt-sm"):
            run_btn = ui.button("Run Experiment", icon="play_arrow")
            stop_btn = ui.button("Stop", icon="stop", color="negative")

            if experiment_svc.is_running:
                run_btn.set_visibility(False)
                stop_btn.set_visibility(True)
            else:
                stop_btn.set_visibility(False)

    # ── Progress bar (event-driven via WebObserver) ─────────────────
    ui.label("Progress").classes("text-h6 q-mt-md q-mb-sm")
    progress = ExperimentProgress()

    # Capture client context for background-thread safety
    client_ref = ui.context.client

    def _on_progress_event(event: BaseEvent):
        """Drive the progress bar from step and experiment events."""
        try:
            with client_ref:
                event_type = event.get_type()
                if event_type == "step.progress":
                    pct = event.data.get("progress_percentage", 0)
                    msg = event.data.get(
                        "progress_message", event.data.get("step_name", "")
                    )
                    progress.update(msg, pct / 100.0)
                elif event_type == "step.execution_started":
                    progress.update(event.data.get("step_name", "Step"), 0.0)
                elif event_type == "step.execution_completed":
                    progress.update(event.data.get("step_name", "Done"), 1.0)
                elif event_type == "experiment.started":
                    progress.reset()
                elif event_type == "experiment.completed":
                    progress.update("Completed", 1.0)
        except RuntimeError:
            pass  # client disconnected

    progress_sub = experiment_svc.web_observer.subscribe(
        _on_progress_event,
        event_types={"step", "experiment"},
    )
    client_ref.on_disconnect(
        lambda: experiment_svc.web_observer.unsubscribe(progress_sub)
    )

    # ── Log viewer section ────────────────────────────────────────────
    ui.label("Experiment Logs").classes("text-h6 q-mt-md q-mb-sm")
    log_viewer = LogViewer(max_lines=1000)

    # Replay historical logs
    for line in experiment_svc.log_lines:
        log_viewer.push(line)

    # Live streaming callbacks
    def on_log(line: str):
        """Push a single log line into the log viewer."""
        log_viewer.push(line)

    def on_status(s: str):
        """Update the status label text."""
        status_label.text = f"Status: {s}"

    experiment_svc.register_callbacks(on_log, on_status)

    # Unregister callbacks when the client disconnects (page navigation)
    ui.context.client.on_disconnect(
        lambda: experiment_svc.unregister_callbacks(on_log, on_status)
    )

    # ── Live event viewer (event-driven via WebObserver) ─────────────
    ui.label("Live Events").classes("text-h6 q-mt-md q-mb-sm")

    live_events: list[dict[str, Any]] = []
    events_container = ui.column().classes("w-full")

    # Populate from history if experiment already ran
    for hist_event in experiment_svc.web_observer.event_history:
        d = hist_event.to_dict()
        d["event_type"] = d.pop("type", hist_event.get_type())
        live_events.append(d)

    if live_events:
        with events_container:
            event_viewer(live_events[-200:])

    def _on_live_event(event: BaseEvent):
        """Append an event to the live feed and re-render the viewer."""
        try:
            with client_ref:
                d = event.to_dict()
                d["event_type"] = d.pop("type", event.get_type())
                live_events.append(d)
                events_container.clear()
                with events_container:
                    event_viewer(live_events[-200:])
        except RuntimeError:
            pass  # client disconnected

    events_sub = experiment_svc.web_observer.subscribe(_on_live_event)
    client_ref.on_disconnect(
        lambda: experiment_svc.web_observer.unsubscribe(events_sub)
    )

    # Poll for status sync (handles experiment finishing while page is open)
    def _sync_status():
        """Poll experiment status and toggle run/stop button visibility."""
        status_label.text = f"Status: {experiment_svc.status}"
        if not experiment_svc.is_running:
            run_btn.set_visibility(True)
            stop_btn.set_visibility(False)

    ui.timer(2.0, _sync_status)

    # Wire up buttons
    async def on_run():
        """Launch an experiment asynchronously and update the UI on completion."""
        path = config_input.value.strip()
        if not path:
            ui.notify("Please provide a config file path", type="warning")
            return
        status_label.text = "Status: Starting..."
        run_btn.set_visibility(False)
        stop_btn.set_visibility(True)
        log_viewer.clear()
        log_viewer.push(f"Starting experiment with config: {path}")

        try:
            await experiment_svc.run_experiment(config_path=path)
            ui.notify("Experiment completed", type="positive")
        except Exception as e:
            status_label.text = f"Status: Error - {e}"
            log_viewer.push(f"ERROR: {e}")
            ui.notify(f"Experiment failed: {e}", type="negative")
        finally:
            run_btn.set_visibility(True)
            stop_btn.set_visibility(False)

    run_btn.on_click(on_run)
    stop_btn.on_click(lambda: experiment_svc.stop())
