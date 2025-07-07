"""
Docker context and host helper utilities for BuildX and multi-platform builds.

This module provides utilities for ensuring proper Docker context configuration
and host connectivity for multi-platform builds and BuildX operations.
"""

import logging
import os
import subprocess
from typing import Optional

logger = logging.getLogger(__name__)


def _ensure_docker_host(explicit: Optional[str] = None) -> None:
    """
    Ensure Docker host is properly configured for the build environment.

    This function configures the DOCKER_HOST environment variable based on
    explicit configuration or platform defaults. It's essential for ensuring
    proper connectivity to Docker daemon across different platforms.

    Args:
        explicit: Explicit Docker host to use, if provided
    """
    if explicit:
        # Use explicitly provided Docker host
        os.environ["DOCKER_HOST"] = explicit
        logger.debug(f"Set explicit Docker host: {explicit}")
        return

    # Check if DOCKER_HOST is already set
    current_host = os.environ.get("DOCKER_HOST")
    if current_host:
        logger.debug(f"Using existing Docker host: {current_host}")
        return

    # Platform-specific defaults
    import platform

    system = platform.system().lower()

    if system == "darwin":  # macOS
        # Check for Docker Desktop socket
        docker_desktop_socket = "/var/run/docker.sock"
        if os.path.exists(docker_desktop_socket):
            os.environ["DOCKER_HOST"] = f"unix://{docker_desktop_socket}"
            logger.debug(f"Set macOS Docker host: unix://{docker_desktop_socket}")
        else:
            logger.debug("Using default Docker host configuration for macOS")
    elif system == "linux":
        # Standard Linux Docker socket
        linux_socket = "/var/run/docker.sock"
        if os.path.exists(linux_socket):
            os.environ["DOCKER_HOST"] = f"unix://{linux_socket}"
            logger.debug(f"Set Linux Docker host: unix://{linux_socket}")
        else:
            logger.debug("Using default Docker host configuration for Linux")
    else:
        # Windows or other platforms - use defaults
        logger.debug(f"Using default Docker host configuration for {system}")


def ensure_builder_context(builder_name: str = "panther-builder") -> bool:
    """
    Ensure BuildX builder context is properly configured and accessible.

    This function ensures that the specified BuildX builder exists and is
    accessible from the current Docker context. It handles context switching
    and builder validation for multi-platform builds.

    Args:
        builder_name: Name of the BuildX builder to ensure

    Returns:
        bool: True if builder context is ready, False if setup failed
    """
    try:
        # Check current Docker context
        result = subprocess.run(
            ["docker", "context", "show"],
            capture_output=True,
            text=True,
            timeout=10,
        )

        if result.returncode == 0:
            current_context = result.stdout.strip()
            logger.debug(f"Current Docker context: {current_context}")

            # Test if the specific builder works with current context
            test_result = subprocess.run(
                ["docker", "buildx", "inspect", builder_name],
                capture_output=True,
                text=True,
                timeout=10,
            )

            if test_result.returncode == 0:
                logger.debug(
                    f"Builder '{builder_name}' is compatible with context '{current_context}'"
                )
                return True
            else:
                logger.warning(
                    f"Builder '{builder_name}' not compatible with context '{current_context}': {test_result.stderr}"
                )

                # Try to switch to default context and test again
                logger.info(
                    "Attempting to switch to default context for Buildx compatibility"
                )
                switch_result = subprocess.run(
                    ["docker", "context", "use", "default"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                )

                if switch_result.returncode == 0:
                    logger.info("Successfully switched to default context")

                    # Test builder again with default context
                    retest_result = subprocess.run(
                        ["docker", "buildx", "inspect", builder_name],
                        capture_output=True,
                        text=True,
                        timeout=10,
                    )

                    if retest_result.returncode == 0:
                        logger.info(
                            f"Builder '{builder_name}' is now compatible with default context"
                        )
                        return True
                    else:
                        logger.error(
                            f"Builder '{builder_name}' still not compatible with default context: {retest_result.stderr}"
                        )
                        return False
                else:
                    logger.error(
                        f"Failed to switch to default context: {switch_result.stderr}"
                    )
                    return False
        else:
            logger.warning(f"Failed to get current Docker context: {result.stderr}")
            return False

    except (
        subprocess.TimeoutExpired,
        subprocess.CalledProcessError,
        FileNotFoundError,
    ) as e:
        logger.warning(f"Error ensuring builder context: {e}")
        return False
