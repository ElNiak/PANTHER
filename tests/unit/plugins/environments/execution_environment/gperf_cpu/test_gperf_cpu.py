"""
Comprehensive unit tests for GperfCpuEnvironment.

Tests CPU profiling functionality, configuration handling, and command generation.
"""

from pathlib import Path
from typing import List
from unittest.mock import MagicMock, Mock, patch

import pytest

from panther.config.core.models.global_config import GlobalConfig
from panther.core.observer.management.event_manager import EventManager
from panther.plugins.environments.config_schema import EnvironmentConfig
from panther.plugins.environments.execution_environment.gperf_cpu.config_schema import (
    GperfCpuConfig,
)
from panther.plugins.environments.execution_environment.gperf_cpu.gperf_cpu import (
    GperfCpuEnvironment,
)
from panther.plugins.services.services_interface import IServiceManager


class TestGperfCpuEnvironmentInitialization:
    """Test suite for GperfCpuEnvironment initialization."""

    @patch(
        "panther.plugins.environments.execution_environment.base_execution_environment.BaseExecutionEnvironment.standardized_environment_initialization"
    )
    def test_basic_initialization(self, mock_std_init, temp_output_dir, event_manager):
        """Test basic GperfCpuEnvironment initialization."""
        config = GperfCpuConfig()

        env = GperfCpuEnvironment(
            env_config_to_test=config,
            output_dir=temp_output_dir,
            env_type="execution",
            env_sub_type="gperf_cpu",
            event_manager=event_manager,
        )

        assert env.env_config_to_test == config
        assert env.output_dir == temp_output_dir
        assert env.env_type == "execution"
        assert env.env_sub_type == "gperf_cpu"
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
        assert hasattr(GperfCpuEnvironment, "_plugin_info")

        plugin_info = GperfCpuEnvironment._plugin_info
        assert plugin_info["name"] == "gperf_cpu"
        assert plugin_info["version"] == "1.0.0"
        assert (
            plugin_info["description"]
            == "Google Performance Tools CPU profiling environment"
        )
        assert "cpu_profiling" in plugin_info["capabilities"]
        assert "performance_analysis" in plugin_info["capabilities"]
        assert "libgoogle-perftools-dev" in plugin_info["external_dependencies"]

    @patch(
        "panther.plugins.environments.execution_environment.base_execution_environment.BaseExecutionEnvironment.standardized_environment_initialization"
    )
    def test_inheritance_chain(self, mock_std_init, temp_output_dir, event_manager):
        """Test that GperfCpuEnvironment has correct inheritance."""
        from panther.plugins.environments.execution_environment.base_execution_environment import (
            BaseExecutionEnvironment,
        )

        config = GperfCpuConfig()
        env = GperfCpuEnvironment(
            env_config_to_test=config,
            output_dir=temp_output_dir,
            env_type="execution",
            env_sub_type="gperf_cpu",
            event_manager=event_manager,
        )

        assert isinstance(env, BaseExecutionEnvironment)
        assert isinstance(env, GperfCpuEnvironment)


class TestGperfCpuConfigurationHandling:
    """Test suite for configuration handling with dual approach."""

    @patch(
        "panther.plugins.environments.execution_environment.base_execution_environment.BaseExecutionEnvironment.standardized_environment_initialization"
    )
    def test_get_plugin_config_caching(
        self, mock_std_init, temp_output_dir, event_manager
    ):
        """Test that plugin config is cached correctly."""
        config = GperfCpuConfig(sampling_frequency=200)

        with patch.object(
            config, "get_plugin_config", return_value=config
        ) as mock_get_config:
            env = GperfCpuEnvironment(
                env_config_to_test=config,
                output_dir=temp_output_dir,
                env_type="execution",
                env_sub_type="gperf_cpu",
                event_manager=event_manager,
            )

            # First call should invoke get_plugin_config
            plugin_config1 = env._get_plugin_config()
            mock_get_config.assert_called_once_with(GperfCpuConfig)

            # Second call should use cached value
            plugin_config2 = env._get_plugin_config()
            mock_get_config.assert_called_once()  # Still only one call

            assert plugin_config1 is plugin_config2
            assert plugin_config1.sampling_frequency == 200

    @patch(
        "panther.plugins.environments.execution_environment.base_execution_environment.BaseExecutionEnvironment.standardized_environment_initialization"
    )
    def test_get_plugin_config_exception_fallback(
        self, mock_std_init, temp_output_dir, event_manager
    ):
        """Test fallback to default config when get_plugin_config fails."""
        config = GperfCpuConfig()

        with patch.object(
            config, "get_plugin_config", side_effect=Exception("Config error")
        ):
            env = GperfCpuEnvironment(
                env_config_to_test=config,
                output_dir=temp_output_dir,
                env_type="execution",
                env_sub_type="gperf_cpu",
                event_manager=event_manager,
            )

            with patch.object(env, "logger") as mock_logger:
                plugin_config = env._get_plugin_config()

                # Should return default config
                assert isinstance(plugin_config, GperfCpuConfig)
                assert plugin_config.sampling_frequency is None  # Default value

                # Should log debug message
                mock_logger.debug.assert_called_once()
                assert "Could not get plugin config, using defaults" in str(
                    mock_logger.debug.call_args
                )

    @patch(
        "panther.plugins.environments.execution_environment.base_execution_environment.BaseExecutionEnvironment.standardized_environment_initialization"
    )
    def test_dual_config_approach_dict_priority(
        self, mock_std_init, temp_output_dir, event_manager
    ):
        """Test that dict config takes priority in dual approach."""
        config = GperfCpuConfig()
        config.plugin_config = {"profiler_library": "/custom/path/libprofiler.so"}

        env = GperfCpuEnvironment(
            env_config_to_test=config,
            output_dir=temp_output_dir,
            env_type="execution",
            env_sub_type="gperf_cpu",
            event_manager=event_manager,
        )

        # Mock the typed config to have a different value
        with patch.object(env, "_get_plugin_config") as mock_get_config:
            typed_config = GperfCpuConfig(profiler_library="/typed/path/libprofiler.so")
            mock_get_config.return_value = typed_config

            # Should prefer dict config over typed config
            # This requires access to the internal logic - we'll test through setup
            mock_service = Mock(spec=IServiceManager)
            mock_service.service_config_to_test.implementation.gperf_compatible = True

            with patch(
                "panther.plugins.environments.execution_environment.gperf_cpu.gperf_cpu.create_execution_environment_builder"
            ) as mock_builder:
                mock_cmd_builder = Mock()
                mock_cmd_builder.register_output_file.return_value = "/tmp/cpu.prof"
                mock_cmd_builder.service_name = "test_service"
                mock_cmd_builder.build_and_apply.return_value = []
                mock_builder.return_value = mock_cmd_builder

                env._setup_plugin_specific_environment([mock_service], "test_timestamp")

                # Verify the custom library path was used in wrapper command
                calls = mock_cmd_builder.add_conditional_wrapper.call_args_list
                assert len(calls) > 0
                wrapper_command = calls[0][1]["wrapper_command"]
                assert "/custom/path/libprofiler.so" in wrapper_command


class TestGperfCpuCommandGeneration:
    """Test suite for command generation functionality."""

    @patch(
        "panther.plugins.environments.execution_environment.base_execution_environment.BaseExecutionEnvironment.standardized_environment_initialization"
    )
    def test_to_command_basic(self, mock_std_init, temp_output_dir, event_manager):
        """Test basic command generation."""
        config = GperfCpuConfig(
            profiler_library="/usr/lib/libprofiler.so",
            sampling_frequency=100,
            use_realtime_signal=True,
        )

        env = GperfCpuEnvironment(
            env_config_to_test=config,
            output_dir=temp_output_dir,
            env_type="execution",
            env_sub_type="gperf_cpu",
            event_manager=event_manager,
        )

        command = env.to_command(output_file="/tmp/test.prof")

        expected_parts = [
            "env LD_PRELOAD=/usr/lib/libprofiler.so",
            "CPUPROFILE=/tmp/test.prof",
            "CPUPROFILE_FREQUENCY=100",
            "CPUPROFILE_REALTIME=1",
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
        config = GperfCpuConfig()

        env = GperfCpuEnvironment(
            env_config_to_test=config,
            output_dir=temp_output_dir,
            env_type="execution",
            env_sub_type="gperf_cpu",
            event_manager=event_manager,
        )

        command = env.to_command()

        # Should use default output file
        assert "CPUPROFILE=/tmp/cpu_profile.prof" in command

    @patch(
        "panther.plugins.environments.execution_environment.base_execution_environment.BaseExecutionEnvironment.standardized_environment_initialization"
    )
    def test_to_command_custom_output_from_config(
        self, mock_std_init, temp_output_dir, event_manager
    ):
        """Test command generation with output file from config."""
        config = GperfCpuConfig(output_file="/custom/output.prof")

        env = GperfCpuEnvironment(
            env_config_to_test=config,
            output_dir=temp_output_dir,
            env_type="execution",
            env_sub_type="gperf_cpu",
            event_manager=event_manager,
        )

        command = env.to_command()

        assert "CPUPROFILE=/custom/output.prof" in command

    @patch(
        "panther.plugins.environments.execution_environment.base_execution_environment.BaseExecutionEnvironment.standardized_environment_initialization"
    )
    def test_to_command_default_profiler_library(
        self, mock_std_init, temp_output_dir, event_manager
    ):
        """Test command generation with default profiler library."""
        config = GperfCpuConfig()

        env = GperfCpuEnvironment(
            env_config_to_test=config,
            output_dir=temp_output_dir,
            env_type="execution",
            env_sub_type="gperf_cpu",
            event_manager=event_manager,
        )

        command = env.to_command()

        # Should use default profiler library
        assert "LD_PRELOAD=/usr/lib/x86_64-linux-gnu/libprofiler.so.0" in command

    @patch(
        "panther.plugins.environments.execution_environment.base_execution_environment.BaseExecutionEnvironment.standardized_environment_initialization"
    )
    def test_to_command_pid_parameter_warning(
        self, mock_std_init, temp_output_dir, event_manager
    ):
        """Test that PID parameter generates warning."""
        config = GperfCpuConfig()

        env = GperfCpuEnvironment(
            env_config_to_test=config,
            output_dir=temp_output_dir,
            env_type="execution",
            env_sub_type="gperf_cpu",
            event_manager=event_manager,
        )

        with patch.object(env, "logger") as mock_logger:
            command = env.to_command(pid=12345)

            # Should log warning about PID being ignored
            mock_logger.warning.assert_called_once()
            warning_msg = str(mock_logger.warning.call_args)
            assert "PID parameter" in warning_msg
            assert "12345" in warning_msg
            assert "does not support attaching" in warning_msg

    @patch(
        "panther.plugins.environments.execution_environment.base_execution_environment.BaseExecutionEnvironment.standardized_environment_initialization"
    )
    def test_to_command_minimal_config(
        self, mock_std_init, temp_output_dir, event_manager
    ):
        """Test command generation with minimal configuration."""
        config = GperfCpuConfig()

        env = GperfCpuEnvironment(
            env_config_to_test=config,
            output_dir=temp_output_dir,
            env_type="execution",
            env_sub_type="gperf_cpu",
            event_manager=event_manager,
        )

        command = env.to_command()

        # Should only include basic environment variables
        assert "env LD_PRELOAD=" in command
        assert "CPUPROFILE=" in command
        assert "CPUPROFILE_FREQUENCY=" not in command  # Should not be present
        assert "CPUPROFILE_REALTIME=" not in command  # Should not be present


class TestGperfCpuPluginSpecificSetup:
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
        "panther.plugins.environments.execution_environment.gperf_cpu.gperf_cpu.create_execution_environment_builder"
    )
    @patch(
        "panther.plugins.environments.execution_environment.base_execution_environment.BaseExecutionEnvironment.standardized_environment_initialization"
    )
    def test_setup_plugin_specific_environment_single_service(
        self, mock_std_init, mock_builder, temp_output_dir, event_manager
    ):
        """Test setup with single gperf-compatible service."""
        config = GperfCpuConfig()
        env = GperfCpuEnvironment(
            env_config_to_test=config,
            output_dir=temp_output_dir,
            env_type="execution",
            env_sub_type="gperf_cpu",
            event_manager=event_manager,
        )

        # Setup mock command builder
        mock_cmd_builder = Mock()
        mock_cmd_builder.register_output_file.return_value = "/tmp/cpu.prof"
        mock_cmd_builder.service_name = "test_service"
        mock_cmd_builder.build_and_apply.return_value = ["command1", "command2"]
        mock_builder.return_value = mock_cmd_builder

        # Create mock service
        service = self.create_mock_service()

        with patch.object(env, "modify_service_commands") as mock_modify:
            env._setup_plugin_specific_environment([service], "test_timestamp")

            # Verify builder was created correctly
            mock_builder.assert_called_once_with(
                service=service,
                environment_name="gperf_cpu",
                timestamp="test_timestamp",
                register_output_callback=env.register_output_file,
                logger=env.logger,
            )

            # Verify output file registration
            mock_cmd_builder.register_output_file.assert_called_with(
                file_type="cpu_profile",
                extension="prof",
                description="CPU profile data",
            )

            # Verify conditional wrapper was added
            mock_cmd_builder.add_conditional_wrapper.assert_called_once()

            # Verify build_and_apply was called
            mock_cmd_builder.build_and_apply.assert_called_once_with(mock_modify)

    @patch(
        "panther.plugins.environments.execution_environment.base_execution_environment.BaseExecutionEnvironment.standardized_environment_initialization"
    )
    def test_setup_plugin_specific_environment_incompatible_service(
        self, mock_std_init, temp_output_dir, event_manager
    ):
        """Test setup skips incompatible services."""
        config = GperfCpuConfig()
        env = GperfCpuEnvironment(
            env_config_to_test=config,
            output_dir=temp_output_dir,
            env_type="execution",
            env_sub_type="gperf_cpu",
            event_manager=event_manager,
        )

        # Create incompatible service
        service = self.create_mock_service(gperf_compatible=False)

        with patch(
            "panther.plugins.environments.execution_environment.gperf_cpu.gperf_cpu.create_execution_environment_builder"
        ) as mock_builder:
            with patch.object(env, "logger") as mock_logger:
                env._setup_plugin_specific_environment([service], "test_timestamp")

                # Should not create builder for incompatible service
                mock_builder.assert_not_called()

                # Should log skip message
                mock_logger.debug.assert_called_with(
                    "Skipping gperf CPU profiling for %s (not gperf compatible)",
                    "test_service",
                )

    @patch(
        "panther.plugins.environments.execution_environment.gperf_cpu.gperf_cpu.create_execution_environment_builder"
    )
    @patch(
        "panther.plugins.environments.execution_environment.base_execution_environment.BaseExecutionEnvironment.standardized_environment_initialization"
    )
    def test_setup_with_pdf_generation(
        self, mock_std_init, mock_builder, temp_output_dir, event_manager
    ):
        """Test setup with PDF generation enabled."""
        config = GperfCpuConfig(generate_pdf=True, pprof_options=["--lines"])
        env = GperfCpuEnvironment(
            env_config_to_test=config,
            output_dir=temp_output_dir,
            env_type="execution",
            env_sub_type="gperf_cpu",
            event_manager=event_manager,
        )

        # Setup mock command builder
        mock_cmd_builder = Mock()
        mock_cmd_builder.register_output_file.side_effect = [
            "/tmp/cpu.prof",
            "/tmp/cpu.pdf",
        ]
        mock_cmd_builder.service_name = "test_service"
        mock_cmd_builder.build_and_apply.return_value = []
        mock_builder.return_value = mock_cmd_builder

        service = self.create_mock_service()

        env._setup_plugin_specific_environment([service], "test_timestamp")

        # Verify both profile and PDF files were registered
        assert mock_cmd_builder.register_output_file.call_count == 2

        # Verify post-processing was added for PDF generation
        mock_cmd_builder.add_post_processing.assert_called_once()
        post_processing_call = mock_cmd_builder.add_post_processing.call_args

        assert post_processing_call[1]["input_file"] == "/tmp/cpu.prof"
        assert post_processing_call[1]["output_file"] == "/tmp/cpu.pdf"
        assert "pprof --pdf --lines" in post_processing_call[1]["processing_command"]

    @patch(
        "panther.plugins.environments.execution_environment.gperf_cpu.gperf_cpu.create_execution_environment_builder"
    )
    @patch(
        "panther.plugins.environments.execution_environment.base_execution_environment.BaseExecutionEnvironment.standardized_environment_initialization"
    )
    def test_setup_with_function_filtering(
        self, mock_std_init, mock_builder, temp_output_dir, event_manager
    ):
        """Test setup with function include/exclude filtering."""
        config = GperfCpuConfig(
            generate_pdf=True,
            exclude_functions=["malloc", "free"],
            include_only_functions=["main", "process_data"],
        )
        env = GperfCpuEnvironment(
            env_config_to_test=config,
            output_dir=temp_output_dir,
            env_type="execution",
            env_sub_type="gperf_cpu",
            event_manager=event_manager,
        )

        # Setup mock command builder
        mock_cmd_builder = Mock()
        mock_cmd_builder.register_output_file.side_effect = [
            "/tmp/cpu.prof",
            "/tmp/cpu.pdf",
        ]
        mock_cmd_builder.service_name = "test_service"
        mock_cmd_builder.build_and_apply.return_value = []
        mock_builder.return_value = mock_cmd_builder

        service = self.create_mock_service()

        env._setup_plugin_specific_environment([service], "test_timestamp")

        # Verify post-processing includes filtering options
        post_processing_call = mock_cmd_builder.add_post_processing.call_args
        processing_command = post_processing_call[1]["processing_command"]

        assert "--ignore malloc" in processing_command
        assert "--ignore free" in processing_command
        assert "--focus main" in processing_command
        assert "--focus process_data" in processing_command

    @patch(
        "panther.plugins.environments.execution_environment.gperf_cpu.gperf_cpu.create_execution_environment_builder"
    )
    @patch(
        "panther.plugins.environments.execution_environment.base_execution_environment.BaseExecutionEnvironment.standardized_environment_initialization"
    )
    def test_setup_multiple_services(
        self, mock_std_init, mock_builder, temp_output_dir, event_manager
    ):
        """Test setup with multiple services (compatible and incompatible)."""
        config = GperfCpuConfig()
        env = GperfCpuEnvironment(
            env_config_to_test=config,
            output_dir=temp_output_dir,
            env_type="execution",
            env_sub_type="gperf_cpu",
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
        mock_cmd_builder.register_output_file.return_value = "/tmp/cpu.prof"
        mock_cmd_builder.service_name = "test_service"
        mock_cmd_builder.build_and_apply.return_value = []
        mock_builder.return_value = mock_cmd_builder

        services = [service1, service2, service3]

        env._setup_plugin_specific_environment(services, "test_timestamp")

        # Should create builder for 2 compatible services (service1 and service3)
        assert mock_builder.call_count == 2


class TestGperfCpuEnvironmentUpdates:
    """Test suite for environment update functionality."""

    @patch(
        "panther.plugins.environments.execution_environment.base_execution_environment.BaseExecutionEnvironment.standardized_environment_initialization"
    )
    def test_update_environment(self, mock_std_init, temp_output_dir, event_manager):
        """Test environment update functionality."""
        config = GperfCpuConfig()
        env = GperfCpuEnvironment(
            env_config_to_test=config,
            output_dir=temp_output_dir,
            env_type="execution",
            env_sub_type="gperf_cpu",
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
                "Updated environment for gperf CPU profiling execution"
            )


class TestGperfCpuErrorHandling:
    """Test suite for error handling and edge cases."""

    @patch(
        "panther.plugins.environments.execution_environment.base_execution_environment.BaseExecutionEnvironment.standardized_environment_initialization"
    )
    def test_service_without_service_name_attribute(
        self, mock_std_init, temp_output_dir, event_manager
    ):
        """Test handling service without service_name attribute."""
        config = GperfCpuConfig()
        env = GperfCpuEnvironment(
            env_config_to_test=config,
            output_dir=temp_output_dir,
            env_type="execution",
            env_sub_type="gperf_cpu",
            event_manager=event_manager,
        )

        # Create service without service_name attribute
        service = Mock(spec=IServiceManager)
        service.service_config_to_test.implementation.gperf_compatible = False
        del service.service_name  # Remove service_name attribute
        service.__class__.__name__ = "TestServiceManager"

        with patch.object(env, "logger") as mock_logger:
            env._setup_plugin_specific_environment([service], "test_timestamp")

            # Should use class name as fallback
            mock_logger.debug.assert_called_with(
                "Skipping gperf CPU profiling for %s (not gperf compatible)",
                "TestServiceManager",
            )

    @patch(
        "panther.plugins.environments.execution_environment.gperf_cpu.gperf_cpu.create_execution_environment_builder"
    )
    @patch(
        "panther.plugins.environments.execution_environment.base_execution_environment.BaseExecutionEnvironment.standardized_environment_initialization"
    )
    def test_empty_services_list(
        self, mock_std_init, mock_builder, temp_output_dir, event_manager
    ):
        """Test setup with empty services list."""
        config = GperfCpuConfig()
        env = GperfCpuEnvironment(
            env_config_to_test=config,
            output_dir=temp_output_dir,
            env_type="execution",
            env_sub_type="gperf_cpu",
            event_manager=event_manager,
        )

        env._setup_plugin_specific_environment([], "test_timestamp")

        # Should not create any builders
        mock_builder.assert_not_called()

    @patch(
        "panther.plugins.environments.execution_environment.base_execution_environment.BaseExecutionEnvironment.standardized_environment_initialization"
    )
    def test_config_with_none_values(
        self, mock_std_init, temp_output_dir, event_manager
    ):
        """Test configuration with None values."""
        config = GperfCpuConfig(
            profiler_library=None, sampling_frequency=None, output_file=None
        )

        env = GperfCpuEnvironment(
            env_config_to_test=config,
            output_dir=temp_output_dir,
            env_type="execution",
            env_sub_type="gperf_cpu",
            event_manager=event_manager,
        )

        command = env.to_command()

        # Should use defaults for None values
        assert "/usr/lib/x86_64-linux-gnu/libprofiler.so.0" in command
        assert "/tmp/cpu_profile.prof" in command
        assert "CPUPROFILE_FREQUENCY=" not in command


@pytest.mark.unit
class TestGperfCpuIntegration:
    """Integration-like tests within unit test scope."""

    @patch(
        "panther.plugins.environments.execution_environment.base_execution_environment.BaseExecutionEnvironment.standardized_environment_initialization"
    )
    def test_full_workflow_simulation(
        self, mock_std_init, temp_output_dir, event_manager
    ):
        """Test a full workflow simulation."""
        config = GperfCpuConfig(
            profiler_library="/usr/lib/libprofiler.so",
            sampling_frequency=100,
            generate_pdf=True,
            pprof_options=["--lines"],
        )

        env = GperfCpuEnvironment(
            env_config_to_test=config,
            output_dir=temp_output_dir,
            env_type="execution",
            env_sub_type="gperf_cpu",
            event_manager=event_manager,
        )

        # Test command generation
        command = env.to_command(output_file="/tmp/test.prof")

        assert "env LD_PRELOAD=/usr/lib/libprofiler.so" in command
        assert "CPUPROFILE=/tmp/test.prof" in command
        assert "CPUPROFILE_FREQUENCY=100" in command

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
