"""Output index builder for tracking experiment artifacts.

Provides an incremental, thread-safe manifest of every output file produced
during an experiment run.  The manifest is persisted as ``output_index.json``
at the experiment root and follows a versioned JSON schema so downstream tools
can parse it reliably.
"""

import json
import logging
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

# Schema version for the output_index.json format.  Bump when the schema
# changes in a backwards-incompatible way.
_SCHEMA_VERSION = "1.0"

# Mapping from file extension to (type, format) defaults.
_EXTENSION_MAP: Dict[str, tuple] = {
    ".pcap": ("artifact", "pcap"),
    ".qlog": ("artifact", "qlog"),
    ".har": ("artifact", "json"),
    ".yaml": ("config", "yaml"),
    ".yml": ("config", "yaml"),
    ".json": ("report", "json"),
    ".jsonl": ("log", "jsonl"),
    ".csv": ("metric", "csv"),
    ".md": ("report", "markdown"),
    ".log": ("log", "text"),
    ".txt": ("log", "text"),
    ".out": ("log", "text"),
}


class FileEntry:
    """A single tracked output file.

    Attributes:
        path: Path relative to the experiment directory.
        type: Semantic category (``log``, ``artifact``, ``report``, ``metric``,
              ``config``).
        format: Data format (``text``, ``jsonl``, ``json``, ``pcap``, ``qlog``,
                ``csv``, ``markdown``, ``yaml``).
        test_id: Optional test identifier the file belongs to.
        service_id: Optional service identifier the file belongs to.
        phase: Optional execution phase (e.g. ``compile``, ``runtime``).
        size_bytes: File size at registration time, or 0 if unknown.
        description: Human-readable description of the file.
    """

    __slots__ = (
        "path",
        "type",
        "format",
        "test_id",
        "service_id",
        "phase",
        "size_bytes",
        "description",
    )

    def __init__(
        self,
        path: str,
        file_type: str = "log",
        file_format: str = "text",
        test_id: Optional[str] = None,
        service_id: Optional[str] = None,
        phase: Optional[str] = None,
        size_bytes: int = 0,
        description: str = "",
    ):
        """Initialize a FileEntry.

        Args:
            path: Relative path to the file from the experiment directory.
            file_type: Semantic category of the file.
            file_format: Data format of the file.
            test_id: Optional test identifier.
            service_id: Optional service identifier.
            phase: Optional execution phase.
            size_bytes: File size in bytes.
            description: Human-readable description.
        """
        self.path = path
        self.type = file_type
        self.format = file_format
        self.test_id = test_id
        self.service_id = service_id
        self.phase = phase
        self.size_bytes = size_bytes
        self.description = description

    def to_dict(self) -> Dict:
        """Serialize to a JSON-safe dictionary.

        Returns:
            Dictionary with all fields. Optional fields that are ``None``
            are omitted to keep the manifest compact.
        """
        d: Dict = {
            "path": self.path,
            "type": self.type,
            "format": self.format,
            "size_bytes": self.size_bytes,
        }
        if self.test_id is not None:
            d["test_id"] = self.test_id
        if self.service_id is not None:
            d["service_id"] = self.service_id
        if self.phase is not None:
            d["phase"] = self.phase
        if self.description:
            d["description"] = self.description
        return d


class OutputIndexBuilder:
    """Incrementally tracks output files produced during an experiment.

    Thread-safe: multiple threads may call :meth:`register` concurrently
    (e.g. when environments run in parallel).  :meth:`flush` serializes the
    accumulated entries to ``output_index.json`` in the experiment directory.

    Args:
        experiment_dir: Root directory of the current experiment run.
        experiment_id: Unique identifier for the experiment.

    Example::

        builder = OutputIndexBuilder(experiment_dir, "quic_test_2026")
        builder.register("structured.jsonl", file_type="log", file_format="jsonl")
        builder.register("artifacts/capture.pcap")  # auto-detects type/format
        builder.flush()
    """

    INDEX_FILENAME = "output_index.json"

    def __init__(self, experiment_dir: Path, experiment_id: str) -> None:
        """Initialize the OutputIndexBuilder.

        Args:
            experiment_dir: Root directory of the current experiment run.
            experiment_id: Unique identifier for the experiment.
        """
        self._experiment_dir = Path(experiment_dir)
        self._experiment_id = experiment_id
        self._entries: List[FileEntry] = []
        self._seen_paths: set = set()
        self._lock = threading.Lock()
        self._created_at = datetime.now(timezone.utc).isoformat()

    # -- Public API ---------------------------------------------------------

    def register(
        self,
        path: str,
        *,
        file_type: Optional[str] = None,
        file_format: Optional[str] = None,
        test_id: Optional[str] = None,
        service_id: Optional[str] = None,
        phase: Optional[str] = None,
        size_bytes: Optional[int] = None,
        description: str = "",
    ) -> None:
        """Register an output file in the index.

        If *file_type* or *file_format* are not provided they are inferred
        from the file extension via :func:`detect_type_and_format`.  If
        *size_bytes* is ``None`` the builder attempts to stat the file on
        disk.

        Duplicate paths (same relative path string) are silently ignored so
        callers do not need to track whether a file was already registered.

        Args:
            path: Path to the file, either absolute or relative to the
                experiment directory.
            file_type: Semantic type override (``log``, ``artifact``,
                ``report``, ``metric``, ``config``).
            file_format: Format override (``text``, ``jsonl``, ``json``,
                ``pcap``, ``qlog``, ``csv``, ``markdown``, ``yaml``).
            test_id: Optional test identifier.
            service_id: Optional service identifier.
            phase: Optional execution phase.
            size_bytes: File size in bytes.  ``None`` triggers a stat call.
            description: Human-readable description.
        """
        rel_path = self._to_relative(path)

        with self._lock:
            if rel_path in self._seen_paths:
                return
            self._seen_paths.add(rel_path)

        # Auto-detect type/format from extension when not provided.
        detected_type, detected_format = detect_type_and_format(rel_path)
        if file_type is None:
            file_type = detected_type
        if file_format is None:
            file_format = detected_format

        # Resolve size on disk if not given explicitly.
        if size_bytes is None:
            size_bytes = self._stat_size(rel_path)

        entry = FileEntry(
            path=rel_path,
            file_type=file_type,
            file_format=file_format,
            test_id=test_id,
            service_id=service_id,
            phase=phase,
            size_bytes=size_bytes,
            description=description,
        )

        with self._lock:
            self._entries.append(entry)

        logger.debug("Indexed output: %s (%s/%s)", rel_path, file_type, file_format)

    def flush(self) -> Path:
        """Write the accumulated index to ``output_index.json``.

        Uses atomic write (temp file + rename) to prevent corruption
        if the process is interrupted mid-write.

        Returns:
            Absolute path to the written index file.
        """
        output_path = self._experiment_dir / self.INDEX_FILENAME
        tmp_path = output_path.with_suffix(".tmp")

        with self._lock:
            entries_snapshot = list(self._entries)

        manifest = {
            "schema_version": _SCHEMA_VERSION,
            "experiment_id": self._experiment_id,
            "created_at": self._created_at,
            "files": [e.to_dict() for e in entries_snapshot],
        }

        try:
            self._experiment_dir.mkdir(parents=True, exist_ok=True)
            with open(tmp_path, "w", encoding="utf-8") as fh:
                json.dump(manifest, fh, indent=2, sort_keys=False)
            tmp_path.replace(output_path)
        except OSError as exc:
            logger.error("Failed to write output index: %s", exc)
            tmp_path.unlink(missing_ok=True)
            raise

        logger.info(
            "Wrote output index with %d entries to %s",
            len(entries_snapshot),
            output_path,
        )
        return output_path

    @property
    def entry_count(self) -> int:
        """Return the number of registered entries."""
        with self._lock:
            return len(self._entries)

    # -- Internal helpers ---------------------------------------------------

    def _to_relative(self, path: str) -> str:
        """Convert *path* to a string relative to the experiment directory.

        If *path* is already relative it is returned as-is.  Absolute paths
        that fall outside the experiment directory are kept absolute (with a
        warning) so they are still captured in the manifest.

        Args:
            path: Absolute or relative file path.

        Returns:
            Relative path string using forward-slash separators.
        """
        p = Path(path)
        if p.is_absolute():
            try:
                rel = p.relative_to(self._experiment_dir)
                return str(rel)
            except ValueError:
                logger.warning(
                    "Path %s is outside experiment directory %s; storing absolute",
                    path,
                    self._experiment_dir,
                )
                return str(p)
        return str(p)

    def _stat_size(self, rel_path: str) -> int:
        """Return the file size on disk, or 0 if the file is missing.

        Args:
            rel_path: Path relative to the experiment directory.

        Returns:
            File size in bytes, or 0 on failure.
        """
        abs_path = self._experiment_dir / rel_path
        try:
            return abs_path.stat().st_size
        except OSError:
            return 0


def detect_type_and_format(path: str) -> tuple:
    """Infer artifact type and format from a file path.

    Uses the file extension to look up defaults in :data:`_EXTENSION_MAP`.
    Falls back to ``("log", "text")`` for unrecognized extensions.

    Args:
        path: File path (absolute or relative).

    Returns:
        A ``(type, format)`` tuple, e.g. ``("artifact", "pcap")``.
    """
    ext = Path(path).suffix.lower()
    return _EXTENSION_MAP.get(ext, ("log", "text"))
