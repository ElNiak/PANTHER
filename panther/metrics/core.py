"""Core metrics collection and management."""

import hashlib
import json
import subprocess
import uuid
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any

from .storage import JSONLinesStorage


class MetricsCollector:
    """Collects and manages metrics for PANTHER experiments and test sessions."""

    def __init__(self, storage_path: Path | None = None):
        """Initialize the metrics collector.

        Args:
            storage_path: Path to store metrics files. Defaults to .panther-metrics/
        """
        self._metrics: dict[str, float] = {}
        self._tags: dict[str, dict[str, str]] = {}
        self._lock = Lock()

        if storage_path is None:
            # Default to .panther-metrics in the project root
            project_root = Path(__file__).parent.parent.parent
            storage_path = project_root / ".panther-metrics"

        self.storage = JSONLinesStorage(storage_path)
        self.run_id = str(uuid.uuid4())

    def record(self, name: str, value: float, tags: dict[str, str] | None = None) -> None:
        """Record a metric value.

        Args:
            name: Metric name (e.g., "container.build_seconds")
            value: Metric value
            tags: Optional tags for the metric
        """
        with self._lock:
            self._metrics[name] = value
            if tags:
                self._tags[name] = tags.copy()

    def flush(self, kind: str, extra: dict[str, Any] | None = None) -> str:
        """Flush collected metrics to storage.

        Args:
            kind: Type of metrics ("builder", "tests", etc.)
            extra: Additional metadata

        Returns:
            The run ID for this flush
        """
        with self._lock:
            # Get git commit if available
            git_commit = self._get_git_commit()

            # Create the metrics record
            record = {
                "run_id": self.run_id,
                "type": kind,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "git_commit": git_commit,
                "metrics": self._metrics.copy(),
                "tags": self._tags.copy(),
            }

            # Add extra metadata
            if extra:
                record.update(extra)

            # Store the record
            self.storage.write_record(record)

            # Clear metrics for next collection
            self._metrics.clear()
            self._tags.clear()

            return self.run_id

    def _get_git_commit(self) -> str | None:
        """Get the current git commit hash."""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"], capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass
        return None

    def get_config_hash(self, config_data: str | dict[str, Any]) -> str:
        """Generate a hash for configuration data.

        Args:
            config_data: Configuration data as string or dict

        Returns:
            SHA256 hash of the configuration
        """
        if isinstance(config_data, dict):
            config_data = json.dumps(config_data, sort_keys=True)

        return hashlib.sha256(config_data.encode()).hexdigest()[:16]


# Global collector instance
_global_collector: MetricsCollector | None = None
_collector_lock = Lock()


def get_current_collector() -> MetricsCollector:
    """Get or create the current global metrics collector."""
    global _global_collector
    with _collector_lock:
        if _global_collector is None:
            _global_collector = MetricsCollector()
        return _global_collector


def record(name: str, value: float, tags: dict[str, str] | None = None) -> None:
    """Record a metric using the global collector.

    Args:
        name: Metric name (e.g., "container.build_seconds")
        value: Metric value
        tags: Optional tags for the metric
    """
    collector = get_current_collector()
    collector.record(name, value, tags)


def flush(kind: str, extra: dict[str, Any] | None = None) -> str:
    """Flush metrics using the global collector.

    Args:
        kind: Type of metrics ("builder", "tests", etc.)
        extra: Additional metadata

    Returns:
        The run ID for this flush
    """
    collector = get_current_collector()
    return collector.flush(kind, extra)
