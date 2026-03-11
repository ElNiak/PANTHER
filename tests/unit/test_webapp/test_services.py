"""Smoke tests for webapp service layer."""

import pytest


@pytest.mark.unit
class TestPluginService:
    def test_instantiation(self):
        from panther.webapp.services.plugin_service import PluginService

        svc = PluginService()
        assert svc._plugins_cache is None

    def test_list_plugins_returns_list(self):
        from panther.webapp.services.plugin_service import PluginService

        svc = PluginService()
        plugins = svc.list_plugins()
        assert isinstance(plugins, list)

    def test_list_plugins_caches(self):
        from panther.webapp.services.plugin_service import PluginService

        svc = PluginService()
        # Pre-seed the cache to test the caching code path directly,
        # avoiding plugin discovery which triggers recursion in __getattr__.
        sentinel = []
        svc._plugins_cache = sentinel
        first = svc.list_plugins()
        second = svc.list_plugins()
        assert first is second
        assert first is sentinel

    def test_get_plugin_detail_missing(self):
        from panther.webapp.services.plugin_service import PluginService

        svc = PluginService()
        assert svc.get_plugin_detail("nonexistent_plugin_xyz") is None


@pytest.mark.unit
class TestConfigService:
    def test_instantiation(self):
        from panther.webapp.services.config_service import ConfigService

        svc = ConfigService()
        assert svc is not None

    def test_get_default_yaml(self):
        from panther.webapp.services.config_service import ConfigService

        svc = ConfigService()
        yaml_content = svc.get_default_yaml()
        assert isinstance(yaml_content, str)
        assert len(yaml_content) > 100
        assert "tests:" in yaml_content or "logging:" in yaml_content

    def test_validate_yaml_valid(self, sample_yaml):
        from panther.webapp.services.config_service import ConfigService

        svc = ConfigService()
        result = svc.validate_yaml(sample_yaml)
        assert result is None

    def test_validate_yaml_invalid_syntax(self):
        from panther.webapp.services.config_service import ConfigService

        svc = ConfigService()
        result = svc.validate_yaml("  - invalid:\n    yaml: [")
        assert result is not None
        assert "syntax" in result.lower() or "error" in result.lower()

    def test_validate_yaml_missing_tests(self):
        from panther.webapp.services.config_service import ConfigService

        svc = ConfigService()
        result = svc.validate_yaml("logging:\n  level: INFO\n")
        assert result is not None
        assert "tests" in result.lower()

    def test_yaml_to_dict(self):
        from panther.webapp.services.config_service import ConfigService

        svc = ConfigService()
        data = svc.yaml_to_dict("key: value\nlist:\n  - a\n  - b\n")
        assert data == {"key": "value", "list": ["a", "b"]}

    def test_yaml_to_dict_invalid(self):
        from panther.webapp.services.config_service import ConfigService

        svc = ConfigService()
        assert svc.yaml_to_dict("  [invalid yaml") is None

    def test_dict_to_yaml(self):
        from panther.webapp.services.config_service import ConfigService

        svc = ConfigService()
        result = svc.dict_to_yaml({"key": "value"})
        assert "key: value" in result


@pytest.mark.unit
class TestResultsService:
    def test_empty_output_dir(self, tmp_path):
        from panther.webapp.services.results import ResultsService

        svc = ResultsService(str(tmp_path))
        assert svc.list_experiments() == []
        assert svc.count_experiments() == 0

    def test_nonexistent_output_dir(self, tmp_path):
        from panther.webapp.services.results import ResultsService

        svc = ResultsService(str(tmp_path / "does_not_exist"))
        assert svc.list_experiments() == []

    def test_list_experiments_with_data(self, output_dir):
        from panther.webapp.services.results import ResultsService

        svc = ResultsService(str(output_dir))
        experiments = svc.list_experiments()
        assert len(experiments) == 1
        assert experiments[0]["name"] == "2026-01-15_10-00-00"
        assert experiments[0]["status"] == "completed"
        assert experiments[0]["date"] == "2026-01-15"
        assert experiments[0]["test_count"] == 2

    def test_get_experiment_detail(self, output_dir):
        from panther.webapp.services.results import ResultsService

        svc = ResultsService(str(output_dir))
        detail = svc.get_experiment_detail("2026-01-15_10-00-00")
        assert detail is not None
        assert detail["name"] == "2026-01-15_10-00-00"
        assert detail["log_content"] is not None
        assert "core_summary" in detail
        assert detail["report_content"] is not None

    def test_get_experiment_detail_missing(self, output_dir):
        from panther.webapp.services.results import ResultsService

        svc = ResultsService(str(output_dir))
        assert svc.get_experiment_detail("nonexistent") is None

    def test_get_experiment_summary(self, output_dir):
        """Test StatusCollector integration."""
        from panther.webapp.services.results import ResultsService

        svc = ResultsService(str(output_dir))
        experiments = svc.list_experiments()
        assert len(experiments) > 0
        exp_path = experiments[0]["path"]
        summary = svc.get_experiment_summary(exp_path)
        # StatusCollector should return a dict (may be minimal since test data is sparse)
        assert summary is None or isinstance(summary, dict)

    def test_get_aggregate_stats(self, output_dir):
        from panther.webapp.services.results import ResultsService

        svc = ResultsService(str(output_dir))
        experiments = svc.list_experiments()
        exp_path = experiments[0]["path"]
        stats = svc.get_aggregate_stats(exp_path)
        assert "total" in stats
        assert "passed" in stats
        assert "failed" in stats
        assert "success_rate" in stats

    def test_get_metrics_timeseries_empty(self, tmp_path):
        from panther.webapp.services.results import ResultsService

        svc = ResultsService(str(tmp_path))
        result = svc.get_metrics_timeseries(str(tmp_path))
        assert result == []

    def test_get_metrics_timeseries_format1(self, tmp_path):
        import json

        from panther.webapp.services.results import ResultsService

        metrics = {
            "memory": {"peak_mb": 512, "avg_mb": 256},
            "timestamp": "2026-01-15T10:00:00",
        }
        (tmp_path / "metrics.json").write_text(json.dumps(metrics))
        svc = ResultsService(str(tmp_path))
        result = svc.get_metrics_timeseries(str(tmp_path))
        assert len(result) == 2
        assert any(r["metric"] == "memory.peak_mb" for r in result)

    def test_get_metrics_timeseries_format2(self, tmp_path):
        import json

        from panther.webapp.services.results import ResultsService

        metrics = {
            "resource_metrics": {
                "cpu_percent": 45.2,
                "memory_usage": {"peak": 1024},
            }
        }
        (tmp_path / "metrics_resource.json").write_text(json.dumps(metrics))
        svc = ResultsService(str(tmp_path))
        result = svc.get_metrics_timeseries(str(tmp_path))
        assert len(result) >= 2

    def test_get_service_health_empty(self, tmp_path):
        from panther.webapp.services.results import ResultsService

        svc = ResultsService(str(tmp_path))
        result = svc.get_service_health(str(tmp_path))
        assert result == []

    def test_get_experiment_summary_missing(self, tmp_path):
        from panther.webapp.services.results import ResultsService

        svc = ResultsService(str(tmp_path))
        result = svc.get_experiment_summary(str(tmp_path / "nonexistent"))
        assert result is None or isinstance(result, dict)

    def test_get_experiment_detail_fallback(self, tmp_path):
        """Test that get_experiment_detail falls back to StatusCollector when no JSON."""
        from panther.webapp.services.results import ResultsService

        # Create experiment dir WITHOUT experiment_summary.json (single-level)
        exp_dir = tmp_path / "2026-01-15_10-00-00_fallback"
        exp_dir.mkdir()
        (exp_dir / "experiment.log").write_text(
            "2026-01-15 10:00:00 INFO: Started\n2026-01-15 10:05:00 INFO: Done\n"
        )

        svc = ResultsService(str(tmp_path))
        detail = svc.get_experiment_detail("2026-01-15_10-00-00_fallback")
        assert detail is not None

    def test_list_tests(self, output_dir):
        from panther.webapp.services.results import ResultsService

        svc = ResultsService(str(output_dir))
        experiments = svc.list_experiments()
        exp_path = experiments[0]["path"]
        tests = svc.list_tests(exp_path)
        assert len(tests) == 2
        assert tests[0]["name"] == "0_test_basic"
        assert tests[0]["status"] == "passed"
        assert tests[0]["has_events"] is True
        assert tests[0]["service_count"] == 1

    def test_get_test_detail(self, output_dir):
        from panther.webapp.services.results import ResultsService

        svc = ResultsService(str(output_dir))
        experiments = svc.list_experiments()
        exp_path = experiments[0]["path"]
        detail = svc.get_test_detail(exp_path, "0_test_basic")
        assert detail is not None
        assert len(detail["services"]) == 1
        assert detail["services"][0]["service_name"] == "picoquic_server"
        assert detail["analysis"] is not None

    def test_get_test_events(self, output_dir):
        from panther.webapp.services.results import ResultsService

        svc = ResultsService(str(output_dir))
        experiments = svc.list_experiments()
        exp_path = experiments[0]["path"]
        events = svc.get_test_events(exp_path, "0_test_basic")
        assert len(events) == 2
        assert events[0]["event_type"] == "test.started"

    def test_get_service_logs(self, output_dir):
        from panther.webapp.services.results import ResultsService

        svc = ResultsService(str(output_dir))
        experiments = svc.list_experiments()
        exp_path = experiments[0]["path"]
        logs = svc.get_service_logs(exp_path, "0_test_basic", "picoquic_server")
        assert "compile" in logs
        assert logs["compile"]["stdout"] is not None

    def test_get_analysis_results(self, output_dir):
        from panther.webapp.services.results import ResultsService

        svc = ResultsService(str(output_dir))
        experiments = svc.list_experiments()
        exp_path = experiments[0]["path"]
        analysis = svc.get_analysis_results(exp_path, "0_test_basic")
        assert analysis is not None
        assert "analysis_results" in analysis

    def test_count_tests(self, output_dir):
        from panther.webapp.services.results import ResultsService

        svc = ResultsService(str(output_dir))
        experiments = svc.list_experiments()
        assert experiments[0]["test_count"] == 2

    def test_list_tests_no_summary(self, tmp_path):
        """list_tests falls back to filesystem scan when no summary JSON."""
        from panther.webapp.services.results import ResultsService

        exp_dir = tmp_path / "2026-01-15_10-00-00"
        exp_dir.mkdir()
        test_dir = exp_dir / "test_a"
        test_dir.mkdir()
        (test_dir / "test.log").write_text("log")

        svc = ResultsService(str(tmp_path))
        tests = svc.list_tests(str(exp_dir))
        assert len(tests) == 1
        assert tests[0]["name"] == "test_a"
        assert tests[0]["status"] == "unknown"


@pytest.mark.unit
class TestConfigServiceValidationRules:
    """Test the enhanced service validation rules in validate_config_detailed."""

    def _make_config(self, services):
        """Build a minimal config dict with given services."""
        return {
            "tests": [
                {
                    "name": "Test1",
                    "network_environment": {"type": "docker_compose"},
                    "services": services,
                }
            ]
        }

    def test_single_service_returns_error(self):
        from panther.webapp.services.config_service import ConfigService

        svc = ConfigService()
        data = self._make_config(
            {
                "server": {
                    "implementation": {"name": "picoquic", "type": "iut"},
                    "protocol": {"name": "quic", "role": "server"},
                }
            }
        )
        errors = svc.validate_config_detailed(data)
        error_msgs = [e.message for e in errors if e.severity == "error"]
        assert any("at least 2 services" in m.lower() for m in error_msgs)

    def test_no_tester_returns_warning(self):
        from panther.webapp.services.config_service import ConfigService

        svc = ConfigService()
        data = self._make_config(
            {
                "client": {
                    "implementation": {"name": "picoquic", "type": "iut"},
                    "protocol": {"name": "quic", "role": "client", "target": "server"},
                },
                "server": {
                    "implementation": {"name": "nginx", "type": "iut"},
                    "protocol": {"name": "quic", "role": "server"},
                },
            }
        )
        errors = svc.validate_config_detailed(data)
        warning_msgs = [e.message for e in errors if e.severity == "warning"]
        assert any("tester service" in m.lower() for m in warning_msgs)

    def test_no_iut_returns_warning(self):
        from panther.webapp.services.config_service import ConfigService

        svc = ConfigService()
        data = self._make_config(
            {
                "t1": {
                    "implementation": {"name": "ivy", "type": "testers"},
                    "protocol": {"name": "quic", "role": "client", "target": "t2"},
                },
                "t2": {
                    "implementation": {"name": "ivy", "type": "testers"},
                    "protocol": {"name": "quic", "role": "server"},
                },
            }
        )
        errors = svc.validate_config_detailed(data)
        warning_msgs = [e.message for e in errors if e.severity == "warning"]
        assert any("iut service" in m.lower() for m in warning_msgs)

    def test_missing_role_counterpart_warning(self):
        from panther.webapp.services.config_service import ConfigService

        svc = ConfigService()
        data = self._make_config(
            {
                "s1": {
                    "implementation": {"name": "picoquic", "type": "iut"},
                    "protocol": {"name": "quic", "role": "server"},
                },
                "s2": {
                    "implementation": {"name": "ivy", "type": "testers"},
                    "protocol": {"name": "quic", "role": "server"},
                },
            }
        )
        errors = svc.validate_config_detailed(data)
        warning_msgs = [e.message for e in errors if e.severity == "warning"]
        assert any("no client" in m for m in warning_msgs)

    def test_client_without_target_warning(self):
        from panther.webapp.services.config_service import ConfigService

        svc = ConfigService()
        data = self._make_config(
            {
                "client": {
                    "implementation": {"name": "picoquic", "type": "iut"},
                    "protocol": {"name": "quic", "role": "client"},
                },
                "server": {
                    "implementation": {"name": "ivy", "type": "testers"},
                    "protocol": {"name": "quic", "role": "server"},
                },
            }
        )
        errors = svc.validate_config_detailed(data)
        error_msgs = [e.message for e in errors if e.severity == "error"]
        assert any("must specify a target" in m.lower() for m in error_msgs)

    def test_valid_config_minimal_issues(self):
        from panther.webapp.services.config_service import ConfigService

        svc = ConfigService()
        data = self._make_config(
            {
                "server": {
                    "implementation": {"name": "picoquic", "type": "iut"},
                    "protocol": {"name": "quic", "role": "server"},
                },
                "client": {
                    "implementation": {"name": "ivy", "type": "testers"},
                    "protocol": {"name": "quic", "role": "client", "target": "server"},
                },
            }
        )
        errors = svc.validate_config_detailed(data)
        # Should have no errors and no warnings
        assert not any(e.severity == "error" for e in errors)
        assert not any(e.severity == "warning" for e in errors)


@pytest.mark.unit
class TestExperimentService:
    def test_singleton(self):
        from panther.webapp.services.experiment_service import get_experiment_service

        svc1 = get_experiment_service()
        svc2 = get_experiment_service()
        assert svc1 is svc2

    def test_initial_state(self):
        from panther.webapp.services.experiment_service import ExperimentService

        svc = ExperimentService()
        assert svc.status == "Idle"
        assert svc.is_running is False
        assert svc.log_lines == []
        assert svc.config_path == ""

    def test_register_unregister_callbacks(self):
        from panther.webapp.services.experiment_service import ExperimentService

        svc = ExperimentService()
        log_cb = lambda line: None
        status_cb = lambda s: None

        svc.register_callbacks(log_cb, status_cb)
        assert log_cb in svc._log_callbacks
        assert status_cb in svc._status_callbacks

        svc.unregister_callbacks(log_cb, status_cb)
        assert log_cb not in svc._log_callbacks
        assert status_cb not in svc._status_callbacks

    def test_unregister_nonexistent_callback(self):
        from panther.webapp.services.experiment_service import ExperimentService

        svc = ExperimentService()
        # Should not raise
        svc.unregister_callbacks(lambda x: None, lambda x: None)

    def test_emit_log(self):
        from panther.webapp.services.experiment_service import ExperimentService

        svc = ExperimentService()
        received = []
        svc.register_callbacks(lambda line: received.append(line), lambda s: None)

        svc._emit_log("test message")
        assert svc.log_lines == ["test message"]
        assert received == ["test message"]

    def test_emit_status(self):
        from panther.webapp.services.experiment_service import ExperimentService

        svc = ExperimentService()
        received = []
        svc.register_callbacks(lambda line: None, lambda s: received.append(s))

        svc._emit_status("Running")
        assert svc.status == "Running"
        assert received == ["Running"]

    def test_stop_sets_flag(self):
        from panther.webapp.services.experiment_service import ExperimentService

        svc = ExperimentService()
        svc.stop()
        assert svc._stop_requested is True

    def test_log_buffer_default(self):
        from panther.webapp.services.experiment_service import ExperimentService

        svc = ExperimentService()
        assert svc._max_log_lines == 10000

    def test_log_buffer_capped(self):
        from panther.webapp.services.experiment_service import ExperimentService

        svc = ExperimentService()
        svc._max_log_lines = 10
        for i in range(25):
            svc._emit_log(f"line {i}")
        assert len(svc._log_lines) == 10
        assert svc._log_lines[0] == "line 15"
        assert svc._log_lines[-1] == "line 24"


@pytest.mark.unit
class TestResultsServiceCaching:
    def test_get_experiment_summary_cached(self, tmp_path):
        """Second call to get_experiment_summary should use cache."""
        from unittest.mock import MagicMock, patch

        from panther.webapp.services.results import ResultsService

        svc = ResultsService(str(tmp_path))
        original_summary = {"status": "completed", "tests": {"total": 5}}

        mock_summary = MagicMock()
        mock_summary.to_dict.return_value = original_summary

        with patch(
            "panther.core.reporting.status_collector.StatusCollector"
        ) as MockCollector:
            MockCollector.return_value.collect_experiment_summary.return_value = (
                mock_summary
            )
            result1 = svc.get_experiment_summary(str(tmp_path))
            result2 = svc.get_experiment_summary(str(tmp_path))

        assert result1 == result2 == original_summary
        # StatusCollector should only be instantiated once (cached on second call)
        assert MockCollector.call_count == 1

    def test_summary_cache_initialized(self):
        from panther.webapp.services.results import ResultsService

        svc = ResultsService()
        assert svc._summary_cache == {}
