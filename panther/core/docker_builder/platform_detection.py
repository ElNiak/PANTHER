"""Platform detection and architecture validation for Docker builds.

Provides the PlatformDetectionMixin with methods for detecting host/target
platforms, checking BuildKit requirements, and validating build modes.
"""

import platform
import re
import subprocess
from pathlib import Path
from typing import Optional


class PlatformDetectionMixin:
    """Mixin providing platform detection and architecture validation.

    Expects the host class to provide:
        - self.logger
        - self.global_config (optional)
        - self._cached_host_platform: Optional[str]
        - self._cached_target_platform: Optional[str]
        - self._cached_buildx_available: Optional[bool]
        - self._platform_detection_logged: bool
        - self.image_cache
    """

    def get_target_platform(self) -> str:
        """Detect the appropriate Docker platform based on the current architecture.

        Respects the target_platform configuration override if specified.
        Results are cached per singleton lifetime; cache is invalidated when
        global_config changes via update_parameters().

        Returns:
            str: Docker platform string (e.g., 'linux/amd64', 'linux/arm64')
        """
        if self._cached_target_platform is not None:
            return self._cached_target_platform

        # Check for configuration override first
        if (
            hasattr(self, "global_config")
            and self.global_config
            and hasattr(self.global_config, "docker")
            and self.global_config.docker.target_platform
        ):
            target_platform = self.global_config.docker.target_platform
            self.logger.debug(
                "Using configured target platform override: %s", target_platform
            )
            self._cached_target_platform = target_platform
            return target_platform

        # Detect host architecture and map to appropriate Docker platform
        machine = platform.machine().lower()
        if machine in ["arm64", "aarch64"]:
            if not self._check_buildx_available():
                if not self._platform_detection_logged:
                    self.logger.warning(
                        "ARM64 architecture detected but Docker Buildx is not available. "
                        "Cross-platform builds may fail without Buildx support. "
                        "Set use_buildx: true to enable buildx for ARM64 builds."
                    )
                    self.logger.warning(
                        "Detected ARM64 architecture '%s' -> using native platform: %s BUT expected errors may occur due to lack of support in some tools (picoTLS, z3, ivy) - set target_platform override if you want to force a different platform",
                        machine,
                        "linux/arm64",
                    )
                    self._platform_detection_logged = True
                docker_platform = "linux/arm64"
            else:
                if not self._platform_detection_logged:
                    self.logger.info(
                        "ARM64 architecture detected with Buildx available -> using linux/amd64 for cross-platform builds"
                    )
                    self._platform_detection_logged = True
                docker_platform = "linux/amd64"
        elif machine in ["x86_64", "amd64"]:
            docker_platform = "linux/amd64"
        else:
            # Default to amd64 for unknown architectures
            docker_platform = "linux/amd64"
            self.logger.warning(
                "Unknown architecture '%s', defaulting to %s", machine, docker_platform
            )

        self.logger.debug(
            "Detected host architecture: %s -> Docker platform: %s",
            machine,
            docker_platform,
        )

        self._cached_target_platform = docker_platform
        return docker_platform

    def _check_buildx_available(self) -> bool:
        """Check if Docker Buildx is available on the system.

        Results are cached per singleton lifetime to avoid repeated subprocess calls.

        Returns:
            bool: True if buildx is available, False otherwise
        """
        if self._cached_buildx_available is not None:
            return self._cached_buildx_available

        try:
            result = subprocess.run(
                ["docker", "buildx", "version"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                self.logger.debug(
                    "Docker Buildx is available: %s", result.stdout.strip()
                )
                self._cached_buildx_available = True
            else:
                self.logger.warning("Docker Buildx not available: %s", result.stderr)
                self._cached_buildx_available = False
        except (
            subprocess.TimeoutExpired,
            subprocess.CalledProcessError,
            FileNotFoundError,
        ) as e:
            self.logger.warning("Failed to check Docker Buildx availability: %s", e)
            self._cached_buildx_available = False

        return self._cached_buildx_available

    def _get_host_platform(self) -> str:
        """Get the host platform without configuration overrides.

        Results are cached per singleton lifetime since host platform never changes.

        Returns:
            str: Host platform string (e.g., 'linux/amd64', 'linux/arm64')
        """
        if self._cached_host_platform is not None:
            return self._cached_host_platform
        machine = platform.machine().lower()
        self._cached_host_platform = (
            "linux/arm64" if machine in ["arm64", "aarch64"] else "linux/amd64"
        )
        return self._cached_host_platform

    def get_effective_build_platform(self) -> str:
        """Get the platform that will actually be built.

        When buildx is enabled, cross-platform builds are possible, so return target platform.
        When buildx is disabled, standard Docker builds for native platform only,
        so return host platform regardless of target platform setting.

        Returns:
            str: Effective build platform (e.g., 'linux/amd64', 'linux/arm64')
        """
        if self._should_use_buildx():
            # Buildx enabled - can cross-compile, use target platform
            return self.get_target_platform()
        else:
            # Buildx disabled - standard Docker builds for native platform only
            host_platform = self._get_host_platform()
            target_platform = self.get_target_platform()
            if host_platform != target_platform:
                self.logger.warning(
                    "Buildx disabled: building for native platform %s instead of target %s. "
                    "Set use_buildx: true to enable cross-platform builds.",
                    host_platform,
                    target_platform,
                )
            return host_platform

    def _dockerfile_requires_buildkit(self, dockerfile_path: Path) -> bool:
        """Check if Dockerfile contains BuildKit-specific features.

        Analyzes Dockerfile content to detect syntax that requires BuildKit/BuildX:
        - RUN --mount (cache mounts, bind mounts, secret mounts)
        - RUN --network (network access control)
        - RUN --security (security sandbox control)
        - COPY --link (independent layer copying)
        - ARG with BUILDPLATFORM, TARGETPLATFORM (automatic platform args)

        Args:
            dockerfile_path: Path to the Dockerfile to analyze

        Returns:
            bool: True if BuildKit features detected, False otherwise
        """
        try:
            if not dockerfile_path.exists():
                self.logger.warning(f"Dockerfile not found: {dockerfile_path}")
                return False

            with open(dockerfile_path, "r", encoding="utf-8") as f:
                content = f.read()

            # BuildKit-specific patterns that require BuildX
            buildkit_patterns = [
                r"RUN\s+--mount\s*=",  # RUN --mount=type=cache,target=...
                r"RUN\s+--network\s*=",  # RUN --network=none
                r"RUN\s+--security\s*=",  # RUN --security=insecure
                r"COPY\s+--link\s+",  # COPY --link
                r"RUN.*--mount.*type\s*=",  # Various mount types
            ]

            for pattern in buildkit_patterns:
                if re.search(pattern, content, re.IGNORECASE | re.MULTILINE):
                    self.logger.debug(
                        f"BuildKit feature detected in {dockerfile_path}: pattern '{pattern}'"
                    )
                    return True

            # Check for BuildKit automatic platform arguments usage
            # These work best with BuildX which provides them automatically
            platform_args = [
                "BUILDPLATFORM",
                "TARGETPLATFORM",
                "TARGETOS",
                "TARGETARCH",
                "BUILDOS",
                "BUILDARCH",
            ]
            for arg in platform_args:
                # Look for ARG declarations or variable usage
                if re.search(
                    rf"ARG\s+{arg}|{{{arg}}}|\${{{arg}}}", content, re.IGNORECASE
                ):
                    self.logger.debug(
                        f"BuildKit platform argument detected in {dockerfile_path}: {arg}"
                    )
                    return True

            self.logger.debug(f"No BuildKit features detected in {dockerfile_path}")
            return False

        except (OSError, UnicodeDecodeError) as e:
            self.logger.error(f"Error reading Dockerfile {dockerfile_path}: {e}")
            # If we can't read the file, assume it MAY need BuildKit (safer fallback)
            return True

    def validate_build_mode_for_architecture(self, build_mode: str) -> str:
        """Validate BUILD_MODE compatibility with host architecture.

        Advanced build modes (rel-lto, debug-asan, release-static-pgo) require x86 architecture.
        Non-x86 architectures fall back to empty BUILD_MODE for compatibility.

        Args:
            build_mode: The requested build mode

        Returns:
            str: Validated build mode (empty string if incompatible with architecture)
        """
        if not build_mode:
            return build_mode

        self.logger.debug(
            "Validating BUILD_MODE='%s' for current architecture '%s'",
            build_mode,
            platform.machine(),
        )

        # Check if we're on x86 architecture
        machine = platform.machine().lower()
        is_x86 = machine in ["x86_64", "amd64", "x86", "i386", "i686"]

        advanced_modes = ["rel-lto", "debug-asan", "release-static-pgo"]

        if build_mode in advanced_modes and not is_x86:
            self.logger.warning(
                "BUILD_MODE='%s' requires x86 architecture but detected '%s'. "
                "Falling back to default build mode for compatibility.",
                build_mode,
                machine,
            )
            return ""  # Fall back to default/legacy build

        return build_mode

    def _get_cache_key_suffix(self) -> str:
        """Generate cache key suffix based on target platform for cache isolation.

        Returns:
            str: Cache key suffix (e.g., '-linux-amd64', '-linux-arm64')
        """
        platform_str = self.get_target_platform().replace("/", "-")
        return f"-{platform_str}"

    def _update_cache_platform(self) -> None:
        """Update image cache platform when target platform changes."""
        current_platform = self.get_target_platform()

        if hasattr(self.image_cache, "target_platform"):
            if self.image_cache.target_platform != current_platform:
                self.image_cache.set_target_platform(current_platform)
                self.logger.debug(
                    f"Updated image cache platform to: {current_platform}"
                )
        else:
            # Fallback for older cache instances
            self.logger.warning("Image cache does not support platform switching")
