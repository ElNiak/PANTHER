"""YAML editor component with CodeMirror and bi-directional sync."""

from typing import Callable, Optional

import yaml
from nicegui import ui


class YamlEditor:
    """CodeMirror-based YAML editor with form synchronization.

    Provides a YAML text editor that can sync bi-directionally with
    a Pydantic model / NiceCRUD form.
    """

    def __init__(
        self,
        initial_value: str = "",
        on_change: Optional[Callable[[str], None]] = None,
        height: str = "500px",
    ):
        self._on_change = on_change
        self.editor = (
            ui.codemirror(initial_value, language="yaml")
            .classes(f"w-full")
            .style(f"height: {height}")
        )
        if on_change:
            self.editor.on_value_change(lambda e: on_change(e.value))

    @property
    def value(self) -> str:
        return self.editor.value

    @value.setter
    def value(self, new_value: str):
        self.editor.value = new_value

    def set_from_dict(self, data: dict):
        """Set editor content from a dictionary (serialized to YAML)."""
        self.editor.value = yaml.dump(data, default_flow_style=False, sort_keys=False)

    def get_as_dict(self) -> Optional[dict]:
        """Parse editor content as YAML and return as dict.

        Returns None if the YAML is invalid.
        """
        try:
            return yaml.safe_load(self.editor.value)
        except yaml.YAMLError:
            return None

    def validate(self) -> Optional[str]:
        """Validate the YAML syntax.

        Returns None if valid, or an error message string.
        """
        try:
            yaml.safe_load(self.editor.value)
            return None
        except yaml.YAMLError as e:
            return str(e)
