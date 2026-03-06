"""Experiments page — launch, monitor, and manage experiments."""

import logging

from nicegui import app, ui

from panther.webapp.components.log_viewer import LogViewer
from panther.webapp.services.experiment_service import get_experiment_service

logger = logging.getLogger(__name__)


def content():
    """Render the experiments page content."""
    config_path = app.storage.general.get("config_path")
    experiment_svc = get_experiment_service()

    ui.label("Experiment Management").classes("text-h5 q-mb-md")

    # Experiment launch section
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

    # Log viewer section
    ui.label("Experiment Logs").classes("text-h6 q-mt-md q-mb-sm")
    log_viewer = LogViewer(max_lines=1000)

    # Replay historical logs
    for line in experiment_svc.log_lines:
        log_viewer.push(line)

    # Live streaming callbacks
    def on_log(line: str):
        log_viewer.push(line)

    def on_status(s: str):
        status_label.text = f"Status: {s}"

    experiment_svc.register_callbacks(on_log, on_status)

    # Unregister callbacks when the client disconnects (page navigation)
    client = ui.context.client
    client.on_disconnect(lambda: experiment_svc.unregister_callbacks(on_log, on_status))

    # Poll for status sync (handles experiment finishing while page is open)
    def _sync_status():
        status_label.text = f"Status: {experiment_svc.status}"
        if not experiment_svc.is_running:
            run_btn.set_visibility(True)
            stop_btn.set_visibility(False)

    ui.timer(2.0, _sync_status)

    # Wire up buttons
    async def on_run():
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
