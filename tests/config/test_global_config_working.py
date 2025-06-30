#!/usr/bin/env python3
"""
Working comprehensive test suite for GlobalConfig and all sub-models.

This module provides exhaustive testing based on the actual structure found in PANTHER.
"""

import json
import os
import sys
import tempfile
from pathlib import Path

import pytest
import yaml
from omegaconf import OmegaConf
from pydantic import ValidationError

from panther.config.core.models.global_config import (
    DockerConfig,
    DockerUserMappingConfig,
    FastFailConfig,
    FeatureLogLevelsConfig,
    GlobalConfig,
    LoggingConfig,
    LoggingLevel,
    MetricsConfig,
    PathsConfig,
    ProgressConfig,
)

# Add PANTHER to Python path
# PANTHER is now available in Python path since we're in the PANTHER project


class TestLoggingConfig:
    """Comprehensive tests for LoggingConfig."""

    def test_logging_config_defaults(self):
        """Test LoggingConfig with default values."""
        config = LoggingConfig()

        assert config.level == LoggingLevel.INFO
        assert config.format == "%(asctime)s [%(levelname)s] - %(module)s - %(message)s"
        assert config.enable_colors is True
        assert isinstance(config.feature_levels, FeatureLogLevelsConfig)

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
            plugin_dir="/custom/plugins",
            cert_dir="/custom/certs",
            temp_dir="/custom/temp",
        )

        assert config.output_dir == "/custom/output"
        assert config.log_dir == "/custom/logs"
        assert config.plugin_dir == "/custom/plugins"
        assert config.cert_dir == "/custom/certs"
        assert config.temp_dir == "/custom/temp"

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

    def test_paths_config_merge(self):
        """Test PathsConfig merging."""
        base_config = PathsConfig()
        override = {"output_dir": "/merged/output", "log_dir": "/merged/logs"}

        merged = base_config.merge(override)
        assert merged.output_dir == "/merged/output"
        assert merged.log_dir == "/merged/logs"
        assert merged.plugin_dir == "panther/plugins"  # Unchanged


class TestDockerConfig:
    """Comprehensive tests for DockerConfig."""

    def test_docker_config_defaults(self):
        """Test DockerConfig with default values."""
        config = DockerConfig()

        assert config.force_build_docker_image is True
        assert config.log_docker_image_build is True
        assert config.registry is None
        assert config.network_mode == "bridge"
        assert isinstance(config.user_mapping, DockerUserMappingConfig)
        assert isinstance(config.build_args, dict)

    def test_docker_config_custom_values(self):
        """Test DockerConfig with custom values."""
        user_mapping = DockerUserMappingConfig(run_as_host_user=True, custom_uid=1000)
        config = DockerConfig(
            force_build_docker_image=False,
            log_docker_image_build=False,
            user_mapping=user_mapping,
            registry="my-registry.com",
            network_mode="host",
        )

        assert config.force_build_docker_image is False
        assert config.log_docker_image_build is False
        assert config.registry == "my-registry.com"
        assert config.network_mode == "host"
        assert config.user_mapping.run_as_host_user is True

    def test_docker_config_serialization(self):
        """Test DockerConfig serialization."""
        config = DockerConfig(force_build_docker_image=False, registry="test-registry")

        # Test dict conversion
        config_dict = config.to_dict()
        assert config_dict["force_build_docker_image"] is False
        assert config_dict["registry"] == "test-registry"


class TestDockerUserMappingConfig:
    """Test DockerUserMappingConfig functionality."""

    def test_docker_user_mapping_defaults(self):
        """Test DockerUserMappingConfig with defaults."""
        config = DockerUserMappingConfig()

        assert config.run_as_host_user is False
        assert config.custom_uid is None
        assert config.custom_gid is None
        assert config.user_name == "panther"
        assert config.fallback_to_root is True

    def test_docker_user_mapping_custom(self):
        """Test DockerUserMappingConfig with custom values."""
        config = DockerUserMappingConfig(
            run_as_host_user=True,
            custom_uid=1000,
            custom_gid=1000,
            user_name="custom_user",
            fallback_to_root=False,
        )

        assert config.run_as_host_user is True
        assert config.custom_uid == 1000
        assert config.custom_gid == 1000
        assert config.user_name == "custom_user"
        assert config.fallback_to_root is False


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

    def test_feature_log_levels_to_dict_filters_none(self):
        """Test that to_dict filters out None values."""
        config = FeatureLogLevelsConfig(docker_build="INFO")
        config_dict = config.to_dict()

        assert config_dict["docker_build"] == "INFO"
        assert "service_start" not in config_dict  # None values filtered out


class TestProgressConfig:
    """Test ProgressConfig functionality."""

    def test_progress_config_defaults(self):
        """Test ProgressConfig with defaults."""
        config = ProgressConfig()

        assert config.enable_progress_bar is True
        assert config.redirect_logging is True
        assert config.show_spinner is True
        assert config.show_test_status is True
        assert config.use_emojis is True
        assert config.update_interval == 0.1

    def test_progress_config_custom(self):
        """Test ProgressConfig with custom values."""
        config = ProgressConfig(
            enable_progress_bar=False,
            redirect_logging=False,
            show_spinner=False,
            update_interval=0.5,
        )

        assert config.enable_progress_bar is False
        assert config.redirect_logging is False
        assert config.show_spinner is False
        assert config.update_interval == 0.5


class TestFastFailConfig:
    """Test FastFailConfig functionality."""

    def test_fast_fail_config_defaults(self):
        """Test FastFailConfig with defaults."""
        config = FastFailConfig()

        assert config.enabled is True
        assert config.test_level is False
        assert config.docker_build_failures is True
        assert config.service_start_failures is True
        assert config.ivy_compilation_failures is False
        assert config.timeout_cascade_threshold == 3
        assert config.critical_only is False

    def test_fast_fail_config_custom(self):
        """Test FastFailConfig with custom values."""
        config = FastFailConfig(
            enabled=False,
            test_level=True,
            docker_build_failures=False,
            timeout_cascade_threshold=5,
            critical_only=True,
        )

        assert config.enabled is False
        assert config.test_level is True
        assert config.docker_build_failures is False
        assert config.timeout_cascade_threshold == 5
        assert config.critical_only is True


class TestMetricsConfig:
    """Test MetricsConfig functionality."""

    def test_metrics_config_defaults(self):
        """Test MetricsConfig with defaults."""
        config = MetricsConfig()

        assert config.enabled is True
        assert config.collect_system_metrics is True
        assert config.publish_interval == 30
        assert config.export_format == "json"
        assert config.retention_days == 30

    def test_metrics_config_custom(self):
        """Test MetricsConfig with custom values."""
        config = MetricsConfig(
            enabled=False,
            collect_system_metrics=False,
            publish_interval=60,
            export_format="yaml",
            retention_days=7,
        )

        assert config.enabled is False
        assert config.collect_system_metrics is False
        assert config.publish_interval == 60
        assert config.export_format == "yaml"
        assert config.retention_days == 7


class TestGlobalConfig:
    """Comprehensive tests for GlobalConfig integration."""

    def test_global_config_defaults(self):
        """Test GlobalConfig with all default values."""
        config = GlobalConfig()

        # Check version and sub-configs exist with defaults
        assert config.version == "1.0"
        assert isinstance(config.logging, LoggingConfig)
        assert config.logging.level == LoggingLevel.INFO

        assert isinstance(config.paths, PathsConfig)
        assert config.paths.output_dir == "outputs"

        assert isinstance(config.docker, DockerConfig)
        assert config.docker.force_build_docker_image is True

    def test_global_config_custom_sub_configs(self):
        """Test GlobalConfig with custom sub-configurations."""
        logging_config = LoggingConfig(level=LoggingLevel.ERROR, format="custom")
        paths_config = PathsConfig(output_dir="/custom", log_dir="/custom/logs")
        docker_config = DockerConfig(force_build_docker_image=False)

        config = GlobalConfig(
            version="2.0",
            logging=logging_config,
            paths=paths_config,
            docker=docker_config,
        )

        assert config.version == "2.0"
        assert config.logging.level == LoggingLevel.ERROR
        assert config.logging.format == "custom"
        assert config.paths.output_dir == "/custom"
        assert config.docker.force_build_docker_image is False

    def test_global_config_dict_creation(self):
        """Test GlobalConfig creation from dictionary."""
        config_dict = {
            "version": "1.5",
            "logging": {"level": "INFO", "format": "%(levelname)s: %(message)s"},
            "paths": {"output_dir": "/dict/output", "log_dir": "/dict/logs"},
            "docker": {
                "force_build_docker_image": False,
                "registry": "my-registry.com",
            },
        }

        config = GlobalConfig(**config_dict)

        assert config.version == "1.5"
        assert config.logging.level == LoggingLevel.INFO
        assert config.logging.format == "%(levelname)s: %(message)s"
        assert config.paths.output_dir == "/dict/output"
        assert config.paths.log_dir == "/dict/logs"
        assert config.docker.force_build_docker_image is False
        assert config.docker.registry == "my-registry.com"

    def test_global_config_merge_complex(self):
        """Test GlobalConfig complex merging scenarios."""
        base_config = GlobalConfig()

        # Complex override with nested changes
        override = {
            "version": "2.0",
            "logging": {"level": "ERROR"},
            "paths": {"output_dir": "/merged/output", "plugin_dir": "/merged/plugins"},
            "docker": {"force_build_docker_image": False},
        }

        merged = base_config.merge(override)

        # Check merged values
        assert merged.version == "2.0"
        assert merged.logging.level == LoggingLevel.ERROR
        assert merged.paths.output_dir == "/merged/output"
        assert merged.paths.plugin_dir == "/merged/plugins"
        assert merged.docker.force_build_docker_image is False

        # Check unchanged values
        assert (
            merged.logging.format
            == "%(asctime)s [%(levelname)s] - %(module)s - %(message)s"
        )
        assert merged.paths.log_dir == "${paths.output_dir}/logs"
        assert merged.docker.log_docker_image_build is True

    def test_global_config_omega_conversion(self):
        """Test GlobalConfig OmegaConf conversion."""
        config = GlobalConfig(
            version="1.5",
            logging=LoggingConfig(level=LoggingLevel.WARNING),
            paths=PathsConfig(output_dir="/omega/test"),
        )

        # Convert to OmegaConf
        omega = config.to_omega()
        assert omega.version == "1.5"
        assert omega.logging.level == "WARNING"
        assert omega.paths.output_dir == "/omega/test"

        # Convert back
        restored = GlobalConfig.from_omega(omega)
        assert restored.version == "1.5"
        assert restored.logging.level == LoggingLevel.WARNING
        assert restored.paths.output_dir == "/omega/test"

    def test_global_config_serialization_roundtrip(self):
        """Test GlobalConfig serialization round-trip."""
        original = GlobalConfig(
            version="1.8",
            logging=LoggingConfig(level=LoggingLevel.INFO, format="test format"),
            paths=PathsConfig(output_dir="/roundtrip", log_dir="/roundtrip/logs"),
            docker=DockerConfig(force_build_docker_image=False),
        )

        # Round-trip through YAML
        yaml_str = original.to_yaml()
        yaml_dict = yaml.safe_load(yaml_str)
        from_yaml = GlobalConfig(**yaml_dict)

        assert from_yaml.version == original.version
        assert from_yaml.logging.level == original.logging.level
        assert from_yaml.logging.format == original.logging.format
        assert from_yaml.paths.output_dir == original.paths.output_dir
        assert (
            from_yaml.docker.force_build_docker_image
            == original.docker.force_build_docker_image
        )

    def test_global_config_file_operations(self):
        """Test GlobalConfig file save/load operations."""
        original = GlobalConfig(
            version="1.9",
            logging=LoggingConfig(level=LoggingLevel.WARNING),
            paths=PathsConfig(output_dir="/file/test"),
        )

        # Test YAML file operations
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            try:
                original.save_to_file(f.name)
                loaded = GlobalConfig.load_from_file(f.name)

                assert loaded.version == "1.9"
                assert loaded.logging.level == LoggingLevel.WARNING
                assert loaded.paths.output_dir == "/file/test"

            finally:
                os.unlink(f.name)


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
        test_docker.test_docker_config_custom_values()
        test_docker.test_docker_config_serialization()
        print("✓ DockerConfig tests passed")

        # Test additional configs
        test_progress = TestProgressConfig()
        test_progress.test_progress_config_defaults()
        test_progress.test_progress_config_custom()
        print("✓ ProgressConfig tests passed")

        test_fast_fail = TestFastFailConfig()
        test_fast_fail.test_fast_fail_config_defaults()
        test_fast_fail.test_fast_fail_config_custom()
        print("✓ FastFailConfig tests passed")

        test_metrics = TestMetricsConfig()
        test_metrics.test_metrics_config_defaults()
        test_metrics.test_metrics_config_custom()
        print("✓ MetricsConfig tests passed")

        # Test GlobalConfig integration
        test_global = TestGlobalConfig()
        test_global.test_global_config_defaults()
        test_global.test_global_config_merge_complex()
        test_global.test_global_config_omega_conversion()
        test_global.test_global_config_file_operations()
        print("✓ GlobalConfig integration tests passed")

        print("\n✅ All comprehensive GlobalConfig tests passed!")

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
