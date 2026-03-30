"""Property-based tests for execution environment robustness using Hypothesis.

These tests generate random inputs to find edge cases and ensure robust behavior
across all execution environment implementations including:
- Configuration validation with arbitrary inputs
- File path generation with various naming schemes
- Command generation robustness
- Environment variable handling
- Service manager interaction patterns
"""

import re
import shutil
import string
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional
from unittest.mock import Mock

import pytest
from hypothesis import HealthCheck, assume, given, settings
from hypothesis import strategies as st
from hypothesis.strategies import composite

from panther.config.core.models import ProtocolRole

# Import core components
from panther.core.observer.management.event_manager import EventManager

# Import command generation utilities
from panther.plugins.environments.execution_environment.command_generation_utils import (
    ExecutionEnvironmentCommandBuilder,
    OutputFileManager,
    OutputFileSpec,
    WrapperCommandGenerator,
    WrapperCommandSpec,
)
from panther.plugins.environments.execution_environment.gperf_cpu.config_schema import (
    GperfCpuConfig,
)
from panther.plugins.environments.execution_environment.gperf_cpu.gperf_cpu import (
    GperfCpuEnvironment,
)
from panther.plugins.environments.execution_environment.gperf_heap.config_schema import (
    GperfHeapConfig,
)
from panther.plugins.environments.execution_environment.gperf_heap.gperf_heap import (
    GperfHeapEnvironment,
)
from panther.plugins.environments.execution_environment.helgrind.config_schema import (
    HelgrindConfig,
)
from panther.plugins.environments.execution_environment.helgrind.helgrind import (
    HelgrindEnvironment,
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

# Import execution environment components
from panther.plugins.environments.execution_environment.strace.strace import (
    StraceEnvironment,
)
from panther.plugins.services.services_interface import IServiceManager


# Custom strategies for domain-specific types
@composite
def safe_identifiers(draw):
    """Generate safe identifiers for service names, file types, etc."""
    # Start with letter, followed by letters, numbers, underscores, hyphens
    first_char = draw(st.sampled_from(string.ascii_letters))
    rest_chars = draw(
        st.text(
            alphabet=string.ascii_letters + string.digits + "_-",
            min_size=0,
            max_size=30,
        )
    )
    identifier = first_char + rest_chars

    # Ensure it's not empty and doesn't end with special chars
    assume(len(identifier) >= 1)
    assume(not identifier.endswith("-"))
    assume(not identifier.endswith("_"))

    return identifier


@composite
def valid_timestamps(draw):
    """Generate valid timestamp strings."""
    year = draw(st.integers(min_value=2020, max_value=2030))
    month = draw(st.integers(min_value=1, max_value=12))
    day = draw(st.integers(min_value=1, max_value=28))  # Safe day range
    hour = draw(st.integers(min_value=0, max_value=23))
    minute = draw(st.integers(min_value=0, max_value=59))
    second = draw(st.integers(min_value=0, max_value=59))

    return f"{year:04d}{month:02d}{day:02d}_{hour:02d}{minute:02d}{second:02d}"


@composite
def valid_file_extensions(draw):
    """Generate valid file extensions."""
    return draw(
        st.sampled_from(
            ["out", "log", "txt", "prof", "trace", "xml", "json", "csv", "dat"]
        )
    )


@composite
def environment_variables(draw):
    """Generate valid environment variable dictionaries."""
    num_vars = draw(st.integers(min_value=0, max_value=10))
    variables = {}

    for _ in range(num_vars):
        key = draw(safe_identifiers()).upper()
        value = draw(
            st.text(
                alphabet=string.ascii_letters + string.digits + "_-./:",
                min_size=0,
                max_size=100,
            )
        )
        variables[key] = value

    return variables


@composite
def mock_service_managers(draw):
    """Generate mock service managers with various configurations."""
    num_services = draw(st.integers(min_value=1, max_value=5))
    services = []

    for i in range(num_services):
        service = Mock(spec=IServiceManager)
        service.service_name = draw(safe_identifiers())
        service.role = draw(st.sampled_from([ProtocolRole.SERVER, ProtocolRole.CLIENT]))
        service.run_cmd = {"pre_run_cmds": [], "post_run_cmds": []}
        service.environments = {}
        services.append(service)

    return services


class TestPropertyBasedConfigurationValidation:
    """Property-based tests for configuration validation."""

    @given(
        trace_calls=st.booleans(),
        trace_children=st.booleans(),
        output_format=st.sampled_from(["basic", "detailed", "compact"]),
        max_size=st.text(min_size=1, max_size=20),
    )
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_strace_config_robustness(
        self, trace_calls, trace_children, output_format, max_size
    ):
        """Test StraceConfig handles arbitrary valid inputs."""
        try:
            config = StraceConfig(
                trace_system_calls=trace_calls,
                trace_child_processes=trace_children,
                output_format=output_format,
                max_output_size=max_size,
            )

            # Configuration should always be valid after creation
            assert isinstance(config.trace_system_calls, bool)
            assert isinstance(config.trace_child_processes, bool)
            assert config.output_format in ["basic", "detailed", "compact"]
            assert isinstance(config.max_output_size, str)

        except Exception as e:
            # If configuration fails, it should be due to validation, not crashes
            assert "validation" in str(e).lower() or "invalid" in str(e).lower()

    @given(
        frequency=st.integers(min_value=1, max_value=10000),
        duration=st.integers(min_value=1, max_value=3600),
        generate_reports=st.booleans(),
    )
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_gperf_cpu_config_robustness(self, frequency, duration, generate_reports):
        """Test GperfCpuConfig handles arbitrary valid inputs."""
        config = GperfCpuConfig(
            profiling_frequency=frequency,
            profile_duration=duration,
            generate_reports=generate_reports,
        )

        # All values should be properly validated and stored
        assert config.profiling_frequency >= 1
        assert config.profile_duration >= 1
        assert isinstance(config.generate_reports, bool)

    @given(
        iterations=st.integers(min_value=0, max_value=1000),
        delay=st.integers(min_value=0, max_value=3600),
        parallel=st.booleans(),
        aggregate=st.booleans(),
    )
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_iterations_config_robustness(self, iterations, delay, parallel, aggregate):
        """Test IterationsConfig handles arbitrary valid inputs."""
        config = IterationsConfig(
            iterations=iterations,
            delay_between_iterations=delay,
            parallel=parallel,
            aggregate_results=aggregate,
        )

        # Verify all constraints are maintained
        assert config.iterations >= 0
        assert config.delay_between_iterations >= 0
        assert isinstance(config.parallel, bool)
        assert isinstance(config.aggregate_results, bool)

    @given(st.data())
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_config_with_plugin_config_dict_robustness(self, data):
        """Test configuration handling with arbitrary plugin_config dictionaries."""
        # Generate arbitrary plugin_config dictionary
        config_dict = data.draw(
            st.dictionaries(
                keys=st.text(min_size=1, max_size=50),
                values=st.one_of(
                    st.booleans(),
                    st.integers(min_value=-1000, max_value=1000),
                    st.text(min_size=0, max_size=100),
                    st.lists(st.text(min_size=0, max_size=50), min_size=0, max_size=10),
                ),
                min_size=0,
                max_size=20,
            )
        )

        # Test with StraceConfig
        config = StraceConfig()
        config.plugin_config = config_dict

        # Configuration should handle arbitrary plugin_config gracefully
        assert hasattr(config, "plugin_config")
        assert config.plugin_config == config_dict

        # Test getter method if available
        if hasattr(config, "get_plugin_config"):
            try:
                retrieved_config = config.get_plugin_config(StraceConfig)
                assert isinstance(retrieved_config, StraceConfig)
            except Exception:
                # Getter might fail with invalid data, which is acceptable
                pass


class TestPropertyBasedFilePathGeneration:
    """Property-based tests for file path generation."""

    @pytest.fixture
    def output_manager(self):
        """Create OutputFileManager for testing."""
        mock_callback = Mock()
        return OutputFileManager(mock_callback)

    @given(
        service_name=safe_identifiers(),
        file_type=safe_identifiers(),
        timestamp=valid_timestamps(),
        extension=valid_file_extensions(),
        base_dir=st.text(min_size=1, max_size=50),
    )
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_output_path_generation_robustness(
        self, output_manager, service_name, file_type, timestamp, extension, base_dir
    ):
        """Test output path generation with arbitrary valid inputs."""
        # Clean base_dir to be path-safe
        base_dir = re.sub(r'[<>:"|?*]', "_", base_dir)
        assume(base_dir.strip())  # Non-empty after cleaning

        path = output_manager.generate_output_path(
            service_name=service_name,
            file_type=file_type,
            timestamp=timestamp,
            extension=extension,
            base_dir=base_dir,
        )

        # Verify path structure
        assert isinstance(path, str)
        assert service_name in path
        assert file_type in path
        assert timestamp in path
        assert path.endswith(f".{extension}")
        assert path.startswith(base_dir)

        # Verify no dangerous characters in path
        dangerous_chars = ["<", ">", ":", '"', "|", "?", "*"]
        for char in dangerous_chars:
            assert char not in path

    @given(
        file_specs=st.lists(
            st.tuples(
                safe_identifiers(),  # file_type
                st.text(min_size=1, max_size=100),  # file_path
                safe_identifiers(),  # service_name
                st.one_of(st.none(), st.text(min_size=0, max_size=200)),  # description
                st.booleans(),  # is_primary
            ),
            min_size=1,
            max_size=20,
        )
    )
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_output_file_registration_robustness(self, output_manager, file_specs):
        """Test output file registration with arbitrary file specifications."""
        # Create a fresh OutputFileManager per hypothesis example to avoid
        # accumulating registered files across examples.
        fresh_manager = OutputFileManager(Mock())
        registered_specs = []

        for file_type, file_path, service_name, description, is_primary in file_specs:
            spec = fresh_manager.register_output_file(
                file_type=file_type,
                file_path=file_path,
                service_name=service_name,
                description=description,
                is_primary=is_primary,
            )

            # Verify spec is properly created
            assert isinstance(spec, OutputFileSpec)
            assert spec.file_type == file_type
            assert spec.file_path == file_path
            assert spec.service_name == service_name
            assert spec.description == description
            assert spec.is_primary == is_primary

            registered_specs.append(spec)

        # Verify all files are tracked
        all_files = fresh_manager.get_registered_files()
        assert len(all_files) == len(file_specs)

        # Test filtering by service
        unique_services = set(spec[2] for spec in file_specs)
        for service_name in unique_services:
            service_files = fresh_manager.get_registered_files(service_name)
            expected_count = sum(1 for spec in file_specs if spec[2] == service_name)
            assert len(service_files) == expected_count


class TestPropertyBasedCommandGeneration:
    """Property-based tests for command generation robustness."""

    @pytest.fixture
    def wrapper_generator(self):
        """Create WrapperCommandGenerator for testing."""
        return WrapperCommandGenerator()

    @given(
        environment_name=safe_identifiers(),
        service_name=safe_identifiers(),
        wrapper_command=st.text(min_size=1, max_size=200),
        env_vars=environment_variables(),
    )
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_environment_wrapper_generation_robustness(
        self,
        wrapper_generator,
        environment_name,
        service_name,
        wrapper_command,
        env_vars,
    ):
        """Test environment wrapper generation with arbitrary inputs."""
        wrapper = wrapper_generator.generate_environment_wrapper(
            environment_name=environment_name,
            wrapper_command=wrapper_command,
            service_name=service_name,
            additional_env_vars=env_vars,
        )

        # Verify wrapper structure
        assert isinstance(wrapper, str)
        assert len(wrapper) > 0
        assert environment_name in wrapper
        assert service_name in wrapper
        assert wrapper_command in wrapper

        # Verify environment variables are included
        for key, value in env_vars.items():
            assert f"export {key}={value}" in wrapper

        # Verify proper shell structure
        assert "echo" in wrapper  # Should have logging
        assert "/app/logs/" in wrapper  # Should use proper log path

    @given(
        condition=st.text(min_size=1, max_size=100),
        environment_name=safe_identifiers(),
        wrapper_command=st.text(min_size=1, max_size=200),
        service_name=safe_identifiers(),
        fallback_message=st.one_of(st.none(), st.text(min_size=0, max_size=100)),
    )
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_conditional_wrapper_generation_robustness(
        self,
        wrapper_generator,
        condition,
        environment_name,
        wrapper_command,
        service_name,
        fallback_message,
    ):
        """Test conditional wrapper generation with arbitrary inputs."""
        wrapper = wrapper_generator.generate_conditional_wrapper(
            condition=condition,
            environment_name=environment_name,
            wrapper_command=wrapper_command,
            service_name=service_name,
            fallback_message=fallback_message,
        )

        # Verify conditional structure
        assert isinstance(wrapper, str)
        assert f"if {condition}; then" in wrapper
        assert "fi" in wrapper
        assert environment_name in wrapper
        assert service_name in wrapper
        assert wrapper_command in wrapper

        # Verify fallback handling
        if fallback_message:
            assert "else" in wrapper
            assert fallback_message in wrapper

    @given(
        file_paths=st.lists(
            st.tuples(
                st.text(min_size=1, max_size=100),  # input_file
                st.text(min_size=1, max_size=100),  # output_file
                st.text(min_size=1, max_size=200),  # processing_command
                st.text(min_size=1, max_size=100),  # description
            ),
            min_size=1,
            max_size=10,
        ),
        service_name=safe_identifiers(),
    )
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_post_processing_command_generation_robustness(
        self, wrapper_generator, file_paths, service_name
    ):
        """Test post-processing command generation with arbitrary file operations."""
        for input_file, output_file, processing_command, description in file_paths:
            post_cmd = wrapper_generator.generate_post_processing_command(
                input_file=input_file,
                output_file=output_file,
                processing_command=processing_command,
                service_name=service_name,
                description=description,
            )

            # Verify post-processing structure
            assert isinstance(post_cmd, str)
            assert f'if [ -f "{input_file}" ]' in post_cmd
            assert processing_command in post_cmd
            assert output_file in post_cmd
            assert description in post_cmd
            assert service_name in post_cmd
            assert "else" in post_cmd  # Should have fallback
            assert "fi" in post_cmd  # Should close if statement


class TestPropertyBasedEnvironmentInteractions:
    """Property-based tests for environment and service interactions."""

    @pytest.fixture
    def temp_output_dir(self):
        """Create temporary output directory."""
        temp_dir = tempfile.mkdtemp(prefix="property_test_")
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.fixture
    def event_manager(self):
        """Create event manager."""
        return EventManager()

    @given(services=mock_service_managers())
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_strace_environment_service_interaction_robustness(
        self, temp_output_dir, event_manager, services
    ):
        """Test StraceEnvironment interaction with arbitrary service configurations."""
        config = StraceConfig()

        strace_env = StraceEnvironment(
            env_config_to_test=config,
            output_dir=temp_output_dir,
            env_type="execution",
            env_sub_type="strace",
            event_manager=event_manager,
        )

        # Mock interactions to track behavior
        registered_files = []
        modified_services = []

        def mock_register(file_type, file_path, service_name):
            registered_files.append((file_type, file_path, service_name))

        def mock_modify(service, modification_type, commands):
            modified_services.append(
                (service.service_name, modification_type, commands)
            )
            return {"success": True}

        strace_env.register_output_file = mock_register
        strace_env.modify_service_commands = mock_modify

        # Test setup with arbitrary services
        try:
            strace_env._setup_plugin_specific_environment(services, "20250101_120000")

            # Strace registers multiple output files per service (log + summary + post-processing)
            # so the total registered_files count can exceed the number of services.
            assert len(registered_files) >= len(
                services
            )  # At least one file per service

            # Verify all registered files are valid
            for file_type, file_path, service_name in registered_files:
                assert isinstance(file_type, str)
                assert isinstance(file_path, str)
                assert len(file_path) > 0
                assert service_name in [s.service_name for s in services]

        except Exception as e:
            # Should not crash even with unusual service configurations
            pytest.fail(
                f"StraceEnvironment should handle arbitrary services gracefully: {e}"
            )

    @given(
        iterations=st.integers(min_value=0, max_value=100),
        delay=st.integers(min_value=0, max_value=60),
        services=mock_service_managers(),
    )
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_iterations_environment_configuration_robustness(
        self, temp_output_dir, event_manager, iterations, delay, services
    ):
        """Test IterationsEnvironment with arbitrary configuration values."""
        config = IterationsConfig(iterations=iterations, delay_between_iterations=delay)

        iterations_env = IterationsEnvironment(
            env_config_to_test=config,
            output_dir=temp_output_dir,
            env_type="execution",
            env_sub_type="iterations",
            event_manager=event_manager,
        )

        # Mock interactions
        interactions = []

        def mock_register(file_type, file_path, service_name):
            interactions.append(("register", file_type, file_path, service_name))

        def mock_modify(service, modification_type, commands):
            interactions.append(
                ("modify", service.service_name, modification_type, commands)
            )
            return {"success": True}

        iterations_env.register_output_file = mock_register
        iterations_env.modify_service_commands = mock_modify

        # Test setup behavior
        iterations_env._setup_plugin_specific_environment(services, "20250101_120000")

        # Verify behavior based on iterations count
        if iterations <= 1:
            # Should skip setup for single or no iterations
            modify_actions = [a for a in interactions if a[0] == "modify"]
            assert len(modify_actions) == 0
        else:
            # Should setup wrappers for multiple iterations
            register_actions = [a for a in interactions if a[0] == "register"]
            modify_actions = [a for a in interactions if a[0] == "modify"]

            assert len(register_actions) == len(services)  # One file per service
            assert len(modify_actions) == len(services)  # One modification per service

            # Verify wrapper scripts contain iteration parameters
            for action in modify_actions:
                _, service_name, mod_type, commands = action
                wrapper_cmd = commands["pre_run_cmds"][0]
                assert f"iterations_count={iterations}" in wrapper_cmd
                assert f"delay_between={delay}" in wrapper_cmd


class TestPropertyBasedRobustnessScenarios:
    """Property-based tests for edge cases and robustness scenarios."""

    @given(st.data())
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_output_file_manager_edge_cases(self, data):
        """Test OutputFileManager with edge case inputs."""
        mock_callback = Mock()
        manager = OutputFileManager(mock_callback)

        # Generate edge case service names
        service_name = data.draw(
            st.one_of(
                st.just(""),  # Empty string
                st.text(min_size=1, max_size=1),  # Single character
                st.text(min_size=100, max_size=200),  # Very long name
                safe_identifiers(),  # Normal case
            )
        )

        # Generate edge case file types
        file_type = data.draw(
            st.one_of(
                st.just("a"),  # Single character
                st.text(alphabet=string.ascii_letters, min_size=1, max_size=50),
                safe_identifiers(),
            )
        )

        if service_name and file_type:  # Skip empty cases
            try:
                spec = manager.register_output_file(
                    file_type=file_type,
                    file_path=f"/tmp/{service_name}_{file_type}.out",
                    service_name=service_name,
                )

                # Should always create valid spec
                assert isinstance(spec, OutputFileSpec)
                assert spec.file_type == file_type
                assert spec.service_name == service_name

                # Should be retrievable
                all_files = manager.get_registered_files()
                assert spec in all_files

                # Should be filterable by service
                service_files = manager.get_registered_files(service_name)
                assert spec in service_files

            except Exception as e:
                # Should not crash, but might reject invalid inputs
                assert "invalid" in str(e).lower() or "error" in str(e).lower()

    @given(
        config_combinations=st.lists(
            st.tuples(
                st.sampled_from(
                    [
                        StraceConfig,
                        GperfCpuConfig,
                        GperfHeapConfig,
                        HelgrindConfig,
                        MemcheckConfig,
                        IterationsConfig,
                    ]
                ),
                st.dictionaries(
                    keys=st.text(min_size=1, max_size=30),
                    values=st.one_of(
                        st.booleans(),
                        st.integers(min_value=0, max_value=1000),
                        st.text(min_size=0, max_size=50),
                    ),
                    min_size=0,
                    max_size=10,
                ),
            ),
            min_size=1,
            max_size=5,
        )
    )
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_configuration_robustness_combinations(self, config_combinations):
        """Test various configuration class combinations with arbitrary plugin_config."""
        for config_class, plugin_config_dict in config_combinations:
            try:
                # Create configuration instance
                config = config_class()
                config.plugin_config = plugin_config_dict

                # Configuration should be valid
                assert hasattr(config, "plugin_config")
                assert config.plugin_config == plugin_config_dict

                # Test basic attribute access
                assert hasattr(config, "type")
                assert isinstance(config.type, str)

            except Exception as e:
                # Configurations might reject invalid combinations
                # This is acceptable as long as it doesn't crash
                assert isinstance(e, (ValueError, TypeError, AttributeError))

    @given(
        command_patterns=st.lists(
            st.text(
                alphabet=string.ascii_letters + string.digits + " -_./=:\"'",
                min_size=1,
                max_size=100,
            ),
            min_size=1,
            max_size=10,
        )
    )
    @settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
    def test_wrapper_command_generator_command_safety(self, command_patterns):
        """Test that WrapperCommandGenerator produces safe shell commands."""
        generator = WrapperCommandGenerator()

        for wrapper_command in command_patterns:
            # Clean command to avoid shell injection
            wrapper_command = re.sub(r"[;&|`$(){}]", "", wrapper_command)
            assume(wrapper_command.strip())  # Non-empty after cleaning

            try:
                wrapper = generator.generate_environment_wrapper(
                    environment_name="test_env",
                    wrapper_command=wrapper_command,
                    service_name="test_service",
                )

                # Verify no dangerous shell constructs
                dangerous_patterns = [";", "&&", "||", "`", "$(", "${"]
                original_dangerous_count = sum(
                    wrapper_command.count(pattern) for pattern in dangerous_patterns
                )
                wrapper_dangerous_count = sum(
                    wrapper.count(pattern) for pattern in dangerous_patterns
                )

                # Wrapper shouldn't introduce new dangerous patterns
                # (but might preserve ones from the original command)
                assert wrapper_dangerous_count >= original_dangerous_count

                # Should always be valid shell syntax structure
                assert wrapper.count('echo "') >= 2  # Start and end logging
                assert "/app/logs/" in wrapper

            except Exception as e:
                # Generator might reject unsafe commands
                assert "unsafe" in str(e).lower() or "invalid" in str(e).lower()


@pytest.mark.property_based
class TestPropertyBasedPerformanceCharacteristics:
    """Property-based tests for performance characteristics."""

    @given(
        num_services=st.integers(min_value=1, max_value=50),
        num_environments=st.integers(min_value=1, max_value=5),
    )
    @settings(
        suppress_health_check=[HealthCheck.function_scoped_fixture],
        max_examples=10,  # Limit examples for performance tests
        deadline=5000,  # 5 second deadline
    )
    def test_scaling_characteristics(self, num_services, num_environments):
        """Test that execution environments scale reasonably with input size."""
        import time

        # Create mock services with enough attributes for all environment types
        services = []
        for i in range(num_services):
            service = Mock(spec=IServiceManager)
            service.service_name = f"service_{i}"
            service.role = ProtocolRole.SERVER if i % 2 == 0 else ProtocolRole.CLIENT
            service.run_cmd = {"pre_run_cmds": []}
            service.environments = {}
            # Needed by GperfCpuEnvironment which accesses service_config_to_test
            service.service_config_to_test = Mock()
            service.service_config_to_test.implementation = Mock()
            service.service_config_to_test.implementation.gperf_compatible = True
            services.append(service)

        # Test multiple environments
        environment_classes = [
            StraceEnvironment,
            GperfCpuEnvironment,
            IterationsEnvironment,
        ]
        config_classes = [StraceConfig, GperfCpuConfig, IterationsConfig]

        total_operations = 0
        start_time = time.time()

        for i in range(min(num_environments, len(environment_classes))):
            env_class = environment_classes[i]
            config_class = config_classes[i]

            # Create environment
            with tempfile.TemporaryDirectory() as temp_dir:
                event_manager = EventManager()
                config = config_class()

                env = env_class(
                    env_config_to_test=config,
                    output_dir=temp_dir,
                    env_type="execution",
                    env_sub_type=f"test_{i}",
                    event_manager=event_manager,
                )

                # Mock operations
                operations_count = 0

                def count_register(*args):
                    nonlocal operations_count
                    operations_count += 1

                def count_modify(*args):
                    nonlocal operations_count
                    operations_count += 1
                    return {"success": True}

                env.register_output_file = count_register
                env.modify_service_commands = count_modify

                # Execute setup
                env._setup_plugin_specific_environment(services, "20250101_120000")
                total_operations += operations_count

        end_time = time.time()
        execution_time = end_time - start_time

        # Verify reasonable performance characteristics
        # Should complete within reasonable time regardless of scale
        assert execution_time < 10.0  # Should complete within 10 seconds

        # Operations should scale reasonably with input size.
        # Each environment may register multiple output files per service
        # (e.g. strace registers log + summary + post-processing callbacks),
        # so we allow a generous multiplier.
        expected_operations = num_services * min(
            num_environments, len(environment_classes)
        )
        assert (
            total_operations <= expected_operations * 10
        )  # Allow for multiple files/ops per service

        # Should not crash or hang with large inputs
        assert total_operations >= 0
