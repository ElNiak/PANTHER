# LSP + MCP Health, Observability & Performance Fixes — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix 6 issues: nct-health check order, staging_health fallback, tier 1/2 caching, observability session IDs, Serena upstream sync, and MCP output investigation.

**Architecture:** Three submodules modified in the `lsp-to-claude` worktree: `panther-ivy-plugin` (commands, hooks), `ivy-lsp` (MCP tools, server setup, bulk orchestrator), `panther-serena` (upstream merge). Changes are independent per-issue; issues 1-3 can be parallelized.

**Tech Stack:** Python 3.10+, Ivy LSP, MCP protocol, Claude Code hooks (JSON), Markdown skills

**Submodule base paths:**
- `PLUGIN`: `panther/plugins/services/testers/panther_ivy/submodules/panther-ivy-plugin/plugins/panther-ivy-plugin`
- `IVY_LSP`: `panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp`
- `SERENA`: `panther/plugins/services/testers/panther_ivy/submodules/panther-serena`

---

## Task 1: Rework nct-health check order (Issue #5)

**Files:**
- Modify: `$PLUGIN/commands/nct-health.md`

- [ ] **Step 1: Read the current nct-health.md**

Read the full file to understand current structure before rewriting.

- [ ] **Step 2: Rewrite nct-health.md with trigger-first order**

Replace the entire content of `$PLUGIN/commands/nct-health.md` with the new 3-phase structure. Key changes:

1. Phase 1 (Trigger): MCP `ivy_capabilities` first (Step 1), then LSP `documentSymbol` (Step 2). If both fail → early exit.
2. Phase 2 (Validate): PID files using `ps -p` not `kill -0` (Step 3), log health (Step 4), layer staging from Step 1 data (Step 5).
3. Phase 3 (Deep): workspace access (Step 6), coverage pipeline (Step 7), cross-file resolution (Step 8), cross-layer resolution (Step 9).

The new nct-health.md structure:

```markdown
---
name: nct-health
description: Run a health check sequence for the Ivy LSP + MCP integration
arguments: []
---
<!-- MODE: FAST — Diagnostic health check, no orchestrator required -->

Run a comprehensive health check of the Ivy LSP and MCP integration stack, reporting PASS/FAIL for each step.

## Instructions

**Workspace Status**: Before running checks, call `ivy_workspace(action="get")` to confirm the active workspace. Report the current workspace state as a preliminary line in the results table.

Run the following 9 checks in order across 3 phases. For each check, record PASS, WARN, or FAIL with a short detail message. If a check fails, continue with the remaining checks (do not abort early) **unless Phase 1 fails entirely** — in that case skip Phases 2-3 and report "Server unreachable."

### Phase 1 — Trigger (forces server start)

### Step 1: MCP server alive

Call `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_capabilities` with no arguments.

- If the tool returns a JSON result with capabilities listed: **PASS** — report the number of capabilities. **Save the full result for use in Step 5.**
- If the tool errors or times out: **FAIL** — report the error.

### Step 2: LSP responding

Use `LSP(operation="documentSymbol", filePath="<path_to_ivy_file>", line=1, character=1)` to request a document symbol list from any `.ivy` file in the workspace. If no `.ivy` file is known, use `Glob` to find one first (e.g., `**/*.ivy` under the protocol-testing directory).

- If the LSP returns a symbol list (even empty): **PASS** — report the number of symbols.
- If the LSP times out or returns an error: **FAIL** — report the error message.

**Early exit**: If BOTH Step 1 AND Step 2 fail, skip Phases 2-3 entirely. Report: "Server unreachable — check installation and PATH. Run `ivy_lsp --help` to verify the binary is available."

### Phase 2 — Validate infrastructure (now fresh)

### Step 3: LSP process alive

**Primary: PID tracking files.** Run via Bash:
```
for f in /tmp/ivy-lsp-pids/*.pid; do
  [ -f "$f" ] || continue
  pid=$(cat "$f")
  if ps -p "$pid" > /dev/null 2>&1; then
    echo "ALIVE $(basename "$f") pid=$pid"
  else
    echo "STALE $(basename "$f") pid=$pid"
  fi
done
```

Classification:
- **PASS**: At least one tracked PID file reports ALIVE.
- **WARN**: Stale PID files exist alongside live ones (suggest cleanup), OR only untracked processes found (no PID files).
- **FAIL**: No live processes found. (Unlikely since Phase 1 succeeded.)

### Step 4: LSP log health

**Check log freshness.** Run via Bash:
```
python3 -c "import os,time; s=os.stat('/tmp/ivy-lsp-latest.log'); age=time.time()-s.st_mtime; print(f'age_seconds={int(age)}')"
```

**Count errors in recent lines only (NOT the entire file).** Run via Bash:
```
tail -50 /tmp/ivy-lsp-latest.log | grep -v -E '\[SIGTERM\]|shutdown|write to closed|BrokenPipeError|ConnectionResetError|interpreter shutdown' | grep -c -E 'CRITICAL|Traceback'
```

**Count include_resolver errors in recent lines.** Run via Bash:
```
tail -200 /tmp/ivy-lsp-latest.log | grep -c "include_resolver ERROR"
```

**Shutdown noise filter**: Lines matching any of the following patterns are benign session teardown artifacts and MUST NOT cause a FAIL: `[SIGTERM]`, `shutdown`, `write to closed`, `BrokenPipeError`, `ConnectionResetError`, `interpreter shutdown`.

Classification:
- If the log file does not exist: **FAIL** — "Log file /tmp/ivy-lsp-latest.log not found."
- If non-shutdown CRITICAL/Traceback count (from `tail -50`) > 0: **FAIL** — quote the relevant non-shutdown line(s).
- If include_resolver ERROR count (from `tail -200`) > 10: **WARN** — "Include resolver has N errors in recent entries."
- If log age > 300 seconds but Phase 1 shows LSP is alive: **WARN** — "Log is stale (Ns old) but LSP responded. Symlink may point to a prior instance's log."
- Otherwise: **PASS** — "No critical errors in recent log entries."

### Step 5: Layer staging active

**Primary: Use MCP capabilities data from Step 1.** Extract `staging_health` from the `ivy_capabilities` result already obtained in Step 1. If Step 1 failed, skip to the fallback.

Report: `layers_active`, `layer_count`, `total_staged`, `files_mapped_to_layers`.

Classification:
- If `staging_health.layers_active` is `true`: **PASS** — report layer_count and total_staged.
- If `staging_health.layers_active` is `false` but `total_staged > 0`: **WARN** — "Flat staging (no layers) with N staged files."
- If `staging_health.source` is `"workspace_config_fallback"`: **WARN** — "Staging not built yet. Layer config found in .ivyworkspace (N layers defined). Staging builds after first file analysis."
- If `staging_health.symlink_failures > 0`: **WARN** — "N symlink failures detected in staging."
- If Step 1 failed (no capabilities data): **WARN** — "Layer staging status unknown."

### Phase 3 — Deep functional checks

### Step 6: Workspace access

Use `Glob` to find any `.ivy` file in the workspace. Then call `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_diagnostics` with:
- `relative_path`: the path to the found `.ivy` file
- `mode`: `"structural"`

- If the tool returns a result (even with diagnostics): **PASS** — report the file and diagnostic count.
- If no `.ivy` files exist in the workspace: **FAIL** — "No .ivy files found in workspace."
- If the tool errors: **FAIL** — report the error.

### Step 7: Coverage pipeline

Call `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_coverage` with `mode=stats` to test that the model analysis pipeline works.

- If the tool returns stats or coverage data: **PASS** — report a summary (e.g., number of requirements, coverage percentage).
- If the tool errors: **FAIL** — report the error.

### Step 8: Cross-file resolution

Use the IDE LSP `goToDefinition` on a known symbol in an `.ivy` file. If no symbol is known, pick one from the symbol list obtained in Step 2.

- If the LSP returns a definition location (file + line): **PASS** — report the target location.
- If the LSP returns no results or errors: **FAIL** — report the issue.

### Step 9: Cross-layer include resolution

Use LSP `goToDefinition` on a symbol that requires cross-directory include resolution. Find a file in a subdirectory that includes a file from a different subdirectory (e.g., `quic_attacks_stack/*.ivy` including `quic_types` from `quic_stack/`).

- If the LSP returns a definition in a different directory: **PASS**
- If the LSP returns no results: **FAIL** — "Cross-directory resolution is broken. Check layer staging."

## Result Presentation

Present the final results in this format:

```
## Ivy LSP + MCP Health Check

| # | Check                    | Status | Details                          |
|---|--------------------------|--------|----------------------------------|
| 1 | MCP server alive         | PASS   | 19 tools, 3 CLI tools            |
| 2 | LSP responding           | PASS   | 42 symbols returned              |
| 3 | LSP process alive        | PASS   | PID 12345                        |
| 4 | LSP log health           | PASS   | No critical errors               |
| 5 | Layer staging active     | PASS   | 2 layers, 180 staged files       |
| 6 | Workspace access         | PASS   | quic_types.ivy — 0 diagnostics   |
| 7 | Coverage pipeline        | PASS   | 97 requirements tracked          |
| 8 | Cross-file resolution    | PASS   | quic_frame.ivy:34                |
| 9 | Cross-layer resolution   | PASS   | quic_types resolved from attacks |

**Overall: 9/9 PASS**
```

### Interactive Follow-up

After presenting the result table, engage the user. Reference the `interaction-patterns` skill for checkpoint format details.

**If any checks FAIL → Gate**:
- Ask: "Health check found {N} failure(s). Which would you like to investigate first?"
- List the failed checks as numbered options.
- Wait for user selection before showing suggested actions for that check.

**If all checks PASS → Inform-and-Continue**:
- State: "All 9 checks pass. System is healthy. Run `/nct-validate` for deeper correctness testing?"

**If WARNings present (but no FAILs) → Collaborative**:
- State: "Health check passed with {N} warning(s): {list}. Any concern, or good to proceed?"

If any checks fail, add a `### Suggested Actions` section at the end:

- If Step 1 fails: "The MCP server is not reachable. Check the plugin configuration and `ivy_lsp --help`."
- If Step 2 fails: "The LSP process may be running but unresponsive. Try restarting it."
- If Step 3 fails: "Stale PID files found. Clean up with `rm /tmp/ivy-lsp-pids/*.pid`."
- If Step 4 fails: "Inspect `/tmp/ivy-lsp-latest.log` for crash details. Consider restarting the LSP."
- If Step 5 warns: "Layer staging is not active. Ensure `.ivyworkspace` has `workspace_layers` defined."
- If Step 6 fails: "Ensure `.ivy` files exist in the workspace and the MCP server has read access."
- If Step 7 fails: "Model analysis failed. This may indicate a missing or corrupt protocol model."
- If Step 8 fails: "Cross-file resolution is not working. The LSP index may need rebuilding."
- If Step 9 fails: "Cross-directory resolution is broken. Check layer staging and `.ivyworkspace` configuration."

See the `tooling-reference` skill for LSP and MCP architecture.
```

- [ ] **Step 3: Verify the new skill renders correctly**

Run `/nct-health` in a test to verify the new check order works and Phase 1 triggers the server before infrastructure validation.

- [ ] **Step 4: Commit**

```bash
cd $PLUGIN && git add commands/nct-health.md
git commit -m "fix(nct-health): reorder checks to trigger-first (Phase 1: MCP+LSP, Phase 2: infra, Phase 3: deep)"
```

---

## Task 2: Fix observability session ID propagation (Issue #4)

**Files:**
- Modify: `$PLUGIN/hooks/scripts/observability/obs_session_start.py`
- Modify: `$PLUGIN/hooks/scripts/observability/log_event.py` (verify `_resolve_session_id`)

- [ ] **Step 1: Investigate what Claude Code sets in hook env**

Run via Bash to check what env vars Claude Code provides to hooks:

```bash
python3 -c "import os, json; print(json.dumps({k:v for k,v in os.environ.items() if 'SESSION' in k or 'CLAUDE' in k}, indent=2))"
```

This tells us which session ID variables are actually available.

- [ ] **Step 2: Read current _resolve_session_id in log_event.py**

The existing `_resolve_session_id()` at `log_event.py:51-76` already has a priority chain:
1. ivy-lsp canonical resolver (if importable)
2. `IVY_SESSION_ID` env var
3. session file (`/tmp/ivy-session-<ws_hash>.id`)
4. raw `session_id` from stdin
5. `"unknown"` fallback

The issue is that the **hook stdin data** (`data.get("session_id", "")`) may be empty AND `IVY_SESSION_ID` isn't set in the hook environment (it's only set by `start-ivy-server.sh`).

- [ ] **Step 3: Fix _resolve_session_id to check CLAUDE_SESSION_ID**

Edit `$PLUGIN/hooks/scripts/observability/log_event.py`, modify the inline fallback at line 63-76:

```python
def _resolve_session_id(raw_session_id: str) -> str:
    """Resolve session ID — delegates to ivy-lsp canonical resolver with fallback."""
    if _canonical_resolve is not None:
        return _canonical_resolve()
    # Inline fallback matching ivy-lsp priority
    for var in ("IVY_SESSION_ID", "CLAUDE_SESSION_ID", "CLAUDE_CODE_SESSION_ID"):
        from_env = os.environ.get(var, "").strip()
        if from_env:
            return from_env
    ws_root = os.environ.get("IVY_WORKSPACE_ROOT", "").strip() or os.getcwd()
    ws_hash = workspace_hash(ws_root)
    session_file = Path("/tmp") / f"ivy-session-{ws_hash}.id"
    try:
        value = session_file.read_text().strip()
        if value:
            return value
    except OSError:
        pass
    return (raw_session_id or "unknown").strip() or "unknown"
```

- [ ] **Step 4: Run a quick test**

```bash
echo '{"session_id":""}' | CLAUDE_SESSION_ID="test-123" python3 $PLUGIN/hooks/scripts/observability/obs_session_start.py
```

Verify the event lands in `.observability/sessions/test-123/` (not `unknown/`).

- [ ] **Step 5: Commit**

```bash
cd $PLUGIN && git add hooks/scripts/observability/log_event.py
git commit -m "fix(observability): check CLAUDE_SESSION_ID in hook session ID resolution"
```

---

## Task 3: Add staging_health fallback to ivy_capabilities (Issue #3)

**Files:**
- Modify: `$IVY_LSP/ivy_lsp/mcp/tools/analysis.py` (lines 278-285)
- Test: `$IVY_LSP/tests/test_mcp_output_quality.py` (or nearby test file)

- [ ] **Step 1: Write the failing test**

Add a test in `$IVY_LSP/tests/` that verifies `ivy_capabilities` returns `staging_health` even when `ctx.include_resolver is None`:

```python
# In an appropriate test file
async def test_ivy_capabilities_staging_health_fallback(mock_ctx_no_resolver):
    """staging_health should fall back to workspace config when resolver is None."""
    result = await ivy_capabilities()
    assert "staging_health" in result
    assert result["staging_health"]["source"] == "workspace_config_fallback"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd $IVY_LSP && python -m pytest tests/test_mcp_output_quality.py -k "staging_health_fallback" -v
```

Expected: FAIL — staging_health not in result.

- [ ] **Step 3: Implement the fallback**

Edit `$IVY_LSP/ivy_lsp/mcp/tools/analysis.py`. After line 284 (`pass  # staging health is optional`), add:

```python
        if "staging_health" not in result and ctx.workspace_context is not None:
            ws_cfg = getattr(ctx.workspace_context, "workspace_config", None)
            layers = getattr(ws_cfg, "workspace_layers", None) if ws_cfg else None
            if layers is None:
                # Try ProtocolIndex-level layer info
                layers = []
                for _proto, idx in ctx.workspace_context.protocol_indexes.items():
                    manifest = getattr(idx, "manifest", {})
                    ws_layers = manifest.get("workspace_layers", [])
                    if ws_layers:
                        layers = ws_layers
                        break
            result["staging_health"] = {
                "layers_active": bool(layers),
                "layer_count": len(layers) if layers else 0,
                "total_staged": 0,
                "files_mapped_to_layers": 0,
                "source": "workspace_config_fallback",
            }
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd $IVY_LSP && python -m pytest tests/test_mcp_output_quality.py -k "staging_health_fallback" -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
cd $IVY_LSP && git add ivy_lsp/mcp/tools/analysis.py tests/test_mcp_output_quality.py
git commit -m "fix(ivy_capabilities): add staging_health fallback from workspace config"
```

---

## Task 4: Workspace-scoped tier 1/2 analysis (Issue #6, Part A)

**Files:**
- Modify: `$IVY_LSP/ivy_lsp/lsp/bulk_orchestrator.py` (around line 265-286)

- [ ] **Step 1: Write the failing test**

```python
# In tests/test_bulk_orchestrator.py or similar
def test_bulk_analysis_filters_to_active_workspace(mock_server):
    """When workspace is active, only files in active layers are analyzed."""
    mock_server._workspace_context = MockWorkspaceContext(
        active_layers={"quic", "quic_tests"},
        layer_paths={"quic": ["protocol-testing/quic/quic_stack"], "quic_tests": ["protocol-testing/quic/quic_tests"]},
    )
    all_files = [
        "/ws/protocol-testing/quic/quic_stack/quic_types.ivy",
        "/ws/protocol-testing/quic/quic_tests/server_tests/test.ivy",
        "/ws/protocol-testing/minip/minip_stack/types.ivy",  # Should be excluded
    ]
    filtered = mock_server._filter_files_to_workspace(all_files)
    assert len(filtered) == 2
    assert "/ws/protocol-testing/minip/minip_stack/types.ivy" not in filtered
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd $IVY_LSP && python -m pytest tests/test_bulk_orchestrator.py -k "filters_to_active_workspace" -v
```

Expected: FAIL — `_filter_files_to_workspace` not defined.

- [ ] **Step 3: Add workspace filter method to BulkOrchestrationMixin**

Edit `$IVY_LSP/ivy_lsp/lsp/bulk_orchestrator.py`. Add method to `BulkOrchestrationMixin`:

```python
def _filter_files_to_workspace(self, all_files: list[str]) -> list[str]:
    """Filter file list to only files within active workspace layers.

    If no workspace is active or no layer paths are configured,
    returns all files unchanged.
    """
    ws = getattr(self, "_workspace_state", None)
    if ws is None or not getattr(ws, "active_layers", None):
        return all_files

    resolver = self._indexer.resolver if self._indexer else None
    if resolver is None or not hasattr(resolver, "_active_layers"):
        return all_files

    active = resolver._active_layers
    if not active:
        return all_files

    file_to_layer = getattr(resolver, "_file_to_layer", {})
    if not file_to_layer:
        return all_files

    filtered = [f for f in all_files if file_to_layer.get(os.path.basename(f)) in active]
    if filtered:
        slog.info(
            "Workspace-scoped bulk analysis: %d/%d files (layers: %s)",
            len(filtered), len(all_files), sorted(active),
            extra={"event": LogEvent(LogCategory.DIAGNOSTIC, "bulk_workspace_filter")},
        )
        return filtered
    # Fallback: if filtering produced empty set, use all files
    return all_files
```

- [ ] **Step 4: Wire the filter into _run_background_analysis**

In `bulk_orchestrator.py`, around line 269 where `all_files = self._indexer.get_all_ivy_file_paths()`, add the filter:

```python
        all_files = self._indexer.get_all_ivy_file_paths()
        all_files = self._filter_files_to_workspace(all_files)  # <-- ADD THIS LINE
        if not all_files:
            return
```

- [ ] **Step 5: Run test to verify it passes**

```bash
cd $IVY_LSP && python -m pytest tests/test_bulk_orchestrator.py -k "filters_to_active_workspace" -v
```

Expected: PASS

- [ ] **Step 6: Commit**

```bash
cd $IVY_LSP && git add ivy_lsp/lsp/bulk_orchestrator.py tests/test_bulk_orchestrator.py
git commit -m "feat(bulk): scope tier 1/2 analysis to active workspace layers"
```

---

## Task 5: Load cached semantic model from offline index (Issue #6, Part B)

**Files:**
- Modify: `$IVY_LSP/ivy_lsp/lsp/server_setup.py` (`_prepopulate_from_offline_index`, around line 480)
- Modify: `$IVY_LSP/ivy_lsp/lsp/bulk_orchestrator.py` (skip T1/T2 for pre-loaded files)

- [ ] **Step 1: Write the failing test**

```python
# In tests/test_offline_index.py or similar
def test_prepopulate_loads_semantic_model(mock_server, tmp_path):
    """Offline index prepopulation should load semantic_model.pickle.gz."""
    # Setup: create a fake .ivy-index with semantic_model.pickle.gz
    import gzip, pickle
    from ivy_lsp.core.semantic.model import SemanticModel
    model = SemanticModel()
    index_dir = tmp_path / "protocol-testing" / "quic" / ".ivy-index"
    index_dir.mkdir(parents=True)
    with gzip.open(index_dir / "semantic_model.pickle.gz", "wb") as f:
        pickle.dump(model, f)

    mock_server._prepopulate_from_offline_index(ws_ctx)
    assert mock_server._semantic_model is not None
    assert mock_server._semantic_model_from_cache is True
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd $IVY_LSP && python -m pytest tests/test_offline_index.py -k "loads_semantic_model" -v
```

Expected: FAIL — `_semantic_model_from_cache` not set.

- [ ] **Step 3: Add semantic model loading to _prepopulate_from_offline_index**

Edit `$IVY_LSP/ivy_lsp/lsp/server_setup.py`. After the requirement graph loading block (line 558-561) and before the log message (line 563), add:

```python
        # -- 5. Semantic model (optional pickle) ----------------------------
        # Merge per-protocol semantic models into the server's model.
        # This avoids running tier 1/2 analysis from scratch.
        loaded_model_files = 0
        for proto_name, proto_idx in ws_ctx.protocol_indexes.items():
            if proto_idx.semantic_model is not None:
                if self._semantic_model is None:
                    from ivy_lsp.core.semantic.model import SemanticModel
                    self._semantic_model = SemanticModel()
                try:
                    self._semantic_model.merge(proto_idx.semantic_model)
                    loaded_model_files += 1
                except Exception:
                    logger.debug(
                        "Skipping incompatible semantic model for %s",
                        proto_name,
                        exc_info=True,
                    )

        self._semantic_model_from_cache = loaded_model_files > 0
        if loaded_model_files > 0:
            slog.info(
                "Loaded cached semantic model from %d protocol(s)",
                loaded_model_files,
                extra={
                    "event": LogEvent(
                        LogCategory.MILESTONE,
                        "offline_semantic_model",
                        {"protocols_loaded": loaded_model_files},
                    )
                },
            )
```

- [ ] **Step 4: Skip tier 1/2 for cached files in bulk orchestrator**

Edit `$IVY_LSP/ivy_lsp/lsp/bulk_orchestrator.py`. In the `_run` closure (around line 279), add a check:

```python
        def _run():
            try:
                # If semantic model was loaded from cache, skip T1/T2
                # for files that haven't changed since the cache was built.
                if getattr(self, "_semantic_model_from_cache", False):
                    ws_ctx = getattr(self, "_workspace_context", None)
                    stale_files = set()
                    if ws_ctx is not None:
                        for proto_idx in ws_ctx.protocol_indexes.values():
                            if proto_idx.staleness.status != "fresh":
                                for f in proto_idx.staleness.changed_files_list:
                                    stale_files.add(f)
                    if stale_files:
                        all_files = [f for f in all_files if f in stale_files]
                        slog.info(
                            "Cached model loaded; re-analyzing %d stale files only",
                            len(all_files),
                            extra={"event": LogEvent(LogCategory.DIAGNOSTIC, "cached_t1t2_skip")},
                        )
                    else:
                        slog.info(
                            "Cached model loaded and fresh; skipping T1/T2 entirely",
                            extra={"event": LogEvent(LogCategory.MILESTONE, "cached_t1t2_skip")},
                        )
                        all_files = []

                if not all_files:
                    self._send_model_ready_notification()
                    return

                result = self._analysis_pipeline.run_bulk_t1_t2(
                    ...
```

- [ ] **Step 5: Run test to verify it passes**

```bash
cd $IVY_LSP && python -m pytest tests/test_offline_index.py -k "loads_semantic_model" -v
```

Expected: PASS

- [ ] **Step 6: Run the full test suite to ensure no regressions**

```bash
cd $IVY_LSP && python -m pytest tests/ -x -q --timeout=60 2>&1 | tail -20
```

Expected: All existing tests still pass.

- [ ] **Step 7: Commit**

```bash
cd $IVY_LSP && git add ivy_lsp/lsp/server_setup.py ivy_lsp/lsp/bulk_orchestrator.py tests/
git commit -m "feat(offline-index): load cached semantic model, skip T1/T2 for fresh files"
```

---

## Task 6: Sync panther-serena with upstream (Issue #2)

**Files:**
- Modify: `$SERENA/` (merge upstream)

- [ ] **Step 1: Fetch upstream and check merge feasibility**

```bash
cd $SERENA
git fetch upstream
git log --oneline HEAD..upstream/main | wc -l  # Count commits behind
git diff --stat HEAD..upstream/main | tail -5    # See scope of changes
```

- [ ] **Step 2: Create a merge branch and merge**

```bash
cd $SERENA
git checkout -b merge/upstream-sync
git merge upstream/main
```

If conflicts arise, resolve them. Ivy-specific files (IvyLanguageServer, ivy tests) are additive and should not conflict with upstream changes. Expected conflict areas:
- `pyproject.toml` (version numbers)
- `src/solidlsp/ls.py` (language list)

- [ ] **Step 3: Run Serena tests to verify merge is clean**

```bash
cd $SERENA && uv run poe test -m "python" 2>&1 | tail -20
```

Expected: Tests pass.

- [ ] **Step 4: Measure instruction length after merge**

```bash
cd $SERENA && python3 -c "
from serena.agent import SerenaAgent
from serena.config.context_mode import SerenaContext
ctx = SerenaContext.from_name('claude-code')
# Approximate: measure context prompt length
print(f'Context prompt: {len(ctx.prompt)} chars')
"
```

If the full system prompt (after PromptFactory assembly) is still > 2048 chars, note the delta for a follow-up compression task.

- [ ] **Step 5: Commit the merge**

```bash
cd $SERENA && git add -A && git commit -m "chore: sync with upstream oraios/serena ($(git log --oneline HEAD..upstream/main | wc -l | tr -d ' ') commits)"
```

- [ ] **Step 6: Update panther_ivy submodule pointer**

```bash
cd $(git rev-parse --show-toplevel)
git add panther/plugins/services/testers/panther_ivy
git commit -m "chore: update panther-serena submodule (upstream sync)"
```

---

## Task 7: Investigate MCP tool output visibility (Issue #1)

**Files:** None (investigation only)

- [ ] **Step 1: Test with context7 MCP tool**

Call `mcp__plugin_context7_context7__resolve-library-id` with `libraryName="react"`. Observe whether the output is visible in the terminal.

- [ ] **Step 2: Test with Mermaid Chart MCP tool**

Call `mcp__claude_ai_Mermaid_Chart__validate_and_render_mermaid_diagram` with a simple diagram. Observe rendering.

- [ ] **Step 3: Compare with ivy-tools output**

Call `mcp__plugin_panther-ivy-plugin_ivy-tools__ivy_capabilities`. Compare terminal rendering with Steps 1-2.

- [ ] **Step 4: Check Claude Code version and changelog**

```bash
claude --version
gh api repos/anthropics/claude-code/releases/latest --jq '.body' 2>/dev/null | head -50
```

Look for any mentions of MCP output display changes.

- [ ] **Step 5: Document findings**

Record whether:
- All MCP tools have the same display behavior (platform-wide change)
- Only ivy-tools is affected (plugin-specific issue)
- There's a setting to restore previous behavior

If confirmed as platform regression, note for filing at github.com/anthropics/claude-code/issues.

---

## Summary Verification

After all tasks:

1. Run `/nct-health` — should show trigger-first order, no stale PID warnings
2. Call `ivy_capabilities` — should include `staging_health` (even with fallback)
3. Check `.observability/sessions/` — should have named session dirs
4. Measure LSP startup time — should be < 10s for warm start with workspace
5. Check Serena instruction length — document post-merge size
