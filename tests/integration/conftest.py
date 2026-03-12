"""Integration test fixtures for browser-based NiceGUI testing."""

import json
from dataclasses import dataclass
from typing import Generator
from unittest.mock import Mock

import pytest


@pytest.fixture(scope="session")
def nicegui_chrome_options(request):
    """Configure Chrome options for NiceGUI screen tests."""
    from selenium import webdriver

    options = webdriver.ChromeOptions()
    options.add_argument("disable-dev-shm-usage")
    options.add_argument("no-sandbox")
    options.add_argument("window-size=1200x900")
    if not request.config.getoption("--headed", default=False):
        options.add_argument("headless")
    return options


@pytest.fixture(scope="session")
def nicegui_driver(
    nicegui_chrome_options,
) -> Generator:
    """Create Chrome driver using webdriver-manager for chromedriver resolution."""
    from selenium import webdriver
    from selenium.webdriver.chrome.service import Service
    from webdriver_manager.chrome import ChromeDriverManager

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=nicegui_chrome_options)
    yield driver
    driver.quit()


@pytest.fixture(autouse=True)
def _slow_browser(request):
    """Pause after each test so the rendered page is visible in headed mode."""
    yield
    if request.config.getoption("--headed", default=False):
        import time

        time.sleep(3)


# ── Bridge helpers for PydanticForm server-side value testing ──────


def make_form_page(model_cls, instance=None, config=None):
    """Create a @ui.page with PydanticForm + get_value/set_value bridge buttons.

    Returns a dict with 'form_ref' key that will hold the PydanticForm after page load.
    The page adds:
      - A "Get Value" button that writes form.get_value() JSON to a label with id "result-label"
      - A "Set Value" button that reads from a hidden textarea with id "set-value-input"
    """
    from nicegui import ui

    from panther.webapp.components.forms.pydantic_form import PydanticForm

    form_ref = {}

    @ui.page("/")
    def page():
        form = PydanticForm(model_cls, instance=instance, config=config)
        form_ref["form"] = form

        result_label = ui.label("").classes("result-label")
        result_label.style("white-space: pre-wrap; font-family: monospace;")

        def on_get_value():
            try:
                val = form.get_value()
                result_label.set_text(json.dumps(val, default=str))
            except Exception as e:
                result_label.set_text(f"ERROR: {e}")

        ui.button("Get Value", on_click=on_get_value)

    return form_ref


def make_app_page(page_module, route="/", mock_patches=None):
    """Create a @ui.page that renders a full app page module with mocks.

    Args:
        page_module: The page module (e.g. dashboard) with a content() function.
        route: The route to register.
        mock_patches: Dict of module paths to mock objects (applied before page render).
    """
    from nicegui import app, ui

    app.storage.general.setdefault("config_path", None)
    app.storage.general.setdefault("output_dir", "/tmp/panther_test_outputs")

    @ui.page(route)
    def page():
        page_module.content()


# ── Mock service fixtures ─────────────────────────────────────────


@dataclass
class FakePluginMetadata:
    """Minimal stand-in for PluginMetadata in tests."""

    name: str
    type: str
    version: str = "1.0.0"
    description: str = ""
    supported_protocols: list = None
    capabilities: list = None
    tags: list = None
    status: str = "active"
    path: str = ""
    author: str = ""
    dependencies: list = None
    external_dependencies: list = None
    runtime_mode: str = ""
    extra_fields: dict = None

    def __post_init__(self):  # noqa: D105
        if self.supported_protocols is None:
            self.supported_protocols = []
        if self.capabilities is None:
            self.capabilities = []
        if self.tags is None:
            self.tags = []
        if self.dependencies is None:
            self.dependencies = []
        if self.external_dependencies is None:
            self.external_dependencies = []
        if self.extra_fields is None:
            self.extra_fields = {}

    def to_dict(self):
        return {
            "name": self.name,
            "type": self.type,
            "version": self.version,
            "description": self.description,
            "supported_protocols": self.supported_protocols,
        }


@pytest.fixture
def mock_plugin_service(monkeypatch):
    """Mock PluginService for browser tests — returns fake plugin data."""
    mock_svc = Mock()
    mock_svc.list_plugins.return_value = []
    mock_svc.get_plugin_manifest.return_value = None
    monkeypatch.setattr(
        "panther.webapp.services.plugin_service.PluginService",
        lambda *a, **kw: mock_svc,
    )
    # Also patch where pages import it
    monkeypatch.setattr(
        "panther.webapp.pages.dashboard.PluginService",
        lambda *a, **kw: mock_svc,
    )
    monkeypatch.setattr(
        "panther.webapp.pages.plugins.PluginService",
        lambda *a, **kw: mock_svc,
    )
    return mock_svc


@pytest.fixture
def mock_results_service(monkeypatch):
    """Mock ResultsService for browser tests."""
    mock_svc = Mock()
    mock_svc.list_experiments.return_value = []
    mock_svc.count_experiments.return_value = 0
    mock_svc.get_experiment_detail.return_value = None
    mock_svc.get_aggregate_stats.return_value = {
        "total": 0,
        "passed": 0,
        "failed": 0,
        "success_rate": 0.0,
        "duration": None,
    }
    mock_svc.get_test_results.return_value = []
    mock_svc.get_service_health.return_value = []
    mock_svc.read_log_lines.return_value = []
    monkeypatch.setattr(
        "panther.webapp.pages.dashboard.ResultsService",
        lambda *a, **kw: mock_svc,
    )
    monkeypatch.setattr(
        "panther.webapp.pages.results.ResultsService",
        lambda *a, **kw: mock_svc,
    )
    return mock_svc


@pytest.fixture
def mock_experiment_service(monkeypatch):
    """Mock ExperimentService singleton for browser tests."""
    mock_svc = Mock()
    mock_svc.status = "Idle"
    mock_svc.log_lines = []
    mock_svc.config_path = ""
    mock_svc.is_running = False
    mock_svc.register_callbacks = Mock()
    mock_svc.unregister_callbacks = Mock()
    monkeypatch.setattr(
        "panther.webapp.pages.experiments.get_experiment_service",
        lambda: mock_svc,
    )
    return mock_svc


@pytest.fixture
def mock_config_service(monkeypatch):
    """Mock ConfigService for browser tests."""
    mock_svc = Mock()
    mock_svc.get_default_yaml.return_value = (
        "logging:\n  level: INFO\ntests:\n  - name: test1\n"
    )
    mock_svc.validate_yaml.return_value = None
    mock_svc.yaml_to_dict.return_value = {
        "logging": {"level": "INFO"},
        "tests": [{"name": "test1"}],
    }
    mock_svc.list_configs.return_value = []
    mock_svc.validate_config_detailed.return_value = []
    monkeypatch.setattr(
        "panther.webapp.pages.config_builder.ConfigService",
        lambda *a, **kw: mock_svc,
    )
    return mock_svc
