"""
Comprehensive unit tests for MemcheckEnvironment.

Tests memory error detection functionality, configuration handling, and command generation.
"""
from pathlib import Path
from typing import List
from unittest.mock import MagicMock, Mock, call, patch

import pytest

from panther.config.core.models.global_config import GlobalConfig
from panther.core.observer.management.event_manager import EventManager
from panther.plugins.environments.config_schema import EnvironmentConfig
from panther.plugins.environments.execution_environment.memcheck.config_schema import (
    MemcheckConfig,
)
from panther.plugins.environments.execution_environment.memcheck.memcheck import (
    MemcheckEnvironment,
)
from panther.plugins.services.services_interface import IServiceManager


class TestMemcheckEnvironmentInitialization:
    """Test suite for MemcheckEnvironment initialization."""

    @patch(
        "panther.plugins.environments.execution_environment.base_execution_environment.BaseExecutionEnvironment.standardized_environment_initialization"
    )
    def test_basic_initialization(self, mock_std_init, temp_output_dir, event_manager):
        """Test basic MemcheckEnvironment initialization."""
        config = MemcheckConfig()

        env = MemcheckEnvironment(
            env_config_to_test=config,
            output_dir=temp_output_dir,
            env_type="execution",
            env_sub_type="memcheck",
            event_manager=event_manager,
        )

        assert env.env_config_to_test == config
        assert env.output_dir == temp_output_dir
        assert env.env_type == "execution"
        assert env.env_sub_type == "memcheck"
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
        assert hasattr(MemcheckEnvironment, "_plugin_info")

        plugin_info = MemcheckEnvironment._plugin_info
        assert plugin_info["name"] == "memcheck"
        assert plugin_info["version"] == "1.0.0"
        assert (
            plugin_info["description"]
            == "Valgrind Memcheck memory error detection environment"
        )
        assert "memory_error_detection" in plugin_info["capabilities"]
        assert "leak_detection" in plugin_info["capabilities"]
        assert "invalid_access_detection" in plugin_info["capabilities"]
        assert "valgrind>=3.15" in plugin_info["external_dependencies"]

    @patch(
        "panther.plugins.environments.execution_environment.base_execution_environment.BaseExecutionEnvironment.standardized_environment_initialization"
    )
    def test_inheritance_chain(self, mock_std_init, temp_output_dir, event_manager):
        """Test that MemcheckEnvironment has correct inheritance."""
        from panther.plugins.environments.execution_environment.base_execution_environment import (
            BaseExecutionEnvironment,
        )

        config = MemcheckConfig()
        env = MemcheckEnvironment(
            env_config_to_test=config,
            output_dir=temp_output_dir,
            env_type="execution",
            env_sub_type="memcheck",
            event_manager=event_manager,
        )

        assert isinstance(env, BaseExecutionEnvironment)
        assert isinstance(env, MemcheckEnvironment)


class TestMemcheckConfigurationHandling:
    """Test suite for configuration handling with dual approach."""

    @patch(
        "panther.plugins.environments.execution_environment.base_execution_environment.BaseExecutionEnvironment.standardized_environment_initialization"
    )
    def test_get_plugin_config_caching(
        self, mock_std_init, temp_output_dir, event_manager
    ):
        """Test that plugin config is cached correctly."""
        config = MemcheckConfig(freelist_vol=30000000)

        with patch.object(
            config, "get_plugin_config", return_value=config
        ) as mock_get_config:
            env = MemcheckEnvironment(
                env_config_to_test=config,
                output_dir=temp_output_dir,
                env_type="execution",
                env_sub_type="memcheck",
                event_manager=event_manager,
            )

            # First call should invoke get_plugin_config
            plugin_config1 = env._get_plugin_config()
            mock_get_config.assert_called_once_with(MemcheckConfig)

            # Second call should use cached value
            plugin_config2 = env._get_plugin_config()
            mock_get_config.assert_called_once()  # Still only one call

            assert plugin_config1 is plugin_config2
            assert plugin_config1.freelist_vol == 30000000

    @patch(
        "panther.plugins.environments.execution_environment.base_execution_environment.BaseExecutionEnvironment.standardized_environment_initialization"
    )
    def test_get_plugin_config_exception_fallback(
        self, mock_std_init, temp_output_dir, event_manager
    ):
        """Test fallback to default config when get_plugin_config fails."""
        config = MemcheckConfig()

        with patch.object(
            config, "get_plugin_config", side_effect=Exception("Config error")
        ):
            env = MemcheckEnvironment(
                env_config_to_test=config,
                output_dir=temp_output_dir,
                env_type="execution",
                env_sub_type="memcheck",
                event_manager=event_manager,
            )

            with patch.object(env, "logger") as mock_logger:
                plugin_config = env._get_plugin_config()

                # Should return default config
                assert isinstance(plugin_config, MemcheckConfig)
                assert plugin_config.freelist_vol == 20000000  # Default value

                # Should log debug message
                mock_logger.debug.assert_called_once()
                assert "Could not get plugin config, using defaults" in str(
                    mock_logger.debug.call_args
                )

    @patch(
        "panther.plugins.environments.execution_environment.base_execution_environment.BaseExecutionEnvironment.standardized_environment_initialization"
    )
    def test_get_config_value_helper_plugin_config_dict(
        self, mock_std_init, temp_output_dir, event_manager
    ):
        """Test _get_config_value helper with plugin_config dict."""
        config = MemcheckConfig()
        config.plugin_config = {"leak_check": "full", "track_origins": True}

        env = MemcheckEnvironment(
            env_config_to_test=config,
            output_dir=temp_output_dir,
            env_type="execution",
            env_sub_type="memcheck",
            event_manager=event_manager,
        )

        # Should get values from plugin_config dict first
        assert env._get_config_value("leak_check") == "full"
        assert env._get_config_value("track_origins") is True
        assert env._get_config_value("nonexistent", "default") == "default"

    @patch(
        "panther.plugins.environments.execution_environment.base_execution_environment.BaseExecutionEnvironment.standardized_environment_initialization"
    )
    def test_get_config_value_helper_typed_config_fallback(
        self, mock_std_init, temp_output_dir, event_manager
    ):
        """Test _get_config_value helper with typed config fallback."""
        config = MemcheckConfig(leak_check="summary", undef_value_errors=False)

        env = MemcheckEnvironment(
            env_config_to_test=config,
            output_dir=temp_output_dir,
            env_type="execution",
            env_sub_type="memcheck",
            event_manager=event_manager,
        )

        with patch.object(env, "_get_plugin_config") as mock_get_config:
            typed_config = Mock()
            typed_config.leak_check = "summary"
            typed_config.undef_value_errors = False
            mock_get_config.return_value = typed_config

            # Should fall back to typed config when no plugin_config dict
            assert env._get_config_value("leak_check") == "summary"
            assert env._get_config_value("undef_value_errors") is False


class TestMemcheckCommandGeneration:
    """Test suite for memcheck command generation."""

    @patch(
        "panther.plugins.environments.execution_environment.base_execution_environment.BaseExecutionEnvironment.standardized_environment_initialization"
    )
    def test_build_memcheck_command_basic(
        self, mock_std_init, temp_output_dir, event_manager
    ):
        """Test basic memcheck command generation."""
        config = MemcheckConfig()
        env = MemcheckEnvironment(
            env_config_to_test=config,
            output_dir=temp_output_dir,
            env_type="execution",
            env_sub_type="memcheck",
            event_manager=event_manager,
        )

        command = env._build_memcheck_command("/tmp/memcheck.log")

        # Check basic command structure
        assert "valgrind" in command
        assert "--tool=memcheck" in command
        assert "--log-file=/tmp/memcheck.log" in command
        assert "--leak-check=summary" in command  # Default value
        assert "--leak-resolution=high" in command
        assert "--show-leak-kinds=definite,possible" in command
        assert "--errors-for-leak-kinds=definite,possible" in command
        assert "--expensive-definedness-checks=auto" in command
        assert "--keep-stacktraces=alloc-and-free" in command
        assert "--freelist-vol=20000000" in command
        assert "--freelist-big-blocks=1000000" in command

    @patch(
        "panther.plugins.environments.execution_environment.base_execution_environment.BaseExecutionEnvironment.standardized_environment_initialization"
    )
    def test_build_memcheck_command_with_xml_output(
        self, mock_std_init, temp_output_dir, event_manager
    ):
        """Test memcheck command generation with XML output format."""
        config = MemcheckConfig()
        config.plugin_config = {"output_format": "xml", "xml_user_comment": "Test run"}

        env = MemcheckEnvironment(
            env_config_to_test=config,
            output_dir=temp_output_dir,
            env_type="execution",
            env_sub_type="memcheck",
            event_manager=event_manager,
        )

        command = env._build_memcheck_command("/tmp/memcheck.log")

        assert "--xml=yes" in command
        assert "--xml-file=/tmp/memcheck.log.xml" in command
        assert "--xml-user-comment=Test run" in command

    @patch(
        "panther.plugins.environments.execution_environment.base_execution_environment.BaseExecutionEnvironment.standardized_environment_initialization"
    )
    def test_build_memcheck_command_with_leak_check_options(
        self, mock_std_init, temp_output_dir, event_manager
    ):
        """Test memcheck command generation with leak checking options."""
        config = MemcheckConfig()
        config.plugin_config = {
            "leak_check": "full",
            "leak_resolution": "med",
            "show_leak_kinds": "all",
            "errors_for_leak_kinds": "definite,indirect",
            "leak_check_heuristics": "stdstring,length64",
        }

        env = MemcheckEnvironment(
            env_config_to_test=config,
            output_dir=temp_output_dir,
            env_type="execution",
            env_sub_type="memcheck",
            event_manager=event_manager,
        )

        command = env._build_memcheck_command("/tmp/memcheck.log")

        assert "--leak-check=full" in command
        assert "--leak-resolution=med" in command
        assert "--show-leak-kinds=all" in command
        assert "--errors-for-leak-kinds=definite,indirect" in command
        assert "--leak-check-heuristics=stdstring,length64" in command

    @patch(
        "panther.plugins.environments.execution_environment.base_execution_environment.BaseExecutionEnvironment.standardized_environment_initialization"
    )
    def test_build_memcheck_command_with_optional_leak_flags(
        self, mock_std_init, temp_output_dir, event_manager
    ):
        """Test memcheck command generation with optional leak flags."""
        config = MemcheckConfig()
        config.plugin_config = {"show_reachable": "yes", "show_possibly_lost": "no"}

        env = MemcheckEnvironment(
            env_config_to_test=config,
            output_dir=temp_output_dir,
            env_type="execution",
            env_sub_type="memcheck",
            event_manager=event_manager,
        )

        command = env._build_memcheck_command("/tmp/memcheck.log")

        assert "--show-reachable=yes" in command
        assert "--show-possibly-lost=no" in command

    @patch(
        "panther.plugins.environments.execution_environment.base_execution_environment.BaseExecutionEnvironment.standardized_environment_initialization"
    )
    def test_build_memcheck_command_with_xtree_leak(
        self, mock_std_init, temp_output_dir, event_manager
    ):
        """Test memcheck command generation with XTree leak output."""
        config = MemcheckConfig()
        config.plugin_config = {
            "xtree_leak": True,
            "xtree_leak_file": "custom_xtleak.kcg",
        }

        env = MemcheckEnvironment(
            env_config_to_test=config,
            output_dir=temp_output_dir,
            env_type="execution",
            env_sub_type="memcheck",
            event_manager=event_manager,
        )

        command = env._build_memcheck_command("/tmp/memcheck.log")

        assert "--xtree-leak=yes" in command
        assert "--xtree-leak-file=custom_xtleak.kcg" in command

    @patch(
        "panther.plugins.environments.execution_environment.base_execution_environment.BaseExecutionEnvironment.standardized_environment_initialization"
    )
    def test_build_memcheck_command_with_error_detection_options(
        self, mock_std_init, temp_output_dir, event_manager
    ):
        """Test memcheck command generation with error detection options."""
        config = MemcheckConfig()
        config.plugin_config = {
            "undef_value_errors": False,
            "track_origins": True,
            "partial_loads_ok": False,
            "expensive_definedness_checks": "yes",
            "keep_stacktraces": "alloc",
        }

        env = MemcheckEnvironment(
            env_config_to_test=config,
            output_dir=temp_output_dir,
            env_type="execution",
            env_sub_type="memcheck",
            event_manager=event_manager,
        )

        command = env._build_memcheck_command("/tmp/memcheck.log")

        assert "--undef-value-errors=no" in command
        assert "--track-origins=yes" in command
        assert "--partial-loads-ok=no" in command
        assert "--expensive-definedness-checks=yes" in command
        assert "--keep-stacktraces=alloc" in command

    @patch(
        "panther.plugins.environments.execution_environment.base_execution_environment.BaseExecutionEnvironment.standardized_environment_initialization"
    )
    def test_build_memcheck_command_with_memory_management_options(
        self, mock_std_init, temp_output_dir, event_manager
    ):
        """Test memcheck command generation with memory management options."""
        config = MemcheckConfig()
        config.plugin_config = {
            "freelist_vol": 50000000,
            "freelist_big_blocks": 2000000,
        }

        env = MemcheckEnvironment(
            env_config_to_test=config,
            output_dir=temp_output_dir,
            env_type="execution",
            env_sub_type="memcheck",
            event_manager=event_manager,
        )

        command = env._build_memcheck_command("/tmp/memcheck.log")

        assert "--freelist-vol=50000000" in command
        assert "--freelist-big-blocks=2000000" in command

    @patch(
        "panther.plugins.environments.execution_environment.base_execution_environment.BaseExecutionEnvironment.standardized_environment_initialization"
    )
    def test_build_memcheck_command_with_special_handling_options(
        self, mock_std_init, temp_output_dir, event_manager
    ):
        """Test memcheck command generation with special handling options."""
        config = MemcheckConfig()
        config.plugin_config = {
            "workaround_gcc296_bugs": True,
            "ignore_range_below_sp": "8192-8189",
            "show_mismatched_frees": False,
            "show_realloc_size_zero": False,
            "ignore_ranges": "0xPP-0xQQ,0xRR-0xSS",
        }

        env = MemcheckEnvironment(
            env_config_to_test=config,
            output_dir=temp_output_dir,
            env_type="execution",
            env_sub_type="memcheck",
            event_manager=event_manager,
        )

        command = env._build_memcheck_command("/tmp/memcheck.log")

        assert "--workaround-gcc296-bugs=yes" in command
        assert "--ignore-range-below-sp=8192-8189" in command
        assert "--show-mismatched-frees=no" in command
        assert "--show-realloc-size-zero=no" in command
        assert "--ignore-ranges=0xPP-0xQQ,0xRR-0xSS" in command

    @patch(
        "panther.plugins.environments.execution_environment.base_execution_environment.BaseExecutionEnvironment.standardized_environment_initialization"
    )
    def test_build_memcheck_command_with_fill_options(
        self, mock_std_init, temp_output_dir, event_manager
    ):
        """Test memcheck command generation with fill options."""
        config = MemcheckConfig()
        config.plugin_config = {"malloc_fill": "0xAA", "free_fill": "0xBB"}

        env = MemcheckEnvironment(
            env_config_to_test=config,
            output_dir=temp_output_dir,
            env_type="execution",
            env_sub_type="memcheck",
            event_manager=event_manager,
        )

        command = env._build_memcheck_command("/tmp/memcheck.log")

        assert "--malloc-fill=0xAA" in command
        assert "--free-fill=0xBB" in command

    @patch(
        "panther.plugins.environments.execution_environment.base_execution_environment.BaseExecutionEnvironment.standardized_environment_initialization"
    )
    def test_build_memcheck_command_with_suppression_and_generation(
        self, mock_std_init, temp_output_dir, event_manager
    ):
        """Test memcheck command generation with suppression options."""
        config = MemcheckConfig()
        config.plugin_config = {
            "suppression_file": "/tmp/suppressions.supp",
            "generate_suppressions": True,
        }

        env = MemcheckEnvironment(
            env_config_to_test=config,
            output_dir=temp_output_dir,
            env_type="execution",
            env_sub_type="memcheck",
            event_manager=event_manager,
        )

        command = env._build_memcheck_command("/tmp/memcheck.log")

        assert "--suppressions=/tmp/suppressions.supp" in command
        assert "--gen-suppressions=all" in command

    @patch(
        "panther.plugins.environments.execution_environment.base_execution_environment.BaseExecutionEnvironment.standardized_environment_initialization"
    )
    def test_build_memcheck_command_with_additional_parameters(
        self, mock_std_init, temp_output_dir, event_manager
    ):
        """Test memcheck command generation with additional parameters."""
        config = MemcheckConfig()
        config.plugin_config = {
            "additional_parameters": ["--show-below-main=yes", "--time-stamp=yes"]
        }

        env = MemcheckEnvironment(
            env_config_to_test=config,
            output_dir=temp_output_dir,
            env_type="execution",
            env_sub_type="memcheck",
            event_manager=event_manager,
        )

        command = env._build_memcheck_command("/tmp/memcheck.log")

        assert "--show-below-main=yes" in command
        assert "--time-stamp=yes" in command

    @patch(
        "panther.plugins.environments.execution_environment.base_execution_environment.BaseExecutionEnvironment.standardized_environment_initialization"
    )
    def test_build_memcheck_command_typed_config_fallback(
        self, mock_std_init, temp_output_dir, event_manager
    ):
        """Test memcheck command generation with typed config fallback."""
        config = MemcheckConfig(
            leak_check="full", track_origins=True, freelist_vol=40000000
        )

        env = MemcheckEnvironment(
            env_config_to_test=config,
            output_dir=temp_output_dir,
            env_type="execution",
            env_sub_type="memcheck",
            event_manager=event_manager,
        )

        # Mock typed config to test fallback
        with patch.object(env, "_get_plugin_config") as mock_get_config:
            typed_config = MemcheckConfig()
            typed_config.leak_check = "full"
            typed_config.track_origins = True
            typed_config.freelist_vol = 40000000
            mock_get_config.return_value = typed_config

            command = env._build_memcheck_command("/tmp/memcheck.log")

            assert "--leak-check=full" in command
            assert "--track-origins=yes" in command
            assert "--freelist-vol=40000000" in command


class TestMemcheckCommandInterface:
    """Test suite for to_command interface."""

    @patch(
        "panther.plugins.environments.execution_environment.base_execution_environment.BaseExecutionEnvironment.standardized_environment_initialization"
    )
    def test_to_command_basic(self, mock_std_init, temp_output_dir, event_manager):
        """Test basic to_command functionality."""
        config = MemcheckConfig()
        env = MemcheckEnvironment(
            env_config_to_test=config,
            output_dir=temp_output_dir,
            env_type="execution",
            env_sub_type="memcheck",
            event_manager=event_manager,
        )

        command = env.to_command(output_file="/tmp/test_memcheck.log")

        assert "valgrind" in command
        assert "--tool=memcheck" in command
        assert "--log-file=/tmp/test_memcheck.log" in command

    @patch(
        "panther.plugins.environments.execution_environment.base_execution_environment.BaseExecutionEnvironment.standardized_environment_initialization"
    )
    def test_to_command_default_output_file(
        self, mock_std_init, temp_output_dir, event_manager
    ):
        """Test to_command with default output file."""
        config = MemcheckConfig()
        env = MemcheckEnvironment(
            env_config_to_test=config,
            output_dir=temp_output_dir,
            env_type="execution",
            env_sub_type="memcheck",
            event_manager=event_manager,
        )

        # Mock _get_config_value to return custom output file
        with patch.object(env, "_get_config_value") as mock_get_value:
            mock_get_value.return_value = "/custom/memcheck.log"

            command = env.to_command()

            assert "--log-file=/custom/memcheck.log" in command

    @patch(
        "panther.plugins.environments.execution_environment.base_execution_environment.BaseExecutionEnvironment.standardized_environment_initialization"
    )
    def test_to_command_fallback_default(
        self, mock_std_init, temp_output_dir, event_manager
    ):
        """Test to_command fallback to absolute default."""
        config = MemcheckConfig()
        env = MemcheckEnvironment(
            env_config_to_test=config,
            output_dir=temp_output_dir,
            env_type="execution",
            env_sub_type="memcheck",
            event_manager=event_manager,
        )

        # Mock _get_config_value to return None
        with patch.object(env, "_get_config_value") as mock_get_value:
            mock_get_value.return_value = None

            command = env.to_command()

            assert "--log-file=/tmp/memcheck.log" in command

    @patch(
        "panther.plugins.environments.execution_environment.base_execution_environment.BaseExecutionEnvironment.standardized_environment_initialization"
    )
    def test_to_command_with_pid_warning(
        self, mock_std_init, temp_output_dir, event_manager
    ):
        """Test to_command logs warning when PID is provided."""
        config = MemcheckConfig()
        env = MemcheckEnvironment(
            env_config_to_test=config,
            output_dir=temp_output_dir,
            env_type="execution",
            env_sub_type="memcheck",
            event_manager=event_manager,
        )

        with patch.object(env, "logger") as mock_logger:
            command = env.to_command(pid=5678)

            # Should log warning about PID not being supported
            mock_logger.warning.assert_called_once()
            assert "PID parameter (5678) not supported" in str(
                mock_logger.warning.call_args
            )


class TestMemcheckAnalysisCommands:
    """Test suite for memcheck analysis and post-processing."""

    @patch(
        "panther.plugins.environments.execution_environment.base_execution_environment.BaseExecutionEnvironment.standardized_environment_initialization"
    )
    def test_add_memcheck_analysis_commands_basic(
        self, mock_std_init, temp_output_dir, event_manager
    ):
        """Test basic memcheck analysis command generation."""
        config = MemcheckConfig()
        env = MemcheckEnvironment(
            env_config_to_test=config,
            output_dir=temp_output_dir,
            env_type="execution",
            env_sub_type="memcheck",
            event_manager=event_manager,
        )

        # Create mock command builder
        mock_builder = Mock()
        mock_builder.service_name = "test_service"

        env._add_memcheck_analysis_commands(
            mock_builder, "/tmp/memcheck.log", "/tmp/memcheck_summary.txt"
        )

        # Verify post-processing was added
        mock_builder.add_post_processing.assert_called_once()

        # Verify the post-processing command content
        call_args = mock_builder.add_post_processing.call_args
        processing_command = call_args[1]["processing_command"]

        assert "Memcheck Memory Error Analysis for test_service" in processing_command
        assert "Memory Error Summary" in processing_command
        assert "Invalid read/write operations" in processing_command
        assert "Use of uninitialized values" in processing_command
        assert "Memory leaks detected" in processing_command
        assert "Invalid free operations" in processing_command
        assert "Memory Leak Analysis" in processing_command
        assert "Invalid Memory Access Analysis" in processing_command
        assert "Uninitialized Value Usage" in processing_command
        assert "Error Severity Assessment" in processing_command
        assert "/tmp/memcheck.log" in processing_command
        assert "/tmp/memcheck_summary.txt" in processing_command

    @patch(
        "panther.plugins.environments.execution_environment.base_execution_environment.BaseExecutionEnvironment.standardized_environment_initialization"
    )
    def test_add_memcheck_analysis_commands_with_full_leak_check(
        self, mock_std_init, temp_output_dir, event_manager
    ):
        """Test memcheck analysis with full leak check enabled."""
        config = MemcheckConfig()
        config.plugin_config = {"leak_check": "full"}

        env = MemcheckEnvironment(
            env_config_to_test=config,
            output_dir=temp_output_dir,
            env_type="execution",
            env_sub_type="memcheck",
            event_manager=event_manager,
        )

        # Create mock command builder
        mock_builder = Mock()
        mock_builder.service_name = "test_service"
        mock_builder.register_output_file.return_value = "/tmp/memcheck_leaks.txt"

        env._add_memcheck_analysis_commands(
            mock_builder, "/tmp/memcheck.log", "/tmp/memcheck_summary.txt"
        )

        # Verify both basic and leak detail post-processing were added
        assert mock_builder.add_post_processing.call_count == 2

        # Verify leak detail file was registered
        mock_builder.register_output_file.assert_called_once_with(
            file_type="memcheck_leaks",
            extension="detailed.txt",
            description="Detailed Memcheck leak analysis",
        )

    @patch(
        "panther.plugins.environments.execution_environment.base_execution_environment.BaseExecutionEnvironment.standardized_environment_initialization"
    )
    def test_add_memcheck_analysis_commands_with_yes_leak_check(
        self, mock_std_init, temp_output_dir, event_manager
    ):
        """Test memcheck analysis with 'yes' leak check."""
        config = MemcheckConfig()
        config.plugin_config = {"leak_check": "yes"}

        env = MemcheckEnvironment(
            env_config_to_test=config,
            output_dir=temp_output_dir,
            env_type="execution",
            env_sub_type="memcheck",
            event_manager=event_manager,
        )

        # Create mock command builder
        mock_builder = Mock()
        mock_builder.service_name = "test_service"
        mock_builder.register_output_file.return_value = "/tmp/memcheck_leaks.txt"

        env._add_memcheck_analysis_commands(
            mock_builder, "/tmp/memcheck.log", "/tmp/memcheck_summary.txt"
        )

        # Should also generate detailed leak analysis for 'yes'
        assert mock_builder.add_post_processing.call_count == 2

    @patch(
        "panther.plugins.environments.execution_environment.base_execution_environment.BaseExecutionEnvironment.standardized_environment_initialization"
    )
    def test_add_memcheck_analysis_commands_no_leak_check(
        self, mock_std_init, temp_output_dir, event_manager
    ):
        """Test memcheck analysis with no leak check."""
        config = MemcheckConfig()
        config.plugin_config = {"leak_check": "no"}

        env = MemcheckEnvironment(
            env_config_to_test=config,
            output_dir=temp_output_dir,
            env_type="execution",
            env_sub_type="memcheck",
            event_manager=event_manager,
        )

        # Create mock command builder
        mock_builder = Mock()
        mock_builder.service_name = "test_service"

        env._add_memcheck_analysis_commands(
            mock_builder, "/tmp/memcheck.log", "/tmp/memcheck_summary.txt"
        )

        # Should only generate basic analysis, not detailed leak analysis
        assert mock_builder.add_post_processing.call_count == 1
        mock_builder.register_output_file.assert_not_called()


class TestMemcheckPluginSpecificSetup:
    """Test suite for plugin-specific environment setup."""

    def create_mock_service(self, service_name="test_service", has_run_cmd=True):
        """Helper to create mock service."""
        service = Mock(spec=IServiceManager)
        service.service_name = service_name
        if has_run_cmd:
            service.run_cmd = {"pre_run_cmds": []}
        return service

    @patch(
        "panther.plugins.environments.execution_environment.memcheck.memcheck.create_execution_environment_builder"
    )
    @patch(
        "panther.plugins.environments.execution_environment.base_execution_environment.BaseExecutionEnvironment.standardized_environment_initialization"
    )
    def test_setup_plugin_specific_environment_single_service(
        self, mock_std_init, mock_builder, temp_output_dir, event_manager
    ):
        """Test setup with single service."""
        config = MemcheckConfig()
        env = MemcheckEnvironment(
            env_config_to_test=config,
            output_dir=temp_output_dir,
            env_type="execution",
            env_sub_type="memcheck",
            event_manager=event_manager,
        )

        # Setup mock command builder
        mock_cmd_builder = Mock()
        mock_cmd_builder.register_output_file.side_effect = [
            "/tmp/memcheck.log",
            "/tmp/memcheck_summary.txt",
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
                    environment_name="memcheck",
                    timestamp="test_timestamp",
                    register_output_callback=mock_register,
                    logger=env.logger,
                )

                # Verify output files were registered
                assert mock_cmd_builder.register_output_file.call_count == 2

                # Verify first call for memcheck log
                first_call = mock_cmd_builder.register_output_file.call_args_list[0]
                assert first_call[1]["file_type"] == "memcheck_log"
                assert first_call[1]["extension"] == "log"

                # Verify second call for memcheck summary
                second_call = mock_cmd_builder.register_output_file.call_args_list[1]
                assert second_call[1]["file_type"] == "memcheck_summary"
                assert second_call[1]["extension"] == "txt"

                # Verify conditional wrapper was added
                mock_cmd_builder.add_conditional_wrapper.assert_called_once()

                # Verify post-processing was added
                mock_cmd_builder.add_post_processing.assert_called()

                # Verify build_and_apply was called
                mock_cmd_builder.build_and_apply.assert_called_once_with(mock_modify)

    @patch(
        "panther.plugins.environments.execution_environment.memcheck.memcheck.create_execution_environment_builder"
    )
    @patch(
        "panther.plugins.environments.execution_environment.base_execution_environment.BaseExecutionEnvironment.standardized_environment_initialization"
    )
    def test_setup_multiple_services(
        self, mock_std_init, mock_builder, temp_output_dir, event_manager
    ):
        """Test setup with multiple services."""
        config = MemcheckConfig()
        env = MemcheckEnvironment(
            env_config_to_test=config,
            output_dir=temp_output_dir,
            env_type="execution",
            env_sub_type="memcheck",
            event_manager=event_manager,
        )

        # Setup mock command builder
        mock_cmd_builder = Mock()
        mock_cmd_builder.register_output_file.side_effect = [
            "/tmp/memcheck1.log",
            "/tmp/memcheck1_summary.txt",  # First service
            "/tmp/memcheck2.log",
            "/tmp/memcheck2_summary.txt",  # Second service
            "/tmp/memcheck3.log",
            "/tmp/memcheck3_summary.txt",  # Third service
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
        "panther.plugins.environments.execution_environment.memcheck.memcheck.create_execution_environment_builder"
    )
    @patch(
        "panther.plugins.environments.execution_environment.base_execution_environment.BaseExecutionEnvironment.standardized_environment_initialization"
    )
    def test_setup_empty_services_list(
        self, mock_std_init, mock_builder, temp_output_dir, event_manager
    ):
        """Test setup with empty services list."""
        config = MemcheckConfig()
        env = MemcheckEnvironment(
            env_config_to_test=config,
            output_dir=temp_output_dir,
            env_type="execution",
            env_sub_type="memcheck",
            event_manager=event_manager,
        )

        env._setup_plugin_specific_environment([], "test_timestamp")

        # Should not create any builders
        mock_builder.assert_not_called()

    @patch(
        "panther.plugins.environments.execution_environment.memcheck.memcheck.create_execution_environment_builder"
    )
    @patch(
        "panther.plugins.environments.execution_environment.base_execution_environment.BaseExecutionEnvironment.standardized_environment_initialization"
    )
    def test_setup_conditional_wrapper_details(
        self, mock_std_init, mock_builder, temp_output_dir, event_manager
    ):
        """Test that setup uses conditional wrapper for Valgrind availability."""
        config = MemcheckConfig()
        env = MemcheckEnvironment(
            env_config_to_test=config,
            output_dir=temp_output_dir,
            env_type="execution",
            env_sub_type="memcheck",
            event_manager=event_manager,
        )

        # Setup mock command builder
        mock_cmd_builder = Mock()
        mock_cmd_builder.register_output_file.side_effect = [
            "/tmp/memcheck.log",
            "/tmp/memcheck_summary.txt",
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
                assert "--tool=memcheck" in call_args[1]["wrapper_command"]
                assert (
                    call_args[1]["fallback_message"]
                    == "Valgrind not found - Memcheck memory error detection disabled"
                )
                assert call_args[1]["is_critical"] is False


class TestMemcheckEnvironmentUpdates:
    """Test suite for environment update functionality."""

    @patch(
        "panther.plugins.environments.execution_environment.base_execution_environment.BaseExecutionEnvironment.standardized_environment_initialization"
    )
    def test_update_environment(self, mock_std_init, temp_output_dir, event_manager):
        """Test environment update functionality."""
        config = MemcheckConfig()
        env = MemcheckEnvironment(
            env_config_to_test=config,
            output_dir=temp_output_dir,
            env_type="execution",
            env_sub_type="memcheck",
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
                "Updated environment for memcheck execution"
            )


class TestMemcheckErrorHandling:
    """Test suite for error handling and edge cases."""

    @patch(
        "panther.plugins.environments.execution_environment.base_execution_environment.BaseExecutionEnvironment.standardized_environment_initialization"
    )
    def test_service_without_service_name_attribute(
        self, mock_std_init, temp_output_dir, event_manager
    ):
        """Test handling service without service_name attribute."""
        config = MemcheckConfig()
        env = MemcheckEnvironment(
            env_config_to_test=config,
            output_dir=temp_output_dir,
            env_type="execution",
            env_sub_type="memcheck",
            event_manager=event_manager,
        )

        # Create service without service_name attribute
        service = Mock(spec=IServiceManager)
        del service.service_name  # Remove service_name attribute
        service.__class__.__name__ = "TestMemcheckServiceManager"

        with patch(
            "panther.plugins.environments.execution_environment.memcheck.memcheck.create_execution_environment_builder"
        ) as mock_builder:
            mock_cmd_builder = Mock()
            mock_cmd_builder.register_output_file.side_effect = [
                "/tmp/memcheck.log",
                "/tmp/memcheck_summary.txt",
            ]
            mock_cmd_builder.service_name = "TestMemcheckServiceManager"
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
        config = MemcheckConfig(
            suppression_file=None,
            additional_parameters=None,
            malloc_fill=None,
            free_fill=None,
        )

        env = MemcheckEnvironment(
            env_config_to_test=config,
            output_dir=temp_output_dir,
            env_type="execution",
            env_sub_type="memcheck",
            event_manager=event_manager,
        )

        command = env._build_memcheck_command("/tmp/memcheck.log")

        # Should handle None values gracefully
        assert "valgrind" in command
        assert "--tool=memcheck" in command
        assert "--log-file=/tmp/memcheck.log" in command
        # Should not include None values
        assert "--suppressions=None" not in command
        assert "--malloc-fill=None" not in command
        assert "--free-fill=None" not in command


@pytest.mark.unit
class TestMemcheckIntegration:
    """Integration-like tests within unit test scope."""

    @patch(
        "panther.plugins.environments.execution_environment.base_execution_environment.BaseExecutionEnvironment.standardized_environment_initialization"
    )
    def test_full_workflow_simulation(
        self, mock_std_init, temp_output_dir, event_manager
    ):
        """Test a full workflow simulation."""
        config = MemcheckConfig(
            leak_check="full",
            leak_resolution="high",
            show_leak_kinds="all",
            errors_for_leak_kinds="definite,indirect",
            track_origins=True,
            undef_value_errors=True,
            freelist_vol=50000000,
            freelist_big_blocks=2000000,
            output_format="xml",
            xml_user_comment="Integration test",
            suppression_file="/tmp/suppressions.supp",
            generate_suppressions=True,
            additional_parameters=["--show-below-main=yes"],
        )
        config.plugin_config = {
            "leak_check": "full",
            "leak_resolution": "high",
            "show_leak_kinds": "all",
            "errors_for_leak_kinds": "definite,indirect",
            "track_origins": True,
            "undef_value_errors": True,
            "freelist_vol": 50000000,
            "freelist_big_blocks": 2000000,
            "output_format": "xml",
            "xml_user_comment": "Integration test",
            "suppression_file": "/tmp/suppressions.supp",
            "generate_suppressions": True,
            "additional_parameters": ["--show-below-main=yes"],
        }

        env = MemcheckEnvironment(
            env_config_to_test=config,
            output_dir=temp_output_dir,
            env_type="execution",
            env_sub_type="memcheck",
            event_manager=event_manager,
        )

        # Test command generation
        command = env._build_memcheck_command("/tmp/test_memcheck.log")

        assert "valgrind" in command
        assert "--tool=memcheck" in command
        assert "--log-file=/tmp/test_memcheck.log" in command
        assert "--xml=yes" in command
        assert "--xml-file=/tmp/test_memcheck.log.xml" in command
        assert "--xml-user-comment=Integration test" in command
        assert "--leak-check=full" in command
        assert "--leak-resolution=high" in command
        assert "--show-leak-kinds=all" in command
        assert "--errors-for-leak-kinds=definite,indirect" in command
        assert "--track-origins=yes" in command
        assert "--freelist-vol=50000000" in command
        assert "--freelist-big-blocks=2000000" in command
        assert "--suppressions=/tmp/suppressions.supp" in command
        assert "--gen-suppressions=all" in command
        assert "--show-below-main=yes" in command

        # Test to_command interface
        cmd_interface = env.to_command(output_file="/tmp/interface_test.log")
        assert "--log-file=/tmp/interface_test.log" in cmd_interface

        # Test config value helper
        assert env._get_config_value("leak_check") == "full"
        assert env._get_config_value("track_origins") is True
        assert env._get_config_value("nonexistent", "default") == "default"

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
