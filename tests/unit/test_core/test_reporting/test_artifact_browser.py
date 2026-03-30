"""Unit tests for ArtifactBrowser."""

import json
from pathlib import Path

import pytest

from panther.core.reporting.artifact_browser import ArtifactBrowser

# -- Helpers -----------------------------------------------------------------


def _write_index(experiment_dir: Path, files: list[dict]) -> Path:
    """Write an output_index.json manifest.

    Args:
        experiment_dir: Root experiment directory.
        files: List of file entry dicts.

    Returns:
        Path to the created index file.
    """
    index = {
        "schema_version": "1.0",
        "experiment_id": "test-exp",
        "created_at": "2025-01-15T10:00:00+00:00",
        "files": files,
    }
    index_path = experiment_dir / "output_index.json"
    with open(index_path, "w", encoding="utf-8") as fh:
        json.dump(index, fh)
    return index_path


SAMPLE_INDEX_FILES = [
    {
        "path": "structured.jsonl",
        "type": "log",
        "format": "jsonl",
        "size_bytes": 1024,
        "test_id": "t1",
        "service_id": "picoquic",
        "phase": "runtime",
        "description": "Main log file",
    },
    {
        "path": "artifacts/capture.pcap",
        "type": "artifact",
        "format": "pcap",
        "size_bytes": 50000,
        "test_id": "t1",
        "service_id": "picoquic",
        "phase": "runtime",
    },
    {
        "path": "artifacts/trace.qlog",
        "type": "artifact",
        "format": "qlog",
        "size_bytes": 12000,
        "test_id": "t1",
        "service_id": "aioquic",
        "phase": "runtime",
    },
    {
        "path": "report.json",
        "type": "report",
        "format": "json",
        "size_bytes": 2048,
    },
    {
        "path": "compile.log",
        "type": "log",
        "format": "text",
        "size_bytes": 500,
        "service_id": "picoquic",
        "phase": "compile",
    },
]


# -- Fixtures ----------------------------------------------------------------


@pytest.fixture()
def indexed_dir(tmp_path):
    """Create a tmp directory with an output_index.json."""
    _write_index(tmp_path, SAMPLE_INDEX_FILES)
    return tmp_path


@pytest.fixture()
def browser(indexed_dir):
    """Return an ArtifactBrowser pointed at the indexed directory."""
    return ArtifactBrowser(indexed_dir)


@pytest.fixture()
def file_dir(tmp_path):
    """Create a tmp directory with actual files (no index)."""
    (tmp_path / "structured.jsonl").write_text("{}\n")
    artifacts = tmp_path / "artifacts"
    artifacts.mkdir()
    (artifacts / "capture.pcap").write_bytes(b"\x00" * 100)
    (artifacts / "trace.qlog").write_text('{"qlog": true}')
    (tmp_path / "report.json").write_text("{}")
    (tmp_path / "compile.log").write_text("compiling...")
    return tmp_path


# -- Tests: Index-based browsing ---------------------------------------------


@pytest.mark.unit
class TestArtifactBrowserIndex:
    """Tests for browsing via output_index.json."""

    def test_list_all_returns_all_entries(self, browser):
        """Listing with no filters returns all entries."""
        results = browser.list_artifacts()
        assert len(results) == len(SAMPLE_INDEX_FILES)

    def test_entries_are_dicts(self, browser):
        """Each result is a dict with standard fields."""
        for entry in browser.list_artifacts():
            assert isinstance(entry, dict)
            assert "path" in entry
            assert "type" in entry
            assert "format" in entry
            assert "size_bytes" in entry

    def test_entries_have_all_fields(self, browser):
        """All standard fields are present (even if None)."""
        for entry in browser.list_artifacts():
            for key in (
                "path",
                "type",
                "format",
                "test_id",
                "service_id",
                "phase",
                "size_bytes",
                "description",
            ):
                assert key in entry

    def test_filter_by_test_id(self, browser):
        """Filter by test_id returns matching entries."""
        results = browser.list_artifacts(test_id="t1")
        assert len(results) == 3
        assert all(r["test_id"] == "t1" for r in results)

    def test_filter_by_service_id(self, browser):
        """Filter by service_id returns matching entries."""
        results = browser.list_artifacts(service_id="picoquic")
        assert len(results) == 3
        assert all(r["service_id"] == "picoquic" for r in results)

    def test_filter_by_artifact_type(self, browser):
        """Filter by artifact type."""
        results = browser.list_artifacts(artifact_type="artifact")
        assert len(results) == 2
        assert all(r["type"] == "artifact" for r in results)

    def test_filter_by_phase(self, browser):
        """Filter by execution phase."""
        results = browser.list_artifacts(phase="compile")
        assert len(results) == 1
        assert results[0]["path"] == "compile.log"

    def test_combined_filters(self, browser):
        """Multiple filters apply with AND semantics."""
        results = browser.list_artifacts(
            service_id="picoquic", artifact_type="artifact"
        )
        assert len(results) == 1
        assert results[0]["path"] == "artifacts/capture.pcap"

    def test_no_match_returns_empty(self, browser):
        """Filters that match nothing return an empty list."""
        results = browser.list_artifacts(test_id="nonexistent")
        assert results == []


# -- Tests: Directory-based fallback -----------------------------------------


@pytest.mark.unit
class TestArtifactBrowserDirectoryFallback:
    """Tests for directory walking when no index exists."""

    def test_discovers_files_without_index(self, file_dir):
        """Files are discovered by walking the directory tree."""
        browser = ArtifactBrowser(file_dir)
        results = browser.list_artifacts()
        paths = {r["path"] for r in results}
        assert "structured.jsonl" in paths
        assert "report.json" in paths
        assert "compile.log" in paths

    def test_infers_type_from_extension(self, file_dir):
        """Type and format are inferred from file extensions."""
        browser = ArtifactBrowser(file_dir)
        results = browser.list_artifacts()
        by_path = {r["path"]: r for r in results}
        pcap = by_path.get("artifacts/capture.pcap")
        assert pcap is not None
        assert pcap["type"] == "artifact"
        assert pcap["format"] == "pcap"

    def test_fallback_entries_have_size(self, file_dir):
        """Fallback entries include file size."""
        browser = ArtifactBrowser(file_dir)
        results = browser.list_artifacts()
        by_path = {r["path"]: r for r in results}
        pcap = by_path.get("artifacts/capture.pcap")
        assert pcap is not None
        assert pcap["size_bytes"] == 100

    def test_fallback_entries_have_none_metadata(self, file_dir):
        """Fallback entries have None for test_id/service_id/phase."""
        browser = ArtifactBrowser(file_dir)
        for entry in browser.list_artifacts():
            assert entry["test_id"] is None
            assert entry["service_id"] is None
            assert entry["phase"] is None

    def test_filter_by_type_on_fallback(self, file_dir):
        """Filtering works on fallback entries."""
        browser = ArtifactBrowser(file_dir)
        results = browser.list_artifacts(artifact_type="artifact")
        assert len(results) == 2
        formats = {r["format"] for r in results}
        assert "pcap" in formats
        assert "qlog" in formats


# -- Tests: Edge cases -------------------------------------------------------


@pytest.mark.unit
class TestArtifactBrowserEdgeCases:
    """Edge case handling."""

    def test_empty_directory(self, tmp_path):
        """Empty directory returns no artifacts."""
        browser = ArtifactBrowser(tmp_path)
        assert browser.list_artifacts() == []

    def test_nonexistent_directory(self, tmp_path):
        """Nonexistent directory returns no artifacts."""
        browser = ArtifactBrowser(tmp_path / "does_not_exist")
        assert browser.list_artifacts() == []

    def test_corrupt_index_falls_back(self, tmp_path):
        """Corrupt index file triggers directory walk fallback."""
        index_path = tmp_path / "output_index.json"
        index_path.write_text("not valid json {{{")
        (tmp_path / "data.csv").write_text("a,b,c\n")

        browser = ArtifactBrowser(tmp_path)
        results = browser.list_artifacts()
        # Should find the csv and the corrupt json via directory walk
        paths = {r["path"] for r in results}
        assert "data.csv" in paths

    def test_index_missing_files_key(self, tmp_path):
        """Index with no 'files' key returns empty list."""
        index_path = tmp_path / "output_index.json"
        index_path.write_text('{"schema_version": "1.0"}')
        browser = ArtifactBrowser(tmp_path)
        results = browser.list_artifacts()
        assert results == []

    def test_caching(self, indexed_dir):
        """Entries are cached after first load."""
        browser = ArtifactBrowser(indexed_dir)
        first = browser.list_artifacts()
        # Modify the index file
        _write_index(
            indexed_dir,
            [{"path": "new.txt", "type": "log", "format": "text", "size_bytes": 0}],
        )
        # Should still return cached results
        second = browser.list_artifacts()
        assert len(second) == len(first)

    def test_normalize_fills_missing_fields(self, tmp_path):
        """Index entries with missing optional fields get defaults."""
        _write_index(tmp_path, [{"path": "minimal.txt"}])
        browser = ArtifactBrowser(tmp_path)
        results = browser.list_artifacts()
        assert len(results) == 1
        entry = results[0]
        assert entry["path"] == "minimal.txt"
        assert entry["type"] == "log"
        assert entry["format"] == "text"
        assert entry["test_id"] is None
        assert entry["service_id"] is None
        assert entry["phase"] is None
        assert entry["size_bytes"] == 0
        assert entry["description"] == ""
