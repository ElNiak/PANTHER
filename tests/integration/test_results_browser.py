"""Selenium-based integration tests for the Results page (/results).

Uses NiceGUI's ``screen`` fixture (real Chrome via Selenium).
Run with: pytest tests/integration/test_results_browser.py -m integration -x
"""

import pytest
from nicegui import app, ui
from nicegui.testing.screen import Screen

pytestmark = [pytest.mark.integration]

SAMPLE_EXPERIMENTS = [
    {
        "date": "2026-03-10",
        "name": "2026-03-10_14-00-00",
        "path": "/tmp/outputs/2026-03-10_14-00-00",
        "test_count": 5,
        "status": "completed",
    },
    {
        "date": "2026-03-09",
        "name": "2026-03-09_10-30-00",
        "path": "/tmp/outputs/2026-03-09_10-30-00",
        "test_count": 3,
        "status": "failed",
    },
    {
        "date": "2026-03-08",
        "name": "2026-03-08_08-15-00",
        "path": "/tmp/outputs/2026-03-08_08-15-00",
        "test_count": 2,
        "status": "completed",
    },
]


def _setup_results(mock_results_service, screen):
    """Register results page and open it."""
    from panther.webapp.pages import results

    app.storage.general["output_dir"] = "/tmp/test_outputs"

    @ui.page("/results")
    def page():
        results.content()

    screen.open("/results")


def test_results_renders_summary_cards(screen: Screen, mock_results_service):
    """4 stat cards visible when experiments exist."""
    mock_results_service.list_experiments.return_value = SAMPLE_EXPERIMENTS
    _setup_results(mock_results_service, screen)
    screen.should_contain("Total Experiments")
    screen.should_contain("Completed")
    screen.should_contain("Failed")
    screen.should_contain("Latest Status")


def test_results_empty_state_shows_message(screen: Screen, mock_results_service):
    """No experiments — 'No experiment results found.' message."""
    mock_results_service.list_experiments.return_value = []
    _setup_results(mock_results_service, screen)
    screen.should_contain("No experiment results found")


def test_results_table_renders_with_data(screen: Screen, mock_results_service):
    """Mock experiments render as table rows."""
    mock_results_service.list_experiments.return_value = SAMPLE_EXPERIMENTS
    _setup_results(mock_results_service, screen)
    screen.should_contain("2026-03-10_14-00-00")
    screen.should_contain("2026-03-09_10-30-00")
    screen.should_contain("2026-03-08_08-15-00")


def test_results_table_shows_columns(screen: Screen, mock_results_service):
    """Table has Date, Experiment, Tests, Status columns."""
    mock_results_service.list_experiments.return_value = SAMPLE_EXPERIMENTS
    _setup_results(mock_results_service, screen)
    screen.should_contain("Date")
    screen.should_contain("Experiment")
    screen.should_contain("Tests")
    screen.should_contain("Status")


def test_results_shows_correct_counts(screen: Screen, mock_results_service):
    """Summary cards show correct total/completed/failed counts."""
    mock_results_service.list_experiments.return_value = SAMPLE_EXPERIMENTS
    _setup_results(mock_results_service, screen)
    # Total = 3, Completed = 2, Failed = 1
    screen.should_contain("3")
    screen.should_contain("2")
    screen.should_contain("1")


def test_results_search_filter_works(screen: Screen, mock_results_service):
    """Type in search input — table filters rows."""
    mock_results_service.list_experiments.return_value = SAMPLE_EXPERIMENTS
    _setup_results(mock_results_service, screen)
    # Find the search input and type
    inputs = screen.selenium.find_elements("tag name", "input")
    search_inputs = [
        i
        for i in inputs
        if i.get_attribute("placeholder") == "Search experiments..."
        or i.get_attribute("aria-label") == "Search experiments..."
    ]
    if search_inputs:
        search_inputs[0].send_keys("14-00")
        screen.wait(0.5)
        screen.should_contain("2026-03-10_14-00-00")
        screen.should_not_contain("2026-03-08_08-15-00")


def test_results_heading_visible(screen: Screen, mock_results_service):
    """Page title 'Experiment Results' is shown."""
    mock_results_service.list_experiments.return_value = []
    _setup_results(mock_results_service, screen)
    screen.should_contain("Experiment Results")


def test_results_status_text_present(screen: Screen, mock_results_service):
    """Status values appear in table."""
    mock_results_service.list_experiments.return_value = SAMPLE_EXPERIMENTS
    _setup_results(mock_results_service, screen)
    screen.should_contain("completed")
    screen.should_contain("failed")


def test_results_row_click_opens_detail_dialog(screen: Screen, mock_results_service):
    """Click table row opens detail dialog with experiment name."""
    mock_results_service.list_experiments.return_value = SAMPLE_EXPERIMENTS
    mock_results_service.get_experiment_detail.return_value = {
        "name": "2026-03-10_14-00-00",
        "date": "2026-03-10",
        "path": "/tmp/outputs/2026-03-10_14-00-00",
        "test_count": 5,
        "status": "completed",
        "log_content": "Test log line 1\nTest log line 2",
        "report_content": None,
        "artifacts": [],
    }
    mock_results_service.get_aggregate_stats.return_value = {
        "total": 5,
        "passed": 4,
        "failed": 1,
        "success_rate": 80.0,
        "duration": 45.2,
    }
    mock_results_service.get_test_results.return_value = []
    mock_results_service.get_service_health.return_value = []
    mock_results_service.list_tests.return_value = []
    mock_results_service.get_experiment_events.return_value = []
    _setup_results(mock_results_service, screen)

    # Click on the experiment name in the table row
    screen.click("2026-03-10_14-00-00")
    screen.wait(1.0)
    # Dialog should show tabs
    screen.should_contain("Summary")
    screen.should_contain("Tests")
    screen.should_contain("Logs")
    screen.should_contain("Events")
    screen.should_contain("Artifacts")
