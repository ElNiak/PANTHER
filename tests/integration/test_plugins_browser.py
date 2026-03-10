"""Selenium-based integration tests for the Plugins page (/plugins).

Uses NiceGUI's ``screen`` fixture (real Chrome via Selenium).
Run with: pytest tests/integration/test_plugins_browser.py -m integration -x
"""

import pytest
from nicegui import ui
from nicegui.testing.screen import Screen

from tests.integration.conftest import FakePluginMetadata

pytestmark = [pytest.mark.integration]


def _setup_plugins(mock_plugin_service, screen):
    """Register plugins page and open it."""
    from panther.webapp.pages import plugins

    @ui.page("/plugins")
    def page():
        plugins.content()

    screen.open("/plugins")


def test_plugins_renders_title(screen: Screen, mock_plugin_service):
    """'Registered Plugins' heading is visible."""
    _setup_plugins(mock_plugin_service, screen)
    screen.should_contain("Registered Plugins")


def test_plugins_empty_state(screen: Screen, mock_plugin_service):
    """No plugins — empty state message shown."""
    mock_plugin_service.list_plugins.return_value = []
    _setup_plugins(mock_plugin_service, screen)
    screen.should_contain("No plugins discovered")


def test_plugins_groups_by_type(screen: Screen, mock_plugin_service):
    """Plugins grouped by type — two section headings for two types."""
    mock_plugin_service.list_plugins.return_value = [
        FakePluginMetadata(name="picoquic", type="services", description="QUIC impl"),
        FakePluginMetadata(
            name="docker_compose", type="environments", description="Docker env"
        ),
    ]
    _setup_plugins(mock_plugin_service, screen)
    screen.should_contain("Services")
    screen.should_contain("Environments")


def test_plugins_table_shows_columns(screen: Screen, mock_plugin_service):
    """Table columns Name, Protocols, Description are visible."""
    mock_plugin_service.list_plugins.return_value = [
        FakePluginMetadata(name="test_plugin", type="services"),
    ]
    _setup_plugins(mock_plugin_service, screen)
    screen.should_contain("Name")
    screen.should_contain("Protocols")
    screen.should_contain("Description")


def test_plugins_displays_plugin_data(screen: Screen, mock_plugin_service):
    """Mock plugin 'picoquic' with description shows in table."""
    mock_plugin_service.list_plugins.return_value = [
        FakePluginMetadata(
            name="picoquic",
            type="services",
            description="Fast QUIC implementation",
            supported_protocols=["quic", "http3"],
        ),
    ]
    _setup_plugins(mock_plugin_service, screen)
    screen.should_contain("picoquic")
    screen.should_contain("Fast QUIC implementation")
    screen.should_contain("quic, http3")
