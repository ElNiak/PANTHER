"""Centralized JSONL writer for the structured log file.

Provides a single thread-safe writer that serializes all JSONL output
(log records, event records, metric records) through one lock and one
persistent file handle.  This eliminates the previous design where three
independent locks could interleave writes and corrupt the file.

Classes:
    JsonlWriter: Thread-safe, single-handle JSONL file writer.
    JsonlLogHandler: ``logging.Handler`` adapter that delegates to a
        ``JsonlWriter`` instance.
"""

import logging
import threading
from pathlib import Path
from typing import Optional, TextIO


class JsonlWriter:
    """Thread-safe JSONL file writer with a single persistent handle.

    All writes are serialized through a single ``threading.Lock`` and
    flushed immediately so that concurrent producers (logging handlers,
    event recorders, metrics collectors) never interleave output.

    Args:
        path: Filesystem path to the JSONL file (opened in append mode).

    Example::

        writer = JsonlWriter(Path("/tmp/structured.jsonl"))
        writer.write_line('{"level": "INFO", "message": "hello"}')
        writer.close()
    """

    def __init__(self, path: Path) -> None:
        """Initialize the JSONL writer.

        Args:
            path: Filesystem path to the JSONL file (created on first write).
        """
        self._path = Path(path)
        self._lock = threading.Lock()
        self._fh: Optional[TextIO] = None

    # -- public API -----------------------------------------------------------

    def write_line(self, line: str) -> None:
        """Write a single line to the JSONL file.

        Acquires the lock, lazily opens the file if needed, writes the
        line followed by a newline, and flushes.

        Args:
            line: A string (typically a JSON-serialized record) to write.
                A trailing newline is always appended regardless of
                whether *line* already ends with one.
        """
        with self._lock:
            fh = self._ensure_open()
            fh.write(line + "\n")
            fh.flush()

    def close(self) -> None:
        """Close the underlying file handle, if open."""
        with self._lock:
            if self._fh is not None and not self._fh.closed:
                self._fh.close()
            self._fh = None

    @property
    def path(self) -> Path:
        """Return the path this writer is bound to."""
        return self._path

    # -- internals ------------------------------------------------------------

    def _ensure_open(self) -> TextIO:
        """Return the open file handle, lazily opening if necessary.

        Must be called while holding ``self._lock``.
        """
        if self._fh is None or self._fh.closed:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            self._fh = open(self._path, "a", encoding="utf-8")  # noqa: SIM115
        return self._fh


class JsonlLogHandler(logging.Handler):
    """Logging handler that writes formatted records via a :class:`JsonlWriter`.

    This replaces the per-logger ``logging.FileHandler`` instances that
    previously each held their own file descriptor and lock.

    Args:
        writer: The shared :class:`JsonlWriter` instance.
        level: Optional logging level (default ``logging.NOTSET``).
    """

    def __init__(self, writer: JsonlWriter, level: int = logging.NOTSET) -> None:
        """Initialize the handler.

        Args:
            writer: The shared :class:`JsonlWriter` to delegate writes to.
            level: Minimum logging level (default ``NOTSET`` -- captures all).
        """
        super().__init__(level)
        self._writer = writer

    def emit(self, record: logging.LogRecord) -> None:
        """Format *record* and write it as a single JSONL line.

        Exceptions during formatting or writing are routed to
        :meth:`logging.Handler.handleError`.
        """
        try:
            msg = self.format(record)
            self._writer.write_line(msg)
        except Exception:  # pylint: disable=broad-exception-caught
            self.handleError(record)
