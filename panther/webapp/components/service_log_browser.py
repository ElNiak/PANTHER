"""Per-service, per-phase log browser component."""

import logging
from typing import Optional

from nicegui import ui

from panther.webapp.components.error_boundary import error_boundary
from panther.webapp.services.results_service import ResultsService

logger = logging.getLogger(__name__)

_PHASE_ICONS = {
    "pre-compile": "build_circle",
    "compile": "build",
    "post-compile": "check_circle",
    "pre-run": "play_circle",
    "runtime": "play_arrow",
    "post-run": "stop_circle",
    "test": "science",
    "artifacts": "inventory_2",
}


def service_log_browser(
    results_svc: ResultsService,
    experiment_path: str,
    test_name: str,
    service_name: str,
):
    """Accordion-based log browser for a single service.

    Top-level: service name with expand to show phases.
    Each phase: tabs for stdout / stderr shown in code blocks.
    """
    with error_boundary(f"Service: {service_name}"):
        logs = results_svc.get_service_logs(experiment_path, test_name, service_name)

        phase_count = len(logs)
        with ui.expansion(
            f"{service_name} ({phase_count} phases)",
            icon="dns",
        ).classes("w-full q-mb-sm"):
            if not logs:
                ui.label("No logs available.").classes("text-grey-7")
                return

            for phase_name, phase_data in logs.items():
                _render_phase(phase_name, phase_data)


def _render_phase(phase_name: str, phase_data: dict[str, Optional[str]]):
    """Render a single phase's logs within an expansion panel."""
    icon = _PHASE_ICONS.get(phase_name, "description")
    stdout = phase_data.get("stdout")
    stderr = phase_data.get("stderr")
    comp_status = phase_data.get("compilation_status")

    # Count non-empty logs
    log_parts = []
    if stdout:
        log_parts.append("stdout")
    if stderr:
        log_parts.append("stderr")
    label = f"{phase_name}"
    if log_parts:
        label += f" [{', '.join(log_parts)}]"

    with ui.expansion(label, icon=icon).classes("w-full q-ml-md q-mb-xs"):
        # Compilation status inline
        if comp_status and comp_status.strip():
            with ui.row().classes("items-center gap-2 q-mb-sm"):
                ui.icon("info", size="xs").classes("text-blue-7")
                ui.label(f"Compilation status: {comp_status.strip()}").classes(
                    "text-caption text-blue-8"
                )

        if not stdout and not stderr:
            ui.label("Empty logs.").classes("text-caption text-grey-5")
            return

        # Tabs for stdout/stderr
        if stdout and stderr:
            with ui.tabs().classes("w-full").props("dense") as log_tabs:
                stdout_tab = ui.tab("stdout")
                stderr_tab = ui.tab("stderr")

            with ui.tab_panels(log_tabs, value=stdout_tab).classes("w-full"):
                with ui.tab_panel(stdout_tab):
                    _render_log_content(stdout)
                with ui.tab_panel(stderr_tab):
                    _render_log_content(stderr, is_stderr=True)
        elif stdout:
            ui.label("stdout").classes("text-caption text-grey-6 q-mb-xs")
            _render_log_content(stdout)
        elif stderr:
            ui.label("stderr").classes("text-caption text-grey-6 q-mb-xs")
            _render_log_content(stderr, is_stderr=True)


def _render_log_content(content: str, is_stderr: bool = False):
    """Render log content in a scrollable code block."""
    # Limit display to last 500 lines for performance
    lines = content.splitlines()
    if len(lines) > 500:
        content = f"... ({len(lines) - 500} lines truncated) ...\n" + "\n".join(
            lines[-500:]
        )

    with ui.scroll_area().style("max-height: 300px"):
        ui.code(content).classes("w-full")
