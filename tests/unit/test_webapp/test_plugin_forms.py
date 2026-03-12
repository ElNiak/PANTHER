"""Tests for plugin_forms.py — plugin discovery bridge for webapp forms."""

from enum import Enum

import pytest
from pydantic import BaseModel, Field


@pytest.mark.unit
class TestPluginFormInfo:
    def test_get_plugin_form_info_unknown_returns_none(self):
        from panther.webapp.components.forms.plugin_forms import get_plugin_form_info

        result = get_plugin_form_info("__nonexistent_plugin__")
        assert result is None

    def test_get_plugin_form_info_picoquic(self):
        """Picoquic should be discoverable via well-known import paths."""
        from panther.webapp.components.forms.plugin_forms import get_plugin_form_info

        info = get_plugin_form_info("picoquic")
        if info is None:
            pytest.skip("picoquic plugin not importable in test environment")
        assert info.plugin_name == "picoquic"
        assert info.form_model is not None
        assert "omega_config" not in info.form_model.model_fields
        assert isinstance(info.defaults, dict)
        assert isinstance(info.id_field, str)

    def test_enum_extraction(self):
        from panther.webapp.components.forms.plugin_forms import _extract_enum_choices

        class Color(Enum):
            RED = "red"
            BLUE = "blue"

        class MyModel(BaseModel):
            color: Color = Color.RED
            name: str = ""

        choices = _extract_enum_choices(MyModel)
        assert "color" in choices
        assert set(choices["color"]) == {"red", "blue"}
        assert "name" not in choices

    def test_enum_extraction_optional(self):
        from typing import Optional

        from panther.webapp.components.forms.plugin_forms import _extract_enum_choices

        class Status(Enum):
            ON = "on"
            OFF = "off"

        class MyModel(BaseModel):
            status: Optional[Status] = None

        choices = _extract_enum_choices(MyModel)
        assert "status" in choices
        assert "on" in choices["status"]


@pytest.mark.unit
class TestListPlugins:
    def test_list_available_plugins_returns_list(self):
        from panther.webapp.components.forms.plugin_forms import list_available_plugins

        result = list_available_plugins()
        assert isinstance(result, list)

    def test_get_protocol_choices_returns_list(self):
        from panther.webapp.components.forms.plugin_forms import get_protocol_choices

        result = get_protocol_choices()
        assert isinstance(result, list)

    def test_get_implementation_choices_returns_list(self):
        from panther.webapp.components.forms.plugin_forms import (
            get_implementation_choices,
        )

        result = get_implementation_choices()
        assert isinstance(result, list)

    def test_get_implementation_choices_filtered(self):
        from panther.webapp.components.forms.plugin_forms import (
            get_implementation_choices,
        )

        # Should not raise even with unknown protocol
        result = get_implementation_choices(protocol="__nonexistent__")
        assert isinstance(result, list)
