"""Utilities for summarizing configurations to reduce log verbosity."""

# panther/core/utils/config_summarizer.py
import json
import re
from typing import Any, Dict, Set


class ConfigSummarizer:
    """Summarize configurations to reduce log verbosity."""

    SENSITIVE_PATTERNS = [
        (r"password.*", "<REDACTED>"),
        (r"token.*", "<TOKEN>"),
        (r"secret.*", "<SECRET>"),
        (r"key.*", "<KEY>"),
        (r"certificate.*", "<CERT>"),
    ]

    DEFAULT_VALUES = {
        "timeout": 60,
        "retries": 3,
        "debug": False,
        "log_level": "INFO",
        "enabled": True,
        "force_build_docker_image": False,
    }

    @classmethod
    def summarize(cls, config: Dict[str, Any], max_depth: int = 2) -> str:
        """Create a concise summary of configuration."""
        non_defaults = cls._extract_non_defaults(config)
        sanitized = cls._sanitize_sensitive(non_defaults)

        if not sanitized:
            return "All settings at default values"

        summary_parts = []
        cls._build_summary(sanitized, summary_parts, max_depth=max_depth)

        return f"Config: {', '.join(summary_parts)}"

    @classmethod
    def _build_summary(
        cls, config: Dict[str, Any], parts: list, depth: int = 0, max_depth: int = 2
    ):
        """Recursively build summary parts."""
        for key, value in config.items():
            if isinstance(value, dict) and depth < max_depth:
                nested_parts = []
                cls._build_summary(value, nested_parts, depth + 1, max_depth)
                if nested_parts:
                    parts.append(f"{key}({', '.join(nested_parts)})")
                else:
                    parts.append(f"{key}(empty)")
            elif isinstance(value, list):
                if value and isinstance(value[0], dict):
                    parts.append(f"{key}[{len(value)} items]")
                else:
                    parts.append(
                        f"{key}={value[:3]}..." if len(value) > 3 else f"{key}={value}"
                    )
            else:
                parts.append(f"{key}={value}")

    @classmethod
    def _extract_non_defaults(cls, config: Dict[str, Any]) -> Dict[str, Any]:
        """Extract only non-default configuration values."""
        result = {}
        for key, value in config.items():
            if isinstance(value, dict):
                nested = cls._extract_non_defaults(value)
                if nested:  # Only include if nested dict has non-default values
                    result[key] = nested
            elif key in cls.DEFAULT_VALUES:
                if value != cls.DEFAULT_VALUES[key]:
                    result[key] = value
            else:
                # Include all non-default keys
                result[key] = value
        return result

    @classmethod
    def _sanitize_sensitive(cls, config: Dict[str, Any]) -> Dict[str, Any]:
        """Mask sensitive configuration values."""

        def _sanitize_value(key: str, value: Any) -> Any:
            key_lower = key.lower()
            for pattern, replacement in cls.SENSITIVE_PATTERNS:
                if re.match(pattern, key_lower):
                    return replacement
            return value

        result = {}
        for key, value in config.items():
            if isinstance(value, dict):
                result[key] = cls._sanitize_sensitive(value)
            elif isinstance(value, list):
                # Don't expose lists that might contain sensitive data
                if any(
                    re.match(pattern[0], key.lower())
                    for pattern in cls.SENSITIVE_PATTERNS
                ):
                    result[key] = f"<{len(value)} items>"
                else:
                    result[key] = value
            else:
                result[key] = _sanitize_value(key, value)
        return result

    @classmethod
    def get_full_config(cls, config: Dict[str, Any]) -> str:
        """Get full sanitized config for TRACE level logging."""
        sanitized = cls._sanitize_sensitive(config)
        return json.dumps(sanitized, indent=2, default=str)

    @classmethod
    def diff_configs(
        cls, old_config: Dict[str, Any], new_config: Dict[str, Any]
    ) -> str:
        """Show only differences between configurations."""
        differences = cls._find_differences(old_config, new_config)
        if not differences:
            return "No configuration changes"

        sanitized = cls._sanitize_sensitive(differences)
        return f"Config changes: {cls.summarize(sanitized)}"

    @classmethod
    def _find_differences(
        cls, old: Dict[str, Any], new: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Find differences between two configurations."""
        diff = {}
        all_keys = set(old.keys()) | set(new.keys())

        for key in all_keys:
            if key not in old:
                diff[key] = {"added": new[key]}
            elif key not in new:
                diff[key] = {"removed": old[key]}
            elif old[key] != new[key]:
                if isinstance(old[key], dict) and isinstance(new[key], dict):
                    nested_diff = cls._find_differences(old[key], new[key])
                    if nested_diff:
                        diff[key] = nested_diff
                else:
                    diff[key] = {"old": old[key], "new": new[key]}

        return diff


def log_omega_config_summary(logger, config_name: str, config_data) -> None:
    """Log OmegaConf configuration with concise summary for debug level.

    This function replaces verbose patterns like:
        logger.debug("Test Config: %s", OmegaConf.to_yaml(test_config_dict))

    With concise summaries that only show non-default values.

    Args:
        logger: Logger instance
        config_name: Name/type of config (e.g., "Test Config", "Global Config")
        config_data: Configuration data (dict, OmegaConf, or Pydantic model)
    """
    try:
        # Convert to dict if it's a Pydantic model
        if hasattr(config_data, "dict"):
            config_dict = config_data.dict()
        elif hasattr(config_data, "_content"):  # OmegaConf DictConfig
            from omegaconf import OmegaConf

            config_dict = OmegaConf.to_container(config_data, resolve=True)
        else:
            config_dict = config_data

        # Use ConfigSummarizer for concise output
        summary = ConfigSummarizer.summarize(config_dict, max_depth=3)
        logger.debug("%s: %s", config_name, summary)

    except Exception as e:
        # Fallback to basic logging if summarization fails
        logger.debug("%s: <summarization failed: %s>", config_name, str(e))


def log_omega_config_full(logger, config_name: str, config_data) -> None:
    """Log full OmegaConf configuration (use sparingly, for TRACE level).

    Args:
        logger: Logger instance
        config_name: Name/type of config
        config_data: Configuration data (dict, OmegaConf, or Pydantic model)
    """
    try:
        # Convert to dict if it's a Pydantic model
        if hasattr(config_data, "dict"):
            config_dict = config_data.dict()
        elif hasattr(config_data, "_content"):  # OmegaConf DictConfig
            from omegaconf import OmegaConf

            config_dict = OmegaConf.to_container(config_data, resolve=True)
        else:
            config_dict = config_data

        # Use ConfigSummarizer for full sanitized output
        full_config = ConfigSummarizer.get_full_config(config_dict)
        logger.debug("%s (full):\n%s", config_name, full_config)

    except Exception as e:
        logger.debug("%s (full): <serialization failed: %s>", config_name, str(e))
