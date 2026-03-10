"""Service layer for experiment execution from the web UI."""

import asyncio
import logging
from typing import Callable, Optional

from panther.core.events.base.event_base import BaseEvent
from panther.webapp.services.web_observer import WebObserver

logger = logging.getLogger(__name__)


class _StopRequested(Exception):
    """Raised internally when the user clicks Stop."""

    pass


class ExperimentService:
    """Wraps ExperimentManager for async web usage.

    Runs experiments in a background thread (via asyncio.to_thread) to avoid
    blocking the NiceGUI event loop.

    Maintains an in-memory log buffer and status so state survives page
    navigation (singleton instance persists for the lifetime of the process).
    """

    def __init__(self):
        """Initialize ExperimentService."""
        self._running = False
        self._stop_requested = False
        self._log_lines: list[str] = []
        self._max_log_lines: int = 10000
        self._status: str = "Idle"
        self._config_path: str = ""
        self._log_callbacks: list[Callable[[str], None]] = []
        self._status_callbacks: list[Callable[[str], None]] = []
        self._web_observer = WebObserver()

    @property
    def status(self) -> str:
        """Current execution status."""
        return self._status

    @property
    def log_lines(self) -> list[str]:
        """Snapshot of collected log lines."""
        return list(self._log_lines)

    @property
    def config_path(self) -> str:
        """Path to the loaded experiment config."""
        return self._config_path

    def register_callbacks(
        self,
        on_log: Callable[[str], None],
        on_status: Callable[[str], None],
    ):
        """Register UI callbacks for live log/status streaming."""
        self._log_callbacks.append(on_log)
        self._status_callbacks.append(on_status)

    def unregister_callbacks(
        self,
        on_log: Callable[[str], None],
        on_status: Callable[[str], None],
    ):
        """Unregister UI callbacks (call on page disconnect)."""
        try:
            self._log_callbacks.remove(on_log)
        except ValueError:
            pass
        try:
            self._status_callbacks.remove(on_status)
        except ValueError:
            pass

    def _emit_log(self, line: str):
        self._log_lines.append(line)
        if len(self._log_lines) > self._max_log_lines:
            self._log_lines = self._log_lines[-self._max_log_lines :]
        for cb in list(self._log_callbacks):
            try:
                cb(line)
            except Exception:
                pass

    def _emit_status(self, s: str):
        self._status = s
        for cb in list(self._status_callbacks):
            try:
                cb(s)
            except Exception:
                pass

    async def run_experiment(
        self,
        config_path: str,
    ):
        """Run a PANTHER experiment in a background thread.

        Args:
            config_path: Path to the experiment config YAML.
        """
        if self._running:
            raise RuntimeError("An experiment is already running")

        self._running = True
        self._stop_requested = False
        self._log_lines.clear()
        self._config_path = config_path

        def _run():
            def _check_stop():
                if self._stop_requested:
                    raise _StopRequested()

            try:
                import yaml as _yaml

                from panther.config import GlobalConfig, load_experiment
                from panther.core.experiment_manager import ExperimentManager

                self._emit_status("Loading config...")

                # 1. Load experiment config (tests, services, protocols)
                experiment_config = load_experiment(
                    config_path, validate=True, auto_fix=True
                )

                # 2. Load raw YAML for global settings
                with open(config_path) as f:
                    config_dict = _yaml.safe_load(f)
                if not isinstance(config_dict, dict):
                    config_dict = {}

                # 3. Build GlobalConfig from YAML sections (matching CLI pattern)
                global_config = GlobalConfig(
                    logging=config_dict.get("logging", {}),
                    paths=config_dict.get("paths", {}),
                    docker=config_dict.get("docker", {}),
                    progress=config_dict.get("progress", None),
                    observers=config_dict.get("observers", None),
                )

                _check_stop()

                self._emit_status("Initializing...")
                self._emit_log(f"Loaded config from {config_path}")

                from panther.core.observer.management.event_manager import (
                    get_event_manager,
                )

                # 4. Use context manager for proper cleanup
                with ExperimentManager(
                    global_config=global_config,
                    experiment_name=config_dict.get("name", "web_experiment"),
                ) as manager:
                    # Register web observer with EventManager as global observer
                    event_manager = get_event_manager()
                    event_manager.register_observer(self._web_observer)
                    self._web_observer.subscribe(self._on_event)

                    try:
                        # 5. Initialize experiments (populates test_cases!)
                        manager.initialize_experiments(experiment_config)

                        _check_stop()

                        self._emit_status("Running tests...")
                        success = manager.run_tests()

                        _check_stop()
                    finally:
                        event_manager.unregister_observer(self._web_observer)
                        self._web_observer.unsubscribe(self._on_event)

                status = "Completed" if success else "Failed"
                self._emit_status(status)
                self._emit_log(f"Experiment {'succeeded' if success else 'failed'}")

            except _StopRequested:
                self._emit_log("Experiment stopped by user")
                self._emit_status("Stopped")
            except Exception as e:
                logger.error("Experiment error: %s", e, exc_info=True)
                self._emit_log(f"ERROR: {e}")
                self._emit_status(f"Error: {e}")
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

    def _on_event(self, event: BaseEvent):
        """Bridge PANTHER events to existing log/status callbacks."""
        event_type = event.get_type()
        self._emit_log(f"[{event_type}] {event}")

        # Map lifecycle events to status updates
        if event_type == "experiment.started":
            self._emit_status("Running")
        elif event_type == "experiment.completed":
            self._emit_status("Completed")
        elif event_type == "experiment.failed":
            self._emit_status("Failed")

    def subscribe_events(self, callback: Callable[[BaseEvent], None]):
        """Subscribe to raw PANTHER events via the web observer."""
        self._web_observer.subscribe(callback)

    def unsubscribe_events(self, callback: Callable[[BaseEvent], None]):
        """Unsubscribe from raw PANTHER events."""
        self._web_observer.unsubscribe(callback)

    @property
    def web_observer(self) -> WebObserver:
        """Return the WebObserver instance."""
        return self._web_observer

    @property
    def is_running(self) -> bool:
        """Return whether an experiment is currently running."""
        return self._running


_instance: Optional[ExperimentService] = None


def get_experiment_service() -> ExperimentService:
    """Return the module-level singleton ExperimentService."""
    global _instance
    if _instance is None:
        _instance = ExperimentService()
    return _instance
