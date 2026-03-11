"""Service layer for configuration validation and YAML generation."""

import copy
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Literal, Optional

import yaml

logger = logging.getLogger(__name__)


@dataclass
class FieldError:
    """Validation error with location and severity."""

    path: str
    message: str
    severity: Literal["error", "warning"] = "error"


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


def _validate_config_path(path_str) -> Path:
    """Sanitize config path: resolve traversal and ensure YAML extension."""
    resolved = Path(str(path_str)).resolve()
    if resolved.suffix.lower() not in (".yaml", ".yml"):
        raise ValueError(f"Path '{path_str}' must be a YAML file (.yaml/.yml)")
    if not resolved.is_relative_to(_PROJECT_ROOT):
        raise ValueError(f"Path must be within the project directory ({_PROJECT_ROOT})")
    return resolved


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
        """Parse YAML content to a dict. Returns None on error."""
        try:
            return yaml.safe_load(yaml_content)
        except yaml.YAMLError as e:
            logger.warning("Failed to parse YAML: %s", e)
            return None

    def dict_to_yaml(self, data: dict) -> str:
        """Convert a dict to YAML string."""
        return yaml.dump(data, default_flow_style=False, sort_keys=False)

    def load_config(self, path) -> dict:
        """Load and parse a YAML config file. Validates path for traversal."""
        p = _validate_config_path(path)
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
        """Save a config dict to a YAML file. Validates path for traversal."""
        p = _validate_config_path(path)
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

    def list_configs_recursive(self, root=None) -> list[dict]:
        """Recursively list all YAML configs under experiment-config/.

        Returns [{name, path, modified, category, summary}].
        summary = {test_count, test_names, services, protocols, environment}
        """
        if root is None:
            root = _PROJECT_ROOT / "experiment-config"
        root = Path(root)
        if not root.exists():
            return []
        results = []
        yaml_files = sorted(
            f for f in root.rglob("*") if f.is_file() and f.suffix in (".yaml", ".yml")
        )
        for f in yaml_files:
            category = str(f.parent.relative_to(root))
            if category == ".":
                category = ""
            summary = self._extract_config_summary(f)
            results.append(
                {
                    "name": f.name,
                    "path": str(f),
                    "modified": datetime.fromtimestamp(f.stat().st_mtime),
                    "category": category,
                    "summary": summary,
                }
            )
        return results

    @staticmethod
    def _extract_config_summary(path: Path) -> dict:
        """Extract a lightweight summary from a config YAML file."""
        try:
            data = yaml.safe_load(path.read_text())
        except Exception:
            logger.warning("Failed to parse config file %s", path, exc_info=True)
            return {
                "test_count": 0,
                "test_names": [],
                "services": [],
                "protocols": [],
                "environment": "",
            }
        if not isinstance(data, dict):
            return {
                "test_count": 0,
                "test_names": [],
                "services": [],
                "protocols": [],
                "environment": "",
            }
        tests = data.get("tests", [])
        if not isinstance(tests, list):
            return {
                "test_count": 0,
                "test_names": [],
                "services": [],
                "protocols": [],
                "environment": "",
            }

        test_names = []
        all_services = []
        all_protocols = set()
        environment = ""
        for t in tests:
            if not isinstance(t, dict):
                continue
            test_names.append(t.get("name", "unnamed"))
            net_env = t.get("network_environment", {})
            if isinstance(net_env, dict) and not environment:
                environment = net_env.get("type", "")
            services = t.get("services", {})
            if isinstance(services, dict):
                for svc_name, svc in services.items():
                    all_services.append(svc_name)
                    if isinstance(svc, dict):
                        proto = svc.get("protocol", {})
                        if isinstance(proto, dict) and proto.get("name"):
                            all_protocols.add(proto["name"])
        return {
            "test_count": len(tests),
            "test_names": test_names,
            "services": list(dict.fromkeys(all_services)),  # unique, order-preserving
            "protocols": sorted(all_protocols),
            "environment": environment,
        }

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

        # Validate individual tests: service count, types, and roles
        if isinstance(tests, list):
            for i, test in enumerate(tests):
                if not isinstance(test, dict):
                    continue
                test_name = test.get("name", f"test[{i}]")
                services = test.get("services")
                if not isinstance(services, dict):
                    continue

                # Rule 1: Min 2 services (ERROR)
                if len(services) < 2:
                    errors.append(
                        FieldError(
                            path=f"tests[{i}].services",
                            message=(
                                f"Test '{test_name}' has {len(services)} service(s);"
                                " at least 2 required."
                            ),
                            severity="error",
                        )
                    )

                # Collect implementation types and roles
                impl_types: set[str] = set()
                roles: set[str] = set()
                for svc in services.values():
                    if isinstance(svc, dict):
                        impl = svc.get("implementation", {})
                        if isinstance(impl, dict):
                            t = impl.get("type", "").lower()
                            if t:
                                impl_types.add(t)
                        proto = svc.get("protocol", {})
                        if isinstance(proto, dict):
                            r = proto.get("role", "").lower()
                            if r:
                                roles.add(r)

                # Rule 2: No tester service (WARNING)
                if "testers" not in impl_types:
                    errors.append(
                        FieldError(
                            path=f"tests[{i}].services",
                            message=f"Test '{test_name}' has no tester service.",
                            severity="warning",
                        )
                    )

                # Rule 5: No IUT service (WARNING)
                if "iut" not in impl_types:
                    errors.append(
                        FieldError(
                            path=f"tests[{i}].services",
                            message=f"Test '{test_name}' has no IUT service.",
                            severity="warning",
                        )
                    )

                # Rule 3: Missing role counterpart (WARNING)
                if "client" in roles and "server" not in roles:
                    errors.append(
                        FieldError(
                            path=f"tests[{i}].services",
                            message=(
                                f"Test '{test_name}' has client(s) but no server."
                            ),
                            severity="warning",
                        )
                    )
                if "server" in roles and "client" not in roles:
                    errors.append(
                        FieldError(
                            path=f"tests[{i}].services",
                            message=(
                                f"Test '{test_name}' has server(s) but no client."
                            ),
                            severity="warning",
                        )
                    )

                # Rule 4: Client without valid target (WARNING)
                for svc_name, svc in services.items():
                    if not isinstance(svc, dict):
                        continue
                    proto = svc.get("protocol", {})
                    if not isinstance(proto, dict):
                        continue
                    if proto.get("role", "").lower() != "client":
                        continue
                    target = proto.get("target")
                    if not target:
                        errors.append(
                            FieldError(
                                path=f"tests[{i}].services.{svc_name}.protocol.target",
                                message=(
                                    f"Client '{svc_name}' has no target specified."
                                ),
                                severity="warning",
                            )
                        )
                    elif target in services:
                        target_svc = services[target]
                        if isinstance(target_svc, dict):
                            target_proto = target_svc.get("protocol", {})
                            if isinstance(target_proto, dict):
                                target_role = target_proto.get("role", "").lower()
                                if target_role != "server":
                                    errors.append(
                                        FieldError(
                                            path=f"tests[{i}].services.{svc_name}.protocol.target",
                                            message=(
                                                f"Client '{svc_name}' targets"
                                                f" '{target}'"
                                                f" (role='{target_role}',"
                                                " expected 'server')."
                                            ),
                                            severity="warning",
                                        )
                                    )

        logging_data = data.get("logging")
        if logging_data and isinstance(logging_data, dict):
            try:
                from panther.config.core.models import GlobalConfig

                GlobalConfig(logging=logging_data)
            except ImportError as e:
                logger.error("Failed to import config models: %s", e)
                errors.append(
                    FieldError(
                        path="logging",
                        message=f"Internal error: config models unavailable ({e})",
                    )
                )
            except Exception as e:
                for err_line in str(e).splitlines()[:5]:
                    errors.append(FieldError(path="logging", message=err_line.strip()))

        return errors

    def merge_configs(self, base: dict, overlay: dict) -> dict:
        """Deep merge overlay into base (overlay wins on conflicts)."""
        return self._deep_merge(base, overlay)

    def resolve_interpolations(self, data: dict) -> dict:
        """Resolve ${section.key} interpolations in config values."""
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

    @staticmethod
    def generate_test_name(test_data: dict) -> str:
        """Generate a test name from services, protocol, and environment info.

        Follows project naming conventions, e.g.:
        ``"QUIC Client-Server Communication Test"``
        ``"Strace - Shadow QUIC Client-Server Communication Test"``
        """
        services = test_data.get("services", {})
        if not services:
            return ""

        protocols: set[str] = set()
        role_parts: list[str] = []
        for svc_data in services.values():
            svc = svc_data if isinstance(svc_data, dict) else {}
            proto = svc.get("protocol", {})
            proto_name = proto.get("name", "") if isinstance(proto, dict) else ""
            if proto_name:
                protocols.add(proto_name.upper())
            role = (
                proto.get("role", "unknown") if isinstance(proto, dict) else "unknown"
            )
            role_parts.append(role.title())

        proto_str = "-".join(sorted(protocols)) if protocols else "Protocol"
        role_str = "-".join(role_parts) if role_parts else ""

        # Execution environment prefix (e.g. "Strace - ")
        exec_envs = test_data.get("execution_environment", [])
        exec_prefix = ""
        if isinstance(exec_envs, list) and exec_envs:
            exec_types = [
                e.get("type", "")
                for e in exec_envs
                if isinstance(e, dict) and e.get("type")
            ]
            if exec_types:
                exec_prefix = " ".join(t.title() for t in exec_types) + " - "

        # Network environment prefix (only for non-default environments)
        net_env = test_data.get("network_environment", {})
        net_type = net_env.get("type", "") if isinstance(net_env, dict) else ""
        net_prefix = ""
        if net_type and net_type not in ("docker_compose", ""):
            net_prefix = net_type.replace("_", " ").title() + " "

        return f"{exec_prefix}{net_prefix}{proto_str} {role_str} Communication Test".strip()

    @staticmethod
    def generate_test_description(test_data: dict) -> str:
        """Generate a test description from services and environment info."""
        services = test_data.get("services", {})
        if not services:
            return ""

        svc_parts: list[str] = []
        for svc_name, svc_data in services.items():
            svc = svc_data if isinstance(svc_data, dict) else {}
            impl = svc.get("implementation", {})
            proto = svc.get("protocol", {})
            impl_name = (
                impl.get("name", svc_name) if isinstance(impl, dict) else svc_name
            )
            role = proto.get("role", "") if isinstance(proto, dict) else ""
            svc_parts.append(f"{impl_name} ({role})" if role else impl_name)

        svc_str = " and ".join(svc_parts)

        net_env = test_data.get("network_environment", {})
        net_type = (
            net_env.get("type", "network") if isinstance(net_env, dict) else "network"
        )

        return (
            f"Verify communication between {svc_str}"
            f" over {net_type.replace('_', ' ')} network."
        )

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
