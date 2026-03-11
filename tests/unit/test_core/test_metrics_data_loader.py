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
            "initialization": {
                "total_time": 2.1,
                "count": 1,
                "errors": 0,
                "success_rate": 1.0,
            },
            "execution": {
                "total_time": 38.0,
                "count": 3,
                "errors": 1,
                "success_rate": 0.67,
            },
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
                {
                    "name": "cpu_percent",
                    "value": 35.2,
                    "timestamp": 1705312100.0,
                    "component": "resource_monitor",
                },
                {
                    "name": "cpu_percent",
                    "value": 40.1,
                    "timestamp": 1705312110.0,
                    "component": "resource_monitor",
                },
            ],
            "errors": [
                {
                    "name": "error_occurred",
                    "metric_type": "error",
                    "value": 1,
                    "timestamp": 1705312200.0,
                    "metadata": {
                        "error_type": "timeout",
                        "error_message": "Connection timed out",
                    },
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
        os.utime(older, (1000, 1000))
        os.utime(newer, (2000, 2000))

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

    def test_no_false_positive_error_data_for_unrelated_metrics(
        self, sample_metrics_json
    ):
        """Regression: 'name.lower() in "error"' matched substrings like 'e', 'or', 'r'."""
        loader = MetricsDataLoader()
        for name in ("e", "or", "r", "ro", "rr", "cpu_usage"):
            values = loader.get_metric_values(sample_metrics_json, name)
            error_sources = [v for v in values if v.get("source") == "error_metrics"]
            assert (
                error_sources == []
            ), f"Metric '{name}' should not return error_metrics data"


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


class TestDataLoaderEdgeCases:
    """Edge cases: partial data, empty files, malformed structures."""

    def test_empty_json_object_loads_successfully(self, tmp_path):
        """A metrics.json containing {} should load without error."""
        exp_dir = tmp_path / "empty_json_exp"
        metrics_dir = exp_dir / "metrics"
        metrics_dir.mkdir(parents=True)
        with open(metrics_dir / "metrics.json", "w") as f:
            json.dump({}, f)

        loader = MetricsDataLoader(output_dir=tmp_path)
        data, path = loader.load_metrics(experiment_dir=exp_dir)
        assert data is not None
        assert data == {}
        assert path == exp_dir

    def test_empty_json_available_metrics(self):
        """get_available_metrics with empty dict returns empty list."""
        loader = MetricsDataLoader()
        available = loader.get_available_metrics({})
        assert available == []

    def test_empty_json_get_summary(self):
        """get_summary with empty dict returns empty/minimal summary."""
        loader = MetricsDataLoader()
        summary = loader.get_summary({})
        assert isinstance(summary, dict)

    def test_empty_json_get_metric_values(self):
        """get_metric_values with empty dict returns empty list."""
        loader = MetricsDataLoader()
        values = loader.get_metric_values({}, "anything")
        assert values == []

    def test_partial_structure_missing_sections(self):
        """Data with only some sections should not crash."""
        loader = MetricsDataLoader()
        partial = {
            "timing_metrics": {"build": 5.0},
            # No resource_metrics, error_metrics, etc.
        }
        available = loader.get_available_metrics(partial)
        assert len(available) >= 1
        names = [m["name"] for m in available]
        assert "build" in names

    def test_partial_structure_get_summary(self):
        """get_summary with partial data should still produce valid output."""
        loader = MetricsDataLoader()
        partial = {
            "summary": {
                "total_experiments": 5,
                "successful_experiments": 3,
                "failed_experiments": 2,
            },
        }
        summary = loader.get_summary(partial)
        assert summary["total_experiments"] == 5

    def test_metrics_dir_exists_but_no_json(self, tmp_path):
        """Experiment dir with metrics/ folder but no metrics.json inside."""
        exp_dir = tmp_path / "no_json_exp"
        metrics_dir = exp_dir / "metrics"
        metrics_dir.mkdir(parents=True)
        # No metrics.json created

        loader = MetricsDataLoader(output_dir=tmp_path)
        data, path = loader.load_metrics(experiment_dir=exp_dir)
        assert data is None
        assert path == exp_dir

    def test_metrics_json_is_empty_file(self, tmp_path):
        """metrics.json that is a zero-byte file should return None."""
        exp_dir = tmp_path / "empty_file_exp"
        metrics_dir = exp_dir / "metrics"
        metrics_dir.mkdir(parents=True)
        (metrics_dir / "metrics.json").write_text("")

        loader = MetricsDataLoader(output_dir=tmp_path)
        data, path = loader.load_metrics(experiment_dir=exp_dir)
        assert data is None
        assert path == exp_dir

    def test_metrics_json_is_array_not_object(self, tmp_path):
        """metrics.json containing a JSON array instead of object."""
        exp_dir = tmp_path / "array_exp"
        metrics_dir = exp_dir / "metrics"
        metrics_dir.mkdir(parents=True)
        with open(metrics_dir / "metrics.json", "w") as f:
            json.dump([1, 2, 3], f)

        loader = MetricsDataLoader(output_dir=tmp_path)
        data, path = loader.load_metrics(experiment_dir=exp_dir)
        # Should load successfully (JSON is valid)
        assert data is not None
        assert path == exp_dir

    def test_nonexistent_output_dir(self):
        """Output dir that doesn't exist should return empty results."""
        loader = MetricsDataLoader(output_dir="/nonexistent/path/to/outputs")
        assert loader.find_latest_experiment() is None
        assert loader.find_experiments_with_metrics() == []
        data, path = loader.load_metrics()
        assert data is None
        assert path is None

    def test_resource_metrics_with_none_values(self):
        """Resource metrics containing None values should not crash."""
        loader = MetricsDataLoader()
        data = {
            "resource_metrics": {
                "cpu_usage": {"average": None, "peak": None, "min": None},
                "memory_usage": None,
                "samples_count": 0,
            },
        }
        summary = loader.get_summary(data)
        assert isinstance(summary, dict)

    def test_raw_metrics_with_unexpected_types(self):
        """raw_metrics sections with unexpected value types should not crash."""
        loader = MetricsDataLoader()
        data = {
            "raw_metrics": {
                "counters": {"test": "not_a_number"},
                "gauges": {"gauge": None},
                "histograms": {"hist": "invalid"},
                "resource_metrics": "not_a_list",
                "errors": "not_a_list",
            },
        }
        available = loader.get_available_metrics(data)
        assert isinstance(available, list)

    def test_phase_metrics_with_non_dict_values(self):
        """phase_metrics with non-dict phase entries should not crash."""
        loader = MetricsDataLoader()
        data = {
            "phase_metrics": {
                "setup": "invalid",
                "execution": {"total_time": 10, "count": 2},
            },
        }
        available = loader.get_available_metrics(data)
        phase_items = [m for m in available if m["category"] == "phase"]
        # Only "execution" should be included (count > 0)
        assert len(phase_items) == 1
        assert phase_items[0]["name"] == "execution"


class TestGetStatCards:
    """Tests for MetricsDataLoader.get_stat_cards()."""

    def test_returns_four_cards(self, sample_metrics_json):
        cards = MetricsDataLoader.get_stat_cards(sample_metrics_json)
        assert len(cards) == 4

    def test_card_titles(self, sample_metrics_json):
        cards = MetricsDataLoader.get_stat_cards(sample_metrics_json)
        titles = [c["title"] for c in cards]
        assert titles == [
            "Total Experiments",
            "Success Rate",
            "Total Execution Time",
            "Error Count",
        ]

    def test_total_experiments_value(self, sample_metrics_json):
        cards = MetricsDataLoader.get_stat_cards(sample_metrics_json)
        card = {c["title"]: c for c in cards}
        assert card["Total Experiments"]["value"] == 1
        assert card["Total Experiments"]["color"] == "blue"

    def test_success_rate_calculated_correctly(self, sample_metrics_json):
        cards = MetricsDataLoader.get_stat_cards(sample_metrics_json)
        card = {c["title"]: c for c in cards}
        # 1 successful / max(1 total, 1) * 100 = 100.0%
        assert card["Success Rate"]["value"] == "100.0%"
        # success (1) > failed (0) -> green
        assert card["Success Rate"]["color"] == "green"

    def test_success_rate_red_when_more_failures(self):
        data = {
            "summary": {
                "total_experiments": 10,
                "successful_experiments": 3,
                "failed_experiments": 7,
                "error_count": 0,
                "total_execution_time": 10.0,
            }
        }
        cards = MetricsDataLoader.get_stat_cards(data)
        card = {c["title"]: c for c in cards}
        assert card["Success Rate"]["value"] == "30.0%"
        assert card["Success Rate"]["color"] == "red"

    def test_execution_time_formatted(self, sample_metrics_json):
        cards = MetricsDataLoader.get_stat_cards(sample_metrics_json)
        card = {c["title"]: c for c in cards}
        assert card["Total Execution Time"]["value"] == "42.50s"
        assert card["Total Execution Time"]["color"] == "purple"

    def test_error_count_green_when_zero(self):
        data = {
            "summary": {
                "total_experiments": 1,
                "successful_experiments": 1,
                "failed_experiments": 0,
                "error_count": 0,
                "total_execution_time": 5.0,
            }
        }
        cards = MetricsDataLoader.get_stat_cards(data)
        card = {c["title"]: c for c in cards}
        assert card["Error Count"]["value"] == 0
        assert card["Error Count"]["color"] == "green"

    def test_error_count_red_when_nonzero(self, sample_metrics_json):
        cards = MetricsDataLoader.get_stat_cards(sample_metrics_json)
        card = {c["title"]: c for c in cards}
        assert card["Error Count"]["value"] == 1
        assert card["Error Count"]["color"] == "red"

    def test_empty_summary_defaults(self):
        cards = MetricsDataLoader.get_stat_cards({})
        card = {c["title"]: c for c in cards}
        assert card["Total Experiments"]["value"] == 0
        assert card["Success Rate"]["value"] == "0.0%"
        assert card["Error Count"]["value"] == 0


class TestGetTimeseries:
    """Tests for MetricsDataLoader.get_timeseries()."""

    def test_groups_by_rounded_timestamp(self, sample_metrics_json):
        ts = MetricsDataLoader.get_timeseries(sample_metrics_json)
        # sample_metrics_json has two cpu_percent entries at timestamps
        # 1705312100.0 and 1705312110.0 -> rounded to 1705312100 and 1705312110
        assert len(ts) == 2
        assert ts[0]["timestamp"] < ts[1]["timestamp"]

    def test_entries_contain_metric_values(self, sample_metrics_json):
        ts = MetricsDataLoader.get_timeseries(sample_metrics_json)
        assert ts[0]["cpu_percent"] == 35.2
        assert ts[1]["cpu_percent"] == 40.1

    def test_multiple_metrics_at_same_timestamp(self):
        data = {
            "raw_metrics": {
                "resource_metrics": [
                    {
                        "name": "cpu_percent",
                        "value": 50.0,
                        "timestamp": 1000.0,
                        "component": "resource_monitor",
                    },
                    {
                        "name": "memory_percent",
                        "value": 70.0,
                        "timestamp": 1000.0,
                        "component": "resource_monitor",
                    },
                ]
            }
        }
        ts = MetricsDataLoader.get_timeseries(data)
        assert len(ts) == 1
        assert ts[0]["cpu_percent"] == 50.0
        assert ts[0]["memory_percent"] == 70.0
        assert ts[0]["timestamp"] == 1000

    def test_sorted_by_timestamp(self):
        data = {
            "raw_metrics": {
                "resource_metrics": [
                    {"name": "cpu", "value": 10, "timestamp": 3000.0},
                    {"name": "cpu", "value": 20, "timestamp": 1000.0},
                    {"name": "cpu", "value": 30, "timestamp": 2000.0},
                ]
            }
        }
        ts = MetricsDataLoader.get_timeseries(data)
        timestamps = [e["timestamp"] for e in ts]
        assert timestamps == [1000, 2000, 3000]

    def test_empty_resource_metrics_returns_empty(self):
        assert MetricsDataLoader.get_timeseries({}) == []
        assert MetricsDataLoader.get_timeseries({"raw_metrics": {}}) == []
        assert (
            MetricsDataLoader.get_timeseries({"raw_metrics": {"resource_metrics": []}})
            == []
        )

    def test_non_list_resource_metrics_returns_empty(self):
        data = {"raw_metrics": {"resource_metrics": "invalid"}}
        assert MetricsDataLoader.get_timeseries(data) == []

    def test_non_dict_raw_metrics_returns_empty(self):
        data = {"raw_metrics": "invalid"}
        assert MetricsDataLoader.get_timeseries(data) == []

    def test_skips_entries_without_timestamp(self):
        data = {
            "raw_metrics": {
                "resource_metrics": [
                    {"name": "cpu", "value": 10, "timestamp": 1000.0},
                    {"name": "cpu", "value": 20},  # no timestamp
                ]
            }
        }
        ts = MetricsDataLoader.get_timeseries(data)
        assert len(ts) == 1

    def test_skips_entries_with_none_value(self):
        data = {
            "raw_metrics": {
                "resource_metrics": [
                    {"name": "cpu", "value": None, "timestamp": 1000.0},
                    {"name": "mem", "value": 80.0, "timestamp": 1000.0},
                ]
            }
        }
        ts = MetricsDataLoader.get_timeseries(data)
        assert len(ts) == 1
        assert "cpu" not in ts[0]
        assert ts[0]["mem"] == 80.0

    def test_skips_non_dict_entries(self):
        data = {
            "raw_metrics": {
                "resource_metrics": [
                    "not_a_dict",
                    {"name": "cpu", "value": 10, "timestamp": 1000.0},
                ]
            }
        }
        ts = MetricsDataLoader.get_timeseries(data)
        assert len(ts) == 1


class TestGetPerformanceInsights:
    """Tests for MetricsDataLoader.get_performance_insights()."""

    def test_excellent_score_no_errors_no_alerts(self):
        data = {
            "summary": {
                "total_experiments": 5,
                "failed_experiments": 0,
                "error_count": 0,
            },
            "timing_metrics": {"setup": 2.0, "test": 5.0},
            "resource_metrics": {
                "cpu_usage": {"average": 40, "peak": 60},
                "memory_usage": {"average": 50, "peak": 70},
            },
        }
        insights = MetricsDataLoader.get_performance_insights(data)
        assert insights["performance_score"] == "excellent"
        assert insights["bottlenecks"] == []
        assert insights["alerts"] == []
        assert insights["recommendations"] == []

    def test_bottleneck_detected_for_slow_operation(self):
        data = {
            "summary": {"error_count": 0},
            "timing_metrics": {
                "fast_op": 3.0,
                "slow_build_duration": 25.0,
            },
        }
        insights = MetricsDataLoader.get_performance_insights(data)
        assert len(insights["bottlenecks"]) == 1
        bottleneck = insights["bottlenecks"][0]
        assert bottleneck["operation"] == "slow_build"
        assert bottleneck["average_time"] == 25.0
        assert bottleneck["total_time"] == 25.0
        assert bottleneck["call_count"] == 1

    def test_multiple_bottlenecks(self):
        data = {
            "summary": {"error_count": 0},
            "timing_metrics": {
                "op_a_duration": 15.0,
                "op_b_duration": 20.0,
                "op_c": 2.0,
            },
        }
        insights = MetricsDataLoader.get_performance_insights(data)
        assert len(insights["bottlenecks"]) == 2
        ops = {b["operation"] for b in insights["bottlenecks"]}
        assert "op_a" in ops
        assert "op_b" in ops

    def test_critical_cpu_alert(self):
        data = {
            "summary": {"error_count": 0},
            "resource_metrics": {
                "cpu_usage": {"average": 50, "peak": 98},
                "memory_usage": {"average": 50, "peak": 70},
            },
        }
        insights = MetricsDataLoader.get_performance_insights(data)
        assert any("CPU usage reached 95%" in a for a in insights["alerts"])
        assert any("CPU-intensive" in r for r in insights["recommendations"])

    def test_warning_high_avg_cpu(self):
        data = {
            "summary": {"error_count": 0},
            "resource_metrics": {
                "cpu_usage": {"average": 85, "peak": 90},
                "memory_usage": {"average": 50, "peak": 70},
            },
        }
        insights = MetricsDataLoader.get_performance_insights(data)
        assert any("High average CPU" in a for a in insights["alerts"])

    def test_critical_memory_alert(self):
        data = {
            "summary": {"error_count": 0},
            "resource_metrics": {
                "cpu_usage": {"average": 30, "peak": 50},
                "memory_usage": {"average": 60, "peak": 97},
            },
        }
        insights = MetricsDataLoader.get_performance_insights(data)
        assert any("Memory usage reached 95%" in a for a in insights["alerts"])
        assert any("memory usage" in r for r in insights["recommendations"])

    def test_warning_high_avg_memory(self):
        data = {
            "summary": {"error_count": 0},
            "resource_metrics": {
                "cpu_usage": {"average": 30, "peak": 50},
                "memory_usage": {"average": 85, "peak": 90},
            },
        }
        insights = MetricsDataLoader.get_performance_insights(data)
        assert any("High average memory" in a for a in insights["alerts"])

    def test_high_failure_rate_alert(self):
        data = {
            "summary": {
                "total_experiments": 10,
                "failed_experiments": 5,
                "error_count": 0,
            },
        }
        insights = MetricsDataLoader.get_performance_insights(data)
        assert any("failure rate" in a.lower() for a in insights["alerts"])

    def test_poor_score_with_errors(self):
        data = {
            "summary": {"error_count": 3},
        }
        insights = MetricsDataLoader.get_performance_insights(data)
        assert insights["performance_score"] == "poor"

    def test_good_score_few_alerts_no_errors(self):
        data = {
            "summary": {"error_count": 0},
            "resource_metrics": {
                "cpu_usage": {"average": 85, "peak": 90},
                "memory_usage": {"average": 50, "peak": 70},
            },
        }
        insights = MetricsDataLoader.get_performance_insights(data)
        # 1 alert (high avg CPU) but no errors -> "good"
        assert insights["performance_score"] == "good"

    def test_fair_score_many_alerts_no_errors(self):
        data = {
            "summary": {
                "total_experiments": 10,
                "failed_experiments": 5,
                "error_count": 0,
            },
            "resource_metrics": {
                "cpu_usage": {"average": 85, "peak": 98},
                "memory_usage": {"average": 85, "peak": 98},
            },
        }
        insights = MetricsDataLoader.get_performance_insights(data)
        # Critical CPU, critical memory, high failure rate = 5 alerts + recs -> "fair"
        assert len(insights["alerts"]) >= 3
        assert insights["performance_score"] == "fair"

    def test_empty_data_returns_unknown(self):
        insights = MetricsDataLoader.get_performance_insights({})
        assert insights["performance_score"] == "excellent"
        assert insights["bottlenecks"] == []
        assert insights["alerts"] == []
        assert insights["recommendations"] == []

    def test_non_numeric_timing_values_ignored(self):
        data = {
            "summary": {"error_count": 0},
            "timing_metrics": {
                "valid_duration": 15.0,
                "invalid": "not_a_number",
            },
        }
        insights = MetricsDataLoader.get_performance_insights(data)
        assert len(insights["bottlenecks"]) == 1
        assert insights["bottlenecks"][0]["operation"] == "valid"

    def test_non_dict_resource_metrics_handled(self):
        data = {
            "summary": {"error_count": 0},
            "resource_metrics": "invalid",
        }
        insights = MetricsDataLoader.get_performance_insights(data)
        assert insights["alerts"] == []
