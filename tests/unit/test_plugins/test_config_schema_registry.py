"""Tests for config schema registry: PluginManifest.config_model and auto-discovery."""

from unittest.mock import MagicMock, patch

import pytest

from panther.config.core.models.plugin import BasePluginConfig, ServicePluginConfig
from panther.plugins.core.plugin_decorators import (
    _discover_sibling_config_model,
    clear_decorated_plugins,
    get_all_config_models,
    get_config_model,
    register_plugin,
)
from panther.plugins.core.structures.plugin_manifest import PluginManifest
from panther.plugins.core.structures.plugin_type import PluginType

pytestmark = [pytest.mark.unit]


class TestPluginManifestConfigModel:
    """Test that PluginManifest supports config_model field."""

    def test_config_model_defaults_to_none(self):
        manifest = PluginManifest(name="test", version="1.0.0", type=PluginType.IUT)
        assert manifest.config_model is None

    def test_config_model_can_be_set(self):
        class FakeConfig(BasePluginConfig):
            type: str = "iut"

        manifest = PluginManifest(name="test", version="1.0.0", type=PluginType.IUT)
        manifest.config_model = FakeConfig
        assert manifest.config_model is FakeConfig

    def test_config_model_not_in_to_dict(self):
        """config_model is runtime-only and should NOT appear in serialized dict."""
        manifest = PluginManifest(name="test", version="1.0.0", type=PluginType.IUT)
        d = manifest.to_dict()
        assert "config_model" not in d


class TestDiscoverSiblingConfigModel:
    """Test _discover_sibling_config_model auto-discovery."""

    def test_returns_none_when_no_config_schema_module(self):
        """If the sibling config_schema module doesn't exist, returns None."""

        class FakeClass:
            __module__ = "some.fake.module"

        result = _discover_sibling_config_model(FakeClass)
        assert result is None

    def test_returns_none_for_module_without_dots(self):
        """Module name without dots should return None (no package)."""

        class FakeClass:
            __module__ = "standalone"

        result = _discover_sibling_config_model(FakeClass)
        assert result is None

    def test_discovers_config_class_from_real_plugin(self):
        """Test discovery using a real plugin module."""
        try:
            from panther.plugins.services.iut.quic.picoquic.config_schema import (
                PicoquicConfig,
            )
            from panther.plugins.services.iut.quic.picoquic.picoquic_service_manager import (
                PicoquicServiceManager,
            )

            result = _discover_sibling_config_model(PicoquicServiceManager)
            assert result is PicoquicConfig
        except ImportError:
            pytest.skip("Picoquic plugin not available")

    def test_skips_base_plugin_config(self):
        """Should not return BasePluginConfig itself."""
        import types

        fake_module = types.ModuleType("fake.config_schema")
        fake_module.BasePluginConfig = BasePluginConfig

        class FakeClass:
            __module__ = "fake.manager"

        with patch("importlib.import_module", return_value=fake_module):
            result = _discover_sibling_config_model(FakeClass)
            assert result is None


class TestRegistryLookupFunctions:
    """Test get_config_model and get_all_config_models."""

    @pytest.fixture(autouse=True)
    def _clean_registry(self):
        """Clear the global registry before and after each test."""
        clear_decorated_plugins()
        yield
        clear_decorated_plugins()

    def test_get_config_model_returns_none_for_unknown(self):
        assert get_config_model("nonexistent_plugin") is None

    def test_get_all_config_models_empty_registry(self):
        assert get_all_config_models() == {}

    def test_register_plugin_populates_config_model(self):
        """Verify @register_plugin populates manifest.config_model via auto-discovery."""

        class FakeConfig(ServicePluginConfig):
            type: str = "iut"

        with patch(
            "panther.plugins.core.plugin_decorators._discover_sibling_config_model",
            return_value=FakeConfig,
        ):

            @register_plugin(plugin_type=PluginType.IUT, name="test_plugin")
            class TestManager:
                pass

        result = get_config_model("test_plugin")
        assert result is FakeConfig

    def test_get_all_config_models_returns_populated_entries(self):
        class FakeConfig(ServicePluginConfig):
            type: str = "iut"

        with patch(
            "panther.plugins.core.plugin_decorators._discover_sibling_config_model",
            return_value=FakeConfig,
        ):

            @register_plugin(plugin_type=PluginType.IUT, name="test_plugin_2")
            class TestManager2:
                pass

        models = get_all_config_models()
        assert "test_plugin_2" in models
        assert models["test_plugin_2"] is FakeConfig


class TestDiscoverySiblingEdgeCases:
    """Test _discover_sibling_config_model edge cases (I3, I4)."""

    def test_returns_none_for_dotless_module(self):
        """Module without dots should be handled gracefully (I4)."""

        class FakeClass:
            __module__ = "standalone"

        result = _discover_sibling_config_model(FakeClass)
        assert result is None

    def test_skips_intermediate_base_classes(self):
        """Should skip known base classes like ServicePluginConfig (I3).

        Uses attribute name 'AAAServicePluginConfig' to ensure it sorts
        before the concrete class, exposing the bug if base filtering is missing.
        """
        import types

        class MyConcreteConfig(ServicePluginConfig):
            """The real config class."""

            type: str = "iut"

        fake_module = types.ModuleType("fake.config_schema")
        # Name sorts before MyConcreteConfig — without base_names filter,
        # ServicePluginConfig would be returned first
        fake_module.AAAServicePluginConfig = ServicePluginConfig
        fake_module.MyConcreteConfig = MyConcreteConfig

        class FakeClass:
            __module__ = "fake.manager"

        with patch("importlib.import_module", return_value=fake_module):
            result = _discover_sibling_config_model(FakeClass)
            assert result is MyConcreteConfig
