"""
Purpose: Detect and reconcile Docker CLI context vs. buildx builder context
to prevent the “use `docker --context=default buildx`” error on Apple Silicon
and other multi-context hosts.
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
from pathlib import Path
from typing import Literal, Optional, Tuple

DockerContext = str
Strategy = Literal["switch-cli-context", "recreate-builder"]


def _ensure_docker_host(explicit: Optional[str] = None) -> None:
    """
    Guarantee DOCKER_HOST is set *before* docker.from_env() is called.

    Order of precedence:
    1. explicit override (arg or global_config).
    2. already-exported value.
    3. value from current `docker context inspect` JSON.
    4. fallback '/var/run/docker.sock'.
    """
    if explicit:  # via config
        os.environ["DOCKER_HOST"] = explicit
        return

    if os.environ.get("DOCKER_HOST"):
        return  # user already set it

    try:
        ctx = subprocess.run(
            ["docker", "context", "inspect", "--format", "{{json .}}"],
            check=True,
            text=True,
            capture_output=True,
        ).stdout
        host = json.loads(ctx)["Endpoints"]["docker"]["Host"]
        if host:
            os.environ["DOCKER_HOST"] = host
            return
    except Exception as err:  # non-fatal: fall back
        logging.getLogger(__name__).debug("Could not auto-detect DOCKER_HOST: %s", err)

    # Final fallback (Unix default)
    os.environ.setdefault("DOCKER_HOST", "unix:///var/run/docker.sock")


def _run(*args: str) -> str:
    """Run a Docker CLI command and return stripped stdout; raise on failure."""
    proc = subprocess.run(
        args,
        check=True,
        capture_output=True,
        text=True,
    )
    return proc.stdout.strip()


def _current_cli_context() -> DockerContext:
    return _run("docker", "context", "show")


def _builder_context(builder: str) -> DockerContext:
    return _run(
        "docker",
        "buildx",
        "inspect",
        builder,
        "--format",
        "{.Context}",
    )


def _switch_cli_context(target: DockerContext) -> None:
    _run("docker", "context", "use", target)


def _recreate_builder(builder: str) -> None:
    # Destroy & recreate with same name in *current* context
    _run("docker", "buildx", "rm", builder)
    _run("docker", "buildx", "create", "--name", builder, "--use")


def ensure_builder_context(
    builder: str = "default",
    strategy: Strategy = "switch-cli-context",
) -> Tuple[DockerContext, DockerContext]:
    """
    Ensure `builder` was created in the same Docker context as the CLI.

    Returns (cli_ctx, builder_ctx). Raises subprocess.CalledProcessError
    on underlying Docker errors.
    """

    cli_ctx = _current_cli_context()
    builder_ctx = _builder_context(builder)

    if cli_ctx == builder_ctx:
        return cli_ctx, builder_ctx  # All good.

    if strategy == "switch-cli-context":
        _switch_cli_context(builder_ctx)
    elif strategy == "recreate-builder":
        _recreate_builder(builder)
    else:
        raise ValueError(f"Unknown strategy: {strategy}")

    return _current_cli_context(), _builder_context(builder)
