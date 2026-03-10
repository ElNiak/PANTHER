"""Per-test drill-down panel for the Results page."""

import logging
from typing import Any

from nicegui import ui

from panther.webapp.components.error_boundary import error_boundary
from panther.webapp.components.event_viewer import event_viewer
from panther.webapp.components.service_log_browser import service_log_browser
from panther.webapp.components.status_badge import status_badge
from panther.webapp.services.results_service import ResultsService
from panther.webapp.utils.format_helpers import format_json

logger = logging.getLogger(__name__)


def test_detail_panel(
    results_svc: ResultsService,
    experiment_path: str,
    test_name: str,
):
    """Render a detailed view for a single test within an experiment.

    Shows: header with status, service log browser, analysis results,
    test artifacts, and test-level events.
    """
    detail = results_svc.get_test_detail(experiment_path, test_name)
    if not detail:
        ui.label("No details available for this test.").classes("text-grey-7")
        return

    info = detail.get("info", {})

    # --- Header ---
    with ui.row().classes("items-center gap-3 q-mb-md"):
        ui.label(test_name).classes("text-subtitle1 font-bold")
        status_badge(info.get("status", "unknown"))
        duration = info.get("duration")
        if duration is not None:
            ui.label(f"{duration:.1f}s").classes("text-caption text-grey-7")

    # Error message
    error_msg = info.get("error_message")
    if error_msg:
        # Strip ANSI escape codes for display
        import re

        clean_msg = re.sub(r"\x1b\[[0-9;]*m", "", error_msg).strip()
        with ui.card().classes("w-full bg-red-1 q-pa-sm q-mb-md"):
            ui.label("Error").classes("text-caption text-red-9 font-bold")
            ui.label(clean_msg).classes("text-body2 text-red-8")

    # --- Sub-tabs within the test detail ---
    with ui.tabs().classes("w-full") as test_tabs:
        svc_tab = ui.tab("Services & Logs", icon="dns")
        analysis_tab = ui.tab("Analysis", icon="analytics")
        events_tab = ui.tab("Events", icon="event")
        artifacts_tab = ui.tab("Artifacts", icon="folder_open")

    with ui.tab_panels(test_tabs, value=svc_tab).classes("w-full"):
        with ui.tab_panel(svc_tab):
            _render_services_tab(results_svc, experiment_path, test_name, detail)
        with ui.tab_panel(analysis_tab):
            _render_analysis_tab(detail)
        with ui.tab_panel(events_tab):
            _render_test_events_tab(results_svc, experiment_path, test_name)
        with ui.tab_panel(artifacts_tab):
            _render_test_artifacts_tab(detail)


def _render_services_tab(
    results_svc: ResultsService,
    experiment_path: str,
    test_name: str,
    detail: dict[str, Any],
):
    """Render service log browsers for this test."""
    with error_boundary("Service Logs"):
        services = detail.get("services", [])
        if not services:
            ui.label("No service logs found.").classes("text-grey-7")
            return

        for svc in services:
            service_log_browser(
                results_svc, experiment_path, test_name, svc["service_name"]
            )


def _render_analysis_tab(detail: dict[str, Any]):
    """Render analysis results (JSON) for this test."""
    with error_boundary("Analysis Results"):
        analysis = detail.get("analysis")
        if not analysis:
            ui.label("No analysis results found.").classes("text-grey-7")
            return

        for result_name, data in analysis.items():
            with ui.expansion(
                result_name.replace("_", " ").title(), icon="science"
            ).classes("w-full q-mb-sm"):
                # Show formatted summary if available
                if isinstance(data, dict) and "results" in data:
                    results = data["results"]
                    if isinstance(results, dict):
                        passed = results.get("passed", None)
                        if passed is not None:
                            badge_color = "green" if passed else "red"
                            badge_text = "Passed" if passed else "Failed"
                            ui.badge(badge_text, color=badge_color).classes("q-mb-sm")

                        summary_text = results.get("analysis_summary", "")
                        if summary_text:
                            ui.label(summary_text).classes(
                                "text-body2 text-grey-8 q-mb-sm"
                            )

                # Full JSON
                ui.code(format_json(data), language="json").classes("w-full").style(
                    "max-height: 400px; overflow: auto"
                )


def _render_test_events_tab(
    results_svc: ResultsService, experiment_path: str, test_name: str
):
    """Render events for this specific test."""
    with error_boundary("Test Events"):
        events = results_svc.get_test_events(experiment_path, test_name)
        if not events:
            ui.label("No events recorded for this test.").classes("text-grey-7")
            return
        event_viewer(events)


def _render_test_artifacts_tab(detail: dict[str, Any]):
    """Render test-level artifacts."""
    with error_boundary("Test Artifacts"):
        artifacts = detail.get("artifacts", [])
        if not artifacts:
            ui.label("No artifacts found.").classes("text-grey-7")
            return

        for artifact in artifacts:
            with ui.row().classes("items-center gap-2 q-py-xs"):
                ui.icon("insert_drive_file", size="sm").classes("text-grey-7")
                ui.label(artifact["name"]).classes("text-body2")
