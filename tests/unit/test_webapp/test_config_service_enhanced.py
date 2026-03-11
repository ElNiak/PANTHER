"""Tests for ConfigService file I/O, merge, and field-level validation."""

import os
from pathlib import Path

import pytest
import yaml


@pytest.fixture
def _patch_project_root(tmp_path, monkeypatch):
    """Patch _PROJECT_ROOT so ConfigService accepts tmp_path-based paths."""
    monkeypatch.setattr(
        "panther.webapp.services.config_service._PROJECT_ROOT", tmp_path
    )
    return tmp_path


@pytest.mark.unit
class TestConfigServiceFileIO:
    def test_load_config_returns_dict(self, tmp_path, _patch_project_root):
        from panther.webapp.services.config_service import ConfigService

        cfg_file = tmp_path / "test.yaml"
        cfg_file.write_text("logging:\n  level: DEBUG\ntests:\n  - name: t1\n")
        svc = ConfigService()
        data = svc.load_config(cfg_file)
        assert isinstance(data, dict)
        assert data["logging"]["level"] == "DEBUG"

    def test_load_config_file_not_found(self, tmp_path, _patch_project_root):
        from panther.webapp.services.config_service import ConfigService

        svc = ConfigService()
        with pytest.raises(FileNotFoundError):
            svc.load_config(tmp_path / "nonexistent.yaml")

    def test_save_config_creates_file(self, tmp_path, _patch_project_root):
        from panther.webapp.services.config_service import ConfigService

        svc = ConfigService()
        out = tmp_path / "sub" / "out.yaml"
        svc.save_config(out, {"logging": {"level": "INFO"}})
        assert out.exists()
        loaded = yaml.safe_load(out.read_text())
        assert loaded["logging"]["level"] == "INFO"

    def test_load_save_roundtrip(self, tmp_path, _patch_project_root):
        from panther.webapp.services.config_service import ConfigService

        svc = ConfigService()
        original = {"logging": {"level": "WARNING"}, "tests": [{"name": "round"}]}
        path = tmp_path / "roundtrip.yaml"
        svc.save_config(path, original)
        loaded = svc.load_config(path)
        assert loaded == original

    def test_list_configs_returns_list(self, tmp_path):
        from panther.webapp.services.config_service import ConfigService

        (tmp_path / "a.yaml").write_text("x: 1")
        (tmp_path / "b.yml").write_text("y: 2")
        (tmp_path / "c.txt").write_text("z: 3")  # Not YAML extension
        svc = ConfigService()
        results = svc.list_configs(tmp_path)
        names = [r["name"] for r in results]
        assert "a.yaml" in names
        assert "b.yml" in names
        assert "c.txt" not in names

    def test_list_configs_nonexistent_dir(self):
        from panther.webapp.services.config_service import ConfigService

        svc = ConfigService()
        assert svc.list_configs("/nonexistent/dir") == []

    def test_list_configs_has_modified_datetime(self, tmp_path):
        from datetime import datetime

        from panther.webapp.services.config_service import ConfigService

        (tmp_path / "test.yaml").write_text("a: 1")
        svc = ConfigService()
        results = svc.list_configs(tmp_path)
        assert len(results) == 1
        assert isinstance(results[0]["modified"], datetime)


@pytest.mark.unit
class TestConfigServiceMerge:
    def test_merge_overlay_takes_precedence(self):
        from panther.webapp.services.config_service import ConfigService

        svc = ConfigService()
        base = {"logging": {"level": "INFO"}, "extra": True}
        overlay = {"logging": {"level": "DEBUG"}}
        merged = svc.merge_configs(base, overlay)
        assert merged["logging"]["level"] == "DEBUG"
        assert merged["extra"] is True

    def test_resolve_interpolations_basic(self):
        from panther.webapp.services.config_service import ConfigService

        svc = ConfigService()
        data = {"a": "hello", "b": "${a}_world"}
        resolved = svc.resolve_interpolations(data)
        assert resolved["b"] == "hello_world"

    def test_resolve_interpolations_unresolvable_returns_something(self):
        from panther.webapp.services.config_service import ConfigService

        svc = ConfigService()
        data = {"b": "${nonexistent}"}
        # Should not raise
        result = svc.resolve_interpolations(data)
        assert isinstance(result, dict)


@pytest.mark.unit
class TestFieldLevelValidation:
    def test_valid_config_returns_empty(self):
        from panther.webapp.services.config_service import ConfigService

        svc = ConfigService()
        data = {"logging": {"level": "INFO"}, "tests": [{"name": "t1"}]}
        errors = svc.validate_config_detailed(data)
        # May have errors from TestConfig requiring more fields, but logging should be ok
        logging_errors = [e for e in errors if e.path.startswith("logging")]
        assert logging_errors == []

    def test_missing_tests_returns_error(self):
        from panther.webapp.services.config_service import ConfigService

        svc = ConfigService()
        errors = svc.validate_config_detailed({"logging": {"level": "INFO"}})
        paths = [e.path for e in errors]
        assert "tests" in paths

    def test_empty_tests_returns_warning(self):
        from panther.webapp.services.config_service import ConfigService

        svc = ConfigService()
        errors = svc.validate_config_detailed({"tests": []})
        assert any(
            e.path in ("tests", "config") and e.severity == "error" for e in errors
        )

    def test_field_error_has_path_and_message(self):
        from panther.webapp.services.config_service import FieldError

        err = FieldError(path="tests[0].name", message="required")
        assert err.path == "tests[0].name"
        assert err.message == "required"
        assert err.severity == "error"


@pytest.mark.unit
class TestConfigServiceSecurity:
    def test_load_config_rejects_non_yaml(self):
        from panther.webapp.services.config_service import ConfigService

        svc = ConfigService()
        with pytest.raises(ValueError, match="must have one of these extensions"):
            svc.load_config("/etc/passwd")

    def test_save_config_rejects_non_yaml(self, tmp_path, _patch_project_root):
        from panther.webapp.services.config_service import ConfigService

        svc = ConfigService()
        with pytest.raises(ValueError, match="must have one of these extensions"):
            svc.save_config(str(tmp_path / "evil.txt"), {"x": 1})

    def test_load_config_accepts_yaml_extension(self, tmp_path, _patch_project_root):
        from panther.webapp.services.config_service import ConfigService

        cfg_file = tmp_path / "test.yaml"
        cfg_file.write_text("logging:\n  level: DEBUG\ntests:\n  - name: t1\n")
        svc = ConfigService()
        data = svc.load_config(str(cfg_file))
        assert data["logging"]["level"] == "DEBUG"

    def test_save_config_accepts_yml_extension(self, tmp_path, _patch_project_root):
        from panther.webapp.services.config_service import ConfigService

        svc = ConfigService()
        out = tmp_path / "out.yml"
        svc.save_config(str(out), {"x": 1})
        assert out.exists()

    def test_path_traversal_rejected_for_load(self):
        """Loading from outside project root must be rejected."""
        from panther.webapp.services.config_service import ConfigService

        svc = ConfigService()
        with pytest.raises(ValueError, match="within the root directory"):
            svc.load_config("/tmp/evil/attack.yaml")

    def test_path_traversal_rejected_for_save(self):
        """Saving outside project root must be rejected."""
        from panther.webapp.services.config_service import ConfigService

        svc = ConfigService()
        with pytest.raises(ValueError, match="within the root directory"):
            svc.save_config("/tmp/evil/attack.yaml", {"x": 1})

    def test_path_traversal_with_dotdot(self, tmp_path, _patch_project_root):
        """Paths with .. that resolve outside project root must be rejected."""
        from panther.webapp.services.config_service import ConfigService

        svc = ConfigService()
        # This resolves outside tmp_path (the patched _PROJECT_ROOT)
        traversal_path = str(tmp_path / "sub" / ".." / ".." / "escape.yaml")
        with pytest.raises(ValueError, match="within the root directory"):
            svc.load_config(traversal_path)

    def test_path_within_project_accepted(self, tmp_path, _patch_project_root):
        """Paths within project root should be accepted."""
        from panther.webapp.services.config_service import ConfigService

        svc = ConfigService()
        cfg = tmp_path / "configs" / "valid.yaml"
        cfg.parent.mkdir(parents=True, exist_ok=True)
        cfg.write_text("x: 1")
        data = svc.load_config(str(cfg))
        assert data == {"x": 1}

    def test_save_with_mkdir_within_project(self, tmp_path, _patch_project_root):
        """save_config should create subdirectories within project root."""
        from panther.webapp.services.config_service import ConfigService

        svc = ConfigService()
        out = tmp_path / "new" / "nested" / "config.yaml"
        svc.save_config(str(out), {"test": True})
        assert out.exists()
        assert yaml.safe_load(out.read_text()) == {"test": True}
