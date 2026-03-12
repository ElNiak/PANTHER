"""ConfigService -- configuration validation, YAML generation, and form-model adaptation.

This module provides a service-layer facade over PANTHER's experiment
configuration system.  It handles every configuration-related operation
that the web UI needs: loading and saving YAML files, validating them
against Pydantic schemas, resolving variable interpolations, and browsing
existing config files on disk.

The service is intentionally stateless -- each method receives its inputs
explicitly and returns plain Python objects (dicts, strings, lists).  This
keeps it easy to test and safe to share across NiceGUI client sessions.

PANTHER context:
    Experiment configurations are YAML documents that describe tests, network
    environments, services (protocol implementations under test), and optional
    execution environments (e.g. strace, gdb).  The canonical schema is defined
    by OmegaConf + Pydantic models in ``panther.config.core.models``, while
    field-level validation is provided by
    ``panther.config.core.components.validators``.
"""

import copy
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal, Optional

import yaml

from panther.config.core.utils.merge import deep_merge
from panther.core.utils.file_utils import ConfigurationLoader, FileUtils

logger = logging.getLogger(__name__)


@dataclass
class FieldError:
    """A single validation finding associated with a specific config field.

    Used by ``ConfigService.validate_config_detailed`` to report per-field
    errors and warnings back to the UI so that they can be rendered inline
    next to the offending form control.

    Attributes:
        path: Dot-delimited path to the field within the config dict
            (e.g. ``"tests.0.services.server.protocol.name"``).
        message: Human-readable description of the problem.
        severity: ``"error"`` for blocking issues that prevent execution,
            ``"warning"`` for non-blocking suggestions.
    """

    path: str
    message: str
    severity: Literal["error", "warning"] = "error"


_PROJECT_ROOT = FileUtils.find_project_root(start_path=Path(__file__).resolve().parent)
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


def _validate_config_path(path_str) -> Path:
    """Sanitize a user-supplied config path, guarding against directory traversal."""
    return FileUtils.validate_path_within_root(
        path_str, _PROJECT_ROOT, (".yaml", ".yml")
    )


class ConfigService:
    """Stateless service for experiment-config validation, I/O, and transformation.

    ConfigService wraps PANTHER's configuration subsystem -- specifically
    the Pydantic models in ``panther.config.core.models`` and the field-level
    validators in ``panther.config.core.components.validators`` -- behind a
    simple, web-friendly API that operates on plain dicts and YAML strings.

    The class follows the *Service Object* pattern: it carries no mutable
    instance state and every method is safe to call from any NiceGUI client
    session without synchronisation.

    Attributes:
        (none -- stateless by design)

    Example::

        svc = ConfigService()
        yaml_text = svc.get_default_yaml()
        error = svc.validate_yaml(yaml_text)
        if error is None:
            data = svc.yaml_to_dict(yaml_text)
            svc.save_config("experiment-config/base/my_config.yaml", data)
    """

    def get_default_yaml(self) -> str:
        """Return a default experiment-config YAML template as a string.

        Searches a predefined list of candidate paths under
        ``experiment-config/base/`` and returns the contents of the first
        file that exists.

        Returns:
            The raw YAML text of the default template.

        Raises:
            FileNotFoundError: If none of the candidate template files exist
                on disk.
        """
        logger.debug("Loading default config YAML template")
        for candidate in _DEFAULT_CONFIG_CANDIDATES:
            if candidate.is_file():
                logger.debug("Default config template found: %s", candidate)
                return candidate.read_text()
        raise FileNotFoundError(
            f"No default config found. Searched: {[str(c) for c in _DEFAULT_CONFIG_CANDIDATES]}"
        )

    def validate_yaml(self, yaml_content: str) -> Optional[str]:
        """Perform quick structural validation of a YAML config string.

        Runs a two-step check: first verifying YAML syntax, then applying
        lightweight structural rules (presence of a ``tests`` section, valid
        log-level if ``logging`` is provided).  This is faster than full
        Pydantic validation and is suitable for on-keystroke feedback in
        the config-builder UI.

        Args:
            yaml_content: Raw YAML text to validate.

        Returns:
            ``None`` if the content passes validation, otherwise a
            human-readable error message string.
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
        except ImportError as e:
            logger.error("Failed to import config models: %s", e)
            return f"Internal error: config models unavailable ({e})"
        except Exception as e:
            return f"Config validation error: {e}"

        if "tests" not in data:
            return "Config must contain a 'tests' section"

        if not isinstance(data["tests"], list) or len(data["tests"]) == 0:
            return "'tests' must be a non-empty list"

        return None

    def yaml_to_dict(self, yaml_content: str) -> Optional[dict]:
        """Parse a YAML string into a Python dict.

        Args:
            yaml_content: Raw YAML text.

        Returns:
            The parsed dict, or ``None`` if the text is not valid YAML.
        """
        try:
            return yaml.safe_load(yaml_content)
        except yaml.YAMLError as e:
            logger.warning("Failed to parse YAML: %s", e)
            return None

    def dict_to_yaml(self, data: dict) -> str:
        """Serialise a Python dict to a YAML string.

        Args:
            data: The dictionary to serialise.

        Returns:
            A YAML-formatted string with block style and original key order
            preserved.
        """
        return yaml.dump(data, default_flow_style=False, sort_keys=False)

    def load_config(self, path) -> dict:
        """Load and parse an experiment-config YAML file from disk.

        The path is sanitised to prevent directory-traversal attacks and
        must point to a ``.yaml`` or ``.yml`` file within the project root.

        Args:
            path: Filesystem path (string or ``Path``) to the YAML file.

        Returns:
            The parsed configuration as a dict.

        Raises:
            FileNotFoundError: If the resolved path does not exist.
            ValueError: If the file is not valid YAML or is not a mapping.
        """
        p = _validate_config_path(path)
        if not p.exists():
            raise FileNotFoundError(f"Config file not found: {path}")
        try:
            data = yaml.safe_load(p.read_text())
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML: {e}") from e
        if not isinstance(data, dict):
            raise ValueError("Config must be a YAML mapping")
        logger.info("Loaded config file: %s", p)
        return data

    def save_config(self, path, data: dict) -> None:
        """Write a configuration dict to a YAML file on disk.

        Parent directories are created automatically if they do not exist.
        The path undergoes the same traversal-safety check as ``load_config``.

        Args:
            path: Destination filesystem path (string or ``Path``).
            data: The configuration dict to serialise and write.

        Raises:
            ValueError: If the path fails sanitisation (wrong extension or
                outside project root).
        """
        p = _validate_config_path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(yaml.dump(data, default_flow_style=False, sort_keys=False))
        logger.info("Saved config file: %s", p)

    def list_configs(self, directory=None) -> list[dict]:
        """List YAML config files in a single directory (non-recursive).

        Args:
            directory: Directory to scan.  Defaults to
                ``<project_root>/experiment-config/base/``.

        Returns:
            A list of dicts, each with keys ``name`` (filename), ``path``
            (absolute string path), and ``modified`` (``datetime`` of last
            modification).  Returns an empty list if the directory does
            not exist.
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
                        "modified": datetime.fromtimestamp(
                            f.stat().st_mtime, tz=timezone.utc
                        ),
                    }
                )
        logger.debug("Listed %d config files in %s", len(results), d)
        return results

    def list_configs_recursive(self, root=None) -> list[dict]:
        """Recursively list all YAML config files under a directory tree.

        Delegates to ``ConfigurationLoader.list_configs_recursive()`` which
        walks the tree and extracts a lightweight summary from each file.

        Args:
            root: Root directory to walk.  Defaults to
                ``<project_root>/experiment-config/``.

        Returns:
            A list of dicts with keys ``name``, ``path``, ``modified``,
            ``category`` (relative subdirectory), and ``summary`` (a dict
            with ``test_count``, ``test_names``, ``services``,
            ``protocols``, ``environment``).
        """
        if root is None:
            root = _PROJECT_ROOT / "experiment-config"
        logger.debug("Listing configs recursively from: %s", root)
        return ConfigurationLoader.list_configs_recursive(root)

    @staticmethod
    def _extract_config_summary(path: Path) -> dict:
        """Extract a lightweight summary dict from a config YAML file."""
        return ConfigurationLoader.extract_config_summary(path)

    def validate_config_detailed(self, data: dict) -> list["FieldError"]:
        """Run full Pydantic-based validation and return per-field findings.

        Unlike ``validate_yaml`` (which performs quick structural checks on
        raw YAML text), this method delegates to
        ``panther.config.core.components.validators.validate_config_dict``
        (PANTHER's exhaustive config validator) and converts the result into
        a flat list of ``FieldError`` instances suitable for rendering in
        the config-builder form.

        Args:
            data: A parsed config dict (as returned by ``yaml_to_dict``).

        Returns:
            A list of ``FieldError`` instances.  An empty list means the
            config is fully valid.
        """
        from panther.config.core.components.validators import validate_config_dict

        result = validate_config_dict(data)

        errors: list[FieldError] = []
        for err in result.errors:
            errors.append(
                FieldError(path=err.field, message=err.message, severity="error")
            )
        for warn in result.warnings:
            errors.append(
                FieldError(path=warn.field, message=warn.message, severity="warning")
            )
        error_count = sum(1 for e in errors if e.severity == "error")
        warning_count = sum(1 for e in errors if e.severity == "warning")
        logger.debug(
            "Detailed validation: %d errors, %d warnings", error_count, warning_count
        )
        return errors

    def merge_configs(self, base: dict, overlay: dict) -> dict:
        """Deep-merge two config dicts, with *overlay* winning on conflicts.

        Nested dicts are merged recursively; all other value types in
        *overlay* replace the corresponding entry in *base*.  Neither
        input dict is mutated.

        Args:
            base: The base configuration dict.
            overlay: The override dict whose values take priority.

        Returns:
            A new dict containing the merged result.
        """
        return deep_merge(copy.deepcopy(base), overlay)

    def resolve_interpolations(self, data: dict) -> dict:
        """Resolve ``${section.key}`` variable interpolations in config values.

        Walks the config dict recursively and replaces every
        ``${dot.separated.path}`` reference with the value found at that
        path within the same dict.  References that cannot be resolved are
        left as-is.  The input dict is not mutated.

        Args:
            data: A parsed config dict potentially containing interpolation
                placeholders.

        Returns:
            A deep copy of *data* with all resolvable placeholders replaced
            by their concrete values.
        """
        import re

        result = copy.deepcopy(data)
        pattern = re.compile(r"\$\{([^}]+)\}")

        def _lookup(keys_str, root):
            node = root
            for k in keys_str.split("."):
                if isinstance(node, dict) and k in node:
                    node = node[k]
                else:
                    return None
            return node if not isinstance(node, dict) else None

        def _resolve(value, root):
            if isinstance(value, str):
                return pattern.sub(
                    lambda m: (
                        str(v)
                        if (v := _lookup(m.group(1), root)) is not None
                        else m.group(0)
                    ),
                    value,
                )
            elif isinstance(value, dict):
                return {k: _resolve(v, root) for k, v in value.items()}
            elif isinstance(value, list):
                return [_resolve(v, root) for v in value]
            return value

        return _resolve(result, result)
