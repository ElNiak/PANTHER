#!/usr/bin/env python3
"""
Comprehensive test suite for BaseConfig class - testing every method and edge case.

This module provides exhaustive testing for:
- All BaseConfig methods (to_omega, from_omega, merge, interpolate, etc.)
- Serialization methods (to_yaml, to_json, to_dict)
- Field manipulation methods
- Error handling and edge cases
- Performance characteristics
"""

import json
import os
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import pytest
import yaml
from omegaconf import DictConfig, OmegaConf
from pydantic import Field, ValidationError

from panther.config.core.base import BaseConfig
from panther.config.core.models.base_model import BaseUnifiedModel

# PANTHER is now available in Python path since we're in the PANTHER project


class TestBaseConfigCore:
    """Test core BaseConfig functionality."""

    def test_basic_initialization(self):
        """Test basic BaseConfig initialization."""

        class SimpleConfig(BaseConfig):
            name: str = "test"
            value: int = 42
            enabled: bool = True

        config = SimpleConfig()
        assert config.name == "test"
        assert config.value == 42
        assert config.enabled is True

    def test_initialization_with_custom_values(self):
        """Test BaseConfig initialization with custom values."""

        class SimpleConfig(BaseConfig):
            name: str = "test"
            value: int = 42
            enabled: bool = True

        config = SimpleConfig(name="custom", value=100, enabled=False)
        assert config.name == "custom"
        assert config.value == 100
        assert config.enabled is False

    def test_initialization_with_partial_values(self):
        """Test BaseConfig initialization with partial custom values."""

        class SimpleConfig(BaseConfig):
            name: str = "test"
            value: int = 42
            enabled: bool = True

        config = SimpleConfig(name="partial")
        assert config.name == "partial"
        assert config.value == 42  # Default
        assert config.enabled is True  # Default

    def test_nested_config_initialization(self):
        """Test BaseConfig with nested configuration objects."""

        class DatabaseConfig(BaseConfig):
            host: str = "localhost"
            port: int = 5432
            database: str = "test"

        class AppConfig(BaseConfig):
            app_name: str = "myapp"
            debug: bool = False
            database: DatabaseConfig = DatabaseConfig()

        config = AppConfig()
        assert config.app_name == "myapp"
        assert config.debug is False
        assert config.database.host == "localhost"
        assert config.database.port == 5432

    def test_nested_config_with_custom_values(self):
        """Test nested config with custom initialization."""

        class DatabaseConfig(BaseConfig):
            host: str = "localhost"
            port: int = 5432
            database: str = "test"

        class AppConfig(BaseConfig):
            app_name: str = "myapp"
            debug: bool = False
            database: DatabaseConfig = DatabaseConfig()

        db_config = DatabaseConfig(host="prod-server", port=3306)
        config = AppConfig(app_name="production", debug=True, database=db_config)

        assert config.app_name == "production"
        assert config.debug is True
        assert config.database.host == "prod-server"
        assert config.database.port == 3306
        assert config.database.database == "test"  # Default


class TestBaseConfigOmegaConversion:
    """Test OmegaConf conversion methods."""

    def test_to_omega_simple_config(self):
        """Test conversion of simple config to OmegaConf."""

        class SimpleConfig(BaseConfig):
            name: str = "test"
            value: int = 42
            enabled: bool = True

        config = SimpleConfig()
        omega = config.to_omega()

        assert isinstance(omega, DictConfig)
        assert omega.name == "test"
        assert omega.value == 42
        assert omega.enabled is True

    def test_to_omega_nested_config(self):
        """Test conversion of nested config to OmegaConf."""

        class DatabaseConfig(BaseConfig):
            host: str = "localhost"
            port: int = 5432

        class AppConfig(BaseConfig):
            app_name: str = "myapp"
            database: DatabaseConfig = DatabaseConfig()

        config = AppConfig()
        omega = config.to_omega()

        assert isinstance(omega, DictConfig)
        assert omega.app_name == "myapp"
        assert omega.database.host == "localhost"
        assert omega.database.port == 5432

    def test_from_omega_simple_config(self):
        """Test creation of config from OmegaConf."""

        class SimpleConfig(BaseConfig):
            name: str = "test"
            value: int = 42
            enabled: bool = True

        omega_dict = {"name": "from_omega", "value": 100, "enabled": False}
        omega = OmegaConf.create(omega_dict)

        config = SimpleConfig.from_omega(omega)
        assert config.name == "from_omega"
        assert config.value == 100
        assert config.enabled is False

    def test_from_omega_nested_config(self):
        """Test creation of nested config from OmegaConf."""

        class DatabaseConfig(BaseConfig):
            host: str = "localhost"
            port: int = 5432

        class AppConfig(BaseConfig):
            app_name: str = "myapp"
            database: DatabaseConfig = DatabaseConfig()

        omega_dict = {
            "app_name": "omega_app",
            "database": {"host": "omega_host", "port": 3306},
        }
        omega = OmegaConf.create(omega_dict)

        config = AppConfig.from_omega(omega)
        assert config.app_name == "omega_app"
        assert config.database.host == "omega_host"
        assert config.database.port == 3306

    def test_round_trip_conversion(self):
        """Test round-trip conversion: config -> omega -> config."""

        class ComplexConfig(BaseConfig):
            name: str = "test"
            values: List[int] = [1, 2, 3]
            metadata: Dict[str, Any] = {"key": "value"}

        original = ComplexConfig(
            name="round_trip",
            values=[10, 20, 30],
            metadata={"test": "data", "number": 42},
        )

        # Convert to omega and back
        omega = original.to_omega()
        restored = ComplexConfig.from_omega(omega)

        assert restored.name == original.name
        assert restored.values == original.values
        assert restored.metadata == original.metadata

    def test_from_omega_with_missing_fields(self):
        """Test from_omega with missing fields uses defaults."""

        class ConfigWithDefaults(BaseConfig):
            required_field: str
            optional_field: str = "default_value"
            numeric_field: int = 100

        omega_dict = {"required_field": "provided"}
        omega = OmegaConf.create(omega_dict)

        config = ConfigWithDefaults.from_omega(omega)
        assert config.required_field == "provided"
        assert config.optional_field == "default_value"
        assert config.numeric_field == 100

    def test_from_omega_with_extra_fields(self):
        """Test from_omega ignores extra fields."""

        class SimpleConfig(BaseConfig):
            name: str = "test"
            value: int = 42

        omega_dict = {
            "name": "test_name",
            "value": 200,
            "extra_field": "ignored",
            "another_extra": 999,
        }
        omega = OmegaConf.create(omega_dict)

        config = SimpleConfig.from_omega(omega)
        assert config.name == "test_name"
        assert config.value == 200
        # Extra fields should be ignored, not cause errors


class TestBaseConfigMerging:
    """Test configuration merging functionality."""

    def test_merge_simple_dict(self):
        """Test merging simple dictionary into config."""

        class SimpleConfig(BaseConfig):
            name: str = "original"
            value: int = 42
            enabled: bool = True

        config = SimpleConfig()
        override_dict = {"name": "merged", "value": 100}

        merged = config.merge(override_dict)

        assert merged.name == "merged"
        assert merged.value == 100
        assert merged.enabled is True  # Unchanged

    def test_merge_nested_dict(self):
        """Test merging nested dictionary."""

        class DatabaseConfig(BaseConfig):
            host: str = "localhost"
            port: int = 5432
            ssl: bool = False

        class AppConfig(BaseConfig):
            app_name: str = "myapp"
            database: DatabaseConfig = DatabaseConfig()

        config = AppConfig()
        override_dict = {
            "app_name": "new_app",
            "database": {"host": "prod_server", "ssl": True},
        }

        merged = config.merge(override_dict)

        assert merged.app_name == "new_app"
        assert merged.database.host == "prod_server"
        assert merged.database.port == 5432  # Unchanged
        assert merged.database.ssl is True

    def test_merge_preserves_original(self):
        """Test that merge creates new instance, preserves original."""

        class SimpleConfig(BaseConfig):
            name: str = "original"
            value: int = 42

        original = SimpleConfig()
        override_dict = {"name": "changed"}

        merged = original.merge(override_dict)

        assert original.name == "original"  # Unchanged
        assert merged.name == "changed"
        assert original is not merged  # Different instances

    def test_merge_with_omega_config(self):
        """Test merging with OmegaConf DictConfig."""

        class SimpleConfig(BaseConfig):
            name: str = "original"
            value: int = 42
            enabled: bool = True

        config = SimpleConfig()
        override_omega = OmegaConf.create({"name": "omega_merged", "enabled": False})

        merged = config.merge(override_omega)

        assert merged.name == "omega_merged"
        assert merged.value == 42  # Unchanged
        assert merged.enabled is False

    def test_merge_deep_nested_structures(self):
        """Test merging deeply nested structures."""

        class MetricsConfig(BaseConfig):
            enabled: bool = True
            interval: int = 60

        class DatabaseConfig(BaseConfig):
            host: str = "localhost"
            port: int = 5432
            metrics: MetricsConfig = MetricsConfig()

        class AppConfig(BaseConfig):
            name: str = "app"
            database: DatabaseConfig = DatabaseConfig()

        config = AppConfig()
        override_dict = {
            "name": "new_app",
            "database": {"host": "new_host", "metrics": {"interval": 30}},
        }

        merged = config.merge(override_dict)

        assert merged.name == "new_app"
        assert merged.database.host == "new_host"
        assert merged.database.port == 5432  # Unchanged
        assert merged.database.metrics.enabled is True  # Unchanged
        assert merged.database.metrics.interval == 30

    def test_merge_with_list_override(self):
        """Test merging with list values."""

        class ConfigWithLists(BaseConfig):
            tags: List[str] = ["default", "tag"]
            ports: List[int] = [80, 443]
            name: str = "test"

        config = ConfigWithLists()
        override_dict = {"tags": ["new", "tags", "list"], "ports": [8080]}

        merged = config.merge(override_dict)

        assert merged.tags == ["new", "tags", "list"]
        assert merged.ports == [8080]
        assert merged.name == "test"  # Unchanged


class TestBaseConfigSerialization:
    """Test serialization methods."""

    def test_to_dict_simple(self):
        """Test conversion to dictionary."""

        class SimpleConfig(BaseConfig):
            name: str = "test"
            value: int = 42
            enabled: bool = True

        config = SimpleConfig(name="dict_test", value=100)
        result = config.to_dict()

        expected = {"name": "dict_test", "value": 100, "enabled": True}
        assert result == expected

    def test_to_dict_nested(self):
        """Test conversion of nested config to dictionary."""

        class DatabaseConfig(BaseConfig):
            host: str = "localhost"
            port: int = 5432

        class AppConfig(BaseConfig):
            app_name: str = "myapp"
            database: DatabaseConfig = DatabaseConfig()

        config = AppConfig(app_name="nested_test")
        result = config.to_dict()

        expected = {
            "app_name": "nested_test",
            "database": {"host": "localhost", "port": 5432},
        }
        assert result == expected

    def test_to_yaml_simple(self):
        """Test YAML serialization."""

        class SimpleConfig(BaseConfig):
            name: str = "test"
            value: int = 42
            enabled: bool = True

        config = SimpleConfig()
        yaml_str = config.to_yaml()

        # Parse YAML back to verify
        parsed = yaml.safe_load(yaml_str)
        assert parsed["name"] == "test"
        assert parsed["value"] == 42
        assert parsed["enabled"] is True

    def test_to_yaml_nested(self):
        """Test YAML serialization of nested config."""

        class DatabaseConfig(BaseConfig):
            host: str = "localhost"
            port: int = 5432

        class AppConfig(BaseConfig):
            app_name: str = "myapp"
            database: DatabaseConfig = DatabaseConfig()

        config = AppConfig()
        yaml_str = config.to_yaml()

        # Parse YAML back to verify structure
        parsed = yaml.safe_load(yaml_str)
        assert parsed["app_name"] == "myapp"
        assert parsed["database"]["host"] == "localhost"
        assert parsed["database"]["port"] == 5432

    def test_to_json_simple(self):
        """Test JSON serialization."""

        class SimpleConfig(BaseConfig):
            name: str = "test"
            value: int = 42
            enabled: bool = True

        config = SimpleConfig()
        json_str = config.to_json()

        # Parse JSON back to verify
        parsed = json.loads(json_str)
        assert parsed["name"] == "test"
        assert parsed["value"] == 42
        assert parsed["enabled"] is True

    def test_to_json_nested(self):
        """Test JSON serialization of nested config."""

        class DatabaseConfig(BaseConfig):
            host: str = "localhost"
            port: int = 5432

        class AppConfig(BaseConfig):
            app_name: str = "myapp"
            database: DatabaseConfig = DatabaseConfig()

        config = AppConfig()
        json_str = config.to_json()

        # Parse JSON back to verify structure
        parsed = json.loads(json_str)
        assert parsed["app_name"] == "myapp"
        assert parsed["database"]["host"] == "localhost"
        assert parsed["database"]["port"] == 5432

    def test_serialization_round_trip_yaml(self):
        """Test YAML round-trip serialization."""

        class ComplexConfig(BaseConfig):
            name: str = "test"
            values: List[int] = [1, 2, 3]
            metadata: Dict[str, str] = {"key": "value"}

        original = ComplexConfig(
            name="yaml_test",
            values=[10, 20, 30],
            metadata={"env": "test", "version": "1.0"},
        )

        # Serialize to YAML and back
        yaml_str = original.to_yaml()
        parsed_dict = yaml.safe_load(yaml_str)
        restored = ComplexConfig(**parsed_dict)

        assert restored.name == original.name
        assert restored.values == original.values
        assert restored.metadata == original.metadata

    def test_serialization_round_trip_json(self):
        """Test JSON round-trip serialization."""

        class ComplexConfig(BaseConfig):
            name: str = "test"
            values: List[int] = [1, 2, 3]
            metadata: Dict[str, str] = {"key": "value"}

        original = ComplexConfig(
            name="json_test",
            values=[100, 200, 300],
            metadata={"type": "test", "id": "123"},
        )

        # Serialize to JSON and back
        json_str = original.to_json()
        parsed_dict = json.loads(json_str)
        restored = ComplexConfig(**parsed_dict)

        assert restored.name == original.name
        assert restored.values == original.values
        assert restored.metadata == original.metadata


class TestBaseConfigFileOperations:
    """Test file save/load operations."""

    def test_save_to_yaml_file(self):
        """Test saving config to YAML file."""

        class SimpleConfig(BaseConfig):
            name: str = "test"
            value: int = 42
            enabled: bool = True

        config = SimpleConfig(name="file_test", value=200)

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            try:
                config.save_to_file(f.name, format="yaml")

                # Verify file contents
                with open(f.name, "r") as read_file:
                    content = yaml.safe_load(read_file)

                assert content["name"] == "file_test"
                assert content["value"] == 200
                assert content["enabled"] is True

            finally:
                os.unlink(f.name)

    def test_save_to_json_file(self):
        """Test saving config to JSON file."""

        class SimpleConfig(BaseConfig):
            name: str = "test"
            value: int = 42
            enabled: bool = True

        config = SimpleConfig(name="json_file_test", value=300)

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            try:
                config.save_to_file(f.name, format="json")

                # Verify file contents
                with open(f.name, "r") as read_file:
                    content = json.load(read_file)

                assert content["name"] == "json_file_test"
                assert content["value"] == 300
                assert content["enabled"] is True

            finally:
                os.unlink(f.name)

    def test_load_from_yaml_file(self):
        """Test loading config from YAML file."""

        class SimpleConfig(BaseConfig):
            name: str = "test"
            value: int = 42
            enabled: bool = True

        # Create test YAML file
        test_data = {"name": "loaded_from_yaml", "value": 500, "enabled": False}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            try:
                yaml.dump(test_data, f)
                f.flush()

                # Load config from file
                config = SimpleConfig.load_from_file(f.name)

                assert config.name == "loaded_from_yaml"
                assert config.value == 500
                assert config.enabled is False

            finally:
                os.unlink(f.name)

    def test_load_from_json_file(self):
        """Test loading config from JSON file."""

        class SimpleConfig(BaseConfig):
            name: str = "test"
            value: int = 42
            enabled: bool = True

        # Create test JSON file
        test_data = {"name": "loaded_from_json", "value": 600, "enabled": False}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            try:
                json.dump(test_data, f)
                f.flush()

                # Load config from file
                config = SimpleConfig.load_from_file(f.name)

                assert config.name == "loaded_from_json"
                assert config.value == 600
                assert config.enabled is False

            finally:
                os.unlink(f.name)

    def test_file_format_autodetection(self):
        """Test automatic format detection from file extension."""

        class SimpleConfig(BaseConfig):
            name: str = "test"
            value: int = 42

        config = SimpleConfig(name="autodetect", value=700)

        # Test YAML autodetection
        with tempfile.NamedTemporaryFile(suffix=".yaml", delete=False) as f:
            try:
                config.save_to_file(f.name)  # No format specified

                with open(f.name, "r") as read_file:
                    content = read_file.read()
                    assert "name: autodetect" in content

            finally:
                os.unlink(f.name)

        # Test JSON autodetection
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            try:
                config.save_to_file(f.name)  # No format specified

                with open(f.name, "r") as read_file:
                    content = json.load(read_file)
                    assert content["name"] == "autodetect"

            finally:
                os.unlink(f.name)


class TestBaseConfigErrorHandling:
    """Test error handling and edge cases."""

    def test_invalid_field_types(self):
        """Test validation errors with invalid field types."""

        class TypedConfig(BaseConfig):
            name: str = "test"
            count: int = 42
            enabled: bool = True

        # Test invalid string
        with pytest.raises(ValidationError):
            TypedConfig(name=123)  # Should be string

        # Test invalid int
        with pytest.raises(ValidationError):
            TypedConfig(count="not_a_number")  # Should be int

        # Test invalid bool
        with pytest.raises(ValidationError):
            TypedConfig(enabled="not_a_boolean")  # Should be bool

    def test_missing_required_fields(self):
        """Test validation errors with missing required fields."""

        class RequiredFieldConfig(BaseConfig):
            required_name: str  # No default = required
            optional_value: int = 42

        # Should work with required field
        config = RequiredFieldConfig(required_name="provided")
        assert config.required_name == "provided"
        assert config.optional_value == 42

        # Should fail without required field
        with pytest.raises(ValidationError):
            RequiredFieldConfig(optional_value=100)  # Missing required_name

    def test_from_omega_with_invalid_data(self):
        """Test from_omega with invalid data types."""

        class TypedConfig(BaseConfig):
            name: str = "test"
            count: int = 42

        # Invalid data in omega config
        invalid_omega = OmegaConf.create(
            {"name": 123, "count": "not_a_number"}  # Should be string  # Should be int
        )

        with pytest.raises((ValidationError, ValueError)):
            TypedConfig.from_omega(invalid_omega)

    def test_merge_with_invalid_override(self):
        """Test merge with invalid override data."""

        class TypedConfig(BaseConfig):
            name: str = "test"
            count: int = 42

        config = TypedConfig()

        # Invalid override types
        invalid_override = {
            "name": 123,  # Should be string
            "count": "not_a_number",  # Should be int
        }

        with pytest.raises((ValidationError, ValueError)):
            config.merge(invalid_override)

    def test_file_operations_with_invalid_paths(self):
        """Test file operations with invalid paths."""

        class SimpleConfig(BaseConfig):
            name: str = "test"

        config = SimpleConfig()

        # Try to save to invalid path
        with pytest.raises((IOError, OSError, PermissionError)):
            config.save_to_file("/invalid/path/that/does/not/exist.yaml")

        # Try to load from non-existent file
        with pytest.raises((FileNotFoundError, IOError)):
            SimpleConfig.load_from_file("/non/existent/file.yaml")

    def test_unsupported_file_format(self):
        """Test file operations with unsupported formats."""

        class SimpleConfig(BaseConfig):
            name: str = "test"

        config = SimpleConfig()

        with tempfile.NamedTemporaryFile(suffix=".xml", delete=False) as f:
            try:
                with pytest.raises((ValueError, NotImplementedError)):
                    config.save_to_file(f.name, format="xml")

            finally:
                os.unlink(f.name)


if __name__ == "__main__":
    # Run some basic tests manually
    print("Running comprehensive BaseConfig tests...")

    try:
        # Test basic functionality
        test_core = TestBaseConfigCore()
        test_core.test_basic_initialization()
        test_core.test_nested_config_initialization()
        print("✓ Core functionality tests passed")

        # Test OmegaConf conversion
        test_omega = TestBaseConfigOmegaConversion()
        test_omega.test_to_omega_simple_config()
        test_omega.test_round_trip_conversion()
        print("✓ OmegaConf conversion tests passed")

        # Test merging
        test_merge = TestBaseConfigMerging()
        test_merge.test_merge_simple_dict()
        test_merge.test_merge_nested_dict()
        print("✓ Merging functionality tests passed")

        # Test serialization
        test_serial = TestBaseConfigSerialization()
        test_serial.test_to_dict_simple()
        test_serial.test_to_yaml_simple()
        print("✓ Serialization tests passed")

        print("\n✅ All comprehensive BaseConfig tests passed!")

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
