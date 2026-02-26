# Task 1: ExportImportInfo Data Structure

**Status:** pending
**Depends on:** nothing

**Files:**
- Create: `ivy_lsp/analysis/test_scope.py`
- Test: `tests/test_export_import_extraction.py`

---

## Step 1: Write the failing test

```python
# tests/test_export_import_extraction.py
"""Tests for ExportImportInfo data structure."""
import pytest
from ivy_lsp.analysis.test_scope import ExportImportInfo


class TestExportImportInfoCreation:
    def test_create_empty(self):
        info = ExportImportInfo(file="/test/file.ivy")
        assert info.file == "/test/file.ivy"
        assert info.exports == []
        assert info.imports == []
        assert info.export_lines == {}
        assert info.import_lines == {}

    def test_create_with_exports(self):
        info = ExportImportInfo(
            file="/test/file.ivy",
            exports=["quic.send", "quic.recv"],
            export_lines={"quic.send": 10, "quic.recv": 15},
        )
        assert info.exports == ["quic.send", "quic.recv"]
        assert info.export_lines["quic.send"] == 10

    def test_create_with_imports(self):
        info = ExportImportInfo(
            file="/test/file.ivy",
            imports=["tls.handshake"],
            import_lines={"tls.handshake": 20},
        )
        assert info.imports == ["tls.handshake"]
        assert info.import_lines["tls.handshake"] == 20

    def test_has_exports_true(self):
        info = ExportImportInfo(
            file="/test/file.ivy",
            exports=["quic.send"],
        )
        assert info.has_exports is True

    def test_has_exports_false(self):
        info = ExportImportInfo(file="/test/file.ivy")
        assert info.has_exports is False
```

## Step 2: Run test to verify it fails

```bash
python -m pytest tests/test_export_import_extraction.py::TestExportImportInfoCreation -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'ivy_lsp.analysis.test_scope'`

## Step 3: Write minimal implementation

```python
# ivy_lsp/analysis/test_scope.py
"""Test scope model for per-test requirement scoping.

Provides data structures for export/import tracking, test scope
computation, and scoped requirement queries.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class ExportImportInfo:
    """Export/import declarations extracted from a single Ivy file."""

    file: str
    exports: List[str] = field(default_factory=list)
    imports: List[str] = field(default_factory=list)
    export_lines: Dict[str, int] = field(default_factory=dict)
    import_lines: Dict[str, int] = field(default_factory=dict)

    @property
    def has_exports(self) -> bool:
        return len(self.exports) > 0
```

## Step 4: Run test to verify it passes

```bash
python -m pytest tests/test_export_import_extraction.py::TestExportImportInfoCreation -v
```

Expected: PASS (5 tests)

## Step 5: Commit

```bash
git add ivy_lsp/analysis/test_scope.py tests/test_export_import_extraction.py
git commit -m "feat(test-scope): add ExportImportInfo data structure"
```
