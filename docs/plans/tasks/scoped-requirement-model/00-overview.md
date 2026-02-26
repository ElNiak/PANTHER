# Scoped Requirement Model -- TDD Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the flat `RequirementGraph` with a `ScopedRequirementModel` that scopes requirements per-test, understands export/import semantics, role partitioning, and NCT classification -- fixing the triple-counting bug in diagnostics.

**Architecture:** Subclass `RequirementGraph` (not replace) with `ScopedRequirementModel` that adds a `TestScope` layer on top. All existing call sites get scoped queries via backward-compatible methods; new scoped methods enable per-test views. `ExportImportInfo` extracted per-file feeds into `TestScope` computation.

**Tech Stack:** Python 3.10+, pytest, lsprotocol, dataclasses. No new dependencies.

**Base path for all files:** `panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp/`

**Test runner:** `cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp && python -m pytest tests/<file> -v`

---

## Task List

| # | Task | Status | Files |
|---|------|--------|-------|
| 1 | [ExportImportInfo Data Structure](./01-export-import-info.md) | pending | create `test_scope.py`, test `test_export_import_extraction.py` |
| 2 | [Light-Mode Export/Import Extraction](./02-light-mode-export-import.md) | pending | modify `light_mode_extractor.py`, extend test |
| 3 | [Full-Mode AST Export/Import Extraction](./03-full-mode-export-import.md) | pending | modify `requirement_extractor.py`, extend test |
| 4 | [TestScope & Role Detection](./04-test-scope-role-detection.md) | pending | modify `test_scope.py`, create `test_test_scope.py` |
| 5 | [ScopedRequirementModel Core](./05-scoped-requirement-model.md) | pending | modify `test_scope.py`, create `test_scoped_requirement_model.py` |
| 6 | [WorkspaceIndexer Integration](./06-workspace-indexer-integration.md) | pending | modify `workspace_indexer.py`, create `test_workspace_indexer_scoping.py` |
| 7 | [NCT Classification](./07-nct-classification.md) | pending | modify `test_scope.py`, create `test_nct_classification.py` |
| 8 | [Scoped Code Lenses](./08-scoped-code-lenses.md) | pending | modify `code_lens.py`, create `test_scoped_code_lens.py` |
| 9 | [Scoped Diagnostics](./09-scoped-diagnostics.md) | pending | modify `diagnostics.py`, create `test_scoped_diagnostics.py` |
| 10 | [Active Test Selector + Compile Commands](./10-active-test-commands.md) | pending | modify `commands.py`, create `test_active_test_command.py` |
| 11 | [Symbol Extraction for ExportDecl/ImportDecl](./11-export-import-symbols.md) | pending | modify `ast_to_symbols.py` |
| 12 | [Integration Regression Tests](./12-integration-regression-tests.md) | pending | create `test_scoped_integration.py` |

---

## Verification

### Run full test suite

```bash
cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp
python -m pytest tests/ -v --tb=short
```

### Existing tests must still pass

```bash
python -m pytest tests/test_requirement_graph.py -v
python -m pytest tests/test_light_mode_extractor.py -v
python -m pytest tests/test_code_lens.py -v
python -m pytest tests/test_requirement_diagnostics.py -v
```

### Key invariants

- `ScopedRequirementModel` passes ALL existing `test_requirement_graph.py` tests unchanged (subclass)
- Code lenses show correct counts when active test is set
- Diagnostics don't flag non-exported actions
- Cache invalidation works on file save/reindex
