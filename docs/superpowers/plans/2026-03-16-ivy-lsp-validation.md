# Ivy LSP + Claude Code Integration — Validation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Validate that all changes from PRs ivy-lsp#4, panther-ivy-plugin#2, and PANTHER-Ivy#17 work correctly after plugin reload in a fresh Claude Code session.

**Architecture:** The Ivy integration has two layers: native LSP (`.lsp.json`) for code intelligence on `.ivy` files, and MCP tools (`.mcp.json`) for verification/analysis. Hooks, commands, skills, and agents orchestrate on top. All 9 Claude Code LSP operations are now implemented. Endpoint-type-aware file assembly filters test files during Docker compilation.

**Tech Stack:** Python (pygls, lsprotocol), Bash (hook scripts), pytest, Claude Code plugin system

---

## Context: What Was Changed

Three repos, three existing PRs:

| Repo | PR | Branch | Changes |
|------|-----|--------|---------|
| **ivy-lsp** | [#4](https://github.com/ElNiak/ivy-lsp/pull/4) | `fix/worktree-workspace-detection` | 4 new LSP handlers (`goToImplementation`, `prepareCallHierarchy`, `incomingCalls`, `outgoingCalls`), test framework (32 tests), synthetic fixtures, consolidated helpers |
| **panther-ivy-plugin** | [#2](https://github.com/ElNiak/panther-ivy-plugin/pull/2) | `fix/hook-json-and-lsp-hint` | 54 integration tests, `/nct-health` command, debugging docs in CLAUDE.md, fixed pre-consolidation tool name |
| **PANTHER-Ivy** | [#17](https://github.com/ElNiak/PANTHER-Ivy/pull/17) | `feat/mcp-tool-fixes-and-requirements` | `classify_endpoint_type()` in `_shared.py`, selective file copy in `_build_ivy_model_setup_commands()`, 9 classification tests |

## File Map (what to look at)

```
ivy-lsp/
  ivy_lsp/features/implementation.py     ← goToImplementation: maps before/after monitors
  ivy_lsp/features/call_hierarchy.py     ← prepareCallHierarchy + incomingCalls + outgoingCalls
  ivy_lsp/server.py:447,466-467         ← import + register new handlers
  pyproject.toml                         ← 4 new markers: lsp, mcp, plugin, real_spec
  tests/test_implementation.py           ← 7 unit tests
  tests/test_call_hierarchy.py           ← 10 unit tests
  tests/test_claude_lsp_coverage.py      ← 15 tests covering all 9 Claude Code LSP ops
  tests/helpers/                         ← mcp_helpers.py, lsp_helpers.py, fixtures/

panther-ivy-plugin/plugins/panther-ivy-plugin/
  CLAUDE.md                              ← LSP operations table + debugging section
  commands/nct-health.md                 ← 7-step health check command
  skills/tooling-reference/SKILL.md      ← verified: lists all 9 ops accurately
  tests/                                 ← 54 tests: hooks, manifests, docs, workspace detection

panther_ivy/
  _shared.py                             ← classify_endpoint_type() added
  ivy_command_mixin.py                   ← _build_ivy_model_setup_commands() selective copy
  tests/test_shared.py                   ← 9 classification unit tests
```

---

## Task 1: Run Automated Test Suites

**Files:**
- Test: `submodules/ivy-lsp/tests/`
- Test: `submodules/panther-ivy-plugin/plugins/panther-ivy-plugin/tests/`

- [ ] **Step 1: Run ivy-lsp full test suite**

```bash
cd panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp
pytest tests/ -q --ignore=tests/test_task_4_4_corpus.py --ignore=tests/test_task_4_5_e2e_serena.py
```

Expected: `1965 passed, 8 skipped` (skips are for missing QUIC spec files)

- [ ] **Step 2: Run new handler tests only**

```bash
pytest tests/test_implementation.py tests/test_call_hierarchy.py tests/test_claude_lsp_coverage.py -v
```

Expected: `32 passed` — all 9 LSP operations verified

- [ ] **Step 3: Run plugin integration tests**

```bash
cd ../panther-ivy-plugin/plugins/panther-ivy-plugin
pytest tests/ -v
```

Expected: `54 passed` — hooks, manifests, documentation accuracy, workspace detection

- [ ] **Step 4: Verify no pre-consolidation tool names**

The `test_documentation.py::TestNoPreConsolidationToolNames` tests scan all skills, agents, and commands for stale tool names like `ivy_traceability_matrix`. If any test fails, a stale reference was reintroduced.

---

## Task 2: Validate New LSP Handlers (Manual)

**Files:**
- Verify: `ivy_lsp/features/implementation.py`
- Verify: `ivy_lsp/features/call_hierarchy.py`

- [ ] **Step 1: Find a test file with before/after monitors**

```
Glob(pattern="protocol-testing/quic/**/*behavior*.ivy")
```

Pick any result. Read it to find an action name and its line number.

- [ ] **Step 2: Test goToImplementation (forward)**

```
LSP(operation="goToImplementation", filePath="<behavior_file>", line=<action_line>, character=<action_col>)
```

Expected: Returns locations pointing to `before <action>` and/or `after <action>` blocks. If the action is defined in a different file, results may point to that file.

- [ ] **Step 3: Test goToImplementation (reverse)**

Find a `before <action>` line in the file. Put cursor on the action name after `before`.

```
LSP(operation="goToImplementation", filePath="<file>", line=<before_line>, character=<action_col>)
```

Expected: Returns the action declaration location (not the monitor).

- [ ] **Step 4: Test prepareCallHierarchy**

```
LSP(operation="prepareCallHierarchy", filePath="<file>", line=<action_line>, character=<action_col>)
```

Expected: Returns a `CallHierarchyItem` with `name` matching the action, `kind=Function`.

- [ ] **Step 5: Test incomingCalls**

```
LSP(operation="incomingCalls", filePath="<file>", line=<action_line>, character=<action_col>)
```

Expected: Returns list of callers. For well-connected actions, expect `before`/`after` monitors and other actions that reference this one.

- [ ] **Step 6: Test outgoingCalls**

```
LSP(operation="outgoingCalls", filePath="<file>", line=<action_line>, character=<action_col>)
```

Expected: Returns actions referenced in the body. For declaration-only actions (no body), returns empty list.

- [ ] **Step 7: Regression-check existing operations**

```
LSP(operation="goToDefinition", filePath="<any .ivy>", line=<include_line>, character=8)
LSP(operation="findReferences", filePath="<any .ivy>", line=<type_line>, character=5)
LSP(operation="hover", filePath="<any .ivy>", line=<action_line>, character=7)
LSP(operation="documentSymbol", filePath="<any .ivy>", line=1, character=1)
```

Expected: Each returns non-null results for valid symbols.

---

## Task 3: Validate Plugin Hooks (Manual)

**Files:**
- Verify: `hooks/scripts/block-direct-ivy.sh`
- Verify: `hooks/scripts/post-write-ivy-lint.sh`
- Verify: `hooks/scripts/detect-ivy-workspace.sh`

- [ ] **Step 1: Check SessionStart hook fired**

At the top of a fresh session, look for `[ivy-workspace]` in the context. If present, the SessionStart hook detected the workspace.

- [ ] **Step 2: Trigger PreToolUse hook**

```bash
ivy_check somefile.ivy
```

Expected: Advisory message suggesting `ivy_verify` MCP tool instead. Command is NOT blocked (exit 0).

- [ ] **Step 3: Trigger PostToolUse hook**

Write a `.ivy` file missing the `#lang ivy1.7` header:

```
Write(file_path="<tmp>/test_no_header.ivy", content="type cid\n")
```

Expected: Warning in tool output about missing `#lang ivy1.7` header. Write is NOT blocked.

---

## Task 4: Validate /nct-health Command (Manual)

**Files:**
- Verify: `commands/nct-health.md`

- [ ] **Step 1: Run /nct-health**

```
/nct-health
```

Expected: A 7-row table with PASS/FAIL status:

| # | Check | Expected |
|---|-------|----------|
| 1 | LSP process alive | PASS (PID shown) |
| 2 | LSP log health | PASS (no CRITICAL) |
| 3 | LSP responding | PASS (symbols returned) |
| 4 | MCP server alive | PASS (capabilities listed) |
| 5 | Workspace access | PASS (ivy_lint returns result) |
| 6 | Model builds | PASS or FAIL (depends on workspace content) |
| 7 | Cross-file resolution | PASS (definition location returned) |

If any fail, the command should show `### Suggested Actions` section.

---

## Task 5: Validate MCP Tool Smoke Tests

**Files:**
- Verify: MCP server connectivity and tool responses

- [ ] **Step 1: Test ivy_capabilities (no model needed)**

```
mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_capabilities()
```

Expected: JSON with `success: true` and capability flags.

- [ ] **Step 2: Test ivy_lint (fast, no subprocess)**

```
mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_lint(relative_path="<any .ivy file>")
```

Expected: JSON with `success`, `file`, `diagnostics`, `diagnostic_count`.

- [ ] **Step 3: Test ivy_coverage (triggers model build)**

```
mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_coverage(mode="stats")
```

Expected: JSON with `total`, `covered`, `coverage_percent`. First call may be slow (model build).

---

## Task 6: Validate Documentation Accuracy

**Files:**
- Verify: `skills/tooling-reference/SKILL.md`
- Verify: `CLAUDE.md`

- [ ] **Step 1: Check tooling-reference skill**

Read `skills/tooling-reference/SKILL.md` line 53. Should list exactly:
`goToDefinition`, `findReferences`, `hover`, `documentSymbol`, `workspaceSymbol`, `goToImplementation`, `prepareCallHierarchy`, `incomingCalls`, `outgoingCalls`

- [ ] **Step 2: Check CLAUDE.md LSP section**

Read the `**Ivy LSP**` section. Should have a table with 3 categories:
- Navigation: goToDefinition, goToImplementation, findReferences
- Inspection: hover, documentSymbol, workspaceSymbol
- Call graph: prepareCallHierarchy, incomingCalls, outgoingCalls

- [ ] **Step 3: Check CLAUDE.md debugging section**

Should exist with:
- Log file location: `/tmp/ivy-lsp.log`
- Environment variables: `IVY_LSP_LOG_LEVEL`, `IVY_LSP_FORCE_REINSTALL`, `IVY_LSP_DEV_ROOT`
- Restart instructions

---

## Task 7: Validate Endpoint-Type File Assembly (Code Review Only)

**Files:**
- Verify: `_shared.py` — `classify_endpoint_type()`
- Verify: `ivy_command_mixin.py` — `_build_ivy_model_setup_commands()`

- [ ] **Step 1: Verify classify_endpoint_type exists**

```python
# In _shared.py, should find:
def classify_endpoint_type(test_name: str, role_name: str) -> str:
    # Returns 'server', 'client', or 'mim'
    # Priority: mim > client > server > attacker(→server) > oppose_role fallback
```

- [ ] **Step 2: Verify selective copy logic**

Read `ivy_command_mixin.py`, method `_build_ivy_model_setup_commands()`. Should:
1. Copy all non-test `.ivy` files (stack, shims, config, utils)
2. Copy ONLY `{protocol}_tests/{endpoint_type}_tests/` — not all test subdirs
3. Fall back to copying all tests if the expected subdirectory doesn't exist
4. Log protocol name and endpoint type for debugging

- [ ] **Step 3: Run classification unit tests**

```bash
cd panther/plugins/services/testers/panther_ivy
pytest tests/test_shared.py -k classify -v
```

Expected: 9 tests pass (server/client/mim detection, attacker mapping, fallback via oppose_role, case insensitivity)

---

## Points of Interest for Future Sessions

### API Shape Gotcha: IvySymbol vs SymbolLocation

```
indexer.lookup_all_symbols()  → List[IvySymbol]      # .name, .detail, .kind, .range, .file_path
indexer.lookup_symbol(name)   → List[SymbolLocation]  # .symbol (IvySymbol), .filepath, .range
indexer.get_symbols(filepath) → List[IvySymbol]       # .name, .detail, .kind, .range, .file_path
```

The two API families return different wrapper types. `lookup_symbol` wraps in `SymbolLocation`; the others return raw `IvySymbol`. This bit us during implementation — don't confuse `.symbol.name` (SymbolLocation) with `.name` (IvySymbol).

### How goToImplementation Works

Ivy has no interface/implementation split. The mapping:
- Action `foo` → its "implementations" are `before foo { ... }` and `after foo { ... }` monitor blocks
- Monitor `before foo` → its "implementation" is the action declaration `action foo(...)`

The handler queries `indexer.lookup_all_symbols()` and filters by `detail` starting with `"before "` or `"after "`. The fallback scanner produces symbols like `IvySymbol(name="connect", detail="before connect(src:cid, dst:cid)", kind=Function)`.

### How Call Hierarchy Works

- **prepareCallHierarchy**: Resolves word at cursor via `indexer.lookup_symbol()`, returns `CallHierarchyItem` with `data={"name": word, "filepath": ...}` stashed for subsequent calls
- **incomingCalls**: Regex-scans all workspace files for the symbol name (same as `findReferences`), groups matches by their containing symbol (`_find_containing_symbol` heuristic)
- **outgoingCalls**: Extracts lines between declaration and next declaration, scans for known action names from `_get_action_symbols(indexer)`

### Known Limitations

1. **Call hierarchy is approximate** — `outgoingCalls` doesn't parse brace-matched scopes, just line ranges between declarations
2. **`_find_containing_symbol` uses line-proximity heuristic** — may be wrong for complex nesting
3. **Plugin tests need `python3` + `bash`** — hook scripts use `python3 -c "import json..."`
4. **`test_shared.py` has pre-existing import issue** — `from ._shared import ...` resolves to wrong package
5. **Pyright mixin noise** — `ivy_command_mixin.py` has many `reportAttributeAccessIssue` warnings (pre-existing)

### Debugging Cheat Sheet

| Symptom | Check | Fix |
|---------|-------|-----|
| LSP not starting | `cat /tmp/ivy-lsp.log` | Check `uvx` on PATH, Z3 availability |
| Empty LSP results | Log for "indexed N files" | Check `IVY_LSP_INCLUDE_PATHS` |
| MCP unresponsive | `ivy_capabilities` returns error | Check `.mcp.json`, restart server |
| Wrong workspace | SessionStart hook output | Check `detect-ivy-workspace.sh` detection logic |
| ARM Z3 errors | Platform check | Use `development-scp-refactor` branch |

### Environment Variables

| Variable | Purpose | Default |
|----------|---------|---------|
| `IVY_LSP_LOG_LEVEL` | Log verbosity | `INFO` |
| `IVY_LSP_LOG_FILE` | Log file path | `/tmp/ivy-lsp.log` |
| `IVY_LSP_DEV_ROOT` | Local ivy-lsp source override | (none) |
| `IVY_LSP_FORCE_REINSTALL` | Force `uvx` reinstall | (none) |
| `IVY_LSP_INCLUDE_PATHS` | Workspace include filter | `protocol-testing` |
| `IVY_LSP_EXCLUDE_PATHS` | Workspace exclude filter | `submodules,test,doc,...` |
