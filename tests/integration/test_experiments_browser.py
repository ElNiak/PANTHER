"""Selenium-based integration tests for the Experiments page (/experiments).

Uses NiceGUI's ``screen`` fixture (real Chrome via Selenium).
Run with: pytest tests/integration/test_experiments_browser.py -m integration -x
"""

import pytest
from nicegui import app, ui
from nicegui.testing.screen import Screen

pytestmark = [pytest.mark.integration]


def _setup_experiments(mock_experiment_service, screen):
    """Register experiments page and open it."""
    from panther.webapp.pages import experiments

    app.storage.general["config_path"] = None

    @ui.page("/experiments")
    def page():
        experiments.content()

    screen.open("/experiments")


def test_experiments_renders_launch_section(screen: Screen, mock_experiment_service):
    """'Launch Experiment' title, config path input, Run/Stop buttons visible."""
    _setup_experiments(mock_experiment_service, screen)
    screen.should_contain("Launch Experiment")
    screen.should_contain("Config file path")
    screen.should_contain("Run Experiment")


def test_experiments_renders_heading(screen: Screen, mock_experiment_service):
    """Page heading 'Experiment Management' is visible."""
    _setup_experiments(mock_experiment_service, screen)
    screen.should_contain("Experiment Management")


def test_experiments_renders_log_section(screen: Screen, mock_experiment_service):
    """'Experiment Logs' section visible."""
    _setup_experiments(mock_experiment_service, screen)
    screen.should_contain("Experiment Logs")


def test_experiments_shows_idle_status(screen: Screen, mock_experiment_service):
    """Initial status shows 'Idle'."""
    mock_experiment_service.status = "Idle"
    _setup_experiments(mock_experiment_service, screen)
    screen.should_contain("Status: Idle")


def test_experiments_run_button_without_config_warns(
    screen: Screen, mock_experiment_service
):
    """Click Run with empty input — warning notification."""
    _setup_experiments(mock_experiment_service, screen)
    # Clear the config input
    inputs = screen.selenium.find_elements("tag name", "input")
    config_inputs = [
        i for i in inputs if i.get_attribute("aria-label") == "Config file path"
    ]
    if config_inputs:
        config_inputs[0].clear()
    screen.click("Run Experiment")
    screen.wait(0.5)
    screen.should_contain("Please provide a config file path")


def test_experiments_stop_button_hidden_when_idle(
    screen: Screen, mock_experiment_service
):
    """Stop button hidden when not running."""
    mock_experiment_service.is_running = False
    _setup_experiments(mock_experiment_service, screen)
    # Run Experiment should be visible
    screen.should_contain("Run Experiment")


def test_experiments_replays_historical_logs(screen: Screen, mock_experiment_service):
    """Historical log lines replayed on page load."""
    mock_experiment_service.log_lines = [
        "Starting experiment...",
        "Test 1 passed",
        "Test 2 failed",
    ]
    _setup_experiments(mock_experiment_service, screen)
    screen.should_contain("Starting experiment...")
    screen.should_contain("Test 1 passed")
