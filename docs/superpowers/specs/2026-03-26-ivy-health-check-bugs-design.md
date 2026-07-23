# Ivy LSP + MCP Health Check Bug Fixes

**Date:** 2026-03-26
**Scope:** 4 bugs + 1 hardening fix across 5 files in ivy-lsp submodule
**Approach:** Targeted surgical fixes (Approach C)

## Context

A 21-step health check of the Ivy LSP + MCP stack revealed 14 failures. Root cause analysis identified 4 distinct bugs and 1 hardening opportunity. All bugs are in the ivy-lsp submodule at `panther/plugins/services/testers/panther_ivy/submodules/ivy-lsp/`.

## Bug 1: MCP Semaphore Deadlock

**Root cause:** The `safe_tool` decorator in `ivy_lsp/mcp/tools/__init__.py` acquires a concurrency semaphore at line 418 with `async with sem:` — no acquisition timeout. If all slots fill up (from hung/timed-out tasks that don't release cleanly), subsequent tool calls block forever, cascading into full MCP server unavailability.

**Secondary:** `TieredExtractor().probe_tiers()` in `ivy_capabilities` (analysis.py:273) has no internal timeout and can hang on parser imports.

**Tertiary:** Circuit breaker state at `/tmp/ivy-mcp-health-state.json` persists across MCP server restarts, carrying old failure counts into new sessions.

### Fix 1a: Semaphore acquisition timeout

**File:** `ivy_lsp/mcp/tools/__init__.py`, line 418

Replace bare `async with sem:` with timed acquisition using `asyncio.wait_for()` at 50% of tool timeout. On timeout, return an error result indicating concurrency slot exhaustion. Use explicit `sem.acquire()`/`sem.release()` in try/finally to guarantee cleanup.

### Fix 1b: Per-tier timeout in probe_tiers()

**File:** `ivy_lsp/mcp/tools/analysis.py`, line 273

Wrap `TieredExtractor().probe_tiers()` in `asyncio.wait_for()` with a 3-second timeout via `run_in_executor`. On timeout, return `{"error": "probe timed out (3s)"}` instead of hanging.

### Fix 1c: Circuit breaker reset on startup

**Location:** MCP server startup path

On MCP server init, check `/tmp/ivy-mcp-health-state.json`. If the file exists and is older than 60 seconds, reset `consecutive_failures` to 0. This prevents inheriting stale failure counts from previous sessions.

## Bug 2: workspaceSymbol Returns Wrong Files

**Root cause:** Three compounding issues:
1. `find_all_ivy_files()` indexes the entire workspace root (patterns/, attacks_stack/, etc.)
2. `compute_workspace_symbols()` only filters by active workspace layers when `active_workspace.is_set()` is True — with no workspace active, all files pass through
3. 100-result cap truncates quic_types.ivy symbols because unrelated files (attack_connection.ivy with 48 symbols) appear first in the flat list

### Fix: Protocol-scoped filtering using active_filepath

**File:** `ivy_lsp/lsp/workspace_symbols.py`, after line 190

When no workspace is active but `active_filepath` is provided, derive the protocol root directory from the filepath (e.g., `protocol-testing/quic/`) and filter the flat symbol list to files under that protocol tree.

New helper `_derive_protocol_root(filepath)` extracts the protocol directory by finding the `protocol-testing/<protocol>/` segment in the path.

No changes to `search_symbols()` or `MAX_RESULTS` — the cap works correctly once the input list is properly scoped.

## Bug 3: documentSymbol Shows "Indexing" When LSP Is Ready

**Root cause:** `document_symbols.py` line 211 checks `server.initializing` which reflects LSP protocol initialization state (cleared in `on_initialized` finally block at server.py:451), not actual indexer readiness. Other operations (hover, goToDefinition, findReferences) don't check this flag and work fine during late init because the indexer is already functional.

### Fix: Check indexer data readiness instead of protocol flag

**File:** `ivy_lsp/lsp/document_symbols.py`, lines 210-214

Replace the `server.initializing` check with a direct check on whether the indexer's symbol table has content (`len(indexer._symbol_table._all) > 0`). Show the "indexing in progress" placeholder only when both the parser is unavailable AND the indexer has no data yet.

## Bug 4: Workspace State Cleared Mid-Session

**Root cause:** `_handle_get()` in `workspace.py` reads from `ctx.active_workspace` (in-memory MCP state). If the MCP server restarted or the context was reloaded, this in-memory state is `None` — and the function returns `ActiveWorkspace.cleared()` without checking the persisted state file.

The RF-5 tiebreak logic in `load_active_workspace()` correctly preserves explicit state. The bug is that `_handle_get()` doesn't fall back to the persisted state.

### Fix: Fall back to persisted state file

**File:** `ivy_lsp/mcp/tools/workspace.py`, lines 138-144

When `ctx.active_workspace` is `None`, attempt to load from `.ivy-workspace-state.json` before returning cleared. If the persisted state has `is_set()`, restore it to `ctx.active_workspace` for future calls too.

Design decision: `set_by="explicit"` is immutable — never overridden by marker re-detection (user chose option A).

## Files Modified

| File | Bug | Change |
|------|-----|--------|
| `ivy_lsp/mcp/tools/__init__.py` | 1a | Semaphore acquisition timeout (~10 lines) |
| `ivy_lsp/mcp/tools/analysis.py` | 1b | probe_tiers() timeout (~5 lines) |
| `ivy_lsp/mcp/server.py` (`start_mcp()`) | 1c | Circuit breaker reset (~8 lines) |
| `ivy_lsp/lsp/workspace_symbols.py` | 2 | Protocol-scoped filtering + helper (~25 lines) |
| `ivy_lsp/lsp/document_symbols.py` | 3 | Indexer readiness check (~3 lines) |
| `ivy_lsp/mcp/tools/workspace.py` | 4 | Persisted state fallback (~8 lines) |

## Testing Strategy

Each fix is independently verifiable:

- **Bug 1:** Health check should complete all 21 steps without MCP disconnection. `ivy_capabilities` should return within 10s even with parser issues.
- **Bug 2:** `workspaceSymbol` with `active_filepath` pointing to a quic file should return quic symbols only, not patterns/ or attacks_stack/.
- **Bug 3:** `documentSymbol` should return actual symbols (not "indexing" placeholder) when the indexer has data, even during late LSP init.
- **Bug 4:** `ivy_workspace(action="get")` should return the persisted workspace state, not `null`, after MCP server restart.

Re-run `/nct-health` after all fixes to verify all 21 checks pass.

## Out of Scope

- Stale PID file cleanup (cosmetic, no functional impact)
- Refactoring `safe_tool` decorator architecture
- Changes to circuit breaker hook script itself
