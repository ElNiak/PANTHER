# Scoped Requirement Model -- TDD Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Replace the flat `RequirementGraph` with a `ScopedRequirementModel` that scopes requirements per-test, understands export/import semantics, role partitioning, and NCT classification -- fixing the triple-counting bug in diagnostics. Extend with LSP server enhancements and full VSCode extension client-side integration.

**Architecture:** Subclass `RequirementGraph` (not replace) with `ScopedRequirementModel` that adds a `TestScope` layer on top. All existing call sites get scoped queries via backward-compatible methods; new scoped methods enable per-test views. `ExportImportInfo` extracted per-file feeds into `TestScope` computation. VSCode extension provides status bar, Quick Pick, and auto-detection UI.

**Tech Stack:** Python 3.10+, pytest, lsprotocol, dataclasses (LSP server). TypeScript, VSCode Extension API, vscode-languageclient (VSCode extension). No new dependencies.

**Base paths:**
- **LSP server:** `panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp/`
- **VSCode extension:** `panther/plugins/services/testers/panther_ivy/submodules/vscode-ivy/`

**Test runners:**
- LSP: `cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp && python -m pytest tests/<file> -v`
- VSCode: `cd panther/plugins/services/testers/panther_ivy/submodules/vscode-ivy && npm run pretest && npm test`

---

## Task List

### Phase 1: Core Model (Tasks 1-7)

| # | Task | Status | Files |
|---|------|--------|-------|
| 1 | [ExportImportInfo Data Structure](./01-export-import-info.md) | pending | create `test_scope.py`, test `test_export_import_extraction.py` |
| 2 | [Light-Mode Export/Import Extraction](./02-light-mode-export-import.md) | pending | modify `light_mode_extractor.py`, extend test |
| 3 | [Full-Mode AST Export/Import Extraction](./03-full-mode-export-import.md) | pending | modify `requirement_extractor.py`, extend test |
| 4 | [TestScope & Role Detection](./04-test-scope-role-detection.md) | pending | modify `test_scope.py`, create `test_test_scope.py` |
| 5 | [ScopedRequirementModel Core](./05-scoped-requirement-model.md) | pending | modify `test_scope.py`, create `test_scoped_requirement_model.py` |
| 6 | [WorkspaceIndexer Integration](./06-workspace-indexer-integration.md) | pending | modify `workspace_indexer.py`, create `test_workspace_indexer_scoping.py` |
| 7 | [NCT Classification](./07-nct-classification.md) | pending | modify `test_scope.py`, create `test_nct_classification.py` |

### Phase 2: LSP Features (Tasks 8-16)

| # | Task | Status | Files |
|---|------|--------|-------|
| 8 | [Scoped Code Lenses](./08-scoped-code-lenses.md) | pending | modify `code_lens.py`, create `test_scoped_code_lens.py` |
| 9 | [Scoped Diagnostics](./09-scoped-diagnostics.md) | pending | modify `diagnostics.py`, create `test_scoped_diagnostics.py` |
| 10 | [Active Test Selector + Compile Commands](./10-active-test-commands.md) | pending | modify `commands.py`, create `test_active_test_commands.py` |
| 11 | [Symbol Extraction for ExportDecl/ImportDecl](./11-export-import-symbols.md) | pending | modify `ast_to_symbols.py`, create `test_export_import_symbols.py` |
| 12 | [Integration Regression Tests](./12-integration-regression-tests.md) | pending | create `test_scoped_integration.py` |
| 13 | [Scoped NCT Counts](./13-scoped-nct-counts.md) | pending | modify `test_scope.py`, extend `test_scoped_requirement_model.py` |
| 14 | [NCT Code Lens Labels](./14-nct-code-lens-labels.md) | pending | modify `code_lens.py`, extend `test_scoped_code_lens.py` |
| 15 | [Diagnostic Refresh on setActiveTest](./15-diagnostic-refresh.md) | pending | modify `commands.py`, extend `test_active_test_commands.py` |
| 16 | [activeDocumentChanged Handler](./16-active-document-changed.md) | pending | modify `commands.py`, extend `test_active_test_commands.py` |

### Phase 3: VSCode Extension (Tasks 17-21)

| # | Task | Status | Files |
|---|------|--------|-------|
| 17 | [VSCode package.json Updates](./17-vscode-package-json.md) | pending | modify `package.json`, extend tests |
| 18 | [VSCode Test Scope Module](./18-vscode-test-scope-module.md) | pending | create `src/testScope.ts` |
| 19 | [VSCode Extension Wiring](./19-vscode-extension-wiring.md) | pending | modify `src/extension.ts` |
| 20 | [VSCode Scoping Tests](./20-vscode-scoping-tests.md) | pending | extend test suites, create `testScope.test.ts` |
| 21 | [VSCode Version Bump](./21-vscode-version-bump.md) | pending | modify `package.json` |

### Phase 4: Release (Task 22)

| # | Task | Status | Files |
|---|------|--------|-------|
| 22 | [ivy-lsp v0.7.0 Version Bump & Release](./22-ivy-lsp-version-bump-and-release.md) | pending | modify `pyproject.toml`, merge + tag |

---

## Dependency Graph

```
Tasks 1-7 (core model) ──────────────────────────────────────────────┐
                                                                     │
Task 07 (nct class.) ───┐                                           │
Task 08 (scoped lens) ──┤                                           │
Task 13 (nct counts) ───┤─→ Task 14 (nct code lens labels)         │
     └── depends on 07 ─┘                                           │
                                                                     │
Task 10 (active cmds) ──┬─→ Task 15 (diagnostic refresh)           │
                        └─→ Task 16 (activeDocumentChanged)         │
                                                                     │
Task 11 (export/import symbols) ── independent                      │
                                                                     │
Tasks 5,6,8,9,14,15,16 ────────→ Task 12 (integration tests)       │
                                                                     │
Task 12 ────────────────────────→ Task 22 (ivy-lsp v0.7.0 release) │
                                                                     │
Task 17 (package.json) ─→ Task 18 (testScope.ts) ─→ Task 19 (wiring)│
    ─→ Task 20 (tests) ─→ Task 21 (version bump)                    │
```

**Dependency notes:**
- Task 13 depends on Task 7 (NCT classification) and Task 5 (ScopedRequirementModel)
- Task 12 (integration tests) should run after Tasks 14, 15, 16 are complete (not just 5, 6, 8, 9)
- Task 9 (scoped diagnostics) is also a prerequisite for Task 12

---

## Verification

### LSP server: Run full test suite

```bash
cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp
python -m pytest tests/ -v --tb=short
```

### LSP server: Existing tests must still pass

```bash
python -m pytest tests/test_requirement_graph.py -v
python -m pytest tests/test_light_mode_extractor.py -v
python -m pytest tests/test_code_lens.py -v
python -m pytest tests/test_requirement_diagnostics.py -v
```

### VSCode extension: Build and test

```bash
cd panther/plugins/services/testers/panther_ivy/submodules/vscode-ivy
npm run compile
npm run pretest && npm test
```

### Known limitations

- `ivy.testScope.showNctLabels` is declared in `package.json` (Task 17) but is NOT consumed by any server-side or client-side code in the current plan. It is a user-facing setting placeholder for future use. A follow-up task could wire it into `ivy/setActiveTest` as a param or read it in the code lens handler via a custom LSP request. For now, NCT labels are always shown when scoped.

### Key invariants

- `ScopedRequirementModel` passes ALL existing `test_requirement_graph.py` tests unchanged (subclass)
- Code lenses show correct counts when active test is set
- Code lenses show NCT tags (`[ASSUMPTION]`/`[GUARANTEE]`) when scoped
- Diagnostics don't flag non-exported actions
- `ivy/setActiveTest` refreshes diagnostics for all open documents
- `ivy/activeDocumentChanged` auto-sets scope for test files, sticky for non-test files
- VSCode status bar shows active test, Quick Pick lists available tests
- Cache invalidation works on file save/reindex

### Final verification: file count

```bash
ls docs/plans/tasks/scoped-requirement-model/
# Should show 23 files: 00-overview.md through 22-ivy-lsp-version-bump-and-release.md
```
