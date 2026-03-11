"""ServiceHealthCard — compact service status display.

Renders a NiceGUI card summarising the health of a single service
(IUT or tester) from a completed PANTHER (Protocol ANalysis and Testing
Harness for Extensible Research) experiment.  The card shows the service
name, a colour-coded status badge, the service type, exit code, and any
error summary.  An optional test-name badge links the service to the
test it participated in.

Used by the results dashboard to give an at-a-glance overview of all
services that ran during an experiment.
"""

from nicegui import ui

from panther.webapp.components.status.status_badge import status_badge


def service_health_card(service: dict):
    """Render a card showing service name, status badge, exit code, and errors.

    Args:
        service: Dictionary describing a service instance with keys:

            * ``service_name`` (str) — display name (e.g. ``"picoquic_server"``).
            * ``service_type`` (str) — ``"iut"`` or ``"tester"``.
            * ``status`` (str) — lifecycle status (``"completed"``,
              ``"failed"``, ``"running"``, etc.).
            * ``exit_code`` (int | None) — process exit code, if available.
            * ``error_summary`` (str | None) — one-line error description.
            * ``test_name`` (str | None) — optional test association.
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
