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


def test_plugins_shows_cards(screen: Screen, mock_plugin_service):
    """Plugin names appear as cards."""
    mock_plugin_service.list_plugins.return_value = [
        FakePluginMetadata(
            name="picoquic",
            type="iut",
            description="Fast QUIC implementation",
            supported_protocols=["quic", "http3"],
            capabilities=["tls", "retry"],
        ),
        FakePluginMetadata(
            name="docker_compose",
            type="network_environment",
            description="Docker-based environment",
        ),
    ]
    _setup_plugins(mock_plugin_service, screen)
    screen.should_contain("picoquic")
    screen.should_contain("docker_compose")
    screen.should_contain("Fast QUIC implementation")


def test_plugins_shows_tabs(screen: Screen, mock_plugin_service):
    """Type tabs are rendered including 'All' and relevant type tabs."""
    mock_plugin_service.list_plugins.return_value = [
        FakePluginMetadata(name="picoquic", type="iut"),
        FakePluginMetadata(name="ivy", type="tester"),
    ]
    _setup_plugins(mock_plugin_service, screen)
    screen.should_contain("All")
    screen.should_contain("IUT")
    screen.should_contain("Tester")


def test_plugins_displays_status_badge(screen: Screen, mock_plugin_service):
    """Status badge text appears on the card."""
    mock_plugin_service.list_plugins.return_value = [
        FakePluginMetadata(name="test_plugin", type="iut", status="active"),
    ]
    _setup_plugins(mock_plugin_service, screen)
    screen.should_contain("Active")


def test_plugins_displays_protocol_chips(screen: Screen, mock_plugin_service):
    """Protocol names appear as chips on the card."""
    mock_plugin_service.list_plugins.return_value = [
        FakePluginMetadata(
            name="picoquic",
            type="iut",
            supported_protocols=["quic", "http3"],
        ),
    ]
    _setup_plugins(mock_plugin_service, screen)
    screen.should_contain("quic")
    screen.should_contain("http3")


def test_plugins_displays_tags_on_card(screen: Screen, mock_plugin_service):
    """Tags from plugin metadata appear on the page."""
    mock_plugin_service.list_plugins.return_value = [
        FakePluginMetadata(
            name="picoquic",
            type="iut",
            tags=["quic", "c", "research"],
        ),
    ]
    _setup_plugins(mock_plugin_service, screen)
    screen.should_contain("picoquic")


def test_plugins_displays_dependencies_on_card(screen: Screen, mock_plugin_service):
    """Plugin and external dependency data is present."""
    mock_plugin_service.list_plugins.return_value = [
        FakePluginMetadata(
            name="picoquic",
            type="iut",
            dependencies=["quic_protocol"],
            external_dependencies=["docker", "picotls"],
        ),
    ]
    _setup_plugins(mock_plugin_service, screen)
    screen.should_contain("picoquic")
