"""
Comprehensive unit tests for command generation utilities.

Tests all shared utilities used by execution environment plugins including:
- Data classes and specifications
- Output file management
- Wrapper command generation
- High-level command building
- Factory patterns
"""

import hashlib
import logging
from pathlib import Path
from typing import Any, Dict, List
from unittest.mock import MagicMock, Mock, call, patch

import pytest

from panther.config.core.models import ProtocolRole
from panther.core.command_processor import ServiceCommandBuilder
from panther.plugins.environments.execution_environment.command_generation_utils import (
    CommandGenerationUtilsFactory,
    ExecutionEnvironmentCommandBuilder,
    OutputFileManager,
    OutputFileSpec,
    WrapperCommandGenerator,
    WrapperCommandSpec,
    create_execution_environment_builder,
)
from panther.plugins.services.services_interface import IServiceManager


class TestOutputFileSpec:
    """Test suite for OutputFileSpec data class."""

    def test_basic_creation(self):
        """Test basic OutputFileSpec creation."""
        spec = OutputFileSpec(
            file_type="profile", file_path="/tmp/test.prof", service_name="test_service"
        )

        assert spec.file_type == "profile"
        assert spec.file_path == "/tmp/test.prof"
        assert spec.service_name == "test_service"
        assert spec.description is None
        assert spec.is_primary is True

    def test_creation_with_all_fields(self):
        """Test OutputFileSpec creation with all fields."""
        spec = OutputFileSpec(
            file_type="trace",
            file_path="/logs/trace.out",
            service_name="client",
            description="System call trace output",
            is_primary=False,
        )

        assert spec.file_type == "trace"
        assert spec.file_path == "/logs/trace.out"
        assert spec.service_name == "client"
        assert spec.description == "System call trace output"
        assert spec.is_primary is False

    def test_equality(self):
        """Test OutputFileSpec equality comparison."""
        spec1 = OutputFileSpec("test", "/path", "service")
        spec2 = OutputFileSpec("test", "/path", "service")
        spec3 = OutputFileSpec("other", "/path", "service")

        assert spec1 == spec2
        assert spec1 != spec3


class TestWrapperCommandSpec:
    """Test suite for WrapperCommandSpec data class."""

    def test_basic_creation(self):
        """Test basic WrapperCommandSpec creation."""
        spec = WrapperCommandSpec(
            environment_name="strace",
            service_name="server",
            wrapper_setup="strace -o output.trace",
        )

        assert spec.environment_name == "strace"
        assert spec.service_name == "server"
        assert spec.wrapper_setup == "strace -o output.trace"
        assert spec.pre_run_commands == []
        assert spec.post_run_commands == []
        assert spec.environment_vars == {}
        assert spec.is_critical is False
        assert spec.use_wrapper_chaining is True

    def test_creation_with_all_fields(self):
        """Test WrapperCommandSpec creation with all fields."""
        spec = WrapperCommandSpec(
            environment_name="gperf",
            service_name="client",
            wrapper_setup="gperf_cpu_profiler.start()",
            pre_run_commands=["export CPUPROFILE=/tmp/prof"],
            post_run_commands=["pprof --text /tmp/prof"],
            environment_vars={"PROF_OUTPUT": "/tmp/output"},
            is_critical=True,
            use_wrapper_chaining=False,
        )

        assert spec.environment_name == "gperf"
        assert spec.service_name == "client"
        assert spec.wrapper_setup == "gperf_cpu_profiler.start()"
        assert spec.pre_run_commands == ["export CPUPROFILE=/tmp/prof"]
        assert spec.post_run_commands == ["pprof --text /tmp/prof"]
        assert spec.environment_vars == {"PROF_OUTPUT": "/tmp/output"}
        assert spec.is_critical is True
        assert spec.use_wrapper_chaining is False


class TestOutputFileManager:
    """Test suite for OutputFileManager class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_callback = Mock()
        self.mock_logger = Mock(spec=logging.Logger)
        self.manager = OutputFileManager(self.mock_callback, self.mock_logger)

    def test_initialization(self):
        """Test OutputFileManager initialization."""
        assert self.manager.register_output_callback == self.mock_callback
        assert self.manager.logger == self.mock_logger
        assert self.manager._registered_files == []

    def test_initialization_without_logger(self):
        """Test OutputFileManager initialization without logger."""
        manager = OutputFileManager(self.mock_callback)

        assert manager.register_output_callback == self.mock_callback
        assert manager.logger is not None  # Should create default logger
        assert manager._registered_files == []

    def test_generate_output_path_default_dir(self):
        """Test output path generation with default directory."""
        path = self.manager.generate_output_path(
            service_name="test_service",
            file_type="profile",
            timestamp="20250101_120000",
            extension="prof",
        )

        expected = "/app/logs/test_service_profile_20250101_120000.prof"
        assert path == expected

    def test_generate_output_path_custom_dir(self):
        """Test output path generation with custom directory."""
        path = self.manager.generate_output_path(
            service_name="client",
            file_type="trace",
            timestamp="20250101_120000",
            extension="out",
            base_dir="/custom/logs",
        )

        expected = "/custom/logs/client_trace_20250101_120000.out"
        assert path == expected

    def test_register_output_file_basic(self):
        """Test basic output file registration."""
        spec = self.manager.register_output_file(
            file_type="profile", file_path="/tmp/test.prof", service_name="test_service"
        )

        # Check returned spec
        assert isinstance(spec, OutputFileSpec)
        assert spec.file_type == "profile"
        assert spec.file_path == "/tmp/test.prof"
        assert spec.service_name == "test_service"
        assert spec.description is None
        assert spec.is_primary is True

        # Check callback was called
        self.mock_callback.assert_called_once_with(
            "profile", "/tmp/test.prof", "test_service"
        )

        # Check internal storage
        assert len(self.manager._registered_files) == 1
        assert self.manager._registered_files[0] == spec

        # Check logging
        self.mock_logger.debug.assert_called_once()
        log_call = self.mock_logger.debug.call_args[0]
        assert "Registered output file" in log_call[0]
        assert "profile" in log_call[0]

    def test_register_output_file_with_all_params(self):
        """Test output file registration with all parameters."""
        spec = self.manager.register_output_file(
            file_type="trace",
            file_path="/logs/trace.out",
            service_name="client",
            description="System call trace",
            is_primary=False,
        )

        assert spec.file_type == "trace"
        assert spec.file_path == "/logs/trace.out"
        assert spec.service_name == "client"
        assert spec.description == "System call trace"
        assert spec.is_primary is False

        self.mock_callback.assert_called_once_with("trace", "/logs/trace.out", "client")

    def test_get_registered_files_all(self):
        """Test getting all registered files."""
        # Register multiple files
        spec1 = self.manager.register_output_file("type1", "/path1", "service1")
        spec2 = self.manager.register_output_file("type2", "/path2", "service2")
        spec3 = self.manager.register_output_file("type3", "/path3", "service1")

        all_files = self.manager.get_registered_files()

        assert len(all_files) == 3
        assert spec1 in all_files
        assert spec2 in all_files
        assert spec3 in all_files

        # Verify it returns a copy (not the original list)
        all_files.append("test")
        assert len(self.manager._registered_files) == 3

    def test_get_registered_files_filtered_by_service(self):
        """Test getting registered files filtered by service name."""
        # Register files for different services
        spec1 = self.manager.register_output_file("type1", "/path1", "service1")
        spec2 = self.manager.register_output_file("type2", "/path2", "service2")
        spec3 = self.manager.register_output_file("type3", "/path3", "service1")

        service1_files = self.manager.get_registered_files("service1")
        service2_files = self.manager.get_registered_files("service2")

        assert len(service1_files) == 2
        assert spec1 in service1_files
        assert spec3 in service1_files
        assert spec2 not in service1_files

        assert len(service2_files) == 1
        assert spec2 in service2_files
        assert spec1 not in service2_files
        assert spec3 not in service2_files

    def test_get_registered_files_no_matches(self):
        """Test getting registered files for non-existent service."""
        # Register some files
        self.manager.register_output_file("type1", "/path1", "service1")

        # Query for non-existent service
        no_files = self.manager.get_registered_files("nonexistent")

        assert len(no_files) == 0
        assert no_files == []


class TestWrapperCommandGenerator:
    """Test suite for WrapperCommandGenerator class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_logger = Mock(spec=logging.Logger)
        self.generator = WrapperCommandGenerator(self.mock_logger)

    def test_initialization(self):
        """Test WrapperCommandGenerator initialization."""
        assert self.generator.logger == self.mock_logger

    def test_initialization_without_logger(self):
        """Test WrapperCommandGenerator initialization without logger."""
        generator = WrapperCommandGenerator()

        assert generator.logger is not None  # Should create default logger

    def test_generate_environment_wrapper_basic(self):
        """Test basic environment wrapper generation."""
        wrapper = self.generator.generate_environment_wrapper(
            environment_name="strace",
            wrapper_command="strace -o output.trace",
            service_name="test_service",
        )

        expected_lines = [
            "# Setup strace wrapper for test_service",
            "# Execute wrapper command directly instead of writing to file",
            "# This prevents wrapper file content concatenation issues",
            'echo "Executing strace wrapper for test_service" >> /app/logs/test_service_exec_env_setup.log',
            "strace -o output.trace",
            'echo "Completed strace wrapper for test_service" >> /app/logs/test_service_exec_env_setup.log',
        ]

        for line in expected_lines:
            assert line in wrapper

        # Should not have environment variables section
        assert "export" not in wrapper

    def test_generate_environment_wrapper_with_env_vars(self):
        """Test environment wrapper generation with environment variables."""
        env_vars = {"STRACE_OUTPUT": "/tmp/trace.out", "STRACE_VERBOSE": "1"}

        wrapper = self.generator.generate_environment_wrapper(
            environment_name="strace",
            wrapper_command="strace -o $STRACE_OUTPUT",
            service_name="server",
            additional_env_vars=env_vars,
        )

        # Check environment variable exports
        assert "export STRACE_OUTPUT=/tmp/trace.out" in wrapper
        assert "export STRACE_VERBOSE=1" in wrapper

        # Check main structure
        assert "# Setup strace wrapper for server" in wrapper
        assert "strace -o $STRACE_OUTPUT" in wrapper
        assert "/app/logs/server_exec_env_setup.log" in wrapper

    def test_generate_conditional_wrapper_basic(self):
        """Test basic conditional wrapper generation."""
        wrapper = self.generator.generate_conditional_wrapper(
            condition="command -v strace >/dev/null 2>&1",
            environment_name="strace",
            wrapper_command="strace -o output.trace",
            service_name="client",
        )

        expected_lines = [
            "# Conditional strace wrapper setup for client",
            "if command -v strace >/dev/null 2>&1; then",
            "# Setup strace wrapper for client",
            "strace -o output.trace",
            "fi",
        ]

        for line in expected_lines:
            assert line in wrapper

    def test_generate_conditional_wrapper_with_fallback(self):
        """Test conditional wrapper generation with fallback message."""
        wrapper = self.generator.generate_conditional_wrapper(
            condition="command -v gperf >/dev/null 2>&1",
            environment_name="gperf",
            wrapper_command="gperf_start()",
            service_name="server",
            fallback_message="gperf not available, skipping profiling",
        )

        expected_lines = [
            "# Conditional gperf wrapper setup for server",
            "if command -v gperf >/dev/null 2>&1; then",
            "gperf_start()",
            "else",
            'echo "gperf not available, skipping profiling" >> /app/logs/server_exec_env_setup.log',
            "fi",
        ]

        for line in expected_lines:
            assert line in wrapper

    def test_generate_post_processing_command_basic(self):
        """Test basic post-processing command generation."""
        cmd = self.generator.generate_post_processing_command(
            input_file="/tmp/profile.prof",
            output_file="/tmp/profile.txt",
            processing_command="pprof --text /tmp/profile.prof > /tmp/profile.txt",
            service_name="test_service",
            description="Profile analysis",
        )

        expected_lines = [
            "# Profile analysis for test_service",
            'if [ -f "/tmp/profile.prof" ]; then',
            "pprof --text /tmp/profile.prof > /tmp/profile.txt",
            'echo "Generated Profile analysis: /tmp/profile.txt" >> /app/logs/test_service_exec_env_setup.log',
            "else",
            'echo "Input file not found: /tmp/profile.prof" >> /app/logs/test_service_exec_env_setup.log',
            "fi",
        ]

        for line in expected_lines:
            assert line in cmd

    def test_generate_post_processing_command_with_custom_error(self):
        """Test post-processing command generation with custom error message."""
        cmd = self.generator.generate_post_processing_command(
            input_file="/tmp/trace.out",
            output_file="/tmp/summary.txt",
            processing_command="analyze_trace /tmp/trace.out > /tmp/summary.txt",
            service_name="client",
            description="Trace analysis",
            error_message="Custom error: trace analysis failed",
        )

        # Check error handling with custom message
        assert "Custom error: trace analysis failed" in cmd
        assert '|| echo "Custom error: trace analysis failed"' in cmd

        # Check structure
        assert "# Trace analysis for client" in cmd
        assert 'if [ -f "/tmp/trace.out" ]' in cmd
        assert "analyze_trace /tmp/trace.out > /tmp/summary.txt" in cmd


class TestExecutionEnvironmentCommandBuilder:
    """Test suite for ExecutionEnvironmentCommandBuilder class."""

    def setup_method(self):
        """Set up test fixtures."""
        self.mock_service = Mock(spec=IServiceManager)
        self.mock_service.service_name = "test_service"
        self.mock_service.role = ProtocolRole.SERVER
        self.mock_service.run_cmd = {"pre_run_cmds": []}

        self.mock_output_manager = Mock(spec=OutputFileManager)
        self.mock_wrapper_generator = Mock(spec=WrapperCommandGenerator)
        self.mock_logger = Mock(spec=logging.Logger)

        self.builder = ExecutionEnvironmentCommandBuilder(
            service=self.mock_service,
            environment_name="test_env",
            timestamp="20250101_120000",
            output_file_manager=self.mock_output_manager,
            wrapper_generator=self.mock_wrapper_generator,
            logger=self.mock_logger,
        )

    def test_initialization(self):
        """Test ExecutionEnvironmentCommandBuilder initialization."""
        assert self.builder.service == self.mock_service
        assert self.builder.environment_name == "test_env"
        assert self.builder.timestamp == "20250101_120000"
        assert self.builder.output_file_manager == self.mock_output_manager
        assert self.builder.wrapper_generator == self.mock_wrapper_generator
        assert self.builder.logger == self.mock_logger
        assert self.builder.service_name == "test_service"
        assert self.builder.service_role == ProtocolRole.SERVER
        assert isinstance(self.builder.command_builder, ServiceCommandBuilder)
        assert self.builder._wrapper_commands == []
        assert self.builder._post_run_commands == []
        assert self.builder._applied_wrappers == set()

    def test_initialization_with_service_without_name(self):
        """Test initialization with service without service_name attribute."""
        service_without_name = Mock(spec=IServiceManager)
        service_without_name.__class__.__name__ = "TestServiceManager"
        del service_without_name.service_name
        service_without_name.role = ProtocolRole.CLIENT

        builder = ExecutionEnvironmentCommandBuilder(
            service=service_without_name,
            environment_name="test_env",
            timestamp="20250101_120000",
            output_file_manager=self.mock_output_manager,
            wrapper_generator=self.mock_wrapper_generator,
            logger=self.mock_logger,
        )

        assert builder.service_name == "TestServiceManager"
        assert builder.service_role == ProtocolRole.CLIENT

    def test_initialization_with_service_without_role(self):
        """Test initialization with service without role attribute."""
        service_without_role = Mock(spec=IServiceManager)
        service_without_role.service_name = "test_service"
        del service_without_role.role

        builder = ExecutionEnvironmentCommandBuilder(
            service=service_without_role,
            environment_name="test_env",
            timestamp="20250101_120000",
            output_file_manager=self.mock_output_manager,
            wrapper_generator=self.mock_wrapper_generator,
            logger=self.mock_logger,
        )

        assert builder.service_role == ProtocolRole.SERVER  # Default

    @patch(
        "panther.plugins.environments.execution_environment.command_generation_utils.CommandSummarizer"
    )
    def test_add_wrapper_command_basic(self, mock_summarizer):
        """Test adding a basic wrapper command."""
        mock_summarizer.summarize_single_command.return_value = "wrapper setup..."
        self.mock_wrapper_generator.generate_environment_wrapper.return_value = (
            "generated wrapper"
        )

        result = self.builder.add_wrapper_command(
            wrapper_command="strace -o output.trace"
        )

        # Should return self for method chaining
        assert result == self.builder

        # Check wrapper generator was called
        self.mock_wrapper_generator.generate_environment_wrapper.assert_called_once_with(
            "test_env", "strace -o output.trace", "test_service", None
        )

        # Check command was added to command builder
        assert len(self.builder._wrapper_commands) == 1
        assert self.builder._wrapper_commands[0] == "generated wrapper"

        # Check logging
        self.mock_logger.debug.assert_called_once()
        assert "Added wrapper command for test_service" in str(
            self.mock_logger.debug.call_args
        )

        # Check command summarization
        mock_summarizer.summarize_single_command.assert_called_once_with(
            "generated wrapper"
        )

    @patch(
        "panther.plugins.environments.execution_environment.command_generation_utils.CommandSummarizer"
    )
    def test_add_wrapper_command_with_all_params(self, mock_summarizer):
        """Test adding wrapper command with all parameters."""
        mock_summarizer.summarize_single_command.return_value = "wrapper setup..."
        self.mock_wrapper_generator.generate_environment_wrapper.return_value = (
            "complex wrapper"
        )

        env_vars = {"VAR1": "value1", "VAR2": "value2"}

        result = self.builder.add_wrapper_command(
            wrapper_command="complex command",
            description="Custom wrapper description",
            additional_env_vars=env_vars,
            is_critical=True,
        )

        assert result == self.builder

        # Check wrapper generator was called with env vars
        self.mock_wrapper_generator.generate_environment_wrapper.assert_called_once_with(
            "test_env", "complex command", "test_service", env_vars
        )

    @patch(
        "panther.plugins.environments.execution_environment.command_generation_utils.CommandSummarizer"
    )
    def test_add_wrapper_command_deduplication(self, mock_summarizer):
        """Test wrapper command deduplication."""
        mock_summarizer.summarize_single_command.return_value = "wrapper setup..."
        self.mock_wrapper_generator.generate_environment_wrapper.return_value = (
            "wrapper"
        )

        # Add the same wrapper command twice
        self.builder.add_wrapper_command("duplicate command")
        self.builder.add_wrapper_command("duplicate command")

        # Should only be called once due to deduplication
        assert self.mock_wrapper_generator.generate_environment_wrapper.call_count == 1
        assert len(self.builder._wrapper_commands) == 1

        # Should log about skipping duplicate
        debug_calls = [call[0][0] for call in self.mock_logger.debug.call_args_list]
        assert any("Skipping duplicate wrapper command" in call for call in debug_calls)

    def test_add_conditional_wrapper(self):
        """Test adding a conditional wrapper command."""
        self.mock_wrapper_generator.generate_conditional_wrapper.return_value = (
            "conditional wrapper"
        )

        result = self.builder.add_conditional_wrapper(
            condition="command -v strace",
            wrapper_command="strace -o trace.out",
            description="Conditional strace",
            fallback_message="strace not available",
            is_critical=False,
        )

        assert result == self.builder

        # Check wrapper generator was called
        self.mock_wrapper_generator.generate_conditional_wrapper.assert_called_once_with(
            "command -v strace",
            "test_env",
            "strace -o trace.out",
            "test_service",
            "strace not available",
        )

        # Check command was added
        assert len(self.builder._wrapper_commands) == 1
        assert self.builder._wrapper_commands[0] == "conditional wrapper"

    def test_add_post_processing(self):
        """Test adding post-processing command."""
        self.mock_wrapper_generator.generate_post_processing_command.return_value = (
            "post process cmd"
        )

        result = self.builder.add_post_processing(
            input_file="/tmp/input.prof",
            output_file="/tmp/output.txt",
            processing_command="pprof --text /tmp/input.prof > /tmp/output.txt",
            description="Profile analysis",
            file_type="analysis",
            error_message="Analysis failed",
        )

        assert result == self.builder

        # Check wrapper generator was called
        self.mock_wrapper_generator.generate_post_processing_command.assert_called_once_with(
            "/tmp/input.prof",
            "/tmp/output.txt",
            "pprof --text /tmp/input.prof > /tmp/output.txt",
            "test_service",
            "Profile analysis",
            "Analysis failed",
        )

        # Check command was added
        assert len(self.builder._post_run_commands) == 1
        assert self.builder._post_run_commands[0] == "post process cmd"

        # Check output file registration
        self.mock_output_manager.register_output_file.assert_called_once_with(
            "analysis",
            "/tmp/output.txt",
            "test_service",
            "Profile analysis",
            is_primary=False,
        )

    def test_add_post_processing_without_file_type(self):
        """Test adding post-processing command without file type registration."""
        self.mock_wrapper_generator.generate_post_processing_command.return_value = (
            "post process cmd"
        )

        self.builder.add_post_processing(
            input_file="/tmp/input.prof",
            output_file="/tmp/output.txt",
            processing_command="pprof --text /tmp/input.prof > /tmp/output.txt",
            description="Profile analysis",
        )

        # Should not register output file when file_type is None
        self.mock_output_manager.register_output_file.assert_not_called()

    def test_register_output_file(self):
        """Test output file registration through builder."""
        self.mock_output_manager.generate_output_path.return_value = (
            "/app/logs/test_service_profile_20250101_120000.prof"
        )

        file_path = self.builder.register_output_file(
            file_type="profile",
            extension="prof",
            description="CPU profile",
            base_dir="/custom/logs",
        )

        # Check path generation
        self.mock_output_manager.generate_output_path.assert_called_once_with(
            "test_service", "profile", "20250101_120000", "prof", "/custom/logs"
        )

        # Check file registration
        self.mock_output_manager.register_output_file.assert_called_once_with(
            "profile",
            "/app/logs/test_service_profile_20250101_120000.prof",
            "test_service",
            "CPU profile",
            is_primary=True,
        )

        # Check returned path
        assert file_path == "/app/logs/test_service_profile_20250101_120000.prof"

    @patch(
        "panther.plugins.environments.execution_environment.command_generation_utils.CommandSummarizer"
    )
    def test_build_and_apply_wrapper_only(self, mock_summarizer):
        """Test building and applying wrapper commands only."""
        mock_summarizer.summarize_command_list.return_value = "wrapper commands..."

        # Add wrapper command
        self.mock_wrapper_generator.generate_environment_wrapper.return_value = (
            "wrapper1"
        )
        self.builder.add_wrapper_command("wrapper command 1")

        # Mock command builder processing
        with patch.object(
            self.builder.command_builder, "process_commands"
        ) as mock_process:
            mock_process.return_value = [{"command": "wrapper1"}]

            # Mock command modifier callback
            mock_modifier = Mock()
            mock_modifier.return_value = {"modified": True}

            results = self.builder.build_and_apply(mock_modifier)

            # Check command processing
            mock_process.assert_called_once()

            # Check wrapper command application
            mock_modifier.assert_called_once_with(
                self.mock_service, "test_env_wrapper", {"pre_run_cmds": ["wrapper1"]}
            )

            # Check results
            assert "wrapper_modifications" in results
            assert results["wrapper_modifications"] == {"modified": True}
            assert "post_processing_modifications" not in results

            # Check service environment marking
            assert hasattr(self.mock_service, "environments")
            assert self.mock_service.environments["TEST_ENV"] is True

            # Check logging
            info_calls = [call[0][0] for call in self.mock_logger.info.call_args_list]
            assert any(
                "Applied test_env wrapper to service test_service" in call
                for call in info_calls
            )

    @patch(
        "panther.plugins.environments.execution_environment.command_generation_utils.CommandSummarizer"
    )
    def test_build_and_apply_post_processing_only(self, mock_summarizer):
        """Test building and applying post-processing commands only."""
        mock_summarizer.summarize_command_list.return_value = "post commands..."

        # Add post-processing command
        self.mock_wrapper_generator.generate_post_processing_command.return_value = (
            "post1"
        )
        self.builder.add_post_processing(
            "/tmp/input", "/tmp/output", "process", "Analysis"
        )

        # Mock command builder processing
        with patch.object(
            self.builder.command_builder, "process_commands"
        ) as mock_process:
            mock_process.return_value = [{"command": "post1"}]

            # Mock command modifier callback
            mock_modifier = Mock()
            mock_modifier.return_value = {"post_modified": True}

            results = self.builder.build_and_apply(mock_modifier)

            # Check post-processing command application
            mock_modifier.assert_called_once_with(
                self.mock_service,
                "test_env_post_processing",
                {"post_run_cmds": ["post1"]},
            )

            # Check results
            assert "post_processing_modifications" in results
            assert results["post_processing_modifications"] == {"post_modified": True}
            assert "wrapper_modifications" not in results

    @patch(
        "panther.plugins.environments.execution_environment.command_generation_utils.CommandSummarizer"
    )
    def test_build_and_apply_both_types(self, mock_summarizer):
        """Test building and applying both wrapper and post-processing commands."""
        mock_summarizer.summarize_command_list.return_value = "commands..."

        # Add both types of commands
        self.mock_wrapper_generator.generate_environment_wrapper.return_value = (
            "wrapper1"
        )
        self.mock_wrapper_generator.generate_post_processing_command.return_value = (
            "post1"
        )

        self.builder.add_wrapper_command("wrapper command")
        self.builder.add_post_processing(
            "/tmp/input", "/tmp/output", "process", "Analysis"
        )

        # Mock command builder processing
        with patch.object(
            self.builder.command_builder, "process_commands"
        ) as mock_process:
            mock_process.return_value = [{"command": "wrapper1"}, {"command": "post1"}]

            # Mock command modifier callback
            mock_modifier = Mock()
            mock_modifier.side_effect = [
                {"wrapper_result": True},
                {"post_result": True},
            ]

            results = self.builder.build_and_apply(mock_modifier)

            # Check both types were applied
            assert mock_modifier.call_count == 2

            expected_calls = [
                call(
                    self.mock_service,
                    "test_env_wrapper",
                    {"pre_run_cmds": ["wrapper1"]},
                ),
                call(
                    self.mock_service,
                    "test_env_post_processing",
                    {"post_run_cmds": ["post1"]},
                ),
            ]
            mock_modifier.assert_has_calls(expected_calls)

            # Check results contain both
            assert "wrapper_modifications" in results
            assert "post_processing_modifications" in results

    def test_build_and_apply_no_commands(self):
        """Test building and applying with no commands."""
        # Mock command builder processing to return empty
        with patch.object(
            self.builder.command_builder, "process_commands"
        ) as mock_process:
            mock_process.return_value = []

            mock_modifier = Mock()

            results = self.builder.build_and_apply(mock_modifier)

            # Should return empty results and warn
            assert results == {}
            mock_modifier.assert_not_called()

            # Check warning was logged
            self.mock_logger.warning.assert_called_once()
            assert "No commands were processed" in str(
                self.mock_logger.warning.call_args
            )

    def test_build_and_apply_service_environment_creation(self):
        """Test that service environments dict is created if missing."""
        # Remove environments attribute
        if hasattr(self.mock_service, "environments"):
            del self.mock_service.environments

        # Add a wrapper command
        self.mock_wrapper_generator.generate_environment_wrapper.return_value = (
            "wrapper1"
        )
        self.builder.add_wrapper_command("wrapper command")

        with patch.object(
            self.builder.command_builder, "process_commands"
        ) as mock_process:
            mock_process.return_value = [{"command": "wrapper1"}]

            mock_modifier = Mock()
            self.builder.build_and_apply(mock_modifier)

            # Check environments dict was created
            assert hasattr(self.mock_service, "environments")
            assert self.mock_service.environments["TEST_ENV"] is True


class TestCommandGenerationUtilsFactory:
    """Test suite for CommandGenerationUtilsFactory class."""

    def test_create_output_file_manager(self):
        """Test creating OutputFileManager via factory."""
        mock_callback = Mock()
        mock_logger = Mock(spec=logging.Logger)

        manager = CommandGenerationUtilsFactory.create_output_file_manager(
            mock_callback, mock_logger
        )

        assert isinstance(manager, OutputFileManager)
        assert manager.register_output_callback == mock_callback
        assert manager.logger == mock_logger

    def test_create_output_file_manager_without_logger(self):
        """Test creating OutputFileManager via factory without logger."""
        mock_callback = Mock()

        manager = CommandGenerationUtilsFactory.create_output_file_manager(
            mock_callback
        )

        assert isinstance(manager, OutputFileManager)
        assert manager.register_output_callback == mock_callback
        assert manager.logger is not None

    def test_create_wrapper_generator(self):
        """Test creating WrapperCommandGenerator via factory."""
        mock_logger = Mock(spec=logging.Logger)

        generator = CommandGenerationUtilsFactory.create_wrapper_generator(mock_logger)

        assert isinstance(generator, WrapperCommandGenerator)
        assert generator.logger == mock_logger

    def test_create_wrapper_generator_without_logger(self):
        """Test creating WrapperCommandGenerator via factory without logger."""
        generator = CommandGenerationUtilsFactory.create_wrapper_generator()

        assert isinstance(generator, WrapperCommandGenerator)
        assert generator.logger is not None

    @patch(
        "panther.plugins.environments.execution_environment.command_generation_utils.CommandGenerationUtilsFactory.create_output_file_manager"
    )
    @patch(
        "panther.plugins.environments.execution_environment.command_generation_utils.CommandGenerationUtilsFactory.create_wrapper_generator"
    )
    def test_create_command_builder(self, mock_create_generator, mock_create_manager):
        """Test creating ExecutionEnvironmentCommandBuilder via factory."""
        mock_service = Mock(spec=IServiceManager)
        mock_service.service_name = "test_service"
        mock_service.role = ProtocolRole.SERVER
        mock_callback = Mock()
        mock_logger = Mock(spec=logging.Logger)

        # Mock the factory methods
        mock_output_manager = Mock(spec=OutputFileManager)
        mock_wrapper_generator = Mock(spec=WrapperCommandGenerator)
        mock_create_manager.return_value = mock_output_manager
        mock_create_generator.return_value = mock_wrapper_generator

        builder = CommandGenerationUtilsFactory.create_command_builder(
            service=mock_service,
            environment_name="test_env",
            timestamp="20250101_120000",
            register_output_callback=mock_callback,
            logger=mock_logger,
        )

        # Check factory methods were called
        mock_create_manager.assert_called_once_with(mock_callback, mock_logger)
        mock_create_generator.assert_called_once_with(mock_logger)

        # Check builder was created correctly
        assert isinstance(builder, ExecutionEnvironmentCommandBuilder)
        assert builder.service == mock_service
        assert builder.environment_name == "test_env"
        assert builder.timestamp == "20250101_120000"
        assert builder.output_file_manager == mock_output_manager
        assert builder.wrapper_generator == mock_wrapper_generator
        assert builder.logger == mock_logger


class TestConvenienceFunction:
    """Test suite for the convenience function."""

    @patch(
        "panther.plugins.environments.execution_environment.command_generation_utils.CommandGenerationUtilsFactory.create_command_builder"
    )
    def test_create_execution_environment_builder(self, mock_factory_create):
        """Test the convenience function."""
        mock_service = Mock(spec=IServiceManager)
        mock_callback = Mock()
        mock_logger = Mock(spec=logging.Logger)
        mock_builder = Mock(spec=ExecutionEnvironmentCommandBuilder)

        mock_factory_create.return_value = mock_builder

        result = create_execution_environment_builder(
            service=mock_service,
            environment_name="test_env",
            timestamp="20250101_120000",
            register_output_callback=mock_callback,
            logger=mock_logger,
        )

        # Check factory was called correctly
        mock_factory_create.assert_called_once_with(
            mock_service, "test_env", "20250101_120000", mock_callback, mock_logger
        )

        # Check correct result returned
        assert result == mock_builder

    @patch(
        "panther.plugins.environments.execution_environment.command_generation_utils.CommandGenerationUtilsFactory.create_command_builder"
    )
    def test_create_execution_environment_builder_without_logger(
        self, mock_factory_create
    ):
        """Test the convenience function without logger."""
        mock_service = Mock(spec=IServiceManager)
        mock_callback = Mock()
        mock_builder = Mock(spec=ExecutionEnvironmentCommandBuilder)

        mock_factory_create.return_value = mock_builder

        result = create_execution_environment_builder(
            service=mock_service,
            environment_name="test_env",
            timestamp="20250101_120000",
            register_output_callback=mock_callback,
        )

        # Check factory was called with None logger
        mock_factory_create.assert_called_once_with(
            mock_service, "test_env", "20250101_120000", mock_callback, None
        )

        assert result == mock_builder


@pytest.mark.unit
class TestCommandGenerationUtilsIntegration:
    """Integration-like tests within unit test scope."""

    def test_full_workflow_simulation(self):
        """Test a complete workflow simulation using all utilities."""
        # Create real instances (not mocks) for integration testing
        mock_callback = Mock()
        logger = logging.getLogger("test")

        # Create service mock
        mock_service = Mock(spec=IServiceManager)
        mock_service.service_name = "integration_service"
        mock_service.role = ProtocolRole.SERVER
        mock_service.run_cmd = {"pre_run_cmds": []}

        # Use the convenience function to create builder
        builder = create_execution_environment_builder(
            service=mock_service,
            environment_name="integration_test",
            timestamp="20250101_120000",
            register_output_callback=mock_callback,
            logger=logger,
        )

        # Verify builder was created correctly
        assert isinstance(builder, ExecutionEnvironmentCommandBuilder)
        assert builder.service_name == "integration_service"
        assert builder.environment_name == "integration_test"

        # Register an output file
        output_path = builder.register_output_file(
            file_type="test_output",
            extension="log",
            description="Integration test output",
        )

        expected_path = "/app/logs/integration_service_test_output_20250101_120000.log"
        assert output_path == expected_path

        # Verify callback was called for output registration
        mock_callback.assert_called_with(
            "test_output", expected_path, "integration_service"
        )

        # Add wrapper command
        builder.add_wrapper_command(
            wrapper_command="echo 'Starting integration test'",
            description="Integration test wrapper",
            additional_env_vars={"TEST_MODE": "integration"},
        )

        # Add post-processing
        builder.add_post_processing(
            input_file="/tmp/input.log",
            output_file="/tmp/processed.log",
            processing_command="cat /tmp/input.log | grep ERROR > /tmp/processed.log",
            description="Error analysis",
        )

        # Verify internal state
        assert len(builder._wrapper_commands) == 1
        assert len(builder._post_run_commands) == 1

        # Test build and apply with mock modifier
        mock_modifier = Mock()
        mock_modifier.side_effect = [{"wrapper": "applied"}, {"post": "applied"}]

        with patch.object(builder.command_builder, "process_commands") as mock_process:
            mock_process.return_value = [
                {"command": "wrapper_cmd"},
                {"command": "post_cmd"},
            ]

            results = builder.build_and_apply(mock_modifier)

            # Verify results
            assert "wrapper_modifications" in results
            assert "post_processing_modifications" in results
            assert results["wrapper_modifications"] == {"wrapper": "applied"}
            assert results["post_processing_modifications"] == {"post": "applied"}

            # Verify service was modified
            assert mock_modifier.call_count == 2

            # Verify environment was marked on service
            assert hasattr(mock_service, "environments")
            assert mock_service.environments["INTEGRATION_TEST"] is True

    def test_output_file_manager_integration(self):
        """Test OutputFileManager with real callback integration."""
        registered_files = []

        def test_callback(file_type, file_path, service_name):
            registered_files.append((file_type, file_path, service_name))

        manager = OutputFileManager(test_callback)

        # Register multiple files
        spec1 = manager.register_output_file(
            "profile", "/tmp/profile1.prof", "service1", "CPU profile"
        )
        spec2 = manager.register_output_file(
            "trace", "/tmp/trace1.out", "service1", "System calls"
        )
        spec3 = manager.register_output_file(
            "profile", "/tmp/profile2.prof", "service2", "Memory profile"
        )

        # Verify callback was called for each registration
        assert len(registered_files) == 3
        assert ("profile", "/tmp/profile1.prof", "service1") in registered_files
        assert ("trace", "/tmp/trace1.out", "service1") in registered_files
        assert ("profile", "/tmp/profile2.prof", "service2") in registered_files

        # Test filtering by service
        service1_files = manager.get_registered_files("service1")
        assert len(service1_files) == 2
        assert spec1 in service1_files
        assert spec2 in service1_files
        assert spec3 not in service1_files

        # Test path generation
        path = manager.generate_output_path(
            "test_service", "analysis", "20250101_120000", "txt", "/custom"
        )
        assert path == "/custom/test_service_analysis_20250101_120000.txt"

    def test_wrapper_command_generator_integration(self):
        """Test WrapperCommandGenerator with complex scenarios."""
        generator = WrapperCommandGenerator()

        # Test complex environment wrapper
        wrapper = generator.generate_environment_wrapper(
            environment_name="complex_profiler",
            wrapper_command="profiler --start --output=/tmp/prof.out",
            service_name="performance_test",
            additional_env_vars={
                "PROFILER_MODE": "detailed",
                "PROFILER_INTERVAL": "1000",
                "PROFILER_THREADS": "all",
            },
        )

        # Verify structure and content
        assert "# Setup complex_profiler wrapper for performance_test" in wrapper
        assert "export PROFILER_MODE=detailed" in wrapper
        assert "export PROFILER_INTERVAL=1000" in wrapper
        assert "export PROFILER_THREADS=all" in wrapper
        assert "profiler --start --output=/tmp/prof.out" in wrapper
        assert "/app/logs/performance_test_exec_env_setup.log" in wrapper

        # Test conditional wrapper with complex condition
        conditional = generator.generate_conditional_wrapper(
            condition="[ -x /usr/bin/profiler ] && [ -w /tmp ]",
            environment_name="conditional_profiler",
            wrapper_command="profiler --safe-mode",
            service_name="safe_service",
            fallback_message="Profiler not available or /tmp not writable",
        )

        # Verify conditional structure
        assert "if [ -x /usr/bin/profiler ] && [ -w /tmp ]; then" in conditional
        assert "profiler --safe-mode" in conditional
        assert "else" in conditional
        assert "Profiler not available or /tmp not writable" in conditional
        assert "fi" in conditional

        # Test post-processing with error handling
        post_cmd = generator.generate_post_processing_command(
            input_file="/tmp/raw_profile.prof",
            output_file="/tmp/human_readable.txt",
            processing_command="pprof --text /tmp/raw_profile.prof > /tmp/human_readable.txt",
            service_name="analysis_service",
            description="Profile text conversion",
            error_message="Failed to convert profile to text format",
        )

        # Verify post-processing structure
        assert "# Profile text conversion for analysis_service" in post_cmd
        assert 'if [ -f "/tmp/raw_profile.prof" ]' in post_cmd
        assert (
            "pprof --text /tmp/raw_profile.prof > /tmp/human_readable.txt" in post_cmd
        )
        assert '|| echo "Failed to convert profile to text format"' in post_cmd
        assert "Generated Profile text conversion: /tmp/human_readable.txt" in post_cmd
        assert "Input file not found: /tmp/raw_profile.prof" in post_cmd
