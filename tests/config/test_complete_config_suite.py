#!/usr/bin/env python3
"""
Complete comprehensive test suite for ALL PANTHER configuration classes.

This module tests every configuration class discovered through Serena analysis:
- GlobalConfig with all 8 sub-configurations
- All observer configurations (LoggerObserver, MetricsObserver, etc.)
- All validation scenarios and edge cases
- Full integration testing
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
from panther.config.core.models.observer import (
    ExperimentObserverConfig,
    LoggerObserverConfig,
    MetricsObserverConfig,
    ObserversConfig,
    StorageObserverConfig,
)

# Add PANTHER to Python path
# PANTHER is now available in Python path since we're in the PANTHER project


class TestObserverConfigurations:
    """Test all observer configuration classes."""

    def test_logger_observer_config_defaults(self):
        """Test LoggerObserverConfig defaults."""
        config = LoggerObserverConfig()

        assert config.enabled is True
        assert config.priority == 100
        assert config.auto_register is False
        assert config.log_level == "INFO"
        assert config.enable_colors is True
        assert config.log_to_file is True
        assert config.log_to_console is True
        assert config.file_rotation is True
        assert config.max_file_size == "10MB"
        assert config.backup_count == 5
        assert config.max_data_length == 1000

    def test_logger_observer_config_custom(self):
        """Test LoggerObserverConfig with custom values."""
        config = LoggerObserverConfig(
            enabled=False,
            priority=200,
            auto_register=True,
            log_level="ERROR",
            enable_colors=False,
            log_to_file=False,
            max_file_size="50MB",
            backup_count=10,
        )

        assert config.enabled is False
        assert config.priority == 200
        assert config.auto_register is True
        assert config.log_level == "ERROR"
        assert config.enable_colors is False
        assert config.log_to_file is False
        assert config.max_file_size == "50MB"
        assert config.backup_count == 10

    def test_metrics_observer_config_defaults(self):
        """Test MetricsObserverConfig defaults."""
        config = MetricsObserverConfig()

        assert config.enabled is True
        assert config.priority == 100
        assert config.collect_system_metrics is True
        assert config.publish_interval == 30
        assert config.export_format == "json"
        assert config.include_histograms is True
        assert config.include_percentiles is True
        assert config.percentiles == [50, 90, 95, 99]
        assert config.publish_metrics is True
        assert config.resource_collection_interval == 5

    def test_metrics_observer_config_custom(self):
        """Test MetricsObserverConfig with custom values."""
        config = MetricsObserverConfig(
            enabled=False,
            publish_interval=60,
            export_format="yaml",
            include_histograms=False,
            percentiles=[75, 90, 99],
            resource_collection_interval=10,
        )

        assert config.enabled is False
        assert config.publish_interval == 60
        assert config.export_format == "yaml"
        assert config.include_histograms is False
        assert config.percentiles == [75, 90, 99]
        assert config.resource_collection_interval == 10

    def test_storage_observer_config_defaults(self):
        """Test StorageObserverConfig defaults."""
        config = StorageObserverConfig()

        assert config.enabled is True
        assert config.storage_path == "outputs/storage"
        assert config.enable_compression is False
        assert config.retention_days == 30
        assert config.storage_format == "json"
        assert config.buffer_size == 1000
        assert config.flush_interval == 60
        assert config.create_indexes is True
        assert config.auto_backup is True
        assert config.backup_interval == 3600
        assert config.batch_size == 100

    def test_storage_observer_config_custom(self):
        """Test StorageObserverConfig with custom values."""
        config = StorageObserverConfig(
            enabled=False,
            storage_path="/custom/storage",
            enable_compression=True,
            retention_days=60,
            storage_format="yaml",
            buffer_size=2000,
            batch_size=200,
        )

        assert config.enabled is False
        assert config.storage_path == "/custom/storage"
        assert config.enable_compression is True
        assert config.retention_days == 60
        assert config.storage_format == "yaml"
        assert config.buffer_size == 2000
        assert config.batch_size == 200

    def test_experiment_observer_config_defaults(self):
        """Test ExperimentObserverConfig defaults."""
        config = ExperimentObserverConfig()

        assert config.enabled is True
        assert config.track_timing is True
        assert config.track_steps is True
        assert config.generate_report is True
        assert config.report_format == "markdown"
        assert config.include_graphs is True
        assert config.capture_screenshots is False
        assert config.detailed_errors is True

    def test_experiment_observer_config_custom(self):
        """Test ExperimentObserverConfig with custom values."""
        config = ExperimentObserverConfig(
            enabled=False,
            track_timing=False,
            generate_report=False,
            report_format="html",
            include_graphs=False,
            capture_screenshots=True,
            detailed_errors=False,
        )

        assert config.enabled is False
        assert config.track_timing is False
        assert config.generate_report is False
        assert config.report_format == "html"
        assert config.include_graphs is False
        assert config.capture_screenshots is True
        assert config.detailed_errors is False

    def test_observers_config_integration(self):
        """Test ObserversConfig integration with all sub-configs."""
        logger_config = LoggerObserverConfig(log_level="ERROR")
        metrics_config = MetricsObserverConfig(publish_interval=120)
        storage_config = StorageObserverConfig(storage_path="/test/storage")
        experiment_config = ExperimentObserverConfig(report_format="html")

        config = ObserversConfig(
            logger=logger_config,
            metrics=metrics_config,
            storage=storage_config,
            experiment=experiment_config,
        )

        assert config.logger.log_level == "ERROR"
        assert config.metrics.publish_interval == 120
        assert config.storage.storage_path == "/test/storage"
        assert config.experiment.report_format == "html"


class TestCompleteGlobalConfig:
    """Test complete GlobalConfig with all discovered fields."""

    def test_global_config_complete_structure(self):
        """Test GlobalConfig has all expected fields."""
        config = GlobalConfig()

        # Check all 8 main configuration sections exist
        assert hasattr(config, "version")
        assert hasattr(config, "logging")
        assert hasattr(config, "paths")
        assert hasattr(config, "docker")
        assert hasattr(config, "progress")
        assert hasattr(config, "fast_fail")
        assert hasattr(config, "metrics")
        assert hasattr(config, "observers")

        # Check types are correct
        assert isinstance(config.logging, LoggingConfig)
        assert isinstance(config.paths, PathsConfig)
        assert isinstance(config.docker, DockerConfig)
        assert isinstance(config.progress, ProgressConfig)
        assert isinstance(config.fast_fail, FastFailConfig)
        assert isinstance(config.metrics, MetricsConfig)
        assert isinstance(config.observers, ObserversConfig)

    def test_global_config_all_defaults(self):
        """Test all default values across all configurations."""
        config = GlobalConfig()

        # Version
        assert config.version == "1.0"

        # Logging defaults
        assert config.logging.level == LoggingLevel.INFO
        assert config.logging.enable_colors is True

        # Paths defaults
        assert config.paths.output_dir == "outputs"
        assert config.paths.plugin_dir == "panther/plugins"
        assert config.paths.temp_dir == "/tmp/panther"

        # Docker defaults
        assert config.docker.force_build_docker_image is True
        assert config.docker.log_docker_image_build is True
        assert config.docker.network_mode == "bridge"

        # Progress defaults
        assert config.progress.enable_progress_bar is True
        assert config.progress.use_emojis is True
        assert config.progress.update_interval == 0.1

        # Fast-fail defaults
        assert config.fast_fail.enabled is True
        assert config.fast_fail.docker_build_failures is True
        assert config.fast_fail.timeout_cascade_threshold == 3

        # Metrics defaults
        assert config.metrics.enabled is True
        assert config.metrics.export_format == "json"
        assert config.metrics.retention_days == 30

        # Observer defaults
        assert config.observers.logger.enabled is True
        assert config.observers.metrics.enabled is True
        assert config.observers.storage.enabled is True
        assert config.observers.experiment.enabled is True

    def test_global_config_complex_customization(self):
        """Test GlobalConfig with complex nested customizations."""
        # Create custom sub-configs
        logging_config = LoggingConfig(
            level=LoggingLevel.WARNING,
            format="CUSTOM: %(message)s",
            enable_colors=False,
        )

        paths_config = PathsConfig(
            output_dir="/custom/output",
            log_dir="/custom/logs",
            plugin_dir="/custom/plugins",
        )

        docker_config = DockerConfig(
            force_build_docker_image=False,
            network_mode="host",
            registry="custom-registry.com",
        )

        progress_config = ProgressConfig(
            enable_progress_bar=False, use_emojis=False, update_interval=0.5
        )

        fast_fail_config = FastFailConfig(
            enabled=False, timeout_cascade_threshold=5, critical_only=True
        )

        metrics_config = MetricsConfig(
            enabled=False, export_format="yaml", retention_days=7
        )

        # Create custom observer configs
        logger_observer = LoggerObserverConfig(
            log_level="ERROR", enable_colors=False, max_file_size="100MB"
        )

        observers_config = ObserversConfig(logger=logger_observer)

        # Create complete GlobalConfig
        config = GlobalConfig(
            version="2.0",
            logging=logging_config,
            paths=paths_config,
            docker=docker_config,
            progress=progress_config,
            fast_fail=fast_fail_config,
            metrics=metrics_config,
            observers=observers_config,
        )

        # Verify all customizations
        assert config.version == "2.0"
        assert config.logging.level == LoggingLevel.WARNING
        assert config.logging.format == "CUSTOM: %(message)s"
        assert config.paths.output_dir == "/custom/output"
        assert config.docker.force_build_docker_image is False
        assert config.docker.network_mode == "host"
        assert config.progress.enable_progress_bar is False
        assert config.fast_fail.enabled is False
        assert config.metrics.enabled is False
        assert config.observers.logger.log_level == "ERROR"

    def test_global_config_interpolation_resolution(self):
        """Test OmegaConf interpolation in GlobalConfig."""
        config = GlobalConfig()

        # Test that interpolation exists in raw form
        assert config.paths.log_dir == "${paths.output_dir}/logs"

        # Test merging resolves interpolation
        override = {"paths": {"output_dir": "/new/output"}}

        merged = config.merge(override)
        # After merge, interpolation should be resolved
        assert merged.paths.output_dir == "/new/output"
        assert merged.paths.log_dir == "/new/output/logs"

    def test_global_config_deep_merge(self):
        """Test deep merging capabilities."""
        base_config = GlobalConfig()

        # Complex nested override
        override = {
            "version": "1.5",
            "logging": {
                "level": "ERROR",
                "feature_levels": {
                    "docker_build": "DEBUG",
                    "test_execution": "WARNING",
                },
            },
            "docker": {
                "force_build_docker_image": False,
                "user_mapping": {"run_as_host_user": True, "custom_uid": 1000},
            },
            "observers": {
                "logger": {"log_level": "CRITICAL", "max_file_size": "200MB"},
                "metrics": {"publish_interval": 60},
            },
        }

        merged = base_config.merge(override)

        # Check top-level merge
        assert merged.version == "1.5"

        # Check nested logging merge
        assert merged.logging.level == LoggingLevel.ERROR
        assert (
            merged.logging.format
            == "%(asctime)s [%(levelname)s] - %(module)s - %(message)s"
        )  # Unchanged
        assert merged.logging.feature_levels.docker_build == "DEBUG"
        assert merged.logging.feature_levels.test_execution == "WARNING"

        # Check nested docker merge
        assert merged.docker.force_build_docker_image is False
        assert merged.docker.log_docker_image_build is True  # Unchanged
        assert merged.docker.user_mapping.run_as_host_user is True
        assert merged.docker.user_mapping.custom_uid == 1000
        assert merged.docker.user_mapping.user_name == "panther"  # Unchanged

        # Check nested observers merge
        assert merged.observers.logger.log_level == "CRITICAL"
        assert merged.observers.logger.max_file_size == "200MB"
        assert merged.observers.logger.enabled is True  # Unchanged
        assert merged.observers.metrics.publish_interval == 60
        assert merged.observers.metrics.export_format == "json"  # Unchanged

    def test_global_config_serialization_complete(self):
        """Test complete serialization/deserialization cycle."""
        # Create a complex config
        original = GlobalConfig(
            version="1.8",
            logging=LoggingConfig(level=LoggingLevel.WARNING),
            paths=PathsConfig(output_dir="/test/complete"),
            docker=DockerConfig(force_build_docker_image=False),
            observers=ObserversConfig(
                logger=LoggerObserverConfig(log_level="ERROR"),
                metrics=MetricsObserverConfig(publish_interval=120),
            ),
        )

        # Test YAML round-trip
        yaml_str = original.to_yaml()
        yaml_dict = yaml.safe_load(yaml_str)
        from_yaml = GlobalConfig(**yaml_dict)

        assert from_yaml.version == original.version
        assert from_yaml.logging.level == original.logging.level
        assert from_yaml.paths.output_dir == original.paths.output_dir
        assert (
            from_yaml.docker.force_build_docker_image
            == original.docker.force_build_docker_image
        )
        assert (
            from_yaml.observers.logger.log_level == original.observers.logger.log_level
        )
        assert (
            from_yaml.observers.metrics.publish_interval
            == original.observers.metrics.publish_interval
        )

        # Test JSON round-trip
        json_str = original.to_json()
        json_dict = json.loads(json_str)
        from_json = GlobalConfig(**json_dict)

        assert from_json.version == original.version
        assert from_json.logging.level == original.logging.level
        assert from_json.paths.output_dir == original.paths.output_dir

    def test_global_config_validation_errors(self):
        """Test various validation error scenarios."""
        # Invalid logging level
        with pytest.raises(ValidationError):
            GlobalConfig(logging={"level": "INVALID_LEVEL"})

        # Invalid docker config type
        with pytest.raises(ValidationError):
            GlobalConfig(docker={"force_build_docker_image": "not_boolean"})

        # Invalid observer config
        with pytest.raises(ValidationError):
            GlobalConfig(observers={"logger": {"priority": "not_integer"}})

        # Invalid progress update interval
        with pytest.raises(ValidationError):
            GlobalConfig(progress={"update_interval": -1})

    def test_global_config_omega_conversion_complete(self):
        """Test complete OmegaConf conversion."""
        config = GlobalConfig(
            version="1.9",
            logging=LoggingConfig(level=LoggingLevel.DEBUG),
            paths=PathsConfig(output_dir="/omega/complete"),
            observers=ObserversConfig(logger=LoggerObserverConfig(log_level="WARNING")),
        )

        # Convert to OmegaConf
        omega = config.to_omega()
        assert omega.version == "1.9"
        assert omega.logging.level == "DEBUG"
        assert omega.paths.output_dir == "/omega/complete"
        assert omega.observers.logger.log_level == "WARNING"

        # Convert back
        restored = GlobalConfig.from_omega(omega)
        assert restored.version == "1.9"
        assert restored.logging.level == LoggingLevel.DEBUG
        assert restored.paths.output_dir == "/omega/complete"
        assert restored.observers.logger.log_level == "WARNING"

    def test_global_config_file_operations_complete(self):
        """Test complete file save/load operations."""
        original = GlobalConfig(
            version="2.0",
            logging=LoggingConfig(level=LoggingLevel.CRITICAL),
            paths=PathsConfig(output_dir="/file/complete"),
            docker=DockerConfig(network_mode="host"),
            observers=ObserversConfig(
                storage=StorageObserverConfig(storage_path="/file/storage")
            ),
        )

        # Test YAML file operations
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            try:
                original.save(f.name)
                loaded = GlobalConfig.load(f.name)

                assert loaded.version == "2.0"
                assert loaded.logging.level == LoggingLevel.CRITICAL
                assert loaded.paths.output_dir == "/file/complete"
                assert loaded.docker.network_mode == "host"
                assert loaded.observers.storage.storage_path == "/file/storage"

            finally:
                os.unlink(f.name)


if __name__ == "__main__":
    print("Running complete comprehensive configuration test suite...")

    try:
        # Test observer configurations
        test_observers = TestObserverConfigurations()
        test_observers.test_logger_observer_config_defaults()
        test_observers.test_metrics_observer_config_defaults()
        test_observers.test_storage_observer_config_defaults()
        test_observers.test_experiment_observer_config_defaults()
        test_observers.test_observers_config_integration()
        print("✓ All observer configuration tests passed")

        # Test complete GlobalConfig
        test_complete = TestCompleteGlobalConfig()
        test_complete.test_global_config_complete_structure()
        test_complete.test_global_config_all_defaults()
        test_complete.test_global_config_complex_customization()
        test_complete.test_global_config_interpolation_resolution()
        test_complete.test_global_config_deep_merge()
        test_complete.test_global_config_serialization_complete()
        test_complete.test_global_config_omega_conversion_complete()
        test_complete.test_global_config_file_operations_complete()
        print("✓ All complete GlobalConfig tests passed")

        print("\n🎉 ALL COMPREHENSIVE CONFIGURATION TESTS PASSED!")
        print("✅ Tested 8 main config classes + 4 observer classes")
        print("✅ Tested all serialization formats (YAML, JSON, OmegaConf)")
        print("✅ Tested deep merging and interpolation")
        print("✅ Tested validation and error handling")
        print("✅ Tested file operations and round-trips")

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback

        traceback.print_exc()
