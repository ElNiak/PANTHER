"""Unit tests for ExperimentObserverMixin.

Tests the observer setup and management functionality provided by
ExperimentObserverMixin, which centralizes observer creation for the
ExperimentManager.

Covers:
- _setup_observers() registers all expected observer types
- setup_observer() handles individual observer exceptions gracefully
- create_logger_observer() configures the correct log level (global vs observer-specific)
"""

import logging
from pathlib import Path
from unittest.mock import MagicMock, call, patch

import pytest

pytestmark = pytest.mark.unit


# ---------------------------------------------------------------------------
# Minimal stub host class
# ---------------------------------------------------------------------------


class _StubHost:
    """Minimal stub that satisfies all ExperimentObserverMixin attribute requirements."""

    def __init__(
        self, tmp_path: Path, log_level: int = logging.INFO, **config_overrides
    ):
        from panther.core.experiment_observer import ExperimentObserverMixin

        # Mix in the mixin by inserting it into the class hierarchy at runtime
        self.__class__ = type(
            "_StubHostWithMixin",
            (ExperimentObserverMixin, _StubHost),
            {},
        )

        self.experiment_name = "test_experiment"
        self.logs_dir = tmp_path / "logs"
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        self.log_level = log_level
        self.logger = MagicMock()
        self.event_manager = MagicMock()
        self.workflow_tracker = MagicMock()
        self.experiment_emitter = MagicMock()
        self.metrics_collector = MagicMock()
        # _jsonl_writer used by register_event_stream_recorder
        self._jsonl_writer = None

        # Build a simple global_config namespace with observer settings
        self.global_config = _make_global_config(**config_overrides)


def _make_global_config(
    logger_enabled: bool = True,
    metrics_enabled: bool = True,
    logger_log_level: str = "INFO",
    metrics_log_level: str = "INFO",
):
    """Return a minimal namespace object mimicking global_config.observers.*."""
    logger_obs_cfg = MagicMock()
    logger_obs_cfg.enabled = logger_enabled
    logger_obs_cfg.log_level = logger_log_level

    metrics_obs_cfg = MagicMock()
    metrics_obs_cfg.enabled = metrics_enabled
    metrics_obs_cfg.log_level = metrics_log_level

    observers_cfg = MagicMock()
    observers_cfg.logger = logger_obs_cfg
    observers_cfg.metrics = metrics_obs_cfg

    cfg = MagicMock()
    cfg.observers = observers_cfg
    return cfg


def _make_stub(tmp_path, **kwargs):
    """Factory helper so each test gets a fresh stub."""
    return _StubHost(tmp_path, **kwargs)


# ---------------------------------------------------------------------------
# Helper: patch all three factory functions at once
# ---------------------------------------------------------------------------


class _FactoryPatches:
    """Context manager that patches all three observer factory functions.

    Usage::

        with _patch_factories() as patches:
            stub.setup_observer()
            patches["create_experiment_observer"].assert_called_once()
    """

    def __init__(self):
        self._create_exp = patch(
            "panther.core.experiment_observer.create_experiment_observer",
            return_value=MagicMock(),
        )
        self._create_log = patch(
            "panther.core.experiment_observer.create_logger",
            return_value=MagicMock(),
        )
        self._create_met = patch(
            "panther.core.experiment_observer.create_metrics",
            return_value=MagicMock(),
        )
        self._mocks = {}

    def __enter__(self):
        self._mocks["create_experiment_observer"] = self._create_exp.__enter__()
        self._mocks["create_logger"] = self._create_log.__enter__()
        self._mocks["create_metrics"] = self._create_met.__enter__()
        return self._mocks

    def __exit__(self, *args):
        self._create_exp.__exit__(*args)
        self._create_log.__exit__(*args)
        self._create_met.__exit__(*args)


def _patch_factories():
    """Return a _FactoryPatches context manager."""
    return _FactoryPatches()


# ---------------------------------------------------------------------------
# Test: _setup_observers — happy path calls setup_observer
# ---------------------------------------------------------------------------


class TestSetupObservers:
    """Tests for _setup_observers()."""

    def test_setup_observers_calls_setup_observer(self, tmp_path):
        """_setup_observers() delegates to setup_observer() on success."""
        stub = _make_stub(tmp_path)

        with patch.object(stub, "setup_observer") as mock_setup:
            stub._setup_observers()

        mock_setup.assert_called_once_with()

    def test_setup_observers_reraises_exception_and_emits_event(self, tmp_path):
        """_setup_observers() emits error event and re-raises on setup_observer failure."""
        stub = _make_stub(tmp_path)
        boom = RuntimeError("observer boom")

        with patch.object(stub, "setup_observer", side_effect=boom):
            with pytest.raises(RuntimeError, match="observer boom"):
                stub._setup_observers()

        stub.experiment_emitter.emit_finished_early.assert_called_once()
        call_kwargs = stub.experiment_emitter.emit_finished_early.call_args
        # reason should mention 'Observer Setup Error'
        reason_arg = call_kwargs[1].get("reason") or call_kwargs[0][0]
        assert "Observer Setup Error" in reason_arg

        stub.logger.error.assert_called_once()

    def test_setup_observers_does_not_swallow_exception(self, tmp_path):
        """_setup_observers() must propagate the exception after emitting the event."""
        stub = _make_stub(tmp_path)

        with patch.object(stub, "setup_observer", side_effect=ValueError("boom")):
            with pytest.raises(ValueError, match="boom"):
                stub._setup_observers()


# ---------------------------------------------------------------------------
# Test: setup_observer — registers expected observer types
# ---------------------------------------------------------------------------


class TestSetupObserverRegistrations:
    """Tests for setup_observer() – verifies which observers get registered."""

    def test_registers_state_event_observer(self, tmp_path):
        """setup_observer() always registers a StateEventObserver."""
        stub = _make_stub(tmp_path)

        with _patch_factories():
            with patch(
                "panther.core.experiment_observer.ExperimentObserverMixin.register_event_stream_recorder"
            ):
                stub.setup_observer()

        # register_observer_once should have been called for state observer
        calls = stub.event_manager.register_observer_once.call_args_list
        observer_ids = [c[1].get("observer_id") or c[0][1] for c in calls]
        assert "experiment_state_observer" in observer_ids

    def test_registers_experiment_observer_via_factory(self, tmp_path):
        """setup_observer() calls create_experiment_observer exactly once."""
        stub = _make_stub(tmp_path)

        with _patch_factories() as patches:
            with patch(
                "panther.core.experiment_observer.ExperimentObserverMixin.register_event_stream_recorder"
            ):
                stub.setup_observer()

        patches["create_experiment_observer"].assert_called_once()

    def test_registers_logger_observer_when_enabled(self, tmp_path):
        """setup_observer() calls create_logger when logger observer is enabled."""
        stub = _make_stub(tmp_path, log_level=logging.INFO, logger_enabled=True)

        with _patch_factories() as patches:
            with patch(
                "panther.core.experiment_observer.ExperimentObserverMixin.register_event_stream_recorder"
            ):
                stub.setup_observer()

        patches["create_logger"].assert_called_once()

    def test_skips_logger_observer_when_disabled(self, tmp_path):
        """setup_observer() skips create_logger when logger observer is disabled."""
        stub = _make_stub(tmp_path, logger_enabled=False)

        with _patch_factories() as patches:
            with patch(
                "panther.core.experiment_observer.ExperimentObserverMixin.register_event_stream_recorder"
            ):
                stub.setup_observer()

        patches["create_logger"].assert_not_called()

    def test_skips_regular_logger_when_debug_level(self, tmp_path):
        """setup_observer() skips create_logger when log_level is DEBUG (debug logger used instead)."""
        stub = _make_stub(tmp_path, log_level=logging.DEBUG, logger_enabled=True)

        with _patch_factories() as patches:
            with patch(
                "panther.core.experiment_observer.ExperimentObserverMixin.register_event_stream_recorder"
            ):
                with patch(
                    "panther.core.experiment_observer.ExperimentObserverMixin.register_debug_logger"
                ) as mock_debug:
                    stub.setup_observer()

        patches["create_logger"].assert_not_called()
        mock_debug.assert_called_once()

    def test_registers_metrics_observer_when_enabled(self, tmp_path):
        """setup_observer() calls create_metrics when metrics observer is enabled."""
        stub = _make_stub(tmp_path, metrics_enabled=True)

        with _patch_factories() as patches:
            with patch(
                "panther.core.experiment_observer.ExperimentObserverMixin.register_event_stream_recorder"
            ):
                stub.setup_observer()

        patches["create_metrics"].assert_called_once()

    def test_skips_metrics_observer_when_disabled(self, tmp_path):
        """setup_observer() skips create_metrics when metrics observer is disabled."""
        stub = _make_stub(tmp_path, metrics_enabled=False)

        with _patch_factories() as patches:
            with patch(
                "panther.core.experiment_observer.ExperimentObserverMixin.register_event_stream_recorder"
            ):
                stub.setup_observer()

        patches["create_metrics"].assert_not_called()


# ---------------------------------------------------------------------------
# Test: setup_observer — exception isolation
# ---------------------------------------------------------------------------


class TestSetupObserverExceptionIsolation:
    """Tests that individual observer registration failures don't abort the rest."""

    def test_metrics_failure_does_not_abort_experiment_observer(self, tmp_path):
        """If metrics registration fails, setup_observer continues and still creates experiment_observer."""
        stub = _make_stub(tmp_path, metrics_enabled=True)

        # Make register_metric raise while create_experiment_observer is mocked to succeed
        with _patch_factories() as patches:
            with patch(
                "panther.core.experiment_observer.ExperimentObserverMixin.register_event_stream_recorder"
            ):
                with patch.object(
                    stub, "register_metric", side_effect=Exception("metrics explode")
                ):
                    stub.setup_observer()

        # experiment observer must still be created
        patches["create_experiment_observer"].assert_called_once()
        # warning must have been logged
        stub.logger.warning.assert_called()
        warning_args = stub.logger.warning.call_args_list
        assert any("metrics" in str(c).lower() for c in warning_args)

    def test_logger_failure_does_not_abort_experiment_observer(self, tmp_path):
        """If logger observer creation fails, setup_observer continues and creates experiment_observer."""
        stub = _make_stub(tmp_path, log_level=logging.INFO, logger_enabled=True)

        # Patch create_logger to raise
        with patch(
            "panther.core.experiment_observer.create_logger",
            side_effect=Exception("logger explode"),
        ):
            with patch(
                "panther.core.experiment_observer.create_experiment_observer",
                return_value=MagicMock(),
            ) as mock_exp:
                with patch(
                    "panther.core.experiment_observer.ExperimentObserverMixin.register_event_stream_recorder"
                ):
                    stub.setup_observer()

        mock_exp.assert_called_once()
        stub.logger.warning.assert_called()

    def test_each_registration_attempt_is_independent(self, tmp_path):
        """Even if multiple observers fail, every attempt is made."""
        stub = _make_stub(
            tmp_path, log_level=logging.INFO, logger_enabled=True, metrics_enabled=True
        )

        # Both metrics and logger observers fail
        with patch(
            "panther.core.experiment_observer.create_logger",
            side_effect=Exception("logger fail"),
        ):
            with patch(
                "panther.core.experiment_observer.create_metrics",
                side_effect=Exception("metrics fail"),
            ):
                with patch(
                    "panther.core.experiment_observer.create_experiment_observer",
                    return_value=MagicMock(),
                ) as mock_exp:
                    with patch(
                        "panther.core.experiment_observer.ExperimentObserverMixin.register_event_stream_recorder"
                    ):
                        # Should not raise
                        stub.setup_observer()

        mock_exp.assert_called_once()
        # Two warnings: one from logger, one from metrics
        assert stub.logger.warning.call_count >= 1


# ---------------------------------------------------------------------------
# Test: create_logger_observer — log level selection
# ---------------------------------------------------------------------------


class TestCreateLoggerObserverLogLevel:
    """Tests for create_logger_observer() log level selection logic."""

    def _run_create_logger_observer(self, stub):
        """Run create_logger_observer with create_logger patched; return the mock and its call kwargs."""
        mock_observer = MagicMock()
        with patch(
            "panther.core.experiment_observer.create_logger", return_value=mock_observer
        ) as mock_create:
            stub.create_logger_observer()
        return mock_create, mock_observer

    def test_uses_global_level_when_more_restrictive(self, tmp_path):
        """Uses global log_level (WARNING) when it is more restrictive than observer level (DEBUG)."""
        # global=WARNING (30), observer=DEBUG (10) -> WARNING wins (higher = more restrictive)
        stub = _make_stub(tmp_path, log_level=logging.WARNING, logger_log_level="DEBUG")

        mock_create, _ = self._run_create_logger_observer(stub)

        call_kwargs = mock_create.call_args[1]
        assert call_kwargs["log_level"].upper() == "WARNING"

    def test_uses_observer_level_when_more_restrictive(self, tmp_path):
        """Uses observer log_level (ERROR) when it is more restrictive than global level (INFO)."""
        # global=INFO (20), observer=ERROR (40) -> ERROR wins (higher = more restrictive)
        stub = _make_stub(tmp_path, log_level=logging.INFO, logger_log_level="ERROR")

        mock_create, _ = self._run_create_logger_observer(stub)

        call_kwargs = mock_create.call_args[1]
        assert call_kwargs["log_level"].upper() == "ERROR"

    def test_uses_same_level_when_equal(self, tmp_path):
        """When global and observer levels are the same, the chosen level is that level."""
        stub = _make_stub(tmp_path, log_level=logging.INFO, logger_log_level="INFO")

        mock_create, _ = self._run_create_logger_observer(stub)

        call_kwargs = mock_create.call_args[1]
        assert call_kwargs["log_level"].upper() == "INFO"

    def test_output_file_is_under_logs_dir(self, tmp_path):
        """create_logger_observer() sets output_file inside logs_dir."""
        stub = _make_stub(tmp_path)

        mock_create, _ = self._run_create_logger_observer(stub)

        call_kwargs = mock_create.call_args[1]
        assert "event_log.log" in call_kwargs["output_file"]
        assert str(stub.logs_dir) in call_kwargs["output_file"]

    def test_registers_observer_with_event_manager(self, tmp_path):
        """create_logger_observer() registers the created observer with event_manager."""
        stub = _make_stub(tmp_path)
        mock_observer = MagicMock()

        with patch(
            "panther.core.experiment_observer.create_logger", return_value=mock_observer
        ):
            stub.create_logger_observer()

        stub.event_manager.register_observer_once.assert_called_once_with(
            observer=mock_observer,
            observer_id="experiment_logger",
            scope="experiment",
            event_types=None,
            priority=0,
        )

    def test_exception_in_create_logger_logs_warning(self, tmp_path):
        """create_logger_observer() catches exceptions and logs a warning instead of raising."""
        stub = _make_stub(tmp_path)

        with patch(
            "panther.core.experiment_observer.create_logger",
            side_effect=OSError("disk full"),
        ):
            # Must not raise
            stub.create_logger_observer()

        stub.logger.warning.assert_called_once()
        warning_msg = str(stub.logger.warning.call_args)
        assert "logger" in warning_msg.lower() or "observer" in warning_msg.lower()
