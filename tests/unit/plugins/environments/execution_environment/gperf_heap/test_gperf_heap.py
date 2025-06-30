"""
Comprehensive unit tests for GperfHeapEnvironment.

Tests memory heap profiling functionality, configuration handling, and command generation.
"""
from pathlib import Path
from typing import List
from unittest.mock import MagicMock, Mock, patch

import pytest

from panther.config.core.models.global_config import GlobalConfig
from panther.core.observer.management.event_manager import EventManager
from panther.plugins.environments.config_schema import EnvironmentConfig
from panther.plugins.environments.execution_environment.gperf_heap.config_schema import (
    GperfHeapConfig,
)
from panther.plugins.environments.execution_environment.gperf_heap.gperf_heap import (
    GperfHeapEnvironment,
)
from panther.plugins.services.services_interface import IServiceManager


class TestGperfHeapEnvironmentInitialization:
    """Test suite for GperfHeapEnvironment initialization."""

    @patch(
        "panther.plugins.environments.execution_environment.base_execution_environment.BaseExecutionEnvironment.standardized_environment_initialization"
    )
    def test_basic_initialization(self, mock_std_init, temp_output_dir, event_manager):
        """Test basic GperfHeapEnvironment initialization."""
        config = GperfHeapConfig()

        env = GperfHeapEnvironment(
            env_config_to_test=config,
            output_dir=temp_output_dir,
            env_type="execution",
            env_sub_type="gperf_heap",
            event_manager=event_manager,
        )

        assert env.env_config_to_test == config
        assert env.output_dir == temp_output_dir
        assert env.env_type == "execution"
        assert env.env_sub_type == "gperf_heap"
        assert env.event_manager == event_manager
        assert env._plugin_config is None  # Should be lazy-loaded

    @patch(
        "panther.plugins.environments.execution_environment.base_execution_environment.BaseExecutionEnvironment.standardized_environment_initialization"
    )
    def test_plugin_registration_decorator(
        self, mock_std_init, temp_output_dir, event_manager
    ):
        """Test that plugin is properly decorated with registration info."""
        # Check if the plugin decorator was applied
        assert hasattr(GperfHeapEnvironment, "_plugin_info")

        plugin_info = GperfHeapEnvironment._plugin_info
        assert plugin_info["name"] == "gperf_heap"
        assert plugin_info["version"] == "1.0.0"
        assert (
            plugin_info["description"]
            == "Memory heap profiling execution environment using Google Performance Tools"
        )
        assert "heap_profiling" in plugin_info["capabilities"]
        assert "memory_analysis" in plugin_info["capabilities"]
        assert "leak_detection" in plugin_info["capabilities"]
        assert "gperf" in plugin_info["external_dependencies"]

    @patch(
        "panther.plugins.environments.execution_environment.base_execution_environment.BaseExecutionEnvironment.standardized_environment_initialization"
    )
    def test_inheritance_chain(self, mock_std_init, temp_output_dir, event_manager):
        """Test that GperfHeapEnvironment has correct inheritance."""
        from panther.plugins.environments.execution_environment.base_execution_environment import (
            BaseExecutionEnvironment,
        )

        config = GperfHeapConfig()
        env = GperfHeapEnvironment(
            env_config_to_test=config,
            output_dir=temp_output_dir,
            env_type="execution",
            env_sub_type="gperf_heap",
            event_manager=event_manager,
        )

        assert isinstance(env, BaseExecutionEnvironment)
        assert isinstance(env, GperfHeapEnvironment)


class TestGperfHeapConfigurationHandling:
    """Test suite for configuration handling with dual approach."""

    @patch(
        "panther.plugins.environments.execution_environment.base_execution_environment.BaseExecutionEnvironment.standardized_environment_initialization"
    )
    def test_get_plugin_config_caching(
        self, mock_std_init, temp_output_dir, event_manager
    ):
        """Test that plugin config is cached correctly."""
        config = GperfHeapConfig(heap_profile_allocation_interval=1024)

        with patch.object(
            config, "get_plugin_config", return_value=config
        ) as mock_get_config:
            env = GperfHeapEnvironment(
                env_config_to_test=config,
                output_dir=temp_output_dir,
                env_type="execution",
                env_sub_type="gperf_heap",
                event_manager=event_manager,
            )

            # First call should invoke get_plugin_config
            plugin_config1 = env._get_plugin_config()
            mock_get_config.assert_called_once_with(GperfHeapConfig)

            # Second call should use cached value
            plugin_config2 = env._get_plugin_config()
            mock_get_config.assert_called_once()  # Still only one call

            assert plugin_config1 is plugin_config2
            assert plugin_config1.heap_profile_allocation_interval == 1024

    @patch(
        "panther.plugins.environments.execution_environment.base_execution_environment.BaseExecutionEnvironment.standardized_environment_initialization"
    )
    def test_get_plugin_config_exception_fallback(
        self, mock_std_init, temp_output_dir, event_manager
    ):
        """Test fallback to default config when get_plugin_config fails."""
        config = GperfHeapConfig()

        with patch.object(
            config, "get_plugin_config", side_effect=Exception("Config error")
        ):
            env = GperfHeapEnvironment(
                env_config_to_test=config,
                output_dir=temp_output_dir,
                env_type="execution",
                env_sub_type="gperf_heap",
                event_manager=event_manager,
            )

            with patch.object(env, "logger") as mock_logger:
                plugin_config = env._get_plugin_config()

                # Should return default config
                assert isinstance(plugin_config, GperfHeapConfig)
                assert (
                    plugin_config.heap_profile_allocation_interval is None
                )  # Default value

                # Should log debug message
                mock_logger.debug.assert_called_once()
                assert "Could not get plugin config, using defaults" in str(
                    mock_logger.debug.call_args
                )


class TestGperfHeapEnvironmentVariableGeneration:
    """Test suite for environment variable generation."""

    @patch(
        "panther.plugins.environments.execution_environment.base_execution_environment.BaseExecutionEnvironment.standardized_environment_initialization"
    )
    def test_build_heap_environment_vars_basic(
        self, mock_std_init, temp_output_dir, event_manager
    ):
        """Test basic environment variable generation."""
        config = GperfHeapConfig()
        env = GperfHeapEnvironment(
            env_config_to_test=config,
            output_dir=temp_output_dir,
            env_type="execution",
            env_sub_type="gperf_heap",
            event_manager=event_manager,
        )

        env_vars = env._build_heap_environment_vars("/tmp/heap.prof")

        # Check required environment variables
        assert "HEAPPROFILE" in env_vars
        assert env_vars["HEAPPROFILE"] == "/tmp/heap.prof"
        assert "LD_PRELOAD" in env_vars
        assert "libtcmalloc_and_profiler.so.4" in env_vars["LD_PRELOAD"]

    @patch(
        "panther.plugins.environments.execution_environment.base_execution_environment.BaseExecutionEnvironment.standardized_environment_initialization"
    )
    def test_build_heap_environment_vars_with_sampling_frequency(
        self, mock_std_init, temp_output_dir, event_manager
    ):
        """Test environment variable generation with sampling frequency."""
        config = GperfHeapConfig()
        config.plugin_config = {"sampling_frequency": 2048}

        env = GperfHeapEnvironment(
            env_config_to_test=config,
            output_dir=temp_output_dir,
            env_type="execution",
            env_sub_type="gperf_heap",
            event_manager=event_manager,
        )

        env_vars = env._build_heap_environment_vars("/tmp/heap.prof")

        assert "HEAP_PROFILE_ALLOCATION_INTERVAL" in env_vars
        assert env_vars["HEAP_PROFILE_ALLOCATION_INTERVAL"] == "2048"

    @patch(
        "panther.plugins.environments.execution_environment.base_execution_environment.BaseExecutionEnvironment.standardized_environment_initialization"
    )
    def test_build_heap_environment_vars_with_heap_check(
        self, mock_std_init, temp_output_dir, event_manager
    ):
        """Test environment variable generation with heap check level."""
        config = GperfHeapConfig()
        config.plugin_config = {"heap_check_level": "strict"}

        env = GperfHeapEnvironment(
            env_config_to_test=config,
            output_dir=temp_output_dir,
            env_type="execution",
            env_sub_type="gperf_heap",
            event_manager=event_manager,
        )

        env_vars = env._build_heap_environment_vars("/tmp/heap.prof")

        assert "HEAPCHECK" in env_vars
        assert env_vars["HEAPCHECK"] == "strict"

    @patch(
        "panther.plugins.environments.execution_environment.base_execution_environment.BaseExecutionEnvironment.standardized_environment_initialization"
    )
    def test_build_heap_environment_vars_with_profile_only_peak(
        self, mock_std_init, temp_output_dir, event_manager
    ):
        """Test environment variable generation with profile only peak option."""
        config = GperfHeapConfig()
        config.plugin_config = {"profile_only_peak": True}

        env = GperfHeapEnvironment(
            env_config_to_test=config,
            output_dir=temp_output_dir,
            env_type="execution",
            env_sub_type="gperf_heap",
            event_manager=event_manager,
        )

        env_vars = env._build_heap_environment_vars("/tmp/heap.prof")

        assert "HEAP_PROFILE_ONLY_PEAK" in env_vars
        assert env_vars["HEAP_PROFILE_ONLY_PEAK"] == "1"

    @patch(
        "panther.plugins.environments.execution_environment.base_execution_environment.BaseExecutionEnvironment.standardized_environment_initialization"
    )
    def test_build_heap_environment_vars_typed_config_fallback(
        self, mock_std_init, temp_output_dir, event_manager
    ):
        """Test environment variable generation with typed config fallback."""
        # Create typed config with specific values
        config = GperfHeapConfig(
            heap_profile_allocation_interval=4096,
            heap_check_type="normal",
            profile_only_mmap=True,
        )

        env = GperfHeapEnvironment(
            env_config_to_test=config,
            output_dir=temp_output_dir,
            env_type="execution",
            env_sub_type="gperf_heap",
            event_manager=event_manager,
        )

        # Mock the plugin config to test fallback mechanism
        with patch.object(env, "_get_plugin_config") as mock_get_config:
            typed_config = GperfHeapConfig()
            typed_config.sampling_frequency = 4096
            typed_config.heap_check_level = "normal"
            typed_config.profile_only_peak = True
            mock_get_config.return_value = typed_config

            env_vars = env._build_heap_environment_vars("/tmp/heap.prof")

            # Should use values from typed config since no plugin_config dict
            assert "HEAP_PROFILE_ALLOCATION_INTERVAL" in env_vars
            assert env_vars["HEAP_PROFILE_ALLOCATION_INTERVAL"] == "4096"
            assert "HEAPCHECK" in env_vars
            assert env_vars["HEAPCHECK"] == "normal"
            assert "HEAP_PROFILE_ONLY_PEAK" in env_vars
            assert env_vars["HEAP_PROFILE_ONLY_PEAK"] == "1"


class TestGperfHeapPostProcessingCommand:
    """Test suite for post-processing command generation."""

    @patch(
        "panther.plugins.environments.execution_environment.base_execution_environment.BaseExecutionEnvironment.standardized_environment_initialization"
    )
    def test_build_post_processing_command_basic(
        self, mock_std_init, temp_output_dir, event_manager
    ):
        """Test basic post-processing command generation."""
        config = GperfHeapConfig()
        env = GperfHeapEnvironment(
            env_config_to_test=config,
            output_dir=temp_output_dir,
            env_type="execution",
            env_sub_type="gperf_heap",
            event_manager=event_manager,
        )

        command = env._build_post_processing_command(
            "/tmp/heap.prof", "/tmp/heap_analysis.txt", "test_service"
        )

        # Check command contains expected elements
        assert "GPerf Heap Analysis" in command
        assert "/tmp/heap.prof" in command
        assert "/tmp/heap_analysis.txt" in command
        assert "test_service" in command
        assert "pprof --text --lines" in command
        assert "pprof --tree --lines" in command
        assert "Top Memory Consumers" in command
        assert "Memory Allocation Tree" in command

    @patch(
        "panther.plugins.environments.execution_environment.base_execution_environment.BaseExecutionEnvironment.standardized_environment_initialization"
    )
    def test_build_post_processing_command_custom_pprof(
        self, mock_std_init, temp_output_dir, event_manager
    ):
        """Test post-processing command with custom pprof binary."""
        config = GperfHeapConfig()
        config.plugin_config = {"pprof_binary": "/custom/bin/pprof"}

        env = GperfHeapEnvironment(
            env_config_to_test=config,
            output_dir=temp_output_dir,
            env_type="execution",
            env_sub_type="gperf_heap",
            event_manager=event_manager,
        )

        command = env._build_post_processing_command(
            "/tmp/heap.prof", "/tmp/heap_analysis.txt", "test_service"
        )

        # Should use custom pprof binary
        assert "/custom/bin/pprof --text --lines" in command
        assert "/custom/bin/pprof --tree --lines" in command

    @patch(
        "panther.plugins.environments.execution_environment.base_execution_environment.BaseExecutionEnvironment.standardized_environment_initialization"
    )
    def test_build_post_processing_command_typed_config_fallback(
        self, mock_std_init, temp_output_dir, event_manager
    ):
        """Test post-processing command with typed config fallback for pprof binary."""
        config = GperfHeapConfig()
        env = GperfHeapEnvironment(
            env_config_to_test=config,
            output_dir=temp_output_dir,
            env_type="execution",
            env_sub_type="gperf_heap",
            event_manager=event_manager,
        )

        # Mock typed config with pprof_binary attribute
        with patch.object(env, "_get_plugin_config") as mock_get_config:
            typed_config = Mock()
            typed_config.pprof_binary = "/typed/bin/pprof"
            mock_get_config.return_value = typed_config

            command = env._build_post_processing_command(
                "/tmp/heap.prof", "/tmp/heap_analysis.txt", "test_service"
            )

            # Should use typed config pprof binary
            assert "/typed/bin/pprof --text --lines" in command

    @patch(
        "panther.plugins.environments.execution_environment.base_execution_environment.BaseExecutionEnvironment.standardized_environment_initialization"
    )
    def test_build_post_processing_command_default_pprof(
        self, mock_std_init, temp_output_dir, event_manager
    ):
        """Test post-processing command with default pprof binary."""
        config = GperfHeapConfig()
        env = GperfHeapEnvironment(
            env_config_to_test=config,
            output_dir=temp_output_dir,
            env_type="execution",
            env_sub_type="gperf_heap",
            event_manager=event_manager,
        )

        # Mock typed config without pprof_binary attribute
        with patch.object(env, "_get_plugin_config") as mock_get_config:
            typed_config = Mock()
            del typed_config.pprof_binary  # Remove attribute to test hasattr check
            mock_get_config.return_value = typed_config

            command = env._build_post_processing_command(
                "/tmp/heap.prof", "/tmp/heap_analysis.txt", "test_service"
            )

            # Should use default "pprof"
            assert "pprof --text --lines" in command
            assert "/typed/bin/pprof" not in command


class TestGperfHeapCommandGeneration:
    """Test suite for command generation functionality."""

    @patch(
        "panther.plugins.environments.execution_environment.base_execution_environment.BaseExecutionEnvironment.standardized_environment_initialization"
    )
    def test_to_command_basic(self, mock_std_init, temp_output_dir, event_manager):
        """Test basic command generation."""
        config = GperfHeapConfig()
        env = GperfHeapEnvironment(
            env_config_to_test=config,
            output_dir=temp_output_dir,
            env_type="execution",
            env_sub_type="gperf_heap",
            event_manager=event_manager,
        )

        command = env.to_command(output_file="/tmp/test_heap.prof")

        expected_parts = [
            "env",
            "HEAPPROFILE=/tmp/test_heap.prof",
            "LD_PRELOAD=",
            "libtcmalloc_and_profiler.so.4",
        ]

        for part in expected_parts:
            assert part in command

    @patch(
        "panther.plugins.environments.execution_environment.base_execution_environment.BaseExecutionEnvironment.standardized_environment_initialization"
    )
    def test_to_command_default_output_file(
        self, mock_std_init, temp_output_dir, event_manager
    ):
        """Test command generation with default output file."""
        config = GperfHeapConfig()
        env = GperfHeapEnvironment(
            env_config_to_test=config,
            output_dir=temp_output_dir,
            env_type="execution",
            env_sub_type="gperf_heap",
            event_manager=event_manager,
        )

        command = env.to_command()

        # Should use default output file
        assert "HEAPPROFILE=/tmp/heap_profile" in command

    @patch(
        "panther.plugins.environments.execution_environment.base_execution_environment.BaseExecutionEnvironment.standardized_environment_initialization"
    )
    def test_to_command_with_all_env_vars(
        self, mock_std_init, temp_output_dir, event_manager
    ):
        """Test command generation with all environment variables."""
        config = GperfHeapConfig()
        config.plugin_config = {
            "sampling_frequency": 1024,
            "heap_check_level": "strict",
            "profile_only_peak": True,
        }

        env = GperfHeapEnvironment(
            env_config_to_test=config,
            output_dir=temp_output_dir,
            env_type="execution",
            env_sub_type="gperf_heap",
            event_manager=event_manager,
        )

        command = env.to_command()

        # Should include all configured environment variables
        assert "HEAPPROFILE=" in command
        assert "LD_PRELOAD=" in command
        assert "HEAP_PROFILE_ALLOCATION_INTERVAL=1024" in command
        assert "HEAPCHECK=strict" in command
        assert "HEAP_PROFILE_ONLY_PEAK=1" in command


class TestGperfHeapPluginSpecificSetup:
    """Test suite for plugin-specific environment setup."""

    def create_mock_service(self, gperf_compatible=True, service_name="test_service"):
        """Helper to create mock service."""
        service = Mock(spec=IServiceManager)
        service.service_config_to_test.implementation.gperf_compatible = (
            gperf_compatible
        )
        service.service_name = service_name
        return service

    @patch(
        "panther.plugins.environments.execution_environment.gperf_heap.gperf_heap.create_execution_environment_builder"
    )
    @patch(
        "panther.plugins.environments.execution_environment.base_execution_environment.BaseExecutionEnvironment.standardized_environment_initialization"
    )
    def test_setup_plugin_specific_environment_single_service(
        self, mock_std_init, mock_builder, temp_output_dir, event_manager
    ):
        """Test setup with single gperf-compatible service."""
        config = GperfHeapConfig()
        env = GperfHeapEnvironment(
            env_config_to_test=config,
            output_dir=temp_output_dir,
            env_type="execution",
            env_sub_type="gperf_heap",
            event_manager=event_manager,
        )

        # Setup mock command builder
        mock_cmd_builder = Mock()
        mock_cmd_builder.register_output_file.side_effect = [
            "/tmp/heap.prof",
            "/tmp/heap_analysis.txt",
        ]
        mock_cmd_builder.service_name = "test_service"
        mock_cmd_builder.build_and_apply.return_value = ["command1", "command2"]
        mock_builder.return_value = mock_cmd_builder

        # Create mock service
        service = self.create_mock_service()

        env._setup_plugin_specific_environment([service], "test_timestamp")

        # Verify builder was created correctly
        mock_builder.assert_called_once_with(
            service=service,
            environment_name="gperf_heap",
            timestamp="test_timestamp",
            register_output_callback=env.register_output_file,
            logger=env.logger,
        )

        # Verify output files were registered
        assert mock_cmd_builder.register_output_file.call_count == 2

        # Verify first call for heap profile
        first_call = mock_cmd_builder.register_output_file.call_args_list[0]
        assert first_call[1]["file_type"] == "heap_profile"
        assert first_call[1]["extension"] == "prof"

        # Verify second call for heap analysis
        second_call = mock_cmd_builder.register_output_file.call_args_list[1]
        assert second_call[1]["file_type"] == "heap_analysis"
        assert second_call[1]["extension"] == "txt"

        # Verify wrapper command was added
        mock_cmd_builder.add_wrapper_command.assert_called_once()

        # Verify post-processing was added
        mock_cmd_builder.add_post_processing.assert_called_once()

        # Verify build_and_apply was called
        mock_cmd_builder.build_and_apply.assert_called_once_with(env)

    @patch(
        "panther.plugins.environments.execution_environment.base_execution_environment.BaseExecutionEnvironment.standardized_environment_initialization"
    )
    def test_setup_plugin_specific_environment_incompatible_service(
        self, mock_std_init, temp_output_dir, event_manager
    ):
        """Test setup skips incompatible services."""
        config = GperfHeapConfig()
        env = GperfHeapEnvironment(
            env_config_to_test=config,
            output_dir=temp_output_dir,
            env_type="execution",
            env_sub_type="gperf_heap",
            event_manager=event_manager,
        )

        # Create incompatible service
        service = self.create_mock_service(gperf_compatible=False)

        with patch(
            "panther.plugins.environments.execution_environment.gperf_heap.gperf_heap.create_execution_environment_builder"
        ) as mock_builder:
            with patch.object(env, "logger") as mock_logger:
                env._setup_plugin_specific_environment([service], "test_timestamp")

                # Should not create builder for incompatible service
                mock_builder.assert_not_called()

                # Should log skip message
                mock_logger.debug.assert_called_with(
                    "Skipping gperf heap profiling for %s (not gperf compatible)",
                    "test_service",
                )

    @patch(
        "panther.plugins.environments.execution_environment.gperf_heap.gperf_heap.create_execution_environment_builder"
    )
    @patch(
        "panther.plugins.environments.execution_environment.base_execution_environment.BaseExecutionEnvironment.standardized_environment_initialization"
    )
    def test_setup_multiple_services_mixed_compatibility(
        self, mock_std_init, mock_builder, temp_output_dir, event_manager
    ):
        """Test setup with multiple services (compatible and incompatible)."""
        config = GperfHeapConfig()
        env = GperfHeapEnvironment(
            env_config_to_test=config,
            output_dir=temp_output_dir,
            env_type="execution",
            env_sub_type="gperf_heap",
            event_manager=event_manager,
        )

        # Create multiple services
        service1 = self.create_mock_service(
            gperf_compatible=True, service_name="service1"
        )
        service2 = self.create_mock_service(
            gperf_compatible=False, service_name="service2"
        )
        service3 = self.create_mock_service(
            gperf_compatible=True, service_name="service3"
        )

        # Setup mock command builder
        mock_cmd_builder = Mock()
        mock_cmd_builder.register_output_file.side_effect = [
            "/tmp/heap.prof",
            "/tmp/heap_analysis.txt",  # First service
            "/tmp/heap2.prof",
            "/tmp/heap2_analysis.txt",  # Third service
        ]
        mock_builder.return_value = mock_cmd_builder

        services = [service1, service2, service3]

        env._setup_plugin_specific_environment(services, "test_timestamp")

        # Should create builder for 2 compatible services (service1 and service3)
        assert mock_builder.call_count == 2

    @patch(
        "panther.plugins.environments.execution_environment.gperf_heap.gperf_heap.create_execution_environment_builder"
    )
    @patch(
        "panther.plugins.environments.execution_environment.base_execution_environment.BaseExecutionEnvironment.standardized_environment_initialization"
    )
    def test_setup_empty_services_list(
        self, mock_std_init, mock_builder, temp_output_dir, event_manager
    ):
        """Test setup with empty services list."""
        config = GperfHeapConfig()
        env = GperfHeapEnvironment(
            env_config_to_test=config,
            output_dir=temp_output_dir,
            env_type="execution",
            env_sub_type="gperf_heap",
            event_manager=event_manager,
        )

        env._setup_plugin_specific_environment([], "test_timestamp")

        # Should not create any builders
        mock_builder.assert_not_called()


class TestGperfHeapEnvironmentUpdates:
    """Test suite for environment update functionality."""

    @patch(
        "panther.plugins.environments.execution_environment.base_execution_environment.BaseExecutionEnvironment.standardized_environment_initialization"
    )
    def test_update_environment(self, mock_std_init, temp_output_dir, event_manager):
        """Test environment update functionality."""
        config = GperfHeapConfig()
        env = GperfHeapEnvironment(
            env_config_to_test=config,
            output_dir=temp_output_dir,
            env_type="execution",
            env_sub_type="gperf_heap",
            event_manager=event_manager,
        )

        with patch.object(env, "logger") as mock_logger:
            env.update_environment(
                execution_environment=Mock(),
                global_config=GlobalConfig(),
                plugin_manager=Mock(),
                services_managers=[],
                test_config=Mock(),
            )

            # Should log debug message
            mock_logger.debug.assert_called_once_with(
                "Updated environment for gperf heap profiling execution"
            )


class TestGperfHeapErrorHandling:
    """Test suite for error handling and edge cases."""

    @patch(
        "panther.plugins.environments.execution_environment.base_execution_environment.BaseExecutionEnvironment.standardized_environment_initialization"
    )
    def test_service_without_service_name_attribute(
        self, mock_std_init, temp_output_dir, event_manager
    ):
        """Test handling service without service_name attribute."""
        config = GperfHeapConfig()
        env = GperfHeapEnvironment(
            env_config_to_test=config,
            output_dir=temp_output_dir,
            env_type="execution",
            env_sub_type="gperf_heap",
            event_manager=event_manager,
        )

        # Create service without service_name attribute
        service = Mock(spec=IServiceManager)
        service.service_config_to_test.implementation.gperf_compatible = False
        del service.service_name  # Remove service_name attribute
        service.__class__.__name__ = "TestHeapServiceManager"

        with patch.object(env, "logger") as mock_logger:
            env._setup_plugin_specific_environment([service], "test_timestamp")

            # Should use class name as fallback
            mock_logger.debug.assert_called_with(
                "Skipping gperf heap profiling for %s (not gperf compatible)",
                "TestHeapServiceManager",
            )

    @patch(
        "panther.plugins.environments.execution_environment.base_execution_environment.BaseExecutionEnvironment.standardized_environment_initialization"
    )
    def test_config_with_none_values(
        self, mock_std_init, temp_output_dir, event_manager
    ):
        """Test configuration with None values."""
        config = GperfHeapConfig(
            tcmalloc_library=None, heap_profile_allocation_interval=None
        )

        env = GperfHeapEnvironment(
            env_config_to_test=config,
            output_dir=temp_output_dir,
            env_type="execution",
            env_sub_type="gperf_heap",
            event_manager=event_manager,
        )

        command = env.to_command()

        # Should handle None values gracefully
        assert "HEAPPROFILE=" in command
        assert "LD_PRELOAD=" in command
        # Should not include None interval
        assert "HEAP_PROFILE_ALLOCATION_INTERVAL=" not in command


@pytest.mark.unit
class TestGperfHeapIntegration:
    """Integration-like tests within unit test scope."""

    @patch(
        "panther.plugins.environments.execution_environment.base_execution_environment.BaseExecutionEnvironment.standardized_environment_initialization"
    )
    def test_full_workflow_simulation(
        self, mock_std_init, temp_output_dir, event_manager
    ):
        """Test a full workflow simulation."""
        config = GperfHeapConfig(
            heap_profile_allocation_interval=2048,
            generate_pdf=True,
            enable_leak_check=True,
        )
        config.plugin_config = {
            "sampling_frequency": 2048,
            "heap_check_level": "normal",
            "profile_only_peak": False,
        }

        env = GperfHeapEnvironment(
            env_config_to_test=config,
            output_dir=temp_output_dir,
            env_type="execution",
            env_sub_type="gperf_heap",
            event_manager=event_manager,
        )

        # Test environment variable generation
        env_vars = env._build_heap_environment_vars("/tmp/test_heap.prof")

        assert env_vars["HEAPPROFILE"] == "/tmp/test_heap.prof"
        assert "libtcmalloc_and_profiler.so.4" in env_vars["LD_PRELOAD"]
        assert env_vars["HEAP_PROFILE_ALLOCATION_INTERVAL"] == "2048"
        assert env_vars["HEAPCHECK"] == "normal"

        # Test command generation
        command = env.to_command(output_file="/tmp/test.prof")

        assert "env" in command
        assert "HEAPPROFILE=/tmp/test.prof" in command
        assert "HEAP_PROFILE_ALLOCATION_INTERVAL=2048" in command
        assert "HEAPCHECK=normal" in command

        # Test post-processing command generation
        post_cmd = env._build_post_processing_command(
            "/tmp/heap.prof", "/tmp/analysis.txt", "test_service"
        )

        assert "GPerf Heap Analysis" in post_cmd
        assert "Top Memory Consumers" in post_cmd
        assert "Memory Allocation Tree" in post_cmd

        # Test environment update
        env.update_environment(
            execution_environment=Mock(),
            global_config=GlobalConfig(),
            plugin_manager=Mock(),
            services_managers=[],
            test_config=Mock(),
        )

        # Should complete without errors
        assert True
