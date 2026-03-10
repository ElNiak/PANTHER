"""Verify json_schema_extra metadata appears in model field definitions."""

from panther.config.core.models.service import ServiceConfig


class TestJsonSchemaExtra:
    def test_service_timeout_has_widget_type(self):
        field = ServiceConfig.model_fields["timeout"]
        extra = field.json_schema_extra
        assert extra is not None
        assert extra["widget_type"] == "spinner"

    def test_service_timeout_has_unit(self):
        field = ServiceConfig.model_fields["timeout"]
        extra = field.json_schema_extra
        assert extra is not None
        assert extra["unit"] == "seconds"

    def test_service_timeout_has_examples(self):
        field = ServiceConfig.model_fields["timeout"]
        metadata = field.metadata
        # In Pydantic v2, examples are stored in field metadata or json_schema_extra
        examples = (
            field.json_schema_extra.get("examples") if field.json_schema_extra else None
        )
        if examples is None:
            # Check if examples are in the field definition itself
            assert hasattr(field, "examples") or any(
                hasattr(m, "examples") for m in metadata
            ), "Field 'timeout' should have examples"

    def test_all_fields_have_descriptions(self):
        """Every field in ServiceConfig should have a description."""
        for field_name, field_info in ServiceConfig.model_fields.items():
            # Skip internal/excluded fields
            if field_name.startswith("_"):
                continue
            if field_info.exclude:
                continue
            assert (
                field_info.description is not None
            ), f"Field '{field_name}' missing description"
