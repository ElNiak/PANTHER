"""Config builder page — NiceCRUD forms + YAML editor."""

import logging
from typing import Any

from nicegui import ui

from panther.webapp.components.yaml_editor import YamlEditor
from panther.webapp.services.config_service import ConfigService

logger = logging.getLogger(__name__)


def _populate_forms_from_dict(cruds: dict[str, Any], config_dict: dict) -> None:
    """Populate all form panels from a parsed config dict."""
    from pydantic import BaseModel

    from panther.config.core.models.experiment import ExperimentMetadata, TestConfig
    from panther.config.core.models.global_config import GlobalConfig
    from panther.webapp.utils.form_models import (
        dict_to_form_instance,
        populate_panel_from_dict,
        split_simple_and_complex,
    )

    # Global sections
    for field_name, panel in cruds.get("global", {}).items():
        section_data = config_dict.get(field_name)
        if section_data and isinstance(section_data, dict):
            annotation = GlobalConfig.model_fields[field_name].annotation
            if isinstance(annotation, type) and issubclass(annotation, BaseModel):
                populate_panel_from_dict(panel, annotation, section_data)

    # Tests
    tests = config_dict.get("tests")
    tests_panel = cruds.get("tests")
    if tests and isinstance(tests, list) and tests_panel:
        models = []
        for t in tests:
            if isinstance(t, dict):
                simple, _ = split_simple_and_complex(TestConfig, t)
                instance = dict_to_form_instance(TestConfig, simple)
                models.append(instance)
        if models:
            tests_panel.crud.basemodels = models
        # Populate widgets from first test's complex fields
        if isinstance(tests[0], dict):
            _, complex_data = split_simple_and_complex(TestConfig, tests[0])
            for fname, widget in tests_panel.widgets.items():
                if fname in complex_data:
                    widget.set_value(complex_data[fname])

    # Metadata
    meta = config_dict.get("metadata")
    meta_panel = cruds.get("metadata")
    if meta and isinstance(meta, dict) and meta_panel:
        populate_panel_from_dict(meta_panel, ExperimentMetadata, meta)


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
    """Render NiceCRUD panels for all config models with auto-sync to YAML."""
    from niceguicrud import NiceCRUD, NiceCRUDConfig
    from pydantic import BaseModel

    from panther.config.core.models.experiment import ExperimentMetadata, TestConfig
    from panther.config.core.models.global_config import GlobalConfig
    from panther.webapp.components.config_form_panel import (
        FormPanelResult,
        config_form_panel,
    )
    from panther.webapp.components.dict_list_widgets import create_widget_for_field
    from panther.webapp.components.error_boundary import error_boundary
    from panther.webapp.utils.form_models import (
        GLOBAL_SECTION_META,
        build_form_model,
        get_complex_fields,
    )

    cruds: dict[str, Any] = {"global": {}}

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
                cruds["global"][field_name] = config_form_panel(
                    annotation,
                    title=title,
                    icon=icon,
                    description=desc,
                    pre_populate=True,
                    singleton=True,
                )

    # === TestConfig (auto-generated from model) ===
    with ui.card().classes("w-full q-mb-md"):
        ui.label("Test Configuration").classes("text-h6")
        ui.label("Test parameters. Add tests and configure their settings.").classes(
            "text-caption text-grey-7 q-mb-sm"
        )
        with error_boundary("Test Config"):
            TestFormModel = build_form_model(TestConfig)
            test_widgets: dict[str, Any] = {}
            with ui.expansion("Test Settings", icon="science").classes("w-full"):
                test_crud = NiceCRUD(
                    TestFormModel,
                    basemodels=[],
                    config=NiceCRUDConfig(id_field="name"),
                )
                # Render custom widgets for complex TestConfig fields
                complex = get_complex_fields(TestConfig)
                if complex:
                    ui.separator().classes("q-my-sm")
                    for fname, info in complex.items():
                        test_widgets[fname] = create_widget_for_field(fname, info)

            cruds["tests"] = FormPanelResult(crud=test_crud, widgets=test_widgets)

    # === ExperimentMetadata ===
    with ui.card().classes("w-full q-mb-md"):
        with error_boundary("Experiment Metadata"):
            cruds["metadata"] = config_form_panel(
                ExperimentMetadata,
                title="Experiment Metadata",
                icon="info",
                description="Optional experiment metadata (name, author, tags).",
                pre_populate=True,
                singleton=True,
            )

    # === Plugin Config (dynamic) ===
    with ui.card().classes("w-full q-mb-md"):
        ui.label("Plugin Configuration").classes("text-h6")
        ui.label("Select a plugin to configure its settings.").classes(
            "text-caption text-grey-7 q-mb-sm"
        )
        with error_boundary("Plugin Config"):
            _render_plugin_config_section()

    yaml_editor_ref["cruds"] = cruds

    def _sync_forms_to_yaml():
        try:
            editor = yaml_editor_ref.get("editor")
            if editor is None:
                return
            # Skip one sync cycle after import/load to preserve full YAML
            if yaml_editor_ref.pop("skip_sync", False):
                return
            config: dict[str, Any] = {}

            # Global sections — each is a single pre-populated instance
            for section_name, panel in cruds.get("global", {}).items():
                items = panel.crud.basemodels
                if items:
                    data = items[0].model_dump()
                    for wf_name, widget in panel.widgets.items():
                        data[wf_name] = widget.get_value()
                    config[section_name] = data

            # Tests — list of dicts
            tests_panel = cruds.get("tests")
            if tests_panel and tests_panel.crud.basemodels:
                tests_list = []
                for item in tests_panel.crud.basemodels:
                    test_data = item.model_dump()
                    for wf_name, widget in tests_panel.widgets.items():
                        test_data[wf_name] = widget.get_value()
                    tests_list.append(test_data)
                config["tests"] = tests_list

            # Metadata
            meta_panel = cruds.get("metadata")
            if meta_panel and meta_panel.crud.basemodels:
                data = meta_panel.crud.basemodels[0].model_dump()
                for wf_name, widget in meta_panel.widgets.items():
                    data[wf_name] = widget.get_value()
                config["metadata"] = data

            if config:
                import yaml

                editor.value = yaml.dump(
                    config, default_flow_style=False, sort_keys=False
                )
        except Exception:
            pass  # Silent fail — YAML preview is secondary

    ui.timer(1.0, _sync_forms_to_yaml)


def _render_plugin_config_section():
    """Render a dropdown of available plugins and their config forms."""
    from panther.webapp.utils.plugin_forms import (
        get_plugin_form_info,
        list_available_plugins,
    )

    plugins = list_available_plugins()
    if not plugins:
        ui.label("No plugins discovered.").classes("text-caption text-grey-6")
        return

    plugin_names = [p["name"] for p in plugins]
    form_container = ui.column().classes("w-full")

    def _on_plugin_selected(e):
        form_container.clear()
        name = e.value
        if not name:
            return
        try:
            info = get_plugin_form_info(name)
            if info is None:
                with form_container:
                    ui.label(f"No config schema found for '{name}'.").classes(
                        "text-caption text-grey-6"
                    )
                return
            with form_container:
                if info.description:
                    ui.label(info.description).classes(
                        "text-caption text-grey-7 q-mb-sm"
                    )
                from niceguicrud import NiceCRUD, NiceCRUDConfig

                NiceCRUD(
                    info.form_model,
                    basemodels=[info.form_model()],
                    config=NiceCRUDConfig(id_field=info.id_field),
                )
                # Render custom widgets for complex fields
                if info.complex_fields:
                    from panther.webapp.components.dict_list_widgets import (
                        create_widget_for_field,
                    )

                    ui.separator().classes("q-my-sm")
                    for fname, finfo in info.complex_fields.items():
                        create_widget_for_field(fname, finfo)
        except Exception as exc:
            with form_container:
                ui.label(f"Error loading plugin '{name}': {exc}").classes(
                    "text-caption text-red-7"
                )

    ui.select(
        options=plugin_names,
        label="Select plugin",
        on_change=_on_plugin_selected,
    ).classes("w-full q-mb-sm")


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
            cruds = yaml_editor_ref.get("cruds")
            if data and cruds:
                _populate_forms_from_dict(cruds, data)
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
                cruds = yaml_editor_ref.get("cruds")
                if cruds:
                    _populate_forms_from_dict(cruds, data)
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
