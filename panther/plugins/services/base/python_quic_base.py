"""Base class for Python QUIC implementations (aioquic)."""

from abc import abstractmethod
from typing import Any, Dict, List, Optional, Protocol

from .quic_service_base import BaseQUICServiceManager


class PythonQUICServiceManager(BaseQUICServiceManager):
    """Provides common functionality for Python implementations like aioquic.

    that use Python modules and async patterns.
    """

    def generate_compile_command(self, **kwargs) -> str:
        """Python implementations typically don't need compilation."""
        # Install dependencies if requirements.txt exists
        return "[ -f requirements.txt ] && pip install -r requirements.txt || true"

    def _extract_common_params(self, **kwargs) -> Dict[str, Any]:
        """Extract Python-specific common parameters."""
        params = super()._extract_common_params(**kwargs)

        # Python-specific settings
        params["python_path"] = kwargs.get("python_path", "/opt/aioquic")
        params["asyncio_debug"] = kwargs.get("asyncio_debug", False)

        return params

    def _build_python_env_vars(self, params: Dict[str, Any]) -> Dict[str, str]:
        """Build Python-specific environment variables."""
        env_vars = {
            "PYTHONPATH": params.get("python_path", "/opt/aioquic"),
            "PYTHONUNBUFFERED": "1",
        }

        if params.get("asyncio_debug"):
            env_vars["PYTHONASYNCIODEBUG"] = "1"

        return env_vars

    def get_supported_features(self) -> Dict[str, bool]:
        """Get common Python QUIC features."""
        features = super().get_supported_features()
        # Python implementations have good async support
        features.update(
            {
                "async": True,
                "asyncio": True,
                "python": True,
                "interpreted": True,
            }
        )
        return features

    @abstractmethod
    def _get_python_module(self) -> str:
        """Get the Python module to execute."""
        pass

    def _get_binary_name(self) -> str:
        """Use python -m module syntax by default."""
        return f"python -m {self._get_python_module()}"
