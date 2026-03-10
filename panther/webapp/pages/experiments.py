"""Experiments page — launch, monitor, and manage experiments."""

import logging

from nicegui import app, ui

from panther.webapp.components.log_viewer import LogViewer
from panther.webapp.services.config_service import ConfigService
from panther.webapp.services.experiment_service import get_experiment_service

logger = logging.getLogger(__name__)


def content():
    """Render the experiments page content."""
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

    # ── Log viewer section ────────────────────────────────────────────
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
