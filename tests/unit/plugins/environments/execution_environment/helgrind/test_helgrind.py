"""
Comprehensive unit tests for HelgrindEnvironment.

Tests thread error detection functionality, configuration handling, and command generation.
"""

from pathlib import Path
from typing import List
from unittest.mock import MagicMock, Mock, call, patch

import pytest

from panther.config.core.models.global_config import GlobalConfig
from panther.core.observer.management.event_manager import EventManager
from panther.plugins.environments.config_schema import EnvironmentConfig
from panther.plugins.environments.execution_environment.helgrind.config_schema import (
    HelgrindConfig,
)
from panther.plugins.environments.execution_environment.helgrind.helgrind import (
    HelgrindEnvironment,
)
from panther.plugins.services.services_interface import IServiceManager


class TestHelgrindEnvironmentInitialization:
    """Test suite for HelgrindEnvironment initialization."""

    @patch(
        "panther.plugins.environments.execution_environment.base_execution_environment.BaseExecutionEnvironment.standardized_environment_initialization"
    )
    def test_basic_initialization(self, mock_std_init, temp_output_dir, event_manager):
        """Test basic HelgrindEnvironment initialization."""
        config = HelgrindConfig()

        env = HelgrindEnvironment(
            env_config_to_test=config,
            output_dir=temp_output_dir,
            env_type="execution",
            env_sub_type="helgrind",
            event_manager=event_manager,
        )

        assert env.env_config_to_test == config
        assert env.output_dir == temp_output_dir
        assert env.env_type == "execution"
        assert env.env_sub_type == "helgrind"
        assert env.event_manager == event_manager
        assert env._cached_plugin_config is None  # Should be lazy-loaded

    @patch(
        "panther.plugins.environments.execution_environment.base_execution_environment.BaseExecutionEnvironment.standardized_environment_initialization"
    )
    def test_plugin_registration_decorator(
        self, mock_std_init, temp_output_dir, event_manager
    ):
        """Test that plugin is properly decorated with registration info."""
        # Check if the plugin decorator was applied
        assert hasattr(HelgrindEnvironment, "_PLUGIN_MANIFEST")

        manifest = HelgrindEnvironment._PLUGIN_MANIFEST
        assert manifest.name == "helgrind"
        assert manifest.version == "1.0.0"
        assert (
            manifest.description
            == "Valgrind Helgrind thread error detection environment"
        )
        assert "thread_error_detection" in manifest.capabilities
        assert "race_condition_analysis" in manifest.capabilities
        assert "deadlock_detection" in manifest.capabilities
        assert "valgrind>=3.15" in manifest.external_dependencies

    @patch(
        "panther.plugins.environments.execution_environment.base_execution_environment.BaseExecutionEnvironment.standardized_environment_initialization"
    )
    def test_inheritance_chain(self, mock_std_init, temp_output_dir, event_manager):
        """Test that HelgrindEnvironment has correct inheritance."""
        from panther.plugins.environments.execution_environment.base_execution_environment import (
            BaseExecutionEnvironment,
        )

        config = HelgrindConfig()
        env = HelgrindEnvironment(
            env_config_to_test=config,
            output_dir=temp_output_dir,
            env_type="execution",
            env_sub_type="helgrind",
            event_manager=event_manager,
        )

        assert isinstance(env, BaseExecutionEnvironment)
        assert isinstance(env, HelgrindEnvironment)


class TestHelgrindConfigurationHandling:
    """Test suite for configuration handling with dual approach."""

    @patch(
        "panther.plugins.environments.execution_environment.base_execution_environment.BaseExecutionEnvironment.standardized_environment_initialization"
    )
    def test_get_plugin_config_caching(
        self, mock_std_init, temp_output_dir, event_manager
    ):
        """Test that plugin config is cached correctly."""
        config = HelgrindConfig(conflict_cache_size=2000000)

        env = HelgrindEnvironment(
            env_config_to_test=config,
            output_dir=temp_output_dir,
            env_type="execution",
            env_sub_type="helgrind",
            event_manager=event_manager,
        )
        env.env_config_to_test = config

        # First call should retrieve and cache the plugin config
        plugin_config1 = env._get_plugin_config()
        assert plugin_config1 is not None
        assert env._cached_plugin_config is not None

        # Second call should use cached value (same object)
        plugin_config2 = env._get_plugin_config()
        assert plugin_config1 is plugin_config2
        assert plugin_config1.conflict_cache_size == 2000000

    @patch(
        "panther.plugins.environments.execution_environment.base_execution_environment.BaseExecutionEnvironment.standardized_environment_initialization"
    )
    def test_get_plugin_config_exception_fallback(
        self, mock_std_init, temp_output_dir, event_manager
    ):
        """Test fallback to default config when get_plugin_config fails."""
        config = HelgrindConfig()

        with patch.object(
            config, "get_plugin_config", side_effect=Exception("Config error")
        ):
            env = HelgrindEnvironment(
                env_config_to_test=config,
                output_dir=temp_output_dir,
                env_type="execution",
                env_sub_type="helgrind",
                event_manager=event_manager,
            )
            env.env_config_to_test = config

            plugin_config = env._get_plugin_config()

            # Should return default config
            assert isinstance(plugin_config, HelgrindConfig)
            assert plugin_config.conflict_cache_size == 1000000  # Default value


class TestHelgrindCommandGeneration:
    """Test suite for helgrind command generation."""

    @patch(
        "panther.plugins.environments.execution_environment.base_execution_environment.BaseExecutionEnvironment.standardized_environment_initialization"
    )
    def test_build_helgrind_command_basic(
        self, mock_std_init, temp_output_dir, event_manager
    ):
        """Test basic helgrind command generation."""
        config = HelgrindConfig()
        env = HelgrindEnvironment(
            env_config_to_test=config,
            output_dir=temp_output_dir,
            env_type="execution",
            env_sub_type="helgrind",
            event_manager=event_manager,
        )

        command = env._build_helgrind_command("/tmp/helgrind.log")

        # Check basic command structure
        assert "/usr/bin/valgrind" in command
        assert "--tool=helgrind" in command
        assert "--log-file=/tmp/helgrind.log" in command
        assert "--history-level=full" in command
        assert "--conflict-cache-size=1000000" in command
        assert "--cache-size=32M" in command

    @patch(
        "panther.plugins.environments.execution_environment.base_execution_environment.BaseExecutionEnvironment.standardized_environment_initialization"
    )
    def test_build_helgrind_command_with_xml_output(
        self, mock_std_init, temp_output_dir, event_manager
    ):
        """Test helgrind command generation with XML output format."""
        config = HelgrindConfig()
        config.plugin_config = {"output_format": "xml"}

        env = HelgrindEnvironment(
            env_config_to_test=config,
            output_dir=temp_output_dir,
            env_type="execution",
            env_sub_type="helgrind",
            event_manager=event_manager,
        )

        command = env._build_helgrind_command("/tmp/helgrind.log")

        assert "--xml=yes" in command
        assert "--xml-file=/tmp/helgrind.log.xml" in command

    @patch(
        "panther.plugins.environments.execution_environment.base_execution_environment.BaseExecutionEnvironment.standardized_environment_initialization"
    )
    def test_build_helgrind_command_with_history_level(
        self, mock_std_init, temp_output_dir, event_manager
    ):
        """Test helgrind command generation with custom history level."""
        config = HelgrindConfig()
        config.plugin_config = {"history_level": "approx"}

        env = HelgrindEnvironment(
            env_config_to_test=config,
            output_dir=temp_output_dir,
            env_type="execution",
            env_sub_type="helgrind",
            event_manager=event_manager,
        )

        command = env._build_helgrind_command("/tmp/helgrind.log")

        assert "--history-level=approx" in command

    @patch(
        "panther.plugins.environments.execution_environment.base_execution_environment.BaseExecutionEnvironment.standardized_environment_initialization"
    )
    def test_build_helgrind_command_with_track_lockorders_disabled(
        self, mock_std_init, temp_output_dir, event_manager
    ):
        """Test helgrind command generation with lock order tracking disabled."""
        config = HelgrindConfig()
        config.plugin_config = {"track_lockorders": False}

        env = HelgrindEnvironment(
            env_config_to_test=config,
            output_dir=temp_output_dir,
            env_type="execution",
            env_sub_type="helgrind",
            event_manager=event_manager,
        )

        command = env._build_helgrind_command("/tmp/helgrind.log")

        assert "--track-lockorders=no" in command

    @patch(
        "panther.plugins.environments.execution_environment.base_execution_environment.BaseExecutionEnvironment.standardized_environment_initialization"
    )
    def test_build_helgrind_command_with_stack_refs_disabled(
        self, mock_std_init, temp_output_dir, event_manager
    ):
        """Test helgrind command generation with stack reference checking disabled."""
        config = HelgrindConfig()
        config.plugin_config = {"check_stack_refs": False}

        env = HelgrindEnvironment(
            env_config_to_test=config,
            output_dir=temp_output_dir,
            env_type="execution",
            env_sub_type="helgrind",
            event_manager=event_manager,
        )

        command = env._build_helgrind_command("/tmp/helgrind.log")

        assert "--check-stack-refs=no" in command

    @patch(
        "panther.plugins.environments.execution_environment.base_execution_environment.BaseExecutionEnvironment.standardized_environment_initialization"
    )
    def test_build_helgrind_command_with_thread_creation_ignore(
        self, mock_std_init, temp_output_dir, event_manager
    ):
        """Test helgrind command generation with thread creation races ignored."""
        config = HelgrindConfig()
        config.plugin_config = {"ignore_thread_creation": True}

        env = HelgrindEnvironment(
            env_config_to_test=config,
            output_dir=temp_output_dir,
            env_type="execution",
            env_sub_type="helgrind",
            event_manager=event_manager,
        )

        command = env._build_helgrind_command("/tmp/helgrind.log")

        assert "--ignore-thread-creation=yes" in command

    @patch(
        "panther.plugins.environments.execution_environment.base_execution_environment.BaseExecutionEnvironment.standardized_environment_initialization"
    )
    def test_build_helgrind_command_with_free_is_write(
        self, mock_std_init, temp_output_dir, event_manager
    ):
        """Test helgrind command generation with free-as-write option."""
        config = HelgrindConfig()
        config.plugin_config = {"free_is_write": True}

        env = HelgrindEnvironment(
            env_config_to_test=config,
            output_dir=temp_output_dir,
            env_type="execution",
            env_sub_type="helgrind",
            event_manager=event_manager,
        )

        command = env._build_helgrind_command("/tmp/helgrind.log")

        assert "--free-is-write=yes" in command

    @patch(
        "panther.plugins.environments.execution_environment.base_execution_environment.BaseExecutionEnvironment.standardized_environment_initialization"
    )
    def test_build_helgrind_command_with_cache_size(
        self, mock_std_init, temp_output_dir, event_manager
    ):
        """Test helgrind command generation with custom cache size."""
        config = HelgrindConfig()
        config.plugin_config = {"cache_size": 64}

        env = HelgrindEnvironment(
            env_config_to_test=config,
            output_dir=temp_output_dir,
            env_type="execution",
            env_sub_type="helgrind",
            event_manager=event_manager,
        )

        command = env._build_helgrind_command("/tmp/helgrind.log")

        assert "--cache-size=64M" in command

    @patch(
        "panther.plugins.environments.execution_environment.base_execution_environment.BaseExecutionEnvironment.standardized_environment_initialization"
    )
    def test_build_helgrind_command_with_suppression_file(
        self, mock_std_init, temp_output_dir, event_manager
    ):
        """Test helgrind command generation with suppression file."""
        config = HelgrindConfig()
        config.plugin_config = {"suppression_file": "/tmp/suppressions.supp"}

        env = HelgrindEnvironment(
            env_config_to_test=config,
            output_dir=temp_output_dir,
            env_type="execution",
            env_sub_type="helgrind",
            event_manager=event_manager,
        )

        command = env._build_helgrind_command("/tmp/helgrind.log")

        assert "--suppressions=/tmp/suppressions.supp" in command

    @patch(
        "panther.plugins.environments.execution_environment.base_execution_environment.BaseExecutionEnvironment.standardized_environment_initialization"
    )
    def test_build_helgrind_command_with_valgrind_options(
        self, mock_std_init, temp_output_dir, event_manager
    ):
        """Test helgrind command generation with additional Valgrind options."""
        config = HelgrindConfig()
        config.plugin_config = {
            "show_below_main": True,
            "track_fds": True,
            "time_stamp": True,
        }

        env = HelgrindEnvironment(
            env_config_to_test=config,
            output_dir=temp_output_dir,
            env_type="execution",
            env_sub_type="helgrind",
            event_manager=event_manager,
        )

        command = env._build_helgrind_command("/tmp/helgrind.log")

        assert "--show-below-main=yes" in command
        assert "--track-fds=yes" in command
        assert "--time-stamp=yes" in command

    @patch(
        "panther.plugins.environments.execution_environment.base_execution_environment.BaseExecutionEnvironment.standardized_environment_initialization"
    )
    def test_build_helgrind_command_with_verbosity(
        self, mock_std_init, temp_output_dir, event_manager
    ):
        """Test helgrind command generation with verbosity level."""
        config = HelgrindConfig()
        config.plugin_config = {"verbosity": 2}

        env = HelgrindEnvironment(
            env_config_to_test=config,
            output_dir=temp_output_dir,
            env_type="execution",
            env_sub_type="helgrind",
            event_manager=event_manager,
        )

        command = env._build_helgrind_command("/tmp/helgrind.log")

        assert "--verbose--verbose" in command  # Two verbose flags for level 2

    @patch(
        "panther.plugins.environments.execution_environment.base_execution_environment.BaseExecutionEnvironment.standardized_environment_initialization"
    )
    def test_build_helgrind_command_with_additional_parameters(
        self, mock_std_init, temp_output_dir, event_manager
    ):
        """Test helgrind command generation with additional parameters."""
        config = HelgrindConfig()
        config.plugin_config = {
            "additional_parameters": ["--show-reachable=yes", "--leak-check=full"]
        }

        env = HelgrindEnvironment(
            env_config_to_test=config,
            output_dir=temp_output_dir,
            env_type="execution",
            env_sub_type="helgrind",
            event_manager=event_manager,
        )

        command = env._build_helgrind_command("/tmp/helgrind.log")

        assert "--show-reachable=yes" in command
        assert "--leak-check=full" in command

    @patch(
        "panther.plugins.environments.execution_environment.base_execution_environment.BaseExecutionEnvironment.standardized_environment_initialization"
    )
    def test_build_helgrind_command_typed_config_fallback(
        self, mock_std_init, temp_output_dir, event_manager
    ):
        """Test helgrind command generation with typed config fallback."""
        config = HelgrindConfig(
            history_level="approx", conflict_cache_size=5000000, track_lockorders=False
        )

        env = HelgrindEnvironment(
            env_config_to_test=config,
            output_dir=temp_output_dir,
            env_type="execution",
            env_sub_type="helgrind",
            event_manager=event_manager,
        )

        # Mock typed config to test fallback
        with patch.object(env, "_get_plugin_config") as mock_get_config:
            typed_config = HelgrindConfig()
            typed_config.history_level = "approx"
            typed_config.conflict_cache_size = 5000000
            typed_config.track_lockorders = False
            mock_get_config.return_value = typed_config

            command = env._build_helgrind_command("/tmp/helgrind.log")

            assert "--history-level=approx" in command
            assert "--conflict-cache-size=5000000" in command
            assert "--track-lockorders=no" in command


class TestHelgrindCommandInterface:
    """Test suite for to_command interface."""

    @patch(
        "panther.plugins.environments.execution_environment.base_execution_environment.BaseExecutionEnvironment.standardized_environment_initialization"
    )
    def test_to_command_basic(self, mock_std_init, temp_output_dir, event_manager):
        """Test basic to_command functionality."""
        config = HelgrindConfig()
        env = HelgrindEnvironment(
            env_config_to_test=config,
            output_dir=temp_output_dir,
            env_type="execution",
            env_sub_type="helgrind",
            event_manager=event_manager,
        )

        command = env.to_command(output_file="/tmp/test_helgrind.log")

        assert "/usr/bin/valgrind" in command
        assert "--tool=helgrind" in command
        assert "--log-file=/tmp/test_helgrind.log" in command

    @patch(
        "panther.plugins.environments.execution_environment.base_execution_environment.BaseExecutionEnvironment.standardized_environment_initialization"
    )
    def test_to_command_default_output_file(
        self, mock_std_init, temp_output_dir, event_manager
    ):
        """Test to_command with default output file."""
        config = HelgrindConfig(output_file="/custom/helgrind.log")
        env = HelgrindEnvironment(
            env_config_to_test=config,
            output_dir=temp_output_dir,
            env_type="execution",
            env_sub_type="helgrind",
            event_manager=event_manager,
        )

        command = env.to_command()

        assert "--log-file=/custom/helgrind.log" in command

    @patch(
        "panther.plugins.environments.execution_environment.base_execution_environment.BaseExecutionEnvironment.standardized_environment_initialization"
    )
    def test_to_command_fallback_default(
        self, mock_std_init, temp_output_dir, event_manager
    ):
        """Test to_command fallback to absolute default."""
        config = HelgrindConfig()
        env = HelgrindEnvironment(
            env_config_to_test=config,
            output_dir=temp_output_dir,
            env_type="execution",
            env_sub_type="helgrind",
            event_manager=event_manager,
        )

        # Use default config without output_file override - falls back to env_config default
        command = env.to_command()

        # Falls back to env_config_to_test.output_file or absolute default
        assert "--log-file=" in command

    @patch(
        "panther.plugins.environments.execution_environment.base_execution_environment.BaseExecutionEnvironment.standardized_environment_initialization"
    )
    def test_to_command_with_pid_warning(
        self, mock_std_init, temp_output_dir, event_manager
    ):
        """Test to_command logs warning when PID is provided."""
        config = HelgrindConfig()
        env = HelgrindEnvironment(
            env_config_to_test=config,
            output_dir=temp_output_dir,
            env_type="execution",
            env_sub_type="helgrind",
            event_manager=event_manager,
        )

        mock_logger = MagicMock()
        env._logger = mock_logger

        command = env.to_command(pid=1234)

        # Should log warning about PID not being supported
        mock_logger.warning.assert_called_once()
        assert "PID parameter" in str(mock_logger.warning.call_args)
        assert "1234" in str(mock_logger.warning.call_args)


class TestHelgrindAnalysisCommands:
    """Test suite for helgrind analysis and post-processing."""

    @patch(
        "panther.plugins.environments.execution_environment.base_execution_environment.BaseExecutionEnvironment.standardized_environment_initialization"
    )
    def test_add_helgrind_analysis_commands_basic(
        self, mock_std_init, temp_output_dir, event_manager
    ):
        """Test basic helgrind analysis command generation."""
        config = HelgrindConfig()
        env = HelgrindEnvironment(
            env_config_to_test=config,
            output_dir=temp_output_dir,
            env_type="execution",
            env_sub_type="helgrind",
            event_manager=event_manager,
        )

        # Create mock command builder
        mock_builder = Mock()
        mock_builder.service_name = "test_service"

        env._add_helgrind_analysis_commands(
            mock_builder, "/tmp/helgrind.log", "/tmp/helgrind_summary.txt"
        )

        # Verify post-processing was added
        mock_builder.add_post_processing.assert_called_once()

        # Verify the post-processing command content
        call_args = mock_builder.add_post_processing.call_args
        processing_command = call_args[1]["processing_command"]

        assert "Helgrind Thread Error Analysis for test_service" in processing_command
        assert "Thread Error Summary" in processing_command
        assert "Data race detections" in processing_command
        assert "Lock order violations" in processing_command
        assert "Thread API misuse" in processing_command
        assert "Data Race Details" in processing_command
        assert "Lock Order Analysis" in processing_command
        assert "Thread Synchronization Issues" in processing_command
        assert "Error Severity Assessment" in processing_command
        assert "/tmp/helgrind.log" in processing_command
        assert "/tmp/helgrind_summary.txt" in processing_command

    @patch(
        "panther.plugins.environments.execution_environment.base_execution_environment.BaseExecutionEnvironment.standardized_environment_initialization"
    )
    def test_add_helgrind_analysis_commands_with_detailed_analysis(
        self, mock_std_init, temp_output_dir, event_manager
    ):
        """Test helgrind analysis with detailed analysis enabled."""
        config = HelgrindConfig()
        config.plugin_config = {"generate_detailed_analysis": True}

        env = HelgrindEnvironment(
            env_config_to_test=config,
            output_dir=temp_output_dir,
            env_type="execution",
            env_sub_type="helgrind",
            event_manager=event_manager,
        )

        # Create mock command builder
        mock_builder = Mock()
        mock_builder.service_name = "test_service"
        mock_builder.register_output_file.return_value = "/tmp/helgrind_detailed.txt"

        env._add_helgrind_analysis_commands(
            mock_builder, "/tmp/helgrind.log", "/tmp/helgrind_summary.txt"
        )

        # Verify both basic and detailed post-processing were added
        assert mock_builder.add_post_processing.call_count == 2

        # Verify detailed file was registered
        mock_builder.register_output_file.assert_called_once_with(
            file_type="helgrind_detailed",
            extension="detailed.txt",
            description="Detailed Helgrind race condition analysis",
        )

    @patch(
        "panther.plugins.environments.execution_environment.base_execution_environment.BaseExecutionEnvironment.standardized_environment_initialization"
    )
    def test_add_helgrind_analysis_commands_typed_config_fallback(
        self, mock_std_init, temp_output_dir, event_manager
    ):
        """Test helgrind analysis with typed config fallback for detailed analysis."""
        config = HelgrindConfig()
        env = HelgrindEnvironment(
            env_config_to_test=config,
            output_dir=temp_output_dir,
            env_type="execution",
            env_sub_type="helgrind",
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
            mock_builder.register_output_file.return_value = (
                "/tmp/helgrind_detailed.txt"
            )

            env._add_helgrind_analysis_commands(
                mock_builder, "/tmp/helgrind.log", "/tmp/helgrind_summary.txt"
            )

            # Should generate detailed analysis
            assert mock_builder.add_post_processing.call_count == 2


class TestHelgrindPluginSpecificSetup:
    """Test suite for plugin-specific environment setup."""

    def create_mock_service(self, service_name="test_service", has_run_cmd=True):
        """Helper to create mock service."""
        service = Mock(spec=IServiceManager)
        service.service_name = service_name
        if has_run_cmd:
            service.run_cmd = {"pre_run_cmds": []}
        return service

    @patch(
        "panther.plugins.environments.execution_environment.helgrind.helgrind.create_execution_environment_builder"
    )
    @patch(
        "panther.plugins.environments.execution_environment.base_execution_environment.BaseExecutionEnvironment.standardized_environment_initialization"
    )
    def test_setup_plugin_specific_environment_single_service(
        self, mock_std_init, mock_builder, temp_output_dir, event_manager
    ):
        """Test setup with single service."""
        config = HelgrindConfig()
        env = HelgrindEnvironment(
            env_config_to_test=config,
            output_dir=temp_output_dir,
            env_type="execution",
            env_sub_type="helgrind",
            event_manager=event_manager,
        )

        # Setup mock command builder
        mock_cmd_builder = Mock()
        mock_cmd_builder.register_output_file.side_effect = [
            "/tmp/helgrind.log",
            "/tmp/helgrind_summary.txt",
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
                    environment_name="helgrind",
                    timestamp="test_timestamp",
                    register_output_callback=mock_register,
                    logger=env.logger,
                )

                # Verify output files were registered
                assert mock_cmd_builder.register_output_file.call_count == 2

                # Verify first call for helgrind log
                first_call = mock_cmd_builder.register_output_file.call_args_list[0]
                assert first_call[1]["file_type"] == "helgrind_log"
                assert first_call[1]["extension"] == "log"

                # Verify second call for helgrind summary
                second_call = mock_cmd_builder.register_output_file.call_args_list[1]
                assert second_call[1]["file_type"] == "helgrind_summary"
                assert second_call[1]["extension"] == "txt"

                # Verify conditional wrapper was added
                mock_cmd_builder.add_conditional_wrapper.assert_called_once()

                # Verify post-processing was added
                mock_cmd_builder.add_post_processing.assert_called()

                # Verify build_and_apply was called
                mock_cmd_builder.build_and_apply.assert_called_once_with(mock_modify)

    @patch(
        "panther.plugins.environments.execution_environment.helgrind.helgrind.create_execution_environment_builder"
    )
    @patch(
        "panther.plugins.environments.execution_environment.base_execution_environment.BaseExecutionEnvironment.standardized_environment_initialization"
    )
    def test_setup_multiple_services(
        self, mock_std_init, mock_builder, temp_output_dir, event_manager
    ):
        """Test setup with multiple services."""
        config = HelgrindConfig()
        env = HelgrindEnvironment(
            env_config_to_test=config,
            output_dir=temp_output_dir,
            env_type="execution",
            env_sub_type="helgrind",
            event_manager=event_manager,
        )

        # Setup mock command builder
        mock_cmd_builder = Mock()
        mock_cmd_builder.register_output_file.side_effect = [
            "/tmp/helgrind1.log",
            "/tmp/helgrind1_summary.txt",  # First service
            "/tmp/helgrind2.log",
            "/tmp/helgrind2_summary.txt",  # Second service
            "/tmp/helgrind3.log",
            "/tmp/helgrind3_summary.txt",  # Third service
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
        "panther.plugins.environments.execution_environment.helgrind.helgrind.create_execution_environment_builder"
    )
    @patch(
        "panther.plugins.environments.execution_environment.base_execution_environment.BaseExecutionEnvironment.standardized_environment_initialization"
    )
    def test_setup_empty_services_list(
        self, mock_std_init, mock_builder, temp_output_dir, event_manager
    ):
        """Test setup with empty services list."""
        config = HelgrindConfig()
        env = HelgrindEnvironment(
            env_config_to_test=config,
            output_dir=temp_output_dir,
            env_type="execution",
            env_sub_type="helgrind",
            event_manager=event_manager,
        )

        env._setup_plugin_specific_environment([], "test_timestamp")

        # Should not create any builders
        mock_builder.assert_not_called()

    @patch(
        "panther.plugins.environments.execution_environment.helgrind.helgrind.create_execution_environment_builder"
    )
    @patch(
        "panther.plugins.environments.execution_environment.base_execution_environment.BaseExecutionEnvironment.standardized_environment_initialization"
    )
    def test_setup_conditional_wrapper_details(
        self, mock_std_init, mock_builder, temp_output_dir, event_manager
    ):
        """Test that setup uses conditional wrapper for Valgrind availability."""
        config = HelgrindConfig()
        env = HelgrindEnvironment(
            env_config_to_test=config,
            output_dir=temp_output_dir,
            env_type="execution",
            env_sub_type="helgrind",
            event_manager=event_manager,
        )

        # Setup mock command builder
        mock_cmd_builder = Mock()
        mock_cmd_builder.register_output_file.side_effect = [
            "/tmp/helgrind.log",
            "/tmp/helgrind_summary.txt",
        ]
        mock_cmd_builder.service_name = "test_service"
        mock_builder.return_value = mock_cmd_builder

        service = self.create_mock_service()

        with patch.object(env, "register_output_file"):
            with patch.object(env, "modify_service_commands"):
                env._setup_plugin_specific_environment([service], "test_timestamp")

                # Verify conditional wrapper was called with correct parameters
                mock_cmd_builder.add_conditional_wrapper.assert_called_once()
                call_args = mock_cmd_builder.add_conditional_wrapper.call_args

                assert (
                    call_args[1]["condition"] == "command -v valgrind >/dev/null 2>&1"
                )
                assert "valgrind" in call_args[1]["wrapper_command"]
                assert "--tool=helgrind" in call_args[1]["wrapper_command"]
                assert (
                    call_args[1]["fallback_message"]
                    == "Valgrind not found - Helgrind thread error detection disabled"
                )
                assert call_args[1]["is_critical"] is False


class TestHelgrindEnvironmentUpdates:
    """Test suite for environment update functionality."""

    @patch(
        "panther.plugins.environments.execution_environment.base_execution_environment.BaseExecutionEnvironment.standardized_environment_initialization"
    )
    def test_update_environment(self, mock_std_init, temp_output_dir, event_manager):
        """Test environment update functionality."""
        config = HelgrindConfig()
        env = HelgrindEnvironment(
            env_config_to_test=config,
            output_dir=temp_output_dir,
            env_type="execution",
            env_sub_type="helgrind",
            event_manager=event_manager,
        )

        mock_logger = MagicMock()
        env._logger = mock_logger

        env.update_environment(
            execution_environment=Mock(),
            global_config=GlobalConfig(),
            plugin_manager=Mock(),
            services_managers=[],
            test_config=Mock(),
        )

        # Should log debug message
        mock_logger.debug.assert_called_once_with(
            "Updated environment for helgrind execution"
        )


class TestHelgrindErrorHandling:
    """Test suite for error handling and edge cases."""

    @patch(
        "panther.plugins.environments.execution_environment.base_execution_environment.BaseExecutionEnvironment.standardized_environment_initialization"
    )
    def test_service_without_service_name_attribute(
        self, mock_std_init, temp_output_dir, event_manager
    ):
        """Test handling service without service_name attribute."""
        config = HelgrindConfig()
        env = HelgrindEnvironment(
            env_config_to_test=config,
            output_dir=temp_output_dir,
            env_type="execution",
            env_sub_type="helgrind",
            event_manager=event_manager,
        )

        # Create service without service_name attribute
        service = Mock(spec=IServiceManager)
        del service.service_name  # Remove service_name attribute
        service.__class__.__name__ = "TestHelgrindServiceManager"

        with patch(
            "panther.plugins.environments.execution_environment.helgrind.helgrind.create_execution_environment_builder"
        ) as mock_builder:
            mock_cmd_builder = Mock()
            mock_cmd_builder.register_output_file.side_effect = [
                "/tmp/helgrind.log",
                "/tmp/helgrind_summary.txt",
            ]
            mock_cmd_builder.service_name = "TestHelgrindServiceManager"
            mock_builder.return_value = mock_cmd_builder

            with patch.object(env, "register_output_file"):
                with patch.object(env, "modify_service_commands"):
                    env._setup_plugin_specific_environment([service], "test_timestamp")

                    # Should handle missing service_name gracefully using class name
                    mock_builder.assert_called_once()

    @patch(
        "panther.plugins.environments.execution_environment.base_execution_environment.BaseExecutionEnvironment.standardized_environment_initialization"
    )
    def test_config_with_none_values(
        self, mock_std_init, temp_output_dir, event_manager
    ):
        """Test configuration with None values."""
        config = HelgrindConfig(suppression_file=None)

        env = HelgrindEnvironment(
            env_config_to_test=config,
            output_dir=temp_output_dir,
            env_type="execution",
            env_sub_type="helgrind",
            event_manager=event_manager,
        )

        command = env._build_helgrind_command("/tmp/helgrind.log")

        # Should handle None values gracefully
        assert "/usr/bin/valgrind" in command
        assert "--tool=helgrind" in command
        assert "--log-file=/tmp/helgrind.log" in command
        # Should not include None suppression file
        assert "--suppressions=None" not in command

    @patch(
        "panther.plugins.environments.execution_environment.base_execution_environment.BaseExecutionEnvironment.standardized_environment_initialization"
    )
    def test_config_validation_errors(
        self, mock_std_init, temp_output_dir, event_manager
    ):
        """Test configuration validation error handling."""
        # Test invalid output format
        with pytest.raises(ValueError, match="Output format must be one of"):
            HelgrindConfig(output_format="invalid")

        # Test invalid history level
        with pytest.raises(ValueError, match="History level must be one of"):
            HelgrindConfig(history_level="invalid")

        # Test invalid verbosity
        with pytest.raises(ValueError, match="Verbosity must be between 0 and 3"):
            HelgrindConfig(verbosity=5)


@pytest.mark.unit
class TestHelgrindIntegration:
    """Integration-like tests within unit test scope."""

    @patch(
        "panther.plugins.environments.execution_environment.base_execution_environment.BaseExecutionEnvironment.standardized_environment_initialization"
    )
    def test_full_workflow_simulation(
        self, mock_std_init, temp_output_dir, event_manager
    ):
        """Test a full workflow simulation."""
        config = HelgrindConfig(
            valgrind_binary="/usr/bin/valgrind",
            output_format="xml",
            history_level="approx",
            conflict_cache_size=5000000,
            track_lockorders=False,
            check_stack_refs=False,
            ignore_thread_creation=True,
            free_is_write=True,
            cache_size=64,
            suppression_file="/tmp/suppressions.supp",
            show_below_main=True,
            track_fds=True,
            time_stamp=True,
            verbosity=2,
            additional_parameters=["--show-reachable=yes"],
        )
        config.plugin_config = {
            "output_format": "xml",
            "history_level": "approx",
            "conflict_cache_size": 5000000,
            "track_lockorders": False,
            "check_stack_refs": False,
            "ignore_thread_creation": True,
            "free_is_write": True,
            "cache_size": 64,
            "suppression_file": "/tmp/suppressions.supp",
            "show_below_main": True,
            "track_fds": True,
            "time_stamp": True,
            "verbosity": 2,
            "additional_parameters": ["--show-reachable=yes"],
        }

        env = HelgrindEnvironment(
            env_config_to_test=config,
            output_dir=temp_output_dir,
            env_type="execution",
            env_sub_type="helgrind",
            event_manager=event_manager,
        )

        # Test command generation
        command = env._build_helgrind_command("/tmp/test_helgrind.log")

        assert "/usr/bin/valgrind" in command
        assert "--tool=helgrind" in command
        assert "--log-file=/tmp/test_helgrind.log" in command
        assert "--xml=yes" in command
        assert "--xml-file=/tmp/test_helgrind.log.xml" in command
        assert "--history-level=approx" in command
        assert "--conflict-cache-size=5000000" in command
        assert "--track-lockorders=no" in command
        assert "--check-stack-refs=no" in command
        assert "--ignore-thread-creation=yes" in command
        assert "--free-is-write=yes" in command
        assert "--cache-size=64M" in command
        assert "--suppressions=/tmp/suppressions.supp" in command
        assert "--show-below-main=yes" in command
        assert "--track-fds=yes" in command
        assert "--time-stamp=yes" in command
        assert "--verbose--verbose" in command  # Two verbose flags
        assert "--show-reachable=yes" in command

        # Test to_command interface
        cmd_interface = env.to_command(output_file="/tmp/interface_test.log")
        assert "--log-file=/tmp/interface_test.log" in cmd_interface

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
