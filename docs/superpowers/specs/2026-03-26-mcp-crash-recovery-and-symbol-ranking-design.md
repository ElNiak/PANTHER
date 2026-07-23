# MCP Crash Recovery, PID Cleanup & Symbol Ranking — Fix Design

**Date**: 2026-03-26
**Branch**: `production` (worktree: `lsp-to-claude`)
**Scope**: 3 fixes across ivy-lsp submodule + panther-ivy-plugin

## Context

The `/nct-health` check reported 11 FAILs and 4 WARNs. Investigation revealed 4 distinct issues (3 actionable):

| Issue | Root Cause | Severity |
|---|---|---|
| A. MCP server crash | MCP SDK anyio cancel scope bug ([#577](https://github.com/modelcontextprotocol/python-sdk/issues/577) P1 OPEN) | Critical — kills all MCP tools |
| B. Stale PID files | SessionEnd cleanup doesn't run on crash; no SessionStart cleanup | Low — cosmetic |
| C. Layer staging unknown | Consequence of A (MCP down) | N/A — resolves with A |
| D. workspaceSymbol truncation | Empty query returns first 100 symbols in file order; auto-generated names dominate | Medium — degrades symbol search |

## Fix A: MCP Server Crash Recovery

### Problem

`mcp.run(transport="stdio")` crashes with `RuntimeError: Attempted to exit a cancel scope that isn't the current tasks's current cancel scope`. This is an architectural bug in the MCP SDK's `BaseSession`/`shared/session.py` — task groups are entered and exited across different async contexts, violating anyio's structured concurrency model. No version of mcp (through 1.26.0) or anyio (through 4.13.0) fixes it. The bug is widely reported across downstream projects.

### Solution: Two-part defense

**Part 1: Retry-loop wrapper** in `ivy_lsp/__main__.py`

Replace the single `start_mcp()` call (line ~305) with a retry loop that catches `BaseExceptionGroup` containing cancel-scope `RuntimeError`s and restarts up to 3 times. Non-cancel-scope errors still crash immediately.

Note: Python 3.10 requires `from exceptiongroup import BaseExceptionGroup` (backport, installed as anyio dependency). Python 3.11+ has it built-in. Use try/except import for compatibility.

```python
MAX_MCP_RESTARTS = 3
for attempt in range(1, MAX_MCP_RESTARTS + 1):
    try:
        start_mcp(...)
        break
    except BaseExceptionGroup as eg:
        cancel_scope_errors = [
            e for e in eg.exceptions
            if isinstance(e, (RuntimeError, BaseExceptionGroup))
            and "cancel scope" in str(e)
        ]
        if cancel_scope_errors and attempt < MAX_MCP_RESTARTS:
            log.warning("[MCP-RESTART] attempt %d/%d", attempt, MAX_MCP_RESTARTS)
            continue
        log.critical("[MCP-FATAL] %s", eg, exc_info=True)
        sys.exit(1)
    except Exception as e:
        log.critical("[MCP-FATAL] %s", e, exc_info=True)
        sys.exit(1)
```

**Part 2: Pin dependencies** in `pyproject.toml`

Add version floor to the `mcp` extra to ensure all partial cancel-scope fixes are included:
- `mcp>=1.26.0`
- `anyio>=4.13.0`

### Files

- `ivy_lsp/__main__.py` — retry loop around `start_mcp()`
- `pyproject.toml` — version floor for mcp and anyio

## Fix B: SessionStart Dead-PID Cleanup

### Problem

`cleanup-ivy-lsp.sh` runs on SessionEnd but doesn't trigger on session crash. PID files accumulate as stale entries in `/tmp/ivy-lsp-pids/`. `start-ivy-server.sh` cleans them but only runs when a new server starts for the same workspace.

### Solution

New `hooks/scripts/cleanup-stale-pids.sh` registered as a SessionStart hook. Iterates all PID files, checks `kill -0`, removes dead entries. Runs before server startup scripts.

```bash
#!/usr/bin/env bash
PID_DIR="/tmp/ivy-lsp-pids"
[ -d "$PID_DIR" ] || exit 0
for pidfile in "$PID_DIR"/*.pid; do
    [ -f "$pidfile" ] || continue
    pid="$(cat "$pidfile" 2>/dev/null)" || continue
    if [ -n "$pid" ] && ! kill -0 "$pid" 2>/dev/null; then
        rm -f "$pidfile" 2>/dev/null || true
    fi
done
exit 0
```

### Files

- New: `hooks/scripts/cleanup-stale-pids.sh`
- Modified: `hooks/hooks.json` — add SessionStart entry

## Fix D: Workspace Symbol Empty-Query Ranking via `synthetic` Flag

### Problem

`workspace_symbols.py:search_symbols()` returns `flat[:MAX_RESULTS]` (first 100 symbols in file-traversal order) when query is empty. Claude Code's LSP tool doesn't pass a query parameter, so the empty-query path always fires. Auto-generated names (`interp14`, `def12`, `bytes.spec.create[before224311]`) dominate results, pushing meaningful definitions (`cid`, `quic_packet_type`) out.

### Solution: `synthetic` flag on `IvySymbol`

**Which declarations produce auto-generated names:**

| Converter | Example Name | Detection |
|---|---|---|
| `_convert_interpret` | `interp14` | Always synthetic |
| `_convert_native` | `native3` | Always synthetic |
| `_convert_mixin` | `bytes.spec.create[after224332]` | Name contains `[` |
| `_convert_definition` | `def12` | Name matches `def\d+` |

**Step 1: Add field to `IvySymbol`** (`symbols.py`)

```python
synthetic: bool = False
```

Update `to_dict()` and `from_dict()` for cross-process index serialization.

**Step 2: Set flag at parse time** (`ast_to_symbols.py`)

- `_convert_interpret()` — `synthetic=True` unconditionally
- `_convert_native()` — `synthetic=True` unconditionally
- `_convert_mixin()` — `synthetic=True` when name contains `[`
- `_convert_definition()` — `synthetic=True` when name matches `re.fullmatch(r"def\d+", name)`

**Step 3: Propagate and rank** (`workspace_symbols.py`)

- Add `synthetic: bool` to `FlatSymbol` dataclass
- In `flatten_symbols()`, carry `sym.synthetic` through
- In `search_symbols()`, sort synthetic symbols last on empty query:

```python
if not query:
    return sorted(flat, key=lambda fs: (fs.synthetic, fs.qualified_name))[:MAX_RESULTS]
```

### Files

- `ivy_lsp/core/parsing/symbols.py` — add field + serialization
- `ivy_lsp/core/parsing/ast_to_symbols.py` — set flag in 4 converters
- `ivy_lsp/lsp/workspace_symbols.py` — propagate in `FlatSymbol`, use in empty-query sorting

## Testing

- **Fix A**: Manual — interrupt a tool call mid-flight to trigger cancel scope crash; verify `[MCP-RESTART]` log message appears and subsequent tool calls succeed.
- **Fix B**: Create stale PID files, start new session, verify they are cleaned up.
- **Fix D**: Add test case to `test_workspace_symbols_filtering.py` for empty-query sorting — verify synthetic symbols sort after real definitions. Verify `to_dict()`/`from_dict()` round-trip with `synthetic` field.

Re-run `/nct-health` after all fixes to verify improvement.

## Non-goals

- Fixing upstream MCP SDK cancel scope bug (architectural, awaiting [#577](https://github.com/modelcontextprotocol/python-sdk/issues/577))
- Increasing `MAX_RESULTS` beyond 100
- Adding `query` parameter to Claude Code's LSP tool interface
