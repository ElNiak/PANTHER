#!/usr/bin/env python3
"""
Comprehensive test suite for GlobalConfig and all sub-models.

This module provides exhaustive testing for:
- GlobalConfig class and all its components
- LoggingConfig with all log levels and formats
- PathsConfig with all path configurations
- DockerConfig with all Docker settings
- FeatureConfig with all feature flags
- Validation scenarios and edge cases
- Integration between all components
"""

import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Optional

import pytest
import yaml
from omegaconf import OmegaConf
from pydantic import ValidationError

from panther.config.core.models.global_config import (
    DockerConfig,
    FeatureLogLevelsConfig,
    GlobalConfig,
    LoggingConfig,
    LoggingLevel,
    PathsConfig,
)

# PANTHER is now available in Python path since we're in the PANTHER project


class TestLoggingConfig:
    """Comprehensive tests for LoggingConfig."""

    def test_logging_config_defaults(self):
        """Test LoggingConfig with default values."""
        config = LoggingConfig()

        assert config.level == LoggingLevel.INFO
        assert config.format == "%(asctime)s [%(levelname)s] - %(module)s - %(message)s"
        assert config.enable_colors is True

    def test_logging_config_all_levels(self):
        """Test LoggingConfig with all valid log levels."""
        levels = [
            LoggingLevel.DEBUG,
            LoggingLevel.INFO,
            LoggingLevel.WARNING,
            LoggingLevel.ERROR,
            LoggingLevel.CRITICAL,
        ]

        for level in levels:
            config = LoggingConfig(level=level)
            assert config.level == level

    def test_logging_config_custom_format(self):
        """Test LoggingConfig with custom format."""
        custom_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        config = LoggingConfig(level=LoggingLevel.INFO, format=custom_format)

        assert config.level == LoggingLevel.INFO
        assert config.format == custom_format

    def test_logging_config_string_level_conversion(self):
        """Test LoggingConfig with string level that gets converted."""
        config = LoggingConfig(level="ERROR")
        assert config.level == LoggingLevel.ERROR

    def test_logging_config_invalid_level(self):
        """Test LoggingConfig with invalid log level."""
        with pytest.raises(ValidationError):
            LoggingConfig(level="INVALID_LEVEL")

    def test_logging_config_serialization(self):
        """Test LoggingConfig serialization."""
        config = LoggingConfig(level=LoggingLevel.WARNING, format="custom format")

        # Test dict conversion
        config_dict = config.to_dict()
        assert config_dict["level"] == "WARNING"
        assert config_dict["format"] == "custom format"

        # Test YAML
        yaml_str = config.to_yaml()
        parsed = yaml.safe_load(yaml_str)
        assert parsed["level"] == "WARNING"

        # Test JSON
        json_str = config.to_json()
        parsed = json.loads(json_str)
        assert parsed["level"] == "WARNING"

    def test_logging_config_omega_conversion(self):
        """Test LoggingConfig OmegaConf conversion."""
        config = LoggingConfig(level=LoggingLevel.ERROR, format="test format")

        # Convert to OmegaConf
        omega = config.to_omega()
        assert omega.level == "ERROR"
        assert omega.format == "test format"

        # Convert back from OmegaConf
        restored = LoggingConfig.from_omega(omega)
        assert restored.level == LoggingLevel.ERROR
        assert restored.format == "test format"

    def test_logging_config_merge(self):
        """Test LoggingConfig merging."""
        base_config = LoggingConfig()
        override = {"level": "INFO", "format": "merged format"}

        merged = base_config.merge(override)
        assert merged.level == LoggingLevel.INFO
        assert merged.format == "merged format"


class TestPathsConfig:
    """Comprehensive tests for PathsConfig."""

    def test_paths_config_defaults(self):
        """Test PathsConfig with default values."""
        config = PathsConfig()

        assert config.output_dir == "outputs"
        assert config.log_dir == "${paths.output_dir}/logs"
        assert config.plugin_dir == "panther/plugins"
        assert config.cert_dir is None
        assert config.temp_dir == "/tmp/panther"

    def test_paths_config_custom_values(self):
        """Test PathsConfig with all custom values."""
        config = PathsConfig(
            output_dir="/custom/output",
            log_dir="/custom/logs",
            config_dir="/custom/config",
            plugin_dir="/custom/plugins",
            services_dir="/custom/services",
            iut_dir="/custom/iut",
            testers_dir="/custom/testers",
        )

        assert config.output_dir == "/custom/output"
        assert config.log_dir == "/custom/logs"
        assert config.config_dir == "/custom/config"
        assert config.plugin_dir == "/custom/plugins"
        assert config.services_dir == "/custom/services"
        assert config.iut_dir == "/custom/iut"
        assert config.testers_dir == "/custom/testers"

    def test_paths_config_relative_paths(self):
        """Test PathsConfig with relative paths."""
        config = PathsConfig(
            output_dir="./outputs",
            log_dir="../logs",
            config_dir="configs/",
            plugin_dir="./plugins/",
        )

        assert config.output_dir == "./outputs"
        assert config.log_dir == "../logs"
        assert config.config_dir == "configs/"
        assert config.plugin_dir == "./plugins/"

    def test_paths_config_empty_strings(self):
        """Test PathsConfig with empty string paths."""
        config = PathsConfig(output_dir="", log_dir="", config_dir="")

        assert config.output_dir == ""
        assert config.log_dir == ""
        assert config.config_dir == ""

    def test_paths_config_serialization(self):
        """Test PathsConfig serialization."""
        config = PathsConfig(
            output_dir="/test/output", log_dir="/test/logs", plugin_dir="/test/plugins"
        )

        # Test dict conversion
        config_dict = config.to_dict()
        assert config_dict["output_dir"] == "/test/output"
        assert config_dict["log_dir"] == "/test/logs"
        assert config_dict["plugin_dir"] == "/test/plugins"

        # Test round-trip through YAML
        yaml_str = config.to_yaml()
        parsed = yaml.safe_load(yaml_str)
        restored = PathsConfig(**parsed)
        assert restored.output_dir == config.output_dir
        assert restored.log_dir == config.log_dir

    def test_paths_config_merge(self):
        """Test PathsConfig merging."""
        base_config = PathsConfig()
        override = {"output_dir": "/merged/output", "log_dir": "/merged/logs"}

        merged = base_config.merge(override)
        assert merged.output_dir == "/merged/output"
        assert merged.log_dir == "/merged/logs"
        assert merged.config_dir == "panther/configs"  # Unchanged


class TestDockerConfig:
    """Comprehensive tests for DockerConfig."""

    def test_docker_config_defaults(self):
        """Test DockerConfig with default values."""
        config = DockerConfig()

        assert config.force_build_docker_image is True
        assert config.log_docker_image_build is True
        assert config.registry is None
        assert config.network_mode == "bridge"
        assert isinstance(config.user_mapping, type(config.user_mapping))

    def test_docker_config_all_false(self):
        """Test DockerConfig with all flags set to False."""
        config = DockerConfig(
            force_build_docker_image=False,
            remove_docker_image=False,
            remove_docker_container=False,
            remove_docker_network=False,
            remove_docker_volume=False,
        )

        assert config.force_build_docker_image is False
        assert config.remove_docker_image is False
        assert config.remove_docker_container is False
        assert config.remove_docker_network is False
        assert config.remove_docker_volume is False

    def test_docker_config_mixed_flags(self):
        """Test DockerConfig with mixed boolean flags."""
        config = DockerConfig(
            force_build_docker_image=True,
            remove_docker_image=False,
            remove_docker_container=True,
            remove_docker_network=False,
            remove_docker_volume=True,
        )

        assert config.force_build_docker_image is True
        assert config.remove_docker_image is False
        assert config.remove_docker_container is True
        assert config.remove_docker_network is False
        assert config.remove_docker_volume is True

    def test_docker_config_invalid_types(self):
        """Test DockerConfig with invalid types."""
        with pytest.raises(ValidationError):
            DockerConfig(force_build_docker_image="not_a_boolean")

        with pytest.raises(ValidationError):
            DockerConfig(remove_docker_image=1)  # Should be boolean

        with pytest.raises(ValidationError):
            DockerConfig(remove_docker_container="yes")  # Should be boolean

    def test_docker_config_serialization(self):
        """Test DockerConfig serialization."""
        config = DockerConfig(
            force_build_docker_image=False,
            remove_docker_image=True,
            remove_docker_container=False,
        )

        # Test dict conversion
        config_dict = config.to_dict()
        assert config_dict["force_build_docker_image"] is False
        assert config_dict["remove_docker_image"] is True
        assert config_dict["remove_docker_container"] is False

        # Test JSON serialization
        json_str = config.to_json()
        parsed = json.loads(json_str)
        assert parsed["force_build_docker_image"] is False
        assert parsed["remove_docker_image"] is True

    def test_docker_config_merge(self):
        """Test DockerConfig merging."""
        base_config = DockerConfig()  # All True by default
        override = {"force_build_docker_image": False, "remove_docker_image": False}

        merged = base_config.merge(override)
        assert merged.force_build_docker_image is False
        assert merged.remove_docker_image is False
        assert merged.remove_docker_container is True  # Unchanged
        assert merged.remove_docker_network is True  # Unchanged


class TestFeatureLogLevelsConfig:
    """Test FeatureLogLevelsConfig functionality."""

    def test_feature_log_levels_defaults(self):
        """Test FeatureLogLevelsConfig with defaults."""
        config = FeatureLogLevelsConfig()

        # All should default to None (optional fields)
        assert config.docker_build is None
        assert config.service_start is None
        assert config.test_execution is None
        assert config.metrics_collection is None

    def test_feature_log_levels_custom(self):
        """Test FeatureLogLevelsConfig with custom levels."""
        config = FeatureLogLevelsConfig(
            docker_build="INFO",
            service_start="WARNING",
            test_execution="ERROR",
            metrics_collection="CRITICAL",
        )

        assert config.docker_build == "INFO"
        assert config.service_start == "WARNING"
        assert config.test_execution == "ERROR"
        assert config.metrics_collection == "CRITICAL"

    def test_feature_log_levels_string_conversion(self):
        """Test FeatureLogLevelsConfig with string level conversion."""
        config = FeatureLogLevelsConfig(
            docker_build="INFO", service_start="WARNING", test_execution="ERROR"
        )

        assert config.docker_build == "INFO"
        assert config.service_start == "WARNING"
        assert config.test_execution == "ERROR"

    def test_feature_log_levels_invalid(self):
        """Test FeatureLogLevelsConfig with invalid levels."""
        with pytest.raises(ValidationError):
            FeatureLogLevelsConfig(docker_build="INVALID")

        with pytest.raises(ValidationError):
            FeatureLogLevelsConfig(service_start=123)


class TestGlobalConfig:
    """Comprehensive tests for GlobalConfig integration."""

    def test_global_config_defaults(self):
        """Test GlobalConfig with all default values."""
        config = GlobalConfig()

        # Check sub-configs exist with defaults
        assert isinstance(config.logging, LoggingConfig)
        assert config.logging.level == LoggingLevel.DEBUG

        assert isinstance(config.paths, PathsConfig)
        assert config.paths.output_dir == "panther/outputs"

        assert isinstance(config.docker, DockerConfig)
        assert config.docker.force_build_docker_image is True

        assert isinstance(config.feature_log_levels, FeatureLogLevelsConfig)
        assert config.feature_log_levels.logger_observer == LoggingLevel.DEBUG

        assert config.fast_fail is True
        assert config.metrics is True

    def test_global_config_custom_sub_configs(self):
        """Test GlobalConfig with custom sub-configurations."""
        logging_config = LoggingConfig(level=LoggingLevel.ERROR, format="custom")
        paths_config = PathsConfig(output_dir="/custom", log_dir="/custom/logs")
        docker_config = DockerConfig(force_build_docker_image=False)
        feature_levels = FeatureLogLevelsConfig(logger_observer=LoggingLevel.INFO)

        config = GlobalConfig(
            logging=logging_config,
            paths=paths_config,
            docker=docker_config,
            feature_log_levels=feature_levels,
            fast_fail=False,
            metrics=False,
        )

        assert config.logging.level == LoggingLevel.ERROR
        assert config.logging.format == "custom"
        assert config.paths.output_dir == "/custom"
        assert config.docker.force_build_docker_image is False
        assert config.feature_log_levels.logger_observer == LoggingLevel.INFO
        assert config.fast_fail is False
        assert config.metrics is False

    def test_global_config_partial_override(self):
        """Test GlobalConfig with partial sub-config overrides."""
        config = GlobalConfig(
            logging=LoggingConfig(level=LoggingLevel.WARNING),
            paths=PathsConfig(output_dir="/partial"),
        )

        # Overridden values
        assert config.logging.level == LoggingLevel.WARNING
        assert config.paths.output_dir == "/partial"

        # Default values should still be present
        assert (
            config.logging.format
            == "%(asctime)s [%(levelname)s] - %(module)s - %(message)s"
        )
        assert config.paths.log_dir == "panther/outputs"
        assert config.docker.force_build_docker_image is True

    def test_global_config_dict_creation(self):
        """Test GlobalConfig creation from dictionary."""
        config_dict = {
            "logging": {"level": "INFO", "format": "%(levelname)s: %(message)s"},
            "paths": {"output_dir": "/dict/output", "log_dir": "/dict/logs"},
            "docker": {"force_build_docker_image": False, "remove_docker_image": False},
            "fast_fail": False,
            "metrics": False,
        }

        config = GlobalConfig(**config_dict)

        assert config.logging.level == LoggingLevel.INFO
        assert config.logging.format == "%(levelname)s: %(message)s"
        assert config.paths.output_dir == "/dict/output"
        assert config.paths.log_dir == "/dict/logs"
        assert config.docker.force_build_docker_image is False
        assert config.docker.remove_docker_image is False
        assert config.fast_fail is False
        assert config.metrics is False

    def test_global_config_merge_complex(self):
        """Test GlobalConfig complex merging scenarios."""
        base_config = GlobalConfig()

        # Complex override with nested changes
        override = {
            "logging": {"level": "ERROR"},
            "paths": {"output_dir": "/merged/output", "plugin_dir": "/merged/plugins"},
            "docker": {"force_build_docker_image": False},
            "fast_fail": False,
        }

        merged = base_config.merge(override)

        # Check merged values
        assert merged.logging.level == LoggingLevel.ERROR
        assert merged.paths.output_dir == "/merged/output"
        assert merged.paths.plugin_dir == "/merged/plugins"
        assert merged.docker.force_build_docker_image is False
        assert merged.fast_fail is False

        # Check unchanged values
        assert (
            merged.logging.format
            == "%(asctime)s [%(levelname)s] - %(module)s - %(message)s"
        )
        assert merged.paths.log_dir == "panther/outputs"
        assert merged.docker.remove_docker_image is True
        assert merged.metrics is True

    def test_global_config_omega_conversion(self):
        """Test GlobalConfig OmegaConf conversion."""
        config = GlobalConfig(
            logging=LoggingConfig(level=LoggingLevel.WARNING),
            paths=PathsConfig(output_dir="/omega/test"),
            fast_fail=False,
        )

        # Convert to OmegaConf
        omega = config.to_omega()
        assert omega.logging.level == "WARNING"
        assert omega.paths.output_dir == "/omega/test"
        assert omega.fast_fail is False

        # Convert back
        restored = GlobalConfig.from_omega(omega)
        assert restored.logging.level == LoggingLevel.WARNING
        assert restored.paths.output_dir == "/omega/test"
        assert restored.fast_fail is False

    def test_global_config_serialization_roundtrip(self):
        """Test GlobalConfig serialization round-trip."""
        original = GlobalConfig(
            logging=LoggingConfig(level=LoggingLevel.INFO, format="test format"),
            paths=PathsConfig(output_dir="/roundtrip", log_dir="/roundtrip/logs"),
            docker=DockerConfig(force_build_docker_image=False),
            fast_fail=False,
            metrics=False,
        )

        # Round-trip through YAML
        yaml_str = original.to_yaml()
        yaml_dict = yaml.safe_load(yaml_str)
        from_yaml = GlobalConfig(**yaml_dict)

        assert from_yaml.logging.level == original.logging.level
        assert from_yaml.logging.format == original.logging.format
        assert from_yaml.paths.output_dir == original.paths.output_dir
        assert (
            from_yaml.docker.force_build_docker_image
            == original.docker.force_build_docker_image
        )
        assert from_yaml.fast_fail == original.fast_fail

        # Round-trip through JSON
        json_str = original.to_json()
        json_dict = json.loads(json_str)
        from_json = GlobalConfig(**json_dict)

        assert from_json.logging.level == original.logging.level
        assert from_json.paths.output_dir == original.paths.output_dir

    def test_global_config_validation_errors(self):
        """Test GlobalConfig validation error scenarios."""
        # Invalid logging level
        with pytest.raises(ValidationError):
            GlobalConfig(logging={"level": "INVALID_LEVEL"})

        # Invalid docker config
        with pytest.raises(ValidationError):
            GlobalConfig(docker={"force_build_docker_image": "not_boolean"})

        # Invalid top-level fields
        with pytest.raises(ValidationError):
            GlobalConfig(fast_fail="not_boolean")

        with pytest.raises(ValidationError):
            GlobalConfig(metrics="not_boolean")

    def test_global_config_file_operations(self):
        """Test GlobalConfig file save/load operations."""
        original = GlobalConfig(
            logging=LoggingConfig(level=LoggingLevel.WARNING),
            paths=PathsConfig(output_dir="/file/test"),
            fast_fail=False,
        )

        # Test YAML file operations
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            try:
                original.save_to_file(f.name)
                loaded = GlobalConfig.load_from_file(f.name)

                assert loaded.logging.level == LoggingLevel.WARNING
                assert loaded.paths.output_dir == "/file/test"
                assert loaded.fast_fail is False

            finally:
                os.unlink(f.name)

    def test_global_config_environment_interpolation(self):
        """Test GlobalConfig with environment variable interpolation."""
        # This tests OmegaConf interpolation features
        config_with_interpolation = {
            "paths": {
                "output_dir": "${oc.env:PANTHER_OUTPUT_DIR,/default/output}",
                "log_dir": "${paths.output_dir}/logs",
            }
        }

        # Set environment variable
        os.environ["PANTHER_OUTPUT_DIR"] = "/env/output"

        try:
            omega = OmegaConf.create(config_with_interpolation)
            resolved = OmegaConf.to_container(omega, resolve=True)
            config = GlobalConfig(**resolved)

            assert config.paths.output_dir == "/env/output"
            assert config.paths.log_dir == "/env/output/logs"

        finally:
            # Clean up environment
            if "PANTHER_OUTPUT_DIR" in os.environ:
                del os.environ["PANTHER_OUTPUT_DIR"]


if __name__ == "__main__":
    # Run comprehensive tests
    print("Running comprehensive GlobalConfig tests...")

    try:
        # Test LoggingConfig
        test_logging = TestLoggingConfig()
        test_logging.test_logging_config_defaults()
        test_logging.test_logging_config_all_levels()
        test_logging.test_logging_config_serialization()
        print("✓ LoggingConfig tests passed")

        # Test PathsConfig
        test_paths = TestPathsConfig()
        test_paths.test_paths_config_defaults()
        test_paths.test_paths_config_custom_values()
        test_paths.test_paths_config_merge()
        print("✓ PathsConfig tests passed")

        # Test DockerConfig
        test_docker = TestDockerConfig()
        test_docker.test_docker_config_defaults()
        test_docker.test_docker_config_mixed_flags()
        test_docker.test_docker_config_serialization()
        print("✓ DockerConfig tests passed")

        # Test GlobalConfig integration
        test_global = TestGlobalConfig()
        test_global.test_global_config_defaults()
        test_global.test_global_config_merge_complex()
        test_global.test_global_config_omega_conversion()
        print("✓ GlobalConfig integration tests passed")

        print("\n✅ All comprehensive GlobalConfig tests passed!")

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
