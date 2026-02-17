"""Tests for MetricsDataLoader."""

import json
import os

import pytest

from panther.core.metrics.data_loader import MetricsDataLoader


@pytest.fixture
def sample_metrics_json():
    """Minimal valid metrics JSON matching MetricsExporter schema."""
    return {
        "export_metadata": {
            "timestamp": "2025-01-15T10:30:00",
            "panther_version": "1.0.0",
            "export_format": "json",
            "include_raw_data": True,
        },
        "summary": {
            "total_experiments": 1,
            "successful_experiments": 1,
            "failed_experiments": 0,
            "total_test_cases": 3,
            "successful_test_cases": 2,
            "failed_test_cases": 1,
            "total_execution_time": 42.5,
            "average_test_duration": 14.17,
            "error_count": 1,
        },
        "timing_metrics": {
            "test_case_duration": 14.2,
            "docker_build_duration": 28.3,
        },
        "resource_metrics": {
            "cpu_usage": {"average": 35.2, "peak": 78.5, "min": 5.1},
            "memory_usage": {"average": 62.0, "peak": 85.3, "min": 40.2},
            "samples_count": 50,
        },
        "phase_metrics": {
            "initialization": {"total_time": 2.1, "count": 1, "errors": 0, "success_rate": 1.0},
            "execution": {"total_time": 38.0, "count": 3, "errors": 1, "success_rate": 0.67},
        },
        "error_metrics": {
            "total_errors": 1,
            "error_categories": {"timeout": 1},
            "error_timeline": [
                {
                    "timestamp": 1705312200.0,
                    "phase": "execution",
                    "component": "client",
                    "error_type": "timeout",
                    "error_message": "Connection timed out",
                }
            ],
        },
        "raw_metrics": {
            "timing_metrics": {"test_case_duration": 14.2},
            "counters": {"tests_passed": 2, "tests_failed": 1},
            "gauges": {"process_cpu_percent": 35.2},
            "histograms": {},
            "resource_metrics": [
                {"name": "cpu_percent", "value": 35.2, "timestamp": 1705312100.0, "component": "resource_monitor"},
                {"name": "cpu_percent", "value": 40.1, "timestamp": 1705312110.0, "component": "resource_monitor"},
            ],
            "errors": [
                {
                    "name": "error_occurred",
                    "metric_type": "error",
                    "value": 1,
                    "timestamp": 1705312200.0,
                    "metadata": {"error_type": "timeout", "error_message": "Connection timed out"},
                }
            ],
        },
    }


@pytest.fixture
def experiment_with_metrics(tmp_path, sample_metrics_json):
    """Create a fake experiment directory with metrics."""
    exp_dir = tmp_path / "2025-01-15_10-00-00_test_exp"
    metrics_dir = exp_dir / "metrics"
    metrics_dir.mkdir(parents=True)
    with open(metrics_dir / "metrics.json", "w") as f:
        json.dump(sample_metrics_json, f)
    return tmp_path, exp_dir


@pytest.fixture
def experiment_without_metrics(tmp_path):
    """Create a fake experiment directory without metrics."""
    exp_dir = tmp_path / "2025-01-15_10-00-00_no_metrics"
    exp_dir.mkdir(parents=True)
    return tmp_path, exp_dir


class TestFindLatestExperiment:
    def test_finds_latest_by_mtime(self, tmp_path):
        older = tmp_path / "older_exp"
        newer = tmp_path / "newer_exp"
        older.mkdir()
        newer.mkdir()

        loader = MetricsDataLoader(output_dir=tmp_path)
        result = loader.find_latest_experiment()
        assert result is not None
        assert result == newer

    def test_returns_none_when_empty(self, tmp_path):
        loader = MetricsDataLoader(output_dir=tmp_path)
        assert loader.find_latest_experiment() is None

    def test_returns_none_when_dir_missing(self, tmp_path):
        loader = MetricsDataLoader(output_dir=tmp_path / "nonexistent")
        assert loader.find_latest_experiment() is None


class TestFindExperimentsWithMetrics:
    def test_finds_experiments_with_metrics(self, experiment_with_metrics):
        root, exp_dir = experiment_with_metrics
        loader = MetricsDataLoader(output_dir=root)
        results = loader.find_experiments_with_metrics()
        assert len(results) == 1
        assert results[0] == exp_dir

    def test_excludes_experiments_without_metrics(self, experiment_without_metrics):
        root, _ = experiment_without_metrics
        loader = MetricsDataLoader(output_dir=root)
        results = loader.find_experiments_with_metrics()
        assert len(results) == 0

    def test_returns_empty_when_no_experiments(self, tmp_path):
        loader = MetricsDataLoader(output_dir=tmp_path)
        assert loader.find_experiments_with_metrics() == []

    def test_returns_experiments_ordered_by_mtime_descending(self, tmp_path):
        exp_a = tmp_path / "exp_a"
        exp_b = tmp_path / "exp_b"
        exp_c = tmp_path / "exp_c"

        for exp in (exp_a, exp_b, exp_c):
            metrics_dir = exp / "metrics"
            metrics_dir.mkdir(parents=True)
            with open(metrics_dir / "metrics.json", "w") as f:
                json.dump({"timing_metrics": {}}, f)

        os.utime(exp_a, (1000, 1000))
        os.utime(exp_b, (3000, 3000))
        os.utime(exp_c, (2000, 2000))

        loader = MetricsDataLoader(output_dir=tmp_path)
        result = loader.find_experiments_with_metrics()

        assert len(result) == 3
        assert result == [exp_b, exp_c, exp_a]


class TestLoadMetrics:
    def test_loads_valid_json(self, experiment_with_metrics, sample_metrics_json):
        root, exp_dir = experiment_with_metrics
        loader = MetricsDataLoader(output_dir=root)
        data, path = loader.load_metrics(experiment_dir=exp_dir)
        assert data is not None
        assert data["export_metadata"]["panther_version"] == "1.0.0"
        assert path == exp_dir

    def test_auto_discovers_latest(self, experiment_with_metrics):
        root, exp_dir = experiment_with_metrics
        loader = MetricsDataLoader(output_dir=root)
        data, path = loader.load_metrics()
        assert data is not None
        assert path == exp_dir

    def test_returns_none_for_corrupt_json(self, tmp_path):
        exp_dir = tmp_path / "corrupt_exp"
        metrics_dir = exp_dir / "metrics"
        metrics_dir.mkdir(parents=True)
        with open(metrics_dir / "metrics.json", "w") as f:
            f.write("{invalid json!!!")

        loader = MetricsDataLoader(output_dir=tmp_path)
        data, path = loader.load_metrics(experiment_dir=exp_dir)
        assert data is None
        assert path == exp_dir

    def test_returns_none_for_missing_file(self, experiment_without_metrics):
        root, exp_dir = experiment_without_metrics
        loader = MetricsDataLoader(output_dir=root)
        data, path = loader.load_metrics(experiment_dir=exp_dir)
        assert data is None
        assert path == exp_dir

    def test_returns_none_when_no_experiments(self, tmp_path):
        loader = MetricsDataLoader(output_dir=tmp_path)
        data, path = loader.load_metrics()
        assert data is None
        assert path is None

    def test_load_metrics_selects_newest_experiment(self, tmp_path):
        """load_metrics() without experiment_dir picks the newest by mtime."""
        older_exp = tmp_path / "older_exp"
        newer_exp = tmp_path / "newer_exp"

        for exp, value in ((older_exp, 1.0), (newer_exp, 9.9)):
            metrics_dir = exp / "metrics"
            metrics_dir.mkdir(parents=True)
            with open(metrics_dir / "metrics.json", "w") as f:
                json.dump({"timing_metrics": {"marker": value}}, f)

        os.utime(older_exp, (1000, 1000))
        os.utime(newer_exp, (2000, 2000))

        loader = MetricsDataLoader(output_dir=tmp_path)
        data, path = loader.load_metrics()

        assert data is not None
        assert path == newer_exp
        assert data["timing_metrics"]["marker"] == 9.9

    def test_load_metrics_returns_none_when_latest_is_corrupt(self, tmp_path):
        older_exp = tmp_path / "older_exp"
        older_metrics_dir = older_exp / "metrics"
        older_metrics_dir.mkdir(parents=True)
        with open(older_metrics_dir / "metrics.json", "w") as f:
            json.dump({"timing_metrics": {"test": 1.0}}, f)

        newer_exp = tmp_path / "newer_exp"
        newer_metrics_dir = newer_exp / "metrics"
        newer_metrics_dir.mkdir(parents=True)
        with open(newer_metrics_dir / "metrics.json", "w") as f:
            f.write("not valid json{")

        os.utime(older_exp, (1000, 1000))
        os.utime(newer_exp, (2000, 2000))

        loader = MetricsDataLoader(output_dir=tmp_path)
        data, path = loader.load_metrics()

        # The loader picks the latest experiment (newer_exp) and returns None
        # for corrupt data without falling back to older experiments.
        assert data is None
        assert path == newer_exp


class TestGetAvailableMetrics:
    def test_extracts_timing_metrics(self, sample_metrics_json):
        loader = MetricsDataLoader()
        available = loader.get_available_metrics(sample_metrics_json)
        timing_names = [m["name"] for m in available if m["category"] == "timing"]
        assert "test_case_duration" in timing_names
        assert "docker_build_duration" in timing_names

    def test_extracts_resource_metrics(self, sample_metrics_json):
        loader = MetricsDataLoader()
        available = loader.get_available_metrics(sample_metrics_json)
        resource_names = [m["name"] for m in available if m["category"] == "resource"]
        assert "cpu_usage" in resource_names
        assert "memory_usage" in resource_names

    def test_extracts_phase_metrics(self, sample_metrics_json):
        loader = MetricsDataLoader()
        available = loader.get_available_metrics(sample_metrics_json)
        phase_names = [m["name"] for m in available if m["category"] == "phase"]
        assert "execution" in phase_names

    def test_extracts_error_metrics(self, sample_metrics_json):
        loader = MetricsDataLoader()
        available = loader.get_available_metrics(sample_metrics_json)
        error_names = [m["name"] for m in available if m["category"] == "error"]
        assert "errors" in error_names

    def test_extracts_raw_counters_and_gauges(self, sample_metrics_json):
        loader = MetricsDataLoader()
        available = loader.get_available_metrics(sample_metrics_json)
        counter_names = [m["name"] for m in available if m["category"] == "counters"]
        assert "tests_passed" in counter_names
        assert "tests_failed" in counter_names
        gauge_names = [m["name"] for m in available if m["category"] == "gauges"]
        assert "process_cpu_percent" in gauge_names

    def test_handles_empty_data(self):
        loader = MetricsDataLoader()
        available = loader.get_available_metrics({})
        assert available == []


class TestGetMetricValues:
    def test_gets_timing_values(self, sample_metrics_json):
        loader = MetricsDataLoader()
        values = loader.get_metric_values(sample_metrics_json, "test_case_duration")
        assert len(values) >= 1
        assert values[0]["value"] == 14.2
        assert values[0]["type"] == "timing"

    def test_gets_resource_breakdown(self, sample_metrics_json):
        loader = MetricsDataLoader()
        values = loader.get_metric_values(sample_metrics_json, "cpu_usage")
        assert len(values) >= 1
        names = [v["name"] for v in values]
        assert any("average" in n for n in names)

    def test_gets_raw_resource_timeseries(self, sample_metrics_json):
        loader = MetricsDataLoader()
        values = loader.get_metric_values(sample_metrics_json, "cpu_percent")
        assert len(values) >= 2
        assert all(v.get("timestamp") is not None for v in values)

    def test_gets_counter_values(self, sample_metrics_json):
        loader = MetricsDataLoader()
        values = loader.get_metric_values(sample_metrics_json, "tests_passed")
        assert len(values) == 1
        assert values[0]["value"] == 2

    def test_respects_limit(self, sample_metrics_json):
        loader = MetricsDataLoader()
        values = loader.get_metric_values(sample_metrics_json, "cpu_percent", limit=1)
        assert len(values) <= 1

    def test_returns_empty_for_unknown(self, sample_metrics_json):
        loader = MetricsDataLoader()
        values = loader.get_metric_values(sample_metrics_json, "nonexistent_metric")
        assert values == []


class TestGetSummary:
    def test_includes_export_metadata(self, sample_metrics_json):
        loader = MetricsDataLoader()
        summary = loader.get_summary(sample_metrics_json)
        assert summary["export_timestamp"] == "2025-01-15T10:30:00"

    def test_includes_experiment_stats(self, sample_metrics_json):
        loader = MetricsDataLoader()
        summary = loader.get_summary(sample_metrics_json)
        assert summary["total_experiments"] == 1
        assert summary["error_count"] == 1

    def test_includes_timing_stats(self, sample_metrics_json):
        loader = MetricsDataLoader()
        summary = loader.get_summary(sample_metrics_json)
        assert summary["timing_metric_count"] == 2

    def test_includes_resource_stats(self, sample_metrics_json):
        loader = MetricsDataLoader()
        summary = loader.get_summary(sample_metrics_json)
        assert "avg_cpu" in summary
        assert "peak_cpu" in summary
        assert "avg_memory" in summary

    def test_includes_error_stats(self, sample_metrics_json):
        loader = MetricsDataLoader()
        summary = loader.get_summary(sample_metrics_json)
        assert summary["total_errors"] == 1
        assert summary["error_categories"] == {"timeout": 1}

    def test_handles_empty_data(self):
        loader = MetricsDataLoader()
        summary = loader.get_summary({})
        # Empty input may still produce zero-value defaults from resource/error checks
        assert "export_timestamp" not in summary
        assert "total_experiments" not in summary
