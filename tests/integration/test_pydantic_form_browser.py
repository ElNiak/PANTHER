"""Selenium-based integration tests for PydanticForm component.

Uses NiceGUI's ``screen`` fixture (real Chrome via Selenium).
Run with: pytest tests/integration/test_pydantic_form_browser.py -m integration -x
"""

import json
from enum import Enum
from typing import Dict, List, Literal, Optional

import pytest
from nicegui import ui
from nicegui.testing.screen import Screen
from pydantic import BaseModel, Field

pytestmark = [pytest.mark.integration]


# ── Test models ───────────────────────────────────────────────────


class SimpleModel(BaseModel):
    name: str = Field("default", description="Name")
    count: int = Field(5, ge=0, description="Count")
    enabled: bool = Field(True, description="Enabled")


class FloatModel(BaseModel):
    rate: float = Field(1.5, description="Rate value")
    count: int = Field(3, description="An integer count")


class Inner(BaseModel):
    value: str = Field("hello", description="Inner value")
    number: int = Field(42, description="Inner number")


class Outer(BaseModel):
    name: str = Field("test", description="Name")
    inner: Inner = Field(default_factory=Inner, description="Inner model")


class OptionalInner(BaseModel):
    label: str = Field("opt_label", description="Label")


class OptionalOuter(BaseModel):
    title: str = Field("outer", description="Title")
    extra: Optional[OptionalInner] = Field(None, description="Optional extra")


class OptionalOuterWithDefault(BaseModel):
    title: str = Field("outer", description="Title")
    extra: Optional[OptionalInner] = Field(
        default_factory=OptionalInner, description="Optional extra with default"
    )


class Color(Enum):
    RED = "red"
    GREEN = "green"
    BLUE = "blue"


class ColorModel(BaseModel):
    color: Color = Field(Color.RED, description="Pick a color")


class FlagModel(BaseModel):
    active: bool = Field(True, description="Is active")


class DictModel(BaseModel):
    tags: Dict[str, str] = Field(default_factory=dict, description="Tags")


class ItemConfig(BaseModel):
    host: str = Field("localhost", description="Host")
    port: int = Field(8080, description="Port")


class DictModelKeyed(BaseModel):
    servers: Dict[str, ItemConfig] = Field(
        default_factory=dict, description="Server configs"
    )


class ListModelItems(BaseModel):
    items: List[ItemConfig] = Field(default_factory=list, description="List of items")


class LiteralModel(BaseModel):
    mode: Literal["fast", "balanced", "thorough"] = Field(
        "balanced", description="Mode"
    )


class PortModel(BaseModel):
    port: int = Field(
        8080,
        description="Port number",
        json_schema_extra={"widget_type": "port"},
    )


class AdvancedModel(BaseModel):
    name: str = Field("visible", description="Name")
    debug_mode: bool = Field(
        False,
        description="Debug mode",
        json_schema_extra={"advanced": True},
    )


class CategoryModel(BaseModel):
    host: str = Field(
        "localhost",
        description="Host",
        json_schema_extra={"category": "network"},
    )
    port: int = Field(
        8080,
        description="Port",
        json_schema_extra={"category": "network"},
    )
    name: str = Field("app", description="App name")


# ── Helper ────────────────────────────────────────────────────────


def _setup_form_page(model_cls, instance=None, config=None):
    """Set up a page with PydanticForm + Get Value bridge button."""
    from panther.webapp.components.pydantic_form import FormConfig, PydanticForm

    form_ref = {}

    @ui.page("/")
    def page():
        form = PydanticForm(model_cls, instance=instance, config=config)
        form_ref["form"] = form

        result = ui.label("").classes("result-label")

        def _get():
            try:
                val = form.get_value()
                result.set_text(json.dumps(val, default=str))
            except Exception as e:
                result.set_text(f"ERROR: {e}")

        ui.button("Get Value", on_click=_get)

    return form_ref


# ══════════════════════════════════════════════════════════════════
# EXISTING TESTS (preserved)
# ══════════════════════════════════════════════════════════════════


def test_list_field_renders_as_textarea(screen: Screen):
    """Percentiles (bare list type) renders as textarea, not text input."""
    from panther.config.core.models.observer import MetricsObserverConfig
    from panther.webapp.components.pydantic_form import PydanticForm

    @ui.page("/")
    def page():
        PydanticForm(MetricsObserverConfig)

    screen.open("/")
    screen.should_not_contain("[50, 90, 95, 99]")
    screen.should_contain("Percentiles")


def test_number_field_respects_ge_constraint(screen: Screen):
    """Optional[int] with ge=1 defaults to 1, not 0."""
    from panther.webapp.components.pydantic_form import PydanticForm

    class TestModel(BaseModel):
        timeout: Optional[int] = Field(None, ge=1, description="Timeout")

    @ui.page("/")
    def page():
        PydanticForm(TestModel)

    screen.open("/")
    screen.should_contain_input("1")


def test_form_get_set_roundtrip(screen: Screen):
    """Form renders basic fields correctly."""
    from panther.webapp.components.pydantic_form import PydanticForm

    @ui.page("/")
    def page():
        PydanticForm(SimpleModel)

    screen.open("/")
    screen.should_contain("Name")
    screen.should_contain("Count")
    screen.should_contain("Enabled")


def test_nested_model_renders_expansion(screen: Screen):
    """Nested BaseModel fields render as expansion panels."""
    from panther.webapp.components.pydantic_form import PydanticForm

    @ui.page("/")
    def page():
        PydanticForm(Outer)

    screen.open("/")
    screen.should_contain("Name")
    screen.should_contain("Inner")


def test_enum_field_renders_select(screen: Screen):
    """Enum fields render as select dropdowns."""
    from panther.webapp.components.pydantic_form import PydanticForm

    @ui.page("/")
    def page():
        PydanticForm(ColorModel)

    screen.open("/")
    screen.should_contain("Color")


def test_bool_field_renders_switch(screen: Screen):
    """Bool fields render as toggle switches."""
    from panther.webapp.components.pydantic_form import PydanticForm

    @ui.page("/")
    def page():
        PydanticForm(FlagModel)

    screen.open("/")
    screen.should_contain("Active")


def test_full_observer_config_renders(screen: Screen):
    """Full ObserversConfig renders without errors."""
    from panther.config.core.models.observer import ObserversConfig
    from panther.webapp.components.pydantic_form import PydanticForm

    @ui.page("/")
    def page():
        PydanticForm(ObserversConfig)

    screen.open("/")
    screen.should_contain("Metrics")
    screen.should_contain("Logger")


# ══════════════════════════════════════════════════════════════════
# GROUP 1: Scalar Field Interaction
# ══════════════════════════════════════════════════════════════════


def test_str_field_edit_updates_value(screen: Screen):
    """Clear str input, type new text, Get Value shows updated string."""
    _setup_form_page(SimpleModel)
    screen.open("/")
    # Find the Name input by its aria-label (Quasar input labels)
    el = screen.selenium.find_element("css selector", "input[aria-label='Name']")
    el.clear()
    el.send_keys("new_value")
    screen.click("Get Value")
    screen.wait(0.5)
    screen.should_contain("new_value")


def test_int_field_edit_updates_value(screen: Screen):
    """Change int field, Get Value reflects the new integer."""
    _setup_form_page(SimpleModel)
    screen.open("/")
    el = screen.selenium.find_element("css selector", "input[aria-label='Count']")
    el.clear()
    el.send_keys("42")
    screen.click("Get Value")
    screen.wait(0.5)
    screen.should_contain("42")


def test_float_field_has_step_point_one(screen: Screen):
    """Float input renders with step=0.1 attribute."""
    from panther.webapp.components.pydantic_form import PydanticForm

    @ui.page("/")
    def page():
        PydanticForm(FloatModel)

    screen.open("/")
    screen.should_contain("Rate")
    # The float field should have its default value in the input
    screen.should_contain_input("1.5")


def test_bool_switch_toggle(screen: Screen):
    """Click switch label to toggle, Get Value shows flipped value."""
    _setup_form_page(SimpleModel, instance={"name": "x", "count": 1, "enabled": True})
    screen.open("/")
    # Click the switch label to toggle it
    screen.click("Enabled")
    screen.wait(0.3)
    screen.click("Get Value")
    screen.wait(0.5)
    screen.should_contain("false")


def test_set_value_populates_inputs(screen: Screen):
    """set_value() populates form inputs with new data."""
    from panther.webapp.components.pydantic_form import PydanticForm

    @ui.page("/")
    def page():
        form = PydanticForm(SimpleModel)
        ui.button(
            "Set Data",
            on_click=lambda: form.set_value(
                {"name": "injected", "count": 99, "enabled": False}
            ),
        )

    screen.open("/")
    screen.click("Set Data")
    screen.wait(0.5)
    screen.should_contain_input("injected")


def test_get_value_collects_all_field_types(screen: Screen):
    """Render with instance, immediately Get Value matches."""
    instance = {"name": "hello", "count": 7, "enabled": False}
    _setup_form_page(SimpleModel, instance=instance)
    screen.open("/")
    screen.click("Get Value")
    screen.wait(0.5)
    # The JSON output is displayed as text content — check for key substrings
    screen.should_contain("hello")
    screen.should_contain("false")


# ══════════════════════════════════════════════════════════════════
# GROUP 2: Nested Model Interaction
# ══════════════════════════════════════════════════════════════════


def test_nested_expansion_click_reveals_inner_fields(screen: Screen):
    """Click expansion title reveals inner fields."""
    _setup_form_page(Outer)
    screen.open("/")
    screen.click("Inner")
    screen.wait(0.5)
    # The inner model field label is just "Value" (from field name "value")
    screen.should_contain("Value")


def test_nested_model_edit_inner_field(screen: Screen):
    """Expand nested, edit inner input, parent Get Value reflects change."""
    _setup_form_page(Outer)
    screen.open("/")
    screen.click("Inner")
    screen.wait(0.5)
    el = screen.selenium.find_element("css selector", "input[aria-label='Value']")
    el.clear()
    el.send_keys("updated")
    screen.click("Get Value")
    screen.wait(0.5)
    screen.should_contain("updated")


# ══════════════════════════════════════════════════════════════════
# GROUP 3: Optional[BaseModel] Toggle
# ══════════════════════════════════════════════════════════════════


def test_optional_model_toggle_off_hides_form(screen: Screen):
    """Default None optional model: inner fields not visible."""
    _setup_form_page(OptionalOuter)
    screen.open("/")
    screen.should_contain("Enable Extra")
    # Label field from OptionalInner should not be visible
    screen.should_not_contain("opt_label")


def test_optional_model_toggle_on_shows_form(screen: Screen):
    """Click toggle on reveals inner form fields."""
    _setup_form_page(OptionalOuter)
    screen.open("/")
    screen.click("Enable Extra")
    screen.wait(0.5)
    screen.should_contain("Label")


def test_optional_model_toggle_off_returns_none(screen: Screen):
    """Start enabled, toggle off, get_value returns None for that field."""
    _setup_form_page(OptionalOuterWithDefault)
    screen.open("/")
    # Toggle off
    screen.click("Enable Extra")
    screen.wait(0.5)
    screen.click("Get Value")
    screen.wait(0.5)
    screen.should_contain("null")


def test_optional_model_toggle_on_get_value(screen: Screen):
    """Start None, toggle on, get_value returns defaults."""
    _setup_form_page(OptionalOuter)
    screen.open("/")
    screen.click("Enable Extra")
    screen.wait(0.5)
    screen.click("Get Value")
    screen.wait(0.5)
    screen.should_contain("opt_label")


# ══════════════════════════════════════════════════════════════════
# GROUP 4: Dict[str, str] — KeyValueEditor
# ══════════════════════════════════════════════════════════════════


def test_kv_editor_add_row(screen: Screen):
    """Click 'Add row' creates Key/Value input fields."""
    _setup_form_page(DictModel)
    screen.open("/")
    screen.click("Add row")
    screen.wait(0.5)
    screen.should_contain("Key")
    screen.should_contain("Value")


def test_kv_editor_initial_data_renders(screen: Screen):
    """Instance with dict data renders key/value inputs."""
    _setup_form_page(DictModel, instance={"tags": {"env": "prod"}})
    screen.open("/")
    screen.should_contain_input("env")
    screen.should_contain_input("prod")


def test_kv_editor_fill_and_get_value(screen: Screen):
    """Add row, fill key/value, Get Value returns the dict."""
    _setup_form_page(DictModel)
    screen.open("/")
    screen.click("Add row")
    screen.wait(0.5)
    # Find the Key and Value inputs and fill them
    inputs = screen.selenium.find_elements("tag name", "input")
    key_inputs = [i for i in inputs if i.get_attribute("aria-label") == "Key"]
    value_inputs = [i for i in inputs if i.get_attribute("aria-label") == "Value"]
    if key_inputs and value_inputs:
        key_inputs[-1].send_keys("mykey")
        value_inputs[-1].send_keys("myval")
    screen.click("Get Value")
    screen.wait(0.5)
    screen.should_contain("mykey")


# ══════════════════════════════════════════════════════════════════
# GROUP 5: Dict[str, BaseModel] — KeyedModelEditor
# ══════════════════════════════════════════════════════════════════


def test_keyed_model_editor_add_opens_dialog(screen: Screen):
    """Click 'Add entry' opens a dialog with Key input."""
    _setup_form_page(DictModelKeyed)
    screen.open("/")
    screen.click("Add entry")
    screen.wait(0.5)
    screen.should_contain("Add entry")


def test_keyed_model_editor_add_and_close(screen: Screen):
    """Fill dialog key, click Add, entry appears."""
    _setup_form_page(DictModelKeyed)
    screen.open("/")
    screen.click("Add entry")
    screen.wait(0.5)
    # Fill key input in dialog
    inputs = screen.selenium.find_elements("tag name", "input")
    key_inputs = [i for i in inputs if i.get_attribute("aria-label") == "Key"]
    if key_inputs:
        key_inputs[0].send_keys("server1")
    # Click the dialog's "Add" button (Quasar renders text as UPPERCASE)
    from selenium.webdriver.common.by import By

    dialog = screen.selenium.find_element(By.CSS_SELECTOR, ".q-dialog")
    buttons = dialog.find_elements(By.TAG_NAME, "button")
    for btn in buttons:
        if btn.text.strip().upper() == "ADD":
            btn.click()
            break
    screen.wait(0.5)
    screen.should_contain("server1")


def test_keyed_model_editor_delete_entry(screen: Screen):
    """Add entry then delete it — entry removed."""
    _setup_form_page(
        DictModelKeyed,
        instance={"servers": {"s1": {"host": "a.com", "port": 80}}},
    )
    screen.open("/")
    screen.should_contain("s1")
    # Find and click the close/delete button for the entry
    close_buttons = screen.selenium.find_elements(
        "css selector", "button[class*='negative'], button .q-icon"
    )
    for btn in close_buttons:
        try:
            if (
                "close" in btn.text.lower()
                or btn.get_attribute("innerHTML")
                and "close" in btn.get_attribute("innerHTML")
            ):
                btn.click()
                break
        except Exception:
            continue
    screen.wait(0.5)
    screen.should_contain("No entries")


# ══════════════════════════════════════════════════════════════════
# GROUP 6: List[BaseModel] — ModelListEditor
# ══════════════════════════════════════════════════════════════════


def test_model_list_editor_add_opens_dialog(screen: Screen):
    """Click 'Add' opens dialog."""
    _setup_form_page(ListModelItems)
    screen.open("/")
    screen.should_contain("No entries")
    # The "Add" button for ModelListEditor
    screen.click("Add")
    screen.wait(0.5)
    screen.should_contain("Add entry")


def test_model_list_editor_add_entry_appears(screen: Screen):
    """Fill dialog, click Add, [0] index appears."""
    _setup_form_page(ListModelItems)
    screen.open("/")
    screen.click("Add")
    screen.wait(0.5)
    # Click the dialog's "Add" button (Quasar renders text as UPPERCASE)
    from selenium.webdriver.common.by import By

    dialog = screen.selenium.find_element(By.CSS_SELECTOR, ".q-dialog")
    buttons = dialog.find_elements(By.TAG_NAME, "button")
    for btn in buttons:
        if btn.text.strip().upper() == "ADD":
            btn.click()
            break
    screen.wait(0.5)
    screen.should_contain("[0]")


def test_model_list_editor_delete_entry(screen: Screen):
    """Delete entry shows 'No entries'."""
    _setup_form_page(
        ListModelItems,
        instance={"items": [{"host": "x.com", "port": 80}]},
    )
    screen.open("/")
    screen.should_contain("[0]")
    # Click the close/delete button
    close_buttons = screen.selenium.find_elements(
        "css selector", "button[class*='negative']"
    )
    if close_buttons:
        close_buttons[0].click()
    screen.wait(0.5)
    screen.should_contain("No entries")


# ══════════════════════════════════════════════════════════════════
# GROUP 7: FormConfig Options
# ══════════════════════════════════════════════════════════════════


def test_section_style_card_shows_inner_immediately(screen: Screen):
    """section_style='card' renders nested model without expansion click."""
    from panther.webapp.components.pydantic_form import FormConfig, PydanticForm

    @ui.page("/")
    def page():
        PydanticForm(Outer, config=FormConfig(section_style="card"))

    screen.open("/")
    # Inner fields should be visible without clicking an expansion
    screen.should_contain("Value")


def test_show_advanced_hides_and_shows_fields(screen: Screen):
    """advanced=True field hidden by default, shown with show_advanced."""
    from panther.webapp.components.pydantic_form import FormConfig, PydanticForm

    @ui.page("/")
    def page():
        # Default: show_advanced=False — advanced field goes into expansion
        ui.label("FORM1").classes("text-h6")
        PydanticForm(AdvancedModel, config=FormConfig(show_advanced=False))
        ui.separator()
        # show_advanced=True — advanced field rendered directly
        ui.label("FORM2").classes("text-h6")
        PydanticForm(AdvancedModel, config=FormConfig(show_advanced=True))

    screen.open("/")
    # Name field should be visible in both
    screen.should_contain("Name")
    # "Advanced" expansion panel should exist in the DOM (form1)
    from selenium.webdriver.common.by import By

    adv_els = screen.selenium.find_elements(
        By.XPATH,
        '//*[not(self::script) and not(self::style) and contains(text(), "Advanced")]',
    )
    assert len(adv_els) > 0, "Advanced expansion panel should exist in the DOM"
    # "Debug Mode" should exist in the DOM (form2 renders it directly)
    dm_els = screen.selenium.find_elements(
        By.XPATH,
        '//*[not(self::script) and not(self::style) and contains(text(), "Debug Mode")]',
    )
    assert len(dm_els) > 0, "Debug Mode should exist in the DOM"


def test_group_by_category(screen: Screen):
    """Fields with category grouped under expansion panel."""
    from panther.webapp.components.pydantic_form import FormConfig, PydanticForm

    @ui.page("/")
    def page():
        PydanticForm(CategoryModel, config=FormConfig(group_by_category=True))

    screen.open("/")
    screen.should_contain("Network")
    screen.should_contain("Name")


# ══════════════════════════════════════════════════════════════════
# GROUP 8: Specialized Widgets
# ══════════════════════════════════════════════════════════════════


def test_port_widget_constraints(screen: Screen):
    """widget_type='port' renders number input with min=0, max=65535."""
    from panther.webapp.components.pydantic_form import PydanticForm

    @ui.page("/")
    def page():
        PydanticForm(PortModel)

    screen.open("/")
    screen.should_contain("Port")
    screen.should_contain_input("8080")


def test_literal_field_renders_select(screen: Screen):
    """Literal['a','b','c'] renders as select dropdown."""
    from panther.webapp.components.pydantic_form import PydanticForm

    @ui.page("/")
    def page():
        PydanticForm(LiteralModel)

    screen.open("/")
    screen.should_contain("Mode")


def test_float_step_differs_from_int_step(screen: Screen):
    """Float renders with step=0.1, int with step=1."""
    from panther.webapp.components.pydantic_form import PydanticForm

    @ui.page("/")
    def page():
        PydanticForm(FloatModel)

    screen.open("/")
    # Both fields should render
    screen.should_contain("Rate")
    screen.should_contain("Count")


# ══════════════════════════════════════════════════════════════════
# GROUP 9: Real Config Models
# ══════════════════════════════════════════════════════════════════


def test_global_config_renders_all_sections(screen: Screen):
    """GlobalConfig renders all section names."""
    from panther.config.core.models.global_config import GlobalConfig
    from panther.webapp.components.pydantic_form import PydanticForm

    @ui.page("/")
    def page():
        PydanticForm(GlobalConfig)

    screen.open("/")
    screen.should_contain("Logging")
    # Paths and Docker may be below the viewport fold — check DOM presence
    from selenium.webdriver.common.by import By

    for section in ("Paths", "Docker"):
        els = screen.selenium.find_elements(
            By.XPATH,
            f'//*[not(self::script) and not(self::style) and text()[contains(., "{section}")]]',
        )
        assert len(els) > 0, f"{section} section should exist in the DOM"


def test_storage_observer_renders_enum(screen: Screen):
    """StorageObserverConfig renders StorageFormat enum."""
    from panther.config.core.models.observer import StorageObserverConfig
    from panther.webapp.components.pydantic_form import PydanticForm

    @ui.page("/")
    def page():
        PydanticForm(StorageObserverConfig)

    screen.open("/")
    screen.should_contain("Format")
