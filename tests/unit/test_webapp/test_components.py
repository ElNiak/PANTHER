"""Tests for webapp UI components (data/logic only, no NiceGUI runtime)."""

import pytest


@pytest.mark.unit
class TestStatusBadge:
    def test_color_mapping(self):
        from panther.webapp.components.status.status_badge import _STATUS_COLORS

        assert _STATUS_COLORS["completed"] == "green"
        assert _STATUS_COLORS["failed"] == "red"
        assert _STATUS_COLORS["running"] == "amber"
        assert _STATUS_COLORS["unknown"] == "grey"

    def test_all_statuses_have_colors(self):
        from panther.webapp.components.status.status_badge import _STATUS_COLORS

        for status in [
            "completed",
            "passed",
            "failed",
            "running",
            "stopped",
            "timeout",
            "idle",
            "unknown",
        ]:
            assert status in _STATUS_COLORS


@pytest.mark.unit
class TestErrorBoundary:
    def test_import(self):
        from panther.webapp.components.status.error_boundary import error_boundary

        assert callable(error_boundary)


@pytest.mark.unit
class TestNotifications:
    def test_imports(self):
        from panther.webapp.components.status.notifications import (
            notify_error,
            notify_info,
            notify_success,
            notify_warning,
        )

        assert all(
            callable(f)
            for f in [notify_success, notify_error, notify_warning, notify_info]
        )


@pytest.mark.unit
class TestExperimentProgress:
    def test_import(self):
        from panther.webapp.components.status.progress_bar import ExperimentProgress

        assert ExperimentProgress is not None


@pytest.mark.unit
class TestComponentExports:
    def test_init_exports(self):
        from panther.webapp.components import (
            ExperimentProgress,
            error_boundary,
            notify_error,
            notify_info,
            notify_success,
            notify_warning,
            service_health_card,
            status_badge,
        )

        assert all(
            x is not None
            for x in [
                ExperimentProgress,
                error_boundary,
                notify_error,
                notify_info,
                notify_success,
                notify_warning,
                service_health_card,
                status_badge,
            ]
        )
