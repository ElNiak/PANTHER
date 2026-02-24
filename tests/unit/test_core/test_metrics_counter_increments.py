"""Tests for Bug 1: experiment_manager correctly increments summary counters."""

import sys
from unittest.mock import MagicMock, call, patch

import pytest

from panther.core.metrics.enums import Phase
from panther.core.metrics.metrics_collector import MetricsCollector

pytestmark = [pytest.mark.unit]


@pytest.fixture
def mock_collector():
    """Create a mock MetricsCollector with increment_counter tracking."""
    collector = MagicMock(spec=MetricsCollector)
    return collector


def _make_manager(mock_collector, test_cases=None):
    """Create a minimally mocked ExperimentManager for run_tests()."""
    from panther.core.experiment_manager import ExperimentManager

    with patch.object(ExperimentManager, "__init__", lambda self, **kw: None):
        mgr = ExperimentManager.__new__(ExperimentManager)

    mgr.metrics_collector = mock_collector
    mgr.experiment_name = "test_exp"
    mgr.dry_run = False
    mgr.test_cases = test_cases or []
    mgr.logger = MagicMock()
    mgr.experiment_emitter = MagicMock()
    mgr.event_manager = MagicMock()
    mgr.fast_fail_handler = MagicMock()
    mgr.emitter_registry = MagicMock()
    mgr._save_test_configuration = MagicMock()

    # global_config stub with all required attributes
    gc = MagicMock()
    gc.progress.show_test_status = False
    gc.progress.use_emojis = False
    gc.progress.enable_progress_bar = False
    mgr.global_config = gc

    return mgr


def _get_counter_names(mock_collector):
    """Extract all counter names from increment_counter calls."""
    names = []
    for c in mock_collector.increment_counter.call_args_list:
        args, kwargs = c
        if args:
            names.append(args[0])
        elif "name" in kwargs:
            names.append(kwargs["name"])
    return names


class TestExperimentManagerCounterIncrements:
    """Verify that run_tests() calls increment_counter at lifecycle points."""

    def test_experiments_total_incremented_on_start(self, mock_collector):
        mgr = _make_manager(mock_collector)
        mgr.run_tests()
        assert "experiments_total" in _get_counter_names(mock_collector)

    def test_experiments_successful_when_no_failures(self, mock_collector):
        mgr = _make_manager(mock_collector)
        mgr.run_tests()
        assert "experiments_successful" in _get_counter_names(mock_collector)

    def test_experiments_failed_when_test_fails(self, mock_collector):
        tc = MagicMock()
        tc.test_config.name = "fail_test"
        tc.run.return_value = False
        mgr = _make_manager(mock_collector, test_cases=[tc])

        mgr.run_tests()

        names = _get_counter_names(mock_collector)
        assert "experiments_failed" in names

    def test_test_cases_counters_on_success(self, mock_collector):
        tc = MagicMock()
        tc.test_config.name = "pass_test"
        tc.run.return_value = True
        mgr = _make_manager(mock_collector, test_cases=[tc])

        mgr.run_tests()

        names = _get_counter_names(mock_collector)
        assert "test_cases_total" in names
        assert "test_cases_successful" in names

    def test_test_cases_counters_on_failure(self, mock_collector):
        tc = MagicMock()
        tc.test_config.name = "fail_test"
        tc.run.return_value = False
        mgr = _make_manager(mock_collector, test_cases=[tc])

        mgr.run_tests()

        names = _get_counter_names(mock_collector)
        assert "test_cases_total" in names
        assert "test_cases_failed" in names

    def test_exception_test_counts_as_failure(self, mock_collector):
        tc = MagicMock()
        tc.test_config.name = "error_test"
        tc.run.side_effect = RuntimeError("boom")
        mgr = _make_manager(mock_collector, test_cases=[tc])

        mgr.run_tests()

        names = _get_counter_names(mock_collector)
        assert "test_cases_total" in names
        assert "test_cases_failed" in names
