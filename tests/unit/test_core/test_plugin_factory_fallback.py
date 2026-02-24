"""Tests for plugin factory fallback when plugin_metadata.path is None (Gap 2).

Verifies that PluginFactory.create_service_manager correctly falls back to
_find_plugin_file when:
- implementation_dir is not a valid directory
- plugin_metadata.path is None

Tests exercise the real PluginFactory branching logic with only IO-boundary
mocking (plugin loading, filesystem access).
"""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

pytestmark = [pytest.mark.unit]


class TestPluginFactoryFallback:
    """Verify the plugin_metadata.path=None fallback in create_service_manager."""

    @staticmethod
    def _make_factory():
        """Create a real PluginFactory with mocked plugin_manager."""
        from panther.plugins.core.plugin_factory import PluginFactory

        mock_pm = MagicMock()
        mock_pm.docker_builder = MagicMock()
        factory = PluginFactory(plugin_manager=mock_pm)
        return factory, mock_pm

    def test_path_none_triggers_find_plugin_file(self):
        """When plugin_metadata.path is None, _find_plugin_file is called."""
        factory, mock_pm = self._make_factory()

        # Plugin metadata with path=None
        metadata = MagicMock()
        metadata.path = None
        metadata.name = "test_plugin"
        mock_pm.get_plugin.return_value = metadata

        # Mock to capture the fallback call
        mock_service_class = MagicMock()
        mock_service_instance = MagicMock()
        mock_service_class.return_value = mock_service_instance

        impl = MagicMock()
        impl.name = "test_plugin"
        impl.type = "iut"

        protocol = MagicMock()
        protocol.version = None

        service_config = MagicMock()
        service_config.implementation = impl

        with patch.object(
            factory, "_find_plugin_file", return_value=Path("/fake/test_plugin.py")
        ) as mock_find, patch(
            "panther.plugins.core.plugin_loader_utils.PluginManagerUtils"
        ) as mock_utils:
            mock_utils.load_plugin_class.return_value = mock_service_class
            factory.create_service_manager(
                protocol=protocol,
                implementation=impl,
                implementation_dir=Path("/nonexistent"),
                service_config_to_test=service_config,
            )

            # _find_plugin_file should have been called
            mock_find.assert_called_once_with("test_plugin", "iut")

    def test_valid_dir_does_not_trigger_fallback(self, tmp_path):
        """When implementation_dir is a valid directory, _find_plugin_file is NOT called."""
        factory, mock_pm = self._make_factory()

        metadata = MagicMock()
        metadata.path = "/some/path"
        mock_pm.get_plugin.return_value = metadata

        mock_service_class = MagicMock()
        mock_service_class.return_value = MagicMock()

        impl = MagicMock()
        impl.name = "test_plugin"
        impl.type = "iut"

        protocol = MagicMock()
        protocol.version = None

        service_config = MagicMock()
        service_config.implementation = impl

        with patch.object(factory, "_find_plugin_file") as mock_find, patch(
            "panther.plugins.core.plugin_loader_utils.PluginManagerUtils"
        ) as mock_utils:
            mock_utils.load_plugin_class.return_value = mock_service_class
            factory.create_service_manager(
                protocol=protocol,
                implementation=impl,
                implementation_dir=tmp_path,  # Real existing directory
                service_config_to_test=service_config,
            )

            # _find_plugin_file should NOT have been called
            mock_find.assert_not_called()

    def test_path_set_uses_metadata_path(self):
        """When plugin_metadata.path is set (not None), that path is used."""
        factory, mock_pm = self._make_factory()

        metadata = MagicMock()
        metadata.path = "/plugins/test_plugin"
        metadata.name = "test_plugin"
        mock_pm.get_plugin.return_value = metadata

        mock_service_class = MagicMock()
        mock_service_class.return_value = MagicMock()

        impl = MagicMock()
        impl.name = "test_plugin"
        impl.type = "iut"

        protocol = MagicMock()
        protocol.version = None

        service_config = MagicMock()
        service_config.implementation = impl

        with patch.object(factory, "_find_plugin_file") as mock_find, patch(
            "panther.plugins.core.plugin_loader_utils.PluginManagerUtils"
        ) as mock_utils:
            mock_utils.load_plugin_class.return_value = mock_service_class
            factory.create_service_manager(
                protocol=protocol,
                implementation=impl,
                implementation_dir=Path("/nonexistent"),  # Not a valid dir
                service_config_to_test=service_config,
            )

            # Should NOT have called _find_plugin_file since metadata.path is set
            mock_find.assert_not_called()

    def test_plugin_not_found_raises(self):
        """When get_plugin returns None, PluginLoadException is raised."""
        from panther.core.exceptions import ServicePluginNotFound

        factory, mock_pm = self._make_factory()
        mock_pm.get_plugin.return_value = None

        impl = MagicMock()
        impl.name = "nonexistent_plugin"
        impl.type = "iut"

        protocol = MagicMock()
        protocol.version = None

        service_config = MagicMock()
        service_config.implementation = impl

        with pytest.raises(Exception):
            factory.create_service_manager(
                protocol=protocol,
                implementation=impl,
                implementation_dir=Path("/nonexistent"),
                service_config_to_test=service_config,
            )
