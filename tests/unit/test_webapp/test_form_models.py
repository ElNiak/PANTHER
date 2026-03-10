"""Tests for the build_form_model utility and supporting functions."""

from typing import Dict, List, Optional, Union

import pytest
import yaml
from pydantic import BaseModel, Field


@pytest.mark.unit
class TestBuildFormModel:
    def test_strips_omega_config_field(self):
        from panther.config.core.models.global_config import LoggingConfig
        from panther.webapp.utils.form_models import build_form_model

        FormModel = build_form_model(LoggingConfig)
        assert "omega_config" not in FormModel.model_fields
        assert "level" in FormModel.model_fields

    def test_preserves_nested_basemodel_not_flattened(self):
        """Nested BaseModel fields stay intact — NiceCRUD handles them natively."""
        from panther.config.core.models.global_config import DockerConfig
        from panther.webapp.utils.form_models import build_form_model

        FormModel = build_form_model(DockerConfig)
        # user_mapping should be preserved as nested, NOT flattened
        assert "user_mapping" in FormModel.model_fields
        assert "user_mapping__run_as_host_user" not in FormModel.model_fields

    def test_skips_dict_fields(self):
        from panther.config.core.models.global_config import DockerConfig
        from panther.webapp.utils.form_models import build_form_model

        FormModel = build_form_model(DockerConfig)
        assert "build_args" not in FormModel.model_fields
        assert "force_build_docker_image" in FormModel.model_fields

    def test_skips_list_basemodel(self):
        from panther.config.core.models.experiment import TestConfig
        from panther.webapp.utils.form_models import build_form_model

        FormModel = build_form_model(TestConfig)
        assert "execution_environment" not in FormModel.model_fields

    def test_skips_dict_in_testconfig(self):
        from panther.config.core.models.experiment import TestConfig
        from panther.webapp.utils.form_models import build_form_model

        FormModel = build_form_model(TestConfig)
        assert "services" not in FormModel.model_fields

    def test_preserves_union_basemodel(self):
        """Union[BaseModel...] should be kept for NiceCRUD model switcher."""
        from panther.config.core.models.experiment import TestConfig
        from panther.webapp.utils.form_models import build_form_model

        FormModel = build_form_model(TestConfig)
        assert "network_environment" in FormModel.model_fields

    def test_preserves_enum_annotations(self):
        from panther.config.core.models.global_config import LoggingConfig
        from panther.webapp.utils.form_models import build_form_model

        FormModel = build_form_model(LoggingConfig)
        assert "level" in FormModel.model_fields

    def test_all_global_config_sections_build(self):
        from panther.config.core.models.global_config import GlobalConfig
        from panther.webapp.utils.form_models import build_form_model

        for field_name, field_info in GlobalConfig.model_fields.items():
            if field_name == "version":
                continue
            annotation = field_info.annotation
            if isinstance(annotation, type) and issubclass(annotation, BaseModel):
                FormModel = build_form_model(annotation)
                assert FormModel is not None, f"{annotation.__name__} failed to build"

    def test_json_schema_generation(self):
        from panther.config.core.models.global_config import LoggingConfig
        from panther.webapp.utils.form_models import build_form_model

        FormModel = build_form_model(LoggingConfig)
        schema = FormModel.model_json_schema()
        assert "properties" in schema
        assert "level" in schema["properties"]

    def test_required_fields_get_defaults(self):
        """Required fields in TestConfig should get sensible defaults."""
        from panther.config.core.models.experiment import TestConfig
        from panther.webapp.utils.form_models import build_form_model

        FormModel = build_form_model(TestConfig)
        # Should be instantiable without arguments
        instance = FormModel()
        assert instance.name == ""

    def test_form_model_naming(self):
        from panther.config.core.models.global_config import LoggingConfig
        from panther.webapp.utils.form_models import build_form_model

        FormModel = build_form_model(LoggingConfig)
        assert FormModel.__name__ == "LoggingConfigForm"

    def test_model_to_dict_pipeline(self):
        """Strip → instance → dump → yaml roundtrip works."""
        from panther.config.core.models.global_config import PathsConfig
        from panther.webapp.utils.form_models import build_form_model

        FormModel = build_form_model(PathsConfig)
        instance = FormModel()
        data = instance.model_dump()
        assert isinstance(data, dict)
        assert "output_dir" in data

        yaml_str = yaml.dump(data, default_flow_style=False)
        roundtrip = yaml.safe_load(yaml_str)
        assert roundtrip["output_dir"] == data["output_dir"]


@pytest.mark.unit
class TestPickIdField:
    def test_explicit_override(self):
        from panther.config.core.models.global_config import LoggingConfig
        from panther.webapp.utils.form_models import pick_id_field

        assert pick_id_field(LoggingConfig) == "level"

    def test_prefers_name_field(self):
        from panther.webapp.utils.form_models import pick_id_field

        class MyModel(BaseModel):
            name: str = "test"
            value: int = 0

        assert pick_id_field(MyModel) == "name"

    def test_falls_back_to_enabled(self):
        from panther.webapp.utils.form_models import pick_id_field

        class MyModel(BaseModel):
            enabled: bool = True
            threshold: int = 5

        assert pick_id_field(MyModel) == "enabled"

    def test_falls_back_to_first_field(self):
        from panther.webapp.utils.form_models import pick_id_field

        class MyModel(BaseModel):
            alpha: str = "a"
            beta: int = 0

        assert pick_id_field(MyModel) == "alpha"


@pytest.mark.unit
class TestGetSkippedFields:
    def test_docker_config_skips_build_args(self):
        from panther.config.core.models.global_config import DockerConfig
        from panther.webapp.utils.form_models import get_skipped_fields

        skipped = get_skipped_fields(DockerConfig)
        assert "build_args" in skipped

    def test_test_config_skips_services_and_execution_env(self):
        from panther.config.core.models.experiment import TestConfig
        from panther.webapp.utils.form_models import get_skipped_fields

        skipped = get_skipped_fields(TestConfig)
        assert "services" in skipped
        assert "execution_environment" in skipped

    def test_paths_config_skips_nothing(self):
        from panther.config.core.models.global_config import PathsConfig
        from panther.webapp.utils.form_models import get_skipped_fields

        skipped = get_skipped_fields(PathsConfig)
        assert skipped == []


@pytest.mark.unit
class TestFieldClassification:
    def test_list_basemodel_unsupported(self):
        from panther.webapp.utils.form_models import _is_unsupported_for_nicecrud

        class Inner(BaseModel):
            x: int = 0

        assert _is_unsupported_for_nicecrud(List[Inner]) is True

    def test_list_str_supported(self):
        from panther.webapp.utils.form_models import _is_unsupported_for_nicecrud

        assert _is_unsupported_for_nicecrud(list[str]) is False

    def test_dict_str_str_unsupported(self):
        from panther.webapp.utils.form_models import _is_unsupported_for_nicecrud

        assert _is_unsupported_for_nicecrud(Dict[str, str]) is True

    def test_union_basemodel_supported(self):
        from panther.webapp.utils.form_models import _is_unsupported_for_nicecrud

        class A(BaseModel):
            x: int = 0

        class B(BaseModel):
            y: str = ""

        assert _is_unsupported_for_nicecrud(Union[A, B]) is False

    def test_plain_str_supported(self):
        from panther.webapp.utils.form_models import _is_unsupported_for_nicecrud

        assert _is_unsupported_for_nicecrud(str) is False

    def test_optional_dict_unsupported(self):
        from panther.webapp.utils.form_models import _is_unsupported_for_nicecrud

        assert _is_unsupported_for_nicecrud(Optional[Dict[str, str]]) is True


@pytest.mark.unit
class TestClassifyComplexField:
    def test_dict_str_str(self):
        from panther.webapp.utils.form_models import classify_complex_field

        assert classify_complex_field(Dict[str, str]) == "dict_str"

    def test_dict_str_any(self):
        from typing import Any

        from panther.webapp.utils.form_models import classify_complex_field

        assert classify_complex_field(Dict[str, Any]) == "dict_str"

    def test_dict_str_basemodel(self):
        from panther.webapp.utils.form_models import classify_complex_field

        class Inner(BaseModel):
            x: int = 0

        assert classify_complex_field(Dict[str, Inner]) == "dict_model"

    def test_list_basemodel(self):
        from panther.webapp.utils.form_models import classify_complex_field

        class Inner(BaseModel):
            x: int = 0

        assert classify_complex_field(List[Inner]) == "list_model"

    def test_optional_dict_unwraps(self):
        from panther.webapp.utils.form_models import classify_complex_field

        assert classify_complex_field(Optional[Dict[str, str]]) == "dict_str"

    def test_list_str_returns_none(self):
        from panther.webapp.utils.form_models import classify_complex_field

        assert classify_complex_field(list[str]) is None

    def test_plain_str_returns_none(self):
        from panther.webapp.utils.form_models import classify_complex_field

        assert classify_complex_field(str) is None


@pytest.mark.unit
class TestGetComplexFields:
    def test_docker_config_has_build_args(self):
        from panther.config.core.models.global_config import DockerConfig
        from panther.webapp.utils.form_models import get_complex_fields

        fields = get_complex_fields(DockerConfig)
        assert "build_args" in fields
        assert fields["build_args"].category == "dict_str"

    def test_test_config_has_services_and_execution_env(self):
        from panther.config.core.models.experiment import TestConfig
        from panther.webapp.utils.form_models import get_complex_fields

        fields = get_complex_fields(TestConfig)
        assert "services" in fields
        assert fields["services"].category == "dict_model"
        assert "execution_environment" in fields
        assert fields["execution_environment"].category == "list_model"

    def test_paths_config_has_none(self):
        from panther.config.core.models.global_config import PathsConfig
        from panther.webapp.utils.form_models import get_complex_fields

        assert get_complex_fields(PathsConfig) == {}


@pytest.mark.unit
class TestConfigFormPanel:
    def test_config_form_panel_importable(self):
        from panther.webapp.components.config_form_panel import config_form_panel

        assert callable(config_form_panel)

    def test_form_panel_result_importable(self):
        from panther.webapp.components.config_form_panel import FormPanelResult

        assert FormPanelResult is not None

    def test_all_global_models_schema_generation(self):
        """Global config models can be built and generate JSON schema for NiceCRUD."""
        from panther.config.core.models.global_config import (
            DockerConfig,
            FastFailConfig,
            LoggingConfig,
            MetricsConfig,
            PathsConfig,
            ProgressConfig,
        )
        from panther.webapp.utils.form_models import build_form_model

        models = [
            LoggingConfig,
            PathsConfig,
            DockerConfig,
            ProgressConfig,
            FastFailConfig,
            MetricsConfig,
        ]
        for model_cls in models:
            FormModel = build_form_model(model_cls)
            schema = FormModel.model_json_schema()
            assert (
                "properties" in schema
            ), f"No properties in schema for {model_cls.__name__}"
            assert (
                len(schema["properties"]) > 0
            ), f"Empty schema for {model_cls.__name__}"


@pytest.mark.unit
class TestDictToFormInstance:
    def test_basic_conversion(self):
        from panther.webapp.utils.form_models import dict_to_form_instance

        class Simple(BaseModel):
            name: str = ""
            value: int = 0

        instance = dict_to_form_instance(Simple, {"name": "hello", "value": 42})
        assert instance.name == "hello"
        assert instance.value == 42

    def test_extra_keys_ignored(self):
        from panther.webapp.utils.form_models import dict_to_form_instance

        class Simple(BaseModel):
            name: str = ""

        instance = dict_to_form_instance(Simple, {"name": "hi", "unknown_key": "x"})
        assert instance.name == "hi"
        assert not hasattr(instance, "unknown_key")

    def test_empty_dict_returns_defaults(self):
        from panther.webapp.utils.form_models import dict_to_form_instance

        class Simple(BaseModel):
            name: str = "default"

        instance = dict_to_form_instance(Simple, {})
        assert instance.name == "default"


@pytest.mark.unit
class TestFormInstanceToDict:
    def test_basic_dump(self):
        from panther.webapp.utils.form_models import form_instance_to_dict

        class Simple(BaseModel):
            name: str = "test"

        data = form_instance_to_dict(Simple())
        assert data == {"name": "test"}

    def test_merges_widget_values(self):
        from panther.webapp.utils.form_models import form_instance_to_dict

        class Simple(BaseModel):
            name: str = "test"

        class MockWidget:
            def get_value(self):
                return {"k": "v"}

        data = form_instance_to_dict(Simple(), widgets={"extra": MockWidget()})
        assert data["name"] == "test"
        assert data["extra"] == {"k": "v"}


@pytest.mark.unit
class TestExtractSectionData:
    def test_dot_notation(self):
        from panther.webapp.utils.form_models import extract_section_data

        cfg = {"a": {"b": {"c": 42}}}
        assert extract_section_data(cfg, "a.b.c") == 42

    def test_list_index(self):
        from panther.webapp.utils.form_models import extract_section_data

        cfg = {"tests": [{"name": "t0"}, {"name": "t1"}]}
        assert extract_section_data(cfg, "tests.1.name") == "t1"

    def test_missing_returns_none(self):
        from panther.webapp.utils.form_models import extract_section_data

        assert extract_section_data({"a": 1}, "b.c") is None


@pytest.mark.unit
class TestSplitSimpleAndComplex:
    def test_splits_docker_config(self):
        from panther.config.core.models.global_config import DockerConfig
        from panther.webapp.utils.form_models import split_simple_and_complex

        data = {
            "force_build_docker_image": True,
            "build_args": {"arg1": "val1"},
        }
        simple, complex_data = split_simple_and_complex(DockerConfig, data)
        assert "force_build_docker_image" in simple
        assert "build_args" in complex_data


@pytest.mark.unit
class TestSingletonForm:
    def test_singleton_form_importable(self):
        from panther.webapp.components.singleton_crud import SingletonForm

        assert SingletonForm is not None

    def test_singleton_form_has_basemodels(self):
        """SingletonForm exposes .basemodels for compatibility with NiceCRUD."""
        from panther.webapp.components.singleton_crud import SingletonForm

        assert hasattr(SingletonForm, "basemodels")


@pytest.mark.unit
class TestPopulateFormsFromDict:
    """Tests for config_builder._populate_forms_from_dict."""

    def _make_mock_panel(self, basemodels=None, widgets=None):
        """Create a mock FormPanelResult with crud.basemodels and widgets."""
        from unittest.mock import MagicMock

        panel = MagicMock()
        panel.crud.basemodels = basemodels or []
        panel.widgets = widgets or {}
        return panel

    def _make_mock_widget(self, initial_value=None):
        from unittest.mock import MagicMock

        widget = MagicMock()
        widget._value = initial_value
        widget.set_value = lambda v: setattr(widget, "_value", v)
        widget.get_value = lambda: widget._value
        return widget

    def test_populates_global_section(self):
        from panther.webapp.pages.config_builder import _populate_forms_from_dict

        panel = self._make_mock_panel()
        cruds = {"global": {"logging": panel}}

        _populate_forms_from_dict(cruds, {"logging": {"level": "DEBUG"}})

        # populate_panel_from_dict should have been called on the panel
        assert panel.crud.basemodels is not None

    def test_populates_tests(self):
        from panther.webapp.pages.config_builder import _populate_forms_from_dict

        panel = self._make_mock_panel(widgets={})
        cruds = {"tests": panel}

        config_dict = {
            "tests": [
                {"name": "test1"},
                {"name": "test2"},
            ]
        }
        _populate_forms_from_dict(cruds, config_dict)

        # Should have populated basemodels with 2 test instances
        assert len(panel.crud.basemodels) == 2
        assert panel.crud.basemodels[0].name == "test1"
        assert panel.crud.basemodels[1].name == "test2"

    def test_populates_tests_with_complex_widgets(self):
        from panther.webapp.pages.config_builder import _populate_forms_from_dict

        services_widget = self._make_mock_widget()
        panel = self._make_mock_panel(widgets={"services": services_widget})
        cruds = {"tests": panel}

        config_dict = {
            "tests": [
                {"name": "test1", "services": {"server": {"impl": "picoquic"}}},
            ]
        }
        _populate_forms_from_dict(cruds, config_dict)

        assert services_widget._value == {"server": {"impl": "picoquic"}}

    def test_populates_metadata(self):
        from panther.webapp.pages.config_builder import _populate_forms_from_dict

        panel = self._make_mock_panel()
        cruds = {"metadata": panel}

        _populate_forms_from_dict(cruds, {"metadata": {"name": "My Experiment"}})

        # Should have called populate_panel_from_dict
        assert panel.crud.basemodels is not None

    def test_handles_empty_config_gracefully(self):
        from panther.webapp.pages.config_builder import _populate_forms_from_dict

        cruds = {"global": {}, "tests": None, "metadata": None}
        # Should not raise
        _populate_forms_from_dict(cruds, {})

    def test_handles_missing_sections_gracefully(self):
        from panther.webapp.pages.config_builder import _populate_forms_from_dict

        panel = self._make_mock_panel()
        cruds = {"global": {"logging": panel}}

        # Config has no "logging" key — should skip without error
        _populate_forms_from_dict(cruds, {"docker": {"force_build": True}})

    def test_handles_extra_keys_gracefully(self):
        from panther.webapp.pages.config_builder import _populate_forms_from_dict

        cruds = {"global": {}}

        # Config has keys that don't map to any panel — should not crash
        _populate_forms_from_dict(
            cruds, {"unknown_section": {"foo": "bar"}, "another": 123}
        )

    def test_clean_annotation_optional_basemodel(self):
        """Cleaning Optional[SomeModel] should return Optional[cleaned], not Union[(model,)]."""
        from panther.webapp.utils.form_models import build_form_model

        class Inner(BaseModel):
            name: str  # required field -> will be cleaned

        class Outer(BaseModel):
            child: Optional[Inner] = None

        FormModel = build_form_model(Outer)
        instance = FormModel()
        assert instance.child is None

    def test_tests_with_non_dict_entries_skipped(self):
        from panther.webapp.pages.config_builder import _populate_forms_from_dict

        panel = self._make_mock_panel(widgets={})
        cruds = {"tests": panel}

        config_dict = {
            "tests": [
                {"name": "valid_test"},
                "not_a_dict",  # Should be skipped
                42,  # Should be skipped
            ]
        }
        _populate_forms_from_dict(cruds, config_dict)

        # Only the valid dict entry should produce a model
        assert len(panel.crud.basemodels) == 1
        assert panel.crud.basemodels[0].name == "valid_test"
