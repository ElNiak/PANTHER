"""YamlEditor — CodeMirror-based YAML editor with bi-directional sync.

Wraps NiceGUI's ``ui.codemirror`` widget (CodeMirror 6) in a convenience
class that can convert between raw YAML text and Python dicts.  Used by
the PANTHER (Protocol ANalysis and Testing Harness for Extensible Research)
config builder page to let users edit experiment configuration as either a
structured form or raw YAML, with changes flowing in both directions:

* ``set_from_dict(data)`` — serialises a Python dict to YAML and pushes
  it into the editor.
* ``get_as_dict()`` — parses the current editor text back into a dict
  (returns ``None`` on syntax errors).
* ``validate()`` — checks YAML syntax without converting, returning an
  error message string or ``None``.
"""

from typing import Callable, Optional

import yaml
from nicegui import ui


class YamlEditor:
    """CodeMirror-based YAML editor with form synchronization.

    Provides a YAML text editor that can sync bi-directionally with
    a Pydantic model / ``PydanticForm``.  The editor renders into the
    currently active NiceGUI container and optionally fires a callback
    on every keystroke.

    Args:
        initial_value: YAML text to display when the editor is created.
        on_change: Optional callback invoked with the new text on every
            content change (debounced by CodeMirror).
        height: CSS height for the editor panel (e.g. ``"500px"``).

    Example::

        editor = YamlEditor(on_change=lambda text: print("changed"))
        editor.set_from_dict({"key": "value"})
        result = editor.get_as_dict()  # {"key": "value"} or None
    """

    def __init__(
        self,
        initial_value: str = "",
        on_change: Optional[Callable[[str], None]] = None,
        height: str = "500px",
    ):
        """Initialise the YAML editor with optional initial content and change callback."""
        self._on_change = on_change
        self.editor = (
            ui.codemirror(initial_value, language="yaml")
            .classes(f"w-full")
            .style(f"height: {height}")
        )
        if on_change:
            self.editor.on_value_change(lambda e: on_change(e.value))

    @property
    def value(self) -> str:  # noqa: D102
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
