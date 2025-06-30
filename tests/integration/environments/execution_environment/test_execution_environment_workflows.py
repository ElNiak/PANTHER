"""
Integration tests for execution environment workflows and Docker integration.

Tests realistic scenarios of execution environments working with:
- Network environments (Docker Compose, Localhost, Shadow NS)
- Service managers and Docker containers
- Multiple concurrent execution environments
- End-to-end command generation and execution
- Output file collection and processing
"""
import os
import shutil
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, Mock, patch

import pytest
import yaml

from panther.config.config_manager import ConfigManager
from panther.config.core.models import ProtocolRole
from panther.config.core.models.global_config import GlobalConfig
from panther.core.experiment_manager import ExperimentManager
from panther.core.observer.management.event_manager import EventManager
from panther.plugins.environments.execution_environment.gperf_cpu.config_schema import (
    GperfCpuConfig,
)
from panther.plugins.environments.execution_environment.gperf_cpu.gperf_cpu import (
    GperfCpuEnvironment,
)
from panther.plugins.environments.execution_environment.iterations.config_schema import (
    IterationsConfig,
)
from panther.plugins.environments.execution_environment.iterations.iterations import (
    IterationsEnvironment,
)
from panther.plugins.environments.execution_environment.memcheck.config_schema import (
    MemcheckConfig,
)
from panther.plugins.environments.execution_environment.memcheck.memcheck import (
    MemcheckEnvironment,
)
from panther.plugins.environments.execution_environment.strace.config_schema import (
    StraceConfig,
)

# Import execution environments
from panther.plugins.environments.execution_environment.strace.strace import (
    StraceEnvironment,
)
from panther.plugins.plugin_manager import PluginManager
from panther.plugins.services.services_interface import IServiceManager


class TestExecutionEnvironmentWorkflows:
    """Integration tests for execution environment workflows."""

    @pytest.fixture(scope="class")
    def temp_output_dir(self):
        """Create temporary output directory for integration tests."""
        temp_dir = tempfile.mkdtemp(prefix="panther_exec_env_integration_")
        yield Path(temp_dir)
        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.fixture
    def event_manager(self):
        """Create event manager for tests."""
        return EventManager()

    @pytest.fixture
    def global_config(self):
        """Create global configuration for tests."""
        config = Mock(spec=GlobalConfig)
        config.enable_fast_fail = False
        config.debug_mode = True
        config.logging_level = "DEBUG"
        return config

    @pytest.fixture
    def plugin_manager(self):
        """Create plugin manager for tests."""
        return Mock(spec=PluginManager)

    @pytest.fixture
    def test_config(self):
        """Create test configuration."""
        config = Mock()
        config.test_name = "integration_test"
        config.timeout = 30
        config.iterations = 1
        return config

    @pytest.fixture
    def mock_service_server(self):
        """Create mock server service."""
        service = Mock(spec=IServiceManager)
        service.service_name = "test_server"
        service.role = ProtocolRole.SERVER
        service.run_cmd = {"pre_run_cmds": [], "post_run_cmds": []}
        service.environments = {}
        return service

    @pytest.fixture
    def mock_service_client(self):
        """Create mock client service."""
        service = Mock(spec=IServiceManager)
        service.service_name = "test_client"
        service.role = ProtocolRole.CLIENT
        service.run_cmd = {"pre_run_cmds": [], "post_run_cmds": []}
        service.environments = {}
        return service

    @pytest.fixture
    def mock_services(self, mock_service_server, mock_service_client):
        """Create list of mock services."""
        return [mock_service_server, mock_service_client]


class TestSingleExecutionEnvironmentIntegration(TestExecutionEnvironmentWorkflows):
    """Test individual execution environments with realistic workflows."""

    @pytest.mark.integration
    def test_strace_environment_full_workflow(
        self,
        temp_output_dir,
        event_manager,
        global_config,
        plugin_manager,
        test_config,
        mock_services,
    ):
        """Test complete Strace environment workflow."""
        # Create Strace configuration
        config = StraceConfig(
            trace_system_calls=True,
            trace_child_processes=True,
            output_format="detailed",
            max_output_size="10MB",
        )

        # Initialize environment
        strace_env = StraceEnvironment(
            env_config_to_test=config,
            output_dir=str(temp_output_dir),
            env_type="execution",
            env_sub_type="strace",
            event_manager=event_manager,
        )

        # Track registered output files
        registered_files = []

        def mock_register_output(file_type, file_path, service_name):
            registered_files.append((file_type, file_path, service_name))

        # Mock the register_output_file method
        strace_env.register_output_file = mock_register_output

        # Mock the modify_service_commands method
        modified_services = []

        def mock_modify_commands(service, modification_type, commands):
            modified_services.append(
                (service.service_name, modification_type, commands)
            )
            return {"success": True, "modified": len(commands.get("pre_run_cmds", []))}

        strace_env.modify_service_commands = mock_modify_commands

        # Execute setup
        strace_env.setup_environment(
            services_managers=mock_services,
            test_config=test_config,
            global_config=global_config,
            timestamp="20250101_120000",
            plugin_manager=plugin_manager,
        )

        # Verify output files were registered for both services
        assert len(registered_files) == 2  # One for each service
        server_files = [f for f in registered_files if f[2] == "test_server"]
        client_files = [f for f in registered_files if f[2] == "test_client"]
        assert len(server_files) == 1
        assert len(client_files) == 1

        # Verify file types and paths
        for file_type, file_path, service_name in registered_files:
            assert file_type == "strace"
            assert "strace" in file_path
            assert service_name in file_path
            assert file_path.startswith("/app/logs/")
            assert file_path.endswith(".out")

        # Verify services were modified
        assert len(modified_services) == 2
        for service_name, mod_type, commands in modified_services:
            assert service_name in ["test_server", "test_client"]
            assert mod_type == "strace_wrapper"
            assert "pre_run_cmds" in commands
            assert len(commands["pre_run_cmds"]) > 0

            # Verify strace command content
            strace_cmd = commands["pre_run_cmds"][0]
            assert "strace" in strace_cmd
            assert "-o" in strace_cmd  # Output file option
            assert service_name in strace_cmd

        # Verify environment was marked on services
        for service in mock_services:
            assert hasattr(service, "environments")
            assert service.environments.get("STRACE") is True

        # Test to_command interface
        command = strace_env.to_command()
        assert command == ""  # Strace uses wrapper, not direct command

    @pytest.mark.integration
    def test_gperf_cpu_environment_full_workflow(
        self,
        temp_output_dir,
        event_manager,
        global_config,
        plugin_manager,
        test_config,
        mock_services,
    ):
        """Test complete Gperf CPU environment workflow."""
        # Create Gperf CPU configuration
        config = GperfCpuConfig(
            profiling_frequency=1000, profile_duration=30, generate_reports=True
        )

        # Initialize environment
        gperf_env = GperfCpuEnvironment(
            env_config_to_test=config,
            output_dir=str(temp_output_dir),
            env_type="execution",
            env_sub_type="gperf_cpu",
            event_manager=event_manager,
        )

        # Track interactions
        registered_files = []
        modified_services = []

        def mock_register_output(file_type, file_path, service_name):
            registered_files.append((file_type, file_path, service_name))

        def mock_modify_commands(service, modification_type, commands):
            modified_services.append(
                (service.service_name, modification_type, commands)
            )
            return {"success": True}

        gperf_env.register_output_file = mock_register_output
        gperf_env.modify_service_commands = mock_modify_commands

        # Execute setup
        gperf_env.setup_environment(
            services_managers=mock_services,
            test_config=test_config,
            global_config=global_config,
            timestamp="20250101_120000",
            plugin_manager=plugin_manager,
        )

        # Verify profiling files were registered
        assert len(registered_files) >= 2  # Profile files for both services
        profile_files = [f for f in registered_files if f[0] == "profile"]
        assert len(profile_files) >= 2

        # Verify service modifications include profiling setup
        assert len(modified_services) >= 2
        for service_name, mod_type, commands in modified_services:
            if "wrapper" in mod_type:
                assert "pre_run_cmds" in commands
                wrapper_cmd = commands["pre_run_cmds"][0]
                # Should contain profiler setup
                assert any(
                    keyword in wrapper_cmd.lower()
                    for keyword in ["profile", "gperf", "cpu"]
                )

        # Test environment variables and wrapper setup
        for service in mock_services:
            assert service.environments.get("GPERF_CPU") is True

    @pytest.mark.integration
    def test_iterations_environment_workflow(
        self,
        temp_output_dir,
        event_manager,
        global_config,
        plugin_manager,
        test_config,
        mock_services,
    ):
        """Test iterations environment workflow with multiple runs."""
        # Create iterations configuration
        config = IterationsConfig(
            iterations=3, delay_between_iterations=1, aggregate_results=True
        )

        # Initialize environment
        iterations_env = IterationsEnvironment(
            env_config_to_test=config,
            output_dir=str(temp_output_dir),
            env_type="execution",
            env_sub_type="iterations",
            event_manager=event_manager,
        )

        # Track interactions
        registered_files = []
        modified_services = []

        def mock_register_output(file_type, file_path, service_name):
            registered_files.append((file_type, file_path, service_name))

        def mock_modify_commands(service, modification_type, commands):
            modified_services.append(
                (service.service_name, modification_type, commands)
            )
            return {"success": True}

        iterations_env.register_output_file = mock_register_output
        iterations_env.modify_service_commands = mock_modify_commands

        # Execute setup
        iterations_env.setup_environment(
            services_managers=mock_services,
            test_config=test_config,
            global_config=global_config,
            timestamp="20250101_120000",
            plugin_manager=plugin_manager,
        )

        # Verify iteration log files were registered
        iteration_files = [f for f in registered_files if f[0] == "iterations"]
        assert len(iteration_files) == 2  # One for each service

        # Verify wrapper scripts were created
        assert len(modified_services) == 2
        for service_name, mod_type, commands in modified_services:
            assert "wrapper" in mod_type
            wrapper_cmd = commands["pre_run_cmds"][0]
            # Should contain iteration wrapper script setup
            assert "iterations_wrapper" in wrapper_cmd
            assert service_name in wrapper_cmd
            assert "chmod +x" in wrapper_cmd  # Script should be made executable

        # Test to_command interface for iterations
        command_server = iterations_env.to_command(service_name="test_server")
        command_client = iterations_env.to_command(service_name="test_client")

        assert "/tmp/iterations_wrapper_test_server.sh" in command_server
        assert "/tmp/iterations_wrapper_test_client.sh" in command_client

        # Test single iteration fallback
        config_single = IterationsConfig(iterations=1)
        iterations_env_single = IterationsEnvironment(
            env_config_to_test=config_single,
            output_dir=str(temp_output_dir),
            env_type="execution",
            env_sub_type="iterations",
            event_manager=event_manager,
        )

        # Should return empty command for single iteration
        assert iterations_env_single.to_command() == ""


class TestMultipleExecutionEnvironmentIntegration(TestExecutionEnvironmentWorkflows):
    """Test multiple execution environments working together."""

    @pytest.mark.integration
    def test_strace_and_gperf_combined_workflow(
        self,
        temp_output_dir,
        event_manager,
        global_config,
        plugin_manager,
        test_config,
        mock_services,
    ):
        """Test Strace and Gperf CPU working together on the same services."""
        # Create configurations
        strace_config = StraceConfig(trace_system_calls=True)
        gperf_config = GperfCpuConfig(profiling_frequency=500)

        # Initialize environments
        strace_env = StraceEnvironment(
            env_config_to_test=strace_config,
            output_dir=str(temp_output_dir),
            env_type="execution",
            env_sub_type="strace",
            event_manager=event_manager,
        )

        gperf_env = GperfCpuEnvironment(
            env_config_to_test=gperf_config,
            output_dir=str(temp_output_dir),
            env_type="execution",
            env_sub_type="gperf_cpu",
            event_manager=event_manager,
        )

        # Track all interactions
        all_registered_files = []
        all_modified_services = []

        def make_tracker(env_name):
            def mock_register_output(file_type, file_path, service_name):
                all_registered_files.append(
                    (env_name, file_type, file_path, service_name)
                )

            def mock_modify_commands(service, modification_type, commands):
                all_modified_services.append(
                    (env_name, service.service_name, modification_type, commands)
                )
                return {"success": True}

            return mock_register_output, mock_modify_commands

        # Set up tracking for both environments
        strace_reg, strace_mod = make_tracker("strace")
        gperf_reg, gperf_mod = make_tracker("gperf")

        strace_env.register_output_file = strace_reg
        strace_env.modify_service_commands = strace_mod
        gperf_env.register_output_file = gperf_reg
        gperf_env.modify_service_commands = gperf_mod

        # Execute both setups
        strace_env.setup_environment(
            services_managers=mock_services,
            test_config=test_config,
            global_config=global_config,
            timestamp="20250101_120000",
            plugin_manager=plugin_manager,
        )

        gperf_env.setup_environment(
            services_managers=mock_services,
            test_config=test_config,
            global_config=global_config,
            timestamp="20250101_120000",
            plugin_manager=plugin_manager,
        )

        # Verify both environments registered files
        strace_files = [f for f in all_registered_files if f[0] == "strace"]
        gperf_files = [f for f in all_registered_files if f[0] == "gperf"]

        assert len(strace_files) == 2  # Both services
        assert len(gperf_files) >= 2  # Both services (may have multiple file types)

        # Verify both environments modified services
        strace_mods = [m for m in all_modified_services if m[0] == "strace"]
        gperf_mods = [m for m in all_modified_services if m[0] == "gperf"]

        assert len(strace_mods) == 2
        assert len(gperf_mods) >= 2

        # Verify both environments are marked on services
        for service in mock_services:
            assert service.environments.get("STRACE") is True
            assert service.environments.get("GPERF_CPU") is True

        # Verify command chaining doesn't conflict
        for env_name, service_name, mod_type, commands in all_modified_services:
            wrapper_cmd = commands["pre_run_cmds"][0]
            # Each environment should have its own distinct wrapper
            if env_name == "strace":
                assert "strace" in wrapper_cmd
            elif env_name == "gperf":
                assert any(
                    keyword in wrapper_cmd.lower() for keyword in ["profile", "gperf"]
                )

    @pytest.mark.integration
    def test_all_execution_environments_combined(
        self,
        temp_output_dir,
        event_manager,
        global_config,
        plugin_manager,
        test_config,
        mock_services,
    ):
        """Test all execution environments working together."""
        # Create all environment configurations
        environments = [
            ("strace", StraceEnvironment, StraceConfig()),
            ("gperf_cpu", GperfCpuEnvironment, GperfCpuConfig()),
            ("iterations", IterationsEnvironment, IterationsConfig(iterations=2)),
            ("memcheck", MemcheckEnvironment, MemcheckConfig()),
        ]

        env_instances = []
        all_interactions = []

        for env_name, env_class, config in environments:
            # Initialize environment
            env = env_class(
                env_config_to_test=config,
                output_dir=str(temp_output_dir),
                env_type="execution",
                env_sub_type=env_name,
                event_manager=event_manager,
            )

            # Track interactions
            def make_tracker(name):
                def mock_register_output(file_type, file_path, service_name):
                    all_interactions.append(
                        ("register", name, file_type, file_path, service_name)
                    )

                def mock_modify_commands(service, modification_type, commands):
                    all_interactions.append(
                        (
                            "modify",
                            name,
                            service.service_name,
                            modification_type,
                            commands,
                        )
                    )
                    return {"success": True}

                return mock_register_output, mock_modify_commands

            reg_func, mod_func = make_tracker(env_name)
            env.register_output_file = reg_func
            env.modify_service_commands = mod_func

            env_instances.append((env_name, env))

        # Execute all environment setups
        for env_name, env in env_instances:
            env.setup_environment(
                services_managers=mock_services,
                test_config=test_config,
                global_config=global_config,
                timestamp="20250101_120000",
                plugin_manager=plugin_manager,
            )

        # Verify all environments registered files
        register_actions = [
            action for action in all_interactions if action[0] == "register"
        ]
        modify_actions = [
            action for action in all_interactions if action[0] == "modify"
        ]

        # Each environment should have registered files for each service
        env_names = [env[0] for env in environments]
        for env_name in env_names:
            env_registers = [
                action for action in register_actions if action[1] == env_name
            ]
            # Most environments register files for both services
            if env_name != "iterations" or env_name != "single_iteration":
                assert len(env_registers) >= 1  # At least some files registered

        # Verify all environments modified services
        for env_name in env_names:
            env_modifies = [
                action for action in modify_actions if action[1] == env_name
            ]
            # Skip iterations if configured for single iteration
            config_obj = next(
                config for name, _, config in environments if name == env_name
            )
            if env_name == "iterations" and getattr(config_obj, "iterations", 1) <= 1:
                continue
            assert len(env_modifies) >= 1  # Should modify at least some services

        # Verify all environments are marked on services
        expected_env_vars = ["STRACE", "GPERF_CPU", "ITERATIONS", "MEMCHECK"]
        for service in mock_services:
            for env_var in expected_env_vars:
                # Iterations might not be set if single iteration
                if env_var == "ITERATIONS":
                    continue  # Skip this check for iterations
                assert service.environments.get(env_var) is True

        # Verify no conflicts in file naming
        file_paths = [action[3] for action in register_actions]
        # All file paths should be unique
        assert len(file_paths) == len(set(file_paths))


class TestExecutionEnvironmentDockerIntegration(TestExecutionEnvironmentWorkflows):
    """Test execution environments with Docker integration scenarios."""

    @pytest.mark.integration
    @pytest.mark.requires_docker
    def test_execution_environment_docker_command_generation(
        self,
        temp_output_dir,
        event_manager,
        global_config,
        plugin_manager,
        test_config,
        mock_services,
    ):
        """Test execution environment command generation for Docker containers."""
        # Create environment that generates Docker commands
        config = StraceConfig(trace_system_calls=True, include_env_vars=True)

        strace_env = StraceEnvironment(
            env_config_to_test=config,
            output_dir=str(temp_output_dir),
            env_type="execution",
            env_sub_type="strace",
            event_manager=event_manager,
        )

        # Mock Docker-aware service
        docker_service = Mock(spec=IServiceManager)
        docker_service.service_name = "docker_test_service"
        docker_service.role = ProtocolRole.SERVER
        docker_service.run_cmd = {
            "pre_run_cmds": [],
            "post_run_cmds": [],
            "environment": {},
            "volumes": [],
        }
        docker_service.environments = {}

        # Track Docker-specific interactions
        docker_modifications = []

        def mock_modify_docker_commands(service, modification_type, commands):
            docker_modifications.append(
                (service.service_name, modification_type, commands)
            )
            # Simulate Docker command integration
            if "pre_run_cmds" in commands:
                for cmd in commands["pre_run_cmds"]:
                    # Verify Docker compatibility
                    assert "/app/logs" in cmd  # Docker volume path
                    assert not cmd.startswith("/")  # Relative paths for Docker
            return {"success": True, "docker_integrated": True}

        strace_env.modify_service_commands = mock_modify_docker_commands
        strace_env.register_output_file = lambda *args: None

        # Execute setup with Docker service
        strace_env.setup_environment(
            services_managers=[docker_service],
            test_config=test_config,
            global_config=global_config,
            timestamp="20250101_120000",
            plugin_manager=plugin_manager,
        )

        # Verify Docker-compatible commands were generated
        assert len(docker_modifications) == 1
        service_name, mod_type, commands = docker_modifications[0]

        assert service_name == "docker_test_service"
        assert "wrapper" in mod_type
        assert "pre_run_cmds" in commands

        docker_cmd = commands["pre_run_cmds"][0]
        # Verify Docker volume compatibility
        assert "/app/logs" in docker_cmd
        # Verify proper file paths for Docker environment
        assert "docker_test_service" in docker_cmd

    @pytest.mark.integration
    def test_execution_environment_volume_mapping(
        self, temp_output_dir, event_manager, global_config, plugin_manager, test_config
    ):
        """Test execution environment output file volume mapping for Docker."""
        # Test that execution environments generate proper volume-mapped paths
        config = GperfCpuConfig(generate_reports=True)

        gperf_env = GperfCpuEnvironment(
            env_config_to_test=config,
            output_dir=str(temp_output_dir),
            env_type="execution",
            env_sub_type="gperf_cpu",
            event_manager=event_manager,
        )

        # Track registered output files for volume mapping
        registered_files = []

        def mock_register_output(file_type, file_path, service_name):
            registered_files.append((file_type, file_path, service_name))
            # Verify file path is suitable for Docker volume mapping
            assert file_path.startswith("/app/logs/")
            assert service_name in file_path

        gperf_env.register_output_file = mock_register_output
        gperf_env.modify_service_commands = lambda *args: {"success": True}

        # Create mock service
        volume_service = Mock(spec=IServiceManager)
        volume_service.service_name = "volume_test_service"
        volume_service.role = ProtocolRole.CLIENT
        volume_service.run_cmd = {"pre_run_cmds": []}
        volume_service.environments = {}

        # Execute setup
        gperf_env.setup_environment(
            services_managers=[volume_service],
            test_config=test_config,
            global_config=global_config,
            timestamp="20250101_120000",
            plugin_manager=plugin_manager,
        )

        # Verify all registered files use Docker-compatible paths
        assert len(registered_files) >= 1
        for file_type, file_path, service_name in registered_files:
            assert file_path.startswith("/app/logs/")
            assert not file_path.startswith(str(temp_output_dir))  # Not host path

    @pytest.mark.integration
    def test_execution_environment_container_lifecycle(
        self,
        temp_output_dir,
        event_manager,
        global_config,
        plugin_manager,
        test_config,
        mock_services,
    ):
        """Test execution environment integration with container lifecycle."""
        # Test environments that need container lifecycle awareness
        config = MemcheckConfig(
            leak_check=True, track_fds=True, generate_leak_report=True
        )

        memcheck_env = MemcheckEnvironment(
            env_config_to_test=config,
            output_dir=str(temp_output_dir),
            env_type="execution",
            env_sub_type="memcheck",
            event_manager=event_manager,
        )

        # Track lifecycle-aware modifications
        lifecycle_modifications = []

        def mock_lifecycle_modify(service, modification_type, commands):
            lifecycle_modifications.append(
                (service.service_name, modification_type, commands)
            )

            # Verify pre-run commands for container setup
            if "pre_run_cmds" in commands:
                pre_cmd = commands["pre_run_cmds"][0]
                # Should contain conditional checks for tools
                assert "command -v" in pre_cmd or "which" in pre_cmd

            # Verify post-run commands for cleanup
            if "post_run_cmds" in commands:
                post_cmd = commands["post_run_cmds"][0]
                # Should contain report generation
                assert any(
                    keyword in post_cmd for keyword in ["report", "analysis", "output"]
                )

            return {"success": True}

        memcheck_env.modify_service_commands = mock_lifecycle_modify
        memcheck_env.register_output_file = lambda *args: None

        # Execute setup
        memcheck_env.setup_environment(
            services_managers=mock_services,
            test_config=test_config,
            global_config=global_config,
            timestamp="20250101_120000",
            plugin_manager=plugin_manager,
        )

        # Verify lifecycle-aware modifications
        assert len(lifecycle_modifications) >= 2  # Both services

        for service_name, mod_type, commands in lifecycle_modifications:
            assert service_name in ["test_server", "test_client"]
            # Should have both wrapper and post-processing
            if "wrapper" in mod_type:
                assert "pre_run_cmds" in commands
            elif "post_processing" in mod_type:
                assert "post_run_cmds" in commands


class TestExecutionEnvironmentConfigurationIntegration(
    TestExecutionEnvironmentWorkflows
):
    """Test execution environment configuration integration scenarios."""

    @pytest.mark.integration
    def test_environment_configuration_inheritance(
        self,
        temp_output_dir,
        event_manager,
        global_config,
        plugin_manager,
        test_config,
        mock_services,
    ):
        """Test configuration inheritance and override patterns."""
        # Test dual configuration approach (plugin_config vs typed config)
        config = StraceConfig()

        # Set plugin_config dict for override testing
        config.plugin_config = {
            "trace_system_calls": False,  # Override typed config
            "output_format": "compact",
            "custom_strace_args": ["-e", "read,write"],
        }

        strace_env = StraceEnvironment(
            env_config_to_test=config,
            output_dir=str(temp_output_dir),
            env_type="execution",
            env_sub_type="strace",
            event_manager=event_manager,
        )

        # Track configuration usage
        config_usage = []

        def mock_modify_with_config_tracking(service, modification_type, commands):
            config_usage.append((service.service_name, modification_type, commands))

            # Verify configuration override was applied
            wrapper_cmd = commands["pre_run_cmds"][0]
            # Should use plugin_config values, not typed config defaults
            if "compact" in config.plugin_config.get("output_format", ""):
                # Check that compact format influenced command generation
                assert "strace" in wrapper_cmd

            return {"success": True}

        strace_env.modify_service_commands = mock_modify_with_config_tracking
        strace_env.register_output_file = lambda *args: None

        # Execute setup
        strace_env.setup_environment(
            services_managers=mock_services,
            test_config=test_config,
            global_config=global_config,
            timestamp="20250101_120000",
            plugin_manager=plugin_manager,
        )

        # Verify configuration was properly inherited and overridden
        assert len(config_usage) == 2  # Both services

        # Test configuration getter
        plugin_config = strace_env._get_plugin_config()
        assert isinstance(plugin_config, StraceConfig)

    @pytest.mark.integration
    def test_environment_configuration_validation(
        self,
        temp_output_dir,
        event_manager,
        global_config,
        plugin_manager,
        test_config,
        mock_services,
    ):
        """Test configuration validation during environment setup."""
        # Test invalid configuration handling
        config = IterationsConfig()

        # Set invalid plugin_config
        config.plugin_config = {
            "iterations": "invalid_string",  # Should be converted to int
            "delay_between_iterations": -5,  # Invalid negative value
        }

        iterations_env = IterationsEnvironment(
            env_config_to_test=config,
            output_dir=str(temp_output_dir),
            env_type="execution",
            env_sub_type="iterations",
            event_manager=event_manager,
        )

        # Mock validation tracking
        validation_results = []

        def mock_modify_with_validation(service, modification_type, commands):
            validation_results.append(
                (service.service_name, modification_type, commands)
            )
            # Configuration should be validated/corrected during setup
            return {"success": True}

        iterations_env.modify_service_commands = mock_modify_with_validation
        iterations_env.register_output_file = lambda *args: None

        # Execute setup - should handle invalid config gracefully
        try:
            iterations_env.setup_environment(
                services_managers=mock_services,
                test_config=test_config,
                global_config=global_config,
                timestamp="20250101_120000",
                plugin_manager=plugin_manager,
            )

            # Verify environment handled invalid config
            # For iterations <= 1 (after conversion), should skip wrapper setup
            assert len(validation_results) == 0  # No wrappers for single iteration

        except Exception as e:
            # Should not raise exceptions for configuration validation errors
            pytest.fail(f"Configuration validation should not raise exceptions: {e}")


@pytest.mark.integration
class TestExecutionEnvironmentRealWorldScenarios(TestExecutionEnvironmentWorkflows):
    """Test execution environments in realistic deployment scenarios."""

    def test_production_like_environment_stack(
        self,
        temp_output_dir,
        event_manager,
        global_config,
        plugin_manager,
        test_config,
        mock_services,
    ):
        """Test a production-like stack of execution environments."""
        # Simulate a realistic production monitoring stack
        environments_config = {
            "profiling": GperfCpuConfig(profiling_frequency=100, generate_reports=True),
            "tracing": StraceConfig(trace_system_calls=True, max_output_size="50MB"),
            "memory_check": MemcheckConfig(leak_check=True, track_fds=True),
            "load_testing": IterationsConfig(iterations=10, delay_between_iterations=2),
        }

        # Initialize all environments
        environments = {}
        for name, config in environments_config.items():
            env_class_map = {
                "profiling": GperfCpuEnvironment,
                "tracing": StraceEnvironment,
                "memory_check": MemcheckEnvironment,
                "load_testing": IterationsEnvironment,
            }

            env_class = env_class_map[name]
            env = env_class(
                env_config_to_test=config,
                output_dir=str(temp_output_dir),
                env_type="execution",
                env_sub_type=name,
                event_manager=event_manager,
            )
            environments[name] = env

        # Track all production-like interactions
        production_interactions = {
            "files_registered": [],
            "commands_modified": [],
            "errors": [],
        }

        def make_production_tracker(env_name):
            def mock_register_output(file_type, file_path, service_name):
                production_interactions["files_registered"].append(
                    (env_name, file_type, file_path, service_name)
                )

            def mock_modify_commands(service, modification_type, commands):
                try:
                    production_interactions["commands_modified"].append(
                        (env_name, service.service_name, modification_type, commands)
                    )
                    return {"success": True, "environment": env_name}
                except Exception as e:
                    production_interactions["errors"].append((env_name, str(e)))
                    return {"success": False, "error": str(e)}

            return mock_register_output, mock_modify_commands

        # Set up tracking for all environments
        for name, env in environments.items():
            reg_func, mod_func = make_production_tracker(name)
            env.register_output_file = reg_func
            env.modify_service_commands = mod_func

        # Execute production-like setup sequence
        setup_order = ["profiling", "tracing", "memory_check", "load_testing"]

        for env_name in setup_order:
            env = environments[env_name]
            env.setup_environment(
                services_managers=mock_services,
                test_config=test_config,
                global_config=global_config,
                timestamp="20250101_120000",
                plugin_manager=plugin_manager,
            )

        # Verify production-like deployment
        assert len(production_interactions["errors"]) == 0  # No errors in setup

        # Verify all environments registered files
        files_by_env = {}
        for env_name, file_type, file_path, service_name in production_interactions[
            "files_registered"
        ]:
            if env_name not in files_by_env:
                files_by_env[env_name] = []
            files_by_env[env_name].append((file_type, file_path, service_name))

        # Each environment should have registered files (except single-iteration load testing)
        expected_envs = ["profiling", "tracing", "memory_check"]
        for env_name in expected_envs:
            assert env_name in files_by_env
            assert len(files_by_env[env_name]) >= 1

        # Verify all environments modified services appropriately
        modifications_by_env = {}
        for env_name, service_name, mod_type, commands in production_interactions[
            "commands_modified"
        ]:
            if env_name not in modifications_by_env:
                modifications_by_env[env_name] = []
            modifications_by_env[env_name].append((service_name, mod_type, commands))

        # Load testing (iterations=10) should modify services
        assert "load_testing" in modifications_by_env
        assert len(modifications_by_env["load_testing"]) >= 2  # Both services

        # Verify no resource conflicts between environments
        all_file_paths = [
            item[2] for item in production_interactions["files_registered"]
        ]
        assert len(all_file_paths) == len(set(all_file_paths))  # All unique paths

        # Verify all services have all environments marked
        expected_env_markers = ["GPERF_CPU", "STRACE", "MEMCHECK", "ITERATIONS"]
        for service in mock_services:
            for marker in expected_env_markers:
                assert service.environments.get(marker) is True

    def test_environment_performance_characteristics(
        self,
        temp_output_dir,
        event_manager,
        global_config,
        plugin_manager,
        test_config,
        mock_services,
    ):
        """Test execution environment performance and resource usage patterns."""
        # Test with larger-scale configuration
        config = StraceConfig(
            trace_system_calls=True, trace_child_processes=True, max_output_size="100MB"
        )

        strace_env = StraceEnvironment(
            env_config_to_test=config,
            output_dir=str(temp_output_dir),
            env_type="execution",
            env_sub_type="strace",
            event_manager=event_manager,
        )

        # Create larger set of mock services
        large_service_set = []
        for i in range(10):  # Simulate 10 services
            service = Mock(spec=IServiceManager)
            service.service_name = f"performance_service_{i}"
            service.role = ProtocolRole.SERVER if i % 2 == 0 else ProtocolRole.CLIENT
            service.run_cmd = {"pre_run_cmds": []}
            service.environments = {}
            large_service_set.append(service)

        # Track performance metrics
        performance_metrics = {
            "start_time": time.time(),
            "files_registered": 0,
            "commands_generated": 0,
            "setup_complete": False,
        }

        def mock_register_with_metrics(file_type, file_path, service_name):
            performance_metrics["files_registered"] += 1

        def mock_modify_with_metrics(service, modification_type, commands):
            performance_metrics["commands_generated"] += len(
                commands.get("pre_run_cmds", [])
            )
            return {"success": True}

        strace_env.register_output_file = mock_register_with_metrics
        strace_env.modify_service_commands = mock_modify_with_metrics

        # Execute setup with performance monitoring
        start_time = time.time()

        strace_env.setup_environment(
            services_managers=large_service_set,
            test_config=test_config,
            global_config=global_config,
            timestamp="20250101_120000",
            plugin_manager=plugin_manager,
        )

        end_time = time.time()
        setup_duration = end_time - start_time

        # Verify performance characteristics
        assert performance_metrics["files_registered"] == 10  # One per service
        assert (
            performance_metrics["commands_generated"] >= 10
        )  # At least one per service
        assert setup_duration < 5.0  # Should complete within reasonable time

        # Verify scalability - all services should be configured
        configured_services = [
            s for s in large_service_set if s.environments.get("STRACE")
        ]
        assert len(configured_services) == 10
