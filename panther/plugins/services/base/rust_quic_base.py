from typing import Any, Dict

"""Base class for Rust QUIC implementations (quiche, quinn)."""

from abc import abstractmethod
from typing import Any, Dict, List, Optional, Protocol

from .quic_service_base import BaseQUICServiceManager


class RustQUICServiceManager(BaseQUICServiceManager):
    """Provides common functionality for Rust implementations like quiche and quinn.
    that share similar command patterns and capabilities.
    """

    def generate_compile_command(self, **kwargs) -> str:
        """Generate Rust-specific compile command."""
        build_type = kwargs.get("build_type", "release")
        jobs = kwargs.get("jobs", "$(nproc)")

        if build_type.lower() == "debug":
            return f"cargo build --jobs {jobs}"
        else:
            return f"cargo build --release --jobs {jobs}"

    def _extract_common_params(self, **kwargs) -> Dict[str, Any]:
        """Extract Rust-specific common parameters."""
        params = super()._extract_common_params(**kwargs)

        # Rust implementations often use different log levels
        params["rust_log"] = kwargs.get("rust_log", "info")
        params["rust_backtrace"] = kwargs.get("rust_backtrace", "1")

        return params

    def _build_rust_env_vars(self, params: Dict[str, Any]) -> Dict[str, str]:
        """Build Rust-specific environment variables."""
        return {
            "RUST_LOG": params.get("rust_log", "info"),
            "RUST_BACKTRACE": params.get("rust_backtrace", "1"),
        }

    def get_supported_features(self) -> Dict[str, bool]:
        """Get common Rust QUIC features."""
        features = super().get_supported_features()
        # Most Rust implementations have good modern QUIC support
        features.update(
            {
                "memory_safety": True,
                "async": True,
                "tokio": True,
                "performance": True,
            }
        )
        return features

    @abstractmethod
    def _get_cargo_bin_name(self) -> str:
        """Get the cargo binary name for this implementation."""
        pass

    def _get_binary_name(self) -> str:
        """Use cargo binary name by default."""
        return self._get_cargo_bin_name()
