"""End-to-end tests for PANTHER webapp pages."""

import pytest

pytestmark = [pytest.mark.e2e, pytest.mark.asyncio]


async def test_dashboard_loads(user):
    """Dashboard renders heading and stat cards."""
    await user.open("/")
    await user.should_see("Overview")
    await user.should_see("Quick Actions")


async def test_config_builder_loads(user):
    """Config builder page renders without 500 error."""
    await user.open("/config")
    await user.should_see("Experiment Configuration Builder")


async def test_config_builder_tabs(user):
    """Config builder has both Form Editor and YAML Preview tabs."""
    await user.open("/config")
    await user.should_see("Form Editor")
    await user.should_see("YAML Preview")


async def test_experiments_page_loads(user):
    """Experiments page renders launch controls."""
    await user.open("/experiments")
    await user.should_see("Experiment Management")
    await user.should_see("Launch Experiment")


async def test_results_page_loads(user):
    """Results page renders heading (empty state with tmp_path)."""
    await user.open("/results")
    await user.should_see("Experiment Results")


async def test_plugins_page_loads(user):
    """Plugins page renders heading."""
    await user.open("/plugins")
    await user.should_see("Registered Plugins")


async def test_navigation_across_pages(user):
    """Can navigate between pages without errors."""
    await user.open("/")
    await user.should_see("Overview")

    await user.open("/config")
    await user.should_see("Experiment Configuration Builder")

    await user.open("/results")
    await user.should_see("Experiment Results")


async def test_config_validate_button_exists(user):
    """Config page has a Validate button."""
    await user.open("/config")
    await user.should_see("Validate")
