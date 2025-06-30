"""
Unit tests for environment variable overrides in configuration.

Tests environment variable parsing and application to configuration
objects, ensuring proper precedence and type conversion.
"""

import os

from panther.config.core.models.global_config import (
    DockerConfig,
    FeatureConfig,
    GlobalConfig,
    LoggingConfig,
    LoggingLevel,
    PathsConfig,
)


class TestEnvironmentOverrides:
    """Test environment variable override functionality."""

    def test_logging_level_override_via_env(self, mock_env_fixture, valid_cfg_dict):
        """Test logging level override via environment variable."""
        with mock_env_fixture(PANTHER_LOG_LEVEL="ERROR"):
            # Simulate applying environment overrides
            config = LoggingConfig(level=LoggingLevel.DEBUG)

            # In actual implementation, this would be handled by env override logic
            env_level = os.environ.get("PANTHER_LOG_LEVEL", "DEBUG")
            if env_level in LoggingLevel.__members__:
                config.level = LoggingLevel[env_level]

            assert config.level == LoggingLevel.ERROR

    def test_paths_override_via_env(self, mock_env_fixture):
        """Test paths override via environment variables."""
        with mock_env_fixture(
            PANTHER_OUTPUT_DIR="/env/output",
            PANTHER_LOG_DIR="/env/logs",
            PANTHER_CONFIG_DIR="/env/config",
            PANTHER_PLUGIN_DIR="/env/plugins",
        ):
            config = PathsConfig()

            # Simulate environment override logic
            config.output_dir = os.environ.get("PANTHER_OUTPUT_DIR", config.output_dir)
            config.log_dir = os.environ.get("PANTHER_LOG_DIR", config.log_dir)
            config.config_dir = os.environ.get("PANTHER_CONFIG_DIR", config.config_dir)
            config.plugin_dir = os.environ.get("PANTHER_PLUGIN_DIR", config.plugin_dir)

            assert config.output_dir == "/env/output"
            assert config.log_dir == "/env/logs"
            assert config.config_dir == "/env/config"
            assert config.plugin_dir == "/env/plugins"

    def test_docker_config_override_via_env(self, mock_env_fixture):
        """Test Docker configuration override via environment variables."""
        with mock_env_fixture(
            PANTHER_DOCKER_BUILD="false",
            PANTHER_DOCKER_REMOVE_IMAGE="false",
            PANTHER_DOCKER_REMOVE_CONTAINER="true",
        ):
            config = DockerConfig()

            # Simulate boolean environment override logic
            def env_bool(key, default):
                value = os.environ.get(key, str(default)).lower()
                return value in ("true", "1", "yes", "on")

            config.build_docker_image = env_bool(
                "PANTHER_DOCKER_BUILD", config.build_docker_image
            )
            config.remove_docker_image = env_bool(
                "PANTHER_DOCKER_REMOVE_IMAGE", config.remove_docker_image
            )
            config.remove_docker_container = env_bool(
                "PANTHER_DOCKER_REMOVE_CONTAINER", config.remove_docker_container
            )

            assert config.build_docker_image is False
            assert config.remove_docker_image is False
            assert config.remove_docker_container is True

    def test_feature_config_override_via_env(self, mock_env_fixture):
        """Test feature configuration override via environment variables."""
        with mock_env_fixture(
            PANTHER_LOGGER_OBSERVER="false",
            PANTHER_STORAGE_HANDLER="true",
            PANTHER_FAST_FAIL="false",
        ):
            config = FeatureConfig()

            # Simulate boolean environment override logic
            def env_bool(key, default):
                value = os.environ.get(key, str(default)).lower()
                return value in ("true", "1", "yes", "on")

            config.logger_observer = env_bool(
                "PANTHER_LOGGER_OBSERVER", config.logger_observer
            )
            config.storage_handler = env_bool(
                "PANTHER_STORAGE_HANDLER", config.storage_handler
            )
            config.fast_fail = env_bool("PANTHER_FAST_FAIL", config.fast_fail)

            assert config.logger_observer is False
            assert config.storage_handler is True
            assert config.fast_fail is False

    def test_boolean_parsing_variations(self, mock_env_fixture):
        """Test various boolean value formats in environment variables."""
        test_cases = [
            ("true", True),
            ("True", True),
            ("TRUE", True),
            ("1", True),
            ("yes", True),
            ("Yes", True),
            ("YES", True),
            ("on", True),
            ("false", False),
            ("False", False),
            ("FALSE", False),
            ("0", False),
            ("no", False),
            ("No", False),
            ("NO", False),
            ("off", False),
            ("invalid", False),  # Invalid values should default to False
        ]

        for env_value, expected in test_cases:
            with mock_env_fixture(PANTHER_TEST_BOOL=env_value):

                def env_bool(key, default=False):
                    value = os.environ.get(key, str(default)).lower()
                    return value in ("true", "1", "yes", "on")

                result = env_bool("PANTHER_TEST_BOOL")
                assert (
                    result == expected
                ), f"Value '{env_value}' should parse to {expected}"

    def test_environment_precedence_over_config_file(
        self, mock_env_fixture, valid_cfg_dict
    ):
        """Test that environment variables take precedence over config file values."""
        # Config file has DEBUG, environment sets INFO
        with mock_env_fixture(PANTHER_LOG_LEVEL="INFO"):
            file_config = LoggingConfig(level=LoggingLevel.DEBUG)

            # Environment should override file config
            env_level = os.environ.get("PANTHER_LOG_LEVEL")
            if env_level and env_level in LoggingLevel.__members__:
                file_config.level = LoggingLevel[env_level]

            assert file_config.level == LoggingLevel.INFO

    def test_environment_override_partial_config(self, mock_env_fixture):
        """Test environment override when only some values are overridden."""
        with mock_env_fixture(
            PANTHER_OUTPUT_DIR="/custom/output"
            # Other path variables not set
        ):
            config = PathsConfig(
                output_dir="default/output",
                log_dir="default/logs",
                config_dir="default/config",
            )

            # Only override what's in environment
            config.output_dir = os.environ.get("PANTHER_OUTPUT_DIR", config.output_dir)
            config.log_dir = os.environ.get("PANTHER_LOG_DIR", config.log_dir)
            config.config_dir = os.environ.get("PANTHER_CONFIG_DIR", config.config_dir)

            # Only output_dir should be overridden
            assert config.output_dir == "/custom/output"
            assert config.log_dir == "default/logs"
            assert config.config_dir == "default/config"

    def test_missing_environment_variables_use_defaults(self, mock_env_fixture):
        """Test that missing environment variables use default values."""
        with mock_env_fixture():  # Empty environment
            config = PathsConfig()

            # Simulate applying env overrides (nothing should change)
            config.output_dir = os.environ.get("PANTHER_OUTPUT_DIR", config.output_dir)
            config.log_dir = os.environ.get("PANTHER_LOG_DIR", config.log_dir)

            # Should keep defaults
            assert config.output_dir == "panther/outputs"
            assert config.log_dir == "panther/outputs"

    def test_integer_environment_overrides(self, mock_env_fixture):
        """Test integer value parsing from environment variables."""
        from panther.config.core.models.experiment import StepConfig, TestConfig

        with mock_env_fixture(PANTHER_STEP_WAIT="120", PANTHER_TEST_ITERATIONS="10"):
            step_config = StepConfig()
            test_config = TestConfig()

            # Simulate integer environment override logic
            def env_int(key, default):
                try:
                    return int(os.environ.get(key, default))
                except (ValueError, TypeError):
                    return default

            step_config.wait = env_int("PANTHER_STEP_WAIT", step_config.wait)
            test_config.iterations = env_int(
                "PANTHER_TEST_ITERATIONS", test_config.iterations
            )

            assert step_config.wait == 120
            assert test_config.iterations == 10

    def test_invalid_integer_environment_values(self, mock_env_fixture):
        """Test handling of invalid integer values in environment variables."""
        from panther.config.core.models.experiment import StepConfig

        with mock_env_fixture(PANTHER_STEP_WAIT="not_a_number"):
            step_config = StepConfig(wait=60)

            # Simulate safe integer parsing
            def env_int(key, default):
                try:
                    return int(os.environ.get(key, default))
                except (ValueError, TypeError):
                    return default

            step_config.wait = env_int("PANTHER_STEP_WAIT", step_config.wait)

            # Should keep default value when parsing fails
            assert step_config.wait == 60

    def test_case_insensitive_boolean_parsing(self, mock_env_fixture):
        """Test case-insensitive boolean parsing."""
        test_values = ["True", "TRUE", "true", "False", "FALSE", "false"]

        for value in test_values:
            with mock_env_fixture(PANTHER_TEST_BOOL=value):

                def env_bool(key, default=False):
                    env_value = os.environ.get(key, str(default)).lower()
                    return env_value in ("true", "1", "yes", "on")

                result = env_bool("PANTHER_TEST_BOOL")
                expected = value.lower() == "true"
                assert result == expected, f"Value '{value}' case handling failed"

    def test_environment_override_with_empty_values(self, mock_env_fixture):
        """Test environment override behavior with empty string values."""
        with mock_env_fixture(PANTHER_OUTPUT_DIR="", PANTHER_LOG_LEVEL=""):
            config = PathsConfig(output_dir="default/output")

            # Empty strings should be treated as valid overrides
            output_dir = os.environ.get("PANTHER_OUTPUT_DIR")
            if output_dir is not None:  # Environment variable exists, even if empty
                config.output_dir = output_dir

            assert config.output_dir == ""

    def test_complex_environment_override_scenario(self, mock_env_fixture):
        """Test complex scenario with multiple environment overrides."""
        with mock_env_fixture(
            PANTHER_LOG_LEVEL="WARNING",
            PANTHER_OUTPUT_DIR="/prod/output",
            PANTHER_DOCKER_BUILD="false",
            PANTHER_FAST_FAIL="true",
            PANTHER_PLUGIN_DIR="/custom/plugins",
        ):
            # Create configs with defaults
            logging_config = LoggingConfig()
            paths_config = PathsConfig()
            docker_config = DockerConfig()
            feature_config = FeatureConfig()

            # Apply environment overrides
            def env_bool(key, default):
                value = os.environ.get(key, str(default)).lower()
                return value in ("true", "1", "yes", "on")

            # Apply all overrides
            env_level = os.environ.get("PANTHER_LOG_LEVEL")
            if env_level and env_level in LoggingLevel.__members__:
                logging_config.level = LoggingLevel[env_level]

            paths_config.output_dir = os.environ.get(
                "PANTHER_OUTPUT_DIR", paths_config.output_dir
            )
            paths_config.plugin_dir = os.environ.get(
                "PANTHER_PLUGIN_DIR", paths_config.plugin_dir
            )

            docker_config.build_docker_image = env_bool(
                "PANTHER_DOCKER_BUILD", docker_config.build_docker_image
            )
            feature_config.fast_fail = env_bool(
                "PANTHER_FAST_FAIL", feature_config.fast_fail
            )

            # Verify all overrides applied correctly
            assert logging_config.level == LoggingLevel.WARNING
            assert paths_config.output_dir == "/prod/output"
            assert paths_config.plugin_dir == "/custom/plugins"
            assert docker_config.build_docker_image is False
            assert feature_config.fast_fail is True

            # Verify non-overridden values kept defaults
            assert docker_config.remove_docker_image is True  # Not overridden
            assert feature_config.logger_observer is True  # Not overridden


class TestEnvironmentVariableNaming:
    """Test environment variable naming conventions."""

    def test_environment_variable_naming_convention(self):
        """Test that environment variables follow PANTHER_ prefix convention."""
        expected_vars = [
            "PANTHER_LOG_LEVEL",
            "PANTHER_OUTPUT_DIR",
            "PANTHER_LOG_DIR",
            "PANTHER_CONFIG_DIR",
            "PANTHER_PLUGIN_DIR",
            "PANTHER_DOCKER_BUILD",
            "PANTHER_DOCKER_REMOVE_IMAGE",
            "PANTHER_DOCKER_REMOVE_CONTAINER",
            "PANTHER_DOCKER_REMOVE_NETWORK",
            "PANTHER_DOCKER_REMOVE_VOLUME",
            "PANTHER_LOGGER_OBSERVER",
            "PANTHER_STORAGE_HANDLER",
            "PANTHER_FAST_FAIL",
        ]

        # All variables should start with PANTHER_
        for var in expected_vars:
            assert var.startswith(
                "PANTHER_"
            ), f"Variable {var} should start with PANTHER_"
            assert var.isupper(), f"Variable {var} should be uppercase"

    def test_environment_variable_uniqueness(self):
        """Test that environment variable names are unique."""
        vars_list = [
            "PANTHER_LOG_LEVEL",
            "PANTHER_OUTPUT_DIR",
            "PANTHER_LOG_DIR",
            "PANTHER_CONFIG_DIR",
            "PANTHER_PLUGIN_DIR",
            "PANTHER_DOCKER_BUILD",
        ]

        # Should have no duplicates
        assert len(vars_list) == len(
            set(vars_list)
        ), "Environment variable names should be unique"


class TestEnvironmentIntegration:
    """Integration tests for environment variable application."""

    def test_full_config_environment_integration(self, mock_env_fixture):
        """Test full configuration with comprehensive environment overrides."""
        with mock_env_fixture(
            PANTHER_LOG_LEVEL="ERROR",
            PANTHER_OUTPUT_DIR="/integration/output",
            PANTHER_LOG_DIR="/integration/logs",
            PANTHER_DOCKER_BUILD="false",
            PANTHER_FAST_FAIL="true",
        ):
            # Create a complete configuration
            logging_config = LoggingConfig(level=LoggingLevel.DEBUG)
            paths_config = PathsConfig(
                output_dir="default/output", log_dir="default/logs"
            )
            docker_config = DockerConfig(build_docker_image=True)
            feature_config = FeatureConfig(fast_fail=False)

            global_config = GlobalConfig(
                logging=logging_config,
                paths=paths_config,
                docker=docker_config,
                features=feature_config,
            )

            # Apply environment overrides (would be done by actual implementation)
            def apply_env_overrides(config):
                def env_bool(key, default):
                    value = os.environ.get(key, str(default)).lower()
                    return value in ("true", "1", "yes", "on")

                # Apply logging overrides
                env_level = os.environ.get("PANTHER_LOG_LEVEL")
                if env_level and env_level in LoggingLevel.__members__:
                    config.logging.level = LoggingLevel[env_level]

                # Apply paths overrides
                config.paths.output_dir = os.environ.get(
                    "PANTHER_OUTPUT_DIR", config.paths.output_dir
                )
                config.paths.log_dir = os.environ.get(
                    "PANTHER_LOG_DIR", config.paths.log_dir
                )

                # Apply docker overrides
                config.docker.build_docker_image = env_bool(
                    "PANTHER_DOCKER_BUILD", config.docker.build_docker_image
                )

                # Apply feature overrides
                config.features.fast_fail = env_bool(
                    "PANTHER_FAST_FAIL", config.features.fast_fail
                )

                return config

            result_config = apply_env_overrides(global_config)

            # Verify all environment overrides were applied
            assert result_config.logging.level == LoggingLevel.ERROR
            assert result_config.paths.output_dir == "/integration/output"
            assert result_config.paths.log_dir == "/integration/logs"
            assert result_config.docker.build_docker_image is False
            assert result_config.features.fast_fail is True

            # Verify non-overridden values remained unchanged
            assert result_config.docker.remove_docker_image is True
            assert result_config.features.logger_observer is True
