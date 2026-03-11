"""Accordion-based editor for List[TestConfig].

Renders each test as an expansion panel with a full PydanticForm inside.
Only one panel is open at a time (accordion behavior).
"""

from __future__ import annotations

import copy
import logging
from typing import Any

from nicegui import ui

logger = logging.getLogger(__name__)


class TestListEditor:
    """Accordion editor for ``List[TestConfig]``.

    Exposes ``get_value()`` / ``set_value()`` matching the widget interface
    used by the config builder's sync logic.
    """

    def __init__(self) -> None:  # noqa: D107
        self._test_data: list[dict[str, Any]] = []
        self._forms: list[Any] = []  # PydanticForm instances
        with ui.column().classes("w-full"):
            self._container = ui.column().classes("w-full gap-2")
            ui.button(
                "Add Test",
                icon="add",
                on_click=self._add_test,
            ).props(
                "flat dense size=sm"
            ).classes("q-mt-xs")

    # ── Public API ──────────────────────────────────────────────

    def get_value(self) -> list[dict[str, Any]]:
        """Return all tests as a list of dicts for YAML serialization."""
        return [f.get_value() for f in self._forms]

    def update_form_field(self, test_idx: int, field_name: str, value: Any) -> None:
        """Push a value into a test form's widget binding."""
        if test_idx < len(self._forms):
            self._forms[test_idx].set_field_value(field_name, value)

    def set_value(self, tests: list[dict[str, Any]]) -> None:
        """Load a list of test dicts (e.g. from YAML import/load)."""
        self._test_data = list(tests) if tests else []
        self._forms = []
        self._rebuild()

    # ── Internal ────────────────────────────────────────────────

    def _snapshot(self) -> None:
        """Capture current form values into ``_test_data``."""
        if self._forms:
            self._test_data = [f.get_value() for f in self._forms]

    def _rebuild(self) -> None:
        """Clear and re-render all expansion panels from ``_test_data``."""
        from panther.config.core.models.experiment import TestConfig
        from panther.webapp.components.pydantic_form import PydanticForm

        self._container.clear()
        self._forms = []

        with self._container:
            if not self._test_data:
                ui.label("No tests configured. Click 'Add Test' to begin.").classes(
                    "text-caption text-grey-5 q-py-sm"
                )
                return

            for idx, test_data in enumerate(self._test_data):
                label = self._get_label(idx, test_data)
                exp = ui.expansion(
                    text=label,
                    icon="science",
                    group="test-configs",
                ).classes("w-full")

                # Header actions (duplicate / delete)
                with exp.add_slot("header"):
                    with ui.row().classes(
                        "w-full items-center justify-between no-wrap"
                    ):
                        with ui.row().classes("items-center gap-1"):
                            ui.icon("science").classes("text-grey-7")
                            ui.label(label).classes("text-subtitle2")
                        with ui.row().classes("items-center gap-0"):
                            ui.button(
                                icon="content_copy",
                                on_click=lambda _, i=idx: self._duplicate_test(i),
                            ).props("flat dense round size=sm").tooltip("Duplicate")
                            ui.button(
                                icon="delete",
                                on_click=lambda _, i=idx: self._remove_test(i),
                            ).props("flat dense round size=sm color=negative").tooltip(
                                "Delete"
                            )

                # Form content inside the expansion
                with exp:
                    form = PydanticForm(TestConfig)
                    if test_data:
                        form.set_value(test_data)
                    self._forms.append(form)

                # Auto-open the first (or only) panel
                if idx == 0:
                    exp.open()

    def _add_test(self) -> None:
        """Append an empty test and rebuild."""
        self._snapshot()
        self._test_data.append({})
        self._rebuild()
        # Open the newly added panel (last one)
        self._open_last()

    def _duplicate_test(self, idx: int) -> None:
        """Deep-copy test at *idx*, append, and rebuild."""
        self._snapshot()
        if idx < len(self._test_data):
            cloned = copy.deepcopy(self._test_data[idx])
            # Append "(copy)" to the name to avoid duplicate name validation errors
            name = cloned.get("name", "")
            if name:
                cloned["name"] = f"{name} (copy)"
            self._test_data.append(cloned)
            self._rebuild()
            self._open_last()

    def _remove_test(self, idx: int) -> None:
        """Remove test at *idx* and rebuild."""
        self._snapshot()
        if idx < len(self._test_data):
            self._test_data.pop(idx)
            self._rebuild()

    def _open_last(self) -> None:
        """Open the last expansion panel (newly added test)."""
        # The container's children are the expansion panels
        children = list(self._container)
        if children:
            last = children[-1]
            if hasattr(last, "open"):
                last.open()

    @staticmethod
    def _get_label(idx: int, data: dict[str, Any]) -> str:
        """Generate a display label for the expansion header."""
        name = data.get("name", "")
        if name and str(name).strip():
            return f"Test {idx + 1}: {name}"
        return f"Test {idx + 1} (unnamed)"
