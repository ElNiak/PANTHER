"""Service health card component."""

from nicegui import ui

from panther.webapp.components.status_badge import status_badge


def service_health_card(service: dict):
    """Card showing service name, status badge, exit code, error summary.

    Args:
        service: Dict with keys: service_name, service_type, status, exit_code,
                 error_summary, and optionally test_name.
    """
    with ui.card().classes("w-full q-pa-sm"):
        with ui.row().classes("items-center gap-2"):
            ui.label(service.get("service_name", "Unknown")).classes("text-subtitle2")
            status_badge(service.get("status", "unknown"))

        with ui.column().classes("gap-1 q-mt-xs"):
            test_name = service.get("test_name")
            if test_name:
                ui.badge(test_name, color="blue-grey").props("outline").classes(
                    "text-caption q-mb-xs"
                )
            ui.label(f"Type: {service.get('service_type', 'N/A')}").classes(
                "text-caption text-grey-7"
            )
            exit_code = service.get("exit_code")
            if exit_code is not None:
                ui.label(f"Exit code: {exit_code}").classes("text-caption text-grey-7")
            error = service.get("error_summary")
            if error:
                ui.label(f"Error: {error}").classes("text-caption text-red-7")
