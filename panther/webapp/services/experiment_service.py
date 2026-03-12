"""ExperimentService -- experiment lifecycle management for the web UI.

This module bridges the gap between PANTHER's synchronous, blocking
ExperimentManager (PANTHER's central orchestrator that drives the
four-phase execution model: initialization, plugin loading, environment
deployment, and test execution) and the asynchronous NiceGUI event loop
that powers the web interface.

The core challenge is that experiment execution is CPU- and I/O-bound work
that can run for minutes (or longer when Docker builds are involved), while
NiceGUI requires the main asyncio event loop to remain responsive for UI
updates.  ExperimentService solves this by running the experiment in a
background thread via ``asyncio.to_thread`` and streaming status updates
and log lines back to the UI through registered callbacks.

Threading model:
    - The NiceGUI event loop runs on the **main thread**.
    - ``run_experiment`` is an ``async`` method called from the main thread;
      it offloads the actual work to a **background thread**.
    - Callbacks (``on_log``, ``on_status``) are invoked from the background
      thread.  UI components that receive these callbacks must handle
      cross-thread safety (e.g. via ``ui.notify`` or NiceGUI's built-in
      client-context wrappers).
    - A ``threading.Lock`` guards the ``_running`` flag to prevent concurrent
      experiment launches.

State management:
    A module-level singleton (accessed via ``get_experiment_service()``)
    persists in-memory log lines and status across page navigations within
    the same server process.  WebObserver GUI state can optionally be
    persisted to NiceGUI's ``app.storage.general`` between runs.
"""

import asyncio
import logging
import threading
from collections import deque
from typing import Callable, Optional

from panther.core.events.base.event_base import BaseEvent
from panther.webapp.infra.web_observer import WebObserver

logger = logging.getLogger(__name__)


class _StopRequested(Exception):
    """Sentinel exception raised in the background thread when the user requests a stop.

    This is caught inside ``ExperimentService._run`` to cleanly abort the
    experiment without propagating to the caller.
    """

    pass


class ExperimentService:
    """Async wrapper around ExperimentManager for use in the NiceGUI web interface.

    Wraps ExperimentManager (PANTHER's central orchestrator) to manage the
    full lifecycle of an experiment run from the web
    UI's perspective: loading the YAML config, instantiating the
    ExperimentManager, running tests in a background thread, streaming log
    lines and status updates to registered UI callbacks, and handling
    user-initiated stops.

    The singleton pattern is enforced by the module-level factory function
    ``get_experiment_service()``.  Because only one instance exists per
    server process, its in-memory log buffer and status string survive
    page navigations -- a user who leaves and returns to the experiment
    page will see the accumulated output.

    Threading model:
        - ``run_experiment`` is ``async`` but delegates blocking work to a
          background thread via ``asyncio.to_thread``.
        - ``_emit_log`` and ``_emit_status`` are called from the background
          thread; registered callbacks must be thread-safe.
        - ``_lock`` (a ``threading.Lock``) serialises access to ``_running``
          and ``_stop_requested`` flags.

    Attributes:
        status: Current human-readable execution status (e.g. ``"Idle"``,
            ``"Running tests..."``, ``"Completed"``).
        log_lines: Snapshot list of collected log line strings.
        config_path: Filesystem path of the currently loaded experiment
            config YAML.
        is_running: Whether an experiment is currently executing.
        web_observer: The ``WebObserver`` instance used for event bridging.

    Example::

        svc = get_experiment_service()
        svc.register_callbacks(on_log=print, on_status=print)
        await svc.run_experiment("experiment-config/base/my_config.yaml")
    """

    def __init__(self):
        """Initialise internal state and create the WebObserver."""
        self._lock = threading.Lock()
        self._running = False
        self._stop_requested = False
        self._log_lines: deque[str] = deque(maxlen=10000)
        self._max_log_lines: int = 10000
        self._status: str = "Idle"
        self._config_path: str = ""
        self._log_callbacks: list[Callable[[str], None]] = []
        self._status_callbacks: list[Callable[[str], None]] = []
        self._web_observer = WebObserver()
        self._batch_timer: Optional[object] = None  # ui.timer handle

        # Restore observer state from NiceGUI app storage if available
        self._try_restore_observer_state()
        logger.debug("ExperimentService initialized")

    @property
    def status(self) -> str:
        """Current human-readable execution status string.

        Typical values: ``"Idle"``, ``"Loading config..."``,
        ``"Initializing..."``, ``"Running tests..."``, ``"Completed"``,
        ``"Failed"``, ``"Stopped"``, or ``"Error: <message>"``.
        """
        return self._status

    @property
    def log_lines(self) -> list[str]:
        """Return a shallow copy of the accumulated log-line buffer.

        The buffer is capped at ``_max_log_lines`` (default 10 000); older
        entries are evicted in FIFO order.
        """
        return list(self._log_lines)

    @property
    def config_path(self) -> str:
        """Filesystem path to the YAML config used by the current (or last) run."""
        return self._config_path

    def register_callbacks(
        self,
        on_log: Callable[[str], None],
        on_status: Callable[[str], None],
    ):
        """Register a pair of UI callbacks for live log and status streaming.

        Callbacks are invoked from the **background thread** that runs the
        experiment.  If the callback updates NiceGUI UI elements, it must
        be wrapped with the appropriate client-context guard (e.g.
        ``client.connected``).

        Multiple callback pairs may be registered (e.g. one per connected
        browser tab).

        Args:
            on_log: Called with each new log line string.
            on_status: Called with the new status string whenever the
                execution phase changes.
        """
        self._log_callbacks.append(on_log)
        self._status_callbacks.append(on_status)
        logger.debug("Registered UI callbacks")

    def unregister_callbacks(
        self,
        on_log: Callable[[str], None],
        on_status: Callable[[str], None],
    ):
        """Remove a previously registered callback pair.

        Should be called when a browser tab disconnects to avoid leaking
        references.  Silently ignores callbacks that are not currently
        registered.

        Args:
            on_log: The log callback to remove.
            on_status: The status callback to remove.
        """
        try:
            self._log_callbacks.remove(on_log)
        except ValueError:
            pass
        try:
            self._status_callbacks.remove(on_status)
        except ValueError:
            pass
        logger.debug("Unregistered UI callbacks")

    def _emit_log(self, line: str):
        """Append a line to the buffer and notify all log callbacks."""
        self._log_lines.append(line)
        for cb in list(self._log_callbacks):
            try:
                cb(line)
            except Exception:
                logger.warning("Log callback failed", exc_info=True)

    def _emit_status(self, s: str):
        """Update the status string and notify all status callbacks."""
        self._status = s
        for cb in list(self._status_callbacks):
            try:
                cb(s)
            except Exception:
                logger.warning("Status callback failed", exc_info=True)

    async def run_experiment(
        self,
        config_path: str,
    ):
        """Load a PANTHER experiment config and execute it in a background thread.

        This is the main entry point for the web UI's "Run" button.  The
        method performs the following steps:

        1. Acquire the run lock and reset state (log buffer, status).
        2. Enable event batching on the ``WebObserver`` and start a
           NiceGUI timer to periodically flush batched events.
        3. Offload the blocking work to a background thread via
           ``asyncio.to_thread``:
           a. Parse the YAML config and build a ``GlobalConfig``.
           b. Instantiate ``ExperimentManager`` (PANTHER's four-phase
              orchestrator) as a context manager.
           c. Register the ``WebObserver`` with the global
              ``EventManager`` so that all core events are forwarded to
              the UI.
           d. Call ``manager.initialize_experiments`` and
              ``manager.run_tests``.
           e. At each stage, check for a user-requested stop.
        4. On completion (or error), update the status and persist
           observer state.

        Only one experiment may run at a time.  Calling this method while
        another run is active raises ``RuntimeError``.

        Args:
            config_path: Filesystem path to the experiment config YAML
                file.

        Raises:
            RuntimeError: If an experiment is already running.
        """
        with self._lock:
            if self._running:
                raise RuntimeError("An experiment is already running")
            self._running = True
            self._stop_requested = False
        self._log_lines.clear()
        self._config_path = config_path
        logger.info("Starting experiment run with config: %s", config_path)

        # Enable event batching for the duration of the experiment
        self._web_observer.enable_batching(500)
        try:
            from nicegui import ui
        except ImportError:
            # Outside NiceGUI context (e.g. in tests)
            self._batch_timer = None
        else:
            try:
                self._batch_timer = ui.timer(0.5, self._web_observer._flush_batch)
            except Exception:
                logger.error("Failed to create batch timer", exc_info=True)
                self._batch_timer = None

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

                logger.info("Experiment config loaded, initializing ExperimentManager")
                self._emit_status("Initializing...")
                self._emit_log(f"Loaded config from {config_path}")

                from panther.core.observer.management.event_manager import (
                    get_event_manager,
                )

                # 4. Use context manager for proper cleanup
                with ExperimentManager(
                    global_config=global_config,
                    experiment_name=(config_dict.get("metadata") or {}).get("name")
                    or "web_experiment",
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
                        logger.info(
                            "Experiment run finished (success=%s) for config: %s",
                            success,
                            config_path,
                        )

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
                with self._lock:
                    self._running = False

        try:
            await asyncio.to_thread(_run)
        except BaseException:
            with self._lock:
                self._running = False
            raise
        finally:
            # Stop batch timer and flush remaining events
            if self._batch_timer is not None:
                try:
                    self._batch_timer.cancel()
                except Exception:
                    logger.warning("Failed to cancel batch timer", exc_info=True)
                self._batch_timer = None
            self._web_observer.disable_batching()

            # Persist observer state
            self._save_observer_state()

    def _try_restore_observer_state(self):
        """Restore WebObserver gui_state from NiceGUI app storage if available."""
        try:
            from nicegui import app
        except ImportError:
            return
        try:
            saved = app.storage.general.get("web_observer_state")
            if saved:
                self._web_observer.restore_state(saved)
        except Exception:
            logger.warning("Failed to restore observer state", exc_info=True)

    def _save_observer_state(self):
        """Persist WebObserver gui_state to NiceGUI app storage."""
        try:
            from nicegui import app
        except ImportError:
            return
        try:
            app.storage.general["web_observer_state"] = self._web_observer.save_state()
        except Exception:
            logger.warning("Failed to save observer state", exc_info=True)

    def stop(self):
        """Request a graceful stop of the currently running experiment.

        Sets the ``_stop_requested`` flag under the lock.  The background
        thread checks this flag at defined checkpoints and raises
        ``_StopRequested`` to unwind cleanly.  This method returns
        immediately -- it does not wait for the experiment to actually
        terminate.
        """
        with self._lock:
            self._stop_requested = True
        logger.info("Experiment stop requested")

    def _on_event(self, event: BaseEvent):
        """Bridge PANTHER core events to the log/status callback system."""
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
        """Subscribe to raw PANTHER events via the internal WebObserver.

        Unlike ``register_callbacks`` (which delivers pre-formatted log
        lines), this method delivers the original ``BaseEvent`` objects so
        that the subscriber can inspect event type, payload, and
        importance.

        Args:
            callback: Function to invoke with each ``BaseEvent``.
        """
        self._web_observer.subscribe(callback)

    def unsubscribe_events(self, callback: Callable[[BaseEvent], None]):
        """Remove a previously registered raw-event subscriber.

        Args:
            callback: The callback to remove.  Silently ignored if not
                currently subscribed.
        """
        self._web_observer.unsubscribe(callback)

    @property
    def web_observer(self) -> WebObserver:
        """The ``WebObserver`` used to bridge core events to the UI.

        Exposed so that UI components can subscribe to events directly or
        access the event history and GUI state counters.
        """
        return self._web_observer

    @property
    def is_running(self) -> bool:
        """Whether an experiment is currently executing in the background thread."""
        with self._lock:
            return self._running


_instance: Optional[ExperimentService] = None
_instance_lock = threading.Lock()


def get_experiment_service() -> ExperimentService:
    """Return the module-level singleton ``ExperimentService`` instance.

    The singleton is lazily created on first call and persists for the
    lifetime of the server process.  This ensures that log buffers and
    execution state survive NiceGUI page navigations.

    Returns:
        The shared ``ExperimentService`` instance.
    """
    global _instance
    if _instance is None:
        with _instance_lock:
            if _instance is None:
                _instance = ExperimentService()
    return _instance
