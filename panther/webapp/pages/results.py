"""Results page — browse past experiment outputs."""

import logging

from nicegui import app, ui

from panther.webapp.services.results_service import ResultsService

logger = logging.getLogger(__name__)


def content():
    """Render the results browser page content."""
    output_dir = app.storage.general.get("output_dir", "outputs")
    results_svc = ResultsService(output_dir)

    ui.label("Experiment Results").classes("text-h5 q-mb-md")

    experiments = results_svc.list_experiments()

    if not experiments:
        with ui.card().classes("w-full q-pa-lg text-center"):
            ui.icon("inbox", size="xl").classes("text-grey-5")
            ui.label("No experiment results found.").classes(
                "text-body1 text-grey-7 q-mt-sm"
            )
            ui.label(f"Looking in: {output_dir}").classes("text-caption text-grey-5")
        return

    # Results table
    columns = [
        {"name": "date", "label": "Date", "field": "date", "sortable": True},
        {"name": "name", "label": "Experiment", "field": "name", "sortable": True},
        {"name": "tests", "label": "Tests", "field": "test_count"},
        {"name": "status", "label": "Status", "field": "status"},
    ]
    rows = [
        {
            "date": exp["date"],
            "name": exp["name"],
            "test_count": exp.get("test_count", "?"),
            "status": exp.get("status", "unknown"),
        }
        for exp in experiments
    ]

    table = ui.table(columns=columns, rows=rows, row_key="name").classes("w-full")
    table.on("rowClick", lambda e: show_detail(e.args[1]["name"]))

    # Detail view
    ui.separator().classes("q-my-md")
    detail_container = ui.column().classes("w-full")

    def show_detail(name: str):
        detail_container.clear()
        with detail_container:
            detail = results_svc.get_experiment_detail(name)
            if not detail:
                ui.label("No details available").classes("text-grey-7")
                return

            ui.label(f"Experiment: {name}").classes("text-h6")

            if detail.get("log_content"):
                ui.label("Logs").classes("text-subtitle2 q-mt-sm")
                ui.code(detail["log_content"]).classes("w-full")

            if detail.get("report_content"):
                ui.label("Report").classes("text-subtitle2 q-mt-sm")
                ui.markdown(detail["report_content"])

            if detail.get("artifacts"):
                ui.label("Artifacts").classes("text-subtitle2 q-mt-sm")
                for artifact in detail["artifacts"]:
                    ui.link(
                        artifact["name"],
                        target=artifact["path"],
                    ).classes("text-body2")
