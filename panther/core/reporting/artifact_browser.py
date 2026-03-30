"""Artifact browser for experiment output directories.

Reads the ``output_index.json`` manifest produced by OutputIndexBuilder
to list and filter experiment artifacts. Falls back to directory walking
when no index file exists.

Typical usage::

    from panther.core.reporting.artifact_browser import ArtifactBrowser

    browser = ArtifactBrowser(Path("outputs/2024-01-01/exp1"))
    for artifact in browser.list_artifacts(service_id="picoquic"):
        print(artifact["path"], artifact["type"])
"""

import json
import logging
import os
from pathlib import Path
from typing import Dict, List, Optional

from panther.core.outputs.output_index import (
    _EXTENSION_MAP,
    OutputIndexBuilder,
    detect_type_and_format,
)

logger = logging.getLogger(__name__)


class ArtifactBrowser:
    """Browse and filter experiment artifacts from an output directory.

    Loads the ``output_index.json`` manifest if present, otherwise falls
    back to walking the directory tree and inferring file metadata from
    extensions.

    Args:
        experiment_dir: Root directory of the experiment output.
    """

    def __init__(self, experiment_dir: Path) -> None:
        """Initialize the artifact browser.

        Args:
            experiment_dir: Root directory of the experiment output.
        """
        self._experiment_dir = Path(experiment_dir)
        self._index: Optional[List[Dict]] = None

    def list_artifacts(
        self,
        *,
        test_id: Optional[str] = None,
        service_id: Optional[str] = None,
        artifact_type: Optional[str] = None,
        phase: Optional[str] = None,
    ) -> List[Dict]:
        """List artifacts matching the given filters.

        Each returned dict contains: ``path``, ``type``, ``format``,
        ``test_id``, ``service_id``, ``phase``, ``size_bytes``,
        ``description``.

        Args:
            test_id: Filter by test identifier.
            service_id: Filter by service identifier.
            artifact_type: Filter by artifact type (e.g. ``artifact``,
                ``log``, ``report``, ``metric``, ``config``).
            phase: Filter by execution phase.

        Returns:
            List of artifact metadata dicts matching all provided filters.
        """
        entries = self._load_entries()
        return self._apply_filters(
            entries,
            test_id=test_id,
            service_id=service_id,
            artifact_type=artifact_type,
            phase=phase,
        )

    # -- Loading -------------------------------------------------------------

    def _load_entries(self) -> List[Dict]:
        """Load artifact entries, preferring the index file.

        Returns:
            List of artifact metadata dicts.
        """
        if self._index is not None:
            return self._index

        index_path = self._experiment_dir / OutputIndexBuilder.INDEX_FILENAME
        if index_path.is_file():
            self._index = self._load_from_index(index_path)
        else:
            logger.debug(
                "No %s found in %s; falling back to directory walk",
                OutputIndexBuilder.INDEX_FILENAME,
                self._experiment_dir,
            )
            self._index = self._load_from_directory()

        return self._index

    def _load_from_index(self, index_path: Path) -> List[Dict]:
        """Parse the output_index.json manifest.

        Args:
            index_path: Path to the ``output_index.json`` file.

        Returns:
            List of artifact dicts from the manifest.
        """
        try:
            with open(index_path, encoding="utf-8") as fh:
                data = json.load(fh)
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Failed to read index %s: %s", index_path, exc)
            return self._load_from_directory()

        raw_files = data.get("files", [])
        entries: List[Dict] = []
        for raw in raw_files:
            entries.append(self._normalize_entry(raw))
        return entries

    def _load_from_directory(self) -> List[Dict]:
        """Walk the experiment directory to discover artifacts.

        Returns:
            List of artifact dicts inferred from file metadata.
        """
        if not self._experiment_dir.is_dir():
            return []

        entries: List[Dict] = []
        for root, _dirs, files in os.walk(self._experiment_dir):
            for filename in sorted(files):
                abs_path = Path(root) / filename
                try:
                    rel_path = str(abs_path.relative_to(self._experiment_dir))
                except ValueError:
                    rel_path = str(abs_path)

                file_type, file_format = detect_type_and_format(filename)
                try:
                    size = abs_path.stat().st_size
                except OSError:
                    size = 0

                entries.append(
                    {
                        "path": rel_path,
                        "type": file_type,
                        "format": file_format,
                        "test_id": None,
                        "service_id": None,
                        "phase": None,
                        "size_bytes": size,
                        "description": "",
                    }
                )
        return entries

    # -- Filtering -----------------------------------------------------------

    @staticmethod
    def _apply_filters(
        entries: List[Dict],
        *,
        test_id: Optional[str] = None,
        service_id: Optional[str] = None,
        artifact_type: Optional[str] = None,
        phase: Optional[str] = None,
    ) -> List[Dict]:
        """Filter entries by the provided criteria (AND semantics).

        Args:
            entries: Full list of artifact dicts.
            test_id: Filter by test identifier.
            service_id: Filter by service identifier.
            artifact_type: Filter by artifact type.
            phase: Filter by execution phase.

        Returns:
            Filtered list of artifact dicts.
        """
        result = entries
        if test_id is not None:
            result = [e for e in result if e.get("test_id") == test_id]
        if service_id is not None:
            result = [e for e in result if e.get("service_id") == service_id]
        if artifact_type is not None:
            result = [e for e in result if e.get("type") == artifact_type]
        if phase is not None:
            result = [e for e in result if e.get("phase") == phase]
        return result

    # -- Normalization -------------------------------------------------------

    @staticmethod
    def _normalize_entry(raw: Dict) -> Dict:
        """Normalize a raw index entry to a consistent schema.

        Ensures all expected keys are present with sensible defaults.

        Args:
            raw: Raw dict from the output_index.json manifest.

        Returns:
            Dict with all standard fields populated.
        """
        return {
            "path": raw.get("path", ""),
            "type": raw.get("type", "log"),
            "format": raw.get("format", "text"),
            "test_id": raw.get("test_id"),
            "service_id": raw.get("service_id"),
            "phase": raw.get("phase"),
            "size_bytes": raw.get("size_bytes", 0),
            "description": raw.get("description", ""),
        }
