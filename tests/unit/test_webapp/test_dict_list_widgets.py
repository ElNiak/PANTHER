"""Tests for Dict/List custom widget utilities and type classification."""

from typing import Any, Dict, List, Optional

import pytest
from pydantic import BaseModel, Field

from panther.webapp.components.forms.form_models import (
    ComplexFieldInfo,
    classify_complex_field,
    get_complex_fields,
)


@pytest.mark.unit
class TestComplexFieldInfo:
    def test_namedtuple_fields(self):
        info = ComplexFieldInfo(
            category="dict_str",
            annotation=Dict[str, str],
            value_type=str,
            description="test",
        )
        assert info.category == "dict_str"
        assert info.value_type is str
        assert info.description == "test"


@pytest.mark.unit
class TestClassifyComplexFieldDetailed:
    def test_dict_str_int(self):
        assert classify_complex_field(Dict[str, int]) == "dict_str"

    def test_dict_str_any(self):
        assert classify_complex_field(Dict[str, Any]) == "dict_str"

    def test_dict_str_basemodel(self):
        class MyModel(BaseModel):
            x: int = 0

        assert classify_complex_field(Dict[str, MyModel]) == "dict_model"

    def test_list_basemodel(self):
        class MyModel(BaseModel):
            x: int = 0

        assert classify_complex_field(List[MyModel]) == "list_model"

    def test_optional_dict_str_str(self):
        assert classify_complex_field(Optional[Dict[str, str]]) == "dict_str"

    def test_optional_dict_str_basemodel(self):
        class MyModel(BaseModel):
            x: int = 0

        assert classify_complex_field(Optional[Dict[str, MyModel]]) == "dict_model"

    def test_list_str_returns_none(self):
        assert classify_complex_field(list[str]) is None

    def test_scalar_returns_none(self):
        assert classify_complex_field(str) is None
        assert classify_complex_field(int) is None
        assert classify_complex_field(bool) is None

    def test_basemodel_returns_none(self):
        class MyModel(BaseModel):
            x: int = 0

        assert classify_complex_field(MyModel) is None


@pytest.mark.unit
class TestGetComplexFieldsDetailed:
    def test_docker_config(self):
        from panther.config.core.models.global_config import DockerConfig

        fields = get_complex_fields(DockerConfig)
        assert "build_args" in fields
        assert fields["build_args"].category == "dict_str"
        assert fields["build_args"].value_type is str

    def test_test_config(self):
        from panther.config.core.models.experiment import TestConfig

        fields = get_complex_fields(TestConfig)
        assert "services" in fields
        assert fields["services"].category == "dict_model"
        assert "execution_environment" in fields
        assert fields["execution_environment"].category == "list_model"

    def test_paths_config_empty(self):
        from panther.config.core.models.global_config import PathsConfig

        assert get_complex_fields(PathsConfig) == {}

    def test_logging_config_empty(self):
        from panther.config.core.models.global_config import LoggingConfig

        assert get_complex_fields(LoggingConfig) == {}

    def test_model_with_mixed_fields(self):
        """Model with both normal and complex fields."""

        class MixedModel(BaseModel):
            name: str = "test"
            tags: Dict[str, str] = Field(default_factory=dict)
            count: int = 0

        fields = get_complex_fields(MixedModel)
        assert "tags" in fields
        assert "name" not in fields
        assert "count" not in fields


@pytest.mark.unit
class TestWidgetImports:
    def test_key_value_editor_importable(self):
        from panther.webapp.components.forms.dict_list_widgets import KeyValueEditor

        assert KeyValueEditor is not None

    def test_keyed_model_editor_importable(self):
        from panther.webapp.components.forms.dict_list_widgets import KeyedModelEditor

        assert KeyedModelEditor is not None

    def test_model_list_editor_importable(self):
        from panther.webapp.components.forms.dict_list_widgets import ModelListEditor

        assert ModelListEditor is not None

    def test_create_widget_for_field_importable(self):
        from panther.webapp.components.forms.dict_list_widgets import (
            create_widget_for_field,
        )

        assert callable(create_widget_for_field)
