"""Form components — Pydantic-to-NiceGUI rendering, YAML editing, config panels."""

try:
    import nicegui  # noqa: F401  -- guard optional dependency
except ImportError:
    __all__: list[str] = []
else:
    from panther.webapp.components.forms.config_form_panel import config_form_panel
    from panther.webapp.components.forms.pydantic_form import (
        FieldBinding,
        FormConfig,
        PydanticForm,
    )
    from panther.webapp.components.forms.test_list_editor import TestListEditor
    from panther.webapp.components.forms.yaml_editor import YamlEditor

    __all__ = [
        "config_form_panel",
        "FieldBinding",
        "FormConfig",
        "PydanticForm",
        "TestListEditor",
        "YamlEditor",
    ]
