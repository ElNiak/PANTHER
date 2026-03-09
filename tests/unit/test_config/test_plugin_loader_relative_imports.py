"""Tests for plugin loader relative import support."""

import sys

import pytest

from panther.plugins.core.plugin_loader_utils import PluginManagerUtils


class TestComputePackagePath:
    def test_returns_none_for_standalone_file(self, tmp_path):
        """File not in a package should return None."""
        f = tmp_path / "standalone.py"
        f.write_text("x = 1")
        assert PluginManagerUtils._compute_package_path(f) is None

    def test_returns_package_name_for_single_level(self, tmp_path):
        """File in a single package level."""
        pkg = tmp_path / "mypkg"
        pkg.mkdir()
        (pkg / "__init__.py").write_text("")
        f = pkg / "mod.py"
        f.write_text("x = 1")
        assert PluginManagerUtils._compute_package_path(f) == "mypkg"

    def test_returns_dotted_path_for_nested_package(self, tmp_path):
        """File in a nested package."""
        outer = tmp_path / "outer"
        outer.mkdir()
        (outer / "__init__.py").write_text("")
        inner = outer / "inner"
        inner.mkdir()
        (inner / "__init__.py").write_text("")
        f = inner / "mod.py"
        f.write_text("x = 1")
        assert PluginManagerUtils._compute_package_path(f) == "outer.inner"


class TestRelativeImportSupport:
    def test_module_in_package_gets_package_set(self, tmp_path):
        """Module loaded from a package should have __package__ set."""
        pkg = tmp_path / "testpkg"
        pkg.mkdir()
        (pkg / "__init__.py").write_text("")
        (pkg / "_helper.py").write_text("VALUE = 42")
        (pkg / "main.py").write_text("from ._helper import VALUE\nresult = VALUE")

        # Add tmp_path to sys.path temporarily so imports can resolve
        sys.path.insert(0, str(tmp_path))
        try:
            module = PluginManagerUtils.load_module_from_file(
                pkg / "main.py", "testpkg_main"
            )
            assert module.__package__ == "testpkg"
            assert module.result == 42
        finally:
            sys.path.pop(0)
            # Clean up sys.modules
            for key in list(sys.modules):
                if "testpkg" in key:
                    del sys.modules[key]

    def test_standalone_module_has_no_package(self, tmp_path):
        """Module not in a package should not have __package__ set."""
        f = tmp_path / "standalone.py"
        f.write_text("x = 1")
        try:
            module = PluginManagerUtils.load_module_from_file(f, "standalone_test")
            assert not module.__package__  # Empty string or None
            assert module.x == 1
        finally:
            sys.modules.pop("standalone_test", None)

    def test_module_registered_under_both_names(self, tmp_path):
        """Module in a package should be in sys.modules under both names."""
        pkg = tmp_path / "regpkg"
        pkg.mkdir()
        (pkg / "__init__.py").write_text("")
        (pkg / "mod.py").write_text("x = 1")

        sys.path.insert(0, str(tmp_path))
        try:
            PluginManagerUtils.load_module_from_file(pkg / "mod.py", "regpkg_mod")
            assert "regpkg_mod" in sys.modules
            assert "regpkg.mod" in sys.modules
        finally:
            sys.path.pop(0)
            for key in list(sys.modules):
                if "regpkg" in key:
                    del sys.modules[key]
