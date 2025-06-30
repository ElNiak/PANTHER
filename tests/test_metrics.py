"""Tests for the PANTHER metrics system."""

import json
import time
from unittest.mock import Mock, patch

import pytest

from panther.metrics import MetricsCollector, record, flush
from panther.metrics.storage import JSONLinesStorage
from panther.metrics.resource_sampler import ResourceSampler
from panther.metrics.utils import get_directory_size_mb, find_latest_wheel


class TestMetricsCollector:
    """Test the core metrics collector functionality."""

    def test_collector_initialization(self, tmp_path):
        """Test that collector initializes correctly."""
        collector = MetricsCollector(tmp_path)
        assert collector.storage.base_path == tmp_path
        assert collector.run_id is not None
        assert len(collector.run_id) == 36  # UUID format

    def test_record_metric(self, tmp_path):
        """Test recording metrics."""
        collector = MetricsCollector(tmp_path)

        collector.record("test.metric", 42.5)
        assert collector._metrics["test.metric"] == 42.5

        collector.record("test.tagged", 100.0, {"env": "test"})
        assert collector._metrics["test.tagged"] == 100.0
        assert collector._tags["test.tagged"] == {"env": "test"}

    def test_flush_metrics(self, tmp_path):
        """Test flushing metrics to storage."""
        collector = MetricsCollector(tmp_path)

        collector.record("build.time", 15.5, {"stage": "test"})
        collector.record("build.size", 100.0)

        run_id = collector.flush("test", {"extra": "data"})

        # Check that metrics were cleared
        assert len(collector._metrics) == 0
        assert len(collector._tags) == 0

        # Check that data was written
        files = list(tmp_path.glob("*.jsonl"))
        assert len(files) == 1

        # Read and verify the record
        with open(files[0]) as f:
            record = json.loads(f.read().strip())

        assert record["run_id"] == run_id
        assert record["type"] == "test"
        assert record["metrics"]["build.time"] == 15.5
        assert record["metrics"]["build.size"] == 100.0
        assert record["tags"]["build.time"] == {"stage": "test"}
        assert record["extra"] == "data"

    def test_config_hash(self, tmp_path):
        """Test configuration hash generation."""
        collector = MetricsCollector(tmp_path)

        config1 = {"key": "value", "number": 42}
        config2 = {"number": 42, "key": "value"}  # Same content, different order
        config3 = {"key": "different", "number": 42}

        hash1 = collector.get_config_hash(config1)
        hash2 = collector.get_config_hash(config2)
        hash3 = collector.get_config_hash(config3)

        assert hash1 == hash2  # Order shouldn't matter
        assert hash1 != hash3  # Different content should produce different hash
        assert len(hash1) == 16  # Truncated to 16 characters


class TestJSONLinesStorage:
    """Test the JSON Lines storage backend."""

    def test_write_and_read_records(self, tmp_path):
        """Test writing and reading records."""
        storage = JSONLinesStorage(tmp_path)

        record1 = {
            "run_id": "test-1",
            "type": "test",
            "timestamp": "2025-05-30T10:00:00Z",
            "metrics": {"time": 10.0},
        }
        record2 = {
            "run_id": "test-2",
            "type": "test",
            "timestamp": "2025-05-30T11:00:00Z",
            "metrics": {"time": 20.0},
        }

        storage.write_record(record1)
        storage.write_record(record2)

        records = storage.read_records()
        assert len(records) == 2
        # Should be sorted by timestamp, newest first
        assert records[0]["run_id"] == "test-2"
        assert records[1]["run_id"] == "test-1"

    def test_get_record_by_id(self, tmp_path):
        """Test retrieving specific records by ID."""
        storage = JSONLinesStorage(tmp_path)

        record = {"run_id": "specific-test", "type": "test", "metrics": {"value": 42.0}}

        storage.write_record(record)

        retrieved = storage.get_record_by_id("specific-test")
        assert retrieved is not None
        assert retrieved["run_id"] == "specific-test"
        assert retrieved["metrics"]["value"] == 42.0

        # Test non-existent ID
        assert storage.get_record_by_id("non-existent") is None

    def test_read_with_limit(self, tmp_path):
        """Test reading records with limit."""
        storage = JSONLinesStorage(tmp_path)

        # Write multiple records
        for i in range(5):
            record = {
                "run_id": f"test-{i}",
                "type": "test",
                "timestamp": f"2025-05-30T{10+i:02d}:00:00Z",
                "metrics": {"value": float(i)},
            }
            storage.write_record(record)

        # Test limit
        records = storage.read_records(limit=3)
        assert len(records) == 3
        # Should get the 3 most recent
        assert records[0]["run_id"] == "test-4"
        assert records[1]["run_id"] == "test-3"
        assert records[2]["run_id"] == "test-2"


class TestResourceSampler:
    """Test the resource sampling functionality."""

    def test_sampler_start_stop(self):
        """Test starting and stopping the sampler."""
        sampler = ResourceSampler(interval=0.1)

        sampler.start()
        time.sleep(0.3)  # Let it collect a few samples
        metrics = sampler.stop()

        assert "cpu.avg_load" in metrics
        assert "cpu.max_load" in metrics
        assert "ram.peak_mb" in metrics
        assert "ram.avg_mb" in metrics

        # Values should be reasonable
        assert 0 <= metrics["cpu.avg_load"] <= 100
        assert 0 <= metrics["cpu.max_load"] <= 100
        assert metrics["ram.peak_mb"] > 0
        assert metrics["ram.avg_mb"] > 0

    def test_sampler_multiple_start_stop(self):
        """Test that multiple start/stop cycles work correctly."""
        sampler = ResourceSampler(interval=0.05)

        # First cycle
        sampler.start()
        time.sleep(0.1)
        metrics1 = sampler.stop()

        # Second cycle
        sampler.start()
        time.sleep(0.1)
        metrics2 = sampler.stop()

        # Both should have metrics
        assert len(metrics1) > 0
        assert len(metrics2) > 0

    def test_get_current_stats(self):
        """Test getting current resource stats."""
        sampler = ResourceSampler()
        stats = sampler.get_current_stats()

        assert "cpu.current_load" in stats
        assert "ram.current_mb" in stats
        assert stats["ram.current_mb"] > 0


class TestUtils:
    """Test utility functions."""

    def test_get_directory_size_mb(self, tmp_path):
        """Test directory size calculation."""
        # Empty directory
        assert get_directory_size_mb(tmp_path) == 0.0

        # Create some test files
        (tmp_path / "file1.txt").write_text("x" * 1024)  # 1KB
        (tmp_path / "file2.txt").write_text("x" * 2048)  # 2KB

        size_mb = get_directory_size_mb(tmp_path)
        expected_mb = 3.0 / 1024  # 3KB in MB
        assert abs(size_mb - expected_mb) < 0.01  # Allow small floating point differences

        # Non-existent directory
        assert get_directory_size_mb(tmp_path / "nonexistent") == 0.0

    def test_find_latest_wheel(self, tmp_path):
        """Test finding the latest wheel file."""
        # No wheel files
        assert find_latest_wheel(tmp_path, "test-package") is None

        # Create mock wheel files
        wheel1 = tmp_path / "test_package-1.0.0-py3-none-any.whl"
        wheel2 = tmp_path / "test_package-1.1.0-py3-none-any.whl"

        wheel1.write_text("content1")
        time.sleep(0.01)  # Ensure different mtime
        wheel2.write_text("content2")

        # Should find the latest one
        result = find_latest_wheel(tmp_path, "test-package")
        assert result is not None
        wheel_path, size_mb = result
        assert wheel_path.name == "test_package-1.1.0-py3-none-any.whl"
        assert size_mb > 0


class TestGlobalAPI:
    """Test the global API functions."""

    def test_global_record_and_flush(self, tmp_path):
        """Test the global record and flush functions."""
        # Mock the global collector to use our test path
        with patch("panther.metrics.core._global_collector", None):
            with patch("panther.metrics.core.MetricsCollector") as mock_collector_class:
                mock_collector = Mock()
                mock_collector_class.return_value = mock_collector

                # Test recording
                record("test.metric", 42.0, {"tag": "value"})
                mock_collector.record.assert_called_once_with("test.metric", 42.0, {"tag": "value"})

                # Test flushing
                mock_collector.flush.return_value = "test-run-id"
                run_id = flush("test", {"extra": "data"})

                mock_collector.flush.assert_called_once_with("test", {"extra": "data"})
                assert run_id == "test-run-id"


@pytest.mark.slow
class TestIntegration:
    """Integration tests for the metrics system."""

    def test_full_workflow(self, tmp_path):
        """Test a complete metrics collection workflow."""
        collector = MetricsCollector(tmp_path)

        # Simulate a build process
        start_time = time.time()

        # Record some metrics
        collector.record("build.start_time", start_time)
        collector.record("build.dependencies", 15.0, {"stage": "install"})

        # Simulate some work
        time.sleep(0.1)

        collector.record("build.compile_time", 5.5, {"stage": "compile"})
        collector.record("artifact.size_mb", 10.2)

        # Flush the metrics
        run_id = collector.flush("build", {"config_hash": "abc123", "git_commit": "def456"})

        # Verify the data was stored correctly
        storage = JSONLinesStorage(tmp_path)
        record = storage.get_record_by_id(run_id)

        assert record is not None
        assert record["type"] == "build"
        assert record["config_hash"] == "abc123"
        assert record["git_commit"] == "def456"
        assert len(record["metrics"]) == 4
        assert record["metrics"]["artifact.size_mb"] == 10.2
        assert record["tags"]["build.dependencies"] == {"stage": "install"}

    def test_resource_sampling_integration(self, tmp_path):
        """Test resource sampling integrated with metrics collection."""
        sampler = ResourceSampler(interval=0.05)
        collector = MetricsCollector(tmp_path)

        # Start sampling
        sampler.start()

        # Simulate some work
        time.sleep(0.2)

        # Stop sampling and record metrics
        resource_metrics = sampler.stop()
        for name, value in resource_metrics.items():
            collector.record(name, value, {"stage": "test"})

        # Flush and verify
        run_id = collector.flush("test")

        storage = JSONLinesStorage(tmp_path)
        record = storage.get_record_by_id(run_id)

        assert record is not None
        assert "cpu.avg_load" in record["metrics"]
        assert "ram.peak_mb" in record["metrics"]
