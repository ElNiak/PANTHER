# Task 11: Symbol Extraction for ExportDecl/ImportDecl

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make `export` and `import` declarations visible in the document outline and workspace symbols by producing `IvySymbol` entries from `ExportDecl`/`ImportDecl` AST nodes.

**Architecture:** Remove `ExportDecl`/`ImportDecl` from the skip list in `_convert_decl`, add two converter functions (`_convert_export`, `_convert_import`) and one shared helper (`_atom_name`). Reuse the existing `_loc_to_tuple` for line range conversion since `decl.lineno` has the `.line` attribute it expects.

**Tech Stack:** Python 3.10+, pytest, lsprotocol, unittest.mock. No new dependencies.

**Status:** pending
**Depends on:** Task 1 (ExportImportInfo establishes AST patterns for ExportDecl/ImportDecl)

**Files:**
- Modify: `ivy_lsp/parsing/ast_to_symbols.py:206-213`
- Create: `tests/test_export_import_symbols.py`

**Base path for all files:** `panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp/`

**Test runner:** `cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp && python -m pytest tests/<file> -v`

---

## Design Decisions

### SymbolKind choice: Event

Export/import declarations describe interface boundaries -- which actions the tester generates (exports) and which it expects from the environment (imports). `SymbolKind.Event` (24) is the closest semantic match. This is consistent with the original plan.

### Name prefix: `"export <name>"` / `"import <name>"`

Prefixing with the keyword makes these symbols visually distinct from the underlying action definitions in the document outline. An `ActionDecl` named `quic.send` and an `ExportDecl` referencing it produce separate symbols: `quic.send` (Function) and `export quic.send` (Event).

### Why ExportDecl/ImportDecl need special handling

Unlike all other converters in `_convert_decl`, `ExportDecl`/`ImportDecl` do **not** implement `defines()`. They don't define new symbols -- they declare interface relationships. Their structure is:

```
ExportDecl
  .args = [ExportDef, ...]      # list of export definitions
  .lineno.line = 5              # 1-based line number

ExportDef
  .args = [Atom]                # single-element list

Atom
  .relname = "quic.send"        # preferred name field
  .rep = "quic.send"            # fallback name field
```

We iterate `decl.args` (list of ExportDef/ImportDef), extract the atom name from each, and produce one `IvySymbol` per exported/imported action.

### Line range conversion

`_loc_to_tuple(loc, source)` already handles any object with a `.line` attribute (1-based). Since `decl.lineno` has exactly that, we pass `decl.lineno` directly -- no new helper needed.

### Test strategy: mocked AST via sys.modules patching

The ivy parser (`ivy.ivy_ast`) is not available in the test environment. We follow the same mock pattern used by `test_export_import_extraction.py`:
- Create fake `_FakeExportDecl`, `_FakeImportDecl` classes
- Create a comprehensive fake `ia` module with sentinel classes for all other decl types (so `isinstance` checks fall through to our export/import handlers)
- Patch `sys.modules["ivy"]` and `sys.modules["ivy.ivy_ast"]`
- Call `ast_to_symbols()` through the public API

---

## Step 1: Write the failing tests

Create `tests/test_export_import_symbols.py`:

```python
# tests/test_export_import_symbols.py
"""Tests for ExportDecl/ImportDecl symbol extraction in ast_to_symbols."""

import sys
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from lsprotocol.types import SymbolKind

from ivy_lsp.parsing.symbols import IvySymbol


# ---------------------------------------------------------------------------
# Fake AST types for mocking ivy.ivy_ast
# ---------------------------------------------------------------------------


class _FakeExportDecl:
    """Stand-in for ivy.ivy_ast.ExportDecl."""

    pass


class _FakeExportDef:
    """Stand-in for ExportDef (child of ExportDecl.args)."""

    pass


class _FakeImportDecl:
    """Stand-in for ivy.ivy_ast.ImportDecl."""

    pass


class _FakeImportDef:
    """Stand-in for ImportDef (child of ImportDecl.args)."""

    pass


class _Sentinel:
    """Type that no fake decl is an instance of.

    Used for all non-export/import decl types so isinstance checks
    in _convert_decl fall through to the export/import handlers.
    """

    pass


def _make_lineno(line_1based: int) -> SimpleNamespace:
    """Create a fake lineno with 1-based .line attribute."""
    return SimpleNamespace(line=line_1based)


def _make_fake_ia_module() -> SimpleNamespace:
    """Fake ivy.ivy_ast with all decl types.

    ExportDecl/ImportDecl map to our fakes; all others map to _Sentinel
    so isinstance checks return False for our fake decls.
    """
    return SimpleNamespace(
        ObjectDecl=_Sentinel,
        ActionDecl=_Sentinel,
        TypeDecl=_Sentinel,
        DefinitionDecl=_Sentinel,
        PropertyDecl=_Sentinel,
        AxiomDecl=_Sentinel,
        ConjectureDecl=_Sentinel,
        IsolateDecl=_Sentinel,
        ModuleDecl=_Sentinel,
        AliasDecl=_Sentinel,
        DestructorDecl=_Sentinel,
        ConstructorDecl=_Sentinel,
        ConstantDecl=_Sentinel,
        InstantiateDecl=_Sentinel,
        MixinDecl=_Sentinel,
        VariantDecl=_Sentinel,
        ExportDecl=_FakeExportDecl,
        ImportDecl=_FakeImportDecl,
    )


def _patch_ivy_ast():
    """Context manager patching sys.modules for import ivy.ivy_ast."""
    ia_module = _make_fake_ia_module()
    ivy_mock = SimpleNamespace(ivy_ast=ia_module)
    return patch.dict(
        "sys.modules", {"ivy": ivy_mock, "ivy.ivy_ast": ia_module}
    )


def _make_export_decl(names_and_lines):
    """Build _FakeExportDecl with ExportDef children.

    Args:
        names_and_lines: list of (name, 1_based_line) tuples.
    """
    decl = _FakeExportDecl()
    defs = []
    last_line = 1
    for name, line_1based in names_and_lines:
        defn = _FakeExportDef()
        defn.args = [SimpleNamespace(relname=name)]
        defs.append(defn)
        last_line = line_1based
    decl.args = defs
    decl.lineno = _make_lineno(last_line)
    return decl


def _make_import_decl(names_and_lines):
    """Build _FakeImportDecl with ImportDef children."""
    decl = _FakeImportDecl()
    defs = []
    last_line = 1
    for name, line_1based in names_and_lines:
        defn = _FakeImportDef()
        defn.args = [SimpleNamespace(relname=name)]
        defs.append(defn)
        last_line = line_1based
    decl.args = defs
    decl.lineno = _make_lineno(last_line)
    return decl


def _make_ast(*decls):
    """Build a fake AST object with .decls list."""
    return SimpleNamespace(decls=list(decls))


def _find_symbol(symbols, name, kind=None):
    """Find a symbol by name (and optionally kind) in a flat or nested list."""
    for sym in symbols:
        if sym.name == name and (kind is None or sym.kind == kind):
            return sym
        found = _find_symbol(sym.children, name, kind)
        if found is not None:
            return found
    return None


# ---------------------------------------------------------------------------
# Export symbol tests
# ---------------------------------------------------------------------------


class TestExportSymbolExtraction:
    """ExportDecl should produce Event symbols prefixed with 'export'."""

    def test_single_export(self):
        decl = _make_export_decl([("quic.send", 5)])
        ast = _make_ast(decl)
        source = "\n".join([""] * 4 + ["export quic.send"])

        with _patch_ivy_ast():
            from ivy_lsp.parsing.ast_to_symbols import ast_to_symbols
            symbols = ast_to_symbols(ast, "test.ivy", source)

        sym = _find_symbol(symbols, "export quic.send")
        assert sym is not None, f"Expected 'export quic.send', got {[s.name for s in symbols]}"
        assert sym.kind == SymbolKind.Event
        assert sym.file_path == "test.ivy"

    def test_export_range_is_zero_based(self):
        decl = _make_export_decl([("quic.send", 5)])
        ast = _make_ast(decl)
        source = "\n".join([""] * 4 + ["export quic.send"])

        with _patch_ivy_ast():
            from ivy_lsp.parsing.ast_to_symbols import ast_to_symbols
            symbols = ast_to_symbols(ast, "test.ivy", source)

        sym = _find_symbol(symbols, "export quic.send")
        assert sym is not None
        # Line 5 (1-based) -> line 4 (0-based)
        assert sym.range[0] == 4, f"Expected start line 4, got {sym.range[0]}"

    def test_export_detail(self):
        decl = _make_export_decl([("quic.send", 3)])
        ast = _make_ast(decl)
        source = "\n\n\nexport quic.send"

        with _patch_ivy_ast():
            from ivy_lsp.parsing.ast_to_symbols import ast_to_symbols
            symbols = ast_to_symbols(ast, "test.ivy", source)

        sym = _find_symbol(symbols, "export quic.send")
        assert sym is not None
        assert sym.detail == "export quic.send"

    def test_multiple_exports_in_one_decl(self):
        decl = _make_export_decl([("quic.send", 3), ("quic.recv", 3)])
        ast = _make_ast(decl)
        source = "\n\nexport quic.send, quic.recv"

        with _patch_ivy_ast():
            from ivy_lsp.parsing.ast_to_symbols import ast_to_symbols
            symbols = ast_to_symbols(ast, "test.ivy", source)

        assert _find_symbol(symbols, "export quic.send") is not None
        assert _find_symbol(symbols, "export quic.recv") is not None

    def test_export_with_rep_fallback(self):
        """When relname is absent, fall back to rep."""
        decl = _FakeExportDecl()
        defn = _FakeExportDef()
        defn.args = [SimpleNamespace(rep="quic.alt_send")]  # no relname
        decl.args = [defn]
        decl.lineno = _make_lineno(2)
        ast = _make_ast(decl)
        source = "\nexport quic.alt_send"

        with _patch_ivy_ast():
            from ivy_lsp.parsing.ast_to_symbols import ast_to_symbols
            symbols = ast_to_symbols(ast, "test.ivy", source)

        sym = _find_symbol(symbols, "export quic.alt_send")
        assert sym is not None

    def test_export_no_lineno_defaults_to_zero(self):
        decl = _FakeExportDecl()
        defn = _FakeExportDef()
        defn.args = [SimpleNamespace(relname="quic.send")]
        decl.args = [defn]
        # No lineno attribute
        ast = _make_ast(decl)

        with _patch_ivy_ast():
            from ivy_lsp.parsing.ast_to_symbols import ast_to_symbols
            symbols = ast_to_symbols(ast, "test.ivy", "export quic.send")

        sym = _find_symbol(symbols, "export quic.send")
        assert sym is not None
        assert sym.range[0] == 0

    def test_export_empty_args(self):
        decl = _FakeExportDecl()
        decl.args = []
        decl.lineno = _make_lineno(1)
        ast = _make_ast(decl)

        with _patch_ivy_ast():
            from ivy_lsp.parsing.ast_to_symbols import ast_to_symbols
            symbols = ast_to_symbols(ast, "test.ivy", "")

        assert len(symbols) == 0

    def test_export_def_with_no_atom_args(self):
        decl = _FakeExportDecl()
        defn = _FakeExportDef()
        defn.args = []  # empty args on the def
        decl.args = [defn]
        decl.lineno = _make_lineno(1)
        ast = _make_ast(decl)

        with _patch_ivy_ast():
            from ivy_lsp.parsing.ast_to_symbols import ast_to_symbols
            symbols = ast_to_symbols(ast, "test.ivy", "")

        assert len(symbols) == 0


# ---------------------------------------------------------------------------
# Import symbol tests
# ---------------------------------------------------------------------------


class TestImportSymbolExtraction:
    """ImportDecl should produce Event symbols prefixed with 'import'."""

    def test_single_import(self):
        decl = _make_import_decl([("tls.handshake", 7)])
        ast = _make_ast(decl)
        source = "\n".join([""] * 6 + ["import tls.handshake"])

        with _patch_ivy_ast():
            from ivy_lsp.parsing.ast_to_symbols import ast_to_symbols
            symbols = ast_to_symbols(ast, "test.ivy", source)

        sym = _find_symbol(symbols, "import tls.handshake")
        assert sym is not None
        assert sym.kind == SymbolKind.Event
        assert sym.file_path == "test.ivy"

    def test_import_range_is_zero_based(self):
        decl = _make_import_decl([("tls.handshake", 7)])
        ast = _make_ast(decl)
        source = "\n".join([""] * 6 + ["import tls.handshake"])

        with _patch_ivy_ast():
            from ivy_lsp.parsing.ast_to_symbols import ast_to_symbols
            symbols = ast_to_symbols(ast, "test.ivy", source)

        sym = _find_symbol(symbols, "import tls.handshake")
        assert sym is not None
        # Line 7 (1-based) -> line 6 (0-based)
        assert sym.range[0] == 6

    def test_import_detail(self):
        decl = _make_import_decl([("tls.handshake", 3)])
        ast = _make_ast(decl)
        source = "\n\nimport tls.handshake"

        with _patch_ivy_ast():
            from ivy_lsp.parsing.ast_to_symbols import ast_to_symbols
            symbols = ast_to_symbols(ast, "test.ivy", source)

        sym = _find_symbol(symbols, "import tls.handshake")
        assert sym is not None
        assert sym.detail == "import tls.handshake"

    def test_multiple_imports(self):
        decl = _make_import_decl([("tls.handshake", 3), ("tls.close", 3)])
        ast = _make_ast(decl)
        source = "\n\nimport tls.handshake, tls.close"

        with _patch_ivy_ast():
            from ivy_lsp.parsing.ast_to_symbols import ast_to_symbols
            symbols = ast_to_symbols(ast, "test.ivy", source)

        assert _find_symbol(symbols, "import tls.handshake") is not None
        assert _find_symbol(symbols, "import tls.close") is not None


# ---------------------------------------------------------------------------
# Mixed export + import tests
# ---------------------------------------------------------------------------


class TestMixedExportImport:
    """AST with both ExportDecl and ImportDecl produces all symbols."""

    def test_exports_and_imports_coexist(self):
        export_decl = _make_export_decl([("quic.send", 3)])
        import_decl = _make_import_decl([("tls.handshake", 5)])
        ast = _make_ast(export_decl, import_decl)
        source = "\n\nexport quic.send\n\nimport tls.handshake"

        with _patch_ivy_ast():
            from ivy_lsp.parsing.ast_to_symbols import ast_to_symbols
            symbols = ast_to_symbols(ast, "test.ivy", source)

        assert _find_symbol(symbols, "export quic.send") is not None
        assert _find_symbol(symbols, "import tls.handshake") is not None

    def test_mixin_variant_still_skipped(self):
        """MixinDecl and VariantDecl must still produce no symbols."""
        mixin = _Sentinel()  # isinstance(mixin, ia.MixinDecl) -> True
        # We need a proper instance of the sentinel used for MixinDecl
        # Since _Sentinel is used for MixinDecl in our fake module,
        # create an instance that will match isinstance check.
        export_decl = _make_export_decl([("quic.send", 3)])
        ast = _make_ast(mixin, export_decl)
        source = "\n\nexport quic.send"

        with _patch_ivy_ast():
            from ivy_lsp.parsing.ast_to_symbols import ast_to_symbols
            symbols = ast_to_symbols(ast, "test.ivy", source)

        # MixinDecl (_Sentinel instance) produces no symbols
        # Only the export should appear
        names = [s.name for s in symbols]
        assert "export quic.send" in names
        # No other symbols from the mixin
        assert len(symbols) == 1
```

## Step 2: Run tests to verify they fail

Run: `python -m pytest tests/test_export_import_symbols.py -v`

Expected: FAIL -- `ExportDecl` is in the skip list at line 207-211, so `_convert_decl` returns `[]` for export/import declarations. All tests expecting symbols will fail with assertion errors.

## Step 3: Write minimal implementation

Modify `ivy_lsp/parsing/ast_to_symbols.py`.

**3a. Add `_atom_name` helper** (after `_name_from_args` at line 696):

```python
def _atom_name(atom: Any) -> Optional[str]:
    """Extract a name from an Ivy AST atom node.

    Checks ``relname`` first (preferred), then ``rep`` as fallback.
    Used by export/import converters where the atom is the action reference.
    """
    if atom is None:
        return None
    relname = getattr(atom, "relname", None)
    if relname:
        return relname
    rep = getattr(atom, "rep", None)
    if rep:
        return rep
    return None
```

**3b. Add `_convert_export` and `_convert_import`** (after `_convert_instantiate` at line 619, before the Helpers section):

```python
# ---------------------------------------------------------------------------
# Export/Import declarations
# ---------------------------------------------------------------------------


def _convert_export(decl: Any, filename: str, source: str) -> List[IvySymbol]:
    """Convert an ExportDecl to IvySymbol(s) with kind=Event.

    ExportDecl does not implement ``defines()``; instead we iterate
    ``decl.args`` (list of ExportDef) and extract the action name
    from each ``defn.args[0]`` atom.
    """
    symbols: List[IvySymbol] = []
    rng = _loc_to_tuple(getattr(decl, "lineno", None), source)
    for defn in getattr(decl, "args", []):
        atom = defn.args[0] if getattr(defn, "args", None) else None
        name = _atom_name(atom) if atom else None
        if name:
            symbols.append(
                IvySymbol(
                    name=f"export {name}",
                    kind=SymbolKind.Event,
                    range=rng,
                    detail=f"export {name}",
                    file_path=filename,
                )
            )
    return symbols


def _convert_import(decl: Any, filename: str, source: str) -> List[IvySymbol]:
    """Convert an ImportDecl to IvySymbol(s) with kind=Event.

    Same structure as ``_convert_export`` but for import declarations.
    """
    symbols: List[IvySymbol] = []
    rng = _loc_to_tuple(getattr(decl, "lineno", None), source)
    for defn in getattr(decl, "args", []):
        atom = defn.args[0] if getattr(defn, "args", None) else None
        name = _atom_name(atom) if atom else None
        if name:
            symbols.append(
                IvySymbol(
                    name=f"import {name}",
                    kind=SymbolKind.Event,
                    range=rng,
                    detail=f"import {name}",
                    file_path=filename,
                )
            )
    return symbols
```

**3c. Update `_convert_decl` skip list** at line 206-213:

Replace:

```python
    # Skip: MixinDecl, VariantDecl, ExportDecl, ImportDecl
    if isinstance(
        decl,
        (ia.MixinDecl, ia.VariantDecl, ia.ExportDecl, ia.ImportDecl),
    ):
        return []

    return []
```

With:

```python
    if isinstance(decl, (ia.MixinDecl, ia.VariantDecl)):
        return []
    if isinstance(decl, ia.ExportDecl):
        return _convert_export(decl, filename, source)
    if isinstance(decl, ia.ImportDecl):
        return _convert_import(decl, filename, source)

    return []
```

## Step 4: Run new tests to verify they pass

Run: `python -m pytest tests/test_export_import_symbols.py -v`

Expected: PASS (all 15 tests)

## Step 5: Run existing tests for regression

Run: `python -m pytest tests/test_task_1_4_ast_to_symbols.py -v`

Expected: PASS (all existing AST-to-symbol tests unchanged)

Run: `python -m pytest tests/test_task_1_2_symbols.py tests/test_task_1_6_document_symbols.py tests/test_task_1_7_workspace_symbols.py -v`

Expected: PASS

## Step 6: Commit

```bash
git add ivy_lsp/parsing/ast_to_symbols.py tests/test_export_import_symbols.py
git commit -m "feat(symbols): extract ExportDecl/ImportDecl as Event symbols"
```

---

## Corrections from original plan

This rewrite fixes the following issues in the original draft:

| Issue | Original | Fixed |
|-------|----------|-------|
| Weak test design | Source inspection via `inspect.getsource` | Full functional tests through public `ast_to_symbols()` API with mocked AST |
| Missing AST mock | Only `ExportDecl`/`ImportDecl` in fake module | All 18 decl types included via `_Sentinel` class so `isinstance` chain works |
| Non-existent helpers | `_get_name`, `_get_line_from_decl` (don't exist) | `_atom_name` (new, matches proven `_atom_to_name` in requirement_extractor), `_loc_to_tuple` (existing) |
| Incorrect atom access | `getattr(defn, "exported", None)` | `defn.args[0]` (matches actual ExportDef structure from test_export_import_extraction.py:191-208) |
| Missing edge cases | 2 tests total | 15 tests: basic, range, detail, multiple, rep fallback, no lineno, empty args, no atom args, mixed, regression |
| Untested fallback | No test for missing `relname` | `test_export_with_rep_fallback` verifies `.rep` field fallback |
