"""Thread-safety tests for MetricsCollector.

Verifies that concurrent access to MetricsCollector from multiple threads
does not lose data, corrupt state, or raise exceptions.
"""

import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import pytest

from panther.core.metrics.enums import MetricType, Phase
from panther.core.metrics.metrics_collector import MetricsCollector

pytestmark = [pytest.mark.unit]


@pytest.fixture
def collector(tmp_path):
    """Create a fresh MetricsCollector for each test."""
    return MetricsCollector(
        experiment_name="thread_safety_test",
        output_dir=tmp_path / "experiment",
        collection_interval=60.0,
    )


class TestConcurrentMetricRecording:
    """Multiple threads recording metrics simultaneously."""

    def test_no_metrics_lost_under_concurrent_writes(self, collector):
        """All metrics recorded from N threads should be present."""
        num_threads = 10
        metrics_per_thread = 100
        barrier = threading.Barrier(num_threads)

        def record_batch(thread_id):
            barrier.wait()  # Synchronize start
            for i in range(metrics_per_thread):
                collector.record_metric(
                    name=f"thread_{thread_id}_metric_{i}",
                    metric_type=MetricType.COUNTER,
                    value=1,
                    component=f"thread_{thread_id}",
                )

        threads = []
        for t in range(num_threads):
            thread = threading.Thread(target=record_batch, args=(t,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join(timeout=30)

        # Count user-recorded metrics (exclude the experiment_start metric)
        user_metrics = [m for m in collector.metrics if m.name != "experiment_start"]
        expected = num_threads * metrics_per_thread
        assert len(user_metrics) == expected

    def test_concurrent_increment_counter_produces_correct_sum(self, collector):
        """Concurrent increments to the same counter should produce exact sum."""
        num_threads = 8
        increments_per_thread = 200
        barrier = threading.Barrier(num_threads)

        def increment_batch(thread_id):
            barrier.wait()
            for _ in range(increments_per_thread):
                collector.increment_counter("shared_counter")

        with ThreadPoolExecutor(max_workers=num_threads) as executor:
            futures = [executor.submit(increment_batch, t) for t in range(num_threads)]
            for f in as_completed(futures):
                f.result()  # Raise any exceptions

        total = collector.get_counter("shared_counter")
        assert total == num_threads * increments_per_thread

    def test_concurrent_record_gauge_keeps_latest(self, collector):
        """Concurrent gauge recordings should result in one of the final values."""
        num_threads = 5
        values_per_thread = 50
        barrier = threading.Barrier(num_threads)

        def record_gauges(thread_id):
            barrier.wait()
            for i in range(values_per_thread):
                collector.record_gauge(
                    "shared_gauge",
                    float(thread_id * 1000 + i),
                )

        threads = []
        for t in range(num_threads):
            thread = threading.Thread(target=record_gauges, args=(t,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join(timeout=30)

        gauge_value = collector.get_gauge("shared_gauge")
        assert gauge_value is not None
        # The value should be one of the recorded values (any valid final value)
        all_possible = [
            float(t * 1000 + i)
            for t in range(num_threads)
            for i in range(values_per_thread)
        ]
        assert gauge_value in all_possible


class TestConcurrentTimerOperations:
    """Timer start/stop operations from multiple threads."""

    def test_concurrent_independent_timers(self, collector):
        """Each thread starts and stops its own timer without interference."""
        num_threads = 10
        barrier = threading.Barrier(num_threads)
        results = {}

        def timed_operation(thread_id):
            barrier.wait()
            timer_name = f"timer_{thread_id}"
            collector.start_timer(
                timer_name,
                component=f"thread_{thread_id}",
                test_case=f"test_{thread_id}",
            )
            time.sleep(0.01)  # Small sleep to ensure measurable duration
            duration = collector.stop_timer(
                timer_name,
                component=f"thread_{thread_id}",
                test_case=f"test_{thread_id}",
            )
            results[thread_id] = duration

        threads = []
        for t in range(num_threads):
            thread = threading.Thread(target=timed_operation, args=(t,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join(timeout=30)

        # All timers should have returned valid durations
        assert len(results) == num_threads
        for thread_id, duration in results.items():
            assert duration is not None
            assert duration >= 0.01

    def test_timing_context_manager_thread_safety(self, collector):
        """timing_context() used from multiple threads simultaneously."""
        num_threads = 8
        barrier = threading.Barrier(num_threads)
        durations = {}

        def timed_context(thread_id):
            barrier.wait()
            with collector.timing_context(
                f"ctx_{thread_id}",
                component=f"thread_{thread_id}",
                test_case=f"test_{thread_id}",
            ):
                time.sleep(0.01)
            durations[thread_id] = True

        threads = []
        for t in range(num_threads):
            thread = threading.Thread(target=timed_context, args=(t,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join(timeout=30)

        assert len(durations) == num_threads

        # Verify timing metrics were recorded
        timing = collector.timing_metrics
        for t in range(num_threads):
            assert f"ctx_{t}_duration" in timing


class TestConcurrentMixedOperations:
    """Threads performing different types of operations simultaneously."""

    def test_mixed_metric_types_concurrent(self, collector):
        """Different threads recording counters, gauges, timing, and errors."""
        num_threads = 4
        ops_per_thread = 50
        barrier = threading.Barrier(num_threads * 4)

        def record_counters(thread_id):
            barrier.wait()
            for i in range(ops_per_thread):
                collector.increment_counter(f"counter_{thread_id}")

        def record_gauges(thread_id):
            barrier.wait()
            for i in range(ops_per_thread):
                collector.record_gauge(f"gauge_{thread_id}", float(i))

        def record_timing(thread_id):
            barrier.wait()
            for i in range(ops_per_thread):
                collector.record_metric(
                    f"timing_{thread_id}_{i}",
                    MetricType.TIMING,
                    0.1 * i,
                    phase=Phase.TEST_EXECUTION,
                )

        def record_errors(thread_id):
            barrier.wait()
            for i in range(ops_per_thread):
                collector.record_error(
                    f"error_type_{thread_id}",
                    error_message=f"Error {i} from thread {thread_id}",
                )

        threads = []
        for t in range(num_threads):
            threads.append(threading.Thread(target=record_counters, args=(t,)))
            threads.append(threading.Thread(target=record_gauges, args=(t,)))
            threads.append(threading.Thread(target=record_timing, args=(t,)))
            threads.append(threading.Thread(target=record_errors, args=(t,)))

        for thread in threads:
            thread.start()

        for thread in threads:
            thread.join(timeout=30)

        # Verify counters
        for t in range(num_threads):
            assert collector.get_counter(f"counter_{t}") == ops_per_thread

        # Verify errors were all recorded
        assert len(collector.errors) == num_threads * ops_per_thread

    def test_concurrent_get_metrics_during_writes(self, collector):
        """Reading metrics while other threads are writing should not crash."""
        num_writers = 4
        num_readers = 2
        ops = 100
        barrier = threading.Barrier(num_writers + num_readers)
        read_errors = []

        def writer(thread_id):
            barrier.wait()
            for i in range(ops):
                collector.record_metric(
                    f"writer_{thread_id}_{i}",
                    MetricType.COUNTER,
                    1,
                )

        def reader(thread_id):
            barrier.wait()
            for _ in range(ops):
                try:
                    _ = collector.get_metrics()
                    _ = collector.counters
                    _ = collector.gauges
                    _ = collector.timing_metrics
                    _ = collector.errors
                except Exception as e:
                    read_errors.append(str(e))

        threads = []
        for t in range(num_writers):
            threads.append(threading.Thread(target=writer, args=(t,)))
        for t in range(num_readers):
            threads.append(threading.Thread(target=reader, args=(t,)))

        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=30)

        assert (
            len(read_errors) == 0
        ), f"Read errors during concurrent access: {read_errors}"


class TestConcurrentFinalization:
    """Finalization with concurrent operations."""

    def test_finalize_during_active_recording(self, collector):
        """Finalization while other threads are still recording should not crash."""
        barrier = threading.Barrier(2)
        recording_done = threading.Event()

        def slow_recorder():
            barrier.wait()
            for i in range(50):
                collector.record_metric(f"late_metric_{i}", MetricType.COUNTER, 1)
                time.sleep(0.001)
            recording_done.set()

        def finalizer():
            barrier.wait()
            time.sleep(0.01)  # Let some recording happen first
            collector.finalize()

        t1 = threading.Thread(target=slow_recorder)
        t2 = threading.Thread(target=finalizer)
        t1.start()
        t2.start()
        t1.join(timeout=30)
        t2.join(timeout=30)

        # Finalization should have completed without error
        assert collector._finalized is True

    def test_concurrent_finalize_calls_are_idempotent(self, collector):
        """Multiple threads calling finalize() should not cause issues."""
        num_threads = 5
        barrier = threading.Barrier(num_threads)
        errors = []

        def try_finalize(thread_id):
            barrier.wait()
            try:
                collector.finalize()
            except Exception as e:
                errors.append(f"Thread {thread_id}: {e}")

        threads = []
        for t in range(num_threads):
            thread = threading.Thread(target=try_finalize, args=(t,))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join(timeout=30)

        assert len(errors) == 0, f"Finalize errors: {errors}"
        assert collector._finalized is True
