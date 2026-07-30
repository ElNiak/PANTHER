#!/usr/bin/env python3
"""Integration tests for plugin discovery functionality."""

import unittest
from pathlib import Path

from panther.plugins.plugin_manager import PluginManager


class TestPluginDiscoveryIntegration(unittest.TestCase):
    """Integration test cases for plugin discovery."""

    def setUp(self):
        """Reset singleton before each test."""
        PluginManager.reset_singleton()

    def tearDown(self):
        """Clean up after each test."""
        PluginManager.reset_singleton()

    def test_plugin_discovery_finds_all_plugin_types(self):
        """Test that plugin discovery finds all expected plugin types."""
        # Create plugin manager and discover plugins
        pm = PluginManager()
        plugins = pm.discover_plugins()

        # Verify plugins were discovered
        self.assertGreater(len(plugins), 0, "Should discover at least one plugin")

        # Group by type
        by_type = {}
        for name, metadata in plugins.items():
            plugin_type = str(metadata.type)
            if plugin_type not in by_type:
                by_type[plugin_type] = []
            by_type[plugin_type].append(name)

        # Verify expected plugin types are found
        expected_types = [
            "execution_environment",
            "network_environment",
            "iut",
            "tester",
        ]
        for expected_type in expected_types:
            self.assertIn(
                expected_type, by_type, f"Should find {expected_type} plugins"
            )
            self.assertGreater(
                len(by_type[expected_type]),
                0,
                f"Should find at least one {expected_type} plugin",
            )

    def test_specific_plugins_discovered(self):
        """Test that specific known plugins are discovered."""
        pm = PluginManager()
        plugins = pm.discover_plugins()

        # Check for specific execution environment plugins
        execution_plugins = ["strace", "memcheck", "helgrind", "iterations"]
        for plugin in execution_plugins:
            self.assertIn(
                plugin, plugins, f"Should discover {plugin} execution environment"
            )

        # Check for specific network environment plugins
        network_plugins = ["docker_compose", "localhost_single_container", "shadow_ns"]
        for plugin in network_plugins:
            self.assertIn(
                plugin, plugins, f"Should discover {plugin} network environment"
            )

        # Check for specific IUT plugins
        iut_plugins = ["picoquic", "aioquic", "quiche", "quinn"]
        for plugin in iut_plugins:
            self.assertIn(plugin, plugins, f"Should discover {plugin} IUT")

        # Check for tester plugin
        self.assertIn("panther_ivy", plugins, "Should discover panther_ivy tester")

    def test_plugin_metadata_structure(self):
        """Test that discovered plugins have proper metadata structure."""
        pm = PluginManager()
        plugins = pm.discover_plugins()

        # Test first plugin's metadata
        if plugins:
            first_plugin_name = next(iter(plugins))
            metadata = plugins[first_plugin_name]

            # Verify required attributes
            self.assertTrue(hasattr(metadata, "name"))
            self.assertTrue(hasattr(metadata, "type"))
            self.assertTrue(hasattr(metadata, "version"))
            self.assertTrue(hasattr(metadata, "status"))
            self.assertTrue(hasattr(metadata, "location"))

            # Verify name matches
            self.assertEqual(metadata.name, first_plugin_name)

            # Verify location is a valid path
            self.assertTrue(Path(metadata.location).exists())

    def test_plugin_discovery_caching_integration(self):
        """Test that plugin discovery caching works in real scenario."""
        pm = PluginManager(enable_cache=True, cache_ttl=3600)

        # First discovery
        import time

        start_time1 = time.time()
        plugins1 = pm.discover_plugins()
        duration1 = time.time() - start_time1

        # Second discovery (should be cached)
        start_time2 = time.time()
        plugins2 = pm.discover_plugins()
        duration2 = time.time() - start_time2

        # Verify results are the same
        self.assertEqual(plugins1, plugins2)

        # Cached call should be significantly faster
        # Note: This might be flaky in CI, so we just check it's faster
        self.assertLess(
            duration2, duration1 * 0.5, "Cached discovery should be at least 2x faster"
        )

    def test_plugin_discovery_count_tracking(self):
        """Test that discovery count is tracked correctly."""
        pm = PluginManager()

        # Initial count should be 0
        self.assertEqual(pm._discovery_count, 0)

        # First discovery
        pm.discover_plugins()
        count_after_first = pm._discovery_count
        self.assertGreater(count_after_first, 0)

        # Second discovery (cached)
        pm.discover_plugins()
        count_after_second = pm._discovery_count

        # Count should not increase for cached call
        self.assertEqual(count_after_first, count_after_second)


if __name__ in {"__main__", "__mp_main__"}:
    unittest.main()
