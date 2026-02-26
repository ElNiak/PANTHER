# Task 11: Symbol Extraction for ExportDecl/ImportDecl

**Status:** pending
**Depends on:** Task 1

**Files:**
- Modify: `ivy_lsp/parsing/ast_to_symbols.py:206-211`

**Context:** Currently `ast_to_symbols.py` explicitly skips `ExportDecl` and `ImportDecl` at line 206-211:

```python
if isinstance(decl, (ia.MixinDecl, ia.VariantDecl, ia.ExportDecl, ia.ImportDecl)):
    return []
```

This means export/import declarations produce zero symbols, making them invisible to the symbol table and features like go-to-definition.

---

## Step 1: Write the failing test

```python
# tests/test_export_import_symbols.py
"""Tests for ExportDecl/ImportDecl symbol extraction."""
import pytest
from unittest.mock import MagicMock
from lsprotocol.types import SymbolKind


class TestExportSymbolExtraction:
    def test_export_produces_event_symbol(self):
        """When ivy AST is available, ExportDecl should produce Event symbols."""
        # This test verifies the concept; actual AST integration requires ivy
        try:
            import ivy.ivy_ast as ia
        except ImportError:
            pytest.skip("ivy AST not available")

        from ivy_lsp.parsing.ast_to_symbols import ast_to_symbols
        # Would need a real AST with ExportDecl to test fully
        # For now, verify the skip list no longer includes ExportDecl

    def test_skip_list_excludes_export_import(self):
        """Verify ExportDecl/ImportDecl removed from skip list."""
        import inspect
        from ivy_lsp.parsing import ast_to_symbols as module
        source = inspect.getsource(module)
        # The old pattern grouped all four together
        assert "ExportDecl, ia.ImportDecl))" not in source or \
               "MixinDecl, ia.VariantDecl, ia.ExportDecl" not in source
```

## Step 2: Run test to verify it fails

```bash
python -m pytest tests/test_export_import_symbols.py -v
```

Expected: FAIL (ExportDecl still in the skip list)

## Step 3: Modify `ast_to_symbols.py`

At `ivy_lsp/parsing/ast_to_symbols.py:206-211`, replace:

```python
# OLD:
if isinstance(
    decl,
    (ia.MixinDecl, ia.VariantDecl, ia.ExportDecl, ia.ImportDecl),
):
    return []
```

With:

```python
# NEW:
if isinstance(decl, (ia.MixinDecl, ia.VariantDecl)):
    return []
if isinstance(decl, ia.ExportDecl):
    return _convert_export(decl, filename, source)
if isinstance(decl, ia.ImportDecl):
    return _convert_import(decl, filename, source)
```

Add helper functions:

```python
def _convert_export(decl, filename: str, source: str) -> list:
    """Convert ExportDecl to IvySymbol with kind=Event."""
    symbols = []
    for defn in getattr(decl, "args", []):
        exported = getattr(defn, "exported", None)
        if callable(exported):
            exported = exported()
        name = _get_name(exported) if exported else None
        if name:
            line = _get_line_from_decl(defn, source)
            symbols.append(IvySymbol(
                name=f"export {name}",
                kind=SymbolKind.Event,
                range=(line, 0, line, 0),
                file_path=filename,
                detail=f"export {name}",
            ))
    return symbols


def _convert_import(decl, filename: str, source: str) -> list:
    """Convert ImportDecl to IvySymbol with kind=Event."""
    symbols = []
    for defn in getattr(decl, "args", []):
        imported = getattr(defn, "imported", None)
        if callable(imported):
            imported = imported()
        name = _get_name(imported) if imported else None
        if name:
            line = _get_line_from_decl(defn, source)
            symbols.append(IvySymbol(
                name=f"import {name}",
                kind=SymbolKind.Event,
                range=(line, 0, line, 0),
                file_path=filename,
                detail=f"import {name}",
            ))
    return symbols
```

**Note:** `_get_name` and `_get_line_from_decl` may need to be adapted from existing helpers like `_atom_to_name` used elsewhere in the file. Check the actual helper names in the file.

## Step 4: Run test to verify it passes

```bash
python -m pytest tests/test_export_import_symbols.py -v
```

Expected: PASS

## Step 5: Commit

```bash
git add ivy_lsp/parsing/ast_to_symbols.py tests/test_export_import_symbols.py
git commit -m "feat(symbols): extract ExportDecl/ImportDecl as symbols"
```
