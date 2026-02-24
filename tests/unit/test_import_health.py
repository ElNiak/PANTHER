"""Test module for import health and circular import detection."""

import importlib
import sys

import pytest


class TestImportHealth:
    """Test suite for import health checks."""

    def test_no_circular_imports_core(self):
        """Test that core modules can be imported without circular dependencies."""
        # Clear any previously imported panther modules to test fresh imports
        modules_to_clear = [
            mod for mod in sys.modules.keys() if mod.startswith("panther")
        ]
        for mod in modules_to_clear:
            if mod in sys.modules:
                del sys.modules[mod]

        # These should all import successfully
        modules_to_test = [
            "panther.core.docker_builder.docker_builder",
            "panther.core.experiment_manager",
            "panther.config.core.manager",
            "panther.plugins.plugin_manager",
        ]

        for module_name in modules_to_test:
            try:
                importlib.import_module(module_name)
            except ImportError as e:
                pytest.fail(f"Failed to import {module_name}: {str(e)}")

    def test_package_imports(self):
        """Test that package-level imports work correctly."""
        # Clear any previously imported panther modules
        modules_to_clear = [
            mod for mod in sys.modules.keys() if mod.startswith("panther")
        ]
        for mod in modules_to_clear:
            if mod in sys.modules:
                del sys.modules[mod]

        # Test package imports
        packages_to_test = ["panther.core", "panther.config", "panther.plugins"]

        for package_name in packages_to_test:
            try:
                importlib.import_module(package_name)
            except ImportError as e:
                pytest.fail(f"Failed to import package {package_name}: {str(e)}")

    def test_main_panther_import(self):
        """Test that the main panther package can be imported."""
        # Clear any previously imported panther modules
        modules_to_clear = [
            mod for mod in sys.modules.keys() if mod.startswith("panther")
        ]
        for mod in modules_to_clear:
            if mod in sys.modules:
                del sys.modules[mod]

        try:
            import panther
        except ImportError as e:
            pytest.fail(f"Failed to import main panther package: {str(e)}")
