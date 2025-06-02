"""Storage backends for metrics data."""

import json
from datetime import datetime
from pathlib import Path
from typing import Any


class JSONLinesStorage:
    """Storage backend using JSON Lines format."""

    def __init__(self, base_path: Path):
        """Initialize the storage backend.

        Args:
            base_path: Base directory for storing metrics files
        """
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

    def write_record(self, record: dict[str, Any]) -> None:
        """Write a metrics record to storage.

        Args:
            record: The metrics record to store
        """
        # Create filename based on current date
        now = datetime.now()
        filename = f"{now.strftime('%Y-%m-%d')}.jsonl"
        filepath = self.base_path / filename

        # Append the record as a JSON line
        with open(filepath, "a", encoding="utf-8") as f:
            json.dump(record, f, separators=(",", ":"))
            f.write("\n")

    def read_records(
        self, date: str | None = None, limit: int | None = None
    ) -> list[dict[str, Any]]:
        """Read metrics records from storage.

        Args:
            date: Optional date filter (YYYY-MM-DD format)
            limit: Optional limit on number of records to return

        Returns:
            List of metrics records
        """
        records = []

        if date:
            # Read from specific date file
            filepath = self.base_path / f"{date}.jsonl"
            if filepath.exists():
                records.extend(self._read_file(filepath))
        else:
            # Read from all files, newest first
            files = sorted(self.base_path.glob("*.jsonl"), reverse=True)
            for filepath in files:
                records.extend(self._read_file(filepath))
                if limit and len(records) >= limit:
                    break

        # Sort by timestamp, newest first
        records.sort(key=lambda x: x.get("timestamp", ""), reverse=True)

        if limit:
            records = records[:limit]

        return records

    def _read_file(self, filepath: Path) -> list[dict[str, Any]]:
        """Read records from a single JSONL file."""
        records = []
        try:
            with open(filepath, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            record = json.loads(line)
                            records.append(record)
                        except json.JSONDecodeError:
                            # Skip malformed lines
                            continue
        except FileNotFoundError:
            pass
        return records

    def get_record_by_id(self, run_id: str) -> dict[str, Any] | None:
        """Get a specific record by run ID.

        Args:
            run_id: The run ID to search for

        Returns:
            The matching record or None
        """
        # Search through all files
        files = sorted(self.base_path.glob("*.jsonl"), reverse=True)
        for filepath in files:
            records = self._read_file(filepath)
            for record in records:
                if record.get("run_id") == run_id:
                    return record
        return None

    def list_files(self) -> list[Path]:
        """List all metrics files."""
        return sorted(self.base_path.glob("*.jsonl"), reverse=True)
