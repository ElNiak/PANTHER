# Task 21: Write Comprehensive Tests for panther.api

## Goal
Write thorough unit and integration tests for all panther.api modules.

## Prerequisites
- Tasks 18-20 completed (all API modules implemented)

## Steps

### Step 1: Create test structure
```bash
mkdir -p tests/unit/test_api
touch tests/unit/test_api/__init__.py
```

### Step 2: Write unit tests with mocked managers

Each API function delegates to a manager. Unit tests should mock the managers and verify:
1. The correct manager method is called
2. Arguments are passed correctly
3. Return values are transformed to plain dicts
4. Exceptions are propagated correctly

```python
# tests/unit/test_api/test_api_config_unit.py
"""Unit tests for config API with mocked ConfigurationManager."""
import pytest
from unittest.mock import MagicMock, patch


class TestLoadConfig:
    @patch("panther.api.config.<manager_import_path>")
    def test_delegates_to_manager(self, mock_manager):
        from panther.api.config import load_config
        # Setup mock
        mock_manager.return_value.load.return_value = MagicMock()
        # Call
        result = load_config("/path/to/config.yaml")
        # Verify
        mock_manager.return_value.load.assert_called_once()

    def test_file_not_found(self):
        from panther.api.config import load_config
        with pytest.raises(FileNotFoundError):
            load_config("/nonexistent/file.yaml")


class TestValidateConfig:
    def test_returns_validation_result(self):
        from panther.api.config import validate_config
        # Create a minimal valid config
        # result = validate_config(config)
        # assert "valid" in result
        # assert "errors" in result
        pass


class TestSaveConfig:
    def test_creates_file(self, tmp_path):
        from panther.api.config import save_config
        output = tmp_path / "output.yaml"
        # config = create_test_config()
        # save_config(config, output)
        # assert output.exists()
        pass


class TestGetConfigSchema:
    def test_returns_json_schema(self):
        from panther.api.config import get_config_schema
        schema = get_config_schema()
        assert isinstance(schema, dict)


class TestMergeConfigs:
    def test_overlay_wins(self):
        from panther.api.config import merge_configs
        # base = {"logging": {"level": "INFO"}}
        # overlay = {"logging": {"level": "DEBUG"}}
        # result = merge_configs(base, overlay)
        # Verify overlay values take precedence
        pass
```

```python
# tests/unit/test_api/test_api_plugins_unit.py
"""Unit tests for plugins API with mocked PluginManager."""
import pytest
from unittest.mock import MagicMock, patch


class TestListPlugins:
    def test_returns_list_of_dicts(self):
        from panther.api.plugins import list_plugins
        result = list_plugins()
        assert isinstance(result, list)
        for item in result:
            assert isinstance(item, dict)
            assert "name" in item

    def test_includes_all_types(self):
        """Should include IUTs, testers, protocols, environments."""
        from panther.api.plugins import list_plugins
        result = list_plugins()
        # Verify multiple plugin types are represented
        pass


class TestGetPluginInfo:
    def test_known_plugin(self):
        from panther.api.plugins import get_plugin_info
        # info = get_plugin_info("panther_ivy")
        # assert info["name"] == "panther_ivy"
        pass

    def test_unknown_plugin(self):
        from panther.api.plugins import get_plugin_info
        with pytest.raises(KeyError):
            get_plugin_info("nonexistent_plugin")
```

### Step 3: Write integration tests

```python
# tests/integration/test_api/test_api_integration.py
"""Integration tests for panther.api (requires Docker)."""
import pytest


@pytest.mark.integration
class TestConfigRoundTrip:
    def test_load_validate_save_reload(self, tmp_path):
        """Load a config, validate it, save it, reload, compare."""
        from panther.api.config import load_config, validate_config, save_config

        # Load example config
        config = load_config(
            "experiment-config/base/experiment_config_example_minimal.yaml"
        )

        # Validate
        result = validate_config(config)
        assert result["valid"]

        # Save
        output = tmp_path / "saved.yaml"
        save_config(config, output)
        assert output.exists()

        # Reload
        reloaded = load_config(str(output))

        # Compare (fields should match)


@pytest.mark.integration
class TestPluginDiscovery:
    def test_list_all_plugins(self):
        """Should discover at least some plugins."""
        from panther.api.plugins import list_plugins
        plugins = list_plugins()
        assert len(plugins) > 0

    def test_list_protocols(self):
        from panther.api.plugins import list_protocols
        protocols = list_protocols()
        # Should include at least QUIC
        names = [p["name"] for p in protocols]
        assert "quic" in names or len(names) > 0


@pytest.mark.integration
@pytest.mark.requires_docker
class TestExperimentLifecycle:
    def test_create_and_check_status(self):
        """Create an experiment and verify it has a status."""
        from panther.api.config import load_config
        from panther.api.experiments import create_experiment, get_status

        config = load_config(
            "experiment-config/base/experiment_config_example_minimal.yaml"
        )
        exp_id = create_experiment(config)
        assert isinstance(exp_id, str)

        status = get_status(exp_id)
        assert "status" in status


@pytest.mark.integration
class TestSchemaGeneration:
    def test_config_schema_valid(self):
        """Generated schema should be valid JSON Schema."""
        from panther.api.schemas import get_config_schema
        schema = get_config_schema()
        assert isinstance(schema, dict)
        # Should have standard JSON Schema fields
        assert "properties" in schema or "type" in schema or "$defs" in schema
```

## Verification
```bash
# Unit tests (no Docker required)
pytest tests/unit/test_api/ -v -m "not integration"

# Integration tests (requires Docker)
pytest tests/integration/test_api/ -v -m integration
```

## Commit Message
```
test(api): add comprehensive tests for panther.api

Unit tests with mocked managers and integration tests for config
round-trip, plugin discovery, experiment lifecycle, and schema
generation.
```

## Files Created
- `tests/unit/test_api/__init__.py`
- `tests/unit/test_api/test_api_config_unit.py`
- `tests/unit/test_api/test_api_plugins_unit.py`
- `tests/integration/test_api/__init__.py`
- `tests/integration/test_api/test_api_integration.py`
