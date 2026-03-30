"""Unit tests for the centralized JsonlWriter and JsonlLogHandler."""

import json
import logging
import threading

import pytest

from panther.core.utils.jsonl_writer import JsonlLogHandler, JsonlWriter
from panther.core.utils.structured_formatter import StructuredJsonFormatter

pytestmark = pytest.mark.unit


# -- JsonlWriter tests -------------------------------------------------------


class TestJsonlWriterBasic:
    """Core write/read/close behaviour."""

    def test_write_line_basic(self, tmp_path):
        """Write 3 JSON lines and read them back."""
        path = tmp_path / "test.jsonl"
        writer = JsonlWriter(path)
        try:
            for i in range(3):
                writer.write_line(json.dumps({"index": i}))

            lines = path.read_text().splitlines()
            assert len(lines) == 3
            for i, line in enumerate(lines):
                record = json.loads(line)
                assert record["index"] == i
        finally:
            writer.close()

    def test_write_line_adds_newline(self, tmp_path):
        """Each call appends exactly one newline, even if the line has none."""
        path = tmp_path / "test.jsonl"
        writer = JsonlWriter(path)
        try:
            writer.write_line('{"a": 1}')
            writer.write_line('{"b": 2}')
            raw = path.read_text()
            # Each line ends with exactly one newline
            assert raw == '{"a": 1}\n{"b": 2}\n'
        finally:
            writer.close()

    def test_close_and_reopen(self, tmp_path):
        """After close(), a subsequent write_line() reopens the file."""
        path = tmp_path / "test.jsonl"
        writer = JsonlWriter(path)
        try:
            writer.write_line('{"line": 1}')
            writer.close()
            writer.write_line('{"line": 2}')

            lines = path.read_text().splitlines()
            assert len(lines) == 2
            assert json.loads(lines[0])["line"] == 1
            assert json.loads(lines[1])["line"] == 2
        finally:
            writer.close()

    def test_close_idempotent(self, tmp_path):
        """Calling close() multiple times does not raise."""
        writer = JsonlWriter(tmp_path / "test.jsonl")
        writer.write_line('{"ok": true}')
        writer.close()
        writer.close()  # should not raise

    def test_creates_parent_directories(self, tmp_path):
        """The writer creates missing parent directories on first write."""
        path = tmp_path / "sub" / "dir" / "test.jsonl"
        writer = JsonlWriter(path)
        try:
            writer.write_line('{"nested": true}')
            assert path.exists()
            assert json.loads(path.read_text().strip())["nested"] is True
        finally:
            writer.close()


class TestJsonlWriterConcurrency:
    """Thread-safety guarantees."""

    def test_concurrent_writes(self, tmp_path):
        """4 threads x 25 writes each produce exactly 100 valid JSON lines."""
        path = tmp_path / "concurrent.jsonl"
        writer = JsonlWriter(path)
        barrier = threading.Barrier(4)

        def _write(thread_id):
            barrier.wait()
            for i in range(25):
                writer.write_line(json.dumps({"thread": thread_id, "seq": i}))

        threads = [threading.Thread(target=_write, args=(t,)) for t in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        writer.close()

        lines = path.read_text().splitlines()
        assert len(lines) == 100

        # Every line must be valid JSON
        for line in lines:
            record = json.loads(line)
            assert "thread" in record
            assert "seq" in record


# -- JsonlLogHandler tests ---------------------------------------------------


class TestJsonlLogHandler:
    """Integration with Python logging."""

    def test_handler_formats_and_writes(self, tmp_path):
        """A logger with JsonlLogHandler + StructuredJsonFormatter produces valid JSONL."""
        path = tmp_path / "handler.jsonl"
        writer = JsonlWriter(path)
        try:
            handler = JsonlLogHandler(writer)
            handler.setFormatter(StructuredJsonFormatter())
            handler.setLevel(logging.DEBUG)

            logger = logging.getLogger("test_jsonl_handler_unique")
            logger.handlers.clear()
            logger.addHandler(handler)
            logger.setLevel(logging.DEBUG)
            logger.propagate = False

            logger.info("hello from test")

            lines = path.read_text().splitlines()
            assert len(lines) == 1
            record = json.loads(lines[0])
            assert record["message"] == "hello from test"
            assert record["level"] == "INFO"
        finally:
            writer.close()

    def test_handler_error_does_not_raise(self, tmp_path):
        """If the writer raises, emit() calls handleError instead of propagating."""
        path = tmp_path / "handler_err.jsonl"
        writer = JsonlWriter(path)
        writer.close()
        # Force the writer into a broken state by making the path a directory
        path.unlink(missing_ok=True)
        path.mkdir()

        handler = JsonlLogHandler(writer)
        handler.setFormatter(logging.Formatter("%(message)s"))

        logger = logging.getLogger("test_jsonl_handler_err_unique")
        logger.handlers.clear()
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)
        logger.propagate = False

        # Should not raise even though the underlying write will fail
        logger.info("this will fail silently")
