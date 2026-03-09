"""Tests for CompatibilityValidator after cleanup."""

from panther.config.core.components.validators import CompatibilityValidator


class TestCompatibilityValidatorCleaned:
    def test_no_warnings_on_valid_config(self):
        """No legacy checks remain — any valid dict should pass clean."""
        validator = CompatibilityValidator()
        result = validator.validate({"some_field": "value"})
        assert result.is_valid
        assert len(result.warnings) == 0

    def test_empty_config(self):
        validator = CompatibilityValidator()
        result = validator.validate({})
        assert result.is_valid
        assert len(result.warnings) == 0

    def test_formerly_deprecated_fields_no_warnings(self):
        """Fields that were formerly deprecated should no longer trigger warnings."""
        validator = CompatibilityValidator()
        result = validator.validate({"use_docker": True, "log_level": "INFO"})
        assert result.is_valid
        assert len(result.warnings) == 0

    def test_legacy_config_key_no_warnings(self):
        """Legacy nested 'config' key should no longer trigger warnings."""
        validator = CompatibilityValidator()
        result = validator.validate({"config": {"nested": "value"}})
        assert result.is_valid
        assert len(result.warnings) == 0
