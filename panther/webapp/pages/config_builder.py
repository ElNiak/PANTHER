"""Config builder page — PydanticForm forms + YAML editor."""

import logging
from datetime import datetime
from typing import Any

from nicegui import ui

from panther.webapp.components.yaml_editor import YamlEditor
from panther.webapp.services.config_service import ConfigService

logger = logging.getLogger(__name__)


def _populate_forms_from_dict(panels: dict[str, Any], config_dict: dict) -> None:
    """Populate all form panels from a parsed config dict."""
    # Global sections
    for field_name, panel in panels.get("global", {}).items():
        section_data = config_dict.get(field_name)
        if section_data and isinstance(section_data, dict):
            panel.form.set_value(section_data)

    # Tests — load all tests (not just the first)
    tests = config_dict.get("tests")
    test_editor = panels.get("tests")
    if tests and isinstance(tests, list) and test_editor:
        test_editor.set_value([t for t in tests if isinstance(t, dict)])

    # Metadata
    meta = config_dict.get("metadata")
    meta_panel = panels.get("metadata")
    if meta and isinstance(meta, dict) and meta_panel:
        meta_panel.form.set_value(meta)


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
        ui.button(
            "Import YAML",
            icon="upload",
            on_click=lambda: _import_yaml_dialog(config_svc, _yaml_editor_ref),
        )
        ui.button(
            "Load Config File",
            icon="folder_open",
            on_click=lambda: _load_config_dialog(config_svc, _yaml_editor_ref),
        )
        ui.button(
            "Save Config File",
            icon="save",
            on_click=lambda: _save_config_dialog(
                config_svc, _yaml_editor_ref.get("editor")
            ),
        )


def _render_config_forms(yaml_editor_ref: dict):
    """Render PydanticForm panels for all config models with auto-sync to YAML."""
    from pydantic import BaseModel

    from panther.config.core.models.experiment import ExperimentMetadata
    from panther.config.core.models.global_config import GlobalConfig
    from panther.webapp.components.config_form_panel import config_form_panel
    from panther.webapp.components.error_boundary import error_boundary
    from panther.webapp.utils.form_models import GLOBAL_SECTION_META

    panels: dict[str, Any] = {"global": {}}

    # === Auto-walk GlobalConfig fields ===
    for field_name, field_info in GlobalConfig.model_fields.items():
        if field_name == "version":
            continue
        annotation = field_info.annotation
        if not (isinstance(annotation, type) and issubclass(annotation, BaseModel)):
            continue

        icon, desc = GLOBAL_SECTION_META.get(
            field_name, ("settings", field_info.description or "")
        )
        title = field_name.replace("_", " ").title()

        with ui.card().classes("w-full q-mb-md"):
            with error_boundary(f"{title} Config"):
                panels["global"][field_name] = config_form_panel(
                    annotation,
                    title=title,
                    icon=icon,
                    description=desc,
                )

    # === TestConfig (multi-test accordion) ===
    with ui.card().classes("w-full q-mb-md"):
        ui.label("Test Configuration").classes("text-h6")
        ui.label(
            "Configure tests. Expand a panel to edit, use buttons to add/remove/duplicate."
        ).classes("text-caption text-grey-7 q-mb-sm")
        with error_boundary("Test Config"):
            from panther.webapp.components.test_list_editor import TestListEditor

            test_editor = TestListEditor()
            test_editor.set_value([{}])  # Start with one empty test
            panels["tests"] = test_editor

    # === ExperimentMetadata ===
    with ui.card().classes("w-full q-mb-md"):
        with error_boundary("Experiment Metadata"):
            panels["metadata"] = config_form_panel(
                ExperimentMetadata,
                title="Experiment Metadata",
                icon="info",
                description="Optional experiment metadata (name, author, tags).",
            )

    # Prefill metadata form with sensible defaults (name, author, timestamps)
    panels["metadata"].form.set_value(ExperimentMetadata().model_dump())

    yaml_editor_ref["panels"] = panels
    yaml_editor_ref["_last_yaml"] = None

    def _sync_forms_to_yaml():
        try:
            editor = yaml_editor_ref.get("editor")
            if editor is None:
                return
            if yaml_editor_ref.pop("skip_sync", False):
                return
            config: dict[str, Any] = {}

            for section_name, panel in panels.get("global", {}).items():
                data = panel.form.get_value()
                if data:
                    config[section_name] = data

            test_editor = panels.get("tests")
            if test_editor:
                tests_data = test_editor.get_value()
                if tests_data:
                    for i, td in enumerate(tests_data):
                        if not td.get("name", "").strip():
                            generated = ConfigService.generate_test_name(td)
                            if generated:
                                td["name"] = generated
                                test_editor.update_form_field(i, "name", generated)
                        if not td.get("description", "").strip():
                            generated = ConfigService.generate_test_description(td)
                            if generated:
                                td["description"] = generated
                                test_editor.update_form_field(
                                    i, "description", generated
                                )
                    config["tests"] = tests_data

            meta_panel = panels.get("metadata")
            if meta_panel:
                data = meta_panel.form.get_value()
                if data:
                    config["metadata"] = data

            if config:
                import yaml

                yaml_str = yaml.dump(config, default_flow_style=False, sort_keys=False)
                if yaml_str == yaml_editor_ref.get("_last_yaml"):
                    return
                yaml_editor_ref["_last_yaml"] = yaml_str
                editor.value = yaml_str
        except Exception:
            logger.warning("Form-to-YAML sync error", exc_info=True)

    ui.timer(1.0, _sync_forms_to_yaml)


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

    field_errors = config_svc.validate_config_detailed(data)
    if field_errors:
        for err in field_errors[:10]:
            severity = "negative" if err.severity == "error" else "warning"
            ui.notify(f"{err.path}: {err.message}", type=severity)
    else:
        ui.notify("Configuration is valid", type="positive")


def _export(yaml_editor):
    """Export YAML content for download."""
    if yaml_editor is None:
        ui.notify("Switch to YAML tab first", type="warning")
        return
    yaml_content = yaml_editor.value
    if not yaml_content.strip():
        ui.notify("Nothing to export", type="warning")
        return
    # Stamp modified_at before exporting
    import yaml as _yaml

    data = _yaml.safe_load(yaml_content)
    if isinstance(data, dict):
        meta = data.setdefault("metadata", {})
        meta["modified_at"] = datetime.now().isoformat()
        yaml_content = _yaml.dump(data, default_flow_style=False, sort_keys=False)
    ui.download(yaml_content.encode(), "panther_config.yaml")


def _import_yaml_dialog(config_svc: ConfigService, yaml_editor_ref: dict):
    """Open a dialog to paste YAML and import into forms."""
    with ui.dialog() as dialog, ui.card().classes("w-[700px]"):
        ui.label("Import YAML Configuration").classes("text-h6")
        ui.label("Paste your YAML config below to populate the form fields.").classes(
            "text-caption text-grey-7"
        )
        textarea = ui.textarea("YAML content").classes("w-full").props("rows=16")

        def _do_import():
            text = textarea.value
            if not text or not text.strip():
                ui.notify("No YAML content provided", type="warning")
                return
            error = config_svc.validate_yaml(text)
            if error:
                ui.notify(f"Invalid config: {error}", type="negative")
                return
            # Update the YAML editor preview
            editor = yaml_editor_ref.get("editor")
            if editor:
                editor.value = text
            # Populate forms from the imported YAML
            data = config_svc.yaml_to_dict(text)
            panels = yaml_editor_ref.get("panels")
            if data and panels:
                _populate_forms_from_dict(panels, data)
            yaml_editor_ref["skip_sync"] = True
            dialog.close()
            ui.notify("Configuration imported into forms", type="positive")

        with ui.row().classes("justify-end w-full q-mt-sm"):
            ui.button("Cancel", on_click=dialog.close).props("flat")
            ui.button("Import", icon="upload", on_click=_do_import).props(
                "color=primary"
            )
    dialog.open()


def _load_config_dialog(config_svc: ConfigService, yaml_editor_ref: dict):
    """Open a dialog to load a config file from disk."""
    with ui.dialog() as dialog, ui.card().classes("w-[500px]"):
        ui.label("Load Config File").classes("text-h6")

        # Show available configs
        configs = config_svc.list_configs()
        if configs:
            ui.label("Available configs:").classes("text-subtitle2 q-mt-sm")
            config_select = ui.select(
                options={c["path"]: c["name"] for c in configs},
                label="Select a config file",
            ).classes("w-full")
        else:
            config_select = None
            ui.label("No configs found in default directory.").classes(
                "text-caption text-grey-6"
            )

        path_input = ui.input("Or enter file path").classes("w-full q-mt-sm")

        def _do_load():
            path = path_input.value or (config_select.value if config_select else "")
            if not path:
                ui.notify("No file path specified", type="warning")
                return
            try:
                data = config_svc.load_config(path)
                import yaml

                yaml_str = yaml.dump(data, default_flow_style=False, sort_keys=False)
                editor = yaml_editor_ref.get("editor")
                if editor:
                    editor.value = yaml_str
                # Populate forms from loaded data
                panels = yaml_editor_ref.get("panels")
                if panels:
                    _populate_forms_from_dict(panels, data)
                yaml_editor_ref["skip_sync"] = True
                dialog.close()
                ui.notify(f"Loaded: {path}", type="positive")
            except FileNotFoundError:
                ui.notify(f"File not found: {path}", type="negative")
            except ValueError as exc:
                ui.notify(f"Error: {exc}", type="negative")

        with ui.row().classes("justify-end w-full q-mt-sm"):
            ui.button("Cancel", on_click=dialog.close).props("flat")
            ui.button("Load", icon="folder_open", on_click=_do_load).props(
                "color=primary"
            )
    dialog.open()


def _save_config_dialog(config_svc: ConfigService, yaml_editor):
    """Open a dialog to save the current config to a file."""
    if yaml_editor is None:
        ui.notify("Switch to YAML tab first", type="warning")
        return
    yaml_content = yaml_editor.value
    if not yaml_content or not yaml_content.strip():
        ui.notify("No configuration to save", type="warning")
        return

    with ui.dialog() as dialog, ui.card().classes("w-[500px]"):
        ui.label("Save Config File").classes("text-h6")
        path_input = ui.input(
            "File path",
            value="experiment-config/base/my_config.yaml",
        ).classes("w-full")

        def _do_save():
            path = path_input.value
            if not path:
                ui.notify("No file path specified", type="warning")
                return
            # Parse fresh YAML content at save time (not stale closure)
            data = config_svc.yaml_to_dict(yaml_editor.value)
            if data is None:
                ui.notify("Invalid YAML — cannot save", type="negative")
                return
            # Stamp modified_at before writing
            meta = data.setdefault("metadata", {})
            meta["modified_at"] = datetime.now().isoformat()
            try:
                config_svc.save_config(path, data)
                dialog.close()
                ui.notify(f"Saved to: {path}", type="positive")
            except Exception as exc:
                ui.notify(f"Error saving: {exc}", type="negative")

        with ui.row().classes("justify-end w-full q-mt-sm"):
            ui.button("Cancel", on_click=dialog.close).props("flat")
            ui.button("Save", icon="save", on_click=_do_save).props("color=primary")
    dialog.open()
