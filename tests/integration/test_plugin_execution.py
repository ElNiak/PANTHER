import pytest
from plugins.plugin_loader import load_plugins

def test_load_plugins_valid():
    plugins = load_plugins("path/to/plugins")
    assert len(plugins) > 0
    assert all(plugin.is_valid() for plugin in plugins)

def test_load_plugins_invalid():
    with pytest.raises(FileNotFoundError):
        load_plugins("invalid/path")
