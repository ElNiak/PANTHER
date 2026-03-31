# LSP + MCP Health, Observability & Performance Fixes

**Date**: 2026-03-31
**Branch**: `refactor/ivy-lsp-cleanup` (worktree: `lsp-to-claude`)
**Scope**: 6 issues across panther-ivy-plugin, ivy-lsp, and panther-serena submodules

## Summary

Fix 6 issues discovered during an nct-health check session: rework the health check order, expose staging_health in MCP, cache tier 1/2 analysis, fix observability session IDs, sync upstream Serena, and investigate MCP output visibility.

## Issues

| # | Issue | Submodule | Severity |
|---|-------|-----------|----------|
| 1 | MCP tool output not visible on stdout | Claude Code platform | Medium |
| 2 | Serena instructions truncated (7650 → 2048 chars) | panther-serena | Medium |
| 3 | staging_health missing from ivy_capabilities | ivy-lsp | Low |
| 4 | Observability session ID → "unknown" | panther-ivy-plugin | Medium |
| 5 | nct-health check order is backwards | panther-ivy-plugin | Medium |
| 6 | Tier 1/2 recomputation despite offline index | ivy-lsp | High |

## Workstream A: Plugin Submodule Fixes

### Issue #5 — nct-health rework (trigger-first order)

**File**: `panther-ivy-plugin/plugins/panther-ivy-plugin/commands/nct-health.md`

**Problem**: Current order checks PID files and log freshness (Steps 1-2) before any MCP/LSP call. These artifacts are stale until the server is triggered. This always produces WARN for stale PIDs on fresh sessions.

**Design**: Reorder into 3 phases:

```
Phase 1 — Trigger (force server start)
  Step 1: MCP ivy_capabilities  (was Step 4)
  Step 2: LSP documentSymbol    (was Step 3)

Phase 2 — Validate infrastructure (now fresh)
  Step 3: PID files             (was Step 1)
  Step 4: Log health            (was Step 2)
  Step 5: Layer staging          (was Step 8, uses Step 1 data)

Phase 3 — Deep functional checks
  Step 6: Workspace access       (was Step 5)
  Step 7: Coverage pipeline      (was Step 6)
  Step 8: Cross-file resolution  (was Step 7)
  Step 9: Cross-layer resolution (was Step 9)
```

**Early exit**: If Phase 1 fails (both MCP and LSP unreachable), skip Phases 2-3 and report "Server unreachable — check installation and PATH."

**Step 5 change**: staging_health is now extracted from the ivy_capabilities result obtained in Step 1 (no separate call needed). Fallback to .ivyworkspace parsing only if staging_health is absent from capabilities.

**Step 3 change**: Use `ps -p <pid>` instead of `kill -0` per project convention. The current nct-health skill uses `kill -0` which is not allowed in sandboxed environments and contradicts the established project convention.

### Issue #3 — staging_health missing from ivy_capabilities

**File**: `ivy-lsp/ivy_lsp/mcp/tools/analysis.py` (lines 278-284)

**Problem**: `ctx.include_resolver` is `None` in the MCP process when the indexer hasn't built layer staging yet. The guard `if ctx.include_resolver is not None` silently skips staging_health.

**Root cause**: The MCP context is created via `MCPContext.from_lsp_server(server)` which reads `server._indexer.resolver`. If the MCP server's internal LSP hasn't completed indexing (or if layer staging wasn't triggered), the resolver is None.

**Fix**: Add a fallback that reads `.ivyworkspace` config directly:

```python
# In ivy_capabilities(), after the existing staging_health block:
if "staging_health" not in result and ctx.workspace_context is not None:
    ws_cfg = ctx.workspace_context.workspace_config
    layers = getattr(ws_cfg, "workspace_layers", None) or []
    result["staging_health"] = {
        "layers_active": bool(layers),
        "layer_count": len(layers),
        "total_staged": 0,  # unknown without resolver
        "files_mapped_to_layers": 0,
        "source": "workspace_config_fallback",
    }
```

This ensures `ivy_capabilities` always reports layer configuration, even before staging is built.

### Issue #6 — Tier 1/2 recomputation (cache + workspace scoping)

**Files**:
- `ivy-lsp/ivy_lsp/lsp/server_setup.py` (prepopulation)
- `ivy-lsp/ivy_lsp/lsp/bulk_orchestrator.py` (tier 1/2 dispatch)
- `ivy-lsp/ivy_lsp/core/workspace/context.py` (index loading)

**Problem**: After offline index prepopulation (651 files, 209k symbols, 9k edges in ~3.4s), the LSP runs tier 1 (annotation extraction) and tier 2 (dependency graph building) on ALL files across ALL 7 protocols. This takes 3+ minutes even though `semantic_model.pickle.gz` (113MB) and `requirement_graph.pickle.gz` (40KB) already exist in `.ivy-index/`.

**Part B — Cache loading**: Extend `_prepopulate_from_offline_index()` in `server_setup.py`:

1. Load `semantic_model.pickle.gz` from `.ivy-index/` if present and not stale
2. Load `requirement_graph.pickle.gz` from `.ivy-index/` if present and not stale
3. Mark files as "tier1_complete" and "tier2_complete" in the indexer state
4. Staleness check: compare `manifest.json` mtime against each source file's mtime. If source is newer than manifest, mark that file for re-analysis.

**Part A — Workspace scoping**: Modify `bulk_orchestrator.py`:

1. Before dispatching tier 1/2, check if a workspace is active via `server._workspace_context`
2. If active, filter the file list to only files within active layer `include_paths`
3. Files outside the active workspace are skipped (their cached tier 1/2 data from the offline index is sufficient)
4. If no workspace is active, analyze all files (current behavior)

**Expected improvement**: With quic workspace active (~200 files instead of 651) AND cached tier 1/2, startup should go from ~3+ minutes to <10 seconds for warm starts.

**Staleness edge case**: If a file is modified after the offline index was built, its tier 1/2 must be recomputed. The staleness check in the manifest already tracks per-file mtimes — extend this to also invalidate tier 1/2 cache entries.

**Cache write**: After tier 1/2 completes, update `semantic_model.pickle.gz` and `requirement_graph.pickle.gz` in `.ivy-index/`. This uses the existing `ivy_index` MCP tool's serialization path. Add a `--update-cache` flag or auto-save on clean shutdown.

### Issue #4 — Observability session ID propagation

**File**: `panther-ivy-plugin/plugins/panther-ivy-plugin/hooks/scripts/observability/obs_session_start.py`

**Problem**: The hook writes to `.observability/sessions/<session_id>/` but the session ID resolves to `"unknown"` because `IVY_SESSION_ID` isn't set when hooks run. The server launcher scripts (`start-ivy-server.sh`, `start-serena.sh`) propagate `CLAUDE_SESSION_ID → IVY_SESSION_ID`, but hooks execute independently of those scripts.

**Fix**: In `obs_session_start.py` (and other obs hooks), read `CLAUDE_SESSION_ID` directly:

```python
session_id = (
    os.environ.get("IVY_SESSION_ID")
    or os.environ.get("CLAUDE_SESSION_ID")
    or os.environ.get("CLAUDE_CODE_SESSION_ID")
    or "unknown"
)
```

Also check: does Claude Code actually set `CLAUDE_SESSION_ID` in the hook execution environment? If not, extract the session ID from the debug log path or conversation metadata. The current debug log path includes the session UUID: `2480a25f-b740-461c-9f5c-1bec9903b1d1`.

**Secondary fix**: Ensure all obs hooks use the same session ID resolution. Extract to a shared helper:

```python
# hooks/scripts/observability/_session.py
def get_session_id() -> str:
    for var in ("IVY_SESSION_ID", "CLAUDE_SESSION_ID", "CLAUDE_CODE_SESSION_ID"):
        val = os.environ.get(var)
        if val:
            return val
    return "unknown"
```

## Workstream B: Platform Investigation

### Issue #2 — Serena instruction truncation

**Submodule**: panther-serena

**Step 1 — Sync with upstream**: panther-serena fork is 100+ commits behind oraios/serena. Upstream changes include prompt factory improvements, new language support, security patches, and MCP protocol upgrades (1.26).

```bash
cd panther/plugins/services/testers/panther_ivy/submodules/panther-serena
git fetch upstream
git merge upstream/main
# Resolve conflicts (Ivy-specific files won't conflict with upstream)
```

**Step 2 — Measure**: After sync, measure the new instruction size. Start the Serena MCP server and check the system prompt length.

**Step 3 — Compress if needed**: If still > 2048 chars after sync:
- Trim the `claude-code` context prompt (currently ~300 chars, unlikely to help much)
- Customize the PromptFactory to omit verbose tool listing from the MCP instructions (since Claude Code already has tool schemas via MCP protocol)
- Move the "how to use Serena" guidance to the plugin CLAUDE.md (already has detailed Serena guidance)

### Issue #1 — MCP tool output visibility

**Investigation plan**:

1. Check if the display issue is specific to ivy-tools or affects all MCP servers:
   - Call `mcp__plugin_context7_context7__resolve-library-id` and observe terminal rendering
   - Call `mcp__claude_ai_Mermaid_Chart__validate_and_render_mermaid_diagram` and observe
   - Compare with ivy-tools tool output rendering

2. Check Claude Code 2.1.88 changelog for display changes:
   - `gh release view` or check github.com/anthropics/claude-code releases

3. Check settings that might affect output rendering:
   - `MAX_MCP_OUTPUT_TOKENS` (default 25,000 — not set in user config)
   - Any display/verbosity settings in `settings.json`

4. If confirmed as platform regression: file issue at github.com/anthropics/claude-code/issues with reproduction steps.

## Implementation Order

1. **Issue #5** (nct-health rework) — standalone, no dependencies
2. **Issue #4** (observability session ID) — standalone, quick fix
3. **Issue #3** (staging_health fallback) — small change in ivy-lsp
4. **Issue #6** (tier 1/2 cache + scoping) — largest change, depends on understanding ivy-lsp internals
5. **Issue #2** (Serena sync + compress) — sync first, then evaluate
6. **Issue #1** (MCP stdout investigation) — investigation, no code changes expected

Issues 1-3 can be parallelized. Issue 6 is the critical path.

## Testing

- **Issue #5**: Run `/nct-health` after changes, verify no stale PID warnings on fresh session
- **Issue #3**: Call `ivy_capabilities` before and after fix, verify `staging_health` is present
- **Issue #4**: Start a new Claude Code session, verify observability events land in a named session dir (not "unknown")
- **Issue #6**: Measure startup time before and after (target: <10s warm start with quic workspace)
- **Issue #2**: Measure Serena instruction length after sync, verify < 2048 or document delta
- **Issue #1**: Compare MCP output rendering across ivy-tools, context7, and Mermaid Chart

## Files Modified

| Submodule | File | Issue |
|-----------|------|-------|
| panther-ivy-plugin | `commands/nct-health.md` | #5 |
| panther-ivy-plugin | `hooks/scripts/observability/obs_session_start.py` | #4 |
| panther-ivy-plugin | `hooks/scripts/observability/_session.py` (new) | #4 |
| ivy-lsp | `ivy_lsp/mcp/tools/analysis.py` | #3 |
| ivy-lsp | `ivy_lsp/lsp/server_setup.py` | #6 |
| ivy-lsp | `ivy_lsp/lsp/bulk_orchestrator.py` | #6 |
| ivy-lsp | `ivy_lsp/core/workspace/context.py` | #6 |
| panther-serena | merge upstream + prompt compression | #2 |

## Risks

- **Issue #6 cache invalidation**: If staleness detection misses a modified file, tier 1/2 results could be stale, causing incorrect diagnostics. Mitigation: conservative staleness — any doubt triggers recomputation.
- **Issue #2 merge conflicts**: panther-serena has Ivy-specific additions that upstream doesn't have. Conflicts likely in `src/solidlsp/` (IvyLanguageServer) and test files. Mitigation: Ivy files are additive, shouldn't conflict with upstream refactors.
- **Issue #6 semantic model compatibility**: The `semantic_model.pickle.gz` format may change between ivy-lsp versions. Add a version marker to the pickle and skip loading if version mismatches.
