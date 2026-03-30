"""Tests for LogContext and log_context context manager."""

import threading

import pytest

pytestmark = pytest.mark.unit

from panther.core.utils.log_context import LogContext, get_log_context, log_context


class TestLogContext:
    """Tests for LogContext dataclass."""

    def test_default_values(self):
        ctx = LogContext()
        assert ctx.experiment_id is None
        assert ctx.test_id is None
        assert ctx.service_id is None
        assert ctx.phase is None
        assert ctx.correlation_id is None

    def test_with_updates_overrides_fields(self):
        ctx = LogContext(experiment_id="exp-1")
        updated = ctx.with_updates(test_id="test-1")
        assert updated.experiment_id == "exp-1"
        assert updated.test_id == "test-1"

    def test_with_updates_preserves_unmentioned_fields(self):
        ctx = LogContext(experiment_id="exp-1", phase="init")
        updated = ctx.with_updates(test_id="test-1")
        assert updated.experiment_id == "exp-1"
        assert updated.phase == "init"
        assert updated.test_id == "test-1"

    def test_with_updates_ignores_none_values(self):
        ctx = LogContext(experiment_id="exp-1")
        updated = ctx.with_updates(experiment_id=None)
        assert updated.experiment_id == "exp-1"

    def test_frozen(self):
        ctx = LogContext()
        with pytest.raises(AttributeError):
            ctx.experiment_id = "x"  # type: ignore[misc]


class TestLogContextManager:
    """Tests for log_context() context manager."""

    def test_basic_context(self):
        with log_context(experiment_id="exp-1"):
            ctx = get_log_context()
            assert ctx.experiment_id == "exp-1"
        assert get_log_context().experiment_id is None

    def test_nested_contexts_merge(self):
        with log_context(experiment_id="exp-1"):
            with log_context(test_id="test-1"):
                ctx = get_log_context()
                assert ctx.experiment_id == "exp-1"
                assert ctx.test_id == "test-1"
            # test_id should be gone after inner context exits
            ctx = get_log_context()
            assert ctx.experiment_id == "exp-1"
            assert ctx.test_id is None

    def test_nested_override(self):
        with log_context(phase="init"):
            with log_context(phase="execution"):
                assert get_log_context().phase == "execution"
            assert get_log_context().phase == "init"

    def test_deeply_nested(self):
        with log_context(experiment_id="e"):
            with log_context(test_id="t"):
                with log_context(service_id="s"):
                    with log_context(phase="p"):
                        ctx = get_log_context()
                        assert ctx.experiment_id == "e"
                        assert ctx.test_id == "t"
                        assert ctx.service_id == "s"
                        assert ctx.phase == "p"

    def test_thread_isolation(self):
        """Each thread gets its own context."""
        results = {}

        def worker(name):
            with log_context(experiment_id=name):
                results[name] = get_log_context().experiment_id

        threads = [threading.Thread(target=worker, args=(f"t-{i}",)) for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        for i in range(5):
            assert results[f"t-{i}"] == f"t-{i}"

    def test_default_context_is_empty(self):
        ctx = get_log_context()
        assert ctx == LogContext()
