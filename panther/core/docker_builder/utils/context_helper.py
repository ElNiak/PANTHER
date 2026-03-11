"""Docker context and host helper utilities.

This module provides utilities for ensuring proper Docker host connectivity.
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
from typing import Optional

logger = logging.getLogger(__name__)


def _ensure_docker_host(explicit: Optional[str] = None) -> None:
    """Guarantee DOCKER_HOST is set *before* docker.from_env() is called.

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
