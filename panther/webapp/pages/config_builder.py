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

    _yaml_editor_ref = {}  # Shared reference between tabs

    with ui.tabs().classes("w-full") as tabs:
        form_tab = ui.tab("Form Editor", icon="edit")
        yaml_tab = ui.tab("YAML Preview", icon="code")

    with ui.tab_panels(tabs, value=form_tab).classes("w-full"):
        with ui.tab_panel(form_tab):
            ui.label("Configure your experiment using the form below.").classes(
                "text-body2 text-grey-7 q-mb-md"
            )
            _render_config_forms(_yaml_editor_ref)

        with ui.tab_panel(yaml_tab):
            ui.label("YAML preview of the current configuration.").classes(
                "text-body2 text-grey-7 q-mb-md"
            )
            yaml_editor = YamlEditor(
                initial_value=config_svc.get_default_yaml(),
                on_change=lambda val: _on_yaml_change(val, config_svc),
            )
            _yaml_editor_ref["editor"] = yaml_editor

    ui.separator().classes("q-my-md")

    with ui.row().classes("gap-3"):
        ui.button(
            "Validate",
            icon="check_circle",
            on_click=lambda: _validate(config_svc, _yaml_editor_ref.get("editor")),
        )
        ui.button(
            "Export YAML",
            icon="download",
            on_click=lambda: _export(_yaml_editor_ref.get("editor")),
        )


def _render_config_forms(yaml_editor_ref: dict):
    """Render NiceCRUD panels for all config models with auto-sync to YAML."""
    from niceguicrud import NiceCRUD, NiceCRUDConfig

    from panther.config.core.models.global_config import (
        DockerConfig,
        FastFailConfig,
        LoggingConfig,
        MetricsConfig,
        PathsConfig,
        ProgressConfig,
    )
    from panther.webapp.components.config_form_panel import config_form_panel
    from panther.webapp.components.error_boundary import error_boundary
    from panther.webapp.utils.form_models import TestConfigForm

    cruds = {}

    # Card: Core Settings
    with ui.card().classes("w-full q-mb-md"):
        ui.label("Core Settings").classes("text-h6")
        ui.label("Logging format, paths, and output directories.").classes(
            "text-caption text-grey-7 q-mb-sm"
        )
        with error_boundary("Logging Config"):
            cruds["logging"] = config_form_panel(
                LoggingConfig,
                "level",
                "Logging",
                icon="description",
                description="Global log level and format settings.",
            )
        with error_boundary("Paths Config"):
            cruds["paths"] = config_form_panel(
                PathsConfig,
                "output_dir",
                "Paths",
                icon="folder",
                description="Output, log, and plugin directory paths.",
            )

    # Card: Docker Settings
    with ui.card().classes("w-full q-mb-md"):
        ui.label("Docker Settings").classes("text-h6")
        ui.label(
            "Docker build options and user mapping (flattened from nested config)."
        ).classes("text-caption text-grey-7 q-mb-sm")
        with error_boundary("Docker Config"):
            cruds["docker"] = config_form_panel(
                DockerConfig,
                "force_build_docker_image",
                "Docker",
                icon="dns",
                description="Build flags, Buildx, and user mapping configuration.",
            )

    # Card: Execution Behavior
    with ui.card().classes("w-full q-mb-md"):
        ui.label("Execution Behavior").classes("text-h6")
        ui.label("Progress display, fast-fail, and metrics collection.").classes(
            "text-caption text-grey-7 q-mb-sm"
        )
        with error_boundary("Progress Config"):
            cruds["progress"] = config_form_panel(
                ProgressConfig,
                "enable_progress_bar",
                "Progress",
                icon="hourglass_top",
                description="Progress bar and spinner display options.",
            )
        with error_boundary("Fast Fail Config"):
            cruds["fast_fail"] = config_form_panel(
                FastFailConfig,
                "enabled",
                "Fast Fail",
                icon="flash_on",
                description="Stop execution early on critical failures.",
            )
        with error_boundary("Metrics Config"):
            cruds["metrics"] = config_form_panel(
                MetricsConfig,
                "enabled",
                "Metrics",
                icon="monitoring",
                description="System metrics collection and export.",
            )

    # Card: Test Configuration
    with ui.card().classes("w-full q-mb-md"):
        ui.label("Test Configuration").classes("text-h6")
        ui.label(
            "Test parameters. Complex fields (services, execution environment) are edited in YAML."
        ).classes("text-caption text-grey-7 q-mb-sm")
        with error_boundary("Test Config"):
            with ui.expansion("Test Settings", icon="science").classes("w-full"):
                cruds["test"] = NiceCRUD(
                    TestConfigForm, config=NiceCRUDConfig(id_field="name")
                )

    def _sync_forms_to_yaml():
        try:
            editor = yaml_editor_ref.get("editor")
            if editor is None:
                return
            config = {}
            for key, crud in cruds.items():
                items = crud.basemodels
                if items:
                    dumped = [item.model_dump() for item in items]
                    data = dumped[0] if len(dumped) == 1 else dumped
                    if isinstance(data, dict):
                        data = _unflatten_dict(data)
                    config[key] = data
            if config:
                import yaml

                editor.value = yaml.dump(
                    config, default_flow_style=False, sort_keys=False
                )
        except Exception:
            pass  # Silent fail -- YAML preview is secondary

    ui.timer(1.0, _sync_forms_to_yaml)


def _unflatten_dict(d: dict) -> dict:
    """Reconstruct nested dicts from ``prefix__field`` keys in form output."""
    from panther.webapp.utils.form_models import unflatten_dict

    return unflatten_dict(d)


def _on_yaml_change(value: str, config_svc: ConfigService):
    """Handle YAML editor changes."""
    errors = config_svc.validate_yaml(value)
    if errors:
        logger.debug("YAML validation errors: %s", errors)


def _validate(config_svc: ConfigService, yaml_editor):
    """Validate the current YAML config."""
    if yaml_editor is None:
        ui.notify("Switch to YAML tab first", type="warning")
        return
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


def _export(yaml_editor):
    """Export YAML content for download."""
    if yaml_editor is None:
        ui.notify("Switch to YAML tab first", type="warning")
        return
    content = yaml_editor.value
    if not content.strip():
        ui.notify("Nothing to export", type="warning")
        return
    ui.download(content.encode(), "panther_config.yaml")
