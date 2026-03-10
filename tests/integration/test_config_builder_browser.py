"""Selenium-based integration tests for the Config Builder page (/config).

Uses NiceGUI's ``screen`` fixture (real Chrome via Selenium).
Run with: pytest tests/integration/test_config_builder_browser.py -m integration -x
"""

import pytest
from nicegui import ui
from nicegui.testing.screen import Screen

pytestmark = [pytest.mark.integration]


def _setup_config_builder(mock_config_service, screen, monkeypatch):
    """Register config builder page and open it."""
    from panther.webapp.pages import config_builder

    # Mock list_available_plugins to avoid real plugin discovery
    monkeypatch.setattr(
        "panther.webapp.pages.config_builder.list_available_plugins",
        lambda *a, **kw: [],
        raising=False,
    )

    @ui.page("/config")
    def page():
        config_builder.content()

    screen.open("/config")


def test_config_builder_renders_tabs(screen: Screen, mock_config_service, monkeypatch):
    """'Form Editor' and 'YAML Preview' tabs visible."""
    _setup_config_builder(mock_config_service, screen, monkeypatch)
    screen.should_contain("Form Editor")
    screen.should_contain("YAML Preview")


def test_config_builder_renders_heading(
    screen: Screen, mock_config_service, monkeypatch
):
    """Page heading visible."""
    _setup_config_builder(mock_config_service, screen, monkeypatch)
    screen.should_contain("Experiment Configuration Builder")


def test_config_builder_renders_action_buttons(
    screen: Screen, mock_config_service, monkeypatch
):
    """Validate, Export, Import, Load, Save buttons visible."""
    _setup_config_builder(mock_config_service, screen, monkeypatch)
    screen.should_contain("Validate")
    screen.should_contain("Export YAML")
    screen.should_contain("Import YAML")
    screen.should_contain("Load Config File")
    screen.should_contain("Save Config File")


def test_config_builder_test_config_panel_renders(
    screen: Screen, mock_config_service, monkeypatch
):
    """'Test Configuration' section visible."""
    _setup_config_builder(mock_config_service, screen, monkeypatch)
    screen.should_contain("Test Configuration")


def test_config_builder_metadata_panel_renders(
    screen: Screen, mock_config_service, monkeypatch
):
    """'Experiment Metadata' section visible."""
    _setup_config_builder(mock_config_service, screen, monkeypatch)
    screen.should_contain("Experiment Metadata")


def test_config_builder_plugin_section_renders(
    screen: Screen, mock_config_service, monkeypatch
):
    """'Plugin Configuration' section visible."""
    _setup_config_builder(mock_config_service, screen, monkeypatch)
    screen.should_contain("Plugin Configuration")


def test_config_builder_switch_to_yaml_tab(
    screen: Screen, mock_config_service, monkeypatch
):
    """Click 'YAML Preview' tab shows YAML content area."""
    _setup_config_builder(mock_config_service, screen, monkeypatch)
    screen.click("YAML Preview")
    screen.wait(0.5)
    screen.should_contain("YAML preview of the current configuration")


def test_config_builder_form_tab_shows_instructions(
    screen: Screen, mock_config_service, monkeypatch
):
    """Form Editor tab shows instruction text."""
    _setup_config_builder(mock_config_service, screen, monkeypatch)
    screen.should_contain("Configure your experiment using the form below")


def test_config_builder_import_yaml_dialog(
    screen: Screen, mock_config_service, monkeypatch
):
    """Click 'Import YAML' opens dialog with textarea."""
    _setup_config_builder(mock_config_service, screen, monkeypatch)
    screen.click("Import YAML")
    screen.wait(0.5)
    screen.should_contain("Import YAML Configuration")
    screen.should_contain("Cancel")
    screen.should_contain("Import")


def test_config_builder_save_config_dialog(
    screen: Screen, mock_config_service, monkeypatch
):
    """Click 'Save Config File' — need to switch to YAML tab first for editor to exist."""
    _setup_config_builder(mock_config_service, screen, monkeypatch)
    # Switch to YAML tab first so the editor ref gets populated
    screen.click("YAML Preview")
    screen.wait(0.5)
    # Go back to see the Save button
    screen.click("Form Editor")
    screen.wait(0.3)
    screen.click("Save Config File")
    screen.wait(0.5)
    screen.should_contain("Save Config File")


def test_config_builder_load_config_dialog(
    screen: Screen, mock_config_service, monkeypatch
):
    """Click 'Load Config File' opens dialog."""
    _setup_config_builder(mock_config_service, screen, monkeypatch)
    screen.click("Load Config File")
    screen.wait(0.5)
    screen.should_contain("Load Config File")
    screen.should_contain("Cancel")


def test_config_builder_global_sections_visible(
    screen: Screen, mock_config_service, monkeypatch
):
    """Form Editor tab shows GlobalConfig section panels."""
    _setup_config_builder(mock_config_service, screen, monkeypatch)
    # GlobalConfig sections rendered as expansion panels — at least "Logging" visible at top
    screen.should_contain("Logging")
    # Other sections (Docker, Paths, etc.) exist but may be below the fold;
    # verify at least one more section title is in the DOM (even if hidden/scrolled away)
    from selenium.webdriver.common.by import By

    docker_els = screen.selenium.find_elements(
        By.XPATH,
        '//*[not(self::script) and not(self::style) and text()[contains(., "Docker")]]',
    )
    assert len(docker_els) > 0, "Docker section should exist in the DOM"
