"""Pure-dict merge and update utilities.

Replaces OmegaConf.merge() and OmegaConf.update() for internal config operations.
OmegaConf is retained only at the YAML loading boundary for ${} interpolation.
"""

from typing import Any


def deep_merge(base: dict, override: dict) -> dict:
    """Recursively merge override into base. Override wins for scalars.

    Args:
        base: Base dictionary.
        override: Dictionary whose values take precedence.

    Returns:
        New merged dictionary (base is not mutated).
    """
    result = base.copy()
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def dot_notation_update(data: dict, dot_key: str, value: Any) -> dict:
    """Update a nested dict value using dot-notation key.

    Creates intermediate dicts as needed. Mutates ``data`` in place.

    Args:
        data: Dictionary to update.
        dot_key: Dot-separated path (e.g. ``"docker.force_build"``).
        value: Value to set.

    Returns:
        The same ``data`` dict (for chaining).
    """
    keys = dot_key.split(".")
    current = data
    for key in keys[:-1]:
        if key not in current or not isinstance(current[key], dict):
            current[key] = {}
        current = current[key]
    current[keys[-1]] = value
    return data
