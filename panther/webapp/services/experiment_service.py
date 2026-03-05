"""Service layer for experiment execution from the web UI."""

import asyncio
import logging
from typing import Callable, Optional

logger = logging.getLogger(__name__)


class ExperimentService:
    """Wraps ExperimentManager for async web usage.

    Runs experiments in a background thread (via asyncio.to_thread) to avoid
    blocking the NiceGUI event loop.
    """

    def __init__(self):
        """Initialize ExperimentService."""
        self._running = False
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

        def _run():
            try:
                if on_status:
                    on_status("Loading config...")

                # Load config through PANTHER's config system
                from omegaconf import OmegaConf

                from panther.config.core.models import GlobalConfig
                from panther.core.experiment_manager import ExperimentManager

                raw = OmegaConf.load(config_path)
                config_dict = OmegaConf.to_container(raw, resolve=True)

                # Build GlobalConfig from the logging/docker/paths sections
                global_config = GlobalConfig(**config_dict.get("global", {}))

                if on_status:
                    on_status("Initializing...")
                if on_log:
                    on_log(f"Loaded config from {config_path}")

                # ExperimentManager.__init__ signature:
                #   global_config, experiment_name, plugin_dir, logger,
                #   metrics_collector, fast_fail_enabled, dry_run
                manager = ExperimentManager(
                    global_config=global_config,
                    experiment_name=config_dict.get("name", "web_experiment"),
                )

                if on_status:
                    on_status("Running tests...")

                success = manager.run_tests()

                status = "Completed" if success else "Failed"
                if on_status:
                    on_status(status)
                if on_log:
                    on_log(f"Experiment {'succeeded' if success else 'failed'}")

            except Exception as e:
                logger.error("Experiment error: %s", e, exc_info=True)
                if on_log:
                    on_log(f"ERROR: {e}")
                if on_status:
                    on_status(f"Error: {e}")
            finally:
                self._running = False

        try:
            await asyncio.to_thread(_run)
        except Exception:
            self._running = False
            raise

    def stop(self):
        """Request experiment stop."""
        self._stop_requested = True
        logger.info("Experiment stop requested")

    @property
    def is_running(self) -> bool:
        """Return whether an experiment is currently running."""
        return self._running
