from pathlib import Path
from typing import Any, Dict

from panther.core.utils.logging_mixin import LoggerMixin
from panther.plugins.environments.environment_utils import EnvironmentUtilities


class EnvironmentPluginMixin(LoggerMixin):
    """
    Base mixin for environment plugins providing common functionality.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._environment_initialized = False
        self._output_directories = {}
        self._environment_state = "uninitialized"

    def standardized_environment_initialization(
        self,
        env_config_to_test: Any,
        output_dir: str,
        env_type: str,
        env_sub_type: str,
        event_manager=None,
    ) -> None:
        """
        Perform standardized environment plugin initialization.

        Args:
            env_config_to_test: Environment configuration
            output_dir: Output directory
            env_type: Environment type
            env_sub_type: Environment sub-type
            event_manager: Event manager instance
        """
        # Store basic attributes
        self.env_config_to_test = env_config_to_test
        # Ensure output_dir is always an absolute path
        self.output_dir = str(Path(output_dir).resolve())
        self.env_type = env_type
        self.env_sub_type = env_sub_type
        self.event_manager = event_manager

        # Set up output directories
        self._output_directories = EnvironmentUtilities.setup_output_directories(
            output_dir, env_sub_type
        )

        # Standard logging
        EnvironmentUtilities.standardize_environment_initialization(
            self.logger, env_type, env_sub_type
        )

        self._environment_initialized = True
        self._environment_state = "initialized"

    @property
    def environment_state(self) -> str:
        """Get the current environment state."""
        return self._environment_state

    @property
    def output_directories(self) -> Dict[str, Path]:
        """Get the output directories."""
        return self._output_directories

    def get_logs_directory(self) -> Path:
        """Get the logs directory path."""
        return self._output_directories.get("logs", Path(self.output_dir) / "logs")

    def get_results_directory(self) -> Path:
        """Get the results directory path."""
        return self._output_directories.get(
            "results", Path(self.output_dir) / "results"
        )

    def get_artifacts_directory(self) -> Path:
        """Get the artifacts directory path."""
        return self._output_directories.get(
            "artifacts", Path(self.output_dir) / "artifacts"
        )

    def update_environment_state(self, new_state: str) -> None:
        """
        Update the environment state.

        Args:
            new_state: New state value
        """
        old_state = self._environment_state
        self._environment_state = new_state
        self.logger.debug(f"Environment state changed: {old_state} -> {new_state}")
