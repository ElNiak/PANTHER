"""Docker Tag Generator - Image tag generation and sanitization.

Provides ``DockerTagGenerator`` for generating deterministic, Docker-compliant
image tags from build parameters (implementation name, version, build mode,
runtime mode, platform, z3 source).

Tag format::

    {impl_name}-{version}:{tag_version}[-{build_mode}][-{runtime_mode}][-z3{z3_source}][-{platform}]

Examples:
    - ``picoquic-v1.0:latest``
    - ``picoquic-v1.0:latest-debug-asan-debug-linux-amd64``
    - ``panther_ivy-rfc9000:latest-z3pip-linux-amd64``
"""

import logging
import re

logger = logging.getLogger(__name__)

MAX_TAG_LENGTH = 100  # Maximum Docker tag length (leave room for registry prefix)


def generate_image_tag(
    impl_name: str,
    version: str,
    tag_version: str,
    build_mode: str = "",
    runtime_mode: str = "minimal",
    target_platform: str = "",
    z3_source: str = "",
) -> str:
    """Generate Docker image tag with build and runtime mode differentiation.

    Args:
        impl_name: Implementation name (e.g., 'picoquic')
        version: Version string (e.g., 'v1.0' or 'latest')
        tag_version: Tag version (e.g., 'latest', 'stable')
        build_mode: Build mode ('', 'debug-asan', 'rel-lto', 'release-static-pgo')
        runtime_mode: Runtime mode ('minimal', 'debug', 'profile')
        target_platform: Target platform (e.g., 'linux/amd64', 'linux/arm64')
        z3_source: Z3 build source ('', 'local', 'pip'). Default 'local' produces no suffix.

    Returns:
        str: Complete sanitized image tag
    """
    # Build mode suffix (empty string results in no suffix)
    build_suffix = f"-{build_mode}" if build_mode else ""

    # Runtime mode suffix (minimal is default, so no suffix needed)
    runtime_suffix = (
        f"-{runtime_mode}" if runtime_mode and runtime_mode != "minimal" else ""
    )

    # Z3 source suffix (local is default, so no suffix needed)
    z3_suffix = f"-z3{z3_source}" if z3_source and z3_source != "local" else ""

    platform_suffix = f"-{target_platform}" if target_platform else ""

    # Construct base name with version
    base_name = f"{impl_name}-{version}" if version else impl_name
    # Combine all parts
    full_tag = f"{base_name}:{tag_version}{build_suffix}{runtime_suffix}{z3_suffix}{platform_suffix}"

    # Sanitize tag (Docker tags have character restrictions)
    return sanitize_docker_tag(full_tag)


def sanitize_docker_tag(tag: str) -> str:
    """Sanitize Docker tag to meet Docker naming requirements.

    Docker tag rules:
    - Lowercase letters, digits, underscores, periods, dashes
    - Cannot start with period or dash
    - Max ``MAX_TAG_LENGTH`` characters

    Args:
        tag: Raw tag string to sanitize

    Returns:
        Sanitized tag string
    """
    # Convert to lowercase and replace invalid characters (allow colon for tag separator)
    sanitized = re.sub(r"[^a-z0-9._:-]", "-", tag.lower())

    # Ensure doesn't start with period or dash
    sanitized = re.sub(r"^[.-]+", "", sanitized)

    if not sanitized:
        logger.warning(
            "Docker tag '%s' became empty after sanitization, using 'unknown'",
            tag,
        )
        sanitized = "unknown"

    # Truncate if too long (leave room for registry prefix)
    if len(sanitized) > MAX_TAG_LENGTH:
        # Keep the tag version part intact
        parts = sanitized.split(":")
        if len(parts) == 2:
            name_part, tag_part = parts
            max_name_length = MAX_TAG_LENGTH - len(tag_part) - 1  # -1 for ':'
            if len(name_part) > max_name_length:
                name_part = name_part[:max_name_length]
            sanitized = f"{name_part}:{tag_part}"
        else:
            sanitized = sanitized[:MAX_TAG_LENGTH]

    return sanitized
