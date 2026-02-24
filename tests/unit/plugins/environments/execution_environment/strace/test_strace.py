"""
Comprehensive unit tests for StraceEnvironment.

Tests system call tracing functionality, configuration handling, and command generation.
"""

from pathlib import Path
from typing import List
from unittest.mock import MagicMock, Mock, call, patch

import pytest

from panther.config.core.models.global_config import GlobalConfig
from panther.core.observer.management.event_manager import EventManager
from panther.plugins.environments.config_schema import EnvironmentConfig
from panther.plugins.environments.execution_environment.strace.config_schema import (
    StraceConfig,
)
from panther.plugins.environments.execution_environment.strace.strace import (
    StraceEnvironment,
)
from panther.plugins.services.services_interface import IServiceManager


class TestStraceEnvironmentInitialization:
    """Test suite for StraceEnvironment initialization."""

    @patch(
        "panther.plugins.environments.execution_environment.base_execution_environment.BaseExecutionEnvironment.standardized_environment_initialization"
    )
    def test_basic_initialization(self, mock_std_init, temp_output_dir, event_manager):
        """Test basic StraceEnvironment initialization."""
        config = StraceConfig()

        env = StraceEnvironment(
            env_config_to_test=config,
            output_dir=temp_output_dir,
            env_type="execution",
            env_sub_type="strace",
            event_manager=event_manager,
        )

        assert env.env_config_to_test == config
        assert env.output_dir == temp_output_dir
        assert env.env_type == "execution"
        assert env.env_sub_type == "strace"
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
        assert hasattr(StraceEnvironment, "_plugin_info")

        plugin_info = StraceEnvironment._plugin_info
        assert plugin_info["name"] == "strace"
        assert plugin_info["version"] == "1.0.0"
        assert plugin_info["description"] == "System call tracing execution environment"
        assert "syscall_tracing" in plugin_info["capabilities"]
        assert "performance_analysis" in plugin_info["capabilities"]
        assert "debugging" in plugin_info["capabilities"]
        assert "strace>=4.0" in plugin_info["external_dependencies"]

    @patch(
        "panther.plugins.environments.execution_environment.base_execution_environment.BaseExecutionEnvironment.standardized_environment_initialization"
    )
    def test_inheritance_chain(self, mock_std_init, temp_output_dir, event_manager):
        """Test that StraceEnvironment has correct inheritance."""
        from panther.plugins.environments.execution_environment.base_execution_environment import (
            BaseExecutionEnvironment,
        )

        config = StraceConfig()
        env = StraceEnvironment(
            env_config_to_test=config,
            output_dir=temp_output_dir,
            env_type="execution",
            env_sub_type="strace",
            event_manager=event_manager,
        )

        assert isinstance(env, BaseExecutionEnvironment)
        assert isinstance(env, StraceEnvironment)


class TestStraceConfigurationHandling:
    """Test suite for configuration handling with dual approach."""

    @patch(
        "panther.plugins.environments.execution_environment.base_execution_environment.BaseExecutionEnvironment.standardized_environment_initialization"
    )
    def test_get_plugin_config_caching(
        self, mock_std_init, temp_output_dir, event_manager
    ):
        """Test that plugin config is cached correctly."""
        config = StraceConfig(timeout=120)

        with patch.object(
            config, "get_plugin_config", return_value=config
        ) as mock_get_config:
            env = StraceEnvironment(
                env_config_to_test=config,
                output_dir=temp_output_dir,
                env_type="execution",
                env_sub_type="strace",
                event_manager=event_manager,
            )

            # First call should invoke get_plugin_config
            plugin_config1 = env._get_plugin_config()
            mock_get_config.assert_called_once_with(StraceConfig)

            # Second call should use cached value
            plugin_config2 = env._get_plugin_config()
            mock_get_config.assert_called_once()  # Still only one call

            assert plugin_config1 is plugin_config2
            assert plugin_config1.timeout == 120

    @patch(
        "panther.plugins.environments.execution_environment.base_execution_environment.BaseExecutionEnvironment.standardized_environment_initialization"
    )
    def test_get_plugin_config_exception_fallback(
        self, mock_std_init, temp_output_dir, event_manager
    ):
        """Test fallback to default config when get_plugin_config fails."""
        config = StraceConfig()

        with patch.object(
            config, "get_plugin_config", side_effect=Exception("Config error")
        ):
            env = StraceEnvironment(
                env_config_to_test=config,
                output_dir=temp_output_dir,
                env_type="execution",
                env_sub_type="strace",
                event_manager=event_manager,
            )

            with patch.object(env, "logger") as mock_logger:
                plugin_config = env._get_plugin_config()

                # Should return default config
                assert isinstance(plugin_config, StraceConfig)
                assert plugin_config.timeout == 60  # Default value

                # Should log debug message
                mock_logger.debug.assert_called_once()
                assert "Could not get plugin config, using defaults" in str(
                    mock_logger.debug.call_args
                )


class TestStraceOutputPatterns:
    """Test suite for output pattern functionality."""

    @patch(
        "panther.plugins.environments.execution_environment.base_execution_environment.BaseExecutionEnvironment.standardized_environment_initialization"
    )
    def test_get_output_patterns(self, mock_std_init, temp_output_dir, event_manager):
        """Test strace-specific output patterns."""
        config = StraceConfig()
        env = StraceEnvironment(
            env_config_to_test=config,
            output_dir=temp_output_dir,
            env_type="execution",
            env_sub_type="strace",
            event_manager=event_manager,
        )

        patterns = env.get_output_patterns()

        expected_patterns = [
            ("strace_log", "strace_{service_name}.log"),
            ("strace_summary", "strace_summary_{service_name}.txt"),
            ("syscall_stats", "strace_stats_{service_name}.log"),
            ("timing", "strace_timing_{service_name}.log"),
        ]

        assert patterns == expected_patterns

    @patch(
        "panther.plugins.environments.execution_environment.base_execution_environment.BaseExecutionEnvironment.standardized_environment_initialization"
    )
    def test_get_additional_output_discovery_patterns(
        self, mock_std_init, temp_output_dir, event_manager
    ):
        """Test additional output discovery patterns."""
        config = StraceConfig()
        env = StraceEnvironment(
            env_config_to_test=config,
            output_dir=temp_output_dir,
            env_type="execution",
            env_sub_type="strace",
            event_manager=event_manager,
        )

        patterns = env.get_additional_output_discovery_patterns()

        expected_patterns = {
            "strace_child": ["strace_*_child_*.log"],
            "strace_error": ["*strace*.err", "*strace*error*"],
            "strace_filtered": ["strace_filtered_*.log"],
        }

        assert patterns == expected_patterns


class TestStraceCommandGeneration:
    """Test suite for strace command generation."""

    @patch(
        "panther.plugins.environments.execution_environment.base_execution_environment.BaseExecutionEnvironment.standardized_environment_initialization"
    )
    def test_build_strace_command_basic(
        self, mock_std_init, temp_output_dir, event_manager
    ):
        """Test basic strace command generation."""
        config = StraceConfig()
        env = StraceEnvironment(
            env_config_to_test=config,
            output_dir=temp_output_dir,
            env_type="execution",
            env_sub_type="strace",
            event_manager=event_manager,
        )

        command = env._build_strace_command("/tmp/strace.log")

        # Check basic command structure
        assert "mkdir -p /tmp" in command
        assert "/usr/bin/strace" in command
        assert "-o /tmp/strace.log" in command
        assert "-tt" in command  # Timestamps

    @patch(
        "panther.plugins.environments.execution_environment.base_execution_environment.BaseExecutionEnvironment.standardized_environment_initialization"
    )
    def test_build_strace_command_with_kernel_stack(
        self, mock_std_init, temp_output_dir, event_manager
    ):
        """Test strace command generation with kernel stack enabled."""
        config = StraceConfig()
        config.plugin_config = {"include_kernel_stack": True}

        env = StraceEnvironment(
            env_config_to_test=config,
            output_dir=temp_output_dir,
            env_type="execution",
            env_sub_type="strace",
            event_manager=event_manager,
        )

        command = env._build_strace_command("/tmp/strace.log")

        assert "-k" in command  # Kernel stack option

    @patch(
        "panther.plugins.environments.execution_environment.base_execution_environment.BaseExecutionEnvironment.standardized_environment_initialization"
    )
    def test_build_strace_command_with_excluded_syscalls(
        self, mock_std_init, temp_output_dir, event_manager
    ):
        """Test strace command generation with excluded syscalls."""
        config = StraceConfig()
        config.plugin_config = {"excluded_syscalls": ["nanosleep", "gettimeofday"]}

        env = StraceEnvironment(
            env_config_to_test=config,
            output_dir=temp_output_dir,
            env_type="execution",
            env_sub_type="strace",
            event_manager=event_manager,
        )

        command = env._build_strace_command("/tmp/strace.log")

        assert "-e trace=!nanosleep,gettimeofday" in command

    @patch(
        "panther.plugins.environments.execution_environment.base_execution_environment.BaseExecutionEnvironment.standardized_environment_initialization"
    )
    def test_build_strace_command_with_network_focus(
        self, mock_std_init, temp_output_dir, event_manager
    ):
        """Test strace command generation with network syscalls focus."""
        config = StraceConfig()
        config.plugin_config = {"trace_network_syscalls": True}

        env = StraceEnvironment(
            env_config_to_test=config,
            output_dir=temp_output_dir,
            env_type="execution",
            env_sub_type="strace",
            event_manager=event_manager,
        )

        command = env._build_strace_command("/tmp/strace.log")

        assert (
            "-e trace=network,read,write,send,recv,connect,bind,listen,accept"
            in command
        )

    @patch(
        "panther.plugins.environments.execution_environment.base_execution_environment.BaseExecutionEnvironment.standardized_environment_initialization"
    )
    def test_build_strace_command_with_timeout(
        self, mock_std_init, temp_output_dir, event_manager
    ):
        """Test strace command generation with timeout (timeout wrapper disabled)."""
        config = StraceConfig()
        config.plugin_config = {"timeout": 30}

        env = StraceEnvironment(
            env_config_to_test=config,
            output_dir=temp_output_dir,
            env_type="execution",
            env_sub_type="strace",
            event_manager=event_manager,
        )

        command = env._build_strace_command("/tmp/strace.log")

        # Timeout wrapper is now disabled - service-level timeout handles process lifecycle
        assert "timeout 30" not in command
        assert "/usr/bin/strace" in command

    @patch(
        "panther.plugins.environments.execution_environment.base_execution_environment.BaseExecutionEnvironment.standardized_environment_initialization"
    )
    def test_build_strace_command_with_additional_parameters(
        self, mock_std_init, temp_output_dir, event_manager
    ):
        """Test strace command generation with additional parameters."""
        config = StraceConfig()
        config.plugin_config = {"additional_parameters": ["-f", "-v"]}

        env = StraceEnvironment(
            env_config_to_test=config,
            output_dir=temp_output_dir,
            env_type="execution",
            env_sub_type="strace",
            event_manager=event_manager,
        )

        command = env._build_strace_command("/tmp/strace.log")

        assert "-f -v" in command

    @patch(
        "panther.plugins.environments.execution_environment.base_execution_environment.BaseExecutionEnvironment.standardized_environment_initialization"
    )
    def test_build_strace_command_typed_config_fallback(
        self, mock_std_init, temp_output_dir, event_manager
    ):
        """Test strace command generation with typed config fallback."""
        config = StraceConfig(
            include_kernel_stack=True, timeout=45, additional_parameters=["-c"]
        )

        env = StraceEnvironment(
            env_config_to_test=config,
            output_dir=temp_output_dir,
            env_type="execution",
            env_sub_type="strace",
            event_manager=event_manager,
        )

        # Mock typed config to test fallback
        with patch.object(env, "_get_plugin_config") as mock_get_config:
            typed_config = StraceConfig()
            typed_config.include_kernel_stack = True
            typed_config.timeout = 45
            typed_config.additional_parameters = ["-c"]
            mock_get_config.return_value = typed_config

            command = env._build_strace_command("/tmp/strace.log")

            assert "-k" in command
            assert "timeout 45" in command
            assert "-c" in command


class TestStraceCommandInterface:
    """Test suite for to_command interface."""

    @patch(
        "panther.plugins.environments.execution_environment.base_execution_environment.BaseExecutionEnvironment.standardized_environment_initialization"
    )
    def test_to_command_basic(self, mock_std_init, temp_output_dir, event_manager):
        """Test basic to_command functionality."""
        config = StraceConfig()
        env = StraceEnvironment(
            env_config_to_test=config,
            output_dir=temp_output_dir,
            env_type="execution",
            env_sub_type="strace",
            event_manager=event_manager,
        )

        command = env.to_command(output_file="/tmp/test.log")

        assert "mkdir -p /tmp" in command
        assert "/usr/bin/strace" in command
        assert "-o /tmp/test.log" in command

    @patch(
        "panther.plugins.environments.execution_environment.base_execution_environment.BaseExecutionEnvironment.standardized_environment_initialization"
    )
    def test_to_command_default_output_file(
        self, mock_std_init, temp_output_dir, event_manager
    ):
        """Test to_command with default output file."""
        config = StraceConfig(output_file="/custom/strace.log")
        env = StraceEnvironment(
            env_config_to_test=config,
            output_dir=temp_output_dir,
            env_type="execution",
            env_sub_type="strace",
            event_manager=event_manager,
        )

        # Mock typed config to test fallback
        with patch.object(env, "_get_plugin_config") as mock_get_config:
            typed_config = StraceConfig()
            typed_config.output_file = "/custom/strace.log"
            mock_get_config.return_value = typed_config

            command = env.to_command()

            assert "-o /custom/strace.log" in command

    @patch(
        "panther.plugins.environments.execution_environment.base_execution_environment.BaseExecutionEnvironment.standardized_environment_initialization"
    )
    def test_to_command_fallback_default(
        self, mock_std_init, temp_output_dir, event_manager
    ):
        """Test to_command fallback to absolute default."""
        config = StraceConfig()
        env = StraceEnvironment(
            env_config_to_test=config,
            output_dir=temp_output_dir,
            env_type="execution",
            env_sub_type="strace",
            event_manager=event_manager,
        )

        # Mock typed config without output_file
        with patch.object(env, "_get_plugin_config") as mock_get_config:
            typed_config = StraceConfig()
            typed_config.output_file = None
            mock_get_config.return_value = typed_config

            command = env.to_command()

            assert "-o /tmp/strace.log" in command


class TestStraceAnalysisCommands:
    """Test suite for strace analysis and post-processing."""

    @patch(
        "panther.plugins.environments.execution_environment.base_execution_environment.BaseExecutionEnvironment.standardized_environment_initialization"
    )
    def test_add_strace_analysis_commands_basic(
        self, mock_std_init, temp_output_dir, event_manager
    ):
        """Test basic strace analysis command generation."""
        config = StraceConfig()
        env = StraceEnvironment(
            env_config_to_test=config,
            output_dir=temp_output_dir,
            env_type="execution",
            env_sub_type="strace",
            event_manager=event_manager,
        )

        # Create mock command builder
        mock_builder = Mock()
        mock_builder.service_name = "test_service"

        env._add_strace_analysis_commands(
            mock_builder, "/tmp/strace.log", "/tmp/summary.txt"
        )

        # Verify post-processing was added
        mock_builder.add_post_processing.assert_called_once()

        # Verify the post-processing command content
        call_args = mock_builder.add_post_processing.call_args
        processing_command = call_args[1]["processing_command"]

        assert "Strace Analysis for test_service" in processing_command
        assert "Top 20 System Calls" in processing_command
        assert "Network Activity Summary" in processing_command
        assert "Error Analysis" in processing_command
        assert "Performance Insights" in processing_command
        assert "/tmp/strace.log" in processing_command
        assert "/tmp/summary.txt" in processing_command

    @patch(
        "panther.plugins.environments.execution_environment.base_execution_environment.BaseExecutionEnvironment.standardized_environment_initialization"
    )
    def test_add_strace_analysis_commands_with_detailed_analysis(
        self, mock_std_init, temp_output_dir, event_manager
    ):
        """Test strace analysis with detailed analysis enabled."""
        config = StraceConfig()
        config.plugin_config = {"generate_detailed_analysis": True}

        env = StraceEnvironment(
            env_config_to_test=config,
            output_dir=temp_output_dir,
            env_type="execution",
            env_sub_type="strace",
            event_manager=event_manager,
        )

        # Create mock command builder
        mock_builder = Mock()
        mock_builder.service_name = "test_service"
        mock_builder.register_output_file.return_value = "/tmp/detailed.txt"

        env._add_strace_analysis_commands(
            mock_builder, "/tmp/strace.log", "/tmp/summary.txt"
        )

        # Verify both basic and detailed post-processing were added
        assert mock_builder.add_post_processing.call_count == 2

        # Verify detailed file was registered
        mock_builder.register_output_file.assert_called_once_with(
            file_type="strace_detailed",
            extension="detailed.txt",
            description="Detailed strace analysis",
        )

    @patch(
        "panther.plugins.environments.execution_environment.base_execution_environment.BaseExecutionEnvironment.standardized_environment_initialization"
    )
    def test_add_strace_analysis_commands_typed_config_fallback(
        self, mock_std_init, temp_output_dir, event_manager
    ):
        """Test strace analysis with typed config fallback for detailed analysis."""
        config = StraceConfig()
        env = StraceEnvironment(
            env_config_to_test=config,
            output_dir=temp_output_dir,
            env_type="execution",
            env_sub_type="strace",
            event_manager=event_manager,
        )

        # Mock typed config with generate_detailed_analysis attribute
        with patch.object(env, "_get_plugin_config") as mock_get_config:
            typed_config = Mock()
            typed_config.generate_detailed_analysis = True
            mock_get_config.return_value = typed_config

            # Create mock command builder
            mock_builder = Mock()
            mock_builder.service_name = "test_service"
            mock_builder.register_output_file.return_value = "/tmp/detailed.txt"

            env._add_strace_analysis_commands(
                mock_builder, "/tmp/strace.log", "/tmp/summary.txt"
            )

            # Should generate detailed analysis
            assert mock_builder.add_post_processing.call_count == 2


class TestStracePluginSpecificSetup:
    """Test suite for plugin-specific environment setup."""

    def create_mock_service(self, service_name="test_service", has_run_cmd=True):
        """Helper to create mock service."""
        service = Mock(spec=IServiceManager)
        service.service_name = service_name
        if has_run_cmd:
            service.run_cmd = {"pre_run_cmds": []}
        return service

    @patch(
        "panther.plugins.environments.execution_environment.strace.strace.create_execution_environment_builder"
    )
    @patch(
        "panther.plugins.environments.execution_environment.base_execution_environment.BaseExecutionEnvironment.standardized_environment_initialization"
    )
    def test_setup_plugin_specific_environment_single_service(
        self, mock_std_init, mock_builder, temp_output_dir, event_manager
    ):
        """Test setup with single service."""
        config = StraceConfig()
        env = StraceEnvironment(
            env_config_to_test=config,
            output_dir=temp_output_dir,
            env_type="execution",
            env_sub_type="strace",
            event_manager=event_manager,
        )

        # Setup mock command builder
        mock_cmd_builder = Mock()
        mock_cmd_builder.register_output_file.side_effect = [
            "/tmp/strace.log",
            "/tmp/summary.txt",
        ]
        mock_cmd_builder.service_name = "test_service"
        mock_cmd_builder.build_and_apply.return_value = ["command1", "command2"]
        mock_builder.return_value = mock_cmd_builder

        # Create mock service
        service = self.create_mock_service()

        with patch.object(env, "register_output_file") as mock_register:
            with patch.object(env, "modify_service_commands") as mock_modify:
                env._setup_plugin_specific_environment([service], "test_timestamp")

                # Verify builder was created correctly
                mock_builder.assert_called_once_with(
                    service=service,
                    environment_name="strace",
                    timestamp="test_timestamp",
                    register_output_callback=mock_register,
                    logger=env.logger,
                )

                # Verify output files were registered
                assert mock_cmd_builder.register_output_file.call_count == 2

                # Verify wrapper command was added
                mock_cmd_builder.add_wrapper_command.assert_called_once()

                # Verify post-processing was added
                mock_cmd_builder.add_post_processing.assert_called()

                # Verify build_and_apply was called
                mock_cmd_builder.build_and_apply.assert_called_once_with(mock_modify)

    @patch(
        "panther.plugins.environments.execution_environment.strace.strace.create_execution_environment_builder"
    )
    @patch(
        "panther.plugins.environments.execution_environment.base_execution_environment.BaseExecutionEnvironment.standardized_environment_initialization"
    )
    def test_setup_multiple_services(
        self, mock_std_init, mock_builder, temp_output_dir, event_manager
    ):
        """Test setup with multiple services."""
        config = StraceConfig()
        env = StraceEnvironment(
            env_config_to_test=config,
            output_dir=temp_output_dir,
            env_type="execution",
            env_sub_type="strace",
            event_manager=event_manager,
        )

        # Setup mock command builder
        mock_cmd_builder = Mock()
        mock_cmd_builder.register_output_file.side_effect = [
            "/tmp/strace1.log",
            "/tmp/summary1.txt",  # First service
            "/tmp/strace2.log",
            "/tmp/summary2.txt",  # Second service
            "/tmp/strace3.log",
            "/tmp/summary3.txt",  # Third service
        ]
        mock_cmd_builder.service_name = "test_service"
        mock_builder.return_value = mock_cmd_builder

        # Create multiple services
        services = [
            self.create_mock_service("service1"),
            self.create_mock_service("service2"),
            self.create_mock_service("service3"),
        ]

        with patch.object(env, "register_output_file"):
            with patch.object(env, "modify_service_commands"):
                env._setup_plugin_specific_environment(services, "test_timestamp")

                # Should create builder for all 3 services
                assert mock_builder.call_count == 3

    @patch(
        "panther.plugins.environments.execution_environment.strace.strace.create_execution_environment_builder"
    )
    @patch(
        "panther.plugins.environments.execution_environment.base_execution_environment.BaseExecutionEnvironment.standardized_environment_initialization"
    )
    def test_setup_empty_services_list(
        self, mock_std_init, mock_builder, temp_output_dir, event_manager
    ):
        """Test setup with empty services list."""
        config = StraceConfig()
        env = StraceEnvironment(
            env_config_to_test=config,
            output_dir=temp_output_dir,
            env_type="execution",
            env_sub_type="strace",
            event_manager=event_manager,
        )

        env._setup_plugin_specific_environment([], "test_timestamp")

        # Should not create any builders
        mock_builder.assert_not_called()

    @patch(
        "panther.plugins.environments.execution_environment.strace.strace.create_execution_environment_builder"
    )
    @patch(
        "panther.plugins.environments.execution_environment.base_execution_environment.BaseExecutionEnvironment.standardized_environment_initialization"
    )
    def test_setup_service_debugging_logs(
        self, mock_std_init, mock_builder, temp_output_dir, event_manager
    ):
        """Test that setup generates comprehensive debug logs."""
        config = StraceConfig()
        env = StraceEnvironment(
            env_config_to_test=config,
            output_dir=temp_output_dir,
            env_type="execution",
            env_sub_type="strace",
            event_manager=event_manager,
        )

        # Setup mock command builder
        mock_cmd_builder = Mock()
        mock_cmd_builder.register_output_file.side_effect = [
            "/tmp/strace.log",
            "/tmp/summary.txt",
        ]
        mock_cmd_builder.service_name = "test_service"
        mock_cmd_builder.build_and_apply.return_value = []
        mock_builder.return_value = mock_cmd_builder

        service = self.create_mock_service()

        with patch.object(env, "register_output_file"):
            with patch.object(env, "modify_service_commands"):
                with patch.object(env, "logger") as mock_logger:
                    env._setup_plugin_specific_environment([service], "test_timestamp")

                    # Verify comprehensive logging occurred
                    assert mock_logger.info.call_count >= 4  # Multiple info messages
                    assert mock_logger.debug.call_count >= 8  # Multiple debug messages

                    # Check for specific log messages
                    log_calls = [
                        call.args[0] for call in mock_logger.info.call_args_list
                    ]
                    assert any(
                        "Setting up strace environment" in msg for msg in log_calls
                    )
                    assert any(
                        "Configuring strace for service" in msg for msg in log_calls
                    )


class TestStraceEnvironmentUpdates:
    """Test suite for environment update functionality."""

    @patch(
        "panther.plugins.environments.execution_environment.base_execution_environment.BaseExecutionEnvironment.standardized_environment_initialization"
    )
    def test_update_environment(self, mock_std_init, temp_output_dir, event_manager):
        """Test environment update functionality."""
        config = StraceConfig()
        env = StraceEnvironment(
            env_config_to_test=config,
            output_dir=temp_output_dir,
            env_type="execution",
            env_sub_type="strace",
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
                "Updated environment for strace execution"
            )


class TestStraceErrorHandling:
    """Test suite for error handling and edge cases."""

    @patch(
        "panther.plugins.environments.execution_environment.base_execution_environment.BaseExecutionEnvironment.standardized_environment_initialization"
    )
    def test_service_without_service_name_attribute(
        self, mock_std_init, temp_output_dir, event_manager
    ):
        """Test handling service without service_name attribute."""
        config = StraceConfig()
        env = StraceEnvironment(
            env_config_to_test=config,
            output_dir=temp_output_dir,
            env_type="execution",
            env_sub_type="strace",
            event_manager=event_manager,
        )

        # Create service without service_name attribute
        service = Mock(spec=IServiceManager)
        del service.service_name  # Remove service_name attribute
        service.__class__.__name__ = "TestStraceServiceManager"

        with patch(
            "panther.plugins.environments.execution_environment.strace.strace.create_execution_environment_builder"
        ) as mock_builder:
            mock_cmd_builder = Mock()
            mock_cmd_builder.register_output_file.side_effect = [
                "/tmp/strace.log",
                "/tmp/summary.txt",
            ]
            mock_cmd_builder.service_name = "TestStraceServiceManager"
            mock_builder.return_value = mock_cmd_builder

            with patch.object(env, "register_output_file"):
                with patch.object(env, "modify_service_commands"):
                    with patch.object(env, "logger") as mock_logger:
                        env._setup_plugin_specific_environment(
                            [service], "test_timestamp"
                        )

                        # Should handle missing service_name gracefully
                        log_calls = [
                            call.args for call in mock_logger.debug.call_args_list
                        ]
                        assert any(
                            "TestStraceServiceManager" in str(args)
                            for args in log_calls
                        )

    @patch(
        "panther.plugins.environments.execution_environment.base_execution_environment.BaseExecutionEnvironment.standardized_environment_initialization"
    )
    def test_config_with_none_values(
        self, mock_std_init, temp_output_dir, event_manager
    ):
        """Test configuration with None values."""
        config = StraceConfig(timeout=None, additional_parameters=None)

        env = StraceEnvironment(
            env_config_to_test=config,
            output_dir=temp_output_dir,
            env_type="execution",
            env_sub_type="strace",
            event_manager=event_manager,
        )

        command = env._build_strace_command("/tmp/strace.log")

        # Should handle None values gracefully
        assert "/usr/bin/strace" in command
        assert "-o /tmp/strace.log" in command
        # Should not include None timeout or parameters
        assert "timeout None" not in command


@pytest.mark.unit
class TestStraceIntegration:
    """Integration-like tests within unit test scope."""

    @patch(
        "panther.plugins.environments.execution_environment.base_execution_environment.BaseExecutionEnvironment.standardized_environment_initialization"
    )
    def test_full_workflow_simulation(
        self, mock_std_init, temp_output_dir, event_manager
    ):
        """Test a full workflow simulation."""
        config = StraceConfig(
            strace_binary="/usr/bin/strace",
            timeout=30,
            include_kernel_stack=True,
            trace_network_syscalls=True,
            excluded_syscalls=["nanosleep", "gettimeofday"],
            additional_parameters=["-f"],
        )
        config.plugin_config = {
            "timeout": 30,
            "include_kernel_stack": True,
            "trace_network_syscalls": True,
            "excluded_syscalls": ["nanosleep", "gettimeofday"],
            "additional_parameters": ["-f"],
        }

        env = StraceEnvironment(
            env_config_to_test=config,
            output_dir=temp_output_dir,
            env_type="execution",
            env_sub_type="strace",
            event_manager=event_manager,
        )

        # Test command generation
        command = env._build_strace_command("/tmp/test_strace.log")

        assert "mkdir -p /tmp" in command
        assert "/usr/bin/strace" in command
        assert "-o /tmp/test_strace.log" in command
        assert "-k" in command  # Kernel stack
        assert "timeout 30" in command
        assert "-e trace=!nanosleep,gettimeofday" in command
        assert (
            "-e trace=network,read,write,send,recv,connect,bind,listen,accept"
            in command
        )
        assert "-f" in command  # Additional parameter

        # Test to_command interface
        cmd_interface = env.to_command(output_file="/tmp/interface_test.log")
        assert "-o /tmp/interface_test.log" in cmd_interface

        # Test output patterns
        patterns = env.get_output_patterns()
        assert len(patterns) == 4
        assert ("strace_log", "strace_{service_name}.log") in patterns

        # Test additional patterns
        additional = env.get_additional_output_discovery_patterns()
        assert "strace_child" in additional
        assert "strace_error" in additional

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
