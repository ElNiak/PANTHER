"""CLI override extraction utility.

Replaces the manual if-statement chain in ``panther/cli/commands/run.py``
with a declarative mapping from Click parameter names to config dot-paths.
"""

from typing import Any, Dict

import click
from click.core import ParameterSource

# Declarative mapping: Click param name -> config dot-notation path.
# To add a new CLI override, just add an entry here.
CLI_CONFIG_MAP: Dict[str, str] = {
    "force_build": "docker.force_build_docker_image",
    "no_docker_cache": "docker.no_docker_cache",
    "enable_metrics": "observers.metrics.enabled",
    "output_dir": "paths.output_dir",
}

# Params that, when set, also force-set other params.
_IMPLIES: Dict[str, Dict[str, Any]] = {
    "no_docker_cache": {"docker.force_build_docker_image": True},
}


def extract_cli_overrides(
    ctx: click.Context, mapping: Dict[str, str] | None = None
) -> Dict[str, Any]:
    """Extract CLI-provided overrides as config dot-notation dict.

    Only includes parameters explicitly passed on the command line
    (``ParameterSource.COMMANDLINE``), not defaults.

    Args:
        ctx: Click invocation context.
        mapping: Override mapping (defaults to ``CLI_CONFIG_MAP``).

    Returns:
        Dict of ``{config_dot_path: value}`` for CLI-provided params.
    """
    if mapping is None:
        mapping = CLI_CONFIG_MAP

    overrides: Dict[str, Any] = {}
    explicit: Dict[str, Any] = {}
    for param_name, dot_path in mapping.items():
        if param_name not in ctx.params:
            continue
        if ctx.get_parameter_source(param_name) == ParameterSource.COMMANDLINE:
            explicit[dot_path] = ctx.params[param_name]
            # Collect implied overrides
            if param_name in _IMPLIES:
                overrides.update(_IMPLIES[param_name])
    # Explicit CLI values always win over implications
    overrides.update(explicit)

    return overrides
