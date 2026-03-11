"""Selenium-based integration tests for the Dashboard page (/).

Uses NiceGUI's ``screen`` fixture (real Chrome via Selenium).
Run with: pytest tests/integration/test_dashboard_browser.py -m integration -x
"""

import pytest
from nicegui import app, ui
from nicegui.testing.screen import Screen

from tests.integration.conftest import FakePluginMetadata

pytestmark = [pytest.mark.integration]


def _setup_dashboard(mock_plugin_service, mock_results_service, screen):
    """Register dashboard page and open it."""
    from panther.webapp.pages import dashboard

    app.storage.general["config_path"] = None
    app.storage.general["output_dir"] = "/tmp/test_outputs"

    @ui.page("/")
    def page():
        dashboard.content()

    screen.open("/")


def test_dashboard_renders_title_and_stats(
    screen: Screen, mock_plugin_service, mock_results_service
):
    """Page shows 'Overview' and stat cards."""
    _setup_dashboard(mock_plugin_service, mock_results_service, screen)
    screen.should_contain("Overview")
    screen.should_contain("Plugins")
    screen.should_contain("Past Experiments")
    screen.should_contain("Loaded Config")


def test_dashboard_shows_plugin_count(
    screen: Screen, mock_plugin_service, mock_results_service
):
    """Mock 5 plugins — stat card shows '5'."""
    mock_plugin_service.list_plugins.return_value = [
        FakePluginMetadata(name=f"p{i}", type="services") for i in range(5)
    ]
    _setup_dashboard(mock_plugin_service, mock_results_service, screen)
    screen.should_contain("5")


def test_dashboard_shows_experiment_count(
    screen: Screen, mock_plugin_service, mock_results_service
):
    """Mock 3 experiments — stat card shows '3'."""
    mock_results_service.count_experiments.return_value = 3
    _setup_dashboard(mock_plugin_service, mock_results_service, screen)
    screen.should_contain("3")


def test_dashboard_quick_action_new_config_navigates(
    screen: Screen, mock_plugin_service, mock_results_service
):
    """Click 'New Config' navigates to /config."""

    @ui.page("/config")
    def config_page():
        ui.label("Config Builder Page")

    _setup_dashboard(mock_plugin_service, mock_results_service, screen)
    screen.click("New Config")
    screen.wait(1.0)
    screen.should_contain("Config Builder Page")


def test_dashboard_quick_action_browse_results_navigates(
    screen: Screen, mock_plugin_service, mock_results_service
):
    """Click 'Browse Results' navigates to /results."""

    @ui.page("/results")
    def results_page():
        ui.label("Results Page")

    _setup_dashboard(mock_plugin_service, mock_results_service, screen)
    screen.click("Browse Results")
    screen.wait(1.0)
    screen.should_contain("Results Page")


def test_dashboard_quick_action_view_plugins_navigates(
    screen: Screen, mock_plugin_service, mock_results_service
):
    """Click 'View Plugins' navigates to /plugins."""

    @ui.page("/plugins")
    def plugins_page():
        ui.label("Plugins Page")

    _setup_dashboard(mock_plugin_service, mock_results_service, screen)
    screen.click("View Plugins")
    screen.wait(1.0)
    screen.should_contain("Plugins Page")


def test_dashboard_empty_state(
    screen: Screen, mock_plugin_service, mock_results_service
):
    """No plugins, no results — stats show '0'."""
    mock_plugin_service.list_plugins.return_value = []
    mock_results_service.count_experiments.return_value = 0
    _setup_dashboard(mock_plugin_service, mock_results_service, screen)
    screen.should_contain("0")
    screen.should_contain("None")
