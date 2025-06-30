#!/usr/bin/env python3
"""Unit tests for PluginManager singleton behavior."""

import unittest
from unittest.mock import MagicMock, patch

from panther.plugins.plugin_manager import PluginManager


class TestPluginManagerSingleton(unittest.TestCase):
    """Test cases for PluginManager singleton pattern implementation."""

    def setUp(self):
        """Reset singleton before each test."""
        PluginManager.reset_singleton()

    def tearDown(self):
        """Clean up after each test."""
        PluginManager.reset_singleton()

    def test_singleton_instance_creation(self):
        """Test that only one instance of PluginManager is created."""
        # Create first instance
        pm1 = PluginManager(plugin_directories=["test/dir1"])

        # Create second instance with different parameters
        pm2 = PluginManager(plugin_directories=["test/dir2"], enable_cache=False)

        # Verify they are the same instance
        self.assertIs(pm1, pm2, "PluginManager should return the same instance")
        self.assertEqual(id(pm1), id(pm2), "Instance IDs should be identical")

    def test_singleton_reset_functionality(self):
        """Test that reset_singleton creates a new instance."""
        # Create initial instance
        pm1 = PluginManager()
        initial_id = id(pm1)

        # Reset singleton
        PluginManager.reset_singleton()

        # Create new instance after reset
        pm2 = PluginManager()
        new_id = id(pm2)

        # Verify new instance was created
        self.assertIsNot(pm1, pm2, "Reset should create a new instance")
        self.assertNotEqual(
            initial_id, new_id, "Instance IDs should be different after reset"
        )

    @patch("panther.plugins.plugin_manager.PluginDiscovery")
    def test_plugin_discovery_caching(self, mock_discovery_class):
        """Test that plugin discovery uses caching correctly."""
        # Setup mock
        mock_discovery = MagicMock()
        mock_discovery.discover_plugins.return_value = {
            "test_plugin": MagicMock(name="test_plugin", type="iut")
        }
        mock_discovery_class.return_value = mock_discovery

        # Create plugin manager
        pm = PluginManager(enable_cache=True, cache_ttl=3600)

        # First discovery call
        result1 = pm.discover_plugins()
        self.assertEqual(len(result1), 1)
        self.assertEqual(pm._discovery_count, 1)

        # Second discovery call (should use cache)
        result2 = pm.discover_plugins()
        self.assertEqual(result1, result2)
        self.assertEqual(
            pm._discovery_count,
            1,
            "Discovery count should not increase when using cache",
        )

        # Verify discovery was called only once
        mock_discovery.discover_plugins.assert_called_once()

    @patch("panther.plugins.plugin_manager.PluginDiscovery")
    def test_singleton_preserves_state(self, mock_discovery_class):
        """Test that singleton preserves state across different references."""
        # Setup mock
        mock_discovery = MagicMock()
        mock_discovery.discover_plugins.return_value = {
            "plugin1": MagicMock(name="plugin1", type="iut"),
            "plugin2": MagicMock(name="plugin2", type="network_environment"),
        }
        mock_discovery_class.return_value = mock_discovery

        # Create first reference and discover plugins
        pm1 = PluginManager()
        plugins1 = pm1.discover_plugins()

        # Create second reference
        pm2 = PluginManager()

        # Verify state is preserved
        self.assertEqual(pm1._discovery_count, pm2._discovery_count)
        self.assertEqual(pm1._discovery_cache, pm2._discovery_cache)
        self.assertEqual(pm1.plugins, pm2.plugins)

        # Verify cached results are returned
        plugins2 = pm2.discover_plugins()
        self.assertEqual(plugins1, plugins2)

    def test_singleton_class_attributes(self):
        """Test that class-level singleton attributes work correctly."""
        # Verify initial state
        self.assertIsNone(PluginManager._instance)
        self.assertFalse(PluginManager._initialized)

        # Create instance
        pm = PluginManager()

        # Verify singleton attributes are set
        self.assertIsNotNone(PluginManager._instance)
        self.assertTrue(PluginManager._initialized)
        self.assertIs(PluginManager._instance, pm)

        # Reset and verify cleanup
        PluginManager.reset_singleton()
        self.assertIsNone(PluginManager._instance)
        self.assertFalse(PluginManager._initialized)


if __name__ == "__main__":
    unittest.main()
