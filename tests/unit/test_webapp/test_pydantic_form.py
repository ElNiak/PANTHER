"""Tests for PydanticForm component — type detection, FormConfig, enum extraction."""

from enum import Enum
from typing import Any, Dict, List, Literal, Optional

import pytest
from pydantic import BaseModel, Field


@pytest.mark.unit
class TestFormConfig:
    def test_importable(self):
        from panther.webapp.components.pydantic_form import FormConfig

        assert FormConfig is not None

    def test_defaults(self):
        from panther.webapp.components.pydantic_form import FormConfig

        cfg = FormConfig()
        assert cfg.show_advanced is False
        assert cfg.group_by_category is True
        assert cfg.section_style == "expansion"
        assert cfg.css_prefix == "pf"

    def test_custom_values(self):
        from panther.webapp.components.pydantic_form import FormConfig

        cfg = FormConfig(show_advanced=True, css_prefix="cr")
        assert cfg.show_advanced is True
        assert cfg.css_prefix == "cr"


@pytest.mark.unit
class TestFieldBinding:
    def test_importable(self):
        from panther.webapp.components.pydantic_form import FieldBinding

        assert FieldBinding is not None

    def test_scalar_binding(self):
        from panther.webapp.components.pydantic_form import FieldBinding

        b = FieldBinding(
            getter=lambda: "hello",
            setter=lambda v: None,
            field_type="scalar",
        )
        assert b.getter() == "hello"
        assert b.field_type == "scalar"
        assert b.sub_form is None
        assert b.widget is None


@pytest.mark.unit
class TestPydanticFormImport:
    def test_importable(self):
        from panther.webapp.components.pydantic_form import PydanticForm

        assert PydanticForm is not None


@pytest.mark.unit
class TestTypeDetection:
    def test_unwrap_optional_str(self):
        from panther.webapp.components.pydantic_form import PydanticForm

        inner, is_opt = PydanticForm._unwrap_optional(Optional[str])
        assert inner is str
        assert is_opt is True

    def test_unwrap_non_optional(self):
        from panther.webapp.components.pydantic_form import PydanticForm

        inner, is_opt = PydanticForm._unwrap_optional(str)
        assert inner is str
        assert is_opt is False

    def test_unwrap_optional_basemodel(self):
        from panther.webapp.components.pydantic_form import PydanticForm

        class Inner(BaseModel):
            x: int = 0

        inner, is_opt = PydanticForm._unwrap_optional(Optional[Inner])
        assert inner is Inner
        assert is_opt is True

    def test_find_enum_with_enum(self):
        from panther.webapp.components.pydantic_form import PydanticForm

        class Color(Enum):
            RED = "red"
            BLUE = "blue"

        assert PydanticForm._find_enum(Color) is Color

    def test_find_enum_with_non_enum(self):
        from panther.webapp.components.pydantic_form import PydanticForm

        assert PydanticForm._find_enum(str) is None
        assert PydanticForm._find_enum(int) is None

    def test_find_enum_with_basemodel(self):
        from panther.webapp.components.pydantic_form import PydanticForm

        class M(BaseModel):
            x: int = 0

        assert PydanticForm._find_enum(M) is None


@pytest.mark.unit
class TestEnumChoicesExtraction:
    def test_logging_level_values(self):
        from panther.config.core.models.global_config import LoggingLevel

        values = [e.value for e in LoggingLevel]
        assert "INFO" in values
        assert "DEBUG" in values
        assert "ERROR" in values

    def test_docker_network_mode_values(self):
        from panther.config.core.models.global_config import DockerNetworkMode

        values = [e.value for e in DockerNetworkMode]
        assert len(values) > 0
        for v in values:
            assert isinstance(v, str)

    def test_export_format_values(self):
        from panther.config.core.models.global_config import ExportFormat

        values = [e.value for e in ExportFormat]
        assert len(values) > 0

    def test_all_config_enums_produce_string_values(self):
        """Every enum used in config models produces string values suitable for ui.select()."""
        from panther.config.core.models.global_config import (
            DockerNetworkMode,
            ExportFormat,
            LoggingLevel,
        )

        for enum_cls in [LoggingLevel, DockerNetworkMode, ExportFormat]:
            values = [e.value for e in enum_cls]
            assert len(values) > 0, f"{enum_cls.__name__} has no values"
            for v in values:
                assert isinstance(v, str), f"{enum_cls.__name__}.{v} is not a string"


@pytest.mark.unit
class TestFieldLabelFormatting:
    def test_simple_name(self):
        assert "output_dir".replace("_", " ").title() == "Output Dir"

    def test_double_underscore(self):
        assert "build_docker_image".replace("_", " ").title() == "Build Docker Image"

    def test_single_word(self):
        assert "level".replace("_", " ").title() == "Level"


@pytest.mark.unit
class TestJsonSchemaExtra:
    def test_advanced_field_detection(self):
        class MyModel(BaseModel):
            basic: str = Field(default="", json_schema_extra={"category": "general"})
            hidden: str = Field(default="", json_schema_extra={"advanced": True})

        finfo = MyModel.model_fields["hidden"]
        extra = finfo.json_schema_extra or {}
        assert isinstance(extra, dict)
        assert extra.get("advanced") is True

    def test_category_extraction(self):
        class MyModel(BaseModel):
            port: int = Field(default=443, json_schema_extra={"category": "network"})

        finfo = MyModel.model_fields["port"]
        extra = finfo.json_schema_extra or {}
        assert isinstance(extra, dict)
        assert extra.get("category") == "network"

    def test_widget_type_extraction(self):
        class MyModel(BaseModel):
            port: int = Field(default=443, json_schema_extra={"widget_type": "port"})

        finfo = MyModel.model_fields["port"]
        extra = finfo.json_schema_extra or {}
        assert isinstance(extra, dict)
        assert extra.get("widget_type") == "port"

    def test_unit_extraction(self):
        class MyModel(BaseModel):
            timeout: float = Field(default=30.0, json_schema_extra={"unit": "seconds"})

        finfo = MyModel.model_fields["timeout"]
        extra = finfo.json_schema_extra or {}
        assert isinstance(extra, dict)
        assert extra.get("unit") == "seconds"

    def test_missing_extra_is_none(self):
        class MyModel(BaseModel):
            name: str = ""

        finfo = MyModel.model_fields["name"]
        extra = finfo.json_schema_extra
        assert extra is None


@pytest.mark.unit
class TestYamlEnumSafeOutput:
    def test_logging_config_no_python_tags(self):
        """Using original model (not create_model copy) preserves use_enum_values=True."""
        import yaml

        from panther.config.core.models.global_config import LoggingConfig

        data = LoggingConfig().model_dump(mode="json")
        s = yaml.dump(data, default_flow_style=False)
        assert "!!python" not in s
