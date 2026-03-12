"""Tests for form_models type introspection utilities."""

from typing import Any, Dict, List, Optional

import pytest
import yaml
from pydantic import BaseModel, Field


@pytest.mark.unit
class TestClassifyComplexField:
    def test_dict_str_str(self):
        from panther.webapp.components.forms.form_models import classify_complex_field

        assert classify_complex_field(Dict[str, str]) == "dict_str"

    def test_dict_str_any(self):
        from panther.webapp.components.forms.form_models import classify_complex_field

        assert classify_complex_field(Dict[str, Any]) == "dict_str"

    def test_dict_str_basemodel(self):
        from panther.webapp.components.forms.form_models import classify_complex_field

        class Inner(BaseModel):
            x: int = 0

        assert classify_complex_field(Dict[str, Inner]) == "dict_model"

    def test_list_basemodel(self):
        from panther.webapp.components.forms.form_models import classify_complex_field

        class Inner(BaseModel):
            x: int = 0

        assert classify_complex_field(List[Inner]) == "list_model"

    def test_optional_dict_unwraps(self):
        from panther.webapp.components.forms.form_models import classify_complex_field

        assert classify_complex_field(Optional[Dict[str, str]]) == "dict_str"

    def test_list_str_returns_none(self):
        from panther.webapp.components.forms.form_models import classify_complex_field

        assert classify_complex_field(list[str]) is None

    def test_plain_str_returns_none(self):
        from panther.webapp.components.forms.form_models import classify_complex_field

        assert classify_complex_field(str) is None


@pytest.mark.unit
class TestGetComplexFields:
    def test_docker_config_has_build_args(self):
        from panther.config.core.models.global_config import DockerConfig
        from panther.webapp.components.forms.form_models import get_complex_fields

        fields = get_complex_fields(DockerConfig)
        assert "build_args" in fields
        assert fields["build_args"].category == "dict_str"

    def test_test_config_has_services_and_execution_env(self):
        from panther.config.core.models.experiment import TestConfig
        from panther.webapp.components.forms.form_models import get_complex_fields

        fields = get_complex_fields(TestConfig)
        assert "services" in fields
        assert fields["services"].category == "dict_model"
        assert "execution_environment" in fields
        assert fields["execution_environment"].category == "list_model"

    def test_paths_config_has_none(self):
        from panther.config.core.models.global_config import PathsConfig
        from panther.webapp.components.forms.form_models import get_complex_fields

        assert get_complex_fields(PathsConfig) == {}


@pytest.mark.unit
class TestExtractSectionData:
    def test_dot_notation(self):
        from panther.webapp.components.forms.form_models import extract_section_data

        cfg = {"a": {"b": {"c": 42}}}
        assert extract_section_data(cfg, "a.b.c") == 42

    def test_list_index(self):
        from panther.webapp.components.forms.form_models import extract_section_data

        cfg = {"tests": [{"name": "t0"}, {"name": "t1"}]}
        assert extract_section_data(cfg, "tests.1.name") == "t1"

    def test_missing_returns_none(self):
        from panther.webapp.components.forms.form_models import extract_section_data

        assert extract_section_data({"a": 1}, "b.c") is None


@pytest.mark.unit
class TestGlobalSectionMeta:
    def test_meta_has_expected_sections(self):
        from panther.webapp.components.forms.form_models import GLOBAL_SECTION_META

        assert "logging" in GLOBAL_SECTION_META
        assert "docker" in GLOBAL_SECTION_META
        assert "paths" in GLOBAL_SECTION_META

    def test_meta_values_are_tuples(self):
        from panther.webapp.components.forms.form_models import GLOBAL_SECTION_META

        for key, val in GLOBAL_SECTION_META.items():
            assert isinstance(val, tuple), f"{key} value is not a tuple"
            assert len(val) == 2, f"{key} tuple has wrong length"
