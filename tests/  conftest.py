import pytest
import tempfile
import os

@pytest.fixture
def mock_plugin_directory():
    with tempfile.TemporaryDirectory() as tempdir:
        plugin_path = os.path.join(tempdir, "dummy_plugin.py")
        with open(plugin_path, "w") as f:
            f.write("class Plugin: pass")
        yield tempdir
