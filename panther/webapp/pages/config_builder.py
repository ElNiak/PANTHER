"""Config builder page -- dual-mode experiment configuration editor.

Provides synchronized PydanticForm-based forms and a raw YAML preview.

This page enables users to build PANTHER (Protocol ANalysis and Testing
Harness for Extensible Research) experiment configurations through two
complementary interfaces:

**Dual-tab architecture:**

1. **Form Editor tab** -- auto-generated forms derived from Pydantic
   models (``GlobalConfig``, ``TestConfig``, ``ExperimentMetadata``).
   Each ``GlobalConfig`` field that is itself a ``BaseModel`` gets its
   own ``config_form_panel`` card.  The test section uses a
   ``TestListEditor`` supporting add / remove / duplicate operations.

2. **YAML Preview tab** -- a ``YamlEditor`` (CodeMirror-based) showing
   the live YAML representation.  Edits are validated periodically
   (1-second timer) and on explicit actions via
   ``ConfigService.validate_yaml()``.

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
import re
from datetime import datetime, timezone
from typing import Any

from nicegui import ui

from panther.config.core.models.experiment import TestConfig
from panther.webapp.components.forms.yaml_editor import YamlEditor
from panther.webapp.services.config_service import ConfigService

logger = logging.getLogger(__name__)


def _dom_token(value: Any) -> str:
    """Return the CSS-class-safe token used by generated form anchors."""
    token = re.sub(r"[^a-zA-Z0-9_-]+", "-", str(value or "").strip()).strip("-")
    return token.lower() or "unnamed"


def _populate_forms_from_dict(
    panels: dict[str, Any], config_dict: dict, open_test_index: int | None = None
) -> None:
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
        open_test_index: Optional test panel to open while rebuilding
            the test editor.
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
        test_editor.set_value(
            [t for t in tests if isinstance(t, dict)], open_index=open_test_index
        )

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
    logger.info("Loading config builder page")
    config_svc = ConfigService()

    # ----------------------------------------------------------------
    # Read navigation context — from app.storage.general (set by topology
    # page via _on_node_click before navigating to /config?source=topology).
    # This is more reliable than browser query_params, which may not be
    # available at page load time depending on the NiceGUI version.
    # ----------------------------------------------------------------
    nav_data = {}
    try:
        from nicegui import app as nicegui_app

        nav_data = nicegui_app.storage.general.pop("topology_nav", {})
        logger.debug(f"Config builder nav_data from storage.general: {nav_data}")
    except Exception as exc:
        logger.debug(f"No topology_nav data in storage.general: {exc}")

    config_path_from_query = nav_data.get("config_path", "")
    test_index_from_query = nav_data.get("test_index", "")
    service_id_from_query = nav_data.get("service_id", "")
    service_name_from_query = nav_data.get("service_name", "")
    source_from_query = nav_data.get("source", "")

    # Log debug info about navigation source
    if source_from_query == "topology":
        logger.info(
            "Navigated from topology: config_path=%s, test_index=%s, service_id=%s, service_name=%s",
            config_path_from_query,
            test_index_from_query,
            service_id_from_query,
            service_name_from_query,
        )
        logger.debug("Full nav_data: %s", nav_data)

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

    # If navigated from topology, auto-load the config and navigate to the service
    # We use ui.timer to defer this after the UI has rendered
    if source_from_query == "topology" and config_path_from_query:
        ui.timer(
            0.5,
            lambda: _auto_navigate_from_topology(
                config_svc=config_svc,
                _yaml_editor_ref=_yaml_editor_ref,
                config_path=config_path_from_query,
                test_index_str=test_index_from_query,
                service_id=service_id_from_query,
                service_name=service_name_from_query,
            ),
            once=True,
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
    from panther.webapp.components.forms.config_form_panel import config_form_panel
    from panther.webapp.components.forms.form_models import GLOBAL_SECTION_META
    from panther.webapp.components.status.error_boundary import error_boundary

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
            from panther.webapp.components.forms.test_list_editor import TestListEditor

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
        logger.info("Configuration validation found %d issues", len(field_errors))
        for err in field_errors[:10]:
            severity = "negative" if err.severity == "error" else "warning"
            ui.notify(f"{err.path}: {err.message}", type=severity)
    else:
        logger.info("Configuration validated successfully")
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
        meta["modified_at"] = datetime.now(tz=timezone.utc).isoformat()
        yaml_content = _yaml.dump(data, default_flow_style=False, sort_keys=False)
    ui.download(yaml_content.encode(), "panther_config.yaml")
    logger.info("Configuration exported as panther_config.yaml")


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
            logger.info("YAML configuration imported from paste")
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
                logger.info("Configuration loaded from file: %s", path)
                ui.notify(f"Loaded: {path}", type="positive")
            except FileNotFoundError as e:
                logger.warning("Failed to load config from %s: %s", path, e)
                ui.notify(f"File not found: {path}", type="negative")
            except ValueError as e:
                logger.warning("Failed to load config from %s: %s", path, e)
                ui.notify(f"Error: {e}", type="negative")

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
            meta["modified_at"] = datetime.now(tz=timezone.utc).isoformat()
            try:
                config_svc.save_config(path, data)
                dialog.close()
                logger.info("Configuration saved to file: %s", path)
                ui.notify(f"Saved to: {path}", type="positive")
            except Exception as exc:
                ui.notify(f"Error saving: {exc}", type="negative")

        with ui.row().classes("justify-end w-full q-mt-sm"):
            ui.button("Cancel", on_click=dialog.close).props("flat")
            ui.button("Save", icon="save", on_click=_do_save).props("color=primary")
    dialog.open()


def _auto_navigate_from_topology(
    config_svc: ConfigService,
    _yaml_editor_ref: dict,
    config_path: str,
    test_index_str: str,
    service_id: str,
    service_name: str,
) -> None:
    """Auto-load config and navigate to the specified service after topology click.

    Called by a deferred ``ui.timer`` when the user navigates from the topology
    page by clicking on a node.  This function:

    1. Loads the config file from *config_path*
    2. Populates all form panels from the loaded config
    3. Opens the correct test accordion panel
    4. Scrolls to the service within the test
    5. Shows a notification with navigation info

    Args:
        config_svc: The configuration service for loading config files.
        _yaml_editor_ref: Shared mutable reference dict containing form panels.
        config_path: Filesystem path of the config file to load.
        test_index_str: String representation of the test index to navigate to.
        service_id: The ID of the service node that was clicked.
        service_name: The display name of the service node that was clicked.
    """
    import json as _json
    import yaml as _yaml
    from urllib.parse import unquote

    logger.info(
        "Auto-navigating from topology: config_path=%s, test_index=%s, service_id=%s, service_name=%s",
        config_path,
        test_index_str,
        service_id,
        service_name,
    )

    # Decode URL-encoded path
    config_path = unquote(config_path)
    service_id = unquote(service_id)
    service_name = unquote(service_name)

    try:
        # Load the config file
        data = config_svc.load_config(config_path)
        logger.debug(f"Loaded config from {config_path} for auto-navigation")

        # Update the YAML editor preview
        editor = _yaml_editor_ref.get("editor")
        if editor:
            yaml_str = _yaml.dump(data, default_flow_style=False, sort_keys=False)
            editor.value = yaml_str
            _yaml_editor_ref["skip_sync"] = True

        # Parse test index
        test_index = 0
        try:
            test_index = int(test_index_str) if test_index_str else 0
        except (ValueError, TypeError):
            test_index = 0
        test_count = (
            len(data.get("tests", [])) if isinstance(data.get("tests"), list) else 0
        )
        if test_count:
            test_index = max(0, min(test_index, test_count - 1))

        # Populate forms from loaded data, then open the target test panel
        panels = _yaml_editor_ref.get("panels")
        if panels:
            _populate_forms_from_dict(panels, data, open_test_index=test_index)
            test_editor = panels.get("tests")
            if test_editor and hasattr(test_editor, "open_test"):
                test_editor.open_test(test_index)
            _yaml_editor_ref["skip_sync"] = True

        # Pre-compute values for safe injection into JavaScript template
        js_config_path = _json.dumps(config_path)
        js_service_id = _json.dumps(service_id)
        js_service_name = _json.dumps(service_name)
        js_service_id_lower = _json.dumps(service_id.lower() if service_id else "")
        js_service_name_lower = _json.dumps(
            service_name.lower() if service_name else ""
        )
        js_service_display = _json.dumps(service_name)
        js_test_panel_selector = _json.dumps(f".panther-test-panel-{test_index}")
        js_service_selector = _json.dumps(
            f".panther-field-services-entry-{_dom_token(service_id)}"
        )

        # Scroll to the correct test and service using JavaScript
        # This runs after a short delay to let the UI fully render
        # Quasar expansion panels have an aria-expanded attribute and use .q-expansion__container
        # For reliably opening, we use the value property or click the expansion header
        js_code = f"""
            console.log("=== PANTHER Config Builder Navigation ===");
            console.log("Navigated from topology node click");
            console.log("Config path:", {js_config_path});
            console.log("Test index:", {test_index});
            console.log("Service ID:", {js_service_id});
            console.log("Service Name:", {js_service_name});

            // Phase 1: the server has already opened the correct test panel.
            // The browser only scrolls/highlights after Vue/Quasar updates.
            setTimeout(function() {{
                var targetExp = document.querySelector({js_test_panel_selector});
                if (targetExp) {{
                    var rect = targetExp.getBoundingClientRect();
                    var scrollTarget = window.scrollY + rect.top - 100;
                    window.scrollTo({{top: scrollTarget, behavior: 'smooth'}});
                    console.log("Scrolled to test panel at y:", scrollTarget);

                    // Open nested form sections inside the target test so service rows are reachable.
                    var nestedHeaders = targetExp.querySelectorAll('.q-expansion__header');
                    nestedHeaders.forEach(function(header, idx) {{
                        if (idx === 0) return;  // skip the test panel header itself
                        var expanded = header.getAttribute('aria-expanded');
                        var item = header.closest('.q-expansion-item');
                        var isExpanded = expanded === 'true' ||
                            (item && item.classList.contains('q-expansion-item--expanded'));
                        if (!isExpanded) {{
                            header.click();
                        }}
                    }});

                    function expandNestedSections() {{
                        targetExp.querySelectorAll('.q-expansion__header').forEach(function(header, idx) {{
                            if (idx === 0) return;
                            var expanded = header.getAttribute('aria-expanded');
                            var item = header.closest('.q-expansion-item');
                            var isExpanded = expanded === 'true' ||
                                (item && item.classList.contains('q-expansion-item--expanded'));
                            if (!isExpanded) {{
                                header.click();
                            }}
                        }});
                    }}

                    function highlightTarget(target) {{
                        target.scrollIntoView({{behavior: 'smooth', block: 'center'}});
                        target.style.backgroundColor = '#fff3cd';
                        target.style.boxShadow = '0 0 0 2px #ffc107';
                        target.style.borderRadius = '4px';
                        target.style.transition = 'background-color 2s, box-shadow 2s';
                        setTimeout(function() {{
                            target.style.backgroundColor = '';
                            target.style.boxShadow = '';
                        }}, 4000);
                    }}

                    function findFallbackTarget() {{
                        if (!{js_service_id}) return null;
                        var allElements = targetExp.querySelectorAll('*:not(script):not(style)');
                        for (var i = 0; i < allElements.length; i++) {{
                            var el = allElements[i];
                            var text = (el.textContent || el.value || '').toLowerCase();
                            if (text.includes({js_service_id_lower}) || text.includes({js_service_name_lower})) {{
                                return el.closest('.panther-field-services-entry') ||
                                    el.closest('.q-field') ||
                                    el.closest('.q-item') ||
                                    el;
                            }}
                        }}
                        return null;
                    }}

                    // Phase 2: wait for nested sections and service rows to render, then exact-match the clicked service.
                    var attempts = 0;
                    var maxAttempts = 20;
                    var servicePoll = setInterval(function() {{
                        attempts += 1;
                        expandNestedSections();

                        var exactServiceRow = targetExp.querySelector({js_service_selector});
                        if (exactServiceRow) {{
                            clearInterval(servicePoll);
                            highlightTarget(exactServiceRow);
                            console.log("Highlighted exact service field:", {js_service_id});

                            var editButton = exactServiceRow.querySelector('.panther-entry-edit-button');
                            if (editButton) {{
                                setTimeout(function() {{
                                    editButton.click();
                                    console.log("Opened edit dialog for exact service:", {js_service_id});
                                }}, 150);
                            }} else {{
                                console.log("Exact service row found, but no edit button was available:", {js_service_id});
                            }}
                            return;
                        }}

                        if (attempts >= maxAttempts) {{
                            clearInterval(servicePoll);
                            var fallbackTarget = findFallbackTarget();
                            if (fallbackTarget) {{
                                highlightTarget(fallbackTarget);
                                console.log("Highlighted fallback service field:", {js_service_id});
                            }} else {{
                                var rect = targetExp.getBoundingClientRect();
                                var scrollTarget = window.scrollY + rect.top - 100;
                                window.scrollTo({{top: scrollTarget, behavior: 'smooth'}});
                                console.log("Could not find service field for:", {js_service_id_lower});
                            }}
                        }}
                    }}, 250);
                }} else {{
                    console.warn("Could not find test panel selector:", {js_test_panel_selector});
                    var testsContainer = document.querySelector('.panther-test-list');
                    if (testsContainer) {{
                        var rect = testsContainer.getBoundingClientRect();
                        var scrollTarget = window.scrollY + rect.top - 100;
                        window.scrollTo({{top: scrollTarget, behavior: 'smooth'}});
                    }}
                }}
            }}, 500);

            // Show floating notification in the browser
            setTimeout(function() {{
                var navInfo = document.createElement('div');
                navInfo.id = 'panther-nav-notification';
                navInfo.style.cssText = 'position:fixed; top:20px; right:20px; z-index:9999; background:#4caf50; color:white; padding:15px 22px; border-radius:8px; box-shadow:0 4px 15px rgba(0,0,0,0.3); font-size:14px; max-width:420px; line-height:1.5;';
                navInfo.innerHTML = '✓ <b>Navigated from Topology</b><br>Service: <b>{js_service_display}</b><br>Test: <b>#{test_index + 1}</b><br><small style="opacity:0.8">Scroll to the highlighted field above</small>';
                document.body.appendChild(navInfo);
                setTimeout(function() {{
                    var el = document.getElementById('panther-nav-notification');
                    if (el) el.remove();
                }}, 8000);
            }}, 2000);
        """

        # Use ui.run_javascript for nicegui 1.x/2.x compatibility
        ui.run_javascript(js_code)

        # Show notification
        test_display_index = test_index + 1
        msg = (
            f"Loaded config from topology: {service_name} → Test #{test_display_index}"
        )
        if service_id:
            msg = f"Loaded config from topology: {service_name} ({service_id}) → Test #{test_display_index}"
        ui.notify(msg, type="positive", position="top")
        logger.info("Auto-navigation complete: %s", msg)

    except FileNotFoundError as e:
        logger.error("Config file not found during auto-navigation: %s", e)
        ui.notify(f"Config file not found: {config_path}", type="negative")
    except ValueError as e:
        logger.error("Error loading config during auto-navigation: %s", e)
        ui.notify(f"Error loading config: {e}", type="negative")
    except Exception as e:
        logger.error("Auto-navigation error: %s", e, exc_info=True)
        ui.notify(f"Navigation error: {e}", type="negative")
