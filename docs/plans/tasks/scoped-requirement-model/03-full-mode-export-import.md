# Task 3: Full-Mode (AST) Export/Import Extraction

**Status:** pending
**Depends on:** Task 1, Task 2

**Files:**
- Modify: `ivy_lsp/analysis/requirement_extractor.py` (add function)
- Test: `tests/test_export_import_extraction.py` (extend)

**Key helpers to reuse from existing code:**
- `_atom_to_name` (line 343-353) -- converts Ivy AST atoms to dotted name strings
- `_get_line` (line 261-268) -- extracts line number from AST node

---

## Step 1: Write the failing test

Append to `tests/test_export_import_extraction.py`:

```python
from ivy_lsp.analysis.requirement_extractor import extract_exports_imports_full


class TestFullModeExportExtraction:
    def test_returns_empty_for_none_ast(self):
        info = extract_exports_imports_full(None, FILEPATH, "")
        assert info.exports == []
        assert info.imports == []

    def test_returns_empty_for_no_decls(self):
        from unittest.mock import MagicMock
        ast_obj = MagicMock()
        ast_obj.decls = []
        info = extract_exports_imports_full(ast_obj, FILEPATH, "")
        assert info.exports == []
        assert info.imports == []

    def test_filepath_preserved(self):
        from unittest.mock import MagicMock
        ast_obj = MagicMock()
        ast_obj.decls = []
        info = extract_exports_imports_full(ast_obj, "/custom/path.ivy", "")
        assert info.file == "/custom/path.ivy"
```

## Step 2: Run test to verify it fails

```bash
python -m pytest tests/test_export_import_extraction.py::TestFullModeExportExtraction -v
```

Expected: FAIL with `ImportError: cannot import name 'extract_exports_imports_full'`

## Step 3: Write minimal implementation

Add to `ivy_lsp/analysis/requirement_extractor.py` (after `extract_requirements_full`):

```python
def extract_exports_imports_full(
    ast_obj: Any,
    filepath: str,
    source: str,
) -> "ExportImportInfo":
    """Extract export/import declarations from full AST.

    Walks ast_obj.decls looking for ExportDecl and ImportDecl nodes.
    Falls back to light mode extraction if ivy AST types unavailable.
    """
    from ivy_lsp.analysis.test_scope import ExportImportInfo

    if ast_obj is None or not hasattr(ast_obj, "decls"):
        return ExportImportInfo(file=filepath)

    try:
        import ivy.ivy_ast as ia
    except ImportError:
        from ivy_lsp.analysis.light_mode_extractor import extract_exports_imports_light
        return extract_exports_imports_light(source, filepath)

    exports: list = []
    imports: list = []
    export_lines: dict = {}
    import_lines: dict = {}

    for decl in ast_obj.decls:
        try:
            if isinstance(decl, ia.ExportDecl):
                for defn in decl.args:
                    exported = getattr(defn, "exported", None)
                    if callable(exported):
                        atom = exported()
                    else:
                        atom = exported
                    name = _atom_to_name(atom) if atom else None
                    if name:
                        line = _get_line(defn) if hasattr(defn, "lineno") else 0
                        exports.append(name)
                        export_lines[name] = line

            elif isinstance(decl, ia.ImportDecl):
                for defn in decl.args:
                    imported = getattr(defn, "imported", None)
                    if callable(imported):
                        atom = imported()
                    else:
                        atom = imported
                    name = _atom_to_name(atom) if atom else None
                    if name:
                        line = _get_line(defn) if hasattr(defn, "lineno") else 0
                        imports.append(name)
                        import_lines[name] = line
        except Exception:
            logger.warning(
                "Failed to extract export/import from %s in %s",
                type(decl).__name__, filepath, exc_info=True,
            )

    return ExportImportInfo(
        file=filepath,
        exports=exports,
        imports=imports,
        export_lines=export_lines,
        import_lines=import_lines,
    )
```

## Step 4: Run test to verify it passes

```bash
python -m pytest tests/test_export_import_extraction.py::TestFullModeExportExtraction -v
```

Expected: PASS (3 tests; ivy-dependent tests may skip gracefully via fallback)

## Step 5: Commit

```bash
git add ivy_lsp/analysis/requirement_extractor.py tests/test_export_import_extraction.py
git commit -m "feat(full-mode): add AST-based export/import extraction"
```
