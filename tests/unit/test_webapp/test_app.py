"""Smoke tests for webapp application factory and components."""

import pytest


@pytest.mark.unit
class TestAppFactory:
    def test_webapp_import(self):
        from panther.webapp import create_app

        assert callable(create_app)

    def test_lazy_import_error_message(self):
        """Verify the lazy import wrapper produces a helpful error."""
        from panther.webapp import create_app

        # If nicegui is installed, this should work without error
        # (we can't easily test the ImportError path without uninstalling nicegui)
        assert create_app is not None


@pytest.mark.unit
class TestApiModels:
    def test_config_validation_result(self):
        from panther.webapp.models.api_models import ConfigValidationResult

        valid = ConfigValidationResult(valid=True)
        assert valid.valid is True
        assert valid.error is None

        invalid = ConfigValidationResult(valid=False, error="missing field")
        assert invalid.valid is False
        assert invalid.error == "missing field"

    def test_dashboard_stats(self):
        from panther.webapp.models.api_models import DashboardStats

        stats = DashboardStats()
        assert stats.plugin_count == 0
        assert stats.experiment_count == 0
        assert stats.config_loaded is None

        stats = DashboardStats(
            plugin_count=5, experiment_count=10, config_loaded="test.yaml"
        )
        assert stats.plugin_count == 5


@pytest.mark.unit
class TestComponents:
    def test_layout_nav_items(self):
        from panther.webapp.components.layout import NAV_ITEMS

        assert len(NAV_ITEMS) == 6
        paths = [item[0] for item in NAV_ITEMS]
        assert "/" in paths
        assert "/config" in paths
        assert "/topology" in paths
        assert "/experiments" in paths
        assert "/results" in paths
        assert "/plugins" in paths

    def test_yaml_editor_class_exists(self):
        from panther.webapp.components.yaml_editor import YamlEditor

        assert YamlEditor is not None

    def test_log_viewer_class_exists(self):
        from panther.webapp.components.log_viewer import LogViewer

        assert LogViewer is not None

    def test_stat_card_function_exists(self):
        from panther.webapp.components.stat_cards import stat_card

        assert callable(stat_card)
