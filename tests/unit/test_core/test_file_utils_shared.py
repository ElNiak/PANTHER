"""Tests for shared FileUtils and ConfigurationLoader methods."""

from pathlib import Path

import pytest

from panther.core.utils.file_utils import (
    ConfigurationLoader,
    FileOperationError,
    FileUtils,
)


class TestFindProjectRoot:
    def test_finds_marker_in_directory(self, tmp_path):
        (tmp_path / "pyproject.toml").write_text("[project]")
        result = FileUtils.find_project_root(start_path=tmp_path)
        assert result == tmp_path

    def test_finds_marker_in_parent(self, tmp_path):
        (tmp_path / "pyproject.toml").write_text("[project]")
        child = tmp_path / "a" / "b"
        child.mkdir(parents=True)
        result = FileUtils.find_project_root(start_path=child)
        assert result == tmp_path

    def test_fallback_when_marker_missing(self, tmp_path):
        child = tmp_path / "no_marker"
        child.mkdir()
        # Should not raise; falls back to cwd
        result = FileUtils.find_project_root(
            start_path=child, marker="nonexistent_marker.xyz"
        )
        assert isinstance(result, Path)

    def test_custom_marker(self, tmp_path):
        (tmp_path / "setup.cfg").write_text("[metadata]")
        result = FileUtils.find_project_root(start_path=tmp_path, marker="setup.cfg")
        assert result == tmp_path


class TestValidatePathWithinRoot:
    def test_accepts_valid_path(self, tmp_path):
        config = tmp_path / "config.yaml"
        config.touch()
        result = FileUtils.validate_path_within_root(
            config, tmp_path, (".yaml", ".yml")
        )
        assert result == config.resolve()

    def test_rejects_wrong_suffix(self, tmp_path):
        bad = tmp_path / "config.txt"
        bad.touch()
        with pytest.raises(ValueError, match="extensions"):
            FileUtils.validate_path_within_root(bad, tmp_path, (".yaml", ".yml"))

    def test_rejects_path_outside_root(self, tmp_path):
        outside = tmp_path.parent / "outside.yaml"
        with pytest.raises(ValueError, match="root directory"):
            FileUtils.validate_path_within_root(outside, tmp_path, (".yaml",))

    def test_allows_any_suffix_when_empty(self, tmp_path):
        txt = tmp_path / "notes.txt"
        txt.touch()
        result = FileUtils.validate_path_within_root(txt, tmp_path)
        assert result == txt.resolve()


class TestReadTextBounded:
    def test_reads_normal_file(self, tmp_path):
        f = tmp_path / "hello.txt"
        f.write_text("hello world")
        assert FileUtils.read_text_bounded(f) == "hello world"

    def test_truncates_oversized_file(self, tmp_path):
        f = tmp_path / "big.txt"
        content = "x" * 1000
        f.write_text(content)
        result = FileUtils.read_text_bounded(f, max_bytes=100)
        assert len(result) == 100

    def test_raises_for_missing_file(self, tmp_path):
        with pytest.raises(FileOperationError):
            FileUtils.read_text_bounded(tmp_path / "missing.txt")


class TestListConfigsRecursive:
    def test_lists_nested_configs(self, tmp_path):
        base = tmp_path / "configs"
        (base / "sub").mkdir(parents=True)
        (base / "a.yaml").write_text("tests: []")
        (base / "sub" / "b.yml").write_text("tests: []")
        results = ConfigurationLoader.list_configs_recursive(base)
        names = {r["name"] for r in results}
        assert names == {"a.yaml", "b.yml"}
        # Check category
        for r in results:
            if r["name"] == "b.yml":
                assert r["category"] == "sub"

    def test_returns_empty_for_missing_dir(self, tmp_path):
        assert ConfigurationLoader.list_configs_recursive(tmp_path / "nope") == []


class TestExtractConfigSummary:
    def test_valid_config(self, tmp_path):
        config = tmp_path / "test.yaml"
        config.write_text(
            """
tests:
  - name: my-test
    network_environment:
      type: docker_compose
    services:
      server:
        protocol:
          name: quic
"""
        )
        summary = ConfigurationLoader.extract_config_summary(config)
        assert summary["test_count"] == 1
        assert summary["test_names"] == ["my-test"]
        assert "server" in summary["services"]
        assert "quic" in summary["protocols"]
        assert summary["environment"] == "docker_compose"

    def test_invalid_yaml(self, tmp_path):
        config = tmp_path / "bad.yaml"
        config.write_text(": : invalid")
        summary = ConfigurationLoader.extract_config_summary(config)
        assert summary["test_count"] == 0

    def test_non_dict_yaml(self, tmp_path):
        config = tmp_path / "list.yaml"
        config.write_text("- item1\n- item2")
        summary = ConfigurationLoader.extract_config_summary(config)
        assert summary["test_count"] == 0
