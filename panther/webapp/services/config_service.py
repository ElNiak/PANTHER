"""Service layer for configuration validation and YAML generation."""

import copy
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

import yaml

logger = logging.getLogger(__name__)


@dataclass
class FieldError:
    """Validation error with location and severity."""

    path: str
    message: str
    severity: str = "error"  # "error" | "warning"


# Resolve default config relative to project root (where pyproject.toml lives)
_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_DEFAULT_CONFIG_CANDIDATES = [
    _PROJECT_ROOT
    / "experiment-config"
    / "base"
    / "experiment_config_example_minimal_docker.yaml",
    _PROJECT_ROOT
    / "experiment-config"
    / "base"
    / "experiment_config_example_minimal.yaml",
]


class ConfigService:
    """Service for config validation, YAML generation, and form model adaptation."""

    def get_default_yaml(self) -> str:
        """Return a default experiment config YAML template."""
        for candidate in _DEFAULT_CONFIG_CANDIDATES:
            if candidate.is_file():
                return candidate.read_text()
        raise FileNotFoundError(
            f"No default config found. Searched: {[str(c) for c in _DEFAULT_CONFIG_CANDIDATES]}"
        )

    def validate_yaml(self, yaml_content: str) -> Optional[str]:
        """Validate a YAML string as a PANTHER config.

        Returns None if valid, or an error message string.
        """
        # Step 1: YAML syntax check
        try:
            data = yaml.safe_load(yaml_content)
        except yaml.YAMLError as e:
            return f"YAML syntax error: {e}"

        if not isinstance(data, dict):
            return "Config must be a YAML mapping (dict)"

        # Step 2: Basic structural validation
        # Full Pydantic validation can be added here via config models
        try:
            from panther.config.core.models import GlobalConfig

            global_section = data.get("logging") or data.get("global", {})
            if isinstance(global_section, dict) and "level" in global_section:
                # Quick check that log level is valid
                GlobalConfig(logging=global_section)
        except Exception as e:
            return f"Config validation error: {e}"

        if "tests" not in data:
            return "Config must contain a 'tests' section"

        if not isinstance(data["tests"], list) or len(data["tests"]) == 0:
            return "'tests' must be a non-empty list"

        return None

    def yaml_to_dict(self, yaml_content: str) -> Optional[dict]:
        """Parse YAML content to a dict. Returns None on error."""
        try:
            return yaml.safe_load(yaml_content)
        except yaml.YAMLError:
            return None

    def dict_to_yaml(self, data: dict) -> str:
        """Convert a dict to YAML string."""
        return yaml.dump(data, default_flow_style=False, sort_keys=False)

    def load_config(self, path) -> dict:
        """Load and parse a YAML config file. Raises FileNotFoundError/ValueError."""
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"Config file not found: {path}")
        try:
            data = yaml.safe_load(p.read_text())
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML: {e}") from e
        if not isinstance(data, dict):
            raise ValueError("Config must be a YAML mapping")
        return data

    def save_config(self, path, data: dict) -> None:
        """Save a config dict to a YAML file, creating parent dirs."""
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(yaml.dump(data, default_flow_style=False, sort_keys=False))

    def list_configs(self, directory=None) -> list[dict]:
        """List YAML config files in a directory.

        Returns [{name, path, modified}]. Defaults to experiment-config/base/.
        """
        if directory is None:
            directory = _PROJECT_ROOT / "experiment-config" / "base"
        d = Path(directory)
        if not d.exists():
            return []
        results = []
        for f in sorted(d.iterdir()):
            if f.is_file() and f.suffix in (".yaml", ".yml"):
                results.append(
                    {
                        "name": f.name,
                        "path": str(f),
                        "modified": datetime.fromtimestamp(f.stat().st_mtime),
                    }
                )
        return results

    def validate_config_detailed(self, data: dict) -> list["FieldError"]:
        """Field-level validation against Pydantic models.

        Returns list of FieldError with path/message/severity.
        """
        errors: list[FieldError] = []

        if "tests" not in data:
            errors.append(
                FieldError(path="tests", message="'tests' section is required")
            )
            return errors

        tests = data.get("tests")
        if not isinstance(tests, list) or len(tests) == 0:
            errors.append(
                FieldError(
                    path="tests",
                    message="'tests' must be a non-empty list",
                    severity="warning",
                )
            )

        logging_data = data.get("logging")
        if logging_data and isinstance(logging_data, dict):
            try:
                from panther.config.core.models import GlobalConfig

                GlobalConfig(logging=logging_data)
            except Exception as e:
                for err_line in str(e).splitlines()[:5]:
                    errors.append(FieldError(path="logging", message=err_line.strip()))

        return errors

    def merge_configs(self, base: dict, overlay: dict) -> dict:
        """Deep merge overlay into base (overlay wins on conflicts)."""
        return self._deep_merge(base, overlay)

    def resolve_interpolations(self, data: dict) -> dict:
        """Resolve ${var} interpolations in config data."""
        try:
            from omegaconf import OmegaConf

            cfg = OmegaConf.create(data)
            return OmegaConf.to_container(cfg, resolve=True)
        except Exception:
            return dict(data)

    @staticmethod
    def _deep_merge(base: dict, overlay: dict) -> dict:
        """Recursively merge overlay into a copy of base."""
        result = copy.deepcopy(base)
        for key, value in overlay.items():
            if (
                key in result
                and isinstance(result[key], dict)
                and isinstance(value, dict)
            ):
                result[key] = ConfigService._deep_merge(result[key], value)
            else:
                result[key] = copy.deepcopy(value)
        return result
