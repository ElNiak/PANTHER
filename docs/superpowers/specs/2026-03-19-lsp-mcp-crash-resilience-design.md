# LSP/MCP Crash Resilience & Bug Fixes

**Date**: 2026-03-19
**Branch**: `refactor/ivy-lsp-cleanup` (worktree: `lsp-to-claude`)
**Scope**: ivy-lsp submodule + panther-ivy-plugin submodule
**Approach**: Prioritized hybrid — crash prevention first, then resilience, then correctness

## Context

Analysis of conversation log (`2026-03-19-105122-*.txt`) and Claude Code debug log (`c8fe62ac-*.txt`) revealed 7 problem categories affecting the Ivy LSP + MCP integration. The LSP server crashed with SIGTERM (exit code 143) during an `nct-validate` run, causing all 14+ MCP tools to become unavailable. A separate JSONDecodeError crash was also observed. Cross-validation of MCP tools vs LSP operations showed only 40% agreement.

### Root Causes Identified

| ID | Problem | Severity | Root Cause |
|----|---------|----------|------------|
| P1 | LSP crash exit code 143 | Critical | Stale PID cleanup in `start-ivy-server.sh` sends SIGTERM to running server |
| P2 | Cascade: MCP tools "not found" after crash | Critical | No auto-reconnect; Claude Code deregisters tools when server dies |
| P3 | JSONDecodeError kills stdio LSP | High | pygls message loop crashes on malformed JSON instead of rejecting |
| P4 | 7-minute first-call latency | Medium | Lazy model build on first `ivy_coverage` call |
| P5 | 7 functional failures (nct-validate) | Medium | Various bugs in hover, workspaceSymbol, xref graph, definition, patterns |
| P6 | 40% cross-validation agreement | Medium | MCP tools and LSP operations return inconsistent results for same queries |
| P7 | "server is running" but can't send | Medium | stdio transport blocked; no request queuing |

### Evidence Timeline (from debug log)

```
09:32:18  MCP server connected (ivy-tools, version "ivy-lsp 1.26.0")
09:33:45  LSP server instance started
09:33:46  First MCP tool calls (ivy_capabilities, ivy_lint) — fast
09:33:46  First ivy_coverage call begins
09:40:42  First ivy_coverage completes — 6m 55s (lazy model build)
09:44:08  Subsequent ivy_coverage calls — 3ms-28ms (cached)
09:47:24  Last successful tool call (Bash PostToolUse hook)
09:47:43  LSP server crashed: exit code 143 (SIGTERM)
09:47:43  LSP server connection closed
09:48:26  ALL MCP tools become "Tool not found" (39+ errors in rapid succession)
```

---

## Phase 1: Crash Prevention

Targeted fixes to prevent the two observed crash modes. Smallest scope, highest impact.

### 1a. Fix PID cleanup race in `start-ivy-server.sh`

**File**: `panther-ivy-plugin/.../scripts/start-ivy-server.sh` (lines 70-98)

**Current behavior**: The script kills any running server with the same `${MODE}-${_WS_HASH}` prefix. When a concurrent Claude session (or subagent) for the same workspace triggers a new server launch, the stale cleanup (line 86: `kill -TERM "$old_pid"`) kills the other session's live server mid-operation. The existing guard `[ "$old_pid" = "$$" ] && continue` (line 83) only prevents self-kill, not cross-session kill.

**Failure sequence**: Session A starts → launches LSP (PID 100). Session B starts (same workspace) → cleanup finds PID 100 under `lsp-<hash>` → kills it → Session A's LSP dies with exit code 143.

**Fix**: Add session scoping to PID prefix using `$PPID` (parent process ID):

```bash
# Session-scoped PID prefix: avoids cross-session kills
# $PPID is the Claude Code process that launched this script.
# NOTE: CLAUDE_SESSION_ID does not exist as an env var today;
# $PPID is the actual mechanism. If Claude launches through
# intermediate shells, $PPID may be unreliable — but this still
# reduces the race window vs. the current approach.
_SESSION_ID="${PPID}"
_PID_PREFIX="${MODE}-${_WS_HASH}-${_SESSION_ID}"
```

Only kill PIDs from the same parent session. The dead-PID cleanup (lines 91-98) stays unchanged and handles stale leftovers from any session.

**Validation**: Launch two concurrent Claude sessions in the same workspace; verify neither kills the other's server.

### 1b. Add SIGTERM/SIGINT signal handlers

**File**: `ivy-lsp/ivy_lsp/__main__.py`

**Current behavior**: No signal handlers. SIGTERM causes immediate process death — no log flush, no staging cleanup, no audit summary.

**Fix**: Install signal handlers before starting either server mode:

```python
import signal

def _graceful_shutdown(signum, frame):
    log.info("Received signal %d, shutting down gracefully", signum)
    raise SystemExit(128 + signum)

signal.signal(signal.SIGTERM, _graceful_shutdown)
signal.signal(signal.SIGINT, _graceful_shutdown)
```

This converts SIGTERM into `SystemExit`, which Python's `try/finally` and `atexit` handlers can catch. The existing `on_shutdown` handler in `server.py` and cleanup logic in `mcp_server.py` then execute normally.

**Risk — asyncio interaction**: For MCP mode (which runs under `mcp.run(transport="stdio")`, an asyncio event loop), raising `SystemExit` from a signal handler while inside an asyncio event loop may not allow `atexit` handlers to run if the loop is blocked. For the MCP path, use `loop.add_signal_handler()` instead of raw `signal.signal()`:

```python
# For MCP (asyncio) path:
loop = asyncio.get_event_loop()
loop.add_signal_handler(signal.SIGTERM, lambda: sys.exit(128 + signal.SIGTERM))
```

**Validation**: Send SIGTERM to running server; verify log file contains shutdown audit summary.

### 1c. Graceful JSON-RPC error handling

**File**: `ivy-lsp/ivy_lsp/pygls_patches.py` (add new patch alongside existing `_patch_pygls_cancelled_future` and `_patch_pygls_closed_pipe`)

**Current behavior**: `json.decoder.JSONDecodeError` in pygls message loop crashes the entire LSP server. The existing `_fixed_params_hook` in `__main__.py` handles missing `params` (cattrs converter) but not malformed JSON at the transport layer.

**Implementation note**: pygls 2.0.x does NOT expose `data_received` on `JsonRPCProtocol`. The JSON deserialization happens inside pygls internals before `_handle_request` / `_handle_notification` are called. The exact entry point must be identified by tracing the pygls source for the message-parsing layer (likely in the `JsonRPCProtocol._procedure_handler` or the transport's message framing). The existing `pygls_patches.py` already patches `_handle_response` and `set_writer` on `JsonRPCProtocol`, establishing the pattern.

**Fix approach** (requires sub-investigation of pygls internals):

1. Identify the pygls method that deserializes incoming JSON-RPC messages (the step before `_handle_request`)
2. Add a new patch function in `pygls_patches.py` that wraps this method
3. Catch `json.JSONDecodeError` and `cattrs.errors.ClassValidationError`, log at ERROR level, and return (skip the malformed message)
4. Register the patch in `apply_patches()` alongside the existing patches

```python
def _patch_pygls_json_safety() -> None:
    """Wrap pygls message deserialization to survive malformed JSON.

    The exact method to patch depends on pygls 2.0.x internals.
    Candidate: the method that calls json.loads() on incoming data,
    typically in the transport layer or JsonRPCProtocol._procedure_handler.
    """
    from pygls.protocol.json_rpc import JsonRPCProtocol

    # TODO: Identify exact method via pygls source inspection.
    # Pattern: wrap with try/except json.JSONDecodeError, log, continue.
    ...
```

**Validation**: Send malformed JSON to server stdin; verify server logs error and continues responding to subsequent valid requests.

---

## Phase 2: Resilience

Architectural improvements so the system degrades gracefully instead of catastrophically.

### 2a. Eager model pre-warming on MCP startup

**File**: `ivy-lsp/ivy_lsp/mcp_server.py` (inside `start_mcp()`, after tool registration)

**Current behavior**: Semantic model built lazily on first tool call (`_get_model()` at line 471). First `ivy_coverage` takes 6m 55s.

**Fix**: Start model building as a background task. Since `mcp.run(transport="stdio")` starts the asyncio event loop, `asyncio.get_event_loop().create_task()` can't be called before `mcp.run()`. Instead, use FastMCP's lifecycle hooks or schedule the task inside the first tool call, or use a `startup` event:

```python
# Option A: Use FastMCP's lifespan/startup hook if available
@mcp.on_event("startup")
async def _prewarm():
    try:
        await _get_model()
        logger.info("Semantic model pre-warmed successfully")
    except Exception:
        logger.warning("Model pre-warm failed; will retry on first tool call", exc_info=True)

# Option B: If FastMCP doesn't support lifecycle hooks,
# add a lightweight wrapper around mcp.run():
async def _run_with_prewarm():
    asyncio.create_task(_prewarm())
    await mcp._run_stdio()  # internal method — check FastMCP API
```

The exact approach depends on FastMCP's lifecycle API — requires sub-investigation during implementation.

Add `model_status` field to `ivy_capabilities` response: `"building"` / `"ready"` / `"failed"`.

**Validation**: Start MCP server; call `ivy_capabilities` immediately — should show `"model_status": "building"`. Wait, call again — should show `"ready"`.

### 2b. Request queuing limitation (document only)

**Problem**: "Cannot send request to LSP server: server is running" — the Claude Code LSP client doesn't queue requests when the stdio transport is busy.

**Status**: This is a **Claude Code client-side limitation**, not fixable server-side. The server already uses `@self.thread()` for heavy operations.

**Mitigation**: Document in plugin CLAUDE.md that LSP operations may fail with "server is running" when the server is processing a heavy request. Recommend retrying after a short delay. Consider adding a retry wrapper in the plugin's hooks if this is frequent.

### 2c. Staging directory cleanup on SIGTERM

**File**: `ivy-lsp/ivy_lsp/mcp_server.py` (inside `start_mcp()`)

**Current behavior**: Staging directory (with flat symlinks) is not cleaned up on SIGTERM.

**Fix**: Register atexit cleanup after staging directory creation:

```python
import atexit, shutil
if staging_dir:
    atexit.register(lambda sd=staging_dir: shutil.rmtree(sd, ignore_errors=True))
```

Phase 1's signal handler (1b) ensures atexit runs on SIGTERM.

**Validation**: Start server, verify staging dir exists, send SIGTERM, verify staging dir is cleaned up.

### 2d. Bidirectional model cache

**File**: `ivy-lsp/ivy_lsp/mcp_server.py` (inside `_get_model()`, after successful build)

**Current behavior**: LSP server writes semantic model cache to disk after bulk analysis. MCP server reads it. But MCP never writes its own builds to the cache.

**Fix**: After MCP's own model build succeeds, write to the shared cache location. The `write_model_cache` signature requires 4 parameters including a freshness key (see `bulk_orchestrator.py:80` for reference):

```python
from ivy_lsp.indexer.shared_cache import compute_freshness_key, write_model_cache

ivy_files = _find_ivy_files(root)
freshness = compute_freshness_key(root, ivy_files)
write_model_cache(root, semantic_model, _req_graph, freshness)
```

This way, if MCP crashes and restarts, the next instance gets a warm cache instead of rebuilding for 7 minutes.

**Validation**: Start MCP, wait for model build, kill server, restart — second startup should show "Loaded semantic model from shared cache" in logs.

---

## Phase 3: Functional Correctness

Six independent bug fixes. Lower priority — edge cases, not core stability.

**Sub-investigation required**: Each fix below requires reading the specific handler code to confirm the exact root cause before implementation. The symptom descriptions are from nct-validate observations; the proposed fixes are hypotheses that may need adjustment once the actual code is inspected. Budget investigation time per item.

### 3a. Hover file attribution

**Files**: `ivy-lsp/ivy_lsp/features/hover.py`

**Symptom**: Hover for `cid` says "Defined in: ping_types.ivy" but actual definition is `quic_types.ivy:30`.

**Fix**: When multiple files define the same symbol, prefer the file in the current document's include closure over alphabetical first match.

### 3b. workspaceSymbol query handling

**Files**: `ivy-lsp/ivy_lsp/features/workspace_symbols.py`

**Symptom**: workspaceSymbol returns 100 unrelated symbols from `apt_entities/` instead of results for `cid`.

**Note**: LSP `workspace/symbol` is a **query-based** request — the client sends a query string, not a cursor position. The word-at-cursor extraction must happen **client-side** (Claude Code LSP adapter). The server receives `params.query` and does substring matching.

**Fix**: Investigate whether the issue is:
- **Client-side** (Claude Code sends empty/wrong query) — if so, this is out of scope for ivy-lsp
- **Server-side** (handler ignores `params.query` or returns truncated/unsorted results) — if so, fix the query matching and result ordering to prioritize exact matches

### 3c. Semantic model xref graph for module-scoped types

**Files**: `ivy-lsp/ivy_lsp/semantic/model.py` or `semantic/cross_refs.py`

**Symptom**: The semantic model's impact traversal returns 0 cross-reference edges for `quic_packet_type` while LSP `findReferences` (which uses the lexical index) returns 406 refs. Note: the `ivy_query` MCP tool has been removed — the underlying semantic model's impact/xref graph is what needs fixing, as it's used by `ivy_coverage` and visualization tools.

**Fix**: Extend xref graph edge-building to include `object`/`module` declarations, not just `action`/`function`.

### 3d. goToDefinition for inner enum classes

**Files**: `ivy-lsp/ivy_lsp/features/definition.py`

**Symptom**: goToDefinition at line 130 (inner enum body) returns nothing; line 129 (outer module) works.

**Fix**: When no definition found at exact position, walk up to nearest enclosing `object`/`module` declaration.

### 3e. Pattern name normalization

**Files**: `ivy-lsp/ivy_lsp/tools/patterns.py`

**Symptom**: `ivy_pattern_scaffold(pattern="monitor")` fails — requires exact plural "monitors".

**Fix**: Add singular→plural normalization map: `{"monitor": "monitors", "variant": "variants", "shim": "shim", ...}`.

### 3f. ivy_model_info for library files

**Files**: `ivy-lsp/ivy_lsp/tools/verification.py`

**Symptom**: `ivy_model_info(quic_types.ivy)` errors with "no isolate specified" for library modules.

**Fix**: Detect no-isolate files and fall back to structural analysis or auto-detect the isolate from module structure.

---

## Out of Scope

- Claude Code client-side LSP request queuing (P7 — framework limitation)
- Claude Code MCP server auto-reconnect after crash (P2 — framework behavior)
- Performance optimization of semantic model building beyond pre-warming
- Changes to the nct-validate ground truth spec

## Testing Strategy

- **Phase 1**: Manual testing — send SIGTERM, send malformed JSON, launch concurrent sessions
- **Phase 2**: Integration testing — verify model pre-warming via `ivy_capabilities`, verify cache round-trip
- **Phase 3**: Unit tests per handler + re-run `/nct-validate` to confirm fixes

## Phasing

| Phase | Items | PRs | Risk |
|-------|-------|-----|------|
| 1 | 1a, 1b, 1c | 1 PR into ivy-lsp + 1 PR into panther-ivy-plugin | Low — targeted fixes |
| 2 | 2a, 2b (docs only), 2c, 2d | 1 PR into ivy-lsp (2b is CLAUDE.md update only) | Medium — touches startup path |
| 3 | 3a–3f (each needs sub-investigation) | 1 PR into ivy-lsp | Low — independent fixes |
