"""Service layer for experiment execution from the web UI."""

import asyncio
import logging
import threading
from typing import Callable, Optional

logger = logging.getLogger(__name__)


class ExperimentService:
    """Wraps ExperimentManager for async web usage.

    Runs experiments in a background thread to avoid blocking the NiceGUI event loop.
    """

    def __init__(self):
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._stop_requested = False

    async def run_experiment(
        self,
        config_path: str,
        on_log: Optional[Callable[[str], None]] = None,
        on_status: Optional[Callable[[str], None]] = None,
    ):
        """Run a PANTHER experiment in a background thread.

        Args:
            config_path: Path to the experiment config YAML.
            on_log: Callback for log line updates.
            on_status: Callback for status updates.
        """
        if self._running:
            raise RuntimeError("An experiment is already running")

        self._running = True
        self._stop_requested = False
        loop = asyncio.get_event_loop()

        def _run():
            try:
                if on_status:
                    loop.call_soon_threadsafe(on_status, "Loading config...")

                # Load config through PANTHER's config system
                from omegaconf import OmegaConf

                from panther.config.core.models import GlobalConfig
                from panther.core.experiment_manager import ExperimentManager

                raw = OmegaConf.load(config_path)
                config_dict = OmegaConf.to_container(raw, resolve=True)

                # Extract global config
                global_config = GlobalConfig(**config_dict.get("global", {}))

                if on_status:
                    loop.call_soon_threadsafe(on_status, "Initializing...")
                if on_log:
                    loop.call_soon_threadsafe(
                        on_log, f"Loaded config from {config_path}"
                    )

                manager = ExperimentManager(
                    global_config=global_config,
                    experiment_name=config_dict.get("name", "web_experiment"),
                )

                if on_status:
                    loop.call_soon_threadsafe(on_status, "Running tests...")

                success = manager.run_tests()

                if on_status:
                    status = "Completed" if success else "Failed"
                    loop.call_soon_threadsafe(on_status, status)
                if on_log:
                    loop.call_soon_threadsafe(
                        on_log, f"Experiment {'succeeded' if success else 'failed'}"
                    )

            except Exception as e:
                logger.error("Experiment error: %s", e, exc_info=True)
                if on_log:
                    loop.call_soon_threadsafe(on_log, f"ERROR: {e}")
                if on_status:
                    loop.call_soon_threadsafe(on_status, f"Error: {e}")
            finally:
                self._running = False

        self._thread = threading.Thread(target=_run, daemon=True)
        self._thread.start()

        # Wait for thread to finish (non-blocking via asyncio)
        while self._thread.is_alive():
            await asyncio.sleep(0.5)

    def stop(self):
        """Request experiment stop. Note: actual cancellation depends on
        ExperimentManager supporting interruption."""
        self._stop_requested = True
        logger.info("Experiment stop requested")

    @property
    def is_running(self) -> bool:
        return self._running
