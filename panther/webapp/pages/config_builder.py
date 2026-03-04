"""Config builder page — NiceCRUD forms + YAML editor."""

import logging

from nicegui import ui

from panther.webapp.components.yaml_editor import YamlEditor
from panther.webapp.services.config_service import ConfigService

logger = logging.getLogger(__name__)


def content():
    """Render the config builder page content."""
    config_svc = ConfigService()

    ui.label("Experiment Configuration Builder").classes("text-h5 q-mb-md")

    with ui.tabs().classes("w-full") as tabs:
        form_tab = ui.tab("Form Editor", icon="edit")
        yaml_tab = ui.tab("YAML Preview", icon="code")

    with ui.tab_panels(tabs, value=form_tab).classes("w-full"):
        with ui.tab_panel(form_tab):
            ui.label("Configure your experiment using the form below.").classes(
                "text-body2 text-grey-7 q-mb-md"
            )
            # NiceCRUD form placeholder — wire up NiceCRUD here
            # Example:
            #   from niceguicrud import NiceCRUD
            #   from panther.config.core.models import GlobalConfig
            #   crud = NiceCRUD(model=GlobalConfig, ...)
            #   crud.ui()
            _render_basic_form(config_svc)

        with ui.tab_panel(yaml_tab):
            ui.label("YAML preview of the current configuration.").classes(
                "text-body2 text-grey-7 q-mb-md"
            )
            yaml_editor = YamlEditor(
                initial_value=config_svc.get_default_yaml(),
                on_change=lambda val: _on_yaml_change(val, config_svc),
            )

    ui.separator().classes("q-my-md")

    with ui.row().classes("gap-3"):
        ui.button(
            "Validate",
            icon="check_circle",
            on_click=lambda: _validate(config_svc, yaml_editor),
        )
        ui.button(
            "Export YAML",
            icon="download",
            on_click=lambda: _export(yaml_editor),
        )


def _render_basic_form(config_svc: ConfigService):
    """Render a basic config form. Placeholder for NiceCRUD integration."""
    with ui.card().classes("w-full q-pa-md"):
        ui.label("Global Settings").classes("text-subtitle1 q-mb-sm")

        with ui.column().classes("gap-2 w-full"):
            ui.select(
                label="Log Level",
                options=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
                value="INFO",
            )
            ui.input(label="Output Directory", value="outputs")
            ui.checkbox("Force Docker Build", value=True)
            ui.checkbox("Enable Metrics", value=True)

        ui.label("Test Configuration").classes("text-subtitle1 q-mt-md q-mb-sm")
        ui.label(
            "Use the YAML editor tab for full test configuration, "
            "or integrate NiceCRUD forms here."
        ).classes("text-caption text-grey-7")


def _on_yaml_change(value: str, config_svc: ConfigService):
    """Handle YAML editor changes."""
    errors = config_svc.validate_yaml(value)
    if errors:
        logger.debug("YAML validation errors: %s", errors)


def _validate(config_svc: ConfigService, yaml_editor: YamlEditor):
    """Validate the current YAML config."""
    error = yaml_editor.validate()
    if error:
        ui.notify(f"Invalid YAML syntax: {error}", type="negative")
        return

    data = yaml_editor.get_as_dict()
    if data is None:
        ui.notify("Empty configuration", type="warning")
        return

    errors = config_svc.validate_yaml(yaml_editor.value)
    if errors:
        ui.notify(f"Config validation errors: {errors}", type="negative")
    else:
        ui.notify("Configuration is valid", type="positive")


def _export(yaml_editor: YamlEditor):
    """Export YAML content for download."""
    content = yaml_editor.value
    if not content.strip():
        ui.notify("Nothing to export", type="warning")
        return
    ui.download(content.encode(), "panther_config.yaml")
