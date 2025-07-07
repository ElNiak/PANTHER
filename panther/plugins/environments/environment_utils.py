"""
Environment Plugin Utilities

This module provides common utilities and mixins for environment plugins.
"""

import logging
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class EnvironmentUtilities:
    """Common utility methods for environment plugins."""

    @staticmethod
    def standardize_environment_initialization(
        logger: logging.Logger, env_type: str, env_sub_type: str
    ) -> None:
        """
        Standardize initialization logging for environment plugins.

        Args:
            logger: Logger instance
            env_type: Type of environment (execution, network)
            env_sub_type: Sub-type of environment (docker_compose, strace, etc.)
        """
        logger.debug("Initializing %s environment plugin: %s", env_type, env_sub_type)

    @staticmethod
    def setup_output_directories(
        output_dir: str, env_sub_type: str, test_name: Optional[str] = None
    ) -> Dict[str, Path]:
        """
        Set up standard output directories for environment plugins.

        Args:
            output_dir: Base output directory
            env_sub_type: Environment sub-type
            test_name: Optional test name for nested directories

        Returns:
            dict: Dictionary of directory paths
        """
        base_path = Path(output_dir)

        # Skip directory creation for execution environments that manage their own file placement
        # TODO: add decorator to skip directory creation for specific execution environments
        execution_environment_skip = {"strace"}

        if env_sub_type in execution_environment_skip:
            logger.debug(
                f"Skipping directory creation for {env_sub_type} - manages own file placement"
            )
            return {
                "base": base_path,
                "env_output": base_path,  # Return base path instead of creating sub-directories
                "logs": base_path / "logs",
                "results": base_path / "results",
                "artifacts": base_path / "artifacts",
            }

        if test_name:
            env_output_dir = base_path / test_name / env_sub_type
        else:
            env_output_dir = base_path / env_sub_type

        directories = {
            "base": base_path,
            "env_output": env_output_dir,
            "logs": env_output_dir / "logs",
            "results": env_output_dir / "results",
            "artifacts": env_output_dir / "artifacts",
        }

        # Ensure directories exist
        for dir_path in directories.values():
            dir_path.mkdir(parents=True, exist_ok=True)

        return directories
