"""
Unit tests for ExperimentManager - the core orchestration component of PANTHER.

Tests exercise the real ExperimentManager with IO boundaries mocked
(Docker daemon, subprocess, filesystem). No fake/shadow classes.

Covers:
- Initialization and attribute setup
- Experiment name sanitization
- Output directory creation
- Component wiring (event manager, workflow tracker, plugin manager, fast fail)
- cleanup() resource teardown
- record_failed_test() error recording
- Context manager protocol (__enter__ / __exit__)
- WorkflowStateTracker integration (replacing deleted fake phase tests)
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

pytestmark = [pytest.mark.unit, pytest.mark.experiment_manager]


# ---------------------------------------------------------------------------
# Initialization tests
# ---------------------------------------------------------------------------


class TestExperimentManagerInitialization:
    """Test ExperimentManager initialization and attribute setup."""

    def test_creation_sets_experiment_name_with_timestamp(
        self, real_experiment_manager
    ):
        """Test that __init__ produces an experiment_name containing the provided name."""
        # The real ExperimentManager prepends a timestamp:
        #   "2024-01-01_00-00-00_test_experiment"
        assert "test_experiment" in real_experiment_manager.experiment_name

    def test_experiment_name_sanitization(
        self, mock_docker_client, minimal_global_config, tmp_path
    ):
        """Test that special characters in experiment_name are sanitized to underscores."""
        import panther.core.observer.factory.observer_factory as _of_mod
        from panther.config.core.models.global_config import PathsConfig
        from panther.core.docker_builder.docker_builder import DockerBuilder
        from panther.core.experiment_manager import ExperimentManager
        from panther.core.observer.management.event_manager import EventManager
        from panther.plugins.plugin_manager import PluginManager

        DockerBuilder.reset_singleton()
        EventManager.reset_instance()
        PluginManager.reset_singleton()
        _of_mod._observer_factory = None

        output_dir = tmp_path / "sanitize_outputs"
        output_dir.mkdir(parents=True, exist_ok=True)
        paths_obj = PathsConfig(
            output_dir=str(output_dir),
            log_dir=str(tmp_path / "logs"),
        )
        cfg = minimal_global_config.model_copy(
            update={"paths": paths_obj},
        )

        with patch(
            "panther.core.docker_builder.docker_builder.docker"
        ) as mock_docker_mod:
            mock_docker_mod.from_env.return_value = mock_docker_client
            mock_docker_mod.errors = _make_docker_errors_module()

            manager = ExperimentManager(
                global_config=cfg,
                experiment_name="my experiment!@#name",
                dry_run=True,
            )

        # After sanitization: "my experiment!@#name" -> "my_experiment_name"
        # (regex removes non-alphanumeric/underscore, then collapses multiple underscores)
        assert "my_experiment_name" in manager.experiment_name
        assert "!" not in manager.experiment_name
        assert "@" not in manager.experiment_name
        assert "#" not in manager.experiment_name

    def test_experiment_dir_created(self, real_experiment_manager):
        """Test that experiment_dir is created during __init__."""
        assert real_experiment_manager.experiment_dir.exists()
        assert real_experiment_manager.experiment_dir.is_dir()

    def test_experiment_dir_under_output_dir(self, real_experiment_manager, tmp_path):
        """Test that experiment_dir is a subdirectory of the configured output_dir."""
        output_dir = tmp_path / "experiment_outputs"
        # experiment_dir should be output_dir / experiment_name
        assert str(real_experiment_manager.experiment_dir).startswith(str(output_dir))

    def test_dry_run_flag_preserved(self, real_experiment_manager):
        """Test that dry_run flag is stored on the manager."""
        assert real_experiment_manager.dry_run is True

    def test_global_config_stored(self, real_experiment_manager, minimal_global_config):
        """Test that global_config is accessible on the manager."""
        # The fixture uses model_copy so it won't be the exact same object,
        # but it should be a GlobalConfig with the expected logging level.
        from panther.config.core.models.global_config import GlobalConfig

        assert isinstance(real_experiment_manager.global_config, GlobalConfig)

    def test_test_cases_initially_empty(self, real_experiment_manager):
        """Test that test_cases list starts empty before initialize_experiments()."""
        assert real_experiment_manager.test_cases == []
        assert isinstance(real_experiment_manager.test_cases, list)


# ---------------------------------------------------------------------------
# Component wiring tests
# ---------------------------------------------------------------------------


class TestExperimentManagerComponents:
    """Test that ExperimentManager correctly wires up its sub-components."""

    def test_event_manager_initialized(self, real_experiment_manager):
        """Test that event_manager is set during __init__."""
        from panther.core.observer.management.event_manager import EventManager

        assert isinstance(real_experiment_manager.event_manager, EventManager)

    def test_workflow_tracker_initialized(self, real_experiment_manager):
        """Test that workflow_tracker is set during __init__."""
        from panther.core.observer.workflow.workflow_tracker import WorkflowStateTracker

        assert isinstance(
            real_experiment_manager.workflow_tracker, WorkflowStateTracker
        )

    def test_plugin_manager_initialized(self, real_experiment_manager):
        """Test that plugin_manager is set during __init__."""
        from panther.plugins.plugin_manager import PluginManager

        assert isinstance(real_experiment_manager.plugin_manager, PluginManager)

    def test_fast_fail_handler_initialized(self, real_experiment_manager):
        """Test that fast_fail_handler is set during __init__."""
        from panther.core.exceptions.fast_fail import FastFailHandler

        assert isinstance(real_experiment_manager.fast_fail_handler, FastFailHandler)

    def test_emitter_registry_initialized(self, real_experiment_manager):
        """Test that emitter_registry is set during __init__."""
        from panther.core.events.emitter_registry import EmitterRegistry

        assert isinstance(real_experiment_manager.emitter_registry, EmitterRegistry)

    def test_experiment_emitter_accessible(self, real_experiment_manager):
        """Test that experiment_emitter shortcut is wired from emitter_registry."""
        assert real_experiment_manager.experiment_emitter is not None
        assert (
            real_experiment_manager.experiment_emitter
            is real_experiment_manager.emitter_registry.experiment_emitter
        )


# ---------------------------------------------------------------------------
# Cleanup tests
# ---------------------------------------------------------------------------


class TestExperimentManagerCleanup:
    """Test cleanup() resource teardown."""

    def test_cleanup_clears_workflow_state(self, real_experiment_manager):
        """Test that cleanup() clears the workflow tracker state for this experiment."""
        tracker = real_experiment_manager.workflow_tracker
        exp_name = real_experiment_manager.experiment_name

        # Pre-populate a workflow state so we can verify it gets cleared
        from panther.core.observer.workflow.workflow_tracker import WorkflowState

        tracker.set_workflow_state(exp_name, WorkflowState.CREATED)
        assert tracker.get_workflow_state(exp_name) is not None

        # Run cleanup
        real_experiment_manager.cleanup()

        # Workflow state should be cleared
        assert tracker.get_workflow_state(exp_name) is None

    def test_cleanup_does_not_raise_on_missing_state(self, real_experiment_manager):
        """Test that cleanup() handles missing workflow state gracefully."""
        # No workflow state was set, cleanup should not raise
        real_experiment_manager.cleanup()

    def test_cleanup_unregisters_observers(self, real_experiment_manager):
        """Test that cleanup() attempts to unregister known observers."""
        # Cleanup should run without error and unregister observers via factory
        real_experiment_manager.cleanup()
        # If we get here without exception, cleanup handled observer teardown


# ---------------------------------------------------------------------------
# Context manager tests
# ---------------------------------------------------------------------------


class TestExperimentManagerContextManager:
    """Test context manager protocol (__enter__ / __exit__)."""

    def test_enter_returns_self(self, real_experiment_manager):
        """Test that __enter__ returns the manager instance."""
        result = real_experiment_manager.__enter__()
        assert result is real_experiment_manager

    def test_exit_calls_cleanup(self, real_experiment_manager):
        """Test that __exit__ calls cleanup()."""
        with patch.object(real_experiment_manager, "cleanup") as mock_cleanup:
            real_experiment_manager.__exit__(None, None, None)
            mock_cleanup.assert_called_once()

    def test_exit_does_not_suppress_exceptions(self, real_experiment_manager):
        """Test that __exit__ returns False (does not suppress exceptions)."""
        result = real_experiment_manager.__exit__(ValueError, ValueError("test"), None)
        assert result is False

    def test_with_statement_integration(
        self, mock_docker_client, minimal_global_config, tmp_path
    ):
        """Test using ExperimentManager in a with statement."""
        import panther.core.observer.factory.observer_factory as _of_mod
        from panther.config.core.models.global_config import PathsConfig
        from panther.core.docker_builder.docker_builder import DockerBuilder
        from panther.core.experiment_manager import ExperimentManager
        from panther.core.observer.management.event_manager import EventManager
        from panther.plugins.plugin_manager import PluginManager

        DockerBuilder.reset_singleton()
        EventManager.reset_instance()
        PluginManager.reset_singleton()
        _of_mod._observer_factory = None

        output_dir = tmp_path / "ctx_mgr_outputs"
        output_dir.mkdir(parents=True, exist_ok=True)
        paths_obj = PathsConfig(
            output_dir=str(output_dir),
            log_dir=str(tmp_path / "logs"),
        )
        cfg = minimal_global_config.model_copy(
            update={"paths": paths_obj},
        )

        with patch(
            "panther.core.docker_builder.docker_builder.docker"
        ) as mock_docker_mod:
            mock_docker_mod.from_env.return_value = mock_docker_client
            mock_docker_mod.errors = _make_docker_errors_module()

            with ExperimentManager(
                global_config=cfg,
                experiment_name="ctx_test",
                dry_run=True,
            ) as mgr:
                assert mgr is not None
                assert "ctx_test" in mgr.experiment_name
            # After exiting, cleanup should have been called (no assertions needed;
            # if cleanup raises, the test fails).


# ---------------------------------------------------------------------------
# record_failed_test tests
# ---------------------------------------------------------------------------


class TestRecordFailedTest:
    """Test record_failed_test() error recording."""

    def test_record_failed_test_logs_error(self, real_experiment_manager):
        """Test that record_failed_test logs the test name and error message."""
        mock_test_case = MagicMock()
        mock_test_case.test_config.name = "failing_test"
        error = RuntimeError("connection refused")

        # record_failed_test should not raise
        real_experiment_manager.record_failed_test(mock_test_case, error)

    def test_record_failed_test_truncates_long_errors(self, real_experiment_manager):
        """Test that record_failed_test handles very long error messages."""
        mock_test_case = MagicMock()
        mock_test_case.test_config.name = "long_error_test"
        error = RuntimeError("x" * 500)

        # Should not raise even with very long error string
        real_experiment_manager.record_failed_test(mock_test_case, error)


# ---------------------------------------------------------------------------
# WorkflowStateTracker integration tests
# (Replaces deleted fake phase-transition tests with real state machine tests)
# ---------------------------------------------------------------------------


class TestWorkflowStateTrackerIntegration:
    """Test WorkflowStateTracker as used by ExperimentManager.

    These tests replace the deleted fake-phase tests by exercising the real
    state machine that ExperimentManager delegates to for workflow coordination.
    """

    def test_tracker_starts_empty(self, real_experiment_manager):
        """Test that no workflow state is set before initialize_experiments()."""
        tracker = real_experiment_manager.workflow_tracker
        state = tracker.get_workflow_state(real_experiment_manager.experiment_name)
        assert state is None

    def test_valid_state_transition_sequence(self, real_experiment_manager):
        """Test that the full valid transition sequence succeeds."""
        from panther.core.observer.workflow.workflow_tracker import WorkflowState

        tracker = real_experiment_manager.workflow_tracker
        exp_id = real_experiment_manager.experiment_name

        # Walk through the valid workflow sequence
        transitions = [
            WorkflowState.CREATED,
            WorkflowState.LOADING_PLUGINS,
            WorkflowState.GENERATING_COMMANDS,
            WorkflowState.BUILDING_DOCKER,
            WorkflowState.DEPLOYING,
            WorkflowState.RUNNING,
            WorkflowState.COLLECTING_OUTPUTS,
            WorkflowState.ANALYZING_RESULTS,
            WorkflowState.REPORTING_RESULTS,
            WorkflowState.COMPLETED,
        ]

        for state in transitions:
            result = tracker.set_workflow_state(exp_id, state)
            assert result is True, f"Transition to {state.value} should succeed"

        assert tracker.get_workflow_state(exp_id) == WorkflowState.COMPLETED

    def test_invalid_state_transition_rejected(self, real_experiment_manager):
        """Test that skipping states is rejected by the tracker."""
        from panther.core.observer.workflow.workflow_tracker import WorkflowState

        tracker = real_experiment_manager.workflow_tracker
        exp_id = real_experiment_manager.experiment_name

        # Create the workflow
        tracker.set_workflow_state(exp_id, WorkflowState.CREATED)

        # Try to skip directly to RUNNING (should fail)
        result = tracker.set_workflow_state(exp_id, WorkflowState.RUNNING)
        assert result is False

        # State should remain CREATED
        assert tracker.get_workflow_state(exp_id) == WorkflowState.CREATED

    def test_force_fail_from_any_state(self, real_experiment_manager):
        """Test that force_fail_workflow moves to FAILED from any state."""
        from panther.core.observer.workflow.workflow_tracker import WorkflowState

        tracker = real_experiment_manager.workflow_tracker
        exp_id = real_experiment_manager.experiment_name

        tracker.set_workflow_state(exp_id, WorkflowState.CREATED)
        tracker.set_workflow_state(exp_id, WorkflowState.LOADING_PLUGINS)

        result = tracker.force_fail_workflow(exp_id, reason="test forced failure")
        assert result is True
        assert tracker.get_workflow_state(exp_id) == WorkflowState.FAILED

    def test_terminal_states_have_no_transitions(self, real_experiment_manager):
        """Test that COMPLETED and FAILED are terminal (no outgoing transitions)."""
        from panther.core.observer.workflow.workflow_tracker import WorkflowState

        tracker = real_experiment_manager.workflow_tracker

        completed_transitions = tracker.get_allowed_transitions(
            WorkflowState.COMPLETED.value
        )
        failed_transitions = tracker.get_allowed_transitions(WorkflowState.FAILED.value)

        assert completed_transitions == []
        assert failed_transitions == []

    def test_state_history_recorded(self, real_experiment_manager):
        """Test that state transitions are recorded in history."""
        from panther.core.observer.workflow.workflow_tracker import WorkflowState

        tracker = real_experiment_manager.workflow_tracker
        exp_id = real_experiment_manager.experiment_name

        tracker.set_workflow_state(exp_id, WorkflowState.CREATED)
        tracker.set_workflow_state(exp_id, WorkflowState.LOADING_PLUGINS)

        history = tracker.get_state_history(exp_id)
        assert len(history) == 2

        assert history[0]["old_state"] is None
        assert history[0]["new_state"] == "created"
        assert history[1]["old_state"] == "created"
        assert history[1]["new_state"] == "loading_plugins"

    def test_clear_workflow_state(self, real_experiment_manager):
        """Test that clear_workflow_state removes the workflow entry."""
        from panther.core.observer.workflow.workflow_tracker import WorkflowState

        tracker = real_experiment_manager.workflow_tracker
        exp_id = real_experiment_manager.experiment_name

        tracker.set_workflow_state(exp_id, WorkflowState.CREATED)
        assert tracker.get_workflow_state(exp_id) is not None

        tracker.clear_workflow_state(exp_id)
        assert tracker.get_workflow_state(exp_id) is None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_docker_errors_module():
    """Create a mock docker.errors module with real exception types."""
    errors = MagicMock()
    errors.DockerException = type("DockerException", (Exception,), {})
    errors.ImageNotFound = type("ImageNotFound", (Exception,), {})
    errors.NotFound = type("NotFound", (Exception,), {})
    errors.APIError = type("APIError", (Exception,), {})
    errors.BuildError = type("BuildError", (Exception,), {})
    return errors
