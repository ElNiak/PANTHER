from typing import Any, Dict, List, Optional, Union

"""
File Utilities

This module provides common file operations used throughout PANTHER.
"""

import json
import logging
from pathlib import Path

import yaml

logger = logging.getLogger(__name__)


class FileOperationError(Exception):
    """Exception raised when file operations fail."""

    pass


class FileUtils:
    """Utility class for common file operations."""

    @staticmethod
    def read_yaml_file(file_path: Union[str, Path]) -> Dict[str, Any]:
        """
        Read and parse a YAML file safely.

        Args:
            file_path: Path to the YAML file

        Returns:
            dict: Parsed YAML content

        Raises:
            FileOperationError: If file cannot be read or parsed
        """
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileOperationError(f"YAML file not found: {file_path}")

        try:
            with open(file_path, encoding="utf-8") as f:
                content = yaml.safe_load(f)
                if content is None:
                    return {}
                return content
        except yaml.YAMLError as e:
            raise FileOperationError(f"Invalid YAML in {file_path}: {e}") from e
        except Exception as e:
            raise FileOperationError(
                f"Failed to read YAML file {file_path}: {e}"
            ) from e

    @staticmethod
    def write_yaml_file(file_path: Union[str, Path], data: Dict[str, Any]) -> None:
        """
        Write data to a YAML file safely.

        Args:
            file_path: Path to write the YAML file
            data: Data to write

        Raises:
            FileOperationError: If file cannot be written
        """
        file_path = Path(file_path)

        try:
            # Ensure parent directory exists
            file_path.parent.mkdir(parents=True, exist_ok=True)

            with open(file_path, "w", encoding="utf-8") as f:
                yaml.safe_dump(data, f, default_flow_style=False, sort_keys=False)
        except Exception as e:
            raise FileOperationError(
                f"Failed to write YAML file {file_path}: {e}"
            ) from e

    @staticmethod
    def read_json_file(file_path: Union[str, Path]) -> Dict[str, Any]:
        """
        Read and parse a JSON file safely.

        Args:
            file_path: Path to the JSON file

        Returns:
            dict: Parsed JSON content

        Raises:
            FileOperationError: If file cannot be read or parsed
        """
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileOperationError(f"JSON file not found: {file_path}")

        try:
            with open(file_path, encoding="utf-8") as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            raise FileOperationError(f"Invalid JSON in {file_path}: {e}") from e
        except Exception as e:
            raise FileOperationError(
                f"Failed to read JSON file {file_path}: {e}"
            ) from e

    @staticmethod
    def write_json_file(
        file_path: Union[str, Path], data: Dict[str, Any], indent: int = 2
    ) -> None:
        """
        Write data to a JSON file safely.

        Args:
            file_path: Path to write the JSON file
            data: Data to write
            indent: JSON indentation level

        Raises:
            FileOperationError: If file cannot be written
        """
        file_path = Path(file_path)

        try:
            # Ensure parent directory exists
            file_path.parent.mkdir(parents=True, exist_ok=True)

            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=indent, ensure_ascii=False)
        except Exception as e:
            raise FileOperationError(
                f"Failed to write JSON file {file_path}: {e}"
            ) from e

    @staticmethod
    def read_text_file(file_path: Union[str, Path]) -> str:
        """
        Read a text file safely.

        Args:
            file_path: Path to the text file

        Returns:
            str: File content

        Raises:
            FileOperationError: If file cannot be read
        """
        file_path = Path(file_path)

        if not file_path.exists():
            raise FileOperationError(f"Text file not found: {file_path}")

        try:
            with open(file_path, encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            raise FileOperationError(
                f"Failed to read text file {file_path}: {e}"
            ) from e

    @staticmethod
    def write_text_file(file_path: Union[str, Path], content: str) -> None:
        """
        Write text to a file safely.

        Args:
            file_path: Path to write the text file
            content: Text content to write

        Raises:
            FileOperationError: If file cannot be written
        """
        file_path = Path(file_path)

        try:
            # Ensure parent directory exists
            file_path.parent.mkdir(parents=True, exist_ok=True)

            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
        except Exception as e:
            raise FileOperationError(
                f"Failed to write text file {file_path}: {e}"
            ) from e

    @staticmethod
    def find_files_by_pattern(directory: Union[str, Path], pattern: str) -> List[Path]:
        """
        Find files matching a pattern in a directory.

        Args:
            directory: Directory to search in
            pattern: Glob pattern to match (e.g., "*.yaml", "config_*")

        Returns:
            list: List of matching file paths

        Raises:
            FileOperationError: If directory doesn't exist
        """
        directory = Path(directory)

        if not directory.exists():
            raise FileOperationError(f"Directory not found: {directory}")

        if not directory.is_dir():
            raise FileOperationError(f"Path is not a directory: {directory}")

        try:
            return list(directory.glob(pattern))
        except Exception as e:
            raise FileOperationError(
                f"Failed to search directory {directory}: {e}"
            ) from e

    @staticmethod
    def ensure_directory_exists(directory: Union[str, Path]) -> Path:
        """
        Ensure a directory exists, creating it if necessary.

        Args:
            directory: Directory path

        Returns:
            Path: The directory path

        Raises:
            FileOperationError: If directory cannot be created
        """
        directory = Path(directory)

        try:
            directory.mkdir(parents=True, exist_ok=True)
            return directory
        except Exception as e:
            raise FileOperationError(
                f"Failed to create directory {directory}: {e}"
            ) from e

    @staticmethod
    def file_exists_and_readable(file_path: Union[str, Path]) -> bool:
        """
        Check if a file exists and is readable.

        Args:
            file_path: Path to check

        Returns:
            bool: True if file exists and is readable
        """
        try:
            file_path = Path(file_path)
            return (
                file_path.exists()
                and file_path.is_file()
                and file_path.stat().st_size >= 0
            )
        except Exception:
            return False


class ConfigurationLoader:
    """
    Utility class for loading configuration files with common patterns.
    """

    @staticmethod
    def load_config_with_defaults(
        config_path: Union[str, Path], defaults: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Load configuration file with default values.

        Args:
            config_path: Path to configuration file
            defaults: Default configuration values

        Returns:
            dict: Merged configuration
        """
        defaults = defaults or {}

        if not FileUtils.file_exists_and_readable(config_path):
            logger.warning(
                f"Configuration file not found: {config_path}, using defaults"
            )
            return defaults.copy()

        try:
            config = FileUtils.read_yaml_file(config_path)
            # Merge with defaults (config takes precedence)
            merged_config = defaults.copy()
            merged_config.update(config)
            return merged_config
        except FileOperationError as e:
            logger.error(f"Failed to load configuration: {e}")
            return defaults.copy()

    @staticmethod
    def load_configs_from_directory(
        directory: Union[str, Path], pattern: str = "*.y*ml"
    ) -> Dict[str, Dict[str, Any]]:
        """
        Load all configuration files from a directory.

        Args:
            directory: Directory containing configuration files
            pattern: File pattern to match

        Returns:
            dict: Dictionary mapping filenames to configuration data
        """
        configs = {}

        try:
            config_files = FileUtils.find_files_by_pattern(directory, pattern)
            for config_file in config_files:
                try:
                    config_data = FileUtils.read_yaml_file(config_file)
                    configs[config_file.stem] = config_data
                except FileOperationError as e:
                    logger.error(f"Failed to load config from {config_file}: {e}")

        except FileOperationError as e:
            logger.error(f"Failed to search config directory {directory}: {e}")

        return configs
