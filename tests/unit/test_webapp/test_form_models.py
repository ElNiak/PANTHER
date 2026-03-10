"""Tests for the strip_omega_config utility and config_form_panel component."""

import pytest
import yaml
from pydantic import BaseModel, Field
from pydantic_core import PydanticUndefined


@pytest.mark.unit
class TestStripOmegaConfig:
    def test_strips_omega_config_field(self):
        from panther.config.core.models.global_config import LoggingConfig
        from panther.webapp.utils.form_models import strip_omega_config

        FormModel = strip_omega_config(LoggingConfig)
        assert "omega_config" not in FormModel.model_fields
        assert "level" in FormModel.model_fields

    def test_preserves_scalar_fields(self):
        from panther.config.core.models.global_config import PathsConfig
        from panther.webapp.utils.form_models import strip_omega_config

        FormModel = strip_omega_config(PathsConfig)
        assert "output_dir" in FormModel.model_fields
        assert "log_dir" in FormModel.model_fields

    def test_generates_json_schema(self):
        from panther.config.core.models.global_config import LoggingConfig
        from panther.webapp.utils.form_models import strip_omega_config

        FormModel = strip_omega_config(LoggingConfig)
        schema = FormModel.model_json_schema()
        assert "properties" in schema
        assert "level" in schema["properties"]

    def test_flattens_nested_model(self):
        from panther.config.core.models.global_config import DockerConfig
        from panther.webapp.utils.form_models import strip_omega_config

        FormModel = strip_omega_config(DockerConfig)
        # user_mapping is a nested BaseModel — should be flattened
        assert "user_mapping" not in FormModel.model_fields
        assert "user_mapping__run_as_host_user" in FormModel.model_fields
        assert "user_mapping__custom_uid" in FormModel.model_fields
        assert "user_mapping__user_name" in FormModel.model_fields

    def test_flattened_model_instantiates(self):
        from panther.config.core.models.global_config import DockerConfig
        from panther.webapp.utils.form_models import strip_omega_config

        FormModel = strip_omega_config(DockerConfig)
        instance = FormModel()
        assert instance.user_mapping__run_as_host_user is False
        assert instance.user_mapping__user_name == "panther"

    def test_flattened_model_generates_schema(self):
        from panther.config.core.models.global_config import DockerConfig
        from panther.webapp.utils.form_models import strip_omega_config

        FormModel = strip_omega_config(DockerConfig)
        schema = FormModel.model_json_schema()
        assert "properties" in schema
        assert "user_mapping__run_as_host_user" in schema["properties"]

    def test_nicecrud_compatible(self):
        from niceguicrud import NiceCRUD

        from panther.config.core.models.global_config import LoggingConfig
        from panther.webapp.utils.form_models import strip_omega_config

        FormModel = strip_omega_config(LoggingConfig)
        crud = NiceCRUD(FormModel, id_field="level")
        assert crud is not None

    def test_docker_config_nicecrud_compatible(self):
        """DockerConfig with flattened user_mapping should work with NiceCRUD."""
        from niceguicrud import NiceCRUD

        from panther.config.core.models.global_config import DockerConfig
        from panther.webapp.utils.form_models import strip_omega_config

        FormModel = strip_omega_config(DockerConfig)
        crud = NiceCRUD(FormModel, id_field="force_build_docker_image")
        assert crud is not None

    def test_all_config_models(self):
        """Verify all key config models can be stripped and used with NiceCRUD."""
        from niceguicrud import NiceCRUD

        from panther.config.core.models.global_config import (
            DockerConfig,
            FastFailConfig,
            GlobalConfig,
            LoggingConfig,
            MetricsConfig,
            PathsConfig,
            ProgressConfig,
        )
        from panther.webapp.utils.form_models import strip_omega_config

        models_and_ids = [
            (LoggingConfig, "level"),
            (PathsConfig, "output_dir"),
            (DockerConfig, "force_build_docker_image"),
            (ProgressConfig, "enable_progress_bar"),
            (FastFailConfig, "enabled"),
            (MetricsConfig, "enabled"),
            (GlobalConfig, "version"),
        ]

        for model_cls, id_field in models_and_ids:
            FormModel = strip_omega_config(model_cls)
            assert (
                "omega_config" not in FormModel.model_fields
            ), f"{model_cls.__name__} still has omega_config"
            crud = NiceCRUD(FormModel, id_field=id_field)
            assert crud is not None, f"NiceCRUD failed for {model_cls.__name__}"

    def test_model_without_omega_config(self):
        """Models without omega_config should pass through unchanged."""
        from panther.webapp.utils.form_models import strip_omega_config

        class SimpleModel(BaseModel):
            name: str = "test"
            value: int = 0

        FormModel = strip_omega_config(SimpleModel)
        assert set(FormModel.model_fields.keys()) == {"name", "value"}

    def test_form_model_naming(self):
        from panther.config.core.models.global_config import LoggingConfig
        from panther.webapp.utils.form_models import strip_omega_config

        FormModel = strip_omega_config(LoggingConfig)
        assert FormModel.__name__ == "LoggingConfigForm"


@pytest.mark.unit
class TestDefaultFactoryHandling:
    def test_default_factory_preserved(self):
        """Fields with default_factory should not crash create_model."""
        from panther.webapp.utils.form_models import strip_omega_config

        class Inner(BaseModel):
            x: int = 1

        class Outer(BaseModel):
            name: str = "test"
            items: list = Field(default_factory=list)

        FormModel = strip_omega_config(Outer)
        instance = FormModel()
        assert instance.items == []

    def test_default_factory_dict_skipped(self):
        """Dict fields with default_factory should still be skipped."""
        from panther.config.core.models.global_config import DockerConfig
        from panther.webapp.utils.form_models import strip_omega_config

        FormModel = strip_omega_config(DockerConfig)
        assert "build_args" not in FormModel.model_fields


@pytest.mark.unit
class TestFlattenNestedModel:
    def test_flatten_simple_nested(self):
        from panther.webapp.utils.form_models import _flatten_nested_model

        class Inner(BaseModel):
            x: int = 1
            y: str = "hello"

        result = _flatten_nested_model("prefix", Inner)
        assert "prefix__x" in result
        assert "prefix__y" in result

    def test_flatten_skips_dict_fields(self):
        from typing import Dict

        from panther.webapp.utils.form_models import _flatten_nested_model

        class Inner(BaseModel):
            x: int = 1
            tags: Dict[str, str] = Field(default_factory=dict)

        result = _flatten_nested_model("prefix", Inner)
        assert "prefix__x" in result
        assert "prefix__tags" not in result

    def test_flatten_skips_nested_nested(self):
        from panther.webapp.utils.form_models import _flatten_nested_model

        class DeepInner(BaseModel):
            z: int = 0

        class Inner(BaseModel):
            x: int = 1
            deep: DeepInner = Field(default_factory=DeepInner)

        result = _flatten_nested_model("prefix", Inner)
        assert "prefix__x" in result
        assert "prefix__deep" not in result
        assert "prefix__deep__z" not in result


@pytest.mark.unit
class TestUnflattenDict:
    def test_unflatten_basic(self):
        from panther.webapp.utils.form_models import unflatten_dict

        d = {"user_mapping__run_as_host_user": True, "force_build": True}
        result = unflatten_dict(d)
        assert result == {
            "user_mapping": {"run_as_host_user": True},
            "force_build": True,
        }

    def test_unflatten_multiple_nested(self):
        from panther.webapp.utils.form_models import unflatten_dict

        d = {
            "user_mapping__run_as_host_user": True,
            "user_mapping__user_name": "panther",
            "force_build": True,
        }
        result = unflatten_dict(d)
        assert result == {
            "user_mapping": {
                "run_as_host_user": True,
                "user_name": "panther",
            },
            "force_build": True,
        }

    def test_unflatten_no_nested(self):
        from panther.webapp.utils.form_models import unflatten_dict

        d = {"a": 1, "b": 2}
        assert unflatten_dict(d) == {"a": 1, "b": 2}

    def test_unflatten_empty(self):
        from panther.webapp.utils.form_models import unflatten_dict

        assert unflatten_dict({}) == {}

    def test_roundtrip_flatten_unflatten(self):
        """Flattened DockerConfig can be unflattened back to nested dict."""
        from panther.config.core.models.global_config import DockerConfig
        from panther.webapp.utils.form_models import strip_omega_config, unflatten_dict

        FormModel = strip_omega_config(DockerConfig)
        instance = FormModel()
        dumped = instance.model_dump()
        unflattened = unflatten_dict(dumped)
        assert "user_mapping" in unflattened
        assert isinstance(unflattened["user_mapping"], dict)
        assert unflattened["user_mapping"]["run_as_host_user"] is False


@pytest.mark.unit
class TestConfigFormPanel:
    def test_config_form_panel_importable(self):
        from panther.webapp.components.config_form_panel import config_form_panel

        assert callable(config_form_panel)

    def test_model_to_dict_pipeline(self):
        """Test the data pipeline: strip model -> create instance -> dump to dict -> dump to yaml."""
        from panther.config.core.models.global_config import PathsConfig
        from panther.webapp.utils.form_models import strip_omega_config

        FormModel = strip_omega_config(PathsConfig)
        instance = FormModel()
        data = instance.model_dump()
        assert isinstance(data, dict)
        assert "output_dir" in data

        yaml_str = yaml.dump(data, default_flow_style=False)
        assert isinstance(yaml_str, str)
        roundtrip = yaml.safe_load(yaml_str)
        assert roundtrip["output_dir"] == data["output_dir"]

    def test_all_global_models_schema_generation(self):
        """Global config models can be stripped and generate JSON schema for NiceCRUD."""
        from panther.config.core.models.global_config import (
            DockerConfig,
            FastFailConfig,
            LoggingConfig,
            MetricsConfig,
            PathsConfig,
            ProgressConfig,
        )
        from panther.webapp.utils.form_models import strip_omega_config

        models = [
            LoggingConfig,
            PathsConfig,
            DockerConfig,
            ProgressConfig,
            FastFailConfig,
            MetricsConfig,
        ]
        for model_cls in models:
            FormModel = strip_omega_config(model_cls)
            schema = FormModel.model_json_schema()
            assert (
                "properties" in schema
            ), f"No properties in schema for {model_cls.__name__}"
            assert (
                len(schema["properties"]) > 0
            ), f"Empty schema for {model_cls.__name__}"


@pytest.mark.unit
class TestIsUnsupportedDict:
    def test_dict_str_str_is_unsupported(self):
        from typing import Dict

        from panther.webapp.utils.form_models import _is_unsupported_dict

        assert _is_unsupported_dict(Dict[str, str]) is True

    def test_optional_dict_str_str_is_unsupported(self):
        from typing import Dict, Optional

        from panther.webapp.utils.form_models import _is_unsupported_dict

        assert _is_unsupported_dict(Optional[Dict[str, str]]) is True

    def test_plain_str_is_supported(self):
        from panther.webapp.utils.form_models import _is_unsupported_dict

        assert _is_unsupported_dict(str) is False

    def test_dict_str_basemodel_is_supported(self):
        from typing import Dict

        from panther.webapp.utils.form_models import _is_unsupported_dict

        class MyModel(BaseModel):
            x: int = 0

        assert _is_unsupported_dict(Dict[str, MyModel]) is False

    def test_strip_omega_config_excludes_build_args(self):
        from panther.config.core.models.global_config import DockerConfig
        from panther.webapp.utils.form_models import strip_omega_config

        FormModel = strip_omega_config(DockerConfig)
        assert "build_args" not in FormModel.model_fields
        assert "force_build_docker_image" in FormModel.model_fields


@pytest.mark.unit
class TestTestConfigForm:
    def test_instantiates_with_defaults(self):
        from panther.webapp.utils.form_models import TestConfigForm

        form = TestConfigForm()
        assert form.name == "my_test"
        assert form.iterations == 1
        assert form.collect_artifacts is True

    def test_network_environment_type_is_valid_enum(self):
        from panther.webapp.utils.form_models import (
            NetworkEnvironmentType,
            TestConfigForm,
        )

        form = TestConfigForm()
        assert isinstance(form.network_environment_type, NetworkEnvironmentType)
        assert form.network_environment_type == NetworkEnvironmentType.docker_compose

    def test_generates_json_schema(self):
        from panther.webapp.utils.form_models import TestConfigForm

        schema = TestConfigForm.model_json_schema()
        assert "properties" in schema
        assert "name" in schema["properties"]
        assert "network_environment_type" in schema["properties"]

    def test_nicecrud_compatible(self):
        from niceguicrud import NiceCRUD

        from panther.webapp.utils.form_models import TestConfigForm

        crud = NiceCRUD(TestConfigForm, id_field="name")
        assert crud is not None
