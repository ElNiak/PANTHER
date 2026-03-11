"""Config builder page -- dual-mode experiment configuration editor.

Provides synchronized PydanticForm-based forms and a raw YAML preview.

This page enables users to build PANTHER (Protocol ANalyzer and THreat
Evaluator for Research) experiment configurations through two
complementary interfaces:

**Dual-tab architecture:**

1. **Form Editor tab** -- auto-generated forms derived from Pydantic
   models (``GlobalConfig``, ``TestConfig``, ``ExperimentMetadata``).
   Each ``GlobalConfig`` field that is itself a ``BaseModel`` gets its
   own ``config_form_panel`` card.  The test section uses a
   ``TestListEditor`` supporting add / remove / duplicate operations.

2. **YAML Preview tab** -- a ``YamlEditor`` (CodeMirror-based) showing
   the live YAML representation.  Edits here are validated on every
   keystroke via ``ConfigService.validate_yaml()``.

**Form-to-YAML synchronisation:**
A ``ui.timer`` fires every 1 second and serialises the current form
state into YAML, writing it into the editor.  A ``skip_sync`` flag
prevents feedback loops when the user imports or loads YAML (those
paths populate forms and set the flag so the next timer tick is a
no-op).  A ``_sync_failures`` counter prevents log-spam on repeated
errors.

**YAML-to-form synchronisation (import / load):**
``_populate_forms_from_dict()`` walks the parsed config dict and calls
``panel.form.set_value()`` for each section.  Test data goes through
``TestListEditor.set_value()``.

**Action buttons:**
    * *Validate* -- runs ``ConfigService.validate_config_detailed()``
      and shows per-field notifications.
    * *Export YAML* -- triggers a browser download, stamping
      ``metadata.modified_at``.
    * *Import YAML* -- opens a paste dialog, validates, then populates
      both forms and the YAML editor.
    * *Load Config File* -- lists configs from disk (via
      ``ConfigService.list_configs()``), loads one, and populates.
    * *Save Config File* -- writes the current YAML to disk via
      ``ConfigService.save_config()``.

NiceGUI patterns used:
    * ``ui.tabs`` / ``ui.tab_panels`` for the dual-tab layout.
    * ``ui.timer(1.0, ...)`` for periodic form-to-YAML sync.
    * ``ui.dialog`` for modal import / load / save workflows.
    * ``ui.download`` for client-side file export.
"""

import logging
from datetime import datetime
from typing import Any

from nicegui import ui

from panther.config.core.models.experiment import TestConfig
from panther.webapp.components.yaml_editor import YamlEditor
from panther.webapp.services.config_service import ConfigService

logger = logging.getLogger(__name__)


def _populate_forms_from_dict(panels: dict[str, Any], config_dict: dict) -> None:
    """Populate all form panels from a parsed config dict.

    Walks the three panel groups (``global``, ``tests``, ``metadata``)
    stored in *panels* and pushes values from *config_dict* into each
    panel's underlying ``PydanticForm``.

    Args:
        panels: A dict with keys ``"global"`` (mapping field names to
            form panels), ``"tests"`` (a ``TestListEditor``), and
            ``"metadata"`` (a single form panel).
        config_dict: A parsed experiment configuration dictionary,
            typically the output of ``yaml.safe_load()`` or
            ``ConfigService.yaml_to_dict()``.
    """
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
    """Render the config builder page content.

    Called by the NiceGUI router when the user navigates to ``/config``.
    The layout is built in three layers:

    1. **Tab bar** -- ``ui.tabs`` with *Form Editor* and *YAML Preview*.
    2. **Tab panels** -- *Form Editor* delegates to
       ``_render_config_forms()``; *YAML Preview* instantiates a
       ``YamlEditor`` seeded with default YAML from
       ``ConfigService.get_default_yaml()``.
    3. **Action bar** -- Validate, Export, Import, Load, and Save
       buttons, each dispatching to a private helper.

    A mutable ``_yaml_editor_ref`` dict is shared between the form
    panel builder and the YAML editor so that the timer-based sync
    and the action helpers can access both.
    """
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
    """Render PydanticForm panels for all config models with auto-sync to YAML.

    Dynamically walks ``GlobalConfig.model_fields`` to discover Pydantic
    sub-models and creates a ``config_form_panel`` for each.  The test
    section uses a ``TestListEditor`` (multi-item accordion), and
    ``ExperimentMetadata`` gets a standalone panel pre-filled with
    defaults.

    Registers a 1-second ``ui.timer`` that serialises the current form
    state to YAML and writes it into the YAML editor (if one exists).
    Auto-generates ``TestConfig.name`` and ``TestConfig.description``
    for tests that lack them.

    Args:
        yaml_editor_ref: Shared mutable dict used to exchange references
            between the form builder, the YAML editor, and the action
            buttons.  Populated keys: ``"panels"``, ``"_last_yaml"``,
            ``"_sync_failures"``, and (later) ``"editor"``.
    """
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
    yaml_editor_ref["_sync_failures"] = 0

    def _sync_forms_to_yaml():
        """Serialise form state to YAML and push it into the editor."""
        import yaml

        # Skip sync when YAML tab is active (user may be editing)
        if yaml_editor_ref.pop("skip_sync", False):
            return
        editor = yaml_editor_ref.get("editor")
        if editor is None:
            return
        try:
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
                            generated = TestConfig.generate_default_name(td)
                            if generated:
                                td["name"] = generated
                                test_editor.update_form_field(i, "name", generated)
                        if not td.get("description", "").strip():
                            generated = TestConfig.generate_default_description(td)
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
                yaml_str = yaml.dump(config, default_flow_style=False, sort_keys=False)
                if yaml_str == yaml_editor_ref.get("_last_yaml"):
                    return
                yaml_editor_ref["_last_yaml"] = yaml_str
                editor.value = yaml_str
            yaml_editor_ref["_sync_failures"] = 0
        except (yaml.YAMLError, AttributeError, KeyError, TypeError) as exc:
            yaml_editor_ref["_sync_failures"] = (
                yaml_editor_ref.get("_sync_failures", 0) + 1
            )
            if yaml_editor_ref["_sync_failures"] <= 3:
                logger.warning("Form-to-YAML sync error: %s", exc)
        except Exception:
            # Unexpected error — log once, stop retrying
            yaml_editor_ref["_sync_failures"] = (
                yaml_editor_ref.get("_sync_failures", 0) + 1
            )
            if yaml_editor_ref["_sync_failures"] <= 1:
                logger.error("Unexpected form-to-YAML sync error", exc_info=True)

    ui.timer(1.0, _sync_forms_to_yaml)


def _on_yaml_change(value: str, config_svc: ConfigService):
    """Handle YAML editor keystroke changes by running lightweight validation.

    Called on every ``on_change`` event from the ``YamlEditor``.
    Validation errors are logged at DEBUG level (not surfaced to the
    user) to avoid notification spam while typing.

    Args:
        value: The current raw YAML string from the editor.
        config_svc: The configuration service used for validation.
    """
    errors = config_svc.validate_yaml(value)
    if errors:
        logger.debug("YAML validation errors: %s", errors)


def _validate(config_svc: ConfigService, yaml_editor):
    """Validate the current YAML config and display per-field notifications.

    Performs a two-stage validation:

    1. **Syntax check** -- ``yaml_editor.validate()`` to catch YAML
       parse errors.
    2. **Schema check** -- ``config_svc.validate_config_detailed()``
       which runs Pydantic validation against the full config model
       tree and returns structured ``FieldError`` objects.

    Up to 10 errors are shown as NiceGUI toast notifications.

    Args:
        config_svc: The configuration service with validation logic.
        yaml_editor: The ``YamlEditor`` instance (may be ``None`` if
            the YAML tab has not been visited yet).
    """
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
    """Export the current YAML content as a downloadable file.

    Before exporting, the ``metadata.modified_at`` timestamp is updated
    to the current ISO-8601 datetime.  Uses ``ui.download()`` to push
    the file to the browser as ``panther_config.yaml``.

    Args:
        yaml_editor: The ``YamlEditor`` instance (may be ``None``).
    """
    if yaml_editor is None:
        ui.notify("Switch to YAML tab first", type="warning")
        return
    yaml_content = yaml_editor.value
    if not yaml_content.strip():
        ui.notify("Nothing to export", type="warning")
        return
    # Stamp modified_at before exporting
    import yaml as _yaml

    try:
        data = _yaml.safe_load(yaml_content)
    except _yaml.YAMLError as exc:
        ui.notify(f"Invalid YAML — exporting raw content: {exc}", type="warning")
        data = None
    if isinstance(data, dict):
        meta = data.setdefault("metadata", {})
        meta["modified_at"] = datetime.now().isoformat()
        yaml_content = _yaml.dump(data, default_flow_style=False, sort_keys=False)
    ui.download(yaml_content.encode(), "panther_config.yaml")


def _import_yaml_dialog(config_svc: ConfigService, yaml_editor_ref: dict):
    """Open a modal dialog for pasting raw YAML to import into forms.

    The dialog contains a multi-line textarea and an *Import* button.
    On import the YAML is validated, then pushed into the YAML editor
    and the form panels via ``_populate_forms_from_dict()``.  The
    ``skip_sync`` flag is set to prevent the timer from overwriting the
    freshly imported YAML on the next tick.

    Args:
        config_svc: The configuration service (used for validation and
            YAML-to-dict conversion).
        yaml_editor_ref: Shared mutable reference dict containing the
            YAML editor and form panels.
    """
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
    """Open a modal dialog listing on-disk config files to load.

    Presents a ``ui.select`` dropdown populated by
    ``ConfigService.list_configs()`` and an optional manual path input.
    On load the file is parsed, serialised back to YAML, and pushed
    into both the editor and the form panels.

    Args:
        config_svc: The configuration service (used for listing and
            loading config files).
        yaml_editor_ref: Shared mutable reference dict containing the
            YAML editor and form panels.
    """
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
    """Open a modal dialog to write the current configuration to disk.

    Re-parses the YAML content at save time (not from a stale closure)
    and stamps ``metadata.modified_at`` before writing via
    ``ConfigService.save_config()``.

    Args:
        config_svc: The configuration service (used for saving).
        yaml_editor: The ``YamlEditor`` instance (may be ``None``).
    """
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
