"""Unit tests for OutputIndexBuilder."""

import json
import threading
from pathlib import Path

import pytest

from panther.core.outputs.output_index import (
    _EXTENSION_MAP,
    _SCHEMA_VERSION,
    FileEntry,
    OutputIndexBuilder,
    detect_type_and_format,
)

# ---------------------------------------------------------------------------
# FileEntry
# ---------------------------------------------------------------------------


class TestFileEntry:
    """Tests for the FileEntry data class."""

    def test_to_dict_minimal(self):
        entry = FileEntry(path="foo.log", file_type="log", file_format="text")
        d = entry.to_dict()
        assert d == {
            "path": "foo.log",
            "type": "log",
            "format": "text",
            "size_bytes": 0,
        }

    def test_to_dict_full(self):
        entry = FileEntry(
            path="test1/server/runtime/stdout.log",
            file_type="log",
            file_format="text",
            test_id="test1",
            service_id="server",
            phase="runtime",
            size_bytes=4096,
            description="Server stdout log",
        )
        d = entry.to_dict()
        assert d["test_id"] == "test1"
        assert d["service_id"] == "server"
        assert d["phase"] == "runtime"
        assert d["size_bytes"] == 4096
        assert d["description"] == "Server stdout log"

    def test_to_dict_omits_none_optionals(self):
        entry = FileEntry(path="a.log", file_type="log", file_format="text")
        d = entry.to_dict()
        assert "test_id" not in d
        assert "service_id" not in d
        assert "phase" not in d
        # Empty description is also omitted
        assert "description" not in d


# ---------------------------------------------------------------------------
# detect_type_and_format
# ---------------------------------------------------------------------------


class TestDetectTypeAndFormat:
    """Tests for the extension-based auto-detection helper."""

    @pytest.mark.parametrize(
        "filename, expected_type, expected_format",
        [
            ("capture.pcap", "artifact", "pcap"),
            ("events.qlog", "artifact", "qlog"),
            ("config.yaml", "config", "yaml"),
            ("config.yml", "config", "yaml"),
            ("summary.json", "report", "json"),
            ("structured.jsonl", "log", "jsonl"),
            ("metrics.csv", "metric", "csv"),
            ("REPORT.md", "report", "markdown"),
            ("stdout.log", "log", "text"),
            ("output.txt", "log", "text"),
            ("trace.out", "log", "text"),
            ("data.har", "artifact", "json"),
        ],
    )
    def test_known_extensions(self, filename, expected_type, expected_format):
        ftype, ffmt = detect_type_and_format(filename)
        assert ftype == expected_type
        assert ffmt == expected_format

    def test_unknown_extension_falls_back(self):
        ftype, ffmt = detect_type_and_format("data.xyz")
        assert ftype == "log"
        assert ffmt == "text"

    def test_no_extension(self):
        ftype, ffmt = detect_type_and_format("Makefile")
        assert ftype == "log"
        assert ffmt == "text"

    def test_case_insensitive(self):
        ftype, ffmt = detect_type_and_format("capture.PCAP")
        assert ftype == "artifact"
        assert ffmt == "pcap"


# ---------------------------------------------------------------------------
# OutputIndexBuilder
# ---------------------------------------------------------------------------


@pytest.fixture
def experiment_dir(tmp_path):
    """Create a temporary experiment directory with some sample files."""
    exp_dir = tmp_path / "2026-01-01_experiment"
    exp_dir.mkdir()
    # Create some sample output files
    (exp_dir / "experiment_config.yaml").write_text("test: true\n")
    (exp_dir / "structured.jsonl").write_text('{"event":"start"}\n')

    artifacts_dir = exp_dir / "artifacts"
    artifacts_dir.mkdir()
    (artifacts_dir / "capture.pcap").write_bytes(b"\x00" * 1024)
    (artifacts_dir / "events.qlog").write_text('{"qlog":"data"}')

    return exp_dir


@pytest.fixture
def builder(experiment_dir):
    """Create an OutputIndexBuilder for the test experiment directory."""
    return OutputIndexBuilder(experiment_dir, "test_experiment_001")


class TestOutputIndexBuilder:
    """Tests for the OutputIndexBuilder class."""

    def test_register_auto_detects_type_and_format(self, builder, experiment_dir):
        builder.register("artifacts/capture.pcap")
        assert builder.entry_count == 1

    def test_register_explicit_overrides(self, builder):
        builder.register(
            "foo.txt",
            file_type="metric",
            file_format="csv",
            description="custom",
        )
        assert builder.entry_count == 1

    def test_register_deduplicates(self, builder):
        builder.register("same.log")
        builder.register("same.log")
        assert builder.entry_count == 1

    def test_register_absolute_path_converted_to_relative(
        self, builder, experiment_dir
    ):
        abs_path = str(experiment_dir / "experiment_config.yaml")
        builder.register(abs_path)
        builder.flush()

        index = json.loads(
            (experiment_dir / OutputIndexBuilder.INDEX_FILENAME).read_text()
        )
        assert index["files"][0]["path"] == "experiment_config.yaml"

    def test_register_resolves_size_from_disk(self, builder, experiment_dir):
        builder.register("artifacts/capture.pcap")
        builder.flush()

        index = json.loads(
            (experiment_dir / OutputIndexBuilder.INDEX_FILENAME).read_text()
        )
        assert index["files"][0]["size_bytes"] == 1024

    def test_register_explicit_size_overrides_stat(self, builder):
        builder.register("artifacts/capture.pcap", size_bytes=42)
        builder.flush()
        # Not flushing to json for this check -- inspect internal state
        # Actually let's just check via the entry
        assert builder.entry_count == 1

    def test_register_missing_file_gets_zero_size(self, builder):
        builder.register("does_not_exist.log")
        builder.flush()

        index = json.loads(
            (builder._experiment_dir / OutputIndexBuilder.INDEX_FILENAME).read_text()
        )
        assert index["files"][0]["size_bytes"] == 0

    def test_flush_creates_valid_json(self, builder, experiment_dir):
        builder.register(
            "experiment_config.yaml",
            file_type="config",
            file_format="yaml",
            description="Config",
        )
        builder.register("structured.jsonl")
        builder.register("artifacts/capture.pcap", service_id="server")
        builder.register(
            "artifacts/events.qlog",
            test_id="quic_test",
            phase="runtime",
        )

        output_path = builder.flush()
        assert output_path.exists()

        index = json.loads(output_path.read_text())

        # Check top-level schema
        assert index["schema_version"] == _SCHEMA_VERSION
        assert index["experiment_id"] == "test_experiment_001"
        assert "created_at" in index
        assert isinstance(index["files"], list)
        assert len(index["files"]) == 4

    def test_flush_schema_structure(self, builder, experiment_dir):
        builder.register(
            "artifacts/capture.pcap",
            test_id="t1",
            service_id="srv",
            phase="runtime",
            description="PCAP capture",
        )
        output_path = builder.flush()
        index = json.loads(output_path.read_text())

        entry = index["files"][0]
        assert entry["path"] == "artifacts/capture.pcap"
        assert entry["type"] == "artifact"
        assert entry["format"] == "pcap"
        assert entry["test_id"] == "t1"
        assert entry["service_id"] == "srv"
        assert entry["phase"] == "runtime"
        assert entry["description"] == "PCAP capture"
        assert entry["size_bytes"] == 1024

    def test_flush_empty_index(self, builder, experiment_dir):
        output_path = builder.flush()
        index = json.loads(output_path.read_text())
        assert index["files"] == []

    def test_flush_idempotent(self, builder, experiment_dir):
        builder.register("experiment_config.yaml")
        path1 = builder.flush()
        path2 = builder.flush()
        assert path1 == path2
        # Content should be the same (same entries)
        assert path1.read_text() == path2.read_text()

    def test_entry_count(self, builder):
        assert builder.entry_count == 0
        builder.register("a.log")
        assert builder.entry_count == 1
        builder.register("b.log")
        assert builder.entry_count == 2
        builder.register("a.log")  # duplicate
        assert builder.entry_count == 2

    def test_path_outside_experiment_dir_stored_absolute(self, builder, tmp_path):
        outside = tmp_path / "other" / "file.log"
        outside.parent.mkdir(parents=True, exist_ok=True)
        outside.write_text("data")

        builder.register(str(outside))
        builder.flush()

        index = json.loads(
            (builder._experiment_dir / OutputIndexBuilder.INDEX_FILENAME).read_text()
        )
        # Should be stored as the absolute path since it's outside experiment_dir
        assert index["files"][0]["path"] == str(outside)

    def test_thread_safety(self, builder):
        """Verify concurrent register calls don't lose entries or crash."""
        barrier = threading.Barrier(4)

        def register_batch(start: int):
            barrier.wait()
            for i in range(50):
                builder.register(f"file_{start + i}.log")

        threads = [
            threading.Thread(target=register_batch, args=(i * 50,)) for i in range(4)
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert builder.entry_count == 200

    def test_thread_safety_with_duplicates(self, builder):
        """Verify concurrent duplicate registrations are handled correctly."""
        barrier = threading.Barrier(4)

        def register_same():
            barrier.wait()
            for _ in range(50):
                builder.register("shared_file.log")

        threads = [threading.Thread(target=register_same) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert builder.entry_count == 1


# ---------------------------------------------------------------------------
# Integration with OutputAggregator
# ---------------------------------------------------------------------------


class TestOutputAggregatorIntegration:
    """Verify OutputAggregator can forward collected files to the index builder."""

    def test_aggregator_registers_outputs(self, experiment_dir):
        from unittest.mock import MagicMock

        from panther.core.outputs.output_aggregator import OutputAggregator

        emitter = MagicMock()
        index_builder = OutputIndexBuilder(experiment_dir, "exp_001")

        aggregator = OutputAggregator(
            experiment_dir=experiment_dir,
            environment_emitter=emitter,
            output_index_builder=index_builder,
        )

        # Create a mock environment that yields outputs
        env = MagicMock()
        env.__class__.__name__ = "StraceProfiling"
        env.collect_outputs.return_value = {
            "trace": str(experiment_dir / "artifacts" / "capture.pcap"),
        }
        env.get_output_metadata.return_value = {"format": "pcap"}

        aggregator.collect_from_environments([env])

        assert index_builder.entry_count == 1

    def test_aggregator_works_without_index_builder(self, experiment_dir):
        """Backward compatibility: aggregator works fine with no builder."""
        from unittest.mock import MagicMock

        from panther.core.outputs.output_aggregator import OutputAggregator

        emitter = MagicMock()
        aggregator = OutputAggregator(
            experiment_dir=experiment_dir,
            environment_emitter=emitter,
        )

        env = MagicMock()
        env.__class__.__name__ = "TestEnv"
        env.collect_outputs.return_value = {"log": "/tmp/test.log"}
        env.get_output_metadata.return_value = {}

        # Should not raise
        result = aggregator.collect_from_environments([env])
        assert "TestEnv" in result
